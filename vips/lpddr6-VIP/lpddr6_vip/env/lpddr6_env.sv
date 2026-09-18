// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

// LPDDR6 UVM Environment with end-to-end scoreboard
`ifndef LPDDR6_ENV_SV
`define LPDDR6_ENV_SV

`uvm_analysis_imp_decl(_lp6_exp)
`uvm_analysis_imp_decl(_lp6_obs)

// End-to-end scoreboard: compares driver-issued (expected) transactions
// against monitor-decoded (observed) transactions.
class lpddr6_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(lpddr6_scoreboard)
  uvm_analysis_imp_lp6_exp #(lpddr6_transaction, lpddr6_scoreboard) exp_ap;
  uvm_analysis_imp_lp6_obs #(lpddr6_transaction, lpddr6_scoreboard) obs_ap;

  lpddr6_transaction exp_q[$], obs_q[$];
  int unsigned n_matches = 0, n_mismatches = 0;

  function new(string name="lpddr6_scoreboard", uvm_component parent=null);
    super.new(name, parent);
    exp_ap = new("exp_ap", this);
    obs_ap = new("obs_ap", this);
  endfunction

  function void write_lp6_exp(lpddr6_transaction t); exp_q.push_back(t); check(); endfunction
  function void write_lp6_obs(lpddr6_transaction t); obs_q.push_back(t); check(); endfunction

  function void check();
    while (exp_q.size() && obs_q.size()) begin
      lpddr6_transaction e = exp_q.pop_front();
      lpddr6_transaction o = obs_q.pop_front();
      bit ok;
      case (e.cmd)
        // ACT/PRE/REF are driver-internal housekeeping; matched by cmd+bank only
        LPDDR6_CMD_ACT, LPDDR6_CMD_PRE, LPDDR6_CMD_REF:
          ok = (e.cmd == o.cmd);
        LPDDR6_CMD_WR:
          ok = (e.cmd == o.cmd) && (e.bg == o.bg) && (e.ba == o.ba) &&
               (e.col == o.col) && (e.data == o.data) && (e.data2 == o.data2);
        default: // RD: compare command + address (read data comes from DUT)
          ok = (e.cmd == o.cmd) && (e.bg == o.bg) && (e.ba == o.ba) && (e.col == o.col);
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
    `uvm_info("SB", $sformatf("lpddr6 scoreboard: n_matches=%0d n_mismatches=%0d",
              n_matches, n_mismatches), UVM_LOW)
    if (n_mismatches) `uvm_error("SB", "end-to-end n_mismatches detected")
  endfunction
endclass

class lpddr6_env extends uvm_env;
  `uvm_component_utils(lpddr6_env)
  lpddr6_agent                  agt;
  lpddr6_scoreboard             sb;
  lpddr6_coverage               cov;
  lpddr6_protocol_checker      protocol_chk;
  lpddr6_data_integrity_checker di_chk;
  lpddr6_timing_checker         timing_chk;
  lpddr6_error_checker          error_chk;
  function new(string name="lpddr6_env", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agt = lpddr6_agent::type_id::create("agt", this);
    sb  = lpddr6_scoreboard::type_id::create("sb", this);
    cov = lpddr6_coverage::type_id::create("cov", this);
    protocol_chk = lpddr6_protocol_checker::type_id::create("protocol_chk", this);
    di_chk       = lpddr6_data_integrity_checker::type_id::create("di_chk", this);
    timing_chk   = lpddr6_timing_checker::type_id::create("timing_chk", this);
    error_chk    = lpddr6_error_checker::type_id::create("error_chk", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap.connect(sb.obs_ap);
    agt.drv.drv_ap.connect(sb.exp_ap);
    agt.mon.ap.connect(cov.analysis_export);
  endfunction
endclass
`endif
