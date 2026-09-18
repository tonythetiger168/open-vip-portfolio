// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axi_driver.svh -- AXI4 master driver: 5-channel handshake (AW/W/B, AR/R),
// INCR/WRAP/FIXED bursts, WLAST generation, BRESP/RRESP capture.

`ifndef AXI_DRIVER_SVH
`define AXI_DRIVER_SVH

class axi_driver extends uvm_driver #(amba_seq_item);
  `uvm_component_utils(axi_driver)
  virtual amba_vip_if vif;
  uvm_analysis_port #(amba_seq_item) drv_ap;  // expected items for scoreboard

  function new(string name, uvm_component parent);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual amba_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "AXI virtual interface not set")
  endfunction

  task run_phase(uvm_phase phase);
    amba_seq_item item;
    // Idle all channels
    vif.drv_cb.awvalid <= 1'b0;
    vif.drv_cb.wvalid  <= 1'b0;
    vif.drv_cb.bready  <= 1'b0;
    vif.drv_cb.arvalid <= 1'b0;
    vif.drv_cb.rready  <= 1'b0;
    vif.drv_cb.awlock  <= 1'b0;
    vif.drv_cb.arlock  <= 1'b0;
    wait (vif.aresetn === 1'b1);
    forever begin
      seq_item_port.get_next_item(item);
      `uvm_info("DRV", {"drive: ", item.convert2string()}, UVM_HIGH)
      if (item.txn.write) drive_write(item);
      else                drive_read(item);
      drv_ap.write(item);           // broadcast expected transaction
      seq_item_port.item_done();
    end
  endtask

  // ---------------- write channel group ----------------
  task drive_write(amba_seq_item item);
    amba_txn t = item.txn;
    repeat (t.delay) @(vif.drv_cb);
    // ---- AW ----
    @(vif.drv_cb);
    vif.drv_cb.awaddr  <= t.addr;
    vif.drv_cb.awlen   <= t.len - 1;
    vif.drv_cb.awsize  <= t.size;
    vif.drv_cb.awburst <= t.burst;
    vif.drv_cb.awcache <= t.cache;
    vif.drv_cb.awprot  <= t.prot;
    vif.drv_cb.awvalid <= 1'b1;
    do @(vif.drv_cb); while (vif.drv_cb.awready !== 1'b1);
    vif.drv_cb.awvalid <= 1'b0;
    // ---- W ----
    for (int i = 0; i < t.len; i++) begin
      vif.drv_cb.wdata  <= t.data[i];
      vif.drv_cb.wstrb  <= 8'hFF;
      vif.drv_cb.wlast  <= (i == t.len - 1);
      vif.drv_cb.wvalid <= 1'b1;
      do @(vif.drv_cb); while (vif.drv_cb.wready !== 1'b1);
      vif.drv_cb.wvalid <= 1'b0;
      vif.drv_cb.wlast  <= 1'b0;
    end
    // ---- B ----
    vif.drv_cb.bready <= 1'b1;
    do @(vif.drv_cb); while (vif.drv_cb.bvalid !== 1'b1);
    t.resp = resp_e'(vif.drv_cb.bresp);
    vif.drv_cb.bready <= 1'b0;
  endtask

  // ---------------- read channel group ----------------
  task drive_read(amba_seq_item item);
    amba_txn t = item.txn;
    repeat (t.delay) @(vif.drv_cb);
    // ---- AR ----
    @(vif.drv_cb);
    vif.drv_cb.araddr  <= t.addr;
    vif.drv_cb.arlen   <= t.len - 1;
    vif.drv_cb.arsize  <= t.size;
    vif.drv_cb.arburst <= t.burst;
    vif.drv_cb.arvalid <= 1'b1;
    do @(vif.drv_cb); while (vif.drv_cb.arready !== 1'b1);
    vif.drv_cb.arvalid <= 1'b0;
    // ---- R ----
    vif.drv_cb.rready <= 1'b1;
    for (int i = 0; i < t.len; i++) begin
      do @(vif.drv_cb); while (vif.drv_cb.rvalid !== 1'b1);
      t.data[i] = vif.drv_cb.rdata;
      t.resp    = resp_e'(vif.drv_cb.rresp);
      if (i == t.len - 1 && vif.drv_cb.rlast !== 1'b1)
        `uvm_warning("DRV", "RLAST missing on final read beat")
    end
    vif.drv_cb.rready <= 1'b0;
  endtask
endclass
`endif
