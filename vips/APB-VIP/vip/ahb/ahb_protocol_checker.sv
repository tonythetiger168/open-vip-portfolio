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
// AHB Protocol Checker
//============================================================================
`ifndef AHB_PROTOCOL_CHECKER_SV
`define AHB_PROTOCOL_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

// ============================================================================
// ahb_protocol_checker_sva -- SVA-carrying module form of the protocol checker
// (class-scope concurrent assertions are illegal per IEEE 1800; the SVA
//  content, counters, coverage and report output are preserved verbatim)
// ============================================================================
module ahb_protocol_checker_sva (amba_vip_if vif);

  int trans_err, burst_err, ready_err;

  initial begin
    trans_err = 0; burst_err = 0; ready_err = 0;
  end

  property p_ahb_htrans;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.hreadyout) |-> vif.htrans inside {2'b00, 2'b01, 2'b10, 2'b11};
  endproperty
  assert_ahb_trans: assert property (p_ahb_htrans)
  else begin
    `uvm_error("AHB_CHK", "Invalid HTRANS");
    trans_err++;
  end

  property p_ahb_burst;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.htrans != 2'b00) |-> vif.hburst inside {3'b000, 3'b001, 3'b010, 3'b011,
                                                   3'b100, 3'b101, 3'b110, 3'b111};
  endproperty
  assert_ahb_burst: assert property (p_ahb_burst)
  else begin
    `uvm_error("AHB_CHK", "Invalid HBURST");
    burst_err++;
  end

  property p_ahb_ready;
    @(posedge vif.aclk) disable iff (!vif.aresetn)
      (vif.htrans inside {2'b10, 2'b11}) |-> ##[1:16] vif.hreadyout;
  endproperty
  assert_ahb_ready: assert property (p_ahb_ready)
  else begin
    `uvm_error("AHB_CHK", "HREADY timeout");
    ready_err++;
  end

  covergroup cg_ahb @(posedge vif.aclk);
    option.per_instance = 1;
    cp_htrans: coverpoint vif.htrans { bins idle = {2'b00}; bins busy = {2'b01};
                                       bins nonseq = {2'b10}; bins seq = {2'b11}; }
    cp_hburst: coverpoint vif.hburst { bins single = {3'b000}; bins incr = {3'b001};
                                       bins wrap4 = {3'b010}; bins incr4 = {3'b011};
                                       bins wrap8 = {3'b100}; bins incr8 = {3'b101};
                                       bins wrap16 = {3'b110}; bins incr16 = {3'b111}; }
    cp_hsize: coverpoint vif.hsize { bins b1 = {3'b000}; bins b2 = {3'b001}; bins b4 = {3'b010};
                                     bins b8 = {3'b011}; bins b16 = {3'b100}; bins b32 = {3'b101};
                                     bins b64 = {3'b110}; bins b128 = {3'b111}; }
    cp_hwrite: coverpoint vif.hwrite { bins rd = {0}; bins wr = {1}; }
    cp_hresp: coverpoint vif.hresp { bins ok = {0}; bins err = {1}; }
    cross_trans_write: cross cp_htrans, cp_hwrite;
  endgroup

  cg_ahb cg;

  initial begin
    cg = new();
  end

  final begin
    `uvm_info("AHB_RPT", $sformatf("AHB Chk | Trans:%0d Burst:%0d Ready:%0d",
              trans_err, burst_err, ready_err), UVM_LOW)
  end
endmodule

// ============================================================================
// ahb_protocol_checker -- thin UVM shell (kept so the environment can create/start it;
// all SVA content moved to the ahb_protocol_checker_sva module above)
// ============================================================================
class ahb_protocol_checker extends uvm_component;
  `uvm_component_utils(ahb_protocol_checker)
  function new(string name = "ahb_chk", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
`endif
