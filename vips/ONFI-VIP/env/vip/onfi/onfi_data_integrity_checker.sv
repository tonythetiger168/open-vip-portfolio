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
// ONFI Data Integrity Checker (module form)
// Checks that the bidirectional IO bus carries known data on every latch
// edge (WE# rising: host->flash, RE# falling: flash->host).
//------------------------------------------------------------------------------
`ifndef ONFI_DATA_INTEGRITY_CHECKER_SV
`define ONFI_DATA_INTEGRITY_CHECKER_SV

`include "uvm_macros.svh"

module onfi_data_integrity_checker (
  input logic       clk,
  input logic       rst_n,
  input logic [7:0] io,
  input logic       ce_n,
  input logic       re_n,
  input logic       we_n
);

  int din_err = 0, dout_err = 0;

  // host -> flash: IO must be known at every WE# rising edge while selected
  property p_din_known;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && $rose(we_n)) |-> !$isunknown($past(io));
  endproperty
  assert_p_din_known: assert property (p_din_known)
    else begin `uvm_error("ONFI_DI", "X on IO at WE# rising edge") din_err++; end
  cover_p_din_known: cover property (p_din_known);

  // flash -> host: IO must be known while RE# is low (data-out window)
  property p_dout_known;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && !re_n) |-> !$isunknown(io);
  endproperty
  assert_p_dout_known: assert property (p_dout_known)
    else begin `uvm_error("ONFI_DI", "X on IO during RE# low window") dout_err++; end
  cover_p_dout_known: cover property (p_dout_known);

  // IO must not be bus-floating contention: never X at any selected strobe edge
  property p_no_contention;
    @(posedge clk) disable iff (!rst_n)
      (!ce_n && ($rose(we_n) || $fell(re_n))) |-> !$isunknown(io);
  endproperty
  assert_p_no_contention: assert property (p_no_contention);
  cover_p_no_contention: cover property (p_no_contention);

  final begin
    $display("ONFI data integrity checker: din_err=%0d dout_err=%0d", din_err, dout_err);
  end

endmodule : onfi_data_integrity_checker

`endif // ONFI_DATA_INTEGRITY_CHECKER_SV
