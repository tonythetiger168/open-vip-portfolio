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

// LPDDR7 UVM Environment with end-to-end scoreboard
`ifndef LPDDR7_ENV_SV
`define LPDDR7_ENV_SV

`uvm_analysis_imp_decl(_lp7_exp)
`uvm_analysis_imp_decl(_lp7_obs)

// End-to-end scoreboard: compares driver-issued (expected) transactions
// against monitor-decoded (observed) transactions.
class lpddr7_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(lpddr7_scoreboard)
  uvm_analysis_imp_lp7_exp #(lpddr7_transaction, lpddr7_scoreboard) exp_ap;
  uvm_analysis_imp_lp7_obs #(lpddr7_transaction, lpddr7_scoreboard) obs_ap;

  lpddr7_transaction exp_q[$], obs_q[$];
  int unsigned n_matches = 0, n_mismatches = 0;

  function new(string name="lpddr7_scoreboard", uvm_component parent=null);
    super.new(name, parent);
    exp_ap = new("exp_ap", this);
    obs_ap = new("obs_ap", this);
  endfunction

  function void write_lp7_exp(lpddr7_transaction t); exp_q.push_back(t); check(); endfunction
  function void write_lp7_obs(lpddr7_transaction t); obs_q.push_back(t); check(); endfunction

  function void check();
    while (exp_q.size() && obs_q.size()) begin
      lpddr7_transaction e = exp_q.pop_front();
      lpddr7_transaction o = obs_q.pop_front();
      bit ok;
      case (e.cmd)
        // ACT/PRE/REF are driver-internal housekeeping; matched by cmd+bank only
        LPDDR7_CMD_ACT, LPDDR7_CMD_PRE, LPDDR7_CMD_REF:
          ok = (e.cmd == o.cmd);
        LPDDR7_CMD_WR:
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
    `uvm_info("SB", $sformatf("lpddr7 scoreboard: n_matches=%0d n_mismatches=%0d",
              n_matches, n_mismatches), UVM_LOW)
    if (n_mismatches) `uvm_error("SB", "end-to-end n_mismatches detected")
  endfunction
endclass

class lpddr7_env extends uvm_env;
  `uvm_component_utils(lpddr7_env)
  lpddr7_agent                  agt;
  lpddr7_scoreboard             sb;
  lpddr7_coverage               cov;
  lpddr7_protocol_checker      protocol_chk;
  lpddr7_data_integrity_checker di_chk;
  lpddr7_timing_checker         timing_chk;
  lpddr7_error_checker          error_chk;
  function new(string name="lpddr7_env", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agt = lpddr7_agent::type_id::create("agt", this);
    sb  = lpddr7_scoreboard::type_id::create("sb", this);
    cov = lpddr7_coverage::type_id::create("cov", this);
    protocol_chk = lpddr7_protocol_checker::type_id::create("protocol_chk", this);
    di_chk       = lpddr7_data_integrity_checker::type_id::create("di_chk", this);
    timing_chk   = lpddr7_timing_checker::type_id::create("timing_chk", this);
    error_chk    = lpddr7_error_checker::type_id::create("error_chk", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap.connect(sb.obs_ap);
    agt.drv.drv_ap.connect(sb.exp_ap);
    agt.mon.ap.connect(cov.analysis_export);
  endfunction
endclass
`endif
