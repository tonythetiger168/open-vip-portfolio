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

// LPDDR6 Top-Level Testbench with functional memory DUT model (closed loop)
`timescale 1ns/1ps
module tb_top;
  logic ck = 0;
  logic rst_n;
  always #5 ck = ~ck;

  lpddr6_if lpddr6_if(ck, rst_n);

  // Functional DRAM memory model: ACT/RD/WR/PRE/REF with open-row tracking
  lpddr6_mem_model dut (
    .ck    (lpddr6_if.ck),
    .rst_n (lpddr6_if.rst_n),
    .cs_n  (lpddr6_if.cs_n),
    .act_n (lpddr6_if.act_n),
    .ras_n (lpddr6_if.ras_n),
    .cas_n (lpddr6_if.cas_n),
    .we_n  (lpddr6_if.we_n),
    .addr  (lpddr6_if.addr),
    .bg    (lpddr6_if.bg),
    .ba    (lpddr6_if.ba),
    .dq    (lpddr6_if.dq),
    .tRCD  (lpddr6_if.tRCD),
    .tRP   (lpddr6_if.tRP),
    .tRAS  (lpddr6_if.tRAS),
    .tCL   (lpddr6_if.tCL)
  );

  // L1/L2/L3 SVA rule modules (companions of the class checkers)
  lpddr6_protocol_sva      protocol_sva (lpddr6_if);
  lpddr6_data_integrity_sva di_sva      (lpddr6_if);
  lpddr6_timing_sva        timing_sva   (lpddr6_if);
  lpddr6_error_sva         error_sva    (lpddr6_if);

  // SVA compliance checker (L4 protocol-specific rules)
  lpddr6_compliance_checker sva_chk (
    .ck    (lpddr6_if.ck),
    .rst_n (lpddr6_if.rst_n),
    .cs_n  (lpddr6_if.cs_n),
    .act_n (lpddr6_if.act_n),
    .ras_n (lpddr6_if.ras_n),
    .cas_n (lpddr6_if.cas_n),
    .we_n  (lpddr6_if.we_n),
    .addr  (lpddr6_if.addr),
    .bg    (lpddr6_if.bg),
    .ba    (lpddr6_if.ba),
    .dq    (lpddr6_if.dq)
  );

  initial begin
    rst_n = 0;
    #100 rst_n = 1;
  end

  initial begin
    uvm_config_db#(virtual lpddr6_if)::set(null, "*", "vif", lpddr6_if);
    run_test("lpddr6_base_test");
  end

  initial begin
    #1000000 $finish;
  end
endmodule
