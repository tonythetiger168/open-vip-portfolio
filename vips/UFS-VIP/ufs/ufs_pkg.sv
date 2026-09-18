// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ufs_pkg.sv -- UFS (Universal Flash Storage) UVM VIP package
// UPIU command/response model over a byte-serial UTP transfer interface:
//   host->device : 10-byte UPIU header {type,lun,tag,opcode,lba[4],len[2]} + optional write data
//   device->host : READY_XFER (RTT) burst, DATA_IN burst, 3-byte response trailer {type,tag,status}
`ifndef UFS_PKG_SV
`define UFS_PKG_SV
package ufs_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `uvm_analysis_imp_decl(_ufs_exp)
  `uvm_analysis_imp_decl(_ufs_obs)

  // SCSI opcodes carried inside the UFS COMMAND UPIU
  localparam bit [7:0] SCSI_TUR       = 8'h00; // test unit ready
  localparam bit [7:0] SCSI_REQ_SENSE = 8'h03; // request sense
  localparam bit [7:0] SCSI_INQUIRY   = 8'h12; // inquiry
  localparam bit [7:0] SCSI_READ10    = 8'h28; // read(10)
  localparam bit [7:0] SCSI_WRITE10   = 8'h2A; // write(10)
  // Device model geometry (must match ufs_device_dut in tb_top.sv)
  localparam int UFS_BLOCK_SIZE  = 512;
  localparam int UFS_CAP_BLOCKS  = 2048; // 1 MiB device
  // Response status bytes
  localparam bit [7:0] UFS_ST_GOOD   = 8'h00;
  localparam bit [7:0] UFS_ST_CHECK  = 8'h02; // check condition
  localparam bit [7:0] UFS_ST_BUSY   = 8'h08;
  localparam bit [7:0] UFS_ST_ABORT  = 8'h0B;

  //============================================================================
  // UFS Sequence Item (one UPIU exchange)
  //============================================================================
  class ufs_seq_item extends uvm_sequence_item;
    `uvm_object_utils(ufs_seq_item)
    typedef enum bit [7:0] {
      NOP_OUT     = 8'h00, COMMAND     = 8'h01, DATA_OUT    = 8'h02,
      TASK_MGT    = 8'h04, QUERY_REQ   = 8'h16, NOP_IN      = 8'h20,
      RESPONSE    = 8'h21, DATA_IN     = 8'h22, TASK_MGT_RSP= 8'h24,
      QUERY_RSP   = 8'h36, READY_XFER  = 8'h31, REJECT      = 8'h3F
    } upiu_type_e;
    rand upiu_type_e upiu_type;
    rand bit [7:0]  opcode;        // SCSI opcode (COMMAND UPIU) / TM function (TASK_MGT)
    rand bit [7:0]  task_tag;
    rand bit [15:0] data_length;   // transfer length in bytes
    rand bit [31:0] lba;           // Logical block address
    rand bit [7:0]  lun;           // Logical unit number
    rand bit [7:0]  data[];        // write payload (host->device)
    rand bit [2:0]  flags;         // bit0: read, bit1: write, bit2: error-injection request
    bit [1:0]       response;      // 00=GOOD, 01=CHECK_CONDITION, etc.
    bit [7:0]       rdata[];       // read payload (device->host)
    bit [7:0]       status;        // response status byte
    rand int unsigned delay;       // inter-transfer idle cycles
    // Constraints
    constraint c_upiu_dist { upiu_type dist {COMMAND := 30, QUERY_REQ := 10, TASK_MGT := 5, NOP_OUT := 5}; }
    constraint c_data_len { data_length inside {512, 1024, 2048, 4096, 8192}; }
    constraint c_data_size { data.size() == data_length; }
    constraint c_lun { lun inside {[0:7]}; }
    constraint c_opcode { opcode inside {SCSI_TUR, SCSI_REQ_SENSE, SCSI_INQUIRY, SCSI_READ10, SCSI_WRITE10}; }
    constraint c_lba_fit { lba <= UFS_CAP_BLOCKS - (data_length / UFS_BLOCK_SIZE); }
    constraint c_delay { delay inside {[0:20]}; }
    function new(string name = "ufs_seq_item"); super.new(name); endfunction
    function bit is_host_upiu();
      return upiu_type inside {NOP_OUT, COMMAND, TASK_MGT, QUERY_REQ};
    endfunction
    function bit is_write10();
      return (upiu_type == COMMAND) && (opcode == SCSI_WRITE10);
    endfunction
    function bit is_read10();
      return (upiu_type == COMMAND) && (opcode == SCSI_READ10);
    endfunction
    virtual function string convert2string();
      return $sformatf("UFS %s: op=0x%0h tag=0x%0h lba=0x%0h len=%0d lun=%0d status=0x%0h",
                       upiu_type.name(), opcode, task_tag, lba, data_length, lun, status);
    endfunction
    virtual function bit do_compare(uvm_object rhs, uvm_comparer comparer);
      ufs_seq_item o;
      if (!$cast(o, rhs)) return 0;
      if (upiu_type != o.upiu_type) return 0;
      if (opcode != o.opcode || task_tag != o.task_tag || lun != o.lun) return 0;
      if (lba != o.lba || data_length != o.data_length) return 0;
      if (data.size() != o.data.size()) return 0;
      foreach (data[i]) if (data[i] != o.data[i]) return 0;
      return 1;
    endfunction
  endclass : ufs_seq_item

  //============================================================================
  // UFS Configuration
  //============================================================================
  class ufs_cfg extends uvm_object;
    `uvm_object_utils(ufs_cfg)
    uvm_active_passive_enum is_active = UVM_ACTIVE;
    bit has_coverage = 1;
    int tActivate = 10;
    int tRead = 50;
    int tWrite = 100;
    int tResponse = 20;
    int rsp_timeout = 100000;   // max cycles to wait for a device response
    function new(string name = "ufs_cfg"); super.new(name); endfunction
  endclass : ufs_cfg

  //============================================================================
  // UFS Sequencer/Driver/Monitor/Agent
  //============================================================================
  class ufs_sequencer extends uvm_sequencer #(ufs_seq_item);
    `uvm_component_utils(ufs_sequencer)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
  endclass : ufs_sequencer

  class ufs_driver extends uvm_driver #(ufs_seq_item);
    `uvm_component_utils(ufs_driver)
    virtual ufs_if vif;
    ufs_cfg cfg;
    uvm_analysis_port #(ufs_seq_item) drv_ap; // expected transactions (e2e scoreboard)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual ufs_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "UFS virtual interface not found")
      if (!uvm_config_db#(ufs_cfg)::get(this, "", "cfg", cfg))
        cfg = ufs_cfg::type_id::create("cfg");
      drv_ap = new("drv_ap", this);
    endfunction

    task run_phase(uvm_phase phase);
      ufs_seq_item req;
      vif.drv_cb.data_out_valid <= 1'b0;
      vif.drv_cb.req_valid      <= 1'b0;
      vif.drv_cb.doorbell       <= 1'b0;
      vif.drv_cb.valid          <= 1'b0;
      wait (vif.rst_n === 1'b1);
      forever begin
        seq_item_port.get_next_item(req);
        `uvm_info(get_type_name(), $sformatf("Driving: %s", req.convert2string()), UVM_MEDIUM)
        repeat (req.delay) @(vif.drv_cb);
        drive_upiu(req);
        drv_ap.write(req);
        seq_item_port.item_done();
      end
    endtask

    // Drive one byte of the host->device UPIU stream
    task automatic send_byte(bit [7:0] b, bit hdr_phase, bit ring);
      @(vif.drv_cb);
      vif.drv_cb.data_out       <= b;
      vif.drv_cb.data_out_valid <= 1'b1;
      vif.drv_cb.valid          <= 1'b1;
      vif.drv_cb.req_valid      <= hdr_phase;
      vif.drv_cb.doorbell       <= ring;
    endtask

    // Full UPIU transfer: doorbell + header + optional write data + response collection
    task automatic drive_upiu(ufs_seq_item req);
      bit [7:0] cat;
      // UTP doorbell: register the new UPIU in the command queue
      case (req.upiu_type)
        ufs_seq_item::COMMAND:   cat = 4'h1;
        ufs_seq_item::TASK_MGT:  cat = 4'h4;
        ufs_seq_item::QUERY_REQ: cat = 4'h6;
        default:                 cat = 4'h0;
      endcase
      vif.drv_cb.task_tag    <= req.task_tag;
      vif.drv_cb.data_length <= req.data_length;
      vif.drv_cb.lun_id      <= req.lun;
      vif.drv_cb.req_data    <= req.opcode;
      vif.drv_cb.cmd_type    <= cat;
      // 10-byte UPIU header (first byte rings the doorbell)
      send_byte(req.upiu_type, 1'b1, 1'b1);
      send_byte(req.lun, 1'b1, 1'b0);
      send_byte(req.task_tag, 1'b1, 1'b0);
      send_byte(req.opcode, 1'b1, 1'b0);
      send_byte(req.lba[31:24], 1'b1, 1'b0);
      send_byte(req.lba[23:16], 1'b1, 1'b0);
      send_byte(req.lba[15:8],  1'b1, 1'b0);
      send_byte(req.lba[7:0],   1'b1, 1'b0);
      send_byte(req.data_length[15:8], 1'b1, 1'b0);
      send_byte(req.data_length[7:0],  1'b1, 1'b0);
      // Header complete: close the host burst while the device decodes / issues RTT
      @(vif.drv_cb);
      vif.drv_cb.data_out_valid <= 1'b0;
      vif.drv_cb.req_valid      <= 1'b0;
      vif.drv_cb.doorbell       <= 1'b0;
      vif.drv_cb.valid          <= 1'b0;
      // Write data phase: wait for READY_XFER (RTT) unless the device fast-paths an error
      if (req.is_write10()) begin
        bit got_rtt = 0;
        int guard = 0;
        while (!got_rtt && guard < cfg.rsp_timeout) begin
          @(vif.drv_cb);
          if (vif.drv_cb.transfer_ready === 1'b1) got_rtt = 1;
          if (vif.drv_cb.resp_valid === 1'b1) break; // device rejected: no data phase
          guard++;
        end
        if (!got_rtt && guard >= cfg.rsp_timeout)
          `uvm_error(get_type_name(), "Timeout waiting for READY_XFER")
        if (got_rtt) begin
          foreach (req.data[i]) send_byte(req.data[i], 1'b0, 1'b0);
          @(vif.drv_cb);
          vif.drv_cb.data_out_valid <= 1'b0;
          vif.drv_cb.valid          <= 1'b0;
        end else begin
          req.data = new[0]; // nothing was actually transferred (error path)
        end
      end else begin
        req.data = new[0]; // no host->device payload for non-write UPIUs
      end
      // Collect the device response (and read data for READ_10)
      collect_response(req);
    endtask

    // Watch device->host bursts: skip RTT, append data bursts to rdata,
    // terminate on a 3-byte response trailer {type, tag, status}
    task automatic collect_response(ufs_seq_item req);
      bit [7:0] burst[$];
      bit [7:0] rd_q[$];
      bit in_burst = 0;
      int guard = 0;
      req.status = UFS_ST_GOOD;
      req.response = 2'b00;
      while (guard < cfg.rsp_timeout) begin
        @(vif.drv_cb);
        guard++;
        if (vif.drv_cb.data_in_valid === 1'b1) begin
          burst.push_back(vif.drv_cb.data_in);
          in_burst = 1;
        end else if (in_burst) begin
          in_burst = 0;
          if (burst.size() == 1 && burst[0] == 8'h31) begin
            // READY_XFER: already handled in the write data phase
          end else if (burst.size() == 3 &&
                       burst[0] inside {8'h20, 8'h21, 8'h24, 8'h36, 8'h3F}) begin
            req.status   = burst[2];
            req.response = burst[2][1:0];
            burst.delete();
            break;
          end else begin
            foreach (burst[i]) rd_q.push_back(burst[i]);
          end
          burst.delete();
        end
      end
      if (guard >= cfg.rsp_timeout)
        `uvm_error(get_type_name(), "Timeout waiting for UFS response UPIU")
      req.rdata = new[rd_q.size()];
      foreach (rd_q[i]) req.rdata[i] = rd_q[i];
    endtask
  endclass : ufs_driver

  class ufs_monitor extends uvm_monitor;
    `uvm_component_utils(ufs_monitor)
    virtual ufs_if vif;
    uvm_analysis_port #(ufs_seq_item) item_collected_port;
    int unsigned txn_count = 0;
    function new(string name, uvm_component parent);
      super.new(name, parent);
      item_collected_port = new("item_collected_port", this);
    endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual ufs_if)::get(this, "", "vif", vif))
        `uvm_fatal(get_type_name(), "UFS virtual interface not found")
    endfunction
    task run_phase(uvm_phase phase);
      fork
        collect_cmd();
        collect_rsp();
      join
    endtask

    // Pending WRITE_10 header waiting for its data-phase burst
    ufs_seq_item pending_wr = null;

    // Decode host->device transfers (UPIU command stream) from the waveform
    task automatic collect_cmd();
      bit [7:0] burst[$];
      bit in_burst = 0;
      forever begin
        @(vif.mon_cb);
        if (!vif.rst_n) begin burst.delete(); in_burst = 0; pending_wr = null; continue; end
        if (vif.mon_cb.data_out_valid === 1'b1) begin
          burst.push_back(vif.mon_cb.data_out);
          in_burst = 1;
        end else if (in_burst) begin
          in_burst = 0;
          decode_cmd(burst);
          burst.delete();
        end
      end
    endtask

    function automatic void decode_cmd(const ref bit [7:0] burst[$]);
      ufs_seq_item item;
      // A data-phase burst completes a pending WRITE_10 command item
      if (pending_wr != null && burst.size() < 10) begin
        pending_wr.data = new[burst.size()];
        foreach (burst[i]) pending_wr.data[i] = burst[i];
        item_collected_port.write(pending_wr);
        txn_count++;
        `uvm_info(get_type_name(), $sformatf("Monitored UPIU: %s", pending_wr.convert2string()), UVM_HIGH)
        pending_wr = null;
        return;
      end
      if (pending_wr != null) begin
        // error path: write was rejected (no data phase) -> flush without payload
        item_collected_port.write(pending_wr);
        txn_count++;
        pending_wr = null;
      end
      if (burst.size() < 10) begin
        `uvm_warning(get_type_name(), $sformatf("Short host burst (%0d bytes) ignored", burst.size()))
        return;
      end
      item = ufs_seq_item::type_id::create("cmd_item");
      item.upiu_type   = ufs_seq_item::upiu_type_e'(burst[0]);
      item.lun         = burst[1];
      item.task_tag    = burst[2];
      item.opcode      = burst[3];
      item.lba         = {burst[4], burst[5], burst[6], burst[7]};
      item.data_length = {burst[8], burst[9]};
      item.data = new[(burst.size() > 10) ? burst.size() - 10 : 0];
      for (int i = 10; i < burst.size(); i++) item.data[i-10] = burst[i];
      if (burst.size() == 10 && item.is_write10()) begin
        pending_wr = item; // wait for the write data-phase burst
        return;
      end
      item_collected_port.write(item);
      txn_count++;
      `uvm_info(get_type_name(), $sformatf("Monitored UPIU: %s", item.convert2string()), UVM_HIGH)
    endfunction

    // Decode device->host bursts: READY_XFER / DATA_IN / response trailer
    task automatic collect_rsp();
      bit [7:0] burst[$];
      bit in_burst = 0;
      forever begin
        @(vif.mon_cb);
        if (!vif.rst_n) begin burst.delete(); in_burst = 0; continue; end
        if (vif.mon_cb.data_in_valid === 1'b1) begin
          burst.push_back(vif.mon_cb.data_in);
          in_burst = 1;
        end else if (in_burst) begin
          in_burst = 0;
          decode_rsp(burst);
          burst.delete();
        end
      end
    endtask

    function automatic void decode_rsp(const ref bit [7:0] burst[$]);
      ufs_seq_item item;
      item = ufs_seq_item::type_id::create("rsp_item");
      if (burst.size() == 1 && burst[0] == 8'h31) begin
        item.upiu_type = ufs_seq_item::READY_XFER;
      end else if (burst.size() == 3 &&
                   burst[0] inside {8'h20, 8'h21, 8'h24, 8'h36, 8'h3F}) begin
        item.upiu_type = ufs_seq_item::upiu_type_e'(burst[0]);
        item.task_tag  = burst[1];
        item.status    = burst[2];
        item.response  = burst[2][1:0];
        // rejected WRITE_10: flush the pending command item (no data phase occurred)
        if (pending_wr != null && burst[2] != UFS_ST_GOOD) begin
          item_collected_port.write(pending_wr);
          txn_count++;
          pending_wr = null;
        end
      end else begin
        item.upiu_type   = ufs_seq_item::DATA_IN;
        item.data_length = burst.size();
        item.rdata = new[burst.size()];
        foreach (burst[i]) item.rdata[i] = burst[i];
      end
      item_collected_port.write(item);
      txn_count++;
    endfunction
  endclass : ufs_monitor

  class ufs_agent extends uvm_agent;
    `uvm_component_utils(ufs_agent)
    ufs_sequencer sqr;
    ufs_driver    drv;
    ufs_monitor   mon;
    ufs_cfg       cfg;
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(ufs_cfg)::get(this, "", "cfg", cfg))
        cfg = ufs_cfg::type_id::create("cfg");
      uvm_config_db#(ufs_cfg)::set(this, "*", "cfg", cfg);
      mon = ufs_monitor::type_id::create("mon", this);
      if (cfg.is_active == UVM_ACTIVE) begin
        sqr = ufs_sequencer::type_id::create("sqr", this);
        drv = ufs_driver::type_id::create("drv", this);
      end
    endfunction
    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (cfg.is_active == UVM_ACTIVE)
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction
  endclass : ufs_agent

  //============================================================================
  // UFS Sequences
  //============================================================================
  class ufs_base_seq extends uvm_sequence #(ufs_seq_item);
    `uvm_object_utils(ufs_base_seq)
    function new(string name = "ufs_base_seq"); super.new(name); endfunction
    task automatic send(ufs_seq_item item);
      start_item(item);
      finish_item(item);
    endtask
    task automatic send_cmd(bit [7:0] op, bit [31:0] lba_, bit [15:0] len_, bit [7:0] lun_);
      ufs_seq_item item = ufs_seq_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with {
        upiu_type == ufs_seq_item::COMMAND; opcode == op;
        lba == lba_; data_length == len_; lun == lun_;
      }) `uvm_error(get_type_name(), "Rand failed");
      finish_item(item);
    endtask
  endclass : ufs_base_seq

  // Random read/write mix (normal traffic)
  class ufs_rw_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_rw_seq)
    rand int num_trans = 20;
    function new(string name = "ufs_rw_seq"); super.new(name); endfunction
    task body();
      ufs_seq_item item;
      repeat (num_trans) begin
        item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND;
          opcode inside {SCSI_READ10, SCSI_WRITE10};
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_rw_seq

  // Directed: normal READ(10) block reads
  class ufs_read_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_read_seq)
    rand int num_trans = 8;
    function new(string name = "ufs_read_seq"); super.new(name); endfunction
    task body();
      repeat (num_trans) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND; opcode == SCSI_READ10;
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_read_seq

  // Directed: normal WRITE(10) block writes
  class ufs_write_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_write_seq)
    rand int num_trans = 8;
    function new(string name = "ufs_write_seq"); super.new(name); endfunction
    task body();
      repeat (num_trans) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND; opcode == SCSI_WRITE10;
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_write_seq

  // Directed: QUERY_REQ descriptor accesses + INQUIRY / TEST UNIT READY
  class ufs_query_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_query_seq)
    rand int num_trans = 8;
    function new(string name = "ufs_query_seq"); super.new(name); endfunction
    task body();
      repeat (num_trans) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::QUERY_REQ;
          opcode inside {SCSI_INQUIRY, SCSI_TUR, SCSI_REQ_SENSE};
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_query_seq

  // Directed error: out-of-capacity LBA and reserved opcodes -> CHECK CONDITION
  class ufs_error_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_error_seq)
    rand int num_trans = 8;
    function new(string name = "ufs_error_seq"); super.new(name); endfunction
    task body();
      // LBA beyond device capacity
      repeat (num_trans) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND;
          opcode inside {SCSI_READ10, SCSI_WRITE10};
          lba inside {[UFS_CAP_BLOCKS : UFS_CAP_BLOCKS + 100]};
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
      // Reserved SCSI opcode
      begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND; opcode == 8'h7F;
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_error_seq

  // Directed reset: UFS task-management functions (abort task set / logical unit reset)
  class ufs_reset_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_reset_seq)
    function new(string name = "ufs_reset_seq"); super.new(name); endfunction
    task body();
      bit [7:0] tmf[4] = '{8'h01, 8'h02, 8'h04, 8'h08}; // abort task / abort task set / LU reset / clear task set
      foreach (tmf[i]) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::TASK_MGT; opcode == tmf[i];
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
      // traffic after task management to prove the link recovered
      send_cmd(SCSI_READ10, 32'd0, 16'd512, 8'd0);
    endtask
  endclass : ufs_reset_seq

  // Back-to-back: zero idle cycles between read/write transfers
  class ufs_b2b_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_b2b_seq)
    rand int num_trans = 16;
    function new(string name = "ufs_b2b_seq"); super.new(name); endfunction
    task body();
      repeat (num_trans) begin
        ufs_seq_item item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
          upiu_type == ufs_seq_item::COMMAND;
          opcode inside {SCSI_READ10, SCSI_WRITE10};
          delay == 0;
        }) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_b2b_seq

  // Stress: heavy randomized traffic across all LUNs and transfer sizes
  class ufs_stress_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_stress_seq)
    rand int num_trans = 64;
    function new(string name = "ufs_stress_seq"); super.new(name); endfunction
    task body();
      ufs_seq_item item;
      repeat (num_trans) begin
        item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize()) `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_stress_seq

  // Corner: LBA 0 / last block, min & max transfer sizes, edge LUNs
  class ufs_corner_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_corner_seq)
    function new(string name = "ufs_corner_seq"); super.new(name); endfunction
    task body();
      send_cmd(SCSI_WRITE10, 32'd0,                          16'd512,  8'd0); // first block, min size
      send_cmd(SCSI_READ10,  32'd0,                          16'd512,  8'd0);
      send_cmd(SCSI_WRITE10, UFS_CAP_BLOCKS-16,              16'd8192, 8'd7); // last blocks, max size
      send_cmd(SCSI_READ10,  UFS_CAP_BLOCKS-16,              16'd8192, 8'd7);
      send_cmd(SCSI_READ10,  UFS_CAP_BLOCKS-1,               16'd512,  8'd3); // very last block
      send_cmd(SCSI_WRITE10, 32'd1,                          16'd1024, 8'd1); // unaligned block
      send_cmd(SCSI_READ10,  32'd1,                          16'd1024, 8'd1);
    endtask
  endclass : ufs_corner_seq

  // Coverage: every UPIU transaction type (preserved API)
  class ufs_cov_upiu_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_cov_upiu_seq)
    function new(string name = "ufs_cov_upiu_seq"); super.new(name); endfunction
    task body();
      ufs_seq_item item;
      ufs_seq_item::upiu_type_e types[12] = '{
        ufs_seq_item::NOP_OUT, ufs_seq_item::COMMAND, ufs_seq_item::DATA_OUT,
        ufs_seq_item::TASK_MGT, ufs_seq_item::QUERY_REQ, ufs_seq_item::NOP_IN,
        ufs_seq_item::RESPONSE, ufs_seq_item::DATA_IN, ufs_seq_item::TASK_MGT_RSP,
        ufs_seq_item::QUERY_RSP, ufs_seq_item::READY_XFER, ufs_seq_item::REJECT};
      foreach (types[i]) begin
        item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with { upiu_type == types[i]; })
          `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_cov_upiu_seq

  // Coverage: COMMAND to every LUN (preserved API)
  class ufs_cov_lun_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_cov_lun_seq)
    function new(string name = "ufs_cov_lun_seq"); super.new(name); endfunction
    task body();
      ufs_seq_item item;
      for (int l = 0; l < 8; l++) begin
        item = ufs_seq_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with { upiu_type == ufs_seq_item::COMMAND; lun == l; })
          `uvm_error(get_type_name(), "Rand failed");
        finish_item(item);
      end
    endtask
  endclass : ufs_cov_lun_seq

  // Regression mix: run every directed sequence in order on one sequencer
  class ufs_regression_mix_seq extends ufs_base_seq;
    `uvm_object_utils(ufs_regression_mix_seq)
    function new(string name = "ufs_regression_mix_seq"); super.new(name); endfunction
    task body();
      ufs_query_seq  q  = ufs_query_seq::type_id::create("q");
      ufs_read_seq   r  = ufs_read_seq::type_id::create("r");
      ufs_write_seq  w  = ufs_write_seq::type_id::create("w");
      ufs_error_seq  e  = ufs_error_seq::type_id::create("e");
      ufs_reset_seq  rs = ufs_reset_seq::type_id::create("rs");
      ufs_b2b_seq    b  = ufs_b2b_seq::type_id::create("b");
      ufs_corner_seq c  = ufs_corner_seq::type_id::create("c");
      ufs_stress_seq s  = ufs_stress_seq::type_id::create("s");
      `uvm_info(get_type_name(), "=== UFS regression mix: query/read/write/error/reset/b2b/corner/stress ===", UVM_LOW)
      q.num_trans = 4;  q.start(m_sequencer);
      r.num_trans = 4;  r.start(m_sequencer);
      w.num_trans = 4;  w.start(m_sequencer);
      e.num_trans = 4;  e.start(m_sequencer);
      rs.start(m_sequencer);
      b.num_trans = 8;  b.start(m_sequencer);
      c.start(m_sequencer);
      s.num_trans = 16; s.start(m_sequencer);
    endtask
  endclass : ufs_regression_mix_seq
endpackage : ufs_pkg
`endif
