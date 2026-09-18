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

// LPDDR6 Timing Performance Checker (L2)
// UVM component handle (env hookup) + companion SVA module lpddr6_timing_sva
// (concurrent assertions live in the module; LRM does not allow
//  property declarations inside classes).
`ifndef LPDDR6_TIMING_CHECKER_SV
`define LPDDR6_TIMING_CHECKER_SV
class lpddr6_timing_checker extends uvm_component;
  `uvm_component_utils(lpddr6_timing_checker)
  virtual lpddr6_if vif;
  function new(string name="lpddr6_timing_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr6_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "LPDDR6: vif not found"); endfunction
endclass

// SVA rule module -- instantiated from tb/tb_top.sv
module lpddr6_timing_sva(lpddr6_if vif);
`include "uvm_macros.svh"
  property p_lpddr6_tRCD; @(posedge vif.ck) disable iff (!vif.rst_n) $fell(vif.cs_n) |-> ##[6:10] vif.ca[4] == 0; endproperty
  assert_p_lpddr6_tRCD: assert property(p_lpddr6_tRCD) else `uvm_warning("LPDDR6_TIM", "tRCD 6-10 cycles violated");
  cover_p_lpddr6_tRCD: cover property(p_lpddr6_tRCD);
  property p_lpddr6_tRP; @(posedge vif.ck) disable iff (!vif.rst_n) $rose(vif.cs_n) |-> ##[6:10] $fell(vif.cs_n); endproperty
  assert_p_lpddr6_tRP: assert property(p_lpddr6_tRP) else `uvm_warning("LPDDR6_TIM", "tRP 6-10 cycles violated");
  cover_p_lpddr6_tRP: cover property(p_lpddr6_tRP);
endmodule
`endif
