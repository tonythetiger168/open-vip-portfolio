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
// ONFI Protocol Checker (module form)
// Validates protocol state machine, field ranges, and command encodings.
//------------------------------------------------------------------------------
`ifndef ONFI_PROTOCOL_CHECKER_SV
`define ONFI_PROTOCOL_CHECKER_SV

`include "uvm_macros.svh"

module onfi_protocol_checker (
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

  int cmd_err = 0, mux_err = 0, enc_err = 0, wp_err = 0;

  // command latch requires CE# active
  property p_ce_cmd;
    @(posedge clk) disable iff (!rst_n)
      (cle && !we_n) |-> !ce_n;
  endproperty
  assert_p_ce_cmd: assert property (p_ce_cmd)
    else begin `uvm_error("ONFI_CHK", "CE# not active for command latch") cmd_err++; end
  cover_p_ce_cmd: cover property (p_ce_cmd);

  // WE# and RE# are mutually exclusive
  property p_we_re;
    @(posedge clk) disable iff (!rst_n)
      !(we_n == 1'b0 && re_n == 1'b0);
  endproperty
  assert_p_we_re: assert property (p_we_re)
    else begin `uvm_error("ONFI_CHK", "WE# and RE# not mutually exclusive") mux_err++; end
  cover_p_we_re: cover property (p_we_re);

  // ALE/CLE require CE# active
  property p_ale_cle_ce;
    @(posedge clk) disable iff (!rst_n)
      ((cle || ale) && !we_n) |-> !ce_n;
  endproperty
  assert_p_ale_cle_ce: assert property (p_ale_cle_ce)
    else begin `uvm_error("ONFI_CHK", "ALE/CLE latch without CE#") mux_err++; end
  cover_p_ale_cle_ce: cover property (p_ale_cle_ce);

  // only legal ONFI command encodings may be latched
  property p_cmd_encoding;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && cle && !we_n)
      |-> (io inside {8'h90, 8'h70, 8'h00, 8'h30, 8'h80, 8'h10,
                      8'h60, 8'hD0, 8'hFF, 8'hEC, 8'hEF, 8'hEE});
  endproperty
  assert_p_cmd_encoding: assert property (p_cmd_encoding)
    else begin `uvm_error("ONFI_CHK", "illegal ONFI command encoding") enc_err++; end
  cover_p_cmd_encoding: cover property (p_cmd_encoding);

  // write-protect: with WP# low a program/erase confirm must not reach the
  // array (the DUT flags FAIL); flag any confirm issued while WP# is low as
  // an observable error-injection event (cover only, no assert).
  cover_wp_violation: cover property (
    @(posedge clk) disable iff (!rst_n)
      (!wp_n && !ce_n && cle && !we_n && (io inside {8'h10, 8'hD0}))
  );

  final begin
    $display("ONFI protocol checker: cmd_err=%0d mux_err=%0d enc_err=%0d wp_err=%0d",
             cmd_err, mux_err, enc_err, wp_err);
  end

endmodule : onfi_protocol_checker

`endif // ONFI_PROTOCOL_CHECKER_SV
