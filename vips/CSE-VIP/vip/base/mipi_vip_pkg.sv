// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//============================================================================
//  MIPI Protocol Verification IP (VIP) Package
//  Protocols: CSI-2, DSI, D-PHY, C-PHY, M-PHY, UniPro, DigRFv4, HSI, CSE 2.0
//  MAC + PHY Layer Coverage-Driven Random Regression Suite
//
//  Deepened: CSE command/response channel. mipi_driver performs the real
//  cse_valid/cse_ready command handshake and captures the cse_irq response;
//  mipi_monitor decodes the same transactions from the bus; mipi_sb compares
//  expected (driver) vs observed (monitor) end-to-end.
//============================================================================
`ifndef MIPI_VIP_PKG_SV
`define MIPI_VIP_PKG_SV

package mipi_vip_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `uvm_analysis_imp_decl(_exp)
  `uvm_analysis_imp_decl(_obs)

  typedef enum int { MIPI_CSI2=0, MIPI_DSI=1, MIPI_DPHY=2, MIPI_CPHY=3,
                     MIPI_MPHY=4, MIPI_UNIPRO=5, MIPI_DIGRF=6, MIPI_HSI=7,
                     MIPI_CSE=8, MIPI_MAX=9 } mipi_protocol_e;

  // NOTE: enum values made unique for strict-LRM tools (original had
  // duplicates); values remain monotonic per protocol family.
  typedef enum int { SPEED_DPHY_1G5=1500, SPEED_DPHY_2G5=2500, SPEED_DPHY_4G5=4500,
                     SPEED_CPHY_2G=2000, SPEED_CPHY_4G=4000,
                     SPEED_MPHY_G1=1248, SPEED_MPHY_G2=2496, SPEED_MPHY_G3=4992,
                     SPEED_MPHY_G4=9984, SPEED_MPHY_G5=19968,
                     SPEED_UNIPRO_1G=1000, SPEED_UNIPRO_2G=2001, SPEED_UNIPRO_4G=4001,
                     SPEED_HSI_150M=150, SPEED_DIGRF_150M=151,
                     SPEED_CSE_1G=1001 } mipi_speed_e;

  typedef enum logic [3:0] { ST_STOP=4'h0, ST_HS_REQ=4'h1, ST_HS_ZERO=4'h2,
                             ST_HS_SYNC=4'h3, ST_HS_DATA=4'h4, ST_HS_TRAIL=4'h5,
                             ST_HS_EXIT=4'h6, ST_LP11=4'h7, ST_LP00=4'h8,
                             ST_LP01=4'h9, ST_LP10=4'hA, ST_TA_REQ=4'hB,
                             ST_TA_GRANT=4'hC, ST_ULPS=4'hD } mipi_lane_state_e;

  typedef enum logic [5:0] { PKT_FS=6'h00, PKT_FE=6'h01, PKT_LS=6'h02, PKT_LE=6'h03,
                             PKT_RGB565=6'h0E, PKT_RGB666=6'h1E, PKT_RGB888=6'h2E,
                             PKT_RAW6=6'h28, PKT_RAW7=6'h29, PKT_RAW8=6'h2A,
                             PKT_RAW10=6'h2B, PKT_RAW12=6'h2C, PKT_RAW14=6'h2D,
                             PKT_YUV422_8B=6'h18, PKT_YUV422_10B=6'h19,
                             PKT_USER_0=6'h30, PKT_USER_1=6'h31, PKT_USER_2=6'h32,
                             PKT_USER_3=6'h33, PKT_USER_4=6'h34, PKT_USER_5=6'h35,
                             PKT_USER_6=6'h36, PKT_USER_7=6'h37,
                             PKT_NULL=6'h3A, PKT_BLANK=6'h3B,
                             PKT_EMBEDDED=6'h3C } mipi_pkt_type_e;

  typedef enum logic [2:0] { VC_0=3'd0, VC_1=3'd1, VC_2=3'd2, VC_3=3'd3,
                             VC_4=3'd4, VC_5=3'd5, VC_6=3'd6, VC_7=3'd7 } mipi_vc_e;

  // CSE 2.0 command set (cse_cmd[3:0]); encodings 10..15 are reserved and
  // must be answered with the error response 0xEE by the target.
  typedef enum logic [3:0] { CSE_NOP        = 4'd0,
                             CSE_RD_REG     = 4'd1,
                             CSE_WR_REG     = 4'd2,
                             CSE_RD_MEM     = 4'd3,
                             CSE_WR_MEM     = 4'd4,
                             CSE_GET_STATUS = 4'd5,
                             CSE_SOFT_RESET = 4'd6,
                             CSE_IRQ_ACK    = 4'd7,
                             CSE_SET_CFG    = 4'd8,
                             CSE_GET_CFG    = 4'd9 } cse_cmd_e;

  localparam logic [7:0] CSE_RESP_ERR   = 8'hEE;  // reserved-command error
  localparam logic [7:0] CSE_RESP_RST   = 8'hA5;  // soft-reset acknowledge
  localparam int unsigned CSE_NUM_REGS  = 16;     // operand[7:4] = address
  localparam int unsigned CSE_NUM_MEM   = 16;     // operand[7:4] = address

  //============================================================================
  // Transaction
  //============================================================================
  class mipi_txn extends uvm_object;
    `uvm_object_utils(mipi_txn)

    rand mipi_protocol_e protocol;
    rand mipi_pkt_type_e pkt_type;
    rand mipi_vc_e       vc;
    rand logic [15:0]    word_count;
    rand logic [31:0]    data[];
    rand logic [15:0]    ecc;
    rand logic [31:0]    crc;
    rand int             lane_count;
    rand int             data_rate;
    rand bit             lp_mode;
    rand bit             hs_mode;
    rand bit             ulps;
    rand bit             inject_err;
    rand int             delay;

    // CSE command/response fields
    rand cse_cmd_e       cse_cmd;
    rand logic [7:0]     cse_operand;   // [7:4]=addr, [3:0]=write data
    logic [7:0]          cse_resp;      // response byte (observed/expected)
    bit                  cse_expect_err;// reserved-command injection

    constraint c_wc   { word_count inside {[1:4095]}; }
    constraint c_data { data.size() == ((word_count+1)/2); }
    constraint c_lane {
      if (protocol==MIPI_DPHY) lane_count inside {1,2,4};
      else if (protocol==MIPI_CPHY) lane_count inside {1,2,3};
      else if (protocol==MIPI_MPHY) lane_count inside {1,2};
      else lane_count inside {1,2,4};
    }
    constraint c_mode { lp_mode != hs_mode; }
    constraint c_cse  { cse_cmd != CSE_SOFT_RESET; }

    function new(string name = "mipi_txn");
      super.new(name);
    endfunction

    function void copy_cse_from(mipi_txn rhs);
      cse_cmd        = rhs.cse_cmd;
      cse_operand    = rhs.cse_operand;
      cse_resp       = rhs.cse_resp;
      cse_expect_err = rhs.cse_expect_err;
      protocol       = rhs.protocol;
      inject_err     = rhs.inject_err;
    endfunction

    virtual function string convert2string();
      return $sformatf("%s pkt=%s vc=%0d wc=%0d cse_cmd=%0d op=0x%02h resp=0x%02h",
                       protocol.name(), pkt_type.name(), vc, word_count,
                       cse_cmd, cse_operand, cse_resp);
    endfunction
  endclass : mipi_txn

  class mipi_seq_item extends uvm_sequence_item;
    `uvm_object_utils(mipi_seq_item)
    rand mipi_txn txn;

    function new(string name = "mipi_seq_item");
      super.new(name);
      txn = mipi_txn::type_id::create("txn");
    endfunction
  endclass : mipi_seq_item

  //============================================================================
  // Sequencer
  //============================================================================
  class mipi_sequencer extends uvm_sequencer #(mipi_seq_item);
    `uvm_component_utils(mipi_sequencer)
    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction
  endclass : mipi_sequencer

  //============================================================================
  // Driver -- CSE command/response handshake + expected publishing
  //============================================================================
  class mipi_driver extends uvm_driver #(mipi_seq_item);
    `uvm_component_utils(mipi_driver)

    virtual mipi_vip_if vif;
    uvm_analysis_port #(mipi_seq_item) drv_ap;  // expected items for scoreboard

    // driver-side mirror of the CSE target state
    protected bit [7:0] reg_mirror [CSE_NUM_REGS];
    protected bit [7:0] mem_mirror [CSE_NUM_MEM];
    protected bit [7:0] cfg_mirror = 8'h00;
    protected bit       err_sticky = 1'b0;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      drv_ap = new("drv_ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "MIPI virtual interface not found")
    endfunction

    task run_phase(uvm_phase phase);
      bus_idle();
      forever begin
        seq_item_port.get_next_item(req);
        drive_cse(req);
        seq_item_port.item_done();
      end
    endtask

    protected task bus_idle();
      vif.drv_cb.cse_valid <= 1'b0;
      vif.drv_cb.cse_cmd   <= 4'h0;
      vif.drv_cb.cse_data  <= 8'hzz;
      vif.drv_cb.valid     <= 1'b0;
      vif.drv_cb.sop      <= 1'b0;
      vif.drv_cb.eop      <= 1'b0;
      vif.drv_cb.dphy_hs_rqst <= 1'b0;
      vif.drv_cb.unipro_valid <= 1'b0;
      vif.drv_cb.hsi_valid    <= 1'b0;
      @(vif.drv_cb);
    endtask

    // expected response from the mirror model
    protected function bit [7:0] expected_resp(mipi_txn t);
      case (t.cse_cmd)
        CSE_NOP:        return 8'h00;
        CSE_RD_REG:     return reg_mirror[t.cse_operand[7:4]];
        CSE_WR_REG:     return {4'h0, t.cse_operand[3:0]};   // echoes write data
        CSE_RD_MEM:     return mem_mirror[t.cse_operand[7:4]];
        CSE_WR_MEM:     return {4'h0, t.cse_operand[3:0]};
        CSE_GET_STATUS: return {6'h00, err_sticky, 1'b1};    // bit0=ready, bit1=err
        CSE_SOFT_RESET: return CSE_RESP_RST;
        CSE_IRQ_ACK:    return 8'h00;
        CSE_SET_CFG:    return t.cse_operand;
        CSE_GET_CFG:    return cfg_mirror;
        default:        return CSE_RESP_ERR;                 // reserved
      endcase
    endfunction

    protected function void update_mirror(mipi_txn t);
      case (t.cse_cmd)
        CSE_WR_REG: reg_mirror[t.cse_operand[7:4]] = {4'h0, t.cse_operand[3:0]};
        CSE_WR_MEM: mem_mirror[t.cse_operand[7:4]] = {4'h0, t.cse_operand[3:0]};
        CSE_SET_CFG: cfg_mirror = t.cse_operand;
        CSE_SOFT_RESET: begin
          foreach (reg_mirror[i]) reg_mirror[i] = 8'h00;
          foreach (mem_mirror[i]) mem_mirror[i] = 8'h00;
          cfg_mirror = 8'h00;
          err_sticky = 1'b0;
        end
        default: ;
      endcase
      if (t.cse_cmd > CSE_GET_CFG) err_sticky = 1'b1;  // reserved command
    endfunction

    protected task drive_cse(mipi_seq_item item);
      mipi_txn t = item.txn;
      mipi_seq_item exp;
      mipi_txn   et;

      // ---- command phase: valid/ready handshake --------------------------
      vif.drv_cb.cse_cmd   <= t.cse_cmd;
      vif.drv_cb.cse_data  <= t.cse_operand;
      vif.drv_cb.cse_valid <= 1'b1;
      do @(vif.drv_cb); while (vif.drv_cb.cse_ready !== 1'b1);
      vif.drv_cb.cse_valid <= 1'b0;
      vif.drv_cb.cse_data  <= 8'hzz;   // host releases the bidirectional bus

      // ---- response phase: wait for cse_irq, sample response -------------
      do @(posedge vif.clk); while (vif.cse_irq !== 1'b1);
      t.cse_resp = vif.cse_data;
      do @(posedge vif.clk); while (vif.cse_irq !== 1'b0);

      // ---- publish expected item ------------------------------------------
      exp = mipi_seq_item::type_id::create("exp");
      et  = mipi_txn::type_id::create("et");
      exp.txn = et;
      et.copy_cse_from(t);
      et.cse_resp = expected_resp(t);
      drv_ap.write(exp);

      // mirror updates take effect after the response is computed
      update_mirror(t);
    endtask
  endclass : mipi_driver

  //============================================================================
  // Monitor -- decodes CSE command/response transactions from the bus
  //============================================================================
  class mipi_monitor extends uvm_monitor;
    `uvm_component_utils(mipi_monitor)

    virtual mipi_vip_if vif;
    uvm_analysis_port #(mipi_seq_item) item_collected_port;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      item_collected_port = new("item_collected_port", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "MIPI virtual interface not found")
    endfunction

    task run_phase(uvm_phase phase);
      bit       prev_hs = 1'b0;    // previous (valid && ready)
      bit       prev_irq = 1'b0;
      bit       cmd_open = 1'b0;
      logic [3:0] pend_cmd;
      logic [7:0] pend_op;

      forever begin
        @(vif.mon_cb);
        if (vif.rst_n !== 1'b1) begin
          prev_hs  = 1'b0;
          prev_irq = 1'b0;
          cmd_open = 1'b0;
          continue;
        end

        // command accept: valid && ready handshake (once per command)
        if (vif.mon_cb.cse_valid && vif.mon_cb.cse_ready && !prev_hs) begin
          pend_cmd = vif.mon_cb.cse_cmd;
          pend_op  = vif.mon_cb.cse_data;
          cmd_open = 1'b1;
        end
        prev_hs = vif.mon_cb.cse_valid && vif.mon_cb.cse_ready;

        // response: cse_irq rising edge, response on cse_data
        if (vif.mon_cb.cse_irq && !prev_irq && cmd_open) begin
          mipi_seq_item item = mipi_seq_item::type_id::create("item");
          mipi_txn t = mipi_txn::type_id::create("t");
          item.txn = t;
          t.protocol    = MIPI_CSE;
          t.cse_cmd     = cse_cmd_e'(pend_cmd);
          t.cse_operand = pend_op;
          t.cse_resp    = vif.mon_cb.cse_data;
          t.cse_expect_err = (pend_cmd > 4'd9);
          item_collected_port.write(item);
          cmd_open = 1'b0;
        end
        prev_irq = vif.mon_cb.cse_irq;
      end
    endtask
  endclass : mipi_monitor

  //============================================================================
  // Agent
  //============================================================================
  class mipi_agent extends uvm_agent;
    `uvm_component_utils(mipi_agent)

    mipi_sequencer sqr;
    mipi_driver    drv;
    mipi_monitor   mon;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      mon = mipi_monitor::type_id::create("mon", this);
      if (is_active == UVM_ACTIVE) begin
        sqr = mipi_sequencer::type_id::create("sqr", this);
        drv = mipi_driver::type_id::create("drv", this);
      end
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (is_active == UVM_ACTIVE)
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction
  endclass : mipi_agent

  //============================================================================
  // Coverage (original MAC/PHY CG + 2 deepened CSE covergroups)
  //============================================================================
  class mipi_cov extends uvm_component;
    `uvm_component_utils(mipi_cov)

    uvm_analysis_imp #(mipi_seq_item, mipi_cov) analysis_export;

    mipi_protocol_e txn_protocol;
    mipi_pkt_type_e txn_pkt;
    mipi_vc_e       txn_vc;
    int             txn_lane;
    int             txn_mode;
    logic [3:0]     txn_cse_cmd;
    logic [7:0]     txn_cse_operand;
    logic [7:0]     txn_cse_resp;
    bit             txn_cse_err;

    covergroup cg_mipi;
      option.per_instance = 1;
      cp_prot: coverpoint txn_protocol {
        bins csi2   = {MIPI_CSI2};
        bins dsi    = {MIPI_DSI};
        bins dphy   = {MIPI_DPHY};
        bins cphy   = {MIPI_CPHY};
        bins mphy   = {MIPI_MPHY};
        bins unipro = {MIPI_UNIPRO};
        bins digrf  = {MIPI_DIGRF};
        bins hsi    = {MIPI_HSI};
        bins cse    = {MIPI_CSE};
      }
      cp_pkt: coverpoint txn_pkt {
        bins fs     = {PKT_FS};
        bins fe     = {PKT_FE};
        bins ls     = {PKT_LS};
        bins le     = {PKT_LE};
        bins rgb    = {PKT_RGB565, PKT_RGB666, PKT_RGB888};
        bins raw    = {PKT_RAW6, PKT_RAW8, PKT_RAW10, PKT_RAW12};
        bins yuv    = {PKT_YUV422_8B, PKT_YUV422_10B};
        bins user   = {[PKT_USER_0:PKT_USER_7]};
        bins null_b = {PKT_NULL, PKT_BLANK};
      }
      cp_vc: coverpoint txn_vc {
        bins vc0   = {VC_0};
        bins vc1   = {VC_1};
        bins vc2   = {VC_2};
        bins vc3   = {VC_3};
        bins vc4_7 = {[VC_4:VC_7]};
      }
      cp_lane: coverpoint txn_lane {
        bins x1 = {1};
        bins x2 = {2};
        bins x3 = {3};
        bins x4 = {4};
      }
      cp_mode: coverpoint txn_mode {
        bins lp   = {0};
        bins hs   = {1};
        bins ulps = {2};
      }
      cross_pkt_vc: cross cp_pkt, cp_vc;
      cross_prot_lane: cross cp_prot, cp_lane;
    endgroup

    // CSE command/config coverage
    covergroup cg_cse_cmd;
      option.per_instance = 1;
      cp_cse_cmd: coverpoint txn_cse_cmd {
        bins nop   = {CSE_NOP};
        bins rdreg = {CSE_RD_REG};
        bins wrreg = {CSE_WR_REG};
        bins rdmem = {CSE_RD_MEM};
        bins wrmem = {CSE_WR_MEM};
        bins stat  = {CSE_GET_STATUS};
        bins rst   = {CSE_SOFT_RESET};
        bins ack   = {CSE_IRQ_ACK};
        bins cfg   = {CSE_SET_CFG, CSE_GET_CFG};
      }
      cp_cse_addr: coverpoint txn_cse_operand[7:4] {
        bins first = {0};
        bins last  = {15};
        bins mid   = {[1:14]};
      }
      cp_cse_err: coverpoint txn_cse_err {
        bins legal = {0};
        bins reserved = {1};
      }
      cx_cmd_addr: cross cp_cse_cmd, cp_cse_addr;
      cx_cmd_err:  cross cp_cse_cmd, cp_cse_err;
    endgroup

    // CSE response/status coverage
    covergroup cg_cse_resp;
      option.per_instance = 1;
      cp_resp: coverpoint txn_cse_resp {
        bins zero = {8'h00};
        bins ones = {8'hFF};
        bins err  = {CSE_RESP_ERR};
        bins rst_ack = {CSE_RESP_RST};
        bins other = default;
      }
      cp_wdata: coverpoint txn_cse_operand[3:0] {
        bins zero = {0};
        bins ones = {15};
        bins mid  = {[1:14]};
      }
      cp_resp_err: coverpoint txn_cse_err {
        bins legal = {0};
        bins reserved = {1};
      }
      cx_resp_cmd: cross cp_resp, cp_resp_err;
    endgroup

    function new(string name = "mipi_cov", uvm_component parent = null);
      super.new(name, parent);
      analysis_export = new("analysis_export", this);
      cg_mipi     = new();
      cg_cse_cmd  = new();
      cg_cse_resp = new();
    endfunction

    function void sample(mipi_txn t);
      txn_protocol = t.protocol;
      txn_pkt      = t.pkt_type;
      txn_vc       = t.vc;
      txn_lane     = t.lane_count;
      txn_mode     = t.lp_mode ? 0 : (t.hs_mode ? 1 : 2);
      cg_mipi.sample();
    endfunction

    function void sample_cse(mipi_txn t);
      txn_cse_cmd     = t.cse_cmd;
      txn_cse_operand = t.cse_operand;
      txn_cse_resp    = t.cse_resp;
      txn_cse_err     = t.cse_expect_err;
      cg_cse_cmd.sample();
      cg_cse_resp.sample();
    endfunction

    virtual function void write(mipi_seq_item item);
      sample(item.txn);
      sample_cse(item.txn);
    endfunction

    function real get_cov();
      return (cg_mipi.get_coverage() + cg_cse_cmd.get_coverage()
              + cg_cse_resp.get_coverage()) / 3.0;
    endfunction
  endclass : mipi_cov

  //============================================================================
  // Scoreboard: legacy counter + CSE end-to-end exp/obs comparison
  //============================================================================
  class mipi_sb extends uvm_scoreboard;
    `uvm_component_utils(mipi_sb)

    uvm_analysis_imp #(mipi_seq_item, mipi_sb) analysis_imp;  // legacy counter
    uvm_analysis_imp_exp #(mipi_seq_item, mipi_sb) exp_ap;
    uvm_analysis_imp_obs #(mipi_seq_item, mipi_sb) obs_ap;

    int txn_cnt, err_cnt;
    int unsigned n_matches = 0, n_mismatches = 0;
    protected mipi_seq_item exp_q[$];

    function new(string name = "mipi_sb", uvm_component parent = null);
      super.new(name, parent);
      analysis_imp = new("analysis_imp", this);
      exp_ap = new("exp_ap", this);
      obs_ap = new("obs_ap", this);
    endfunction

    virtual function void write(mipi_seq_item item);
      txn_cnt++;
      if (item.txn.inject_err) err_cnt++;
    endfunction

    virtual function void write_exp(mipi_seq_item item);
      exp_q.push_back(item);
    endfunction

    virtual function void write_obs(mipi_seq_item item);
      txn_cnt++;
      compare_cse(item);
    endfunction

    protected function void compare_cse(mipi_seq_item obs);
      int idx[$];
      idx = exp_q.find_first_index with (item.txn.cse_cmd == obs.txn.cse_cmd);
      if (idx.size() == 0) begin
        n_mismatches++;
        `uvm_error(get_type_name(),
          $sformatf("CSE SB: observed %s with no expected item",
                    obs.txn.convert2string()))
        return;
      end
      begin
        mipi_seq_item exp = exp_q[idx[0]];
        exp_q.delete(idx[0]);
        if (exp.txn.cse_cmd !== obs.txn.cse_cmd ||
            exp.txn.cse_operand !== obs.txn.cse_operand ||
            exp.txn.cse_resp !== obs.txn.cse_resp) begin
          n_mismatches++;
          `uvm_error(get_type_name(),
            $sformatf("CSE SB mismatch:\n  EXP: %s\n  OBS: %s",
                      exp.txn.convert2string(), obs.txn.convert2string()))
        end
        else begin
          n_matches++;
          `uvm_info(get_type_name(),
            $sformatf("CSE SB match: %s", obs.txn.convert2string()), UVM_HIGH)
        end
      end
    endfunction

    virtual function void report_phase(uvm_phase phase);
      `uvm_info("SB", $sformatf("TXN:%0d ERR:%0d", txn_cnt, err_cnt), UVM_LOW)
      `uvm_info("SB", $sformatf("CSE end-to-end: n_matches=%0d n_mismatches=%0d",
                n_matches, n_mismatches), UVM_LOW)
      if (exp_q.size() != 0)
        `uvm_error("SB", $sformatf("CSE SB: %0d expected items never observed",
                   exp_q.size()))
      if (n_mismatches != 0)
        `uvm_error("SB", "CSE end-to-end n_mismatches detected")
    endfunction
  endclass : mipi_sb

  //============================================================================
  // CSE Sequence library
  //============================================================================
  class cse_base_seq extends uvm_sequence #(mipi_seq_item);
    `uvm_object_utils(cse_base_seq)

    function new(string name = "cse_base_seq");
      super.new(name);
    endfunction

    task send_item(mipi_seq_item item);
      start_item(item);
      finish_item(item);
    endtask

    function mipi_seq_item mk_cse(cse_cmd_e cmd, bit [7:0] operand = 8'h00,
                                  bit expect_err = 1'b0);
      mipi_seq_item it = mipi_seq_item::type_id::create("it");
      it.txn.protocol       = MIPI_CSE;
      it.txn.cse_cmd        = cmd;
      it.txn.cse_operand    = operand;
      it.txn.cse_expect_err = expect_err;
      it.txn.pkt_type       = PKT_USER_0;
      it.txn.vc             = VC_0;
      it.txn.word_count     = 1;
      it.txn.lp_mode        = 1'b0;
      it.txn.hs_mode        = 1'b1;
      it.txn.lane_count     = 1;
      return it;
    endfunction
  endclass : cse_base_seq

  // ---- 1. register write/readback (normal) ---------------------------------
  class cse_wr_reg_seq extends cse_base_seq;
    `uvm_object_utils(cse_wr_reg_seq)
    function new(string name = "cse_wr_reg_seq");
      super.new(name);
    endfunction
    task body();
      for (int a = 0; a < 8; a++) begin
        send_item(mk_cse(CSE_WR_REG, {a[3:0], 4'hA - a[3:0]}));
        send_item(mk_cse(CSE_RD_REG, {a[3:0], 4'h0}));
      end
    endtask
  endclass : cse_wr_reg_seq

  // ---- 2. read sweep (normal: NOP/status/reg reads) -------------------------
  class cse_rd_seq extends cse_base_seq;
    `uvm_object_utils(cse_rd_seq)
    function new(string name = "cse_rd_seq");
      super.new(name);
    endfunction
    task body();
      send_item(mk_cse(CSE_NOP));
      send_item(mk_cse(CSE_GET_STATUS));
      for (int a = 0; a < 16; a++)
        send_item(mk_cse(CSE_RD_REG, {a[3:0], 4'h0}));
    endtask
  endclass : cse_rd_seq

  // ---- 3. memory write/readback ---------------------------------------------
  class cse_mem_seq extends cse_base_seq;
    `uvm_object_utils(cse_mem_seq)
    function new(string name = "cse_mem_seq");
      super.new(name);
    endfunction
    task body();
      for (int a = 0; a < 16; a++) begin
        send_item(mk_cse(CSE_WR_MEM, {a[3:0], a[3:0] ^ 4'hF}));
        send_item(mk_cse(CSE_RD_MEM, {a[3:0], 4'h0}));
      end
    endtask
  endclass : cse_mem_seq

  // ---- 4. error sequence (reserved commands -> 0xEE, sticky ERR) ------------
  class cse_error_seq extends cse_base_seq;
    `uvm_object_utils(cse_error_seq)
    function new(string name = "cse_error_seq");
      super.new(name);
    endfunction
    task body();
      mipi_seq_item it;
      for (int c = 10; c < 16; c++) begin
        it = mk_cse(cse_cmd_e'(c[3:0]), 8'h5A, 1'b1);
        send_item(it);
      end
      send_item(mk_cse(CSE_GET_STATUS));   // ERR bit must be set
      send_item(mk_cse(CSE_SOFT_RESET));   // clears ERR + state
      send_item(mk_cse(CSE_GET_STATUS));
    endtask
  endclass : cse_error_seq

  // ---- 5. reset sequence ------------------------------------------------------
  class cse_reset_seq extends cse_base_seq;
    `uvm_object_utils(cse_reset_seq)
    function new(string name = "cse_reset_seq");
      super.new(name);
    endfunction
    task body();
      send_item(mk_cse(CSE_WR_REG, 8'h3C));
      send_item(mk_cse(CSE_SET_CFG, 8'h77));
      send_item(mk_cse(CSE_SOFT_RESET));
      send_item(mk_cse(CSE_RD_REG, 8'h30));  // expect 0 after reset
      send_item(mk_cse(CSE_GET_CFG));        // expect 0 after reset
    endtask
  endclass : cse_reset_seq

  // ---- 6. back-to-back (no idle gap) -------------------------------------------
  class cse_b2b_seq extends cse_base_seq;
    `uvm_object_utils(cse_b2b_seq)
    int num_trans = 8;
    function new(string name = "cse_b2b_seq");
      super.new(name);
    endfunction
    task body();
      for (int i = 0; i < num_trans; i++) begin
        send_item(mk_cse(CSE_WR_REG, {i[3:0], i[3:0]}));
        send_item(mk_cse(CSE_RD_REG, {i[3:0], 4'h0}));
      end
    endtask
  endclass : cse_b2b_seq

  // ---- 7. stress (random legal command mix) -------------------------------------
  class cse_stress_seq extends cse_base_seq;
    `uvm_object_utils(cse_stress_seq)
    int num_trans = 48;
    function new(string name = "cse_stress_seq");
      super.new(name);
    endfunction
    task body();
      repeat (num_trans) begin
        mipi_seq_item it = mipi_seq_item::type_id::create("it");
        if (!it.randomize() with {
              txn.protocol == MIPI_CSE;
              txn.cse_cmd != CSE_SOFT_RESET;
              txn.cse_cmd <= CSE_GET_CFG;
              txn.word_count == 1;
              txn.lp_mode == 0;
              txn.hs_mode == 1;
            }) `uvm_error(get_type_name(), "cse_stress_seq randomize failed")
        send_item(it);
      end
    endtask
  endclass : cse_stress_seq

  // ---- 8. corner (first/last addr, extreme data, cfg, irq ack) -------------------
  class cse_corner_seq extends cse_base_seq;
    `uvm_object_utils(cse_corner_seq)
    function new(string name = "cse_corner_seq");
      super.new(name);
    endfunction
    task body();
      send_item(mk_cse(CSE_WR_REG, 8'h00));
      send_item(mk_cse(CSE_RD_REG, 8'h00));
      send_item(mk_cse(CSE_WR_REG, 8'hFF));
      send_item(mk_cse(CSE_RD_REG, 8'hF0));
      send_item(mk_cse(CSE_WR_MEM, 8'h00));
      send_item(mk_cse(CSE_RD_MEM, 8'h00));
      send_item(mk_cse(CSE_WR_MEM, 8'hFF));
      send_item(mk_cse(CSE_RD_MEM, 8'hF0));
      send_item(mk_cse(CSE_SET_CFG, 8'h00));
      send_item(mk_cse(CSE_SET_CFG, 8'hFF));
      send_item(mk_cse(CSE_GET_CFG));
      send_item(mk_cse(CSE_IRQ_ACK));
      send_item(mk_cse(CSE_NOP));
    endtask
  endclass : cse_corner_seq

  // ---- 9. regression mix ---------------------------------------------------------
  class cse_regression_seq extends cse_base_seq;
    `uvm_object_utils(cse_regression_seq)
    int num_iters = 3;
    function new(string name = "cse_regression_seq");
      super.new(name);
    endfunction
    task body();
      for (int i = 0; i < num_iters; i++) begin
        int pick = $urandom_range(0, 6);
        case (pick)
          0: begin cse_wr_reg_seq s = cse_wr_reg_seq::type_id::create("s"); s.start(m_sequencer, null); end
          1: begin cse_rd_seq     s = cse_rd_seq::type_id::create("s");     s.start(m_sequencer, null); end
          2: begin cse_mem_seq    s = cse_mem_seq::type_id::create("s");    s.start(m_sequencer, null); end
          3: begin cse_error_seq  s = cse_error_seq::type_id::create("s");  s.start(m_sequencer, null); end
          4: begin cse_reset_seq  s = cse_reset_seq::type_id::create("s");  s.start(m_sequencer, null); end
          5: begin cse_b2b_seq    s = cse_b2b_seq::type_id::create("s");    s.start(m_sequencer, null); end
          6: begin cse_corner_seq s = cse_corner_seq::type_id::create("s"); s.start(m_sequencer, null); end
        endcase
      end
    endtask
  endclass : cse_regression_seq

endpackage : mipi_vip_pkg

`endif // MIPI_VIP_PKG_SV
