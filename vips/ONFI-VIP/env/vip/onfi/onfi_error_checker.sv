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
// ONFI Error Checker (module form)
// Detects X-propagation / illegal control states; covers error-injection
// scenarios (WP# violations) driven by onfi_error_seq.
//------------------------------------------------------------------------------
`ifndef ONFI_ERROR_CHECKER_SV
`define ONFI_ERROR_CHECKER_SV

`include "uvm_macros.svh"

module onfi_error_checker (
  input logic       clk,
  input logic       rst_n,
  input logic [7:0] io,
  input logic       cle,
  input logic       ale,
  input logic       ce_n,
  input logic       re_n,
  input logic       we_n,
  input logic       wp_n
);

  int x_err = 0, ctl_err = 0;

  // no X on control signals while the chip is selected
  property p_no_x_ctrl;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n) |-> !$isunknown({cle, ale, we_n, re_n});
  endproperty
  assert_p_no_x_ctrl: assert property (p_no_x_ctrl)
    else begin `uvm_error("ONFI_ERR", "X on control signals while CE# low") x_err++; end
  cover_p_no_x_ctrl: cover property (p_no_x_ctrl);

  // CLE/ALE mutual exclusion
  property p_no_cle_ale;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n) |-> !(cle && ale);
  endproperty
  assert_p_no_cle_ale: assert property (p_no_cle_ale)
    else begin `uvm_error("ONFI_ERR", "CLE and ALE both high") ctl_err++; end
  cover_p_no_cle_ale: cover property (p_no_cle_ale);

  // WP# is a static-level protection signal: it must not glitch mid-transaction
  property p_wp_stable;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && !we_n && !cle && !ale) |-> $stable(wp_n);
  endproperty
  assert_p_wp_stable: assert property (p_wp_stable)
    else begin `uvm_error("ONFI_ERR", "WP# glitched during data-in cycle") ctl_err++; end
  cover_p_wp_stable: cover property (p_wp_stable);

  // error-injection coverage: WP# violation on program/erase confirm
  cover_wp_prog_violation: cover property (
    @(posedge clk) disable iff (!rst_n)
      (!wp_n && !ce_n && cle && !we_n && io == 8'h10)
  );
  cover_wp_erase_violation: cover property (
    @(posedge clk) disable iff (!rst_n)
      (!wp_n && !ce_n && cle && !we_n && io == 8'hD0)
  );

  final begin
    $display("ONFI error checker: x_err=%0d ctl_err=%0d", x_err, ctl_err);
  end

endmodule : onfi_error_checker

`endif // ONFI_ERROR_CHECKER_SV
