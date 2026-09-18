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

// LPDDR7 Error Handling Checker (L3)
// UVM component handle (env hookup) + companion SVA module lpddr7_error_sva
// (concurrent assertions live in the module; LRM does not allow
//  property declarations inside classes).
`ifndef LPDDR7_ERROR_CHECKER_SV
`define LPDDR7_ERROR_CHECKER_SV
class lpddr7_error_checker extends uvm_component;
  `uvm_component_utils(lpddr7_error_checker)
  virtual lpddr7_if vif;
  function new(string name="lpddr7_error_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr7_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "LPDDR7: vif not found"); endfunction
endclass

// SVA rule module -- instantiated from tb/tb_top.sv
module lpddr7_error_sva(lpddr7_if vif);
`include "uvm_macros.svh"
  property p_lpddr7_pm; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pm_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_lpddr7_pm: assert property(p_lpddr7_pm) else `uvm_warning("LPDDR7", "Power management failed");
  cover_p_lpddr7_pm: cover property(p_lpddr7_pm);
  property p_lpddr7_refresh; @(posedge vif.ck) disable iff (!vif.rst_n) vif.refresh |-> ##[1:3900] vif.cs_n == 0; endproperty
  assert_p_lpddr7_refresh: assert property(p_lpddr7_refresh) else `uvm_warning("LPDDR7", "Refresh interval failed");
  cover_p_lpddr7_refresh: cover property(p_lpddr7_refresh);
  property p_lpddr7_vrefca; @(posedge vif.ck) disable iff (!vif.rst_n) vif.vrefca_train |-> vif.cs_n == 0; endproperty
  assert_p_lpddr7_vrefca: assert property(p_lpddr7_vrefca) else `uvm_warning("LPDDR7", "VrefCA training failed");
  cover_p_lpddr7_vrefca: cover property(p_lpddr7_vrefca);
  property p_lpddr7_temp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp_sensor <= 8'd127; endproperty
  assert_p_lpddr7_temp: assert property(p_lpddr7_temp) else `uvm_warning("LPDDR7", "Temperature failed");
  cover_p_lpddr7_temp: cover property(p_lpddr7_temp);
  property p_lpddr7_wck2ck; @(posedge vif.ck) disable iff (!vif.rst_n) vif.wck2ck_train |-> vif.wck_ratio > 0; endproperty
  assert_p_lpddr7_wck2ck: assert property(p_lpddr7_wck2ck) else `uvm_warning("LPDDR7", "WCK2CK training failed");
  cover_p_lpddr7_wck2ck: cover property(p_lpddr7_wck2ck);
  property p_lpddr7_rdqs; @(posedge vif.ck) disable iff (!vif.rst_n) vif.rdqs == 1 |-> vif.cs_n == 0; endproperty
  assert_p_lpddr7_rdqs: assert property(p_lpddr7_rdqs) else `uvm_warning("LPDDR7", "RDQS valid failed");
  cover_p_lpddr7_rdqs: cover property(p_lpddr7_rdqs);
  property p_lpddr7_bw; @(posedge vif.ck) disable iff (!vif.rst_n) vif.bandwidth <= 32'hFFFFFFFF; endproperty
  assert_p_lpddr7_bw: assert property(p_lpddr7_bw) else `uvm_warning("LPDDR7", "Bandwidth failed");
  cover_p_lpddr7_bw: cover property(p_lpddr7_bw);
  property p_lpddr7_latency; @(posedge vif.ck) disable iff (!vif.rst_n) vif.latency_target <= 8'd127; endproperty
  assert_p_lpddr7_latency: assert property(p_lpddr7_latency) else `uvm_warning("LPDDR7", "Latency target failed");
  cover_p_lpddr7_latency: cover property(p_lpddr7_latency);
endmodule
`endif
