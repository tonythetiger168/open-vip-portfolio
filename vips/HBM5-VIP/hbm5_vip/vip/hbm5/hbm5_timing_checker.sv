// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 Timing Performance Checker (L2)
// NOTE: deepened to a module-based SVA checker (concurrent assertions are
// module items); the interface port keeps the original vif.* references.

`ifndef HBM5_TIMING_CHECKER_SV
`define HBM5_TIMING_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm5_timing_checker (hbm5_if vif);

  property p_hbm5_tRCD; @(posedge vif.ck) disable iff (!vif.rst_n) $fell(vif.cs_n) |-> ##[6:10] vif.ca[4] == 0; endproperty
  assert_p_hbm5_tRCD: assert property(p_hbm5_tRCD) else `uvm_warning("HBM5", "tRCD 6-10 cycles failed");
  cover_p_hbm5_tRCD: cover property(p_hbm5_tRCD);
  property p_hbm5_tRP; @(posedge vif.ck) disable iff (!vif.rst_n) $rose(vif.cs_n) |-> ##[6:10] $fell(vif.cs_n); endproperty
  assert_p_hbm5_tRP: assert property(p_hbm5_tRP) else `uvm_warning("HBM5", "tRP 6-10 cycles failed");
  cover_p_hbm5_tRP: cover property(p_hbm5_tRP);

endmodule : hbm5_timing_checker
`endif
