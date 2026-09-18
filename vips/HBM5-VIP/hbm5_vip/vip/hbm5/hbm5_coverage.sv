// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 functional coverage -- command distribution, bank-state transitions
// and address/page patterns, with crosses.
`ifndef HBM5_COVERAGE_SV
`define HBM5_COVERAGE_SV

class hbm5_coverage extends uvm_subscriber #(hbm5_transaction);
  `uvm_component_utils(hbm5_coverage)

  hbm5_transaction tr;

  // 1) Command distribution x bank geometry
  covergroup cg_cmd;
    option.per_instance = 1;
    cp_cmd : coverpoint tr.cmd {
      bins act = {hbm5_transaction::ACT};
      bins rd  = {hbm5_transaction::READ};
      bins wr  = {hbm5_transaction::WRITE};
      bins pre = {hbm5_transaction::PRE};
      bins refr = {hbm5_transaction::REF};
    }
    cp_bg : coverpoint tr.bg { bins bg[] = {[0:7]}; }
    cp_ba : coverpoint tr.ba { bins ba[] = {[0:3]}; }
    cx_cmd_bg : cross cp_cmd, cp_bg;
    cx_cmd_ba : cross cp_cmd, cp_ba;
  endgroup

  // 2) Bank state transitions (sampled from monitor-decoded state)
  covergroup cg_bank_state with function sample(bank_state_e s, hbm5_transaction t);
    option.per_instance = 1;
    cp_state : coverpoint s { bins idle = {B_IDLE}; bins active = {B_ACTIVE}; }
    cp_trans : coverpoint s {
      bins row_open   = (B_IDLE   => B_ACTIVE);
      bins access     = (B_ACTIVE => B_ACTIVE);
      bins row_close  = (B_ACTIVE => B_IDLE);
    }
    cp_cmd : coverpoint t.cmd {
      bins act = {hbm5_transaction::ACT};
      bins rd  = {hbm5_transaction::READ};
      bins wr  = {hbm5_transaction::WRITE};
      bins pre = {hbm5_transaction::PRE};
    }
    cx_state_cmd : cross cp_state, cp_cmd;
  endgroup

  // 3) Address / page-hit pattern coverage
  covergroup cg_addr;
    option.per_instance = 1;
    cp_row : coverpoint tr.addr iff (tr.cmd == hbm5_transaction::ACT) {
      bins low  = {[16'h0000:16'h00FF]};
      bins mid  = {[16'h0100:16'h7FFF]};
      bins high = {[16'h8000:16'hFFFF]};
    }
    cp_col : coverpoint tr.addr[11:0] iff (tr.cmd inside {hbm5_transaction::READ,
                                                          hbm5_transaction::WRITE}) {
      bins low  = {[12'h000:12'h0FF]};
      bins mid  = {[12'h100:12'h7FF]};
      bins high = {[12'h800:12'hFFF]};
    }
    cp_page : coverpoint tr.page_hit iff (tr.cmd inside {hbm5_transaction::READ,
                                                           hbm5_transaction::WRITE}) {
      bins hit  = {1};
      bins miss = {0};
    }
    cp_bl : coverpoint tr.bl { bins b8 = {8}; bins b16 = {16}; }
    cx_cmd_page : cross cp_page, cp_bl;
  endgroup

  function new(string name = "hbm5_coverage", uvm_component parent = null);
    super.new(name, parent);
    cg_cmd        = new();
    cg_bank_state = new();
    cg_addr       = new();
  endfunction

  function void write(hbm5_transaction t);
    tr = t;
    cg_cmd.sample();
    cg_bank_state.sample(t.bstate, t);
    cg_addr.sample();
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("COV", $sformatf("HBM5 coverage: cmd=%0.1f%% bank_state=%0.1f%% addr=%0.1f%%",
              cg_cmd.get_coverage(), cg_bank_state.get_coverage(),
              cg_addr.get_coverage()), UVM_LOW)
  endfunction
endclass
`endif
