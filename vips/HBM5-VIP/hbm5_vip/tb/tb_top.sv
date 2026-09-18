// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 top-level testbench -- clock/reset, hbm5_if instance, DRAM functional
// memory model (bank/row/col storage + refresh counter) closing the loop, and
// module-based SVA checkers.
`timescale 1ns/1ps
`include "uvm_macros.svh"
import uvm_pkg::*;

module tb_top;
  logic ck = 0;
  logic rst_n;
  always #5 ck = ~ck;

  hbm5_if hbm5_if_inst (ck, rst_n);

  initial begin
    rst_n = 0;
    #100 rst_n = 1;
  end

  // DRAM functional model: closes the read/write data loop
  hbm5_mem_model #(.TCL(12), .TCWL(10)) dut (.vif(hbm5_if_inst));

  // SVA checkers (module-based; L1/L2/L3 legacy rules)
  hbm5_protocol_checker       u_protocol_chk (.vif(hbm5_if_inst));
  hbm5_data_integrity_checker u_di_chk       (.vif(hbm5_if_inst));
  hbm5_timing_checker         u_timing_chk   (.vif(hbm5_if_inst));
  hbm5_error_checker          u_error_chk    (.vif(hbm5_if_inst));
  // Consolidated compliance checker with L4 protocol-specific rules
  hbm5_compliance_checker     u_compliance   (.vif(hbm5_if_inst));

  initial begin
    uvm_config_db #(virtual hbm5_if)::set(null, "*", "vif", hbm5_if_inst);
    run_test("hbm5_base_test");
  end
endmodule

// ---------------------------------------------------------------------------
// HBM5 DRAM functional model (HBM5 (High Bandwidth Memory, 5th generation))
// - bank/row tracking: ACT opens a row, PRE closes it
// - column storage in an associative array keyed by {bg,ba,row,col}
// - write data captured tCWL after WR; read data driven tCL after RD
// - refresh command counter
// ---------------------------------------------------------------------------
module hbm5_mem_model #(parameter int TCL = 12, parameter int TCWL = 10)
  (hbm5_if vif);

  localparam int NB = 32;                     // {bg[2:0],ba[1:0]} flattened

  bit        bank_open [NB];
  bit [15:0] open_row  [NB];
  bit [63:0] mem [bit [63:0]];                // sparse column storage
  int unsigned refresh_count = 0;
  int unsigned write_count = 0, read_count = 0;

  function automatic bit [63:0] key(input bit [2:0] bg, input bit [1:0] ba,
                                    input bit [15:0] row, input bit [15:0] col);
    return {16'h0, bg, ba, row, col};
  endfunction

  // Capture a write burst starting TCWL cycles after the WR command
  task automatic do_write(input bit [2:0] bg, input bit [1:0] ba,
                          input bit [15:0] col);
    bit [15:0] row;
    repeat (TCWL) @(posedge vif.ck);
    row = open_row[bg * 4 + ba];
    for (int i = 0; i < 16; i++) begin
      mem[key(bg, ba, row, col + i * 8)] = vif.dq;
      write_count++;
      @(posedge vif.ck);
    end
  endtask

  // Drive a read burst starting TCL cycles after the RD command
  task automatic do_read(input bit [2:0] bg, input bit [1:0] ba,
                         input bit [15:0] col);
    bit [15:0] row;
    repeat (TCL) @(posedge vif.ck);
    row = open_row[bg * 4 + ba];
    for (int i = 0; i < 16; i++) begin
      vif.dq <= mem.exists(key(bg, ba, row, col + i * 8))
                ? mem[key(bg, ba, row, col + i * 8)] : 64'h0;
      read_count++;
      @(posedge vif.ck);
    end
  endtask

  always @(posedge vif.ck) begin
    if (vif.rst_n && !vif.cs_n) begin
      if (!vif.act_n) begin                          // ACT: open row
        bank_open[vif.bg * 4 + vif.ba] <= 1'b1;
        open_row[vif.bg * 4 + vif.ba]  <= vif.addr;
      end
      else if (vif.ras_n && !vif.cas_n && !vif.we_n) // WR
        fork do_write(vif.bg, vif.ba, vif.addr); join_none
      else if (vif.ras_n && !vif.cas_n && vif.we_n)  // RD
        fork do_read(vif.bg, vif.ba, vif.addr); join_none
      else if (!vif.ras_n && vif.cas_n && !vif.we_n) // PRE
        bank_open[vif.bg * 4 + vif.ba] <= 1'b0;
      else if (!vif.ras_n && !vif.cas_n && vif.we_n) begin // REF
        refresh_count++;
        for (int b = 0; b < NB; b++) bank_open[b] <= 1'b0;
      end
    end
  end

  final
    $display("HBM5_mem_model: reads=%0d writes=%0d refreshes=%0d",
             read_count, write_count, refresh_count);
endmodule
