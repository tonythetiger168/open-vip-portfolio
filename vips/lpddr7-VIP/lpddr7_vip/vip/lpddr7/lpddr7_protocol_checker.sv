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

// LPDDR7 Protocol Compliance Checker (L1)
// UVM component handle (env hookup) + companion SVA module lpddr7_protocol_sva
// (concurrent assertions live in the module; LRM does not allow
//  property declarations inside classes).
`ifndef LPDDR7_PROTOCOL_CHECKER_SV
`define LPDDR7_PROTOCOL_CHECKER_SV
class lpddr7_protocol_checker extends uvm_component;
  `uvm_component_utils(lpddr7_protocol_checker)
  virtual lpddr7_if vif;
  function new(string name="lpddr7_protocol_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr7_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "LPDDR7: vif not found"); endfunction
endclass

// SVA rule module -- instantiated from tb/tb_top.sv
module lpddr7_protocol_sva(lpddr7_if vif);
`include "uvm_macros.svh"
  property p_lpddr7_cmd_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.ca); endproperty
  assert_p_lpddr7_cmd_valid: assert property(p_lpddr7_cmd_valid) else `uvm_warning("LPDDR7", "Command valid failed");
  cover_p_lpddr7_cmd_valid: cover property(p_lpddr7_cmd_valid);
  property p_lpddr7_addr_valid; @(posedge vif.ck) disable iff (!vif.rst_n) vif.cs_n == 0 |-> !$isunknown(vif.addr); endproperty
  assert_p_lpddr7_addr_valid: assert property(p_lpddr7_addr_valid) else `uvm_warning("LPDDR7", "Address valid failed");
  cover_p_lpddr7_addr_valid: cover property(p_lpddr7_addr_valid);
  property p_lpddr7_bg; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bg <= 3'd7; endproperty
  assert_p_lpddr7_bg: assert property(p_lpddr7_bg) else `uvm_warning("LPDDR7", "Bank group 0-7 failed");
  cover_p_lpddr7_bg: cover property(p_lpddr7_bg);
  property p_lpddr7_ba; @(posedge vif.ck) disable iff (!vif.rst_n) vif.ba <= 2'd3; endproperty
  assert_p_lpddr7_ba: assert property(p_lpddr7_ba) else `uvm_warning("LPDDR7", "Bank address 0-3 failed");
  cover_p_lpddr7_ba: cover property(p_lpddr7_ba);
endmodule
`endif
