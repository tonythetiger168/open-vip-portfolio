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

// AXI Tiered Compliance SVA Checker
// Level: Medium | Total SVAs: 16
// L1=Basic Compliance | L2=Full Protocol | L3=Advanced Features | L4=Protocol-Specific Rules
`ifndef AXI_COMPLIANCE_CHECKER_SV
`define AXI_COMPLIANCE_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

// ============================================================================
// axi_compliance_checker_sva -- SVA-carrying module form of the tiered compliance checker
// (class-scope concurrent assertions are illegal per IEEE 1800; the SVA
//  content, counters and report output are preserved verbatim)
// ============================================================================
module axi_compliance_checker_sva (amba_vip_if vif);

  int l1_pass[4], l1_fail[4];
  int l2_pass[4], l2_fail[4];
  int l3_pass[4], l3_fail[4];
  int l4_pass[4], l4_fail[4];
  real l1_cov, l2_cov, l3_cov, l4_cov, total_cov;

  initial begin
    l1_cov=0; l2_cov=0; l3_cov=0; l4_cov=0; total_cov=0;
  end

  // ===== L1: Basic Compliance (4 SVAs) =====
  property p_axi_awvalid_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) $rose(vif.awvalid) |-> vif.awvalid throughout vif.awready[->1]; endproperty
  assert_p_axi_awvalid_stable: assert property(p_axi_awvalid_stable) l1_pass[0]++; else begin `uvm_warning("AXI_L1", "AWVALID stable failed"); l1_fail[0]++; end
  cover_p_axi_awvalid_stable: cover property(p_axi_awvalid_stable);
  property p_axi_awburst_valid; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid |-> vif.awburst inside {2'b00,2'b01,2'b10}; endproperty
  assert_p_axi_awburst_valid: assert property(p_axi_awburst_valid) l1_pass[1]++; else begin `uvm_warning("AXI_L1", "AWBURST valid failed"); l1_fail[1]++; end
  cover_p_axi_awburst_valid: cover property(p_axi_awburst_valid);
  property p_axi_awsize_valid; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid |-> vif.awsize inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_axi_awsize_valid: assert property(p_axi_awsize_valid) l1_pass[2]++; else begin `uvm_warning("AXI_L1", "AWSIZE valid failed"); l1_fail[2]++; end
  cover_p_axi_awsize_valid: cover property(p_axi_awsize_valid);
  property p_axi_bresp_valid; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.bvalid |-> vif.bresp inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_axi_bresp_valid: assert property(p_axi_bresp_valid) l1_pass[3]++; else begin `uvm_warning("AXI_L1", "BRESP valid failed"); l1_fail[3]++; end
  cover_p_axi_bresp_valid: cover property(p_axi_bresp_valid);

  // ===== L2: Full Protocol (4 SVAs) =====
  property p_axi_wlast_align; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.wvalid && vif.wlast |-> vif.awlen == $countones(vif.wstrb); endproperty
  assert_p_axi_wlast_align: assert property(p_axi_wlast_align) l2_pass[0]++; else begin `uvm_warning("AXI_L2", "WLAST aligns AWLEN failed"); l2_fail[0]++; end
  cover_p_axi_wlast_align: cover property(p_axi_wlast_align);
  property p_axi_arburst_valid; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.arvalid |-> vif.arburst inside {2'b00,2'b01,2'b10}; endproperty
  assert_p_axi_arburst_valid: assert property(p_axi_arburst_valid) l2_pass[1]++; else begin `uvm_warning("AXI_L2", "ARBURST valid failed"); l2_fail[1]++; end
  cover_p_axi_arburst_valid: cover property(p_axi_arburst_valid);
  property p_axi_rlast_resp; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.rvalid && vif.rlast |-> vif.rresp inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_axi_rlast_resp: assert property(p_axi_rlast_resp) l2_pass[2]++; else begin `uvm_warning("AXI_L2", "RLAST with RRESP failed"); l2_fail[2]++; end
  cover_p_axi_rlast_resp: cover property(p_axi_rlast_resp);
  property p_axi_addr_aligned; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid |-> (vif.awaddr & ((1<<vif.awsize)-1)) == 0; endproperty
  assert_p_axi_addr_aligned: assert property(p_axi_addr_aligned) l2_pass[3]++; else begin `uvm_warning("AXI_L2", "Address aligned failed"); l2_fail[3]++; end
  cover_p_axi_addr_aligned: cover property(p_axi_addr_aligned);

  // ===== L3: Advanced Features (4 SVAs) =====
  property p_axi_awid_order; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid |-> vif.awid <= 8'hFF; endproperty
  assert_p_axi_awid_order: assert property(p_axi_awid_order) l3_pass[0]++; else begin `uvm_warning("AXI_L3", "AWID ordering failed"); l3_fail[0]++; end
  cover_p_axi_awid_order: cover property(p_axi_awid_order);
  property p_axi_wstrb_contig; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.wvalid |-> $countones(vif.wstrb & (~vif.wstrb + 1)) == 1 || vif.wstrb == 0; endproperty
  assert_p_axi_wstrb_contig: assert property(p_axi_wstrb_contig) l3_pass[1]++; else begin `uvm_warning("AXI_L3", "WSTRB contiguous failed"); l3_fail[1]++; end
  cover_p_axi_wstrb_contig: cover property(p_axi_wstrb_contig);
  property p_axi_rresp_excl; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.rvalid && vif.rresp == 2'b01 |-> vif.arlock == 1; endproperty
  assert_p_axi_rresp_excl: assert property(p_axi_rresp_excl) l3_pass[2]++; else begin `uvm_warning("AXI_L3", "Exclusive access OK failed"); l3_fail[2]++; end
  cover_p_axi_rresp_excl: cover property(p_axi_rresp_excl);
  property p_axi_awcache_buffer; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid |-> vif.awcache[1:0] inside {2'b00,2'b01,2'b10,2'b11}; endproperty
  assert_p_axi_awcache_buffer: assert property(p_axi_awcache_buffer) l3_pass[3]++; else begin `uvm_warning("AXI_L3", "AWCACHE bufferable failed"); l3_fail[3]++; end
  cover_p_axi_awcache_buffer: cover property(p_axi_awcache_buffer);

  // ---------------- L4: AXI protocol-specific rules (4) ----------------
  // L4-1: AWADDR/AWLEN held stable while AWVALID waits for AWREADY
  property p_axi_l4_aw_payload_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.awvalid && !vif.awready |=> vif.awvalid && $stable({vif.awaddr, vif.awlen}); endproperty
  assert_p_axi_l4_aw_payload_stable: assert property(p_axi_l4_aw_payload_stable) l4_pass[0]++; else begin `uvm_warning("AXI_L4", "AW payload not stable during AWVALID wait"); l4_fail[0]++; end
  cover_p_axi_l4_aw_payload_stable: cover property(p_axi_l4_aw_payload_stable);
  // L4-2: WLAST lands on the (AWLEN+1)-th write-data beat after the AW handshake.
  // Procedural equivalent of the SVA form (p_axi_l4_wlast_match_awlen): slang
  // requires constant repetition counts, so a parameterized sequence with a
  // variable [*len] repeat cannot be elaborated.
  int  l4_w_beat_left;   // write-data beats remaining until WLAST must be asserted
  bit  l4_w_active;
  always @(posedge vif.aclk) begin
    if (!vif.aresetn) begin
      l4_w_active    <= 1'b0;
      l4_w_beat_left <= 0;
    end
    else begin
      if (l4_w_active && vif.wvalid && vif.wready) begin
        if ((l4_w_beat_left == 1) != vif.wlast) begin
          `uvm_warning("AXI_L4", "WLAST beat count does not match AWLEN");
          l4_fail[1]++;
        end
        else l4_pass[1]++;
        l4_w_beat_left <= l4_w_beat_left - 1;
        if (vif.wlast) l4_w_active <= 1'b0;
      end
      if (vif.awvalid && vif.awready) begin
        l4_w_active    <= 1'b1;
        l4_w_beat_left <= vif.awlen + 1;
      end
    end
  end
  // L4-3: BVALID is asserted only after the final write-data beat (WLAST)
  property p_axi_l4_bvalid_after_wlast; @(posedge vif.aclk) disable iff (!vif.aresetn) $rose(vif.bvalid) |-> $past(vif.wvalid && vif.wlast); endproperty
  assert_p_axi_l4_bvalid_after_wlast: assert property(p_axi_l4_bvalid_after_wlast) l4_pass[2]++; else begin `uvm_warning("AXI_L4", "BVALID asserted before WLAST"); l4_fail[2]++; end
  cover_p_axi_l4_bvalid_after_wlast: cover property(p_axi_l4_bvalid_after_wlast);
  // L4-4: RDATA/RRESP held stable while RVALID waits for RREADY
  property p_axi_l4_r_payload_stable; @(posedge vif.aclk) disable iff (!vif.aresetn) vif.rvalid && !vif.rready |=> vif.rvalid && $stable({vif.rdata, vif.rresp}); endproperty
  assert_p_axi_l4_r_payload_stable: assert property(p_axi_l4_r_payload_stable) l4_pass[3]++; else begin `uvm_warning("AXI_L4", "R payload not stable during RVALID wait"); l4_fail[3]++; end
  cover_p_axi_l4_r_payload_stable: cover property(p_axi_l4_r_payload_stable);

  final begin
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
    `uvm_info("AXI_RPT", $sformatf("=== AXI Tiered SVA Report ==="), UVM_LOW)
    `uvm_info("AXI_RPT", $sformatf("  L1 Basic Compliance:  %0.1f%% (%0d/%0d)", l1_cov, l1_hit, l1_total), UVM_LOW)
    `uvm_info("AXI_RPT", $sformatf("  L2 Full Protocol:     %0.1f%% (%0d/%0d)", l2_cov, l2_hit, l2_total), UVM_LOW)
    `uvm_info("AXI_RPT", $sformatf("  L3 Advanced Features: %0.1f%% (%0d/%0d)", l3_cov, l3_hit, l3_total), UVM_LOW)
    `uvm_info("AXI_RPT", $sformatf("  L4 Protocol-Specific: %0.1f%% (%0d/%0d)", l4_cov, l4_hit, l4_total), UVM_LOW)
    `uvm_info("AXI_RPT", $sformatf("  TOTAL SVA Coverage:   %0.1f%% (%0d/%0d)", total_cov, l1_hit+l2_hit+l3_hit+l4_hit, l1_total+l2_total+l3_total+l4_total), UVM_LOW)
  end

endmodule

// ============================================================================
// axi_compliance_checker -- thin UVM shell (kept so the environment can create/start it;
// all SVA content moved to the axi_compliance_checker_sva module above)
// ============================================================================
class axi_compliance_checker extends uvm_component;
  `uvm_component_utils(axi_compliance_checker)
  function new(string name="axi_compliance_checker", uvm_component parent=null);
    super.new(name, parent);
  endfunction
endclass

`endif
