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
// APB Protocol Checker
//============================================================================
`ifndef APB_PROTOCOL_CHECKER_SV
`define APB_PROTOCOL_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

// ============================================================================
// apb_protocol_checker_sva -- SVA-carrying module form of the protocol checker
// (class-scope concurrent assertions are illegal per IEEE 1800; the SVA
//  content, counters, coverage and report output are preserved verbatim)
// ============================================================================
module apb_protocol_checker_sva (amba_vip_if vif);

  int setup_err, enable_err, resp_err;

  initial begin
    setup_err = 0; enable_err = 0; resp_err = 0;
  end

  property p_apb_setup;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.psel && !vif.penable) |-> ##1 vif.penable;
  endproperty
  assert_apb_setup: assert property (p_apb_setup)
  else begin
    `uvm_error("APB_CHK", "APB SETUP->ENABLE timing");
    setup_err++;
  end

  property p_apb_enable;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.penable) |-> $past(vif.psel, 1);
  endproperty
  assert_apb_enable: assert property (p_apb_enable)
  else begin
    `uvm_error("APB_CHK", "APB PENABLE without PSEL");
    enable_err++;
  end

  property p_apb_pready;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.penable) |-> ##[1:16] vif.pready;
  endproperty
  assert_apb_pready: assert property (p_apb_pready)
  else begin
    `uvm_error("APB_CHK", "APB PREADY timeout");
    resp_err++;
  end

  property p_apb_pslverr;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.pslverr) |-> vif.penable && vif.pready;
  endproperty
  assert_apb_pslverr: assert property (p_apb_pslverr)
  else begin
    `uvm_error("APB_CHK", "APB PSLVERR without enable/ready");
    resp_err++;
  end

  covergroup cg_apb @(posedge vif.aclk);
    option.per_instance = 1;
    cp_psel: coverpoint vif.psel { bins off = {0}; bins on = {1}; }
    cp_penable: coverpoint vif.penable { bins off = {0}; bins on = {1}; }
    cp_pwrite: coverpoint vif.pwrite { bins rd = {0}; bins wr = {1}; }
    cp_pprot: coverpoint vif.pprot { bins normal = {3'b000}; bins privileged = {3'b001}; bins secure = {3'b010}; }
    cp_pstrb: coverpoint vif.pstrb { bins none = {4'b0000}; bins byte0 = {4'b0001}; bins byte1 = {4'b0010};
                                     bins byte2 = {4'b0100}; bins byte3 = {4'b1000}; bins all = {4'b1111}; }
    cp_pready: coverpoint vif.pready { bins wait_s = {0}; bins ok = {1}; }
    cp_pslverr: coverpoint vif.pslverr { bins ok = {0}; bins err = {1}; }
    cross_sel_en: cross cp_psel, cp_penable;
    cross_wr_strb: cross cp_pwrite, cp_pstrb;
  endgroup

  cg_apb cg;

  initial begin
    cg = new();
  end

  final begin
    `uvm_info("APB_RPT", $sformatf("APB Chk | Setup:%0d Enable:%0d Resp:%0d",
              setup_err, enable_err, resp_err), UVM_LOW)
  end
endmodule

// ============================================================================
// apb_protocol_checker -- thin UVM shell (kept so the environment can create/start it;
// all SVA content moved to the apb_protocol_checker_sva module above)
// ============================================================================
class apb_protocol_checker extends uvm_component;
  `uvm_component_utils(apb_protocol_checker)
  function new(string name = "apb_chk", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
`endif
