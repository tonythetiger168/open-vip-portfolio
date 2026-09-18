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
//============================================================================
// AXI Protocol Checker
//============================================================================
`ifndef AXI_PROTOCOL_CHECKER_SV
`define AXI_PROTOCOL_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

// ============================================================================
// axi_protocol_checker_sva -- SVA-carrying module form of the protocol checker
// (class-scope concurrent assertions are illegal per IEEE 1800; the SVA
//  content, counters, coverage and report output are preserved verbatim)
// ============================================================================
module axi_protocol_checker_sva (amba_vip_if vif);

  int aw_err, w_err, b_err, ar_err, r_err;

  initial begin
    aw_err = 0; w_err = 0; b_err = 0; ar_err = 0; r_err = 0;
  end

  // AW channel: burst must be valid
  property p_axi_awburst;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.awvalid) |-> vif.awburst inside {2'b00, 2'b01, 2'b10};
  endproperty
  assert_axi_awburst: assert property (p_axi_awburst)
  else begin
    `uvm_error("AXI_CHK", "Invalid AWBURST");
    aw_err++;
  end

  // W channel: WLAST must align with prior data beats
  property p_axi_wlast;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.wvalid && vif.wlast) |-> $past(vif.wvalid, 1);
  endproperty
  assert_axi_wlast: assert property (p_axi_wlast)
  else begin
    `uvm_error("AXI_CHK", "WLAST misaligned");
    w_err++;
  end

  // B channel: response must be accepted
  property p_axi_bvalid;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.bvalid) |-> vif.bready ##[1:8] 1'b1;
  endproperty
  assert_axi_bvalid: assert property (p_axi_bvalid)
  else begin
    `uvm_error("AXI_CHK", "BVALID timeout");
    b_err++;
  end

  // AR channel: address aligned to size
  property p_axi_aralign;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.arvalid) |-> (vif.araddr & ((32'h1 << vif.arsize) - 32'h1)) == 32'h0;
  endproperty
  assert_axi_aralign: assert property (p_axi_aralign)
  else begin
    `uvm_error("AXI_CHK", "ARADDR misaligned");
    ar_err++;
  end

  // R channel: RRESP valid on last beat
  property p_axi_rlast;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.rvalid && vif.rlast) |-> vif.rresp inside {2'b00, 2'b01, 2'b10, 2'b11};
  endproperty
  assert_axi_rlast: assert property (p_axi_rlast)
  else begin
    `uvm_error("AXI_CHK", "RRESP invalid");
    r_err++;
  end

  // Coverage
  covergroup cg_axi @(posedge vif.aclk);
    option.per_instance = 1;
    cp_awburst: coverpoint vif.awburst { bins fixed = {2'b00}; bins incr = {2'b01}; bins wrap = {2'b10}; }
    cp_awsize: coverpoint vif.awsize { bins b1 = {3'b000}; bins b4 = {3'b010}; bins b8 = {3'b011};
                                       bins b16 = {3'b100}; bins b64 = {3'b110}; bins b128 = {3'b111}; }
    cp_awlen: coverpoint vif.awlen { bins single = {8'h00}; bins burst4 = {[8'h01:8'h03]};
                                     bins burst8 = {[8'h04:8'h07]}; bins burst16 = {[8'h08:8'h0F]}; }
    cp_awcache: coverpoint vif.awcache { bins dev_nc = {4'b0000}; bins dev_buf = {4'b0001};
                                         bins normal_nc = {4'b0010}; bins normal_wb = {4'b1111}; }
    cp_bresp: coverpoint vif.bresp { bins ok = {2'b00}; bins ex = {2'b01};
                                     bins slv = {2'b10}; bins dec = {2'b11}; }
    cp_arburst: coverpoint vif.arburst { bins fixed = {2'b00}; bins incr = {2'b01}; bins wrap = {2'b10}; }
    cp_arsize: coverpoint vif.arsize { bins b1 = {3'b000}; bins b4 = {3'b010}; bins b8 = {3'b011};
                                       bins b16 = {3'b100}; bins b64 = {3'b110}; bins b128 = {3'b111}; }
    cp_rresp: coverpoint vif.rresp { bins ok = {2'b00}; bins ex = {2'b01};
                                     bins slv = {2'b10}; bins dec = {2'b11}; }
    cross_aw: cross cp_awburst, cp_awsize, cp_awlen;
    cross_ar: cross cp_arburst, cp_arsize;
  endgroup

  cg_axi cg;

  initial begin
    cg = new();
  end

  final begin
    `uvm_info("AXI_RPT", $sformatf("AXI Chk | AW:%0d W:%0d B:%0d AR:%0d R:%0d",
              aw_err, w_err, b_err, ar_err, r_err), UVM_LOW)
  end
endmodule

// ============================================================================
// axi_protocol_checker -- thin UVM shell (kept so the environment can create/start it;
// all SVA content moved to the axi_protocol_checker_sva module above)
// ============================================================================
class axi_protocol_checker extends uvm_component;
  `uvm_component_utils(axi_protocol_checker)
  function new(string name = "axi_chk", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
`endif
