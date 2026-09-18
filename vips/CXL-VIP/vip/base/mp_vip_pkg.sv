// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Verification IP (VIP) Package
// Protocols: PCIe Gen5/6, CXL 2.0/3.0, UCIe, UALink
// Coverage-Driven Random Regression Suite
//============================================================================
`ifndef MP_VIP_PKG_SV
`define MP_VIP_PKG_SV
package mp_vip_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  //==========================================================================
  // Protocol Enumeration
  //==========================================================================
  typedef enum int {
    PROTO_PCIE_GEN5 = 0,
    PROTO_PCIE_GEN6 = 1,
    PROTO_CXL_20    = 2,
    PROTO_CXL_30    = 3,
    PROTO_UCIE      = 4,
    PROTO_UALINK    = 5,
    PROTO_MAX       = 6
  } protocol_e;

  //==========================================================================
  // Protocol Speed/Rate Enumeration
  //==========================================================================
  typedef enum int {
    SPEED_GEN1  = 2500,    // 2.5 GT/s
    SPEED_GEN2  = 5000,    // 5.0 GT/s
    SPEED_GEN3  = 8000,    // 8.0 GT/s
    SPEED_GEN4  = 16000,   // 16.0 GT/s
    SPEED_GEN5  = 32000,   // 32.0 GT/s
    SPEED_GEN6  = 64000    // 64.0 GT/s
  } speed_e;

  // Protocol speed aliases (same GT/s rates as the PCIe base speeds;
  // kept as constants because enum values must be unique)
  localparam int SPEED_CXL20  = 32000;  // 32.0 GT/s (PCIe Gen5 base)
  localparam int SPEED_CXL30  = 32000;  // 32.0 GT/s with CXL.mem
  localparam int SPEED_UCIE   = 16000;  // 16-32 GT/s per lane
  localparam int SPEED_UALINK = 64000;  // 64-224 GT/s

  //==========================================================================
  // Link State Enumeration
  //==========================================================================
  typedef enum logic [3:0] {
    LINK_RESET      = 4'b0000,
    LINK_DETECT     = 4'b0001,
    LINK_POLLING    = 4'b0010,
    LINK_CONFIG     = 4'b0011,
    LINK_L0         = 4'b0100,
    LINK_L0S        = 4'b0101,
    LINK_L1         = 4'b0110,
    LINK_L2         = 4'b0111,
    LINK_RECOVERY   = 4'b1000,
    LINK_DISABLED   = 4'b1001,
    LINK_LOOPBACK   = 4'b1010,
    LINK_HOT_RESET  = 4'b1011
  } link_state_e;

  //==========================================================================
  // Transaction Type Enumeration
  //==========================================================================
  typedef enum logic [4:0] {
    // PCIe Types
    TLP_MEM_RD      = 5'b00000,
    TLP_MEM_WR      = 5'b00001,
    TLP_CFG_RD      = 5'b00010,
    TLP_CFG_WR      = 5'b00011,
    TLP_IO_RD       = 5'b00100,
    TLP_IO_WR       = 5'b00101,
    TLP_MSG         = 5'b00110,
    TLP_CPL         = 5'b00111,
    TLP_CPL_D       = 5'b01000,
    // CXL Types
    CXL_IO_RD       = 5'b01001,
    CXL_IO_WR       = 5'b01010,
    CXL_MEM_RD      = 5'b01011,
    CXL_MEM_WR      = 5'b01100,
    CXL_MEM_RW      = 5'b01101,
    CXL_BIAS_RD     = 5'b01110,
    CXL_BIAS_WR     = 5'b01111,
    CXL_CACHE_RD    = 5'b10000,
    CXL_CACHE_WR    = 5'b10001,
    // UCIe Types
    UCIE_REG_RD     = 5'b10010,
    UCIE_REG_WR     = 5'b10011,
    UCIE_DATA_RD    = 5'b10100,
    UCIE_DATA_WR    = 5'b10101,
    UCIE_SIDEBAND   = 5'b10110,
    // UALink Types
    UALINK_FLIT     = 5'b11000,
    UALINK_CTRL     = 5'b11001,
    UALINK_DATA     = 5'b11010,
    TLP_UNKNOWN     = 5'b11111
  } tlp_type_e;

  //==========================================================================
  // Transaction Status
  //==========================================================================
  typedef enum logic [2:0] {
    TXN_PENDING     = 3'b000,
    TXN_COMPLETE    = 3'b001,
    TXN_ERROR       = 3'b010,
    TXN_TIMEOUT     = 3'b011,
    TXN_RETRY       = 3'b100,
    TXN_ABORT       = 3'b101
  } txn_status_e;

  //==========================================================================
  // Configuration Structure
  //==========================================================================
  typedef struct packed {
    protocol_e      protocol;
    speed_e         speed;
    int             num_lanes;
    int             max_payload_size;
    bit             ecrc_enabled;
    bit             ltr_enabled;
    bit             sriov_enabled;
    bit             ari_enabled;
    bit             pasid_enabled;
    bit             ten_bit_tag;
    bit             vendor_ext;
    int             credit_timeout;
    int             replay_timeout;
  } protocol_cfg_t;

  //==========================================================================
  // Coverage Configuration
  //==========================================================================
  typedef struct packed {
    bit             cov_txn_types;
    bit             cov_addresses;
    bit             cov_data_patterns;
    bit             cov_link_states;
    bit             cov_error_injection;
    bit             cov_power_states;
    bit             cov_bandwidth;
    bit             cov_latency;
    bit             cov_cross_protocol;
  } coverage_cfg_t;

  //==========================================================================
  // Common Transaction Descriptor
  //==========================================================================
  class mp_txn_descriptor extends uvm_object;
    `uvm_object_utils(mp_txn_descriptor)

    rand protocol_e     protocol;
    rand tlp_type_e     txn_type;
    rand logic [63:0]   address;
    rand int            length;
    rand logic [31:0]   data[];
    rand logic [15:0]   requester_id;
    rand logic [15:0]   completer_id;
    rand logic [7:0]    tag;
    rand logic [2:0]    tc;           // Traffic Class
    rand logic          ep;           // Error Poisoned
    rand logic          td;           // TLP Digest
    rand logic [1:0]    attr;
    rand logic [9:0]    length_dw;    // Length in DW
    rand txn_status_e   status;
    rand int            delay_cycles;
    rand bit            inject_error;
    rand bit            trigger_irq;

    // Protocol-specific fields
    rand logic [15:0]   cxl_meta;
    rand logic [7:0]    ucie_credits;
    rand logic [3:0]    ucie_vc;
    rand logic [3:0]    ualink_vc;

    // Timestamp
    time                start_time;
    time                end_time;

    constraint c_length {
      length inside {[1:4096]};
      length % 4 == 0;
    }
    constraint c_length_dw {
      length_dw == (length / 4);
      length_dw inside {[1:1024]};
    }
    constraint c_address_align {
      address[1:0] == 2'b00;  // DWORD aligned
    }
    constraint c_pcie_addr {
      if (protocol inside {PROTO_PCIE_GEN5, PROTO_PCIE_GEN6})
        address[63:32] == 32'h0000_0000;
    }
    constraint c_cxl_addr {
      if (protocol inside {PROTO_CXL_20, PROTO_CXL_30})
        address inside {[64'h0 : 64'h000F_FFFF_FFFF_FFFF]};
    }
    constraint c_ucie_addr {
      if (protocol == PROTO_UCIE)
        address inside {[64'h0 : 64'hFFFF]};
    }
    constraint c_data_size {
      data.size() == length_dw;
    }
    constraint c_delay {
      delay_cycles inside {[0:1000]};
    }
    constraint c_error_rate {
      inject_error dist { 0 := 95, 1 := 5 };  // 5% error injection
    }

    function new(string name = "mp_txn_descriptor");
      super.new(name);
    endfunction

    function void post_randomize();
      start_time = $time;
    endfunction

    function void set_complete(txn_status_e s);
      status = s;
      end_time = $time;
    endfunction

    function int get_latency_ns();
      if (end_time > start_time)
        return int'((end_time - start_time) / 1ns);
      else
        return 0;
    endfunction

    virtual function string convert2string();
      return $sformatf("protocol=%s type=%s addr=0x%016X len=%0d status=%s lat=%0dns",
        protocol.name(), txn_type.name(), address, length, status.name(), get_latency_ns());
    endfunction
  endclass

  //==========================================================================
  // Base Sequence Item
  //==========================================================================
  class mp_sequence_item extends uvm_sequence_item;
    `uvm_object_utils(mp_sequence_item)
    rand mp_txn_descriptor txn;

    constraint c_default {
      txn.protocol != PROTO_MAX;
    }

    function new(string name = "mp_sequence_item");
      super.new(name);
      txn = mp_txn_descriptor::type_id::create("txn");
    endfunction

    virtual function string convert2string();
      return txn.convert2string();
    endfunction
  endclass

  //==========================================================================
  // Protocol Configuration Object
  //==========================================================================
  class mp_protocol_config extends uvm_object;
    `uvm_object_utils(mp_protocol_config)
    protocol_e      protocol;
    protocol_cfg_t  cfg;
    coverage_cfg_t  cov_cfg;

    function new(string name = "mp_protocol_config", protocol_e p = PROTO_PCIE_GEN5);
      super.new(name);
      protocol = p;
      set_default_cfg();
    endfunction

    function void set_default_cfg();
      cfg.num_lanes        = 16;
      cfg.max_payload_size = 4096;
      cfg.ecrc_enabled     = 1;
      cfg.credit_timeout   = 1000;
      cfg.replay_timeout   = 512;
      cov_cfg = '{default: 1'b1};
    endfunction
  endclass

  //==========================================================================
  // Base Scoreboard (observed-transaction accounting)
  //==========================================================================
  class mp_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(mp_scoreboard)
    uvm_analysis_imp #(mp_sequence_item, mp_scoreboard) analysis_imp;

    mp_sequence_item expected_queue[$];
    mp_sequence_item received_queue[$];
    int txn_count;
    int error_count;
    int mismatch_count;

    function new(string name = "mp_scoreboard", uvm_component parent = null);
      super.new(name, parent);
      analysis_imp = new("analysis_imp", this);
    endfunction

    virtual function void write(mp_sequence_item txn);
      received_queue.push_back(txn);
      txn_count++;
      `uvm_info("SCOREBOARD", $sformatf("Received: %s", txn.convert2string()), UVM_MEDIUM)
      check_transaction(txn);
    endfunction

    virtual function void check_transaction(mp_sequence_item txn);
      if (txn.txn.status == TXN_ERROR) begin
        error_count++;
        `uvm_warning("SCOREBOARD", "Transaction completed with error status")
      end
    endfunction

    virtual function void report_phase(uvm_phase phase);
      super.report_phase(phase);
      `uvm_info("SCOREBOARD_REPORT", $sformatf(
        "Total Transactions: %0d | Errors: %0d | Mismatches: %0d",
        txn_count, error_count, mismatch_count), UVM_LOW)
    endfunction
  endclass

  //==========================================================================
  // Functional Coverage Model
  //==========================================================================
  class mp_coverage_model extends uvm_component;
    `uvm_component_utils(mp_coverage_model)

    protocol_e     txn_protocol;
    tlp_type_e     txn_type;
    logic [63:0]   address;
    int            latency_ns;
    bit            all_zeros, all_ones, walking_ones, walking_zeros, is_random;
    int            error_type;
    bit            recovery_triggered;

    // Transaction coverage (protocol config x transaction type cross)
    covergroup cg_txn_type;
      option.per_instance = 1;
      cp_protocol: coverpoint txn_protocol {
        bins pcie_gen5 = {PROTO_PCIE_GEN5};
        bins pcie_gen6 = {PROTO_PCIE_GEN6};
        bins cxl20     = {PROTO_CXL_20};
        bins cxl30     = {PROTO_CXL_30};
        bins ucie      = {PROTO_UCIE};
        bins ualink    = {PROTO_UALINK};
      }
      cp_txn_type: coverpoint txn_type {
        bins mem_rd = {TLP_MEM_RD, CXL_MEM_RD, UCIE_DATA_RD, UALINK_DATA};
        bins mem_wr = {TLP_MEM_WR, CXL_MEM_WR, UCIE_DATA_WR};
        bins cfg_rd = {TLP_CFG_RD, UCIE_REG_RD};
        bins cfg_wr = {TLP_CFG_WR, UCIE_REG_WR};
        bins cpl    = {TLP_CPL, TLP_CPL_D};
        bins msg    = {TLP_MSG, UALINK_CTRL, UCIE_SIDEBAND};
        bins io     = {TLP_IO_RD, TLP_IO_WR, CXL_IO_RD, CXL_IO_WR};
        bins cache  = {CXL_CACHE_RD, CXL_CACHE_WR};
        bins bias   = {CXL_BIAS_RD, CXL_BIAS_WR};
        bins flit   = {UALINK_FLIT};
      }
      cross_protocol_txn: cross cp_protocol, cp_txn_type;
    endgroup

    // Address map coverage
    covergroup cg_address_map;
      option.per_instance = 1;
      cp_address_range: coverpoint address[63:40] {
        bins low_mem  = {[24'h000000 : 24'h00000F]};
        bins mid_mem  = {[24'h000010 : 24'h0000FF]};
        bins high_mem = {[24'h000100 : 24'hFFFFFF]};
      }
      cp_address_align: coverpoint address[3:0] {
        bins dword_aligned = {4'h0};
        bins other_align   = {[4'h1 : 4'hF]};
      }
      cx_range_align: cross cp_address_range, cp_address_align;
    endgroup

    // Data pattern coverage
    covergroup cg_data_patterns;
      option.per_instance = 1;
      cp_all_zeros:     coverpoint all_zeros     { bins yes = {1}; bins no = {0}; }
      cp_all_ones:      coverpoint all_ones      { bins yes = {1}; bins no = {0}; }
      cp_walking_ones:  coverpoint walking_ones  { bins yes = {1}; bins no = {0}; }
      cp_walking_zeros: coverpoint walking_zeros { bins yes = {1}; bins no = {0}; }
      cp_random:        coverpoint is_random     { bins yes = {1}; bins no = {0}; }
    endgroup

    // Latency coverage
    covergroup cg_latency;
      option.per_instance = 1;
      cp_latency_ns: coverpoint latency_ns {
        bins fast   = {[0:100]};
        bins med    = {[101:500]};
        bins slow   = {[501:2000]};
        bins xslow  = default;
      }
      cp_protocol_lat: coverpoint txn_protocol;
      cross cp_latency_ns, cp_protocol_lat;
    endgroup

    // Error injection coverage
    covergroup cg_error_injection;
      option.per_instance = 1;
      cp_error_type: coverpoint error_type {
        bins none  = {0};
        bins ecrc  = {1};
        bins lcrc  = {2};
        bins frame = {3};
        bins proto = {4};
      }
      cp_recovery: coverpoint recovery_triggered { bins yes = {1}; bins no = {0}; }
      cross cp_error_type, cp_recovery;
    endgroup

    //========================================================================
    // Link FSM (LTSSM) transition coverage
    //========================================================================
    covergroup cg_link_fsm with function sample(link_state_e s);
      option.per_instance = 1;
      cp_link_state: coverpoint s {
        bins st_reset    = {LINK_RESET};
        bins st_detect   = {LINK_DETECT};
        bins st_polling  = {LINK_POLLING};
        bins st_config   = {LINK_CONFIG};
        bins st_l0       = {LINK_L0};
        bins st_l0s      = {LINK_L0S};
        bins st_l1       = {LINK_L1};
        bins st_l2       = {LINK_L2};
        bins st_recovery = {LINK_RECOVERY};
      }
      cp_link_trans: coverpoint s {
        bins link_train  = (LINK_RESET => LINK_DETECT => LINK_POLLING => LINK_CONFIG => LINK_L0);
        bins enter_l0s   = (LINK_L0 => LINK_L0S);
        bins exit_l0s    = (LINK_L0S => LINK_L0);
        bins enter_l1    = (LINK_L0 => LINK_L1);
        bins exit_l1     = (LINK_L1 => LINK_L0);
        bins to_recovery = (LINK_L0 => LINK_RECOVERY);
      }
    endgroup

    function new(string name = "mp_coverage_model", uvm_component parent = null);
      super.new(name, parent);
      cg_txn_type = new();
      cg_address_map = new();
      cg_data_patterns = new();
      cg_latency = new();
      cg_error_injection = new();
      cg_link_fsm = new();
    endfunction

    virtual function void sample_transaction(mp_txn_descriptor txn);
      txn_protocol = txn.protocol;
      txn_type     = txn.txn_type;
      address      = txn.address;
      latency_ns   = txn.get_latency_ns();
      // Data pattern analysis
      if (txn.data.size() > 0) begin
        all_zeros = 1; all_ones = 1;
        walking_ones = 0; walking_zeros = 0; is_random = 1;
        foreach (txn.data[i]) begin
          if (txn.data[i] != 32'h0000_0000) all_zeros = 0;
          if (txn.data[i] != 32'hFFFF_FFFF) all_ones  = 0;
        end
        begin
          logic [31:0] d;
          d = txn.data[0];
          if ($countones(d) == 1)  walking_ones  = 1;
          if ($countones(~d) == 1) walking_zeros = 1;
        end
        if (all_zeros || all_ones || walking_ones || walking_zeros) is_random = 0;
      end
      cg_txn_type.sample();
      cg_address_map.sample();
      cg_data_patterns.sample();
      cg_latency.sample();
    endfunction

    virtual function void sample_error(int err_type, bit recovery);
      error_type = err_type;
      recovery_triggered = recovery;
      cg_error_injection.sample();
    endfunction

    virtual function void sample_link_state(link_state_e s);
      cg_link_fsm.sample(s);
    endfunction

    virtual function real get_coverage();
      real cov = 0;
      cov += cg_txn_type.get_coverage();
      cov += cg_address_map.get_coverage();
      cov += cg_data_patterns.get_coverage();
      cov += cg_latency.get_coverage();
      cov += cg_error_injection.get_coverage();
      cov += cg_link_fsm.get_coverage();
      return cov / 6.0;
    endfunction
  endclass

  //==========================================================================
  // UVM component/object class hierarchy (compiled inside this package so
  // that declaration order is well defined; each file has an include guard
  // and becomes a no-op at its standalone compilation unit position)
  //==========================================================================
  `include "mp_sequencer.sv"
  `include "mp_driver.sv"
  `include "mp_monitor.sv"
  `include "mp_agent.sv"
  `include "cxl_protocol_checker.sv"

  //==========================================================================
  // Minimal protocol checker stubs for protocols whose dedicated checker
  // class is not part of this tree. They reuse the CXL checker's generic
  // mp_vip_if rule checks so the multi-protocol env API is preserved.
  //==========================================================================
  class pcie_protocol_checker extends cxl_protocol_checker;
    `uvm_component_utils(pcie_protocol_checker)
    function new(string name = "pcie_protocol_checker", uvm_component parent = null);
      super.new(name, parent);
    endfunction
  endclass

  class ucie_protocol_checker extends cxl_protocol_checker;
    `uvm_component_utils(ucie_protocol_checker)
    function new(string name = "ucie_protocol_checker", uvm_component parent = null);
      super.new(name, parent);
    endfunction
  endclass

  class ualink_protocol_checker extends cxl_protocol_checker;
    `uvm_component_utils(ualink_protocol_checker)
    function new(string name = "ualink_protocol_checker", uvm_component parent = null);
      super.new(name, parent);
    endfunction
  endclass

  `include "mp_env.sv"

  // Sequences
  `include "mp_base_sequence.sv"
  `include "mp_error_inject_sequence.sv"
  `include "mp_power_mgmt_sequence.sv"
  `include "mp_random_sequence.sv"
  `include "mp_regression_sequence.sv"

  // Tests
  `include "mp_base_test.sv"
  `include "mp_cxl_test.sv"
  `include "mp_error_inject_test.sv"
  `include "mp_power_mgmt_test.sv"
  `include "mp_random_regression_test.sv"

endpackage
`endif
