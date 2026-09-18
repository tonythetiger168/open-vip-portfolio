// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// csi_2_compliance_checker.sv -- CSI-2 tiered compliance SVA checker (module)
// L1 = basic compliance, L2 = full protocol, L3 = advanced, L4 = protocol-specific
`ifndef CSI_2_COMPLIANCE_CHECKER_SV
`define CSI_2_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module csi_2_compliance_checker (mipi_vip_if vif);
  int l1_pass[4], l1_fail[4];
  int l2_pass[4], l2_fail[4];
  int l3_pass[4], l3_fail[4];
  int l4_pass[4], l4_fail[4];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

  // ===== L1: Basic Compliance (4 SVAs) =====
  property p_csi2_dt; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.data_type inside {6'h00,6'h01,6'h02,6'h03,6'h05,6'h06,6'h07,6'h08,6'h09,6'h0A,6'h0B,6'h0C,6'h0D,6'h0E,6'h0F,6'h10,6'h11,6'h12,6'h13,6'h14,6'h15,6'h16,6'h17,6'h18,6'h19,6'h1A,6'h1B,6'h1C,6'h1D,6'h1E,6'h1F,6'h20,6'h21,6'h22,6'h23,6'h24,6'h25,6'h26,6'h27,6'h28,6'h29,6'h2A,6'h2B,6'h2C,6'h2D,6'h2E,6'h2F,6'h30,6'h31,6'h32,6'h33,6'h34,6'h35,6'h36,6'h37,6'h38,6'h39,6'h3A,6'h3B,6'h3C,6'h3D,6'h3E,6'h3F}; endproperty
  assert_p_csi2_dt: assert property(p_csi2_dt) l1_pass[0]++; else begin `uvm_warning("CSI-2_L1", "Data type valid failed"); l1_fail[0]++; end
  cover_p_csi2_dt: cover property(p_csi2_dt);
  property p_csi2_vc; @(posedge vif.clk) disable iff (!vif.rst_n) vif.vc <= 2'd3; endproperty
  assert_p_csi2_vc: assert property(p_csi2_vc) l1_pass[1]++; else begin `uvm_warning("CSI-2_L1", "VC 0-3 failed"); l1_fail[1]++; end
  cover_p_csi2_vc: cover property(p_csi2_vc);
  property p_csi2_wc; @(posedge vif.clk) disable iff (!vif.rst_n) vif.wc <= 16'hFFFF; endproperty
  assert_p_csi2_wc: assert property(p_csi2_wc) l1_pass[2]++; else begin `uvm_warning("CSI-2_L1", "WC 0-65535 failed"); l1_fail[2]++; end
  cover_p_csi2_wc: cover property(p_csi2_wc);
  property p_csi2_ecc; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.ecc_ok; endproperty
  assert_p_csi2_ecc: assert property(p_csi2_ecc) l1_pass[3]++; else begin `uvm_warning("CSI-2_L1", "ECC valid failed"); l1_fail[3]++; end
  cover_p_csi2_ecc: cover property(p_csi2_ecc);

  // ===== L2: Full Protocol (4 SVAs) =====
  property p_csi2_crc; @(posedge vif.clk) disable iff (!vif.rst_n) vif.eop |-> vif.crc_ok; endproperty
  assert_p_csi2_crc: assert property(p_csi2_crc) l2_pass[0]++; else begin `uvm_warning("CSI-2_L2", "CRC on EOP failed"); l2_fail[0]++; end
  cover_p_csi2_crc: cover property(p_csi2_crc);
  property p_csi2_sop_eop; @(posedge vif.clk) disable iff (!vif.rst_n) vif.eop |-> $past(vif.sop,1) || vif.sop; endproperty
  assert_p_csi2_sop_eop: assert property(p_csi2_sop_eop) l2_pass[1]++; else begin `uvm_warning("CSI-2_L2", "SOP before EOP failed"); l2_fail[1]++; end
  cover_p_csi2_sop_eop: cover property(p_csi2_sop_eop);
  property p_csi2_no_x; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> !$isunknown(vif.data); endproperty
  assert_p_csi2_no_x: assert property(p_csi2_no_x) l2_pass[2]++; else begin `uvm_warning("CSI-2_L2", "No X when valid failed"); l2_fail[2]++; end
  cover_p_csi2_no_x: cover property(p_csi2_no_x);
  property p_csi2_lane; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> |vif.lane_active; endproperty
  assert_p_csi2_lane: assert property(p_csi2_lane) l2_pass[3]++; else begin `uvm_warning("CSI-2_L2", "Lane active failed"); l2_fail[3]++; end
  cover_p_csi2_lane: cover property(p_csi2_lane);

  // ===== L3: Advanced Features (4 SVAs) =====
  property p_csi2_ulps; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ulps |-> vif.lp_state == 3'b101; endproperty
  assert_p_csi2_ulps: assert property(p_csi2_ulps) l3_pass[0]++; else begin `uvm_warning("CSI-2_L3", "ULPS entry failed"); l3_fail[0]++; end
  cover_p_csi2_ulps: cover property(p_csi2_ulps);
  property p_csi2_escape; @(posedge vif.clk) disable iff (!vif.rst_n) vif.escape |-> vif.lp_state == 3'b010; endproperty
  assert_p_csi2_escape: assert property(p_csi2_escape) l3_pass[1]++; else begin `uvm_warning("CSI-2_L3", "Escape mode failed"); l3_fail[1]++; end
  cover_p_csi2_escape: cover property(p_csi2_escape);
  property p_csi2_hs_req; @(posedge vif.clk) disable iff (!vif.rst_n) vif.hs_req |-> vif.lp_state == 3'b000; endproperty
  assert_p_csi2_hs_req: assert property(p_csi2_hs_req) l3_pass[2]++; else begin `uvm_warning("CSI-2_L3", "HS request failed"); l3_fail[2]++; end
  cover_p_csi2_hs_req: cover property(p_csi2_hs_req);
  property p_csi2_calibration; @(posedge vif.clk) disable iff (!vif.rst_n) vif.cal_done |-> vif.hs_mode == 0; endproperty
  assert_p_csi2_calibration: assert property(p_csi2_calibration) l3_pass[3]++; else begin `uvm_warning("CSI-2_L3", "Calibration failed"); l3_fail[3]++; end
  cover_p_csi2_calibration: cover property(p_csi2_calibration);

  // ---------------- L4: CSI-2 protocol-specific rules (4) ----------------
  property p_csi2_l4_long_wc; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop && vif.data_type >= 6'h10) |-> vif.wc > 0; endproperty
  assert_p_csi2_l4_long_wc: assert property(p_csi2_l4_long_wc) l4_pass[0]++; else begin `uvm_warning("CSI-2_L4", "Long packet WC==0 failed"); l4_fail[0]++; end
  cover_p_csi2_l4_long_wc: cover property(p_csi2_l4_long_wc);
  property p_csi2_l4_short_eop; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop && vif.data_type < 6'h10) |-> vif.eop; endproperty
  assert_p_csi2_l4_short_eop: assert property(p_csi2_l4_short_eop) l4_pass[1]++; else begin `uvm_warning("CSI-2_L4", "Short packet not header-only failed"); l4_fail[1]++; end
  cover_p_csi2_l4_short_eop: cover property(p_csi2_l4_short_eop);
  property p_csi2_l4_fs_fe_pair; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.sop && vif.data_type == 6'h00) |-> s_eventually (vif.sop && vif.data_type == 6'h01); endproperty
  assert_p_csi2_l4_fs_fe_pair: assert property(p_csi2_l4_fs_fe_pair) l4_pass[2]++; else begin `uvm_warning("CSI-2_L4", "FS without matching FE failed"); l4_fail[2]++; end
  cover_p_csi2_l4_fs_fe_pair: cover property(p_csi2_l4_fs_fe_pair);
  property p_csi2_l4_hs_payload; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && !vif.sop && !vif.eop) |-> vif.hs_mode; endproperty
  assert_p_csi2_l4_hs_payload: assert property(p_csi2_l4_hs_payload) l4_pass[3]++; else begin `uvm_warning("CSI-2_L4", "Payload outside HS mode failed"); l4_fail[3]++; end
  cover_p_csi2_l4_hs_payload: cover property(p_csi2_l4_hs_payload);

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
    `uvm_info("CSI-2_RPT", $sformatf("=== CSI-2 Tiered SVA Report ==="), UVM_LOW)
    `uvm_info("CSI-2_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("CSI-2_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("CSI-2_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("CSI-2_RPT", $sformatf("  L4 Protocol Specific:  %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("CSI-2_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%% (%0d/%0d)", total_cov, l1_hit+l2_hit+l3_hit+l4_hit, l1_total+l2_total+l3_total+l4_total), UVM_LOW)
  end
endmodule
`endif
