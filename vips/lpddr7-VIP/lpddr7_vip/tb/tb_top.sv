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

// LPDDR7 Top-Level Testbench with functional memory DUT model (closed loop)
`timescale 1ns/1ps
module tb_top;
  logic ck = 0;
  logic rst_n;
  always #5 ck = ~ck;

  lpddr7_if lpddr7_if(ck, rst_n);

  // Functional DRAM memory model: ACT/RD/WR/PRE/REF with open-row tracking
  lpddr7_mem_model dut (
    .ck    (lpddr7_if.ck),
    .rst_n (lpddr7_if.rst_n),
    .cs_n  (lpddr7_if.cs_n),
    .act_n (lpddr7_if.act_n),
    .ras_n (lpddr7_if.ras_n),
    .cas_n (lpddr7_if.cas_n),
    .we_n  (lpddr7_if.we_n),
    .addr  (lpddr7_if.addr),
    .bg    (lpddr7_if.bg),
    .ba    (lpddr7_if.ba),
    .dq    (lpddr7_if.dq),
    .tRCD  (lpddr7_if.tRCD),
    .tRP   (lpddr7_if.tRP),
    .tRAS  (lpddr7_if.tRAS),
    .tCL   (lpddr7_if.tCL)
  );

  // L1/L2/L3 SVA rule modules (companions of the class checkers)
  lpddr7_protocol_sva      protocol_sva (lpddr7_if);
  lpddr7_data_integrity_sva di_sva      (lpddr7_if);
  lpddr7_timing_sva        timing_sva   (lpddr7_if);
  lpddr7_error_sva         error_sva    (lpddr7_if);

  // SVA compliance checker (L4 protocol-specific rules)
  lpddr7_compliance_checker sva_chk (
    .ck    (lpddr7_if.ck),
    .rst_n (lpddr7_if.rst_n),
    .cs_n  (lpddr7_if.cs_n),
    .act_n (lpddr7_if.act_n),
    .ras_n (lpddr7_if.ras_n),
    .cas_n (lpddr7_if.cas_n),
    .we_n  (lpddr7_if.we_n),
    .addr  (lpddr7_if.addr),
    .bg    (lpddr7_if.bg),
    .ba    (lpddr7_if.ba),
    .dq    (lpddr7_if.dq)
  );

  initial begin
    rst_n = 0;
    #100 rst_n = 1;
  end

  initial begin
    uvm_config_db#(virtual lpddr7_if)::set(null, "*", "vif", lpddr7_if);
    run_test("lpddr7_base_test");
  end

  initial begin
    #1000000 $finish;
  end
endmodule
