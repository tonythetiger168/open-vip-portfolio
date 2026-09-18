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

// LPDDR6 Monitor -- decodes DRAM commands from the command/address bus,
// reconstructs transactions (bank/row/col + burst data) and publishes them
// on an analysis port.
`ifndef LPDDR6_MONITOR_SV
`define LPDDR6_MONITOR_SV

class lpddr6_monitor extends uvm_monitor;
  `uvm_component_utils(lpddr6_monitor)
  virtual lpddr6_if vif;
  uvm_analysis_port #(lpddr6_transaction) ap;
  int unsigned txn_count = 0;

  protected lpddr6_transaction open_tr;   // RD/WR waiting for burst data
  protected int              burst_phase = 0;
  protected int              rd_wait = 0;

  function new(string name="lpddr6_monitor", uvm_component parent=null);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr6_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "LPDDR6 monitor: vif not found")
  endfunction

  task run_phase(uvm_phase phase);
    lpddr6_transaction tr;
    forever begin
      @(posedge vif.ck);
      if (vif.rst_n !== 1'b1) begin burst_phase = 0; rd_wait = 0; continue; end

      // ---- burst data capture (write: 2 beats following WR; read: after tCL) ----
      if (burst_phase > 0) begin
        if (burst_phase == 1) open_tr.data = vif.dq;
        else                  open_tr.data2 = vif.dq;
        burst_phase++;
        if (burst_phase > 2) begin
          burst_phase = 0;
          txn_count++;
          `uvm_info("MON", {"mon: ", open_tr.convert2string()}, UVM_HIGH)
          ap.write(open_tr);
        end
      end else if (rd_wait > 0) begin
        rd_wait--;
        if (rd_wait == 1) open_tr.rdata  = vif.dq;
        if (rd_wait == 0) begin
          open_tr.rdata2 = vif.dq;
          txn_count++;
          `uvm_info("MON", {"mon: ", open_tr.convert2string()}, UVM_HIGH)
          ap.write(open_tr);
        end
      end

      // ---- command decode on {cs_n, act_n, ras_n, cas_n, we_n} ----
      if (vif.cs_n === 1'b0) begin
        if (vif.act_n === 1'b0) begin                 // ACT
          tr = lpddr6_transaction::type_id::create("tr");
          tr.cmd = LPDDR6_CMD_ACT;
          tr.bg = vif.bg; tr.ba = vif.ba; tr.row = vif.addr; tr.col = '0;
          txn_count++;
          `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
          ap.write(tr);
        end else if (vif.ras_n === 1'b1 && vif.cas_n === 1'b0 && vif.we_n === 1'b0) begin
          open_tr = lpddr6_transaction::type_id::create("tr");  // WR
          open_tr.cmd = LPDDR6_CMD_WR;
          open_tr.bg = vif.bg; open_tr.ba = vif.ba; open_tr.col = vif.addr[9:0];
          burst_phase = 1;
        end else if (vif.ras_n === 1'b1 && vif.cas_n === 1'b0 && vif.we_n === 1'b1) begin
          open_tr = lpddr6_transaction::type_id::create("tr");  // RD
          open_tr.cmd = LPDDR6_CMD_RD;
          open_tr.bg = vif.bg; open_tr.ba = vif.ba; open_tr.col = vif.addr[9:0];
          // BL from the config sideband (see WR arm above).
          open_tr.bl = vif.bl;
          rd_wait = (vif.tCL > 0 ? vif.tCL : 6) + 1;
        end else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b1 && vif.we_n === 1'b0) begin
          tr = lpddr6_transaction::type_id::create("tr");       // PRE
          tr.cmd = LPDDR6_CMD_PRE;
          tr.bg = vif.bg; tr.ba = vif.ba;
          txn_count++;
          `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
          ap.write(tr);
        end else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b0 && vif.we_n === 1'b1) begin
          tr = lpddr6_transaction::type_id::create("tr");       // REF
          tr.cmd = LPDDR6_CMD_REF;
          txn_count++;
          `uvm_info("MON", {"mon: ", tr.convert2string()}, UVM_HIGH)
          ap.write(tr);
        end
      end
    end
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("MON", $sformatf("lpddr6 monitor observed %0d transactions", txn_count), UVM_LOW)
  endfunction
endclass
`endif
