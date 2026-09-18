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
//  CSI2 Protocol Checker (stub)
//  Minimal activity/validity checker for the CSI2 lane of mipi_vip_if.
//  Only the CSE protocol is deepened in this VIP.
//============================================================================
`ifndef CSI2_PROTOCOL_CHECKER_SV
`define CSI2_PROTOCOL_CHECKER_SV

`include "uvm_macros.svh"

import uvm_pkg::*;

class csi2_protocol_checker extends uvm_component;
  `uvm_component_utils(csi2_protocol_checker)

  virtual mipi_vip_if vif;
  int unsigned active_cycles = 0;
  int unsigned err_cnt = 0;

  function new(string name = "csi2_chk", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "CSI2 chk: no vif")
  endfunction

  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.clk);
      if (!vif.rst_n) continue;
      if (vif.valid && vif.sop) active_cycles++;
      if (vif.eop && !vif.sop && vif.word_count == 0 && vif.valid) err_cnt++;
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("CSI2_RPT", $sformatf("CSI2 chk | active:%0d err:%0d",
              active_cycles, err_cnt), UVM_LOW)
  endfunction
endclass

`endif // CSI2_PROTOCOL_CHECKER_SV
