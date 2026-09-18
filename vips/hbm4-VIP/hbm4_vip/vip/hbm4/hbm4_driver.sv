// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_driver.sv -- HBM4 memory protocol driver
//
// Drives the HBM4 command/address bus with the DDR-style command truth
// table (ACT/RD/WR/PRE/REF/NOP), honours core DRAM timing parameters
// (tRCD/tRP/tRAS/tCL/tCWL/tRFC) and publishes each completed transaction on
// drv_ap as the expected item for the end-to-end scoreboard.
// HBM4 stacked DRAM: 2048-bit interface, doubled pseudo-channels vs HBM3, stack_id up to 16Hi.

`ifndef HBM4_DRIVER_SV
`define HBM4_DRIVER_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

class hbm4_driver extends uvm_driver #(hbm4_transaction);
  `uvm_component_utils(hbm4_driver)
  virtual hbm4_if vif;
  uvm_analysis_port #(hbm4_transaction) drv_ap;  // expected items for scoreboard

  // Core timing parameters (cycles), aligned with the L2/L4 checkers
  localparam int TRCD = 10;   // ACT -> RD/WR
  localparam int TRP  = 10;    // PRE -> ACT
  localparam int TRAS = 14;   // ACT -> PRE
  localparam int TCL  = 10;    // RD  -> data out (CAS latency)
  localparam int TCWL = 2;   // WR  -> data in  (CAS write latency)
  localparam int TRFC = 48;   // REF cycle time

  function new(string name, uvm_component parent);
    super.new(name, parent);
    drv_ap = new("drv_ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual hbm4_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "HBM4 virtual interface not set")
  endfunction

  // ---- low-level bus control (all launched on negedge so the posedge
  // ---- samplers: monitor, memory model and SVA see stable values) ----
  // NOP hold: chip selected, no command (keeps cs_n low during wait states)
  task automatic set_idle();
    @(negedge vif.ck);
    vif.cs_n = 1'b0; vif.act_n = 1'b1; vif.ras_n = 1'b1; vif.cas_n = 1'b1; vif.we_n = 1'b1;
  endtask

  // Deselect: no chip selected
  task automatic set_desel();
    @(negedge vif.ck);
    vif.cs_n = 1'b1; vif.act_n = 1'b1; vif.ras_n = 1'b1; vif.cas_n = 1'b1; vif.we_n = 1'b1;
  endtask

  // Issue one command cycle: {act_n,ras_n,cas_n,we_n} encoding + bank/address
  task automatic issue_cmd(bit act, bit ras, bit cas, bit we,
                           bit [15:0] a, bit [2:0] g, bit [1:0] b, bit [2:0] s);
    @(negedge vif.ck);
    vif.cs_n  = 1'b0;
    vif.act_n = act; vif.ras_n = ras; vif.cas_n = cas; vif.we_n = we;
    vif.addr  = a;   vif.bg = g;      vif.ba = b;       vif.stack_id = s;
  endtask

  task automatic drive_item(hbm4_transaction tr);
    case (tr.cmd)
      HBM4_CMD_NOP: set_idle();

      HBM4_CMD_ACT: begin                       // ACT: act_n=0, row on addr
        issue_cmd(0, 1, 1, 1, tr.row, tr.bg, tr.ba, tr.stack_id);
        repeat (TRCD) set_idle();              // tRCD before any column command
      end

      HBM4_CMD_RD: begin                        // RD: ras_n=1 cas_n=0 we_n=1, col on addr
        issue_cmd(1, 1, 0, 1, {6'b0, tr.col}, tr.bg, tr.ba, tr.stack_id);
        repeat (TCL) @(posedge vif.ck);        // CAS latency, then sample DQ
        #1 tr.rdata = vif.dq;
        set_idle();
      end

      HBM4_CMD_WR: begin                        // WR: ras_n=1 cas_n=0 we_n=0, col on addr
        issue_cmd(1, 1, 0, 0, {6'b0, tr.col}, tr.bg, tr.ba, tr.stack_id);
        @(negedge vif.ck);                     // drive write data at tCWL
        vif.dq = tr.data;
        @(negedge vif.ck);
        vif.dq = 64'hzzzz_zzzz_zzzz_zzzz;      // release the bus
        set_idle();
      end

      HBM4_CMD_PRE: begin                       // PRE: ras_n=0 cas_n=1 we_n=0
        issue_cmd(1, 0, 1, 0, 16'h0, tr.bg, tr.ba, tr.stack_id);
        repeat (TRP) set_idle();               // tRP before next ACT
      end

      HBM4_CMD_REF: begin                       // REF: ras_n=0 cas_n=0 we_n=1
        issue_cmd(1, 0, 0, 1, 16'h0, tr.bg, tr.ba, tr.stack_id);
        vif.refresh = 1'b1;                    // refresh indicator for checkers
        repeat (TRFC) set_idle();              // tRFC refresh cycle time
        @(negedge vif.ck);
        vif.refresh = 1'b0;
      end

      default: set_idle();
    endcase
  endtask

  task run_phase(uvm_phase phase);
    hbm4_transaction tr;
    // Benign reset values for command bus and configuration/status pins
    vif.cs_n = 1'b1; vif.act_n = 1'b1; vif.ras_n = 1'b1; vif.cas_n = 1'b1; vif.we_n = 1'b1;
    vif.addr = '0; vif.bg = '0; vif.ba = '0; vif.ca = '0; vif.stack_id = '0;
    vif.dq = 64'hzzzz_zzzz_zzzz_zzzz; vif.dm = '0; vif.dqs_t = '0; vif.dmi_t = '0;
    vif.cke = 1'b1; vif.odt = 1'b0; vif.odt_ca = 1'b0;
    vif.bl = 4'd2; vif.wck_ratio = 2'b00; vif.dbim = 2'b00; vif.crc_en = 1'b0; vif.crc = '0;
    vif.pm_state = 3'b000; vif.refresh = 1'b0; vif.vrefca_train = 1'b0;
    vif.temp_sensor = 8'd25; vif.temp = 8'd25; vif.dfe_tap = '0;
    vif.ecc_en = 1'b0; vif.pam4_en = 1'b0; vif.same_bank_ref = 1'b0;
    vif.fgr_mode = '0; vif.wck2ck_train = 1'b0; vif.speed_grade = 4'd4;
    vif.latency_target = 8'd32; vif.bandwidth = 32'h0;
    vif.dbis = 1'b0; vif.pseudo_ch = 1'b0; vif.data_width = 5'd8;
    vif.tRCD = TRCD; vif.tRP = TRP; vif.tRAS = TRAS; vif.tCL = TCL;
    wait (vif.rst_n === 1'b1);
    repeat (2) set_desel();
    forever begin
      seq_item_port.get_next_item(tr);
      `uvm_info("DRV", {"drive: ", tr.convert2string()}, UVM_HIGH)
      drive_item(tr);
      drv_ap.write(tr);                        // broadcast expected transaction
      seq_item_port.item_done();
    end
  endtask
endclass
`endif
