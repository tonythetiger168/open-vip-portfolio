// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
`ifndef PCIE_COMPLIANCE_CHECKER_SV
`define PCIE_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import mp_vip_pkg::*;

// Module form of the tiered PCIe compliance checker (bindable from any tb).
// L1=Basic Compliance | L2=Full Protocol | L3=Advanced Features | L4=PCIe specific
module pcie_compliance_checker (mp_vip_if vif);

  int l1_pass[8], l1_fail[8];
  int l2_pass[8], l2_fail[8];
  int l3_pass[8], l3_fail[8];
  int l4_pass[8], l4_fail[8];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

// ===== L1: Basic Compliance (4 SVAs) =====
  property p_pcie_tlp_fmt; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop) |-> vif.data[31:29] inside {3'b000,3'b001,3'b010,3'b100,3'b101,3'b110}; endproperty
  assert_p_pcie_tlp_fmt: assert property(p_pcie_tlp_fmt) l1_pass[0]++; else begin `uvm_warning("PCIE_L1", "TLP FMT valid failed"); l1_fail[0]++; end
  cover_p_pcie_tlp_fmt: cover property(p_pcie_tlp_fmt);
  property p_pcie_tlp_type; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop) |-> vif.data[28:24] inside {5'b00000,5'b00001,5'b00010,5'b00100,5'b01010,5'b01011,5'b01100,5'b01101,5'b10000,5'b10001,5'b10010,5'b10100,5'b10101,5'b10111,5'b11000,5'b11001,5'b11010,5'b11011,5'b11101,5'b11110,5'b11111}; endproperty
  assert_p_pcie_tlp_type: assert property(p_pcie_tlp_type) l1_pass[1]++; else begin `uvm_warning("PCIE_L1", "TLP TYPE valid failed"); l1_fail[1]++; end
  cover_p_pcie_tlp_type: cover property(p_pcie_tlp_type);
  property p_pcie_tag_range; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop) |-> vif.tag <= 8'd255; endproperty
  assert_p_pcie_tag_range: assert property(p_pcie_tag_range) l1_pass[2]++; else begin `uvm_warning("PCIE_L1", "TAG 0-255 failed"); l1_fail[2]++; end
  cover_p_pcie_tag_range: cover property(p_pcie_tag_range);
  property p_pcie_tc_range; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop) |-> vif.tc inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_pcie_tc_range: assert property(p_pcie_tc_range) l1_pass[3]++; else begin `uvm_warning("PCIE_L1", "TC 0-7 failed"); l1_fail[3]++; end
  cover_p_pcie_tc_range: cover property(p_pcie_tc_range);

  // ===== L2: Full Protocol (8 SVAs) =====
  property p_pcie_length_dw; @(posedge vif.clk) disable iff (!vif.rst_n) (vif.valid && vif.sop) |-> vif.length_dw > 10'd0; endproperty
  assert_p_pcie_length_dw: assert property(p_pcie_length_dw) l2_pass[0]++; else begin `uvm_warning("PCIE_L2", "Length DW > 0 failed"); l2_fail[0]++; end
  cover_p_pcie_length_dw: cover property(p_pcie_length_dw);
  property p_pcie_sop_eop; @(posedge vif.clk) disable iff (!vif.rst_n) $rose(vif.eop) |-> $past(vif.sop,1); endproperty
  assert_p_pcie_sop_eop: assert property(p_pcie_sop_eop) l2_pass[1]++; else begin `uvm_warning("PCIE_L2", "SOP before EOP failed"); l2_fail[1]++; end
  cover_p_pcie_sop_eop: cover property(p_pcie_sop_eop);
  property p_pcie_link_up; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.link_up; endproperty
  assert_p_pcie_link_up: assert property(p_pcie_link_up) l2_pass[2]++; else begin `uvm_warning("PCIE_L2", "Link up before traffic failed"); l2_fail[2]++; end
  cover_p_pcie_link_up: cover property(p_pcie_link_up);
  property p_pcie_err_poison; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ep |-> vif.valid; endproperty
  assert_p_pcie_err_poison: assert property(p_pcie_err_poison) l2_pass[3]++; else begin `uvm_warning("PCIE_L2", "EP only with valid failed"); l2_fail[3]++; end
  cover_p_pcie_err_poison: cover property(p_pcie_err_poison);
  property p_pcie_completion_timeout; @(posedge vif.clk) disable iff (!vif.rst_n) vif.tlp_type == 5'b01010 |-> ##[1:1000] vif.completion_valid; endproperty
  assert_p_pcie_completion_timeout: assert property(p_pcie_completion_timeout) l2_pass[4]++; else begin `uvm_warning("PCIE_L2", "Completion timeout failed"); l2_fail[4]++; end
  cover_p_pcie_completion_timeout: cover property(p_pcie_completion_timeout);
  property p_pcie_fc_credit; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.fc_credit > 0; endproperty
  assert_p_pcie_fc_credit: assert property(p_pcie_fc_credit) l2_pass[5]++; else begin `uvm_warning("PCIE_L2", "Flow control credit failed"); l2_fail[5]++; end
  cover_p_pcie_fc_credit: cover property(p_pcie_fc_credit);
  property p_pcie_max_payload; @(posedge vif.clk) disable iff (!vif.rst_n) vif.length_dw <= 11'd1024; endproperty
  assert_p_pcie_max_payload: assert property(p_pcie_max_payload) l2_pass[6]++; else begin `uvm_warning("PCIE_L2", "Max payload 128B-4KB failed"); l2_fail[6]++; end
  cover_p_pcie_max_payload: cover property(p_pcie_max_payload);
  property p_pcie_vendor_id; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.requester_id != 16'h0000; endproperty
  assert_p_pcie_vendor_id: assert property(p_pcie_vendor_id) l2_pass[7]++; else begin `uvm_warning("PCIE_L2", "Vendor ID non-zero failed"); l2_fail[7]++; end
  cover_p_pcie_vendor_id: cover property(p_pcie_vendor_id);

  // ===== L3: Advanced Features (8 SVAs) =====
  property p_pcie_pm_l0s; @(posedge vif.clk) disable iff (!vif.rst_n) vif.pm_state == 3'b001 |-> vif.link_up == 0; endproperty
  assert_p_pcie_pm_l0s: assert property(p_pcie_pm_l0s) l3_pass[0]++; else begin `uvm_warning("PCIE_L3", "L0s entry valid failed"); l3_fail[0]++; end
  cover_p_pcie_pm_l0s: cover property(p_pcie_pm_l0s);
  property p_pcie_pm_l1; @(posedge vif.clk) disable iff (!vif.rst_n) vif.pm_state == 3'b010 |-> vif.link_up == 0 && vif.idle_count > 0; endproperty
  assert_p_pcie_pm_l1: assert property(p_pcie_pm_l1) l3_pass[1]++; else begin `uvm_warning("PCIE_L3", "L1 entry valid failed"); l3_fail[1]++; end
  cover_p_pcie_pm_l1: cover property(p_pcie_pm_l1);
  property p_pcie_ecrc; @(posedge vif.clk) disable iff (!vif.rst_n) vif.td == 1 |-> vif.ecrc != 32'h00000000; endproperty
  assert_p_pcie_ecrc: assert property(p_pcie_ecrc) l3_pass[2]++; else begin `uvm_warning("PCIE_L3", "ECRC valid failed"); l3_fail[2]++; end
  cover_p_pcie_ecrc: cover property(p_pcie_ecrc);
  property p_pcie_replay; @(posedge vif.clk) disable iff (!vif.rst_n) vif.nak_received |-> ##[1:32] vif.replay_valid; endproperty
  assert_p_pcie_replay: assert property(p_pcie_replay) l3_pass[3]++; else begin `uvm_warning("PCIE_L3", "Replay buffer failed"); l3_fail[3]++; end
  cover_p_pcie_replay: cover property(p_pcie_replay);
  property p_pcie_ltssm_recovery; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ltssm_state == 4'b1011 |-> vif.link_up == 0; endproperty
  assert_p_pcie_ltssm_recovery: assert property(p_pcie_ltssm_recovery) l3_pass[4]++; else begin `uvm_warning("PCIE_L3", "Recovery from error failed"); l3_fail[4]++; end
  cover_p_pcie_ltssm_recovery: cover property(p_pcie_ltssm_recovery);
  property p_pcie_aspm; @(posedge vif.clk) disable iff (!vif.rst_n) vif.aspm_state inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_pcie_aspm: assert property(p_pcie_aspm) l3_pass[5]++; else begin `uvm_warning("PCIE_L3", "ASPM L0s/L1 valid failed"); l3_fail[5]++; end
  cover_p_pcie_aspm: cover property(p_pcie_aspm);
  property p_pcie_drs; @(posedge vif.clk) disable iff (!vif.rst_n) vif.drs_msg |-> vif.link_speed >= 3'b010; endproperty
  assert_p_pcie_drs: assert property(p_pcie_drs) l3_pass[6]++; else begin `uvm_warning("PCIE_L3", "DRS message valid failed"); l3_fail[6]++; end
  cover_p_pcie_drs: cover property(p_pcie_drs);
  property p_pcie_parity; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> ^vif.data != 1'bx; endproperty
  assert_p_pcie_parity: assert property(p_pcie_parity) l3_pass[7]++; else begin `uvm_warning("PCIE_L3", "Parity check failed"); l3_fail[7]++; end
  cover_p_pcie_parity: cover property(p_pcie_parity);

  
  // ---------------- L4: PCIe protocol-specific rules (5) ----------------
  // L4-1: EOP may only be asserted together with VALID
  property p_pcie_l4_eop_valid;
    @(posedge vif.clk) disable iff (!vif.rst_n) vif.eop |-> vif.valid;
  endproperty
  assert_p_pcie_l4_eop_valid: assert property(p_pcie_l4_eop_valid) l4_pass[0]++;
    else begin `uvm_warning("PCIE_L4", "EOP without VALID"); l4_fail[0]++; end
  cover_p_pcie_l4_eop_valid: cover property(p_pcie_l4_eop_valid);

  // L4-2: SOP may only start at a TLP boundary (link idle or previous beat was EOP)
  property p_pcie_l4_sop_boundary;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop) |-> ($past(!vif.valid) || $past(vif.eop) || $past(!vif.rst_n));
  endproperty
  assert_p_pcie_l4_sop_boundary: assert property(p_pcie_l4_sop_boundary) l4_pass[1]++;
    else begin `uvm_warning("PCIE_L4", "SOP asserted mid-TLP"); l4_fail[1]++; end
  cover_p_pcie_l4_sop_boundary: cover property(p_pcie_l4_sop_boundary);

  // L4-3: a continuation beat (VALID without SOP) must follow an in-flight TLP
  property p_pcie_l4_cont_beat;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && !vif.sop) |-> $past(vif.valid && !vif.eop);
  endproperty
  assert_p_pcie_l4_cont_beat: assert property(p_pcie_l4_cont_beat) l4_pass[2]++;
    else begin `uvm_warning("PCIE_L4", "continuation beat without active TLP"); l4_fail[2]++; end
  cover_p_pcie_l4_cont_beat: cover property(p_pcie_l4_cont_beat);

  // L4-4: every SOP must be followed by EOP within 64 beats (no unbounded TLP)
  property p_pcie_l4_sop_to_eop;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop && !vif.eop) |-> ##[1:64] vif.eop;
  endproperty
  assert_p_pcie_l4_sop_to_eop: assert property(p_pcie_l4_sop_to_eop) l4_pass[3]++;
    else begin `uvm_warning("PCIE_L4", "TLP missing EOP within 64 beats"); l4_fail[3]++; end
  cover_p_pcie_l4_sop_to_eop: cover property(p_pcie_l4_sop_to_eop);

  // L4-5: no traffic may be driven while the link is in reset
  property p_pcie_l4_rst_no_traffic;
    @(posedge vif.clk) !vif.rst_n |-> !vif.valid;
  endproperty
  assert_p_pcie_l4_rst_no_traffic: assert property(p_pcie_l4_rst_no_traffic) l4_pass[4]++;
    else begin `uvm_warning("PCIE_L4", "VALID asserted during reset"); l4_fail[4]++; end
  cover_p_pcie_l4_rst_no_traffic: cover property(p_pcie_l4_rst_no_traffic);

  function void report_sva();
    int l1_total=0, l2_total=0, l3_total=0, l4_total=0;
    int l1_hit=0, l2_hit=0, l3_hit=0, l4_hit=0;
    foreach(l1_pass[i]) begin l1_total++; if(l1_pass[i]>0) l1_hit++; end
    foreach(l2_pass[i]) begin l2_total++; if(l2_pass[i]>0) l2_hit++; end
    foreach(l3_pass[i]) begin l3_total++; if(l3_pass[i]>0) l3_hit++; end
    foreach(l4_pass[i]) begin l4_total++; if(l4_pass[i]>0) l4_hit++; end
    l1_cov = (l1_total>0) ? (l1_hit*100.0/l1_total) : 0;
    l2_cov = (l2_total>0) ? (l2_hit*100.0/l2_total) : 0;
    l3_cov = (l3_total>0) ? (l3_hit*100.0/l3_total) : 0;
    l4_cov = (l4_total>0) ? (l4_hit*100.0/l4_total) : 0;
    total_cov = ((l1_hit+l2_hit+l3_hit+l4_hit)*100.0)/(l1_total+l2_total+l3_total+l4_total);
    `uvm_info("PCIE_RPT", "=== PCIe Tiered SVA Report ===", UVM_LOW)
    `uvm_info("PCIE_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("PCIE_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("PCIE_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("PCIE_RPT", $sformatf("  L4 PCIe Specific:  %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("PCIE_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%%", total_cov), UVM_LOW)
  endfunction

  final report_sva();

endmodule
`endif
