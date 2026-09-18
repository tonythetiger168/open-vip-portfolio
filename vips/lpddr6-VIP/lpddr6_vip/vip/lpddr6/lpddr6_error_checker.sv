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

// LPDDR6 Error Handling Checker (L3)
// UVM component handle (env hookup) + companion SVA module lpddr6_error_sva
// (concurrent assertions live in the module; LRM does not allow
//  property declarations inside classes).
`ifndef LPDDR6_ERROR_CHECKER_SV
`define LPDDR6_ERROR_CHECKER_SV
class lpddr6_error_checker extends uvm_component;
  `uvm_component_utils(lpddr6_error_checker)
  virtual lpddr6_if vif;
  function new(string name="lpddr6_error_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr6_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "LPDDR6: vif not found"); endfunction
endclass

// SVA rule module -- instantiated from tb/tb_top.sv
module lpddr6_error_sva(lpddr6_if vif);
`include "uvm_macros.svh"
  property p_lpddr6_pm; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pm_state inside {3'b000,3'b001,3'b010,3'b011,3'b100,3'b101,3'b110,3'b111}; endproperty
  assert_p_lpddr6_pm: assert property(p_lpddr6_pm) else `uvm_warning("LPDDR6_L3", "Power management failed");
  cover_p_lpddr6_pm: cover property(p_lpddr6_pm);
  property p_lpddr6_refresh; @(posedge vif.ck) disable iff (!vif.rst_n) vif.refresh |-> ##[1:3900] vif.cs_n == 0; endproperty
  assert_p_lpddr6_refresh: assert property(p_lpddr6_refresh) else `uvm_warning("LPDDR6_L3", "Refresh interval failed");
  cover_p_lpddr6_refresh: cover property(p_lpddr6_refresh);
  property p_lpddr6_vrefca; @(posedge vif.ck) disable iff (!vif.rst_n) vif.vrefca_train |-> vif.cs_n == 0; endproperty
  assert_p_lpddr6_vrefca: assert property(p_lpddr6_vrefca) else `uvm_warning("LPDDR6_L3", "VrefCA training failed");
  cover_p_lpddr6_vrefca: cover property(p_lpddr6_vrefca);
  property p_lpddr6_temp; @(posedge vif.ck) disable iff (!vif.rst_n) vif.temp_sensor <= 8'd127; endproperty
  assert_p_lpddr6_temp: assert property(p_lpddr6_temp) else `uvm_warning("LPDDR6_L3", "Temperature sensor failed");
  cover_p_lpddr6_temp: cover property(p_lpddr6_temp);
  property p_lpddr6_wck2ck; @(posedge vif.ck) disable iff (!vif.rst_n) vif.wck2ck_train |-> vif.wck_ratio > 0; endproperty
  assert_p_lpddr6_wck2ck: assert property(p_lpddr6_wck2ck) else `uvm_warning("LPDDR6_L3", "WCK2CK training failed");
  cover_p_lpddr6_wck2ck: cover property(p_lpddr6_wck2ck);
  property p_lpddr6_rdqs; @(posedge vif.ck) disable iff (!vif.rst_n) vif.rdqs == 1 |-> vif.cs_n == 0; endproperty
  assert_p_lpddr6_rdqs: assert property(p_lpddr6_rdqs) else `uvm_warning("LPDDR6_L3", "RDQS valid failed");
  cover_p_lpddr6_rdqs: cover property(p_lpddr6_rdqs);
  property p_lpddr6_pam4; @(posedge vif.ck) disable iff (!vif.rst_n) vif.pam4_en |-> vif.data_width == 5'b10000; endproperty
  assert_p_lpddr6_pam4: assert property(p_lpddr6_pam4) else `uvm_warning("LPDDR6_L3", "PAM4 mode failed");
  cover_p_lpddr6_pam4: cover property(p_lpddr6_pam4);
  property p_lpddr6_ecc; @(posedge vif.ck) disable iff (!vif.rst_n) vif.ecc_en |-> vif.data_width >= 5'b01000; endproperty
  assert_p_lpddr6_ecc: assert property(p_lpddr6_ecc) else `uvm_warning("LPDDR6_L3", "On-die ECC failed");
  cover_p_lpddr6_ecc: cover property(p_lpddr6_ecc);
endmodule
`endif
