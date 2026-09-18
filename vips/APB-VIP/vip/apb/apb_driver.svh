// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_driver.svh -- APB4 master driver: SETUP -> ACCESS state progression,
// PREADY wait-state handling, PSLVERR capture, PSTRB byte enables.

`ifndef APB_DRIVER_SVH
`define APB_DRIVER_SVH

class apb_driver extends uvm_driver #(amba_seq_item);
  `uvm_component_utils(apb_driver)
  virtual amba_vip_if vif;
  uvm_analysis_port #(amba_seq_item) drv_ap;  // expected items for scoreboard

  function new(string name, uvm_component parent);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual amba_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "APB virtual interface not set")
  endfunction

  task run_phase(uvm_phase phase);
    amba_seq_item item;
    vif.drv_cb.psel    <= 1'b0;
    vif.drv_cb.penable <= 1'b0;
    vif.drv_cb.paddr   <= '0;
    vif.drv_cb.pwrite  <= 1'b0;
    vif.drv_cb.pwdata  <= '0;
    vif.drv_cb.pstrb   <= 4'h0;
    vif.drv_cb.pprot   <= 3'b000;
    wait (vif.aresetn === 1'b1);
    forever begin
      seq_item_port.get_next_item(item);
      `uvm_info("DRV", {"drive: ", item.convert2string()}, UVM_HIGH)
      drive_xfer(item);
      drv_ap.write(item);           // broadcast expected transaction
      seq_item_port.item_done();
    end
  endtask

  // One APB transfer per data word (APB is single-beat); words of a burst
  // are issued back-to-back (PSEL stays high between SETUP phases).
  task drive_xfer(amba_seq_item item);
    amba_txn t = item.txn;
    repeat (t.delay) @(vif.drv_cb);
    t.resp = RESP_OKAY;
    for (int i = 0; i < t.len; i++) begin
      // ---- SETUP phase ----
      @(vif.drv_cb);
      vif.drv_cb.psel    <= 1'b1;
      vif.drv_cb.penable <= 1'b0;
      vif.drv_cb.paddr   <= t.addr + i * 4;
      vif.drv_cb.pwrite  <= t.write;
      vif.drv_cb.pprot   <= t.prot;
      vif.drv_cb.pstrb   <= t.write ? 4'hF : 4'h0;
      if (t.write) vif.drv_cb.pwdata <= t.data[i][31:0];
      // ---- ACCESS phase ----
      @(vif.drv_cb);
      vif.drv_cb.penable <= 1'b1;
      // wait for PREADY (wait states)
      do @(vif.drv_cb); while (vif.drv_cb.pready !== 1'b1);
      if (vif.drv_cb.pslverr === 1'b1) t.resp = RESP_SLVERR;
      if (!t.write) t.data[i] = {32'h0, vif.drv_cb.prdata};
      vif.drv_cb.penable <= 1'b0;    // SETUP of next word follows immediately
    end
    // ---- IDLE at burst end ----
    vif.drv_cb.psel <= 1'b0;
  endtask
endclass
`endif
