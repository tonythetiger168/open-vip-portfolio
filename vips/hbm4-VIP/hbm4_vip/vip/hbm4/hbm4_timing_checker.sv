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

// HBM4 Timing Performance Checker (L2) (TIMING)
// NOTE: the L2 concurrent assertions now live in hbm4_compliance_checker
// (module, instanced in tb_top). This component keeps its original API and
// performs equivalent procedural tRCD/tRP/tRAS measurements per bank.
`ifndef HBM4_TIMING_CHECKER_SV
`define HBM4_TIMING_CHECKER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
class hbm4_timing_checker extends uvm_component;
  `uvm_component_utils(hbm4_timing_checker)
  virtual hbm4_if vif;
  // ck period is 10 ns in tb_top; convert cycle counts to ns
  localparam time TRCD_NS = 10 * 10;
  localparam time TRP_NS  = 10 * 10;
  localparam time TRAS_NS = 14 * 10;
  time act_t [bit [7:0]];
  time pre_t [bit [7:0]];
  bit  [7:0] bkey;
  function new(string name="hbm4_timing_checker", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase);
    if(!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif)) `uvm_fatal("CONFIG", "HBM4: vif not found"); endfunction
  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) continue;
      if (vif.cs_n !== 1'b0) continue;
      bkey = {vif.stack_id, vif.bg, vif.ba};
      if (vif.act_n === 1'b0) begin                          // ACT
        if (pre_t.exists(bkey) && ($time - pre_t[bkey] < TRP_NS))
          `uvm_warning("HBM4_L2", "tRP violation: ACT too soon after PRE")
        act_t[bkey] = $time;
      end
      else if (vif.ras_n === 1'b1 && vif.cas_n === 1'b0) begin  // RD/WR
        if (act_t.exists(bkey) && ($time - act_t[bkey] < TRCD_NS))
          `uvm_warning("HBM4_L2", "tRCD violation: column command too soon after ACT")
      end
      else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b1 && vif.we_n === 1'b0) begin  // PRE
        if (act_t.exists(bkey) && ($time - act_t[bkey] < TRAS_NS))
          `uvm_warning("HBM4_L2", "tRAS violation: PRE too soon after ACT")
        pre_t[bkey] = $time;
      end
    end
  endtask
endclass
`endif
