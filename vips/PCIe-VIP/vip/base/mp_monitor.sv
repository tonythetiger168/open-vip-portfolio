// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Monitor
// Observes all protocol transactions on the interface
//============================================================================
`ifndef MP_MONITOR_SV
`define MP_MONITOR_SV
class mp_monitor extends uvm_monitor;
  `uvm_component_utils(mp_monitor)

  virtual mp_vip_if vif;
  protocol_e        protocol;

  // Analysis port for collected transactions
  uvm_analysis_port #(mp_sequence_item) analysis_port;

  // Transaction tracking
  int txn_count;
  int error_count;

  // Coverage model handle
  mp_coverage_model cov_model;

  function new(string name = "mp_monitor", uvm_component parent = null);
    super.new(name, parent);
    analysis_port = new("analysis_port", this);
    txn_count = 0;
    error_count = 0;
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual mp_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "Virtual interface not found")
    if (!uvm_config_db#(protocol_e)::get(this, "", "protocol", protocol))
      protocol = PROTO_PCIE_GEN5;
  endfunction

  task run_phase(uvm_phase phase);
    wait (vif.rst_n === 1'b1);
    `uvm_info("MONITOR", "Monitor started", UVM_MEDIUM)
    forever begin
      // sample LTSSM FSM coverage every cycle
      if (cov_model != null) cov_model.sample_link_state(vif.monitor_cb.link_state);
      collect_transaction();
    end
  endtask

  virtual task collect_transaction();
    mp_sequence_item item;
    mp_txn_descriptor txn;

    // Wait for SOP
    @(vif.monitor_cb);
    while (vif.monitor_cb.sop !== 1'b1 || vif.monitor_cb.valid !== 1'b1)
      @(vif.monitor_cb);

    item = mp_sequence_item::type_id::create("item");
    txn = item.txn;
    txn.protocol = protocol;

    // Decode protocol-specific header
    case (protocol)
      PROTO_PCIE_GEN5, PROTO_PCIE_GEN6: collect_pcie(txn);
      PROTO_CXL_20, PROTO_CXL_30:       collect_cxl(txn);
      PROTO_UCIE:                       collect_ucie(txn);
      PROTO_UALINK:                     collect_ualink(txn);
      default:                          collect_pcie(txn);
    endcase

    // Sample coverage
    if (cov_model != null)
      cov_model.sample_transaction(txn);

    // Send to analysis port
    analysis_port.write(item);
    txn_count++;

    if (txn.status == TXN_ERROR) error_count++;
  endtask

  //==========================================================================
  // PCIe Transaction Collection
  //==========================================================================
  virtual task collect_pcie(mp_txn_descriptor txn);
    logic [511:0] header;
    int data_idx = 0;

    // Capture header
    header = vif.monitor_cb.data;
    txn.requester_id = vif.monitor_cb.requester_id;
    txn.completer_id = vif.monitor_cb.completer_id;
    txn.tag          = vif.monitor_cb.tag;
    txn.tc           = vif.monitor_cb.tc;
    txn.ep           = vif.monitor_cb.ep;
    txn.td           = vif.monitor_cb.td;
    txn.attr         = vif.monitor_cb.attr;
    txn.length_dw    = vif.monitor_cb.length_dw;
    txn.length       = int'(vif.monitor_cb.length_dw) * 4;

    // Decode address from header
    txn.address = header[127:64];

    // Determine transaction type
    if (vif.monitor_cb.sop && !vif.monitor_cb.eop)
      txn.txn_type = TLP_MEM_WR;
    else if (vif.monitor_cb.sop)
      txn.txn_type = TLP_MEM_RD;

    // Collect data beats
    while (vif.monitor_cb.eop !== 1'b1) begin
      @(vif.monitor_cb);
      if (vif.monitor_cb.valid) begin
        for (int j = 0; j < (vif.DATA_WIDTH/32); j++) begin
          if (data_idx < txn.length_dw) begin
            txn.data = new[txn.data.size() + 1](txn.data);
            txn.data[data_idx] = vif.monitor_cb.data[j*32 +: 32];
            data_idx++;
          end
        end
      end
    end

    // Check for errors
    if (vif.monitor_cb.ecrc_error || vif.monitor_cb.lcrc_error ||
        vif.monitor_cb.framing_error)
      txn.status = TXN_ERROR;
    else
      txn.status = TXN_COMPLETE;

    txn.set_complete(txn.status);
  endtask

  //==========================================================================
  // CXL Transaction Collection
  //==========================================================================
  virtual task collect_cxl(mp_txn_descriptor txn);
    logic [511:0] header;

    header = vif.monitor_cb.data;
    txn.address = header[127:64];
    txn.cxl_meta = header[47:32];
    txn.requester_id = vif.monitor_cb.requester_id;
    txn.tag = vif.monitor_cb.tag;
    txn.length_dw = vif.monitor_cb.length_dw;
    txn.length = int'(vif.monitor_cb.length_dw) * 4;

    // Decode CXL type from meta field
    case (txn.cxl_meta[3:0])
      4'b0000: txn.txn_type = CXL_MEM_RD;
      4'b0001: txn.txn_type = CXL_MEM_WR;
      4'b0010: txn.txn_type = CXL_IO_RD;
      4'b0011: txn.txn_type = CXL_IO_WR;
      4'b0100: txn.txn_type = CXL_CACHE_RD;
      4'b0101: txn.txn_type = CXL_CACHE_WR;
      4'b0110: txn.txn_type = CXL_BIAS_RD;
      4'b0111: txn.txn_type = CXL_BIAS_WR;
      default: txn.txn_type = CXL_MEM_RW;
    endcase

    // Collect data
    begin
      int data_idx = 0;
      while (vif.monitor_cb.eop !== 1'b1) begin
        @(vif.monitor_cb);
        if (vif.monitor_cb.valid) begin
          for (int j = 0; j < (vif.DATA_WIDTH/32) && data_idx < txn.length_dw; j++) begin
            txn.data = new[txn.data.size() + 1](txn.data);
            txn.data[data_idx] = vif.monitor_cb.data[j*32 +: 32];
            data_idx++;
          end
        end
      end
    end

    txn.status = (vif.monitor_cb.ecrc_error) ? TXN_ERROR : TXN_COMPLETE;
    txn.set_complete(txn.status);
  endtask

  //==========================================================================
  // UCIe Transaction Collection
  //==========================================================================
  virtual task collect_ucie(mp_txn_descriptor txn);
    logic [511:0] header;

    header = vif.monitor_cb.data;
    txn.address = {48'h0, header[15:0]};
    txn.length = int'(header[31:16]);
    txn.ucie_credits = vif.monitor_cb.ucie_credits;
    txn.ucie_vc = vif.monitor_cb.ucie_vc;

    if (txn.length > 0)
      txn.txn_type = UCIE_DATA_WR;
    else
      txn.txn_type = UCIE_REG_RD;

    txn.data = new[1];
    txn.data[0] = header[63:32];

    txn.status = (vif.monitor_cb.protocol_error) ? TXN_ERROR : TXN_COMPLETE;
    txn.set_complete(txn.status);
  endtask

  //==========================================================================
  // UALink Transaction Collection
  //==========================================================================
  virtual task collect_ualink(mp_txn_descriptor txn);
    logic [511:0] header;

    header = vif.monitor_cb.data;
    txn.address = header[127:64];
    txn.length = int'(header[63:32]);
    txn.ualink_vc = vif.monitor_cb.ualink_vc;

    txn.txn_type = (vif.monitor_cb.ualink_flit_mode) ? UALINK_FLIT : UALINK_DATA;

    if (txn.length > 0) begin
      txn.data = new[1];
      txn.data[0] = header[31:0];
    end

    txn.status = (vif.monitor_cb.framing_error) ? TXN_ERROR : TXN_COMPLETE;
    txn.set_complete(txn.status);
  endtask

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("MONITOR_REPORT", $sformatf(
      "Protocol: %s | Total Collected: %0d | Errors: %0d",
      protocol.name(), txn_count, error_count), UVM_LOW)
  endfunction
endclass
`endif
