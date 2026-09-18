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
//------------------------------------------------------------------------------
// CSE Tiered Compliance SVA Checker (module form, bound to the CSE channel)
// L1 = signal sanity | L2 = handshake rules | L3 = response/IRQ timing
// L4 = CSE command/response protocol rules
//------------------------------------------------------------------------------
`ifndef CSE_COMPLIANCE_CHECKER_SV
`define CSE_COMPLIANCE_CHECKER_SV

`include "uvm_macros.svh"

module cse_compliance_checker (
  input logic       clk,
  input logic       rst_n,
  input logic [7:0] cse_data,
  input logic       cse_valid,
  input logic       cse_ready,
  input logic [3:0] cse_cmd,
  input logic       cse_irq
);

  int l1_pass[4], l1_fail[4];
  int l2_pass[4], l2_fail[4];
  int l3_pass[4], l3_fail[4];
  int l4_pass[5], l4_fail[5];

  // ---------------- L1: signal sanity (4) ----------------
  property p_cmd_known;
    @(posedge clk) disable iff (!rst_n)
      cse_valid |-> !$isunknown(cse_cmd);
  endproperty
  assert_l1_cmd_known: assert property (p_cmd_known) l1_pass[0]++;
    else begin `uvm_warning("CSE_L1", "command X while valid") l1_fail[0]++; end
  cover_l1_cmd_known: cover property (p_cmd_known);

  property p_data_known;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready) |-> !$isunknown(cse_data);
  endproperty
  assert_l1_data_known: assert property (p_data_known) l1_pass[1]++;
    else begin `uvm_warning("CSE_L1", "operand X at command accept") l1_fail[1]++; end
  cover_l1_data_known: cover property (p_data_known);

  property p_ctrl_known;
    @(posedge clk) disable iff (!rst_n)
      !$isunknown({cse_valid, cse_ready, cse_irq});
  endproperty
  assert_l1_ctrl_known: assert property (p_ctrl_known) l1_pass[2]++;
    else begin `uvm_warning("CSE_L1", "X on control signals") l1_fail[2]++; end
  cover_l1_ctrl_known: cover property (p_ctrl_known);

  property p_resp_known;
    @(posedge clk) disable iff (!rst_n)
      cse_irq |-> !$isunknown(cse_data);
  endproperty
  assert_l1_resp_known: assert property (p_resp_known) l1_pass[3]++;
    else begin `uvm_warning("CSE_L1", "response X during IRQ") l1_fail[3]++; end
  cover_l1_resp_known: cover property (p_resp_known);

  // ---------------- L2: handshake rules (4) ----------------
  property p_valid_stable;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && !cse_ready) |=> cse_valid;
  endproperty
  assert_l2_valid_stable: assert property (p_valid_stable) l2_pass[0]++;
    else begin `uvm_warning("CSE_L2", "valid dropped before accept") l2_fail[0]++; end
  cover_l2_valid_stable: cover property (p_valid_stable);

  property p_cmd_stable;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && !cse_ready) |=> $stable(cse_cmd);
  endproperty
  assert_l2_cmd_stable: assert property (p_cmd_stable) l2_pass[1]++;
    else begin `uvm_warning("CSE_L2", "command changed while stalled") l2_fail[1]++; end
  cover_l2_cmd_stable: cover property (p_cmd_stable);

  property p_ready_eventually;
    @(posedge clk) disable iff (!rst_n)
      cse_valid |-> ##[1:16] cse_ready;
  endproperty
  assert_l2_ready: assert property (p_ready_eventually) l2_pass[2]++;
    else begin `uvm_warning("CSE_L2", "ready never asserted for command") l2_fail[2]++; end
  cover_l2_ready: cover property (p_ready_eventually);

  property p_valid_drops;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready) |=> !cse_valid;
  endproperty
  assert_l2_valid_drops: assert property (p_valid_drops) l2_pass[3]++;
    else begin `uvm_warning("CSE_L2", "valid not dropped after accept") l2_fail[3]++; end
  cover_l2_valid_drops: cover property (p_valid_drops);

  // ---------------- L3: response / IRQ timing (4) ----------------
  property p_irq_after_cmd;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready) |-> ##[1:16] $rose(cse_irq);
  endproperty
  assert_l3_irq_after_cmd: assert property (p_irq_after_cmd) l3_pass[0]++;
    else begin `uvm_warning("CSE_L3", "no IRQ after accepted command") l3_fail[0]++; end
  cover_l3_irq_after_cmd: cover property (p_irq_after_cmd);

  property p_irq_width;
    @(posedge clk) disable iff (!rst_n)
      $rose(cse_irq) |-> ##[1:16] $fell(cse_irq);
  endproperty
  assert_l3_irq_width: assert property (p_irq_width) l3_pass[1]++;
    else begin `uvm_warning("CSE_L3", "IRQ never deasserted") l3_fail[1]++; end
  cover_l3_irq_width: cover property (p_irq_width);

  property p_no_cmd_during_irq;
    @(posedge clk) disable iff (!rst_n)
      cse_irq |-> !cse_valid;
  endproperty
  assert_l3_no_cmd_irq: assert property (p_no_cmd_during_irq) l3_pass[2]++;
    else begin `uvm_warning("CSE_L3", "new command during response window") l3_fail[2]++; end
  cover_l3_no_cmd_irq: cover property (p_no_cmd_during_irq);

  property p_ready_low_while_busy;
    @(posedge clk) disable iff (!rst_n)
      $fell(cse_ready) |-> ##[1:16] $rose(cse_ready);
  endproperty
  assert_l3_ready_recovers: assert property (p_ready_low_while_busy) l3_pass[3]++;
    else begin `uvm_warning("CSE_L3", "ready never recovered") l3_fail[3]++; end
  cover_l3_ready_recovers: cover property (p_ready_low_while_busy);

  // ---------------- L4: CSE command/response protocol rules (5) ----------------
  property p_rd_reg_resp;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready && cse_cmd == 4'd1)
      |-> ##[1:16] (cse_irq && !$isunknown(cse_data));
  endproperty
  assert_l4_rd_reg: assert property (p_rd_reg_resp) l4_pass[0]++;
    else begin `uvm_warning("CSE_L4", "RD_REG without valid response") l4_fail[0]++; end
  cover_l4_rd_reg: cover property (p_rd_reg_resp);

  property p_wr_reg_resp;
    logic [3:0] d;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready && cse_cmd == 4'd2, d = cse_data[3:0])
      |-> ##[1:16] (cse_irq && cse_data == {4'h0, d});
  endproperty
  assert_l4_wr_reg: assert property (p_wr_reg_resp) l4_pass[1]++;
    else begin `uvm_warning("CSE_L4", "WR_REG response does not echo write data") l4_fail[1]++; end
  cover_l4_wr_reg: cover property (p_wr_reg_resp);

  property p_soft_reset_ack;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready && cse_cmd == 4'd6)
      |-> ##[1:16] (cse_irq && cse_data == 8'hA5);
  endproperty
  assert_l4_rst_ack: assert property (p_soft_reset_ack) l4_pass[2]++;
    else begin `uvm_warning("CSE_L4", "SOFT_RESET not acknowledged with 0xA5") l4_fail[2]++; end
  cover_l4_rst_ack: cover property (p_soft_reset_ack);

  property p_reserved_err;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready && cse_cmd > 4'd9)
      |-> ##[1:16] (cse_irq && cse_data == 8'hEE);
  endproperty
  assert_l4_reserved: assert property (p_reserved_err) l4_pass[3]++;
    else begin `uvm_warning("CSE_L4", "reserved command not answered with 0xEE") l4_fail[3]++; end
  cover_l4_reserved: cover property (p_reserved_err);

  property p_get_cfg_resp;
    @(posedge clk) disable iff (!rst_n)
      (cse_valid && cse_ready && cse_cmd == 4'd9)
      |-> ##[1:16] cse_irq;
  endproperty
  assert_l4_get_cfg: assert property (p_get_cfg_resp) l4_pass[4]++;
    else begin `uvm_warning("CSE_L4", "GET_CFG without response") l4_fail[4]++; end
  cover_l4_get_cfg: cover property (p_get_cfg_resp);

  // ---------------- tiered summary ----------------
  final begin
    int l1_hit, l2_hit, l3_hit, l4_hit;
    foreach (l1_pass[i]) if (l1_pass[i] > 0) l1_hit++;
    foreach (l2_pass[i]) if (l2_pass[i] > 0) l2_hit++;
    foreach (l3_pass[i]) if (l3_pass[i] > 0) l3_hit++;
    foreach (l4_pass[i]) if (l4_pass[i] > 0) l4_hit++;
    $display("=== CSE Tiered SVA Report ===");
    $display("  L1 signal sanity:       %0d/4 hit, %0d fails", l1_hit, l1_fail.sum());
    $display("  L2 handshake rules:     %0d/4 hit, %0d fails", l2_hit, l2_fail.sum());
    $display("  L3 response/IRQ timing: %0d/4 hit, %0d fails", l3_hit, l3_fail.sum());
    $display("  L4 protocol rules:      %0d/5 hit, %0d fails", l4_hit, l4_fail.sum());
  end

endmodule : cse_compliance_checker

`endif // CSE_COMPLIANCE_CHECKER_SV
