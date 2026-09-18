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
//  CSE 2.0 Protocol Checker (UVM component, deepened)
//  Runtime checks: command encoding, response latency, IRQ discipline.
//  (Timed SVA lives in rtl/sva/cse_compliance_checker.sv, module form.)
//============================================================================
`ifndef CSE_PROTOCOL_CHECKER_SV
`define CSE_PROTOCOL_CHECKER_SV

`include "uvm_macros.svh"

import uvm_pkg::*;

class cse_protocol_checker extends uvm_component;
  `uvm_component_utils(cse_protocol_checker)

  virtual mipi_vip_if vif;
  int cmd_err, irq_err, ready_err;
  int unsigned cmd_cnt, resp_cnt;
  real coverage_target = 100.0;

  covergroup cg_cse @(posedge vif.clk);
    option.per_instance = 1;
    cp_cmd: coverpoint vif.cse_cmd {
      bins cmd0 = {0};
      bins cmd1 = {1};
      bins cmd2 = {2};
      bins cmd3 = {3};
      bins cmd4_9 = {[4:9]};
      bins reserved = {[10:15]};
    }
    cp_irq: coverpoint vif.cse_irq { bins off = {0}; bins on = {1}; }
    cp_valid: coverpoint vif.cse_valid { bins off = {0}; bins on = {1}; }
    cx_cmd_valid: cross cp_cmd, cp_valid;
  endgroup

  function new(string name = "cse_chk", uvm_component parent = null);
    super.new(name, parent);
    cmd_err = 0;
    irq_err = 0;
    ready_err = 0;
    cmd_cnt = 0;
    resp_cnt = 0;
    cg_cse = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "CSE chk: no vif")
  endfunction

  // Runtime protocol checks (sampled every clock):
  //  - a command is accepted only when valid && ready
  //  - every accepted command must be answered by cse_irq within 32 cycles
  //  - cse_irq must never fire without an outstanding command
  task run_phase(uvm_phase phase);
    int unsigned wait_irq = 0;
    bit          outstanding = 1'b0;
    bit          prev_irq = 1'b0;
    forever begin
      @(posedge vif.clk);
      if (!vif.rst_n) begin
        wait_irq = 0;
        outstanding = 1'b0;
        prev_irq = 1'b0;
        continue;
      end

      if (vif.cse_valid && vif.cse_ready) begin
        cmd_cnt++;
        if (outstanding) begin
          `uvm_error("CSE_CHK", "CSE new command while previous outstanding")
          cmd_err++;
        end
        outstanding = 1'b1;
        wait_irq = 0;
      end

      if (vif.cse_irq && !prev_irq) begin
        if (!outstanding) begin
          `uvm_error("CSE_CHK", "CSE IRQ without outstanding command")
          irq_err++;
        end
        else begin
          resp_cnt++;
          outstanding = 1'b0;
        end
      end
      else if (!vif.cse_irq && outstanding) begin
        wait_irq++;
        if (wait_irq > 32) begin
          `uvm_error("CSE_CHK", "CSE response (IRQ) timeout")
          ready_err++;
          wait_irq = 0;
          outstanding = 1'b0;
        end
      end
      prev_irq = vif.cse_irq;
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("CSE_RPT", $sformatf(
      "CSE Chk | cmds:%0d resps:%0d cmd_err:%0d irq_err:%0d rdy_err:%0d cov:%0.2f%%",
      cmd_cnt, resp_cnt, cmd_err, irq_err, ready_err, cg_cse.get_coverage()), UVM_LOW)
  endfunction
endclass

`endif // CSE_PROTOCOL_CHECKER_SV
