// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axi_monitor.svh -- AXI4 monitor: tracks the 5 handshake channels and
// reconstructs write/read burst transactions, published via analysis port.

`ifndef AXI_MONITOR_SVH
`define AXI_MONITOR_SVH

class axi_monitor extends uvm_monitor;
  `uvm_component_utils(axi_monitor)
  virtual amba_vip_if vif;
  uvm_analysis_port #(amba_seq_item) ap;
  int unsigned txn_count = 0;

  // write burst tracking
  protected amba_seq_item wr_item;
  protected int unsigned  wr_beat;
  // read burst tracking
  protected amba_seq_item rd_item;
  protected int unsigned  rd_beat;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual amba_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "AXI virtual interface not set")
  endfunction

  task run_phase(uvm_phase phase);
    wait (vif.aresetn === 1'b1);
    forever begin
      @(vif.mon_cb);

      // ---- AW handshake: open a write burst ----
      if (vif.mon_cb.awvalid && vif.mon_cb.awready) begin
        wr_item = amba_seq_item::type_id::create("wr_item");
        wr_item.txn.protocol = AXI4;
        wr_item.txn.write = 1'b1;
        wr_item.txn.addr  = vif.mon_cb.awaddr;
        wr_item.txn.len   = int'(vif.mon_cb.awlen) + 1;
        wr_item.txn.size  = axsize_e'(vif.mon_cb.awsize);
        wr_item.txn.burst = axburst_e'(vif.mon_cb.awburst);
        wr_item.txn.cache = vif.mon_cb.awcache;
        wr_item.txn.prot  = vif.mon_cb.awprot;
        wr_item.txn.resp  = RESP_OKAY;
        wr_item.txn.data  = new[wr_item.txn.len];
        wr_beat = 0;
      end

      // ---- W handshake: collect beats ----
      if (vif.mon_cb.wvalid && vif.mon_cb.wready && wr_item != null) begin
        wr_item.txn.data[wr_beat] = vif.mon_cb.wdata;
        wr_beat++;
      end

      // ---- B handshake: close write burst ----
      if (vif.mon_cb.bvalid && vif.mon_cb.bready && wr_item != null) begin
        wr_item.txn.resp = resp_e'(vif.mon_cb.bresp);
        wr_item.txn.len  = wr_beat;
        wr_item.txn.data = new[wr_beat](wr_item.txn.data);
        txn_count++;
        `uvm_info("MON", {"mon: ", wr_item.convert2string()}, UVM_HIGH)
        ap.write(wr_item);
        wr_item = null;
      end

      // ---- AR handshake: open a read burst ----
      if (vif.mon_cb.arvalid && vif.mon_cb.arready) begin
        rd_item = amba_seq_item::type_id::create("rd_item");
        rd_item.txn.protocol = AXI4;
        rd_item.txn.write = 1'b0;
        rd_item.txn.addr  = vif.mon_cb.araddr;
        rd_item.txn.len   = int'(vif.mon_cb.arlen) + 1;
        rd_item.txn.size  = axsize_e'(vif.mon_cb.arsize);
        rd_item.txn.burst = axburst_e'(vif.mon_cb.arburst);
        rd_item.txn.resp  = RESP_OKAY;
        rd_item.txn.data  = new[rd_item.txn.len];
        rd_beat = 0;
      end

      // ---- R handshake: collect beats, close on RLAST ----
      if (vif.mon_cb.rvalid && vif.mon_cb.rready && rd_item != null) begin
        rd_item.txn.data[rd_beat] = vif.mon_cb.rdata;
        rd_item.txn.resp = resp_e'(vif.mon_cb.rresp);
        rd_beat++;
        if (vif.mon_cb.rlast) begin
          rd_item.txn.len  = rd_beat;
          rd_item.txn.data = new[rd_beat](rd_item.txn.data);
          txn_count++;
          `uvm_info("MON", {"mon: ", rd_item.convert2string()}, UVM_HIGH)
          ap.write(rd_item);
          rd_item = null;
        end
      end
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("MON", $sformatf("AXI monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
`endif
