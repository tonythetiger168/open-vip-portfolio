// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// top_tb.sv -- AXI4 master-port kit self-test: the manager BFM (in the test)
// drives axim_if, the kit's subordinate answers. No DUT.
//   +UVM_TESTNAME=axim_func_test | axim_checker_test

module top_tb;
  import uvm_pkg::*;
  import ssv_pkg::*;
  import axim_kit_pkg::*;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;
  initial begin
    repeat (5) @(posedge aclk);
    @(negedge aclk);   // released on a falling edge: no race with the rising-edge logic
    aresetn = 1'b1;
  end

  axim_if axi (.aclk(aclk), .aresetn(aresetn));

  initial begin
    uvm_config_db #(virtual axim_if)::set(null, "*", "axim_vif", axi);
    run_test("axim_func_test");
  end
endmodule
