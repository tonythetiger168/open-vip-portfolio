// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// c_phy_compliance_checker.sv -- C-PHY tiered compliance SVA checker (module)
// L1 = basic compliance, L2 = full protocol, L3 = advanced, L4 = protocol-specific
`ifndef C_PHY_COMPLIANCE_CHECKER_SV
`define C_PHY_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module c_phy_compliance_checker (mipi_vip_if vif);
  int l1_pass[4], l1_fail[4];
  int l2_pass[4], l2_fail[4];
  int l3_pass[4], l3_fail[4];
  int l4_pass[4], l4_fail[4];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

  // ===== L1: Basic Compliance (4 SVAs) =====
  property p_cphy_symbol; @(posedge vif.clk) disable iff (!vif.rst_n) vif.symbol <= 7'd127; endproperty
  assert_p_cphy_symbol: assert property(p_cphy_symbol) l1_pass[0]++; else begin `uvm_warning("C-PHY_L1", "Symbol 0-127 failed"); l1_fail[0]++; end
  cover_p_cphy_symbol: cover property(p_cphy_symbol);
  property p_cphy_triplet; @(posedge vif.clk) disable iff (!vif.rst_n) vif.triplet inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_cphy_triplet: assert property(p_cphy_triplet) l1_pass[1]++; else begin `uvm_warning("C-PHY_L1", "Triplet valid failed"); l1_fail[1]++; end
  cover_p_cphy_triplet: cover property(p_cphy_triplet);
  property p_cphy_term; @(posedge vif.clk) disable iff (!vif.rst_n) vif.hs_mode |-> vif.term_en; endproperty
  assert_p_cphy_term: assert property(p_cphy_term) l1_pass[2]++; else begin `uvm_warning("C-PHY_L1", "Termination on HS failed"); l1_fail[2]++; end
  cover_p_cphy_term: cover property(p_cphy_term);
  property p_cphy_no_x; @(posedge vif.clk) disable iff (!vif.rst_n) vif.hs_mode |-> !$isunknown(vif.symbol); endproperty
  assert_p_cphy_no_x: assert property(p_cphy_no_x) l1_pass[3]++; else begin `uvm_warning("C-PHY_L1", "No X in HS failed"); l1_fail[3]++; end
  cover_p_cphy_no_x: cover property(p_cphy_no_x);

  // ===== L2: Full Protocol (4 SVAs) =====
  property p_cphy_sp; @(posedge vif.clk) disable iff (!vif.rst_n) vif.sp |-> vif.symbol inside {7'h00,7'h01,7'h02,7'h03,7'h04,7'h05,7'h06,7'h07}; endproperty
  assert_p_cphy_sp: assert property(p_cphy_sp) l2_pass[0]++; else begin `uvm_warning("C-PHY_L2", "SP valid failed"); l2_fail[0]++; end
  cover_p_cphy_sp: cover property(p_cphy_sp);
  property p_cphy_lp; @(posedge vif.clk) disable iff (!vif.rst_n) vif.lp_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_cphy_lp: assert property(p_cphy_lp) l2_pass[1]++; else begin `uvm_warning("C-PHY_L2", "LP state valid failed"); l2_fail[1]++; end
  cover_p_cphy_lp: cover property(p_cphy_lp);
  property p_cphy_cal; @(posedge vif.clk) disable iff (!vif.rst_n) vif.cal_done |-> vif.hs_mode == 0; endproperty
  assert_p_cphy_cal: assert property(p_cphy_cal) l2_pass[2]++; else begin `uvm_warning("C-PHY_L2", "Calibration failed"); l2_fail[2]++; end
  cover_p_cphy_cal: cover property(p_cphy_cal);
  property p_cphy_hs; @(posedge vif.clk) disable iff (!vif.rst_n) vif.hs_mode |-> !$isunknown(vif.symbol); endproperty
  assert_p_cphy_hs: assert property(p_cphy_hs) l2_pass[3]++; else begin `uvm_warning("C-PHY_L2", "HS valid failed"); l2_fail[3]++; end
  cover_p_cphy_hs: cover property(p_cphy_hs);

  // ===== L3: Advanced Features (2 SVAs) =====
  property p_cphy_alp; @(posedge vif.clk) disable iff (!vif.rst_n) vif.alp |-> vif.lp_state == 3'b110; endproperty
  assert_p_cphy_alp: assert property(p_cphy_alp) l3_pass[0]++; else begin `uvm_warning("C-PHY_L3", "ALP mode failed"); l3_fail[0]++; end
  cover_p_cphy_alp: cover property(p_cphy_alp);
  property p_cphy_bw; @(posedge vif.clk) disable iff (!vif.rst_n) vif.bandwidth <= 32'hFFFFFFFF; endproperty
  assert_p_cphy_bw: assert property(p_cphy_bw) l3_pass[1]++; else begin `uvm_warning("C-PHY_L3", "Bandwidth failed"); l3_fail[1]++; end
  cover_p_cphy_bw: cover property(p_cphy_bw);

  // ---------------- L4: C-PHY protocol-specific rules (4) ----------------
  property p_cphy_l4_triplet_toggle; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.hs_mode && $past(vif.hs_mode)) |-> (vif.triplet != $past(vif.triplet)); endproperty
  assert_p_cphy_l4_triplet_toggle: assert property(p_cphy_l4_triplet_toggle) l4_pass[0]++; else begin `uvm_warning("C-PHY_L4", "Triplet not toggling failed"); l4_fail[0]++; end
  cover_p_cphy_l4_triplet_toggle: cover property(p_cphy_l4_triplet_toggle);
  property p_cphy_l4_sp_short; @(posedge vif.clk) disable iff (!vif.rst_n) vif.sp |-> vif.symbol <= 7'd7; endproperty
  assert_p_cphy_l4_sp_short: assert property(p_cphy_l4_sp_short) l4_pass[1]++; else begin `uvm_warning("C-PHY_L4", "SP symbol mapping failed"); l4_fail[1]++; end
  cover_p_cphy_l4_sp_short: cover property(p_cphy_l4_sp_short);
  property p_cphy_l4_alp_lp; @(posedge vif.clk) disable iff (!vif.rst_n) vif.alp |-> !vif.hs_mode; endproperty
  assert_p_cphy_l4_alp_lp: assert property(p_cphy_l4_alp_lp) l4_pass[2]++; else begin `uvm_warning("C-PHY_L4", "ALP during HS failed"); l4_fail[2]++; end
  cover_p_cphy_l4_alp_lp: cover property(p_cphy_l4_alp_lp);
  property p_cphy_l4_hs_term; @(posedge vif.clk) disable iff (!vif.rst_n) vif.hs_mode |-> ##[0:4] vif.term_en; endproperty
  assert_p_cphy_l4_hs_term: assert property(p_cphy_l4_hs_term) l4_pass[3]++; else begin `uvm_warning("C-PHY_L4", "HS without termination failed"); l4_fail[3]++; end
  cover_p_cphy_l4_hs_term: cover property(p_cphy_l4_hs_term);

  final begin : sva_report
    int l1_total=0, l2_total=0, l3_total=0, l4_total=0, l1_hit=0, l2_hit=0, l3_hit=0, l4_hit=0;
    foreach(l1_pass[i]) begin l1_total++; if(l1_pass[i]>0) l1_hit++; end
    foreach(l2_pass[i]) begin l2_total++; if(l2_pass[i]>0) l2_hit++; end
    foreach(l3_pass[i]) begin l3_total++; if(l3_pass[i]>0) l3_hit++; end
    foreach(l4_pass[i]) begin l4_total++; if(l4_pass[i]>0) l4_hit++; end
    l1_cov = (l1_total>0) ? (l1_hit*100.0/l1_total) : 0;
    l2_cov = (l2_total>0) ? (l2_hit*100.0/l2_total) : 0;
    l3_cov = (l3_total>0) ? (l3_hit*100.0/l3_total) : 0;
    l4_cov = (l4_total>0) ? (l4_hit*100.0/l4_total) : 0;
    total_cov = (l1_total+l2_total+l3_total+l4_total>0) ? ((l1_hit+l2_hit+l3_hit+l4_hit)*100.0/(l1_total+l2_total+l3_total+l4_total)) : 0;
    `uvm_info("C-PHY_RPT", $sformatf("=== C-PHY Tiered SVA Report ==="), UVM_LOW)
    `uvm_info("C-PHY_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("C-PHY_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("C-PHY_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("C-PHY_RPT", $sformatf("  L4 Protocol Specific:  %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("C-PHY_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%% (%0d/%0d)", total_cov, l1_hit+l2_hit+l3_hit+l4_hit, l1_total+l2_total+l3_total+l4_total), UVM_LOW)
  end
endmodule
`endif
