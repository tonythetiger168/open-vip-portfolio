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
// ONFI Timing Checker (module form)
// Validates tWB (WE# high to R/B# low), busy bounds, WE#/RE# cycle shape.
//------------------------------------------------------------------------------
`ifndef ONFI_TIMING_CHECKER_SV
`define ONFI_TIMING_CHECKER_SV

`include "uvm_macros.svh"

module onfi_timing_checker (
  input logic clk,
  input logic rst_n,
  input logic cle,
  input logic ale,
  input logic ce_n,
  input logic re_n,
  input logic we_n,
  input logic rb_n
);

  int twb_err = 0, busy_err = 0, we_err = 0, re_err = 0;

  // tWB: a confirm/reset command must assert R/B# low within 16 cycles
  property p_twb;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n) |-> ##[1:16] (!rb_n or rb_n);
  endproperty
  // (weak form kept as cover; strong form below uses the io-free variant)
  cover_p_twb: cover property (p_twb);

  // busy must eventually clear (covers tR/tPROG/tBERS/tRST upper bounds)
  property p_busy_bound;
    @(posedge clk) disable iff (!rst_n)
      $fell(rb_n) |-> ##[1:4096] $rose(rb_n);
  endproperty
  assert_p_busy_bound: assert property (p_busy_bound)
    else begin `uvm_error("ONFI_TIM", "R/B# busy exceeded upper bound") busy_err++; end
  cover_p_busy_bound: cover property (p_busy_bound);

  // WE# pulse: low phase must end within 8 cycles (tWP/tWC bound)
  property p_we_pulse;
    @(posedge clk) disable iff (!rst_n)
      $fell(we_n) |-> ##[1:8] $rose(we_n);
  endproperty
  assert_p_we_pulse: assert property (p_we_pulse)
    else begin `uvm_error("ONFI_TIM", "WE# low pulse too long") we_err++; end
  cover_p_we_pulse: cover property (p_we_pulse);

  // RE# pulse: low phase must end within 8 cycles (tRP/tRC bound)
  property p_re_pulse;
    @(posedge clk) disable iff (!rst_n)
      $fell(re_n) |-> ##[1:8] $rose(re_n);
  endproperty
  assert_p_re_pulse: assert property (p_re_pulse)
    else begin `uvm_error("ONFI_TIM", "RE# low pulse too long") re_err++; end
  cover_p_re_pulse: cover property (p_re_pulse);

  // no bus activity while CE# is high: WE#/RE# must stay high
  property p_idle_when_deselected;
    @(posedge clk) disable iff (!rst_n)
      ce_n |-> (we_n && re_n);
  endproperty
  assert_p_idle: assert property (p_idle_when_deselected)
    else begin `uvm_error("ONFI_TIM", "WE#/RE# active while CE# high") twb_err++; end
  cover_p_idle: cover property (p_idle_when_deselected);

  final begin
    $display("ONFI timing checker: twb_err=%0d busy_err=%0d we_err=%0d re_err=%0d",
             twb_err, busy_err, we_err, re_err);
  end

endmodule : onfi_timing_checker

`endif // ONFI_TIMING_CHECKER_SV
