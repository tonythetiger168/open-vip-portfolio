// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM driver -- issues real DRAM command sequences (ACT/RD/WR/PRE/REF)
// on the hbm5_if command/address bus with JEDEC-style bank/row/col timing
// (tRCD/tRP/tRAS/tCL/tCWL/tFAW) and publishes expected items to the scoreboard.
`ifndef HBM5_DRIVER_SV
`define HBM5_DRIVER_SV

class hbm5_driver extends uvm_driver #(hbm5_transaction);
  `uvm_component_utils(hbm5_driver)

  virtual hbm5_if vif;
  uvm_analysis_port #(hbm5_transaction) drv_ap;  // expected items for scoreboard

  // DRAM timing parameters (clock cycles), aligned with the timing checker
  int tRCD = 6;
  int tRP  = 6;
  int tRAS = 16;
  int tCL  = 12;
  int tCWL = 10;
  int tFAW = 12;
  int tRFC = 20;

  int unsigned cyc = 0;                 // driver-local free-running cycle count
  bit          bank_active [32];        // flattened {bg,ba} bank state
  bit [15:0]   active_row  [32];
  int unsigned act_cycle   [32];        // cycle of last ACT per bank (tRAS/tFAW)
  int unsigned act_hist    [4];         // last 4 ACT cycles (tFAW window)
  int          act_hist_idx = 0;

  function new(string name = "hbm5_driver", uvm_component parent = null);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual hbm5_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "HBM5: virtual interface not set")
  endfunction

  function int bank_id(bit [2:0] bg, bit [1:0] ba);
    return bg * 4 + ba;
  endfunction

  // Drive one command cycle on the CA bus, then count the cycle
  task drive_cmd(bit cs_n, bit act_n, bit ras_n, bit cas_n, bit we_n,
                 bit [15:0] a, bit [2:0] bg, bit [1:0] ba);
    vif.cb.cs_n  <= cs_n;
    vif.cb.act_n <= act_n;
    vif.cb.ras_n <= ras_n;
    vif.cb.cas_n <= cas_n;
    vif.cb.we_n  <= we_n;
    vif.cb.addr  <= a;
    vif.cb.bg    <= bg;
    vif.cb.ba    <= ba;
    @(vif.cb);
    cyc++;
  endtask

  // Deselect (NOP) for n cycles
  task idle(int n);
    vif.cb.cs_n  <= 1'b1;
    vif.cb.act_n <= 1'b1;
    vif.cb.ras_n <= 1'b1;
    vif.cb.cas_n <= 1'b1;
    vif.cb.we_n  <= 1'b1;
    repeat (n) begin
      @(vif.cb);
      cyc++;
    end
  endtask

  task drive_activate(hbm5_transaction tr);
    int id = bank_id(tr.bg, tr.ba);
    // tFAW: no more than 4 ACTs inside the rolling window
    while (cyc - act_hist[act_hist_idx] <= tFAW && act_hist[act_hist_idx] != 0)
      idle(1);
    // ACT: cs_n=0, act_n=0, row address on addr bus
    drive_cmd(0, 0, 1, 1, 1, tr.addr, tr.bg, tr.ba);
    bank_active[id] = 1;
    active_row[id]  = tr.addr;
    act_cycle[id]   = cyc;
    act_hist[act_hist_idx] = cyc;
    act_hist_idx = (act_hist_idx + 1) % 4;
    idle(tRCD - 1);                     // tRCD before a CAS command may follow
  endtask

  task drive_read(hbm5_transaction tr);
    int id = bank_id(tr.bg, tr.ba);
    if (!bank_active[id])
      `uvm_warning("DRV", $sformatf("RD to closed bank bg=%0d ba=%0d", tr.bg, tr.ba))
    // RD: cs_n=0, act_n=1, ras_n=1, cas_n=0, we_n=1, column on addr bus
    drive_cmd(0, 1, 1, 0, 1, tr.addr, tr.bg, tr.ba);
    idle(tCL);                          // CAS latency
    tr.rdata = new[tr.bl];
    for (int i = 0; i < tr.bl; i++) begin
      @(vif.cb);
      cyc++;
      tr.rdata[i] = vif.cb.dq;          // sample read data burst
    end
  endtask

  task drive_write(hbm5_transaction tr);
    int id = bank_id(tr.bg, tr.ba);
    if (!bank_active[id])
      `uvm_warning("DRV", $sformatf("WR to closed bank bg=%0d ba=%0d", tr.bg, tr.ba))
    // WR: cs_n=0, act_n=1, ras_n=1, cas_n=0, we_n=0
    drive_cmd(0, 1, 1, 0, 0, tr.addr, tr.bg, tr.ba);
    idle(tCWL - 1);                     // CAS write latency
    for (int i = 0; i < tr.bl; i++) begin
      vif.cb.dq <= tr.data;
      vif.cb.dm <= '0;
      @(vif.cb);
      cyc++;
    end
  endtask

  task drive_precharge(hbm5_transaction tr);
    int id = bank_id(tr.bg, tr.ba);
    while (cyc - act_cycle[id] < tRAS)  // tRAS: earliest legal PRE after ACT
      idle(1);
    // PRE: cs_n=0, act_n=1, ras_n=0, cas_n=1, we_n=0
    drive_cmd(0, 1, 0, 1, 0, tr.addr, tr.bg, tr.ba);
    bank_active[id] = 0;
    idle(tRP - 1);                      // tRP before the bank may be re-activated
  endtask

  task drive_refresh(hbm5_transaction tr);
    foreach (bank_active[i]) begin
      if (bank_active[i])
        `uvm_warning("DRV", "REF issued with open banks (sequence should PRE first)")
    end
    // REF: cs_n=0, act_n=1, ras_n=0, cas_n=0, we_n=1
    drive_cmd(0, 1, 0, 0, 1, tr.addr, tr.bg, tr.ba);
    idle(tRFC - 1);
  endtask

  task run_phase(uvm_phase phase);
    hbm5_transaction tr;
    idle(1);
    wait (vif.rst_n === 1'b1);
    idle(5);
    forever begin
      seq_item_port.get_next_item(tr);
      `uvm_info("DRV", {"drive: ", tr.convert2string()}, UVM_HIGH)
      case (tr.cmd)
        hbm5_transaction::ACT:   drive_activate(tr);
        hbm5_transaction::READ:  drive_read(tr);
        hbm5_transaction::WRITE: drive_write(tr);
        hbm5_transaction::PRE:   drive_precharge(tr);
        hbm5_transaction::REF:   drive_refresh(tr);
        default:                idle(1);   // NOP
      endcase
      if (tr.cmd != hbm5_transaction::NOP)
        drv_ap.write(tr);               // broadcast expected transaction
      seq_item_port.item_done();
    end
  endtask
endclass
`endif
