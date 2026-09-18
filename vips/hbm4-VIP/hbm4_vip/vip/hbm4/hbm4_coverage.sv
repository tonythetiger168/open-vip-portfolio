// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_coverage.sv -- HBM4 functional coverage
//
// cg_command    : command distribution x bank cross
// cg_bank_state : bank state machine transition coverage (ACT->RD/WR->PRE->ACT)
// cg_addr       : row/column/stack address pattern coverage with cross

`ifndef HBM4_COVERAGE_SV
`define HBM4_COVERAGE_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

class hbm4_coverage extends uvm_subscriber #(hbm4_transaction);
  `uvm_component_utils(hbm4_coverage)

  hbm4_transaction tr;

  covergroup cg_command;
    cp_cmd : coverpoint tr.cmd {
      bins act = {HBM4_CMD_ACT};
      bins rd  = {HBM4_CMD_RD};
      bins wr  = {HBM4_CMD_WR};
      bins pre = {HBM4_CMD_PRE};
      bins refr = {HBM4_CMD_REF};
      // REACHABILITY: NOP is a bus wait state; the monitor intentionally does not
      // publish NOP transactions (see hbm4_monitor.sv), so this bin can never be hit.
      ignore_bins nop = {HBM4_CMD_NOP};
    }
    cp_bg : coverpoint tr.bg { bins bg[] = {[0:7]}; }
    cp_ba : coverpoint tr.ba { bins ba[] = {[0:3]}; }
    cx_cmd_bank : cross cp_cmd, cp_ba;
  endgroup

  covergroup cg_bank_state with function sample(hbm4_cmd_e c);
    cp_trans : coverpoint c {
      bins act_rd  = (HBM4_CMD_ACT => HBM4_CMD_RD);
      bins act_wr  = (HBM4_CMD_ACT => HBM4_CMD_WR);
      bins rd_pre  = (HBM4_CMD_RD  => HBM4_CMD_PRE);
      bins wr_pre  = (HBM4_CMD_WR  => HBM4_CMD_PRE);
      bins pre_act = (HBM4_CMD_PRE => HBM4_CMD_ACT);
      bins ref_act = (HBM4_CMD_REF => HBM4_CMD_ACT);
      bins rd_wr   = (HBM4_CMD_RD  => HBM4_CMD_WR);
      bins wr_rd   = (HBM4_CMD_WR  => HBM4_CMD_RD);
    }
  endgroup

  covergroup cg_addr;
    cp_row : coverpoint tr.row iff (tr.cmd == HBM4_CMD_ACT) {
      bins low  = {[16'h0000 : 16'h00FF]};
      bins mid  = {[16'h0100 : 16'hFEFF]};
      bins high = {[16'hFF00 : 16'hFFFF]};
    }
    cp_col : coverpoint tr.col iff (tr.cmd == HBM4_CMD_RD || tr.cmd == HBM4_CMD_WR) {
      bins low  = {[10'h000 : 10'h0FF]};
      bins high = {[10'h100 : 10'h3FF]};
    }
    cp_stack : coverpoint tr.stack_id { bins s[] = {[0:7]}; }
    cx_row_col : cross cp_row, cp_col;
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_command    = new();
    cg_bank_state = new();
    cg_addr       = new();
  endfunction

  function void write(hbm4_transaction t);
    tr = t;
    cg_command.sample();
    cg_bank_state.sample(t.cmd);
    cg_addr.sample();
  endfunction
endclass
`endif
