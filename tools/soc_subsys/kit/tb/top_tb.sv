// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// top_tb.sv -- AXI4 master-port kit self-test: the manager BFM (in the test)
// drives axim_if, the kit's subordinate answers. No DUT.
//   +UVM_TESTNAME=axim_func_test | axim_checker_test | kit_if_rules_test
// A second axim_if and an ssv_apb_if, with their own reset, are driven pin by
// pin by kit_if_rules_test to trip each cycle-level rule of the two checkers.

interface kit_ctl_if;
  logic rstn = 1'b0;
endinterface

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

  kit_ctl_if ctl ();
  wire       chk_rstn = ctl.rstn;
  axim_if    chk_axi (.aclk(aclk), .aresetn(chk_rstn));
  ssv_apb_if chk_apb (.pclk(aclk), .presetn(chk_rstn));

  initial begin
    uvm_config_db #(virtual axim_if)::set(null, "*", "axim_vif", axi);
    uvm_config_db #(virtual axim_if)::set(null, "*", "chk_axim_vif", chk_axi);
    uvm_config_db #(virtual ssv_apb_if)::set(null, "*", "chk_apb_vif", chk_apb);
    uvm_config_db #(virtual kit_ctl_if)::set(null, "*", "kit_ctl_vif", ctl);
    run_test("axim_func_test");
  end
endmodule
