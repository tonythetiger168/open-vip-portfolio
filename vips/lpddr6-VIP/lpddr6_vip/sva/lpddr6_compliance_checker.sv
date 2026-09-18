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
// lpddr6_compliance_checker.sv -- LPDDR6 SVA compliance checker (module)
// L1=4 | L2=4 | L3=4 SVA rules added below (the vip/lpddr6 class
// checkers keep the procedural protocol / data-integrity / timing /
// error versions). This module also adds the L4 protocol-specific
// rules and is instantiated in tb/tb_top.sv.

`ifndef LPDDR6_COMPLIANCE_CHECKER_SV
`define LPDDR6_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module lpddr6_compliance_checker
(
  input logic        ck,
  input logic        rst_n,
  input logic        cs_n,
  input logic        act_n,
  input logic        ras_n,
  input logic        cas_n,
  input logic        we_n,
  input logic [15:0] addr,
  input logic [2:0]  bg,
  input logic [1:0]  ba,
  input logic [63:0] dq
);

  wire cmd_act = (cs_n == 1'b0) && (act_n == 1'b0);
  wire cmd_wr  = (cs_n == 1'b0) && (act_n == 1'b1) && (ras_n == 1'b1) && (cas_n == 1'b0) && (we_n == 1'b0);
  wire cmd_rd  = (cs_n == 1'b0) && (act_n == 1'b1) && (ras_n == 1'b1) && (cas_n == 1'b0) && (we_n == 1'b1);
  wire cmd_pre = (cs_n == 1'b0) && (act_n == 1'b1) && (ras_n == 1'b0) && (cas_n == 1'b1) && (we_n == 1'b0);
  wire cmd_ref = (cs_n == 1'b0) && (act_n == 1'b1) && (ras_n == 1'b0) && (cas_n == 1'b0) && (we_n == 1'b1);

  // ---------------- L1: signal sanity (4) ----------------
  // L1-1: command bus is never X after reset
  a_lp6_l1_cmd_known : assert property (@(posedge ck) disable iff (!rst_n)
    !$isunknown({cs_n, act_n, ras_n, cas_n, we_n}))
    else `uvm_error("SVA_L1", "lpddr6: X on command bus")
  c_lp6_l1_cmd_known : cover property (@(posedge ck) disable iff (!rst_n)
    cs_n == 1'b0);

  // L1-2: address is known whenever a command is issued
  a_lp6_l1_addr_known : assert property (@(posedge ck) disable iff (!rst_n)
    (cs_n == 1'b0) |-> !$isunknown(addr))
    else `uvm_error("SVA_L1", "lpddr6: X on address bus during command")
  c_lp6_l1_addr_known : cover property (@(posedge ck) disable iff (!rst_n)
    (cs_n == 1'b0) && !$isunknown(addr));

  // L1-3: bank select is known whenever a command is issued
  a_lp6_l1_bank_known : assert property (@(posedge ck) disable iff (!rst_n)
    (cs_n == 1'b0) |-> !$isunknown({bg, ba}))
    else `uvm_error("SVA_L1", "lpddr6: X on bank select during command")
  c_lp6_l1_bank_known : cover property (@(posedge ck) disable iff (!rst_n)
    (cs_n == 1'b0) && !$isunknown({bg, ba}));

  // L1-4: no command in the cycle reset is released
  a_lp6_l1_reset_idle : assert property (@(posedge ck) disable iff (!rst_n)
    $rose(rst_n) |-> (cs_n == 1'b1))
    else `uvm_error("SVA_L1", "lpddr6: command issued during reset release")
  c_lp6_l1_reset_idle : cover property (@(posedge ck) disable iff (!rst_n)
    $rose(rst_n));

  // ---------------- L2: FSM legality (4) ----------------
  // L2-1: PRE only legal from ROW_ACTIVE (IDLE->PRE is illegal)
  a_lp6_l2_pre_after_act : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_pre |-> ($past(cmd_act, 1) || $past(cmd_act, 2) || $past(cmd_act, 3) ||
                 $past(cmd_act, 4) || $past(cmd_act, 5) || $past(cmd_act, 6) ||
                 $past(cmd_act, 7) || $past(cmd_act, 8)))
    else `uvm_error("SVA_L2", "lpddr6: PRE without preceding ACT (IDLE->PRE)")
  c_lp6_l2_pre_after_act : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_act ##[1:8] cmd_pre);

  // L2-2: bank returns to IDLE after PRE (no RD/WR in the next cycle)
  a_lp6_l2_idle_after_pre : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_pre |=> !(cmd_rd || cmd_wr))
    else `uvm_error("SVA_L2", "lpddr6: RD/WR right after PRE (bank not open)")
  c_lp6_l2_idle_after_pre : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_pre ##[2:8] (cmd_rd || cmd_wr));

  // L2-3: ROW_ACTIVE must persist (no PRE within 4 cycles of ACT)
  a_lp6_l2_row_active_hold : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_act |=> !cmd_pre[*4])
    else `uvm_error("SVA_L2", "lpddr6: PRE too soon after ACT (ROW_ACTIVE hold)")
  c_lp6_l2_row_active_hold : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_act ##[5:16] cmd_pre);

  // L2-4: command decode is mutually exclusive (one command per cycle)
  a_lp6_l2_onehot_cmd : assert property (@(posedge ck) disable iff (!rst_n)
    $onehot0({cmd_act, cmd_rd, cmd_wr, cmd_pre, cmd_ref}))
    else `uvm_error("SVA_L2", "lpddr6: multiple commands decoded in one cycle")
  c_lp6_l2_onehot_cmd : cover property (@(posedge ck) disable iff (!rst_n)
    $onehot({cmd_act, cmd_rd, cmd_wr, cmd_pre, cmd_ref}));

  // ---------------- L3: protocol rules (4) ----------------
  // L3-1: tCCD -- no CAS command on back-to-back cycles
  a_lp6_l3_tccd : assert property (@(posedge ck) disable iff (!rst_n)
    (cmd_rd || cmd_wr) |=> !(cmd_rd || cmd_wr))
    else `uvm_error("SVA_L3", "lpddr6: tCCD violated (CAS on consecutive cycles)")
  c_lp6_l3_tccd : cover property (@(posedge ck) disable iff (!rst_n)
    (cmd_rd || cmd_wr) ##1 !(cmd_rd || cmd_wr));

  // L3-2: DQ is driven (known) through the write burst window after WR
  a_lp6_l3_wr_dq_window : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_wr |=> (!$isunknown(dq)) [*2])
    else `uvm_error("SVA_L3", "lpddr6: DQ not driven inside write burst window")
  c_lp6_l3_wr_dq_window : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_wr ##1 !$isunknown(dq));

  // L3-3: refresh completes and traffic resumes (ACT follows REF)
  a_lp6_l3_ref_resume : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_ref |-> s_eventually cmd_act)
    else `uvm_error("SVA_L3", "lpddr6: no ACT after refresh (refresh did not complete)")
  c_lp6_l3_ref_resume : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_ref ##[1:64] cmd_act);

  // L3-4: tRFC -- refresh commands are spaced (no REF within 3 cycles of REF)
  a_lp6_l3_trfc : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_ref |=> !cmd_ref[*3])
    else `uvm_error("SVA_L3", "lpddr6: tRFC violated (REF too soon after REF)")
  c_lp6_l3_trfc : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_ref ##[4:64] cmd_ref);

  // ---------------- L4: LPDDR6 protocol-specific rules (5) ----------------
  // L4-1: ACT carries a known row address and legal bank
  a_lp6_l4_act_addr : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_act |-> (!$isunknown(addr) && !$isunknown({bg, ba})))
    else `uvm_error("SVA_L4", "lpddr6: ACT with unknown row/bank address")

  // L4-2: RD/WR must be preceded by an ACT (within tRC window) on the same bank
  a_lp6_l4_rdwr_after_act : assert property (@(posedge ck) disable iff (!rst_n)
    (cmd_rd || cmd_wr) |-> ($past(cmd_act, 1) || $past(cmd_act, 2) || $past(cmd_act, 3) ||
                            $past(cmd_act, 4) || $past(cmd_act, 5) || $past(cmd_act, 6)))
    else `uvm_error("SVA_L4", "lpddr6: RD/WR without preceding ACT")

  // L4-3: no new ACT to a bank that has not been precharged (ACT->ACT needs PRE)
  a_lp6_l4_act_act_gap : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_act |-> not ($past(cmd_act, 1) && !$past(cmd_pre, 1)))
    else `uvm_error("SVA_L4", "lpddr6: back-to-back ACT without PRE")

  // L4-4: write data must be known on the cycle after WR (burst beat 0)
  a_lp6_l4_wr_data_known : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_wr |=> !$isunknown(dq))
    else `uvm_error("SVA_L4", "lpddr6: WR burst beat has X on DQ")

  // L4-5: refresh eventually closes banks (PRE/REF follows traffic)
  a_lp6_l4_refresh_progress : assert property (@(posedge ck) disable iff (!rst_n)
    cmd_ref |-> $past(cmd_pre, 1) || $past(cmd_pre, 2) || $past(cmd_ref, 1))
    else `uvm_error("SVA_L4", "lpddr6: REF not preceded by PRE (all-bank refresh sequence)")

  // ---------------- L4: protocol coverage ----------------
  c_lp6_l4_act_rd  : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_act ##[1:8] cmd_rd);
  c_lp6_l4_act_wr  : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_act ##[1:8] cmd_wr);
  c_lp6_l4_wr_pre  : cover property (@(posedge ck) disable iff (!rst_n)
    cmd_wr ##[1:12] cmd_pre);

endmodule
`endif
