// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_env.sv -- HBM4 verification environment with end-to-end scoreboard

`ifndef HBM4_ENV_SV
`define HBM4_ENV_SV
`include "uvm_macros.svh"

`uvm_analysis_imp_decl(_exp)
`uvm_analysis_imp_decl(_obs)

// End-to-end scoreboard: compares driver-issued (expected) transactions
// against monitor-decoded (observed) transactions.
class hbm4_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(hbm4_scoreboard)
  uvm_analysis_imp_exp #(hbm4_transaction, hbm4_scoreboard) exp_ap;
  uvm_analysis_imp_obs #(hbm4_transaction, hbm4_scoreboard) obs_ap;

  hbm4_transaction exp_q[$], obs_q[$];
  int unsigned n_matches = 0, n_mismatches = 0;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    exp_ap = new("exp_ap", this);
    obs_ap = new("obs_ap", this);
  endfunction

  function void write_exp(hbm4_transaction t); exp_q.push_back(t); check(); endfunction
  function void write_obs(hbm4_transaction t); obs_q.push_back(t); check(); endfunction

  function void check();
    while (exp_q.size() && obs_q.size()) begin
      hbm4_transaction e = exp_q.pop_front();
      hbm4_transaction o = obs_q.pop_front();
      bit ok = (e.cmd == o.cmd) && (e.bg == o.bg) && (e.ba == o.ba);
      case (e.cmd)
        HBM4_CMD_ACT: ok = ok && (e.row == o.row) && (e.stack_id == o.stack_id);
        HBM4_CMD_RD:  ok = ok && (e.col == o.col) && (e.rdata == o.rdata);
        HBM4_CMD_WR:  ok = ok && (e.col == o.col) && (e.data == o.data);
        default: ; // PRE/REF/NOP: command + bank comparison is sufficient
      endcase
      if (ok) n_matches++;
      else begin
        n_mismatches++;
        `uvm_error("SB", $sformatf("mismatch exp{%s} obs{%s}",
                   e.convert2string(), o.convert2string()))
      end
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("SB", $sformatf("hbm4 scoreboard: n_matches=%0d n_mismatches=%0d",
              n_matches, n_mismatches), UVM_LOW)
    if (n_mismatches) `uvm_error("SB", "end-to-end n_mismatches detected")
  endfunction
endclass

class hbm4_env extends uvm_env;
  `uvm_component_utils(hbm4_env)
  hbm4_protocol_checker       protocol_chk;
  hbm4_data_integrity_checker di_chk;
  hbm4_timing_checker         timing_chk;
  hbm4_error_checker          error_chk;
  hbm4_agent                  agt;
  hbm4_scoreboard             sb;
  hbm4_coverage               cov;
  function new(string name="hbm4_env", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    protocol_chk = hbm4_protocol_checker::type_id::create("protocol_chk", this);
    di_chk       = hbm4_data_integrity_checker::type_id::create("di_chk", this);
    timing_chk   = hbm4_timing_checker::type_id::create("timing_chk", this);
    error_chk    = hbm4_error_checker::type_id::create("error_chk", this);
    agt = hbm4_agent::type_id::create("agt", this);
    sb  = hbm4_scoreboard::type_id::create("sb", this);
    cov = hbm4_coverage::type_id::create("cov", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap.connect(sb.obs_ap);
    agt.drv.drv_ap.connect(sb.exp_ap);
    agt.mon.ap.connect(cov.analysis_export);
  endfunction
endclass
`endif
