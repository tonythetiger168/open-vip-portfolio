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

// HBM4 Error Handling Checker (L3) (ERROR)
// NOTE: the L3 concurrent assertions now live in hbm4_compliance_checker
// (module, instanced in tb_top). This component keeps its original API and
// performs equivalent procedural error-condition monitoring.
`ifndef HBM4_ERROR_CHECKER_SV
`define HBM4_ERROR_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
class hbm4_error_checker extends uvm_component;
  `uvm_component_utils(hbm4_error_checker)
  virtual hbm4_if vif;
  localparam time TRFC_NS = (48 + 2) * 10;
  time ref_rise_t = 0;
  bit  ref_seen = 0;
  function new(string name="hbm4_error_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "HBM4: vif not found"); endfunction
  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) continue;
      if (!$isunknown(vif.temp) && vif.temp > 8'd85 && vif.cs_n === 1'b0)
        `uvm_warning("HBM4_L3", "Overtemp: commands issued above 85C")
      if (!$isunknown(vif.latency_target) && vif.latency_target > 8'd127)
        `uvm_warning("HBM4_L3", "Latency target out of range")
      if (!$isunknown(vif.dfe_tap) && vif.dfe_tap > 4'd15)
        `uvm_warning("HBM4_L3", "DFE tap out of range")
      if ($rose(vif.refresh)) begin ref_rise_t = $time; ref_seen = 1; end
      if ($fell(vif.refresh) && ref_seen && ($time - ref_rise_t > TRFC_NS))
        `uvm_warning("HBM4_L3", "Refresh pulse wider than tRFC")
    end
  endtask
endclass
`endif
