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

// HBM4 Data Integrity Checker (L2) (DATA_INTEGRITY)
// NOTE: the L2 concurrent assertions now live in hbm4_compliance_checker
// (module, instanced in tb_top). This component keeps its original API and
// performs equivalent procedural data-bus sanity sampling.
`ifndef HBM4_DATA_INTEGRITY_CHECKER_SV
`define HBM4_DATA_INTEGRITY_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
class hbm4_data_integrity_checker extends uvm_component;
  `uvm_component_utils(hbm4_data_integrity_checker)
  virtual hbm4_if vif;
  function new(string name="hbm4_data_integrity_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "HBM4: vif not found"); endfunction
  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) continue;
      if (vif.dqs_t === 1'b1 && $isunknown(vif.dq))
        `uvm_warning("HBM4_L2", "Data unknown while DQS active")
      if (vif.dbis === 1'b1 && vif.dqs_t !== 1'b1)
        `uvm_warning("HBM4_L2", "DBI status active without DQS")
      if (!$isunknown(vif.bl) && !(vif.bl inside {4'd1, 4'd2, 4'd3}))
        `uvm_warning("HBM4_L2", "Burst length setting outside 1/2/3")
      if (vif.ecc_en === 1'b1 && vif.data_width < 5'd8)
        `uvm_warning("HBM4_L2", "ECC enabled with too-narrow data width")
    end
  endtask
endclass
`endif
