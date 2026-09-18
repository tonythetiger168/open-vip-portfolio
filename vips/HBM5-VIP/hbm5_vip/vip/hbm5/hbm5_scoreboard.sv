// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 scoreboard -- end-to-end comparison of driver-issued (expected)
// transactions against monitor-decoded (observed) transactions.
`ifndef HBM5_SCOREBOARD_SV
`define HBM5_SCOREBOARD_SV

`uvm_analysis_imp_decl(_exp)
`uvm_analysis_imp_decl(_obs)

class hbm5_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(hbm5_scoreboard)

  uvm_analysis_imp_exp #(hbm5_transaction, hbm5_scoreboard) exp_ap;
  uvm_analysis_imp_obs #(hbm5_transaction, hbm5_scoreboard) obs_ap;

  hbm5_transaction exp_q[$], obs_q[$];
  int unsigned n_matches = 0, n_mismatches = 0;

  function new(string name = "hbm5_scoreboard", uvm_component parent = null);
    super.new(name, parent);
    exp_ap = new("exp_ap", this);
    obs_ap = new("obs_ap", this);
  endfunction

  function void write_exp(hbm5_transaction t);
    exp_q.push_back(t);
    check();
  endfunction

  function void write_obs(hbm5_transaction t);
    obs_q.push_back(t);
    check();
  endfunction

  function void check();
    while (exp_q.size() && obs_q.size()) begin
      hbm5_transaction e = exp_q.pop_front();
      hbm5_transaction o = obs_q.pop_front();
      if (e.cmd == o.cmd && e.addr == o.addr && e.bg == o.bg && e.ba == o.ba)
        n_matches++;
      else begin
        n_mismatches++;
        `uvm_error("SB", $sformatf("mismatch exp{%s} obs{%s}",
                   e.convert2string(), o.convert2string()))
      end
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("SB", $sformatf("HBM5 scoreboard: n_matches=%0d n_mismatches=%0d",
              n_matches, n_mismatches), UVM_LOW)
    if (n_mismatches)
      `uvm_error("SB", "end-to-end n_mismatches detected")
  endfunction
endclass
`endif
