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
// ONFI Tiered Compliance SVA Checker (module form, bound to the ONFI bus)
// L1 = signal sanity | L2 = protocol rules | L3 = timing/busy rules
// L4 = ONFI command-sequence rules
//------------------------------------------------------------------------------
`ifndef ONFI_COMPLIANCE_CHECKER_SV
`define ONFI_COMPLIANCE_CHECKER_SV

`include "uvm_macros.svh"

module onfi_compliance_checker (
  input logic       clk,
  input logic       rst_n,
  input logic [7:0] io,
  input logic       cle,
  input logic       ale,
  input logic       ce_n,
  input logic       re_n,
  input logic       we_n,
  input logic       wp_n,
  input logic       rb_n
);

  int l1_pass[4], l1_fail[4];
  int l2_pass[4], l2_fail[4];
  int l3_pass[4], l3_fail[4];
  int l4_pass[5], l4_fail[5];

  // ---------------- L1: signal sanity (4) ----------------
  property p_cmd_io_valid;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n) |-> !$isunknown(io);
  endproperty
  assert_l1_cmd_io: assert property (p_cmd_io_valid) l1_pass[0]++;
    else begin `uvm_warning("ONFI_L1", "command latch with X on IO") l1_fail[0]++; end
  cover_l1_cmd_io: cover property (p_cmd_io_valid);

  property p_addr_io_valid;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && ale && !we_n) |-> !$isunknown(io);
  endproperty
  assert_l1_addr_io: assert property (p_addr_io_valid) l1_pass[1]++;
    else begin `uvm_warning("ONFI_L1", "address latch with X on IO") l1_fail[1]++; end
  cover_l1_addr_io: cover property (p_addr_io_valid);

  property p_we_re_mutex;
    @(posedge clk) disable iff (!rst_n)
      !(we_n == 1'b0 && re_n == 1'b0);
  endproperty
  assert_l1_we_re: assert property (p_we_re_mutex) l1_pass[2]++;
    else begin `uvm_warning("ONFI_L1", "WE# and RE# simultaneously low") l1_fail[2]++; end
  cover_l1_we_re: cover property (p_we_re_mutex);

  property p_cle_ale_mutex;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n) |-> !(cle && ale);
  endproperty
  assert_l1_cle_ale: assert property (p_cle_ale_mutex) l1_pass[3]++;
    else begin `uvm_warning("ONFI_L1", "CLE and ALE simultaneously high") l1_fail[3]++; end
  cover_l1_cle_ale: cover property (p_cle_ale_mutex);

  // ---------------- L2: protocol rules (4) ----------------
  property p_cmd_needs_ce;
    @(posedge clk) disable iff (!rst_n)
      (cle && !we_n) |-> !ce_n;
  endproperty
  assert_l2_cmd_ce: assert property (p_cmd_needs_ce) l2_pass[0]++;
    else begin `uvm_warning("ONFI_L2", "command latch without CE#") l2_fail[0]++; end
  cover_l2_cmd_ce: cover property (p_cmd_needs_ce);

  property p_addr_needs_ce;
    @(posedge clk) disable iff (!rst_n)
      (ale && !we_n) |-> !ce_n;
  endproperty
  assert_l2_addr_ce: assert property (p_addr_needs_ce) l2_pass[1]++;
    else begin `uvm_warning("ONFI_L2", "address latch without CE#") l2_fail[1]++; end
  cover_l2_addr_ce: cover property (p_addr_needs_ce);

  property p_data_in_valid;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && !cle && !ale && !we_n) |-> !$isunknown(io);
  endproperty
  assert_l2_din: assert property (p_data_in_valid) l2_pass[2]++;
    else begin `uvm_warning("ONFI_L2", "data-in cycle with X on IO") l2_fail[2]++; end
  cover_l2_din: cover property (p_data_in_valid);

  property p_read_known;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && !re_n) |-> !$isunknown(io);
  endproperty
  assert_l2_dout: assert property (p_read_known) l2_pass[3]++;
    else begin `uvm_warning("ONFI_L2", "data-out cycle with X on IO") l2_fail[3]++; end
  cover_l2_dout: cover property (p_read_known);

  // ---------------- L3: timing / busy rules (4) ----------------
  property p_busy_recovers;
    @(posedge clk) disable iff (!rst_n)
      (!rb_n) |-> ##[1:4096] rb_n;
  endproperty
  assert_l3_busy: assert property (p_busy_recovers) l3_pass[0]++;
    else begin `uvm_warning("ONFI_L3", "R/B# busy never recovered") l3_fail[0]++; end
  cover_l3_busy: cover property (p_busy_recovers);

  property p_confirm_goes_busy;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && (io inside {8'h10, 8'h30, 8'hD0, 8'hFF}))
      |-> ##[1:16] (!rb_n);
  endproperty
  assert_l3_twb: assert property (p_confirm_goes_busy) l3_pass[1]++;
    else begin `uvm_warning("ONFI_L3", "confirm command did not assert busy (tWB)") l3_fail[1]++; end
  cover_l3_twb: cover property (p_confirm_goes_busy);

  property p_reset_recovers;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'hFF) |-> ##[1:64] rb_n;
  endproperty
  assert_l3_rst: assert property (p_reset_recovers) l3_pass[2]++;
    else begin `uvm_warning("ONFI_L3", "reset did not complete (tRST)") l3_fail[2]++; end
  cover_l3_rst: cover property (p_reset_recovers);

  property p_re_cycle_ends;
    @(posedge clk) disable iff (!rst_n)
      $fell(re_n) |-> ##[1:64] $rose(re_n);
  endproperty
  assert_l3_re: assert property (p_re_cycle_ends) l3_pass[3]++;
    else begin `uvm_warning("ONFI_L3", "RE# cycle never ended") l3_fail[3]++; end
  cover_l3_re: cover property (p_re_cycle_ends);

  // ---------------- L4: ONFI command-sequence rules (5) ----------------
  property p_read_id_has_addr;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'h90) |-> ##[1:32] (!ce_n && ale && !we_n);
  endproperty
  assert_l4_read_id: assert property (p_read_id_has_addr) l4_pass[0]++;
    else begin `uvm_warning("ONFI_L4", "READ ID (90h) not followed by address cycle") l4_fail[0]++; end
  cover_l4_read_id: cover property (p_read_id_has_addr);

  property p_program_confirmed;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'h80)
      |-> ##[1:4096] (!ce_n && cle && !we_n && io == 8'h10);
  endproperty
  assert_l4_prog: assert property (p_program_confirmed) l4_pass[1]++;
    else begin `uvm_warning("ONFI_L4", "PROGRAM PAGE (80h) missing confirm (10h)") l4_fail[1]++; end
  cover_l4_prog: cover property (p_program_confirmed);

  property p_erase_confirmed;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'h60)
      |-> ##[1:64] (!ce_n && cle && !we_n && io == 8'hD0);
  endproperty
  assert_l4_erase: assert property (p_erase_confirmed) l4_pass[2]++;
    else begin `uvm_warning("ONFI_L4", "ERASE BLOCK (60h) missing confirm (D0h)") l4_fail[2]++; end
  cover_l4_erase: cover property (p_erase_confirmed);

  property p_read_confirmed;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'h00)
      |-> ##[1:64] (!ce_n && cle && !we_n && io == 8'h30);
  endproperty
  assert_l4_read: assert property (p_read_confirmed) l4_pass[3]++;
    else begin `uvm_warning("ONFI_L4", "READ PAGE (00h) missing confirm (30h)") l4_fail[3]++; end
  cover_l4_read: cover property (p_read_confirmed);

  property p_set_feat_has_addr;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n && io == 8'hEF) |-> ##[1:32] (!ce_n && ale && !we_n);
  endproperty
  assert_l4_feat: assert property (p_set_feat_has_addr) l4_pass[4]++;
    else begin `uvm_warning("ONFI_L4", "SET FEATURES (EFh) not followed by feature address") l4_fail[4]++; end
  cover_l4_feat: cover property (p_set_feat_has_addr);

  // ---------------- tiered summary ----------------
  final begin
    int l1_hit, l2_hit, l3_hit, l4_hit;
    foreach (l1_pass[i]) if (l1_pass[i] > 0) l1_hit++;
    foreach (l2_pass[i]) if (l2_pass[i] > 0) l2_hit++;
    foreach (l3_pass[i]) if (l3_pass[i] > 0) l3_hit++;
    foreach (l4_pass[i]) if (l4_pass[i] > 0) l4_hit++;
    $display("=== ONFI Tiered SVA Report ===");
    $display("  L1 signal sanity:          %0d/4 hit, %0d fails", l1_hit, l1_fail.sum());
    $display("  L2 protocol rules:         %0d/4 hit, %0d fails", l2_hit, l2_fail.sum());
    $display("  L3 timing/busy rules:      %0d/4 hit, %0d fails", l3_hit, l3_fail.sum());
    $display("  L4 command-sequence rules: %0d/5 hit, %0d fails", l4_hit, l4_fail.sum());
  end

endmodule : onfi_compliance_checker

`endif // ONFI_COMPLIANCE_CHECKER_SV
