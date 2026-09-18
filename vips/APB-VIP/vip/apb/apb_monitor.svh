// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_monitor.svh -- APB4 monitor: decodes SETUP/ACCESS transfers from the
// bus (completes on PSEL&PENABLE&PREADY) and publishes transactions.

`ifndef APB_MONITOR_SVH
`define APB_MONITOR_SVH

class apb_monitor extends uvm_monitor;
  `uvm_component_utils(apb_monitor)
  virtual amba_vip_if vif;
  uvm_analysis_port #(amba_seq_item) ap;
  int unsigned txn_count = 0;

  // Re-assemble consecutive same-direction transfers into one burst item
  protected amba_seq_item open_item;
  protected int unsigned beat_cnt;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual amba_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "APB virtual interface not set")
  endfunction

  function automatic void flush();
    if (open_item != null) begin
      open_item.txn.len = beat_cnt;
      open_item.txn.data = new[beat_cnt](open_item.txn.data);
      txn_count++;
      `uvm_info("MON", {"mon: ", open_item.convert2string()}, UVM_HIGH)
      ap.write(open_item);
      open_item = null;
      beat_cnt = 0;
    end
  endfunction

  task run_phase(uvm_phase phase);
    wait (vif.aresetn === 1'b1);
    beat_cnt = 0;
    forever begin
      @(vif.mon_cb);
      // Transfer completes on PSEL & PENABLE & PREADY
      if (vif.mon_cb.psel && vif.mon_cb.penable && vif.mon_cb.pready) begin
        bit wr = vif.mon_cb.pwrite;
        bit [31:0] a = vif.mon_cb.paddr;
        if (open_item != null &&
            (open_item.txn.write != wr ||
             a != open_item.txn.addr + beat_cnt * 4))
          flush();                       // direction/address discontinuity
        if (open_item == null) begin
          open_item = amba_seq_item::type_id::create("open_item");
          open_item.txn.protocol = APB4;
          open_item.txn.addr  = a;
          open_item.txn.write = wr;
          open_item.txn.len   = 1;
          open_item.txn.size  = SIZE_4B;
          open_item.txn.burst = BURST_INCR;
          open_item.txn.prot  = vif.mon_cb.pprot;
          open_item.txn.resp  = RESP_OKAY;
          open_item.txn.data  = new[64];
          beat_cnt = 0;
        end
        if (wr) open_item.txn.data[beat_cnt] = {32'h0, vif.mon_cb.pwdata};
        else    open_item.txn.data[beat_cnt] = {32'h0, vif.mon_cb.prdata};
        if (vif.mon_cb.pslverr) open_item.txn.resp = RESP_SLVERR;
        beat_cnt++;
      end
      else if (!vif.mon_cb.psel && open_item != null)
        flush();                         // bus returned to IDLE: close burst
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("MON", $sformatf("APB monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
`endif
