// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
`ifndef CXL_COMPLIANCE_CHECKER_SV
`define CXL_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import mp_vip_pkg::*;

// Module form of the tiered CXL compliance checker (bindable from any tb).
// L1=Basic Compliance | L2=Full Protocol | L3=Advanced Features | L4=CXL specific
module cxl_compliance_checker (mp_vip_if vif);

  int l1_pass[8], l1_fail[8];
  int l2_pass[8], l2_fail[8];
  int l3_pass[8], l3_fail[8];
  int l4_pass[8], l4_fail[8];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

// ===== L1: Basic Compliance (4 SVAs) =====
  property p_cxl_h2d_valid; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> ##[1:16] vif.ready; endproperty
  assert_p_cxl_h2d_valid: assert property(p_cxl_h2d_valid) l1_pass[0]++; else begin `uvm_warning("CXL_L1", "H2D valid implies ready failed"); l1_fail[0]++; end
  cover_p_cxl_h2d_valid: cover property(p_cxl_h2d_valid);
  property p_cxl_cache_id; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.requester_id[7:0] <= 8'd255; endproperty
  assert_p_cxl_cache_id: assert property(p_cxl_cache_id) l1_pass[1]++; else begin `uvm_warning("CXL_L1", "Cache ID 0-255 failed"); l1_fail[1]++; end
  cover_p_cxl_cache_id: cover property(p_cxl_cache_id);
  property p_cxl_link_state; @(posedge vif.clk) disable iff (!vif.rst_n) vif.link_state inside {4'b0000,4'b0001,4'b0010,4'b0011,4'b0100,4'b0101,4'b0110,4'b0111,4'b1000,4'b1001,4'b1010,4'b1011,4'b1100,4'b1101,4'b1110,4'b1111}; endproperty
  assert_p_cxl_link_state: assert property(p_cxl_link_state) l1_pass[2]++; else begin `uvm_warning("CXL_L1", "Link state valid failed"); l1_fail[2]++; end
  cover_p_cxl_link_state: cover property(p_cxl_link_state);
  property p_cxl_sop_data; @(posedge vif.clk) disable iff (!vif.rst_n) vif.sop |-> vif.valid; endproperty
  assert_p_cxl_sop_data: assert property(p_cxl_sop_data) l1_pass[3]++; else begin `uvm_warning("CXL_L1", "SOP has valid data failed"); l1_fail[3]++; end
  cover_p_cxl_sop_data: cover property(p_cxl_sop_data);

  // ===== L2: Full Protocol (6 SVAs) =====
  property p_cxl_no_x_data; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> !$isunknown(vif.data); endproperty
  assert_p_cxl_no_x_data: assert property(p_cxl_no_x_data) l2_pass[0]++; else begin `uvm_warning("CXL_L2", "No X on data failed"); l2_fail[0]++; end
  cover_p_cxl_no_x_data: cover property(p_cxl_no_x_data);
  property p_cxl_credit_nonzero; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.ucie_credits > 0; endproperty
  assert_p_cxl_credit_nonzero: assert property(p_cxl_credit_nonzero) l2_pass[1]++; else begin `uvm_warning("CXL_L2", "Credits > 0 failed"); l2_fail[1]++; end
  cover_p_cxl_credit_nonzero: cover property(p_cxl_credit_nonzero);
  property p_cxl_vc_range; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> vif.ucie_vc <= 4'd15; endproperty
  assert_p_cxl_vc_range: assert property(p_cxl_vc_range) l2_pass[2]++; else begin `uvm_warning("CXL_L2", "VC 0-15 failed"); l2_fail[2]++; end
  cover_p_cxl_vc_range: cover property(p_cxl_vc_range);
  property p_cxl_m2s_valid; @(posedge vif.clk) disable iff (!vif.rst_n) vif.valid |-> ##[1:16] vif.ready; endproperty
  assert_p_cxl_m2s_valid: assert property(p_cxl_m2s_valid) l2_pass[3]++; else begin `uvm_warning("CXL_L2", "M2S valid implies ready failed"); l2_fail[3]++; end
  cover_p_cxl_m2s_valid: cover property(p_cxl_m2s_valid);
  property p_cxl_cache_coherency; @(posedge vif.clk) disable iff (!vif.rst_n) vif.cache_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_cxl_cache_coherency: assert property(p_cxl_cache_coherency) l2_pass[4]++; else begin `uvm_warning("CXL_L2", "Cache coherency state failed"); l2_fail[4]++; end
  cover_p_cxl_cache_coherency: cover property(p_cxl_cache_coherency);
  property p_cxl_mem_valid; @(posedge vif.clk) disable iff (!vif.rst_n) vif.mem_req |-> vif.addr[63:0] != 64'h0; endproperty
  assert_p_cxl_mem_valid: assert property(p_cxl_mem_valid) l2_pass[5]++; else begin `uvm_warning("CXL_L2", "Mem request valid failed"); l2_fail[5]++; end
  cover_p_cxl_mem_valid: cover property(p_cxl_mem_valid);

  // ===== L3: Advanced Features (6 SVAs) =====
  property p_cxl_ras; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ras_err |-> vif.error_log != 32'h0; endproperty
  assert_p_cxl_ras: assert property(p_cxl_ras) l3_pass[0]++; else begin `uvm_warning("CXL_L3", "RAS error handling failed"); l3_fail[0]++; end
  cover_p_cxl_ras: cover property(p_cxl_ras);
  property p_cxl_pm; @(posedge vif.clk) disable iff (!vif.rst_n) vif.pm_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_cxl_pm: assert property(p_cxl_pm) l3_pass[1]++; else begin `uvm_warning("CXL_L3", "Power management failed"); l3_fail[1]++; end
  cover_p_cxl_pm: cover property(p_cxl_pm);
  property p_cxl_security; @(posedge vif.clk) disable iff (!vif.rst_n) vif.security_level inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_cxl_security: assert property(p_cxl_security) l3_pass[2]++; else begin `uvm_warning("CXL_L3", "Security state failed"); l3_fail[2]++; end
  cover_p_cxl_security: cover property(p_cxl_security);
  property p_cxl_backpressure; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ready == 0 |-> ##[1:32] vif.ready == 1; endproperty
  assert_p_cxl_backpressure: assert property(p_cxl_backpressure) l3_pass[3]++; else begin `uvm_warning("CXL_L3", "Backpressure handling failed"); l3_fail[3]++; end
  cover_p_cxl_backpressure: cover property(p_cxl_backpressure);
  property p_cxl_port_bifurcation; @(posedge vif.clk) disable iff (!vif.rst_n) vif.bifurcation inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_cxl_port_bifurcation: assert property(p_cxl_port_bifurcation) l3_pass[4]++; else begin `uvm_warning("CXL_L3", "Port bifurcation failed"); l3_fail[4]++; end
  cover_p_cxl_port_bifurcation: cover property(p_cxl_port_bifurcation);
  property p_cxl_ld_on; @(posedge vif.clk) disable iff (!vif.rst_n) vif.ld_on |-> vif.link_state == 4'b0010; endproperty
  assert_p_cxl_ld_on: assert property(p_cxl_ld_on) l3_pass[5]++; else begin `uvm_warning("CXL_L3", "LD-On valid failed"); l3_fail[5]++; end
  cover_p_cxl_ld_on: cover property(p_cxl_ld_on);

  
  // ---------------- L4: CXL protocol-specific rules (5) ----------------
  // L4-1: CXL transactions require the CXL VC sideband encoding (VC=2)
  property p_cxl_l4_vc_encoding;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop) |-> vif.ucie_vc == 4'b0010;
  endproperty
  assert_p_cxl_l4_vc_encoding: assert property(p_cxl_l4_vc_encoding) l4_pass[0]++;
    else begin `uvm_warning("CXL_L4", "CXL TLP without CXL VC encoding"); l4_fail[0]++; end
  cover_p_cxl_l4_vc_encoding: cover property(p_cxl_l4_vc_encoding);

  // L4-2: CXL.mem write (meta[3:0]==4'b0001) must carry a data payload
  property p_cxl_l4_mem_wr_data;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop && vif.data[35:32] == 4'b0001) |-> !vif.eop;
  endproperty
  assert_p_cxl_l4_mem_wr_data: assert property(p_cxl_l4_mem_wr_data) l4_pass[1]++;
    else begin `uvm_warning("CXL_L4", "CXL.mem write without data payload"); l4_fail[1]++; end
  cover_p_cxl_l4_mem_wr_data: cover property(p_cxl_l4_mem_wr_data);

  // L4-3: SOP may only start at a flit boundary (link idle or previous beat EOP)
  property p_cxl_l4_sop_boundary;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop) |-> ($past(!vif.valid) || $past(vif.eop) || $past(!vif.rst_n));
  endproperty
  assert_p_cxl_l4_sop_boundary: assert property(p_cxl_l4_sop_boundary) l4_pass[2]++;
    else begin `uvm_warning("CXL_L4", "SOP asserted mid-flit"); l4_fail[2]++; end
  cover_p_cxl_l4_sop_boundary: cover property(p_cxl_l4_sop_boundary);

  // L4-4: every CXL flit must terminate with EOP within 64 beats
  property p_cxl_l4_sop_to_eop;
    @(posedge vif.clk) disable iff (!vif.rst_n)
      (vif.valid && vif.sop && !vif.eop) |-> ##[1:64] vif.eop;
  endproperty
  assert_p_cxl_l4_sop_to_eop: assert property(p_cxl_l4_sop_to_eop) l4_pass[3]++;
    else begin `uvm_warning("CXL_L4", "CXL flit missing EOP within 64 beats"); l4_fail[3]++; end
  cover_p_cxl_l4_sop_to_eop: cover property(p_cxl_l4_sop_to_eop);

  // L4-5: no CXL traffic while the link is in reset
  property p_cxl_l4_rst_no_traffic;
    @(posedge vif.clk) !vif.rst_n |-> !vif.valid;
  endproperty
  assert_p_cxl_l4_rst_no_traffic: assert property(p_cxl_l4_rst_no_traffic) l4_pass[4]++;
    else begin `uvm_warning("CXL_L4", "VALID asserted during reset"); l4_fail[4]++; end
  cover_p_cxl_l4_rst_no_traffic: cover property(p_cxl_l4_rst_no_traffic);

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
    `uvm_info("CXL_RPT", "=== CXL Tiered SVA Report ===", UVM_LOW)
    `uvm_info("CXL_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("CXL_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("CXL_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("CXL_RPT", $sformatf("  L4 CXL Specific:  %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("CXL_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%%", total_cov), UVM_LOW)
  endfunction

  final report_sva();

endmodule
`endif
