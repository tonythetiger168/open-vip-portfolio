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

// HBM4 Protocol Compliance Checker (L1) (PROTOCOL)
// NOTE: the L1 concurrent assertions now live in hbm4_compliance_checker
// (module, instanced in tb_top). This component keeps its original API and
// performs equivalent procedural L1 signal-sanity sampling.
`ifndef HBM4_PROTOCOL_CHECKER_SV
`define HBM4_PROTOCOL_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
class hbm4_protocol_checker extends uvm_component;
  `uvm_component_utils(hbm4_protocol_checker)
  virtual hbm4_if vif;
  int unsigned act_count = 0;
  function new(string name="hbm4_protocol_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "HBM4: vif not found"); endfunction
  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) continue;
      if (vif.cs_n === 1'b0 && vif.act_n === 1'b0) begin
        act_count++;
        if ($isunknown(vif.addr)) `uvm_warning("HBM4_L1", "Address unknown during ACT")
        if ($isunknown(vif.ca))   `uvm_warning("HBM4_L1", "CA bus unknown during ACT")
      end
      if (!$isunknown(vif.bg) && vif.bg > 3'd3) `uvm_warning("HBM4_L1", "Bank group 0-3 failed")
      if (!$isunknown(vif.ba) && vif.ba > 2'd3) `uvm_warning("HBM4_L1", "Bank address 0-3 failed")
    end
  endtask
  function void report_phase(uvm_phase phase);
    `uvm_info("HBM4_L1", $sformatf("hbm4 protocol checker observed %0d activates", act_count), UVM_LOW)
  endfunction
endclass
`endif
