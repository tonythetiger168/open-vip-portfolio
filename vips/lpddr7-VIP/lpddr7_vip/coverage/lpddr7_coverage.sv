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

// LPDDR7 Functional Coverage:
//   cg_protocol - command/bank/burst configuration (with crosses)
//   cg_fsm      - command sequence (FSM) transitions
//   cg_data     - data pattern corners (with cross)
`ifndef LPDDR7_COVERAGE_SV
`define LPDDR7_COVERAGE_SV

class lpddr7_coverage extends uvm_subscriber #(lpddr7_transaction);
  `uvm_component_utils(lpddr7_coverage)

  lpddr7_transaction tr;
  lpddr7_cmd_e prev_cmd = LPDDR7_CMD_NOP;

  covergroup cg_protocol;
    option.per_instance = 1;
    cp_cmd : coverpoint tr.cmd {
      bins act = {LPDDR7_CMD_ACT};
      bins rd  = {LPDDR7_CMD_RD};
      bins wr  = {LPDDR7_CMD_WR};
      bins pre = {LPDDR7_CMD_PRE};
      bins refr = {LPDDR7_CMD_REF};
    }
    cp_bg  : coverpoint tr.bg { bins bg[] = {[0:3]}; }
    cp_ba  : coverpoint tr.ba { bins ba[] = {[0:3]}; }
    cp_bl  : coverpoint tr.bl { bins bl8 = {8}; bins bl16 = {16}; }
    cp_row : coverpoint tr.row {
      bins low  = {[16'h0000:16'h00FF]};
      bins mid  = {[16'h0100:16'h7FFF]};
      bins high = {[16'h8000:16'hFFFF]};
    }
    cx_cmd_bank : cross cp_cmd, cp_bg, cp_ba;
    cx_cmd_bl   : cross cp_cmd, cp_bl;
  endgroup

  covergroup cg_fsm;
    option.per_instance = 1;
    cp_trans : coverpoint tr.cmd {
      bins act_rd  = (LPDDR7_CMD_ACT => LPDDR7_CMD_RD);
      bins act_wr  = (LPDDR7_CMD_ACT => LPDDR7_CMD_WR);
      bins rw_pre  = (LPDDR7_CMD_RD  => LPDDR7_CMD_PRE),
                     (LPDDR7_CMD_WR  => LPDDR7_CMD_PRE);
      bins pre_act = (LPDDR7_CMD_PRE => LPDDR7_CMD_ACT),
                     (LPDDR7_CMD_PRE => LPDDR7_CMD_RD),
                     (LPDDR7_CMD_PRE => LPDDR7_CMD_WR);
      bins ref_seq = (LPDDR7_CMD_PRE => LPDDR7_CMD_REF);
    }
  endgroup

  covergroup cg_data;
    option.per_instance = 1;
    cp_data : coverpoint tr.data iff (tr.cmd == LPDDR7_CMD_WR) {
      bins zero     = {64'h0};
      bins ones     = {64'hFFFF_FFFF_FFFF_FFFF};
      bins aa       = {64'hAAAA_AAAA_AAAA_AAAA};
      bins five5    = {64'h5555_5555_5555_5555};
      bins walk     = default;
    }
    cp_data2 : coverpoint tr.data2 iff (tr.cmd == LPDDR7_CMD_WR) {
      bins zero = {64'h0};
      bins ones = {64'hFFFF_FFFF_FFFF_FFFF};
      bins mix  = default;
    }
    cx_data_bank : cross cp_data, cp_data2;
  endgroup

  function new(string name="lpddr7_coverage", uvm_component parent=null);
    super.new(name, parent);
    cg_protocol = new();
    cg_fsm      = new();
    cg_data     = new();
  endfunction

  function void write(lpddr7_transaction t);
    tr = t;
    cg_protocol.sample();
    cg_fsm.sample();
    cg_data.sample();
    prev_cmd = t.cmd;
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("COV", $sformatf("lpddr7 coverage: protocol=%0.1f%% fsm=%0.1f%% data=%0.1f%%",
              cg_protocol.get_coverage(), cg_fsm.get_coverage(), cg_data.get_coverage()), UVM_LOW)
  endfunction
endclass
`endif
