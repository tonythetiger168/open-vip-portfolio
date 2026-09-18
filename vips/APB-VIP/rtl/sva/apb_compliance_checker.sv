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

// APB Tiered Compliance SVA Checker
// Level: Simple | Total SVAs: 14
// L1=Basic Compliance | L2=Full Protocol | L3=Advanced Features
`ifndef APB_COMPLIANCE_CHECKER_SV
`define APB_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

// ============================================================================
// apb_compliance_checker_sva -- SVA-carrying module form of the tiered compliance checker
// (class-scope concurrent assertions are illegal per IEEE 1800; the SVA
//  content, counters and report output are preserved verbatim)
// ============================================================================
module apb_compliance_checker_sva (amba_vip_if vif);

  int l1_pass[4], l1_fail[4];
  int l2_pass[2], l2_fail[2];
  int l3_pass[4], l3_fail[4];
  int l4_pass[4], l4_fail[4];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

  initial begin
    l1_cov = 0; l2_cov = 0; l3_cov = 0; l4_cov = 0; total_cov = 0;
  end

  // ===== L1: Basic Compliance (4 SVAs) =====
  property p_apb_psel_setup; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.psel |-> ##1 vif.penable; endproperty
  assert_p_apb_psel_setup: assert property(p_apb_psel_setup) l1_pass[0]++; else begin `uvm_warning("APB_L1", "PSEL then PENABLE failed"); l1_fail[0]++; end
  cover_p_apb_psel_setup: cover property(p_apb_psel_setup);
  property p_apb_penable_1cycle; @(posedge vif.aclk) disable iff (!vif.aresetn) $rose(vif.penable) |-> ##1 !vif.penable; endproperty
  assert_p_apb_penable_1cycle: assert property(p_apb_penable_1cycle) l1_pass[1]++; else begin `uvm_warning("APB_L1", "PENABLE single cycle failed"); l1_fail[1]++; end
  cover_p_apb_penable_1cycle: cover property(p_apb_penable_1cycle);
  property p_apb_pwrite_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.psel |-> $stable(vif.pwrite); endproperty
  assert_p_apb_pwrite_stable: assert property(p_apb_pwrite_stable) l1_pass[2]++; else begin `uvm_warning("APB_L1", "PWRITE stable failed"); l1_fail[2]++; end
  cover_p_apb_pwrite_stable: cover property(p_apb_pwrite_stable);
  property p_apb_paddr_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.psel |-> $stable(vif.paddr); endproperty
  assert_p_apb_paddr_stable: assert property(p_apb_paddr_stable) l1_pass[3]++; else begin `uvm_warning("APB_L1", "PADDR stable failed"); l1_fail[3]++; end
  cover_p_apb_paddr_stable: cover property(p_apb_paddr_stable);

  // ===== L2: Full Protocol (2 SVAs) =====
  property p_apb_pwdata_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.psel && vif.pwrite |-> $stable(vif.pwdata); endproperty
  assert_p_apb_pwdata_stable: assert property(p_apb_pwdata_stable) l2_pass[0]++; else begin `uvm_warning("APB_L2", "PWDATA stable on write failed"); l2_fail[0]++; end
  cover_p_apb_pwdata_stable: cover property(p_apb_pwdata_stable);
  property p_apb_pready_resp; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.penable |-> ##[0:16] vif.pready; endproperty
  assert_p_apb_pready_resp: assert property(p_apb_pready_resp) l2_pass[1]++; else begin `uvm_warning("APB_L2", "PREADY response failed"); l2_fail[1]++; end
  cover_p_apb_pready_resp: cover property(p_apb_pready_resp);

  // ===== L3: Advanced Features (4 SVAs) =====
  // L3-1: after a completed transfer, PSEL either drops or a back-to-back SETUP starts
  property p_apb_l3_b2b_setup;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && vif.penable && vif.pready) |=> (!vif.psel || !vif.penable);
  endproperty
  assert_p_apb_l3_b2b_setup: assert property(p_apb_l3_b2b_setup) l3_pass[0]++;
    else begin `uvm_warning("APB_L3", "No IDLE or SETUP after completed transfer"); l3_fail[0]++; end
  cover_p_apb_l3_b2b_setup: cover property(p_apb_l3_b2b_setup);

  // L3-2: write data must be known throughout the ACCESS phase
  property p_apb_l3_wdata_known;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && vif.penable && vif.pwrite) |-> !$isunknown(vif.pwdata);
  endproperty
  assert_p_apb_l3_wdata_known: assert property(p_apb_l3_wdata_known) l3_pass[1]++;
    else begin `uvm_warning("APB_L3", "PWDATA unknown during ACCESS"); l3_fail[1]++; end
  cover_p_apb_l3_wdata_known: cover property(p_apb_l3_wdata_known);

  // L3-3: PSTRB must be all-zero during read transfers
  property p_apb_l3_strb_read;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && vif.penable && !vif.pwrite) |-> (vif.pstrb == 4'h0);
  endproperty
  assert_p_apb_l3_strb_read: assert property(p_apb_l3_strb_read) l3_pass[2]++;
    else begin `uvm_warning("APB_L3", "PSTRB nonzero during read"); l3_fail[2]++; end
  cover_p_apb_l3_strb_read: cover property(p_apb_l3_strb_read);

  // L3-4: PREADY may only be asserted in the ACCESS phase
  property p_apb_l3_ready_window;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      vif.pready |-> (vif.psel && vif.penable);
  endproperty
  assert_p_apb_l3_ready_window: assert property(p_apb_l3_ready_window) l3_pass[3]++;
    else begin `uvm_warning("APB_L3", "PREADY outside ACCESS phase"); l3_fail[3]++; end
  cover_p_apb_l3_ready_window: cover property(p_apb_l3_ready_window);

  // ---------------- L4: APB4 protocol-specific rules (4) ----------------
  // L4-1: PENABLE may only be asserted while PSEL is asserted
  property p_apb_l4_en_needs_sel;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      vif.penable |-> vif.psel;
  endproperty
  assert_p_apb_l4_en_needs_sel: assert property(p_apb_l4_en_needs_sel) l4_pass[0]++;
    else begin `uvm_warning("APB_L4", "PENABLE without PSEL"); l4_fail[0]++; end
  cover_p_apb_l4_en_needs_sel: cover property(p_apb_l4_en_needs_sel);

  // L4-2: PSLVERR is only valid in the last cycle of an access (PSEL&PENABLE&PREADY)
  property p_apb_l4_err_window;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      vif.pslverr |-> (vif.psel && vif.penable && vif.pready);
  endproperty
  assert_p_apb_l4_err_window: assert property(p_apb_l4_err_window) l4_pass[1]++;
    else begin `uvm_warning("APB_L4", "PSLVERR outside access completion"); l4_fail[1]++; end
  cover_p_apb_l4_err_window: cover property(p_apb_l4_err_window);

  // L4-3: control signals stable throughout the whole access phase
  property p_apb_l4_access_stable;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && vif.penable && !vif.pready) |=>
      $stable({vif.paddr, vif.pwrite, vif.pwdata, vif.pstrb, vif.pprot});
  endproperty
  assert_p_apb_l4_access_stable: assert property(p_apb_l4_access_stable) l4_pass[2]++;
    else begin `uvm_warning("APB_L4", "Control changed during wait-stated access"); l4_fail[2]++; end
  cover_p_apb_l4_access_stable: cover property(p_apb_l4_access_stable);

  // L4-4: transfer completes with PENABLE deasserted or back-to-back SETUP
  property p_apb_l4_next_state;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && vif.penable && vif.pready) |=> !vif.penable;
  endproperty
  assert_p_apb_l4_next_state: assert property(p_apb_l4_next_state) l4_pass[3]++;
    else begin `uvm_warning("APB_L4", "PENABLE not deasserted after transfer"); l4_fail[3]++; end
  cover_p_apb_l4_next_state: cover property(p_apb_l4_next_state);

  final begin
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
    total_cov = (l1_total+l2_total+l3_total+l4_total>0) ?
                ((l1_hit+l2_hit+l3_hit+l4_hit)*100.0/(l1_total+l2_total+l3_total+l4_total)) : 0;
    `uvm_info("APB_RPT", $sformatf("=== APB Tiered SVA Report ==="), UVM_LOW)
    `uvm_info("APB_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("APB_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("APB_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("APB_RPT", $sformatf("  L4 Protocol-Specific: %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("APB_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%% (%0d/%0d)", total_cov,
              l1_hit+l2_hit+l3_hit+l4_hit, l1_total+l2_total+l3_total+l4_total), UVM_LOW)
  end
endmodule

// ============================================================================
// apb_compliance_checker -- thin UVM shell (kept so the environment can create/start it;
// all SVA content moved to the apb_compliance_checker_sva module above)
// ============================================================================
class apb_compliance_checker extends uvm_component;
  `uvm_component_utils(apb_compliance_checker)
  function new(string name = "apb_compliance_checker", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass

`endif
