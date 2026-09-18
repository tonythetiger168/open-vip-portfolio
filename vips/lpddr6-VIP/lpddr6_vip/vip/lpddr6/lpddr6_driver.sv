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

// LPDDR6 Driver -- issues DRAM command encodings (ACT/RD/WR/PRE/REF/NOP)
// with bank/row/column addressing and tRCD/tRP/tRAS/tCL timing concepts.
`ifndef LPDDR6_DRIVER_SV
`define LPDDR6_DRIVER_SV

class lpddr6_driver extends uvm_driver #(lpddr6_transaction);
  `uvm_component_utils(lpddr6_driver)
  virtual lpddr6_if vif;
  uvm_analysis_port #(lpddr6_transaction) drv_ap;  // expected items for scoreboard

  // timing (clock cycles); seeded into the interface for the DUT/monitors
  int tRCD = 4;
  int tRP  = 4;
  int tRAS = 8;
  int tCL  = 6;

  function new(string name="lpddr6_driver", uvm_component parent=null);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual lpddr6_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "LPDDR6 driver: vif not found")
  endfunction

  // ---- command encodings on {cs_n, act_n, ras_n, cas_n, we_n} ----
  task drive_nop();
    vif.cb.cs_n <= 1'b1; vif.cb.act_n <= 1'b1; vif.cb.ras_n <= 1'b1;
    vif.cb.cas_n <= 1'b1; vif.cb.we_n  <= 1'b1;
    @(vif.cb);
  endtask

  task drive_act(input bit [2:0] bg, input bit [1:0] ba, input bit [15:0] row);
    vif.cb.cs_n <= 1'b0; vif.cb.act_n <= 1'b0;         // ACT
    vif.cb.ras_n <= 1'b0; vif.cb.cas_n <= 1'b1; vif.cb.we_n <= 1'b1;
    vif.cb.bg <= bg; vif.cb.ba <= ba; vif.cb.addr <= row; vif.cb.ca <= row[6:0];
    @(vif.cb);
    drive_nop();
  endtask

  task drive_pre(input bit [2:0] bg, input bit [1:0] ba);
    vif.cb.cs_n <= 1'b0; vif.cb.act_n <= 1'b1;         // PRE
    vif.cb.ras_n <= 1'b0; vif.cb.cas_n <= 1'b1; vif.cb.we_n <= 1'b0;
    vif.cb.bg <= bg; vif.cb.ba <= ba;
    @(vif.cb);
    drive_nop();
    repeat (tRP) @(vif.cb);                            // tRP
  endtask

  task drive_ref();
    vif.cb.cs_n <= 1'b0; vif.cb.act_n <= 1'b1;         // REF
    vif.cb.ras_n <= 1'b0; vif.cb.cas_n <= 1'b0; vif.cb.we_n <= 1'b1;
    @(vif.cb);
    drive_nop();
    repeat (tRP + 2) @(vif.cb);                        // tRFC (abbreviated)
  endtask

  task drive_write(lpddr6_transaction tr);
    vif.cb.cs_n <= 1'b0; vif.cb.act_n <= 1'b1;         // WR
    vif.cb.ras_n <= 1'b1; vif.cb.cas_n <= 1'b0; vif.cb.we_n <= 1'b0;
    vif.cb.bg <= tr.bg; vif.cb.ba <= tr.ba;
    vif.cb.addr <= {6'b0, tr.col}; vif.cb.ca <= tr.col[6:0];
    vif.cb.dq <= tr.data; vif.cb.dm <= 8'h00;          // burst beat 0
    vif.cb.dqs_t <= 8'hFF; vif.cb.dmi_t <= 8'h00;
    @(vif.cb);
    vif.cb.dq <= tr.data2;                             // burst beat 1
    vif.cb.dqs_t <= 8'h00;
    @(vif.cb);
    drive_nop();
    vif.cb.dqs_t <= 8'h00;
  endtask

  task drive_read(lpddr6_transaction tr);
    vif.cb.cs_n <= 1'b0; vif.cb.act_n <= 1'b1;         // RD
    vif.cb.ras_n <= 1'b1; vif.cb.cas_n <= 1'b0; vif.cb.we_n <= 1'b1;
    vif.cb.bg <= tr.bg; vif.cb.ba <= tr.ba;
    vif.cb.addr <= {6'b0, tr.col}; vif.cb.ca <= tr.col[6:0];
    @(vif.cb);
    drive_nop();
    repeat (tCL) @(vif.cb);                            // CAS latency
  endtask

  task run_phase(uvm_phase phase);
    lpddr6_transaction tr;
    vif.cb.cs_n <= 1'b1; vif.cb.act_n <= 1'b1; vif.cb.ras_n <= 1'b1;
    vif.cb.cas_n <= 1'b1; vif.cb.we_n  <= 1'b1; vif.cb.cke   <= 1'b1;
    vif.tRCD = tRCD; vif.tRP = tRP; vif.tRAS = tRAS; vif.tCL = tCL;
    vif.bl = 5'd16;                                    // BL16 default until first RD/WR
    wait (vif.rst_n === 1'b1);
    repeat (4) @(vif.cb);
    forever begin
      seq_item_port.get_next_item(tr);
      `uvm_info("DRV", {"drive: ", tr.convert2string()}, UVM_HIGH)
      case (tr.cmd)
        LPDDR6_CMD_ACT: begin
          drive_act(tr.bg, tr.ba, tr.row);
          repeat (tRAS) @(vif.cb);
          drive_pre(tr.bg, tr.ba);
        end
        LPDDR6_CMD_WR: begin
          if (!tr.no_act) begin
            drive_act(tr.bg, tr.ba, tr.row);
            repeat (tRCD) @(vif.cb);
          end
          drive_write(tr);
          repeat (tRP) @(vif.cb);
          drive_pre(tr.bg, tr.ba);
        end
        LPDDR6_CMD_RD: begin
          if (!tr.no_act) begin
            drive_act(tr.bg, tr.ba, tr.row);
            repeat (tRCD) @(vif.cb);
          end
          drive_read(tr);
          repeat (tRP) @(vif.cb);
          drive_pre(tr.bg, tr.ba);
        end
        LPDDR6_CMD_PRE: drive_pre(tr.bg, tr.ba);
        LPDDR6_CMD_REF: drive_ref();
        default:         drive_nop();
      endcase
      drv_ap.write(tr);                  // broadcast expected transaction
      seq_item_port.item_done();
    end
  endtask
endclass
`endif
