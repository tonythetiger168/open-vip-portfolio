// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 Error Handling Checker (L3)
// NOTE: deepened to a module-based SVA checker (concurrent assertions are
// module items); the interface port keeps the original vif.* references.

`ifndef HBM5_ERROR_CHECKER_SV
`define HBM5_ERROR_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm5_error_checker (hbm5_if vif);

  property p_hbm5_pm; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pm_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_hbm5_pm: assert property(p_hbm5_pm) else `uvm_warning("HBM5", "Power management failed");
  cover_p_hbm5_pm: cover property(p_hbm5_pm);
  property p_hbm5_refresh; @(posedge vif.ck) disable iff (!vif.rst_n) vif.refresh |-> ##[1:3900] vif.cs_n == 0; endproperty
  assert_p_hbm5_refresh: assert property(p_hbm5_refresh) else `uvm_warning("HBM5", "Refresh interval failed");
  cover_p_hbm5_refresh: cover property(p_hbm5_refresh);
  property p_hbm5_overtemp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp_sensor > 8'd85 |-> vif.cs_n == 1; endproperty
  assert_p_hbm5_overtemp: assert property(p_hbm5_overtemp) else `uvm_warning("HBM5", "Overtemp protection failed");
  cover_p_hbm5_overtemp: cover property(p_hbm5_overtemp);
  property p_hbm5_dfe; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dfe_tap <= 4'd15; endproperty
  assert_p_hbm5_dfe: assert property(p_hbm5_dfe) else `uvm_warning("HBM5", "DFE tap valid failed");
  cover_p_hbm5_dfe: cover property(p_hbm5_dfe);
  property p_hbm5_ecc; @(posedge vif.ck) disable iff (!vif.rst_n) vif.ecc_en |-> vif.data_width >= 5'b01000; endproperty
  assert_p_hbm5_ecc: assert property(p_hbm5_ecc) else `uvm_warning("HBM5", "On-die ECC failed");
  cover_p_hbm5_ecc: cover property(p_hbm5_ecc);
  property p_hbm5_pam4; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pam4_en |-> vif.data_width >= 5'b10000; endproperty
  assert_p_hbm5_pam4: assert property(p_hbm5_pam4) else `uvm_warning("HBM5", "PAM4 mode failed");
  cover_p_hbm5_pam4: cover property(p_hbm5_pam4);
  property p_hbm5_bw; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bandwidth >= 32'h80000000; endproperty
  assert_p_hbm5_bw: assert property(p_hbm5_bw) else `uvm_warning("HBM5", "Bandwidth 4Tb/s+ failed");
  cover_p_hbm5_bw: cover property(p_hbm5_bw);
  property p_hbm5_latency; @(posedge vif.ck) disable iff (!vif.rst_n) vif.latency_target <= 8'd127; endproperty
  assert_p_hbm5_latency: assert property(p_hbm5_latency) else `uvm_warning("HBM5", "Latency target failed");
  cover_p_hbm5_latency: cover property(p_hbm5_latency);
  property p_hbm5_3ds; @(posedge vif.ck) disable iff (!vif.rst_n) vif.stack_id <= 4'd15; endproperty
  assert_p_hbm5_3ds: assert property(p_hbm5_3ds) else `uvm_warning("HBM5", "3DS 16-Hi stack failed");
  cover_p_hbm5_3ds: cover property(p_hbm5_3ds);
  property p_hbm5_link_training; @(posedge vif.ck) disable iff (!vif.rst_n) vif.lt_done |-> vif.speed_grade >= 5'd16; endproperty
  assert_p_hbm5_link_training: assert property(p_hbm5_link_training) else `uvm_warning("HBM5", "Link training failed");
  cover_p_hbm5_link_training: cover property(p_hbm5_link_training);

endmodule : hbm5_error_checker
`endif
