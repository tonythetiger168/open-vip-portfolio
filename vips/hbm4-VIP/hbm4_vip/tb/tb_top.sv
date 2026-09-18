// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// tb_top.sv -- HBM4 top-level testbench with a DRAM memory-array
// functional model (bank/row/column storage) closing the loop, plus the
// L1-L4 SVA compliance checker instance.

`timescale 1ns/1ps
`include "uvm_macros.svh"
import uvm_pkg::*;

module tb_top;
  logic ck = 0;
  logic rst_n;
  always #5 ck = ~ck;

  hbm4_if hbm4_if(ck, rst_n);

  // DRAM functional model: stores write data per {stack,bank,row,col} and
  // returns it on reads at the CAS latency
  hbm4_mem_model mem (.vif(hbm4_if));

  // SVA compliance checker (L1 signal sanity, L2 timing/data integrity,
  // L3 error handling, L4 protocol-specific timing & bank-state rules)
  hbm4_compliance_checker sva_chk (.vif(hbm4_if));

  initial begin
    rst_n = 0;
    hbm4_if.tRCD = 10;
    hbm4_if.tRP  = 10;
    hbm4_if.tRAS = 14;
    hbm4_if.tCL  = 10;
    #100 rst_n = 1;
  end

  initial begin
    uvm_config_db#(virtual hbm4_if)::set(null, "*", "vif", hbm4_if);
    run_test("hbm4_base_test");
  end

  initial begin #2000000 $finish; end
endmodule

// ---------------------------------------------------------------------------
// HBM4 DRAM memory-array functional model
// Command decode mirrors the driver encoding:
//   ACT latches the row per bank, WR stores data after tCWL, RD drives data
//   after tCL, PRE closes the bank, REF closes all banks.
// ---------------------------------------------------------------------------
module hbm4_mem_model (hbm4_if vif);
  localparam int TCL  = 10;
  localparam int TCWL = 2;

  bit [63:0] mem      [bit [33:0]];  // {stack,bg,ba,row,col} -> data
  bit [15:0] open_row [bit [7:0]];   // {stack,bg,ba} -> open row
  bit        is_open  [bit [7:0]];   // {stack,bg,ba} -> bank open flag
  bit [7:0]  bkey;
  bit [33:0] akey;

  always @(posedge vif.ck) begin
    if (vif.rst_n === 1'b1 && vif.cs_n === 1'b0) begin
      bkey = {vif.stack_id, vif.bg, vif.ba};
      if (vif.act_n === 1'b0) begin                      // ACT
        open_row[bkey] = vif.addr;
        is_open[bkey]  = 1'b1;
      end
      else if (vif.ras_n === 1'b1 && vif.cas_n === 1'b0) begin
        akey = {bkey, open_row[bkey], vif.addr[9:0]};
        if (vif.we_n === 1'b0) begin                     // WR: capture at tCWL
          fork
            begin
              repeat (TCWL-1) @(posedge vif.ck);
              mem[akey] = vif.dq;
            end
          join_none
        end
        else begin                                       // RD: drive at tCL
          fork
            begin
              repeat (TCL-1) @(posedge vif.ck);
              @(negedge vif.ck);
              vif.dq = mem.exists(akey) ? mem[akey] : 64'h0;
              @(negedge vif.ck);
              vif.dq = 64'hzzzz_zzzz_zzzz_zzzz;
            end
          join_none
        end
      end
      else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b1) begin  // PRE
        is_open[bkey] = 1'b0;
      end
      else if (vif.ras_n === 1'b0 && vif.cas_n === 1'b0) begin  // REF
        is_open.delete();
      end
    end
  end
endmodule
