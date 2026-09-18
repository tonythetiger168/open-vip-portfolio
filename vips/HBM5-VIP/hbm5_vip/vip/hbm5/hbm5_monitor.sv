// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM monitor -- decodes DRAM commands from the hbm5_if command/address
// bus waveform (cs_n/act_n/ras_n/cas_n/we_n), tracks per-bank state and page
// hit/miss, and publishes reconstructed transactions on the analysis port.
`ifndef HBM5_MONITOR_SV
`define HBM5_MONITOR_SV

class hbm5_monitor extends uvm_monitor;
  `uvm_component_utils(hbm5_monitor)

  virtual hbm5_if vif;
  uvm_analysis_port #(hbm5_transaction) ap;
  int unsigned txn_count = 0;

  protected bit        bank_active [32];
  protected bit [15:0] active_row  [32];

  function new(string name = "hbm5_monitor", uvm_component parent = null);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual hbm5_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "HBM5: virtual interface not set")
  endfunction

  function int bank_id(bit [2:0] bg, bit [1:0] ba);
    return bg * 4 + ba;
  endfunction

  task run_phase(uvm_phase phase);
    hbm5_transaction tr;
    int id;
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) begin
        foreach (bank_active[i]) bank_active[i] = 0;
        continue;
      end
      if (vif.cs_n) continue;           // deselect = NOP, not published

      tr = hbm5_transaction::type_id::create("tr");
      tr.addr = vif.addr;
      tr.bg   = vif.bg;
      tr.ba   = vif.ba;
      id      = bank_id(vif.bg, vif.ba);
      tr.page_hit = 1'b0;

      if (!vif.act_n) begin                     // ACT: row address
        tr.cmd    = hbm5_transaction::ACT;
        tr.bstate = bank_active[id] ? B_ACTIVE : B_IDLE;
        bank_active[id] = 1;
        active_row[id]  = vif.addr;
      end
      else if (vif.ras_n && !vif.cas_n && vif.we_n) begin   // RD
        tr.cmd      = hbm5_transaction::READ;
        tr.bstate   = bank_active[id] ? B_ACTIVE : B_IDLE;
        tr.page_hit = bank_active[id];          // read hits the open page
      end
      else if (vif.ras_n && !vif.cas_n && !vif.we_n) begin  // WR
        tr.cmd      = hbm5_transaction::WRITE;
        tr.bstate   = bank_active[id] ? B_ACTIVE : B_IDLE;
        tr.page_hit = bank_active[id];
      end
      else if (!vif.ras_n && vif.cas_n && !vif.we_n) begin  // PRE
        tr.cmd    = hbm5_transaction::PRE;
        tr.bstate = bank_active[id] ? B_ACTIVE : B_IDLE;
        bank_active[id] = 0;
      end
      else if (!vif.ras_n && !vif.cas_n && vif.we_n) begin  // REF
        tr.cmd    = hbm5_transaction::REF;
        tr.bstate = B_IDLE;
        foreach (bank_active[i]) bank_active[i] = 0;
      end
      else begin                                // MRS/ZQC/other: record as NOP
        tr.cmd    = hbm5_transaction::NOP;
        tr.bstate = B_IDLE;
      end

      if (tr.cmd != hbm5_transaction::NOP) begin
        txn_count++;
        `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
        ap.write(tr);
      end
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("MON", $sformatf("HBM5 monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
`endif
