// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 Data Integrity Checker (L2)
// NOTE: deepened to a module-based SVA checker (concurrent assertions are
// module items); the interface port keeps the original vif.* references.

`ifndef HBM5_DATA_INTEGRITY_CHECKER_SV
`define HBM5_DATA_INTEGRITY_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module hbm5_data_integrity_checker (hbm5_if vif);

  property p_hbm5_bl; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bl inside {3'b001,3'b010,3'b011,3'b100,3'b101,3'b110}; endproperty
  assert_p_hbm5_bl: assert property(p_hbm5_bl) else `uvm_warning("HBM5", "Burst length 2/4/8/16/32/64 failed");
  cover_p_hbm5_bl: cover property(p_hbm5_bl);
  property p_hbm5_tRCD; @(posedge vif.ck) disable iff (!vif.rst_n) $fell(vif.cs_n) |-> ##[6:10] vif.ca[4] == 0; endproperty
  assert_p_hbm5_tRCD: assert property(p_hbm5_tRCD) else `uvm_warning("HBM5", "tRCD 6-10 cycles failed");
  cover_p_hbm5_tRCD: cover property(p_hbm5_tRCD);
  property p_hbm5_tRP; @(posedge vif.ck) disable iff (!vif.rst_n) $rose(vif.cs_n) |-> ##[6:10] $fell(vif.cs_n); endproperty
  assert_p_hbm5_tRP: assert property(p_hbm5_tRP) else `uvm_warning("HBM5", "tRP 6-10 cycles failed");
  cover_p_hbm5_tRP: cover property(p_hbm5_tRP);
  property p_hbm5_data_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dqs_t == 1 |-> !$isunknown(vif.dq); endproperty
  assert_p_hbm5_data_valid: assert property(p_hbm5_data_valid) else `uvm_warning("HBM5", "Data valid on RW failed");
  cover_p_hbm5_data_valid: cover property(p_hbm5_data_valid);
  property p_hbm5_dbis; @(posedge vif.ck) disable iff (!vif.rst_n) vif.dbis == 1 |-> vif.dqs_t == 1; endproperty
  assert_p_hbm5_dbis: assert property(p_hbm5_dbis) else `uvm_warning("HBM5", "DBI valid failed");
  cover_p_hbm5_dbis: cover property(p_hbm5_dbis);
  property p_hbm5_temp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp_sensor <= 8'd127; endproperty
  assert_p_hbm5_temp: assert property(p_hbm5_temp) else `uvm_warning("HBM5", "Temperature valid failed");
  cover_p_hbm5_temp: cover property(p_hbm5_temp);
  property p_hbm5_no_x; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.ca); endproperty
  assert_p_hbm5_no_x: assert property(p_hbm5_no_x) else `uvm_warning("HBM5", "No X when active failed");
  cover_p_hbm5_no_x: cover property(p_hbm5_no_x);
  property p_hbm5_reset; @(posedge vif.ck) disable iff (!vif.rst_n) vif.rst_n == 0 |-> ##[100:200] vif.rst_n == 1; endproperty
  assert_p_hbm5_reset: assert property(p_hbm5_reset) else `uvm_warning("HBM5", "Reset stable failed");
  cover_p_hbm5_reset: cover property(p_hbm5_reset);
  property p_hbm5_speed; @(posedge vif.ck) disable iff (!vif.rst_n) vif.speed_grade >= 5'd16; endproperty
  assert_p_hbm5_speed: assert property(p_hbm5_speed) else `uvm_warning("HBM5", "Speed grade 12Gbps+ failed");
  cover_p_hbm5_speed: cover property(p_hbm5_speed);
  property p_hbm5_wck; @(posedge vif.ck) disable iff (!vif.rst_n) vif.wck_ratio inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_hbm5_wck: assert property(p_hbm5_wck) else `uvm_warning("HBM5", "WCK ratio failed");
  cover_p_hbm5_wck: cover property(p_hbm5_wck);

endmodule : hbm5_data_integrity_checker
`endif
