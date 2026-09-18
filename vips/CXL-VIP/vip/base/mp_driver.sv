// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Driver
// Handles all protocol types with protocol-aware driving
//============================================================================
`ifndef MP_DRIVER_SV
`define MP_DRIVER_SV
class mp_driver extends uvm_driver #(mp_sequence_item);
  `uvm_component_utils(mp_driver)

  virtual mp_vip_if vif;
  protocol_e        protocol;
  protocol_cfg_t    cfg;

  // expected items for the end-to-end scoreboard
  uvm_analysis_port #(mp_sequence_item) drv_ap;

  // Transaction tracking
  int txn_count;
  int error_count;

  // Timing parameters (in clock cycles)
  int t_ready_latency;
  int t_recovery_time;

  function new(string name = "mp_driver", uvm_component parent = null);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
    txn_count = 0;
    error_count = 0;
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual mp_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "Virtual interface not found")
    if (!uvm_config_db#(protocol_e)::get(this, "", "protocol", protocol))
      protocol = PROTO_PCIE_GEN5;
    if (!uvm_config_db#(protocol_cfg_t)::get(this, "", "cfg", cfg))
      `uvm_warning("CONFIG", "Protocol config not found, using defaults")
  endfunction

  task run_phase(uvm_phase phase);
    // Idle the bus and wait for reset release + link training
    vif.driver_cb.valid       <= 1'b0;
    vif.driver_cb.sop         <= 1'b0;
    vif.driver_cb.eop         <= 1'b0;
    vif.driver_cb.pm_request  <= 1'b0;
    wait (vif.rst_n === 1'b1);
    wait (vif.driver_cb.link_up === 1'b1);
    forever begin
      mp_sequence_item req_item;
      seq_item_port.get_next_item(req_item);
      drive_item(req_item);
      // broadcast expected transaction to the end-to-end scoreboard
      drv_ap.write(req_item);
      seq_item_port.item_done();
    end
  endtask

  virtual task drive_item(mp_sequence_item item);
    mp_txn_descriptor txn = item.txn;

    `uvm_info("DRIVER", $sformatf("Driving: %s", txn.convert2string()), UVM_HIGH)

    // Inter-transaction delay (models idle / low-power entry windows)
    if (txn.delay_cycles > 0)
      repeat (txn.delay_cycles) @(vif.driver_cb);

    // Wait for reset
    wait (vif.rst_n === 1'b1);

    // Protocol-specific driving
    case (txn.protocol)
      PROTO_PCIE_GEN5, PROTO_PCIE_GEN6: drive_pcie(txn);
      PROTO_CXL_20, PROTO_CXL_30:       drive_cxl(txn);
      PROTO_UCIE:                       drive_ucie(txn);
      PROTO_UALINK:                     drive_ualink(txn);
      default:                          drive_pcie(txn);
    endcase

    txn_count++;
    if (txn.status == TXN_ERROR) error_count++;
  endtask

  //==========================================================================
  // PCIe Gen5/6 Driving: TLP header beat + data beats with ready backpressure
  //==========================================================================
  virtual task drive_pcie(mp_txn_descriptor txn);
    int beats;
    int data_idx = 0;

    // Calculate number of beats
    beats = (txn.length + (vif.DATA_WIDTH/8) - 1) / (vif.DATA_WIDTH/8);
    if (beats == 0) beats = 1;

    // Drive header beat
    @(vif.driver_cb);
    vif.driver_cb.sop          <= 1'b1;
    vif.driver_cb.eop          <= (beats == 1);
    vif.driver_cb.valid        <= 1'b1;
    vif.driver_cb.requester_id <= txn.requester_id;
    vif.driver_cb.completer_id <= txn.completer_id;
    vif.driver_cb.tag          <= txn.tag;
    vif.driver_cb.tc           <= txn.tc;
    vif.driver_cb.ep           <= txn.ep;
    vif.driver_cb.td           <= txn.td;
    vif.driver_cb.attr         <= txn.attr;
    vif.driver_cb.length_dw    <= txn.length_dw;
    vif.driver_cb.be           <= 8'hFF;
    vif.driver_cb.data         <= {txn.address, 32'h0, 16'h0, txn.cxl_meta};

    // Drive data beats with backpressure handling
    for (int i = 1; i < beats; i++) begin
      @(vif.driver_cb);
      // hold the current beat until the completer accepts it
      while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
      vif.driver_cb.sop   <= 1'b0;
      vif.driver_cb.valid <= 1'b1;
      vif.driver_cb.eop   <= (i == beats - 1);

      // Pack data
      begin
        logic [511:0] beat_data;
        beat_data = '0;
        for (int j = 0; j < (vif.DATA_WIDTH/32) && data_idx < txn.data.size(); j++) begin
          beat_data[j*32 +: 32] = txn.data[data_idx++];
        end
        vif.driver_cb.data <= beat_data;
      end
    end

    // End transaction
    @(vif.driver_cb);
    while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
    vif.driver_cb.valid <= 1'b0;
    vif.driver_cb.sop   <= 1'b0;
    vif.driver_cb.eop   <= 1'b0;

    txn.set_complete(TXN_COMPLETE);
  endtask

  //==========================================================================
  // CXL 2.0/3.0 Driving (CXL.cache/CXL.mem semantics on PCIe PHY)
  //==========================================================================
  virtual task drive_cxl(mp_txn_descriptor txn);
    // CXL uses PCIe physical layer with CXL-specific extensions
    @(vif.driver_cb);
    vif.driver_cb.sop          <= 1'b1;
    vif.driver_cb.valid        <= 1'b1;
    vif.driver_cb.eop          <= 1'b0;
    vif.driver_cb.requester_id <= txn.requester_id;
    vif.driver_cb.tag          <= txn.tag;
    vif.driver_cb.length_dw    <= txn.length_dw;
    vif.driver_cb.be           <= 8'hFF;
    vif.driver_cb.data         <= {txn.address, txn.cxl_meta, 16'h0};

    // Drive CXL-specific sideband (VC for CXL.mem/CXL.cache)
    vif.driver_cb.ucie_vc <= 4'b0010;  // CXL VC

    // Similar data driving as PCIe
    begin
      int beats;
      beats = (txn.length + (vif.DATA_WIDTH/8) - 1) / (vif.DATA_WIDTH/8);
      for (int i = 1; i < beats; i++) begin
        @(vif.driver_cb);
        while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
        vif.driver_cb.sop <= 1'b0;
        if (i == beats - 1) vif.driver_cb.eop <= 1'b1;
        begin
          logic [511:0] beat_data;
          beat_data = '0;
          for (int j = 0; j < (vif.DATA_WIDTH/32); j++) begin
            int idx;
            idx = (i-1)*(vif.DATA_WIDTH/32) + j;
            if (idx < txn.data.size())
              beat_data[j*32 +: 32] = txn.data[idx];
          end
          vif.driver_cb.data <= beat_data;
        end
      end
    end

    @(vif.driver_cb);
    while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
    vif.driver_cb.valid <= 1'b0;
    vif.driver_cb.eop   <= 1'b0;
    txn.set_complete(TXN_COMPLETE);
  endtask

  //==========================================================================
  // UCIe Driving
  //==========================================================================
  virtual task drive_ucie(mp_txn_descriptor txn);
    // UCIe uses a different framing - register/data access
    @(vif.driver_cb);
    vif.driver_cb.sop          <= 1'b1;
    vif.driver_cb.valid        <= 1'b1;
    vif.driver_cb.ucie_credits <= txn.ucie_credits;
    vif.driver_cb.ucie_vc      <= txn.ucie_vc;
    vif.driver_cb.data         <= {txn.address[15:0], txn.length[15:0], 16'h0, txn.data[0]};

    // UCIe typically has shorter bursts
    @(vif.driver_cb);
    while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
    vif.driver_cb.sop   <= 1'b0;
    vif.driver_cb.eop   <= 1'b1;
    vif.driver_cb.valid <= 1'b0;

    txn.set_complete(TXN_COMPLETE);
  endtask

  //==========================================================================
  // UALink Driving
  //==========================================================================
  virtual task drive_ualink(mp_txn_descriptor txn);
    // UALink uses flit-based transport
    @(vif.driver_cb);
    vif.driver_cb.sop              <= 1'b1;
    vif.driver_cb.valid            <= 1'b1;
    vif.driver_cb.ualink_vc        <= txn.ualink_vc;
    vif.driver_cb.ualink_flit_mode <= 1'b1;
    vif.driver_cb.data             <= {txn.address, txn.length[31:0], txn.data[0]};

    // Flit boundary
    @(vif.driver_cb);
    while (vif.driver_cb.ready !== 1'b1) @(vif.driver_cb);
    vif.driver_cb.sop   <= 1'b0;
    vif.driver_cb.eop   <= 1'b1;
    vif.driver_cb.valid <= 1'b0;

    txn.set_complete(TXN_COMPLETE);
  endtask

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("DRIVER_REPORT", $sformatf(
      "Protocol: %s | Total Driven: %0d | Errors: %0d",
      protocol.name(), txn_count, error_count), UVM_LOW)
  endfunction
endclass
`endif
