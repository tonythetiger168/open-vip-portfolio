// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_monitor.sv -- HBM4 bus monitor
//
// Decodes HBM4 commands (ACT/RD/WR/PRE/REF) from the command/address bus
// on every posedge of ck, samples the DQ data bus at the CAS latency /
// CAS write latency point, reconstructs transactions and publishes them on
// the analysis port for the scoreboard, coverage and checkers.

`ifndef HBM4_MONITOR_SV
`define HBM4_MONITOR_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

class hbm4_monitor extends uvm_monitor;
  `uvm_component_utils(hbm4_monitor)
  virtual hbm4_if vif;
  uvm_analysis_port #(hbm4_transaction) ap;
  int unsigned txn_count = 0;

  // Must match the driver / memory-model latencies
  localparam int TCL  = 10;
  localparam int TCWL = 2;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "HBM4 virtual interface not set")
  endfunction

  task run_phase(uvm_phase phase);
    hbm4_transaction tr;
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) continue;
      if (vif.cs_n !== 1'b0) continue;               // deselect cycle
      if (vif.act_n === 1'b0) begin                  // ACT: row on addr
        tr = hbm4_transaction::type_id::create("tr");
        tr.cmd = HBM4_CMD_ACT;
        tr.row = vif.addr; tr.addr = vif.addr;
        tr.bg = vif.bg; tr.ba = vif.ba; tr.stack_id = vif.stack_id;
        txn_count++;
        `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
        ap.write(tr);
      end
      else if (vif.ras_n === 1'b1 && vif.cas_n === 1'b0) begin  // RD or WR
        tr = hbm4_transaction::type_id::create("tr");
        tr.cmd = vif.we_n ? HBM4_CMD_RD : HBM4_CMD_WR;
        tr.col = vif.addr[9:0]; tr.addr = vif.addr;
        tr.bg = vif.bg; tr.ba = vif.ba; tr.stack_id = vif.stack_id;
        if (vif.we_n) begin                          // RD: sample at CAS latency
          repeat (TCL-1) @(posedge vif.ck);
          #1 tr.rdata = vif.dq;
        end
        else begin                                   // WR: sample at CAS write latency
          repeat (TCWL-1) @(posedge vif.ck);
          #1 tr.data = vif.dq;
        end
        txn_count++;
        `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
        ap.write(tr);
      end
      else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b1 && vif.we_n === 1'b0) begin  // PRE
        tr = hbm4_transaction::type_id::create("tr");
        tr.cmd = HBM4_CMD_PRE;
        tr.bg = vif.bg; tr.ba = vif.ba; tr.stack_id = vif.stack_id;
        txn_count++;
        `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
        ap.write(tr);
      end
      else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b0 && vif.we_n === 1'b1) begin  // REF
        tr = hbm4_transaction::type_id::create("tr");
        tr.cmd = HBM4_CMD_REF;
        tr.bg = vif.bg; tr.ba = vif.ba; tr.stack_id = vif.stack_id;
        txn_count++;
        `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
        ap.write(tr);
      end
      // NOP (cs_n=0, act_n=ras_n=cas_n=we_n=1) is a wait state: not published
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("MON", $sformatf("hbm4 monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
`endif
