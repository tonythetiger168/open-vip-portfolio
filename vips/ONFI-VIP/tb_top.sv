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
//------------------------------------------------------------------------------
// Multi-protocol memory VIP top-level testbench.
// ONFI path is closed-loop: onfi_driver <-> onfi_nand_model (DUT) <-> onfi_monitor
// plus the tiered SVA compliance checker bound to the ONFI bus.
//------------------------------------------------------------------------------
`timescale 1ns/1ps
`ifndef TB_TOP_SV
`define TB_TOP_SV

import uvm_pkg::*;
`include "uvm_macros.svh"
import memory_test_pkg::*;

//------------------------------------------------------------------------------
// ONFI NAND flash DUT model
//   - command / address / data-in latched on WE# rising edge (CE# low)
//   - page buffer + sparse NAND array (erased = 0xFF)
//   - status register (FAIL / RDY / WP), R/B# busy timing (tR/tPROG/tBERS/tRST)
//   - data-out on RE# cycles (status / ID / parameter / feature / page data)
//------------------------------------------------------------------------------
module onfi_nand_model #(
  parameter int NUM_BLOCKS      = 64,
  parameter int PAGES_PER_BLOCK = 64,
  parameter int PAGE_SIZE       = 256,
  parameter int T_R             = 25,
  parameter int T_PROG          = 200,
  parameter int T_BERS          = 2000,
  parameter int T_RST           = 10
)(
  onfi_if vif
);
  // sparse storage: key = {block, page, byte}
  bit [7:0] mem [longint unsigned];
  bit [7:0] page_buf [PAGE_SIZE];
  bit [7:0] feat_regs [256];

  typedef enum logic [2:0] {
    OUT_NONE, OUT_STATUS, OUT_ID, OUT_PARAM, OUT_FEATURE, OUT_PAGE
  } out_sel_e;

  out_sel_e  out_sel = OUT_NONE;
  bit [7:0]  out_byte = 8'hFF;
  bit [7:0]  status = 8'hC0;       // RDY | WP
  bit [7:0]  cur_cmd;
  bit [23:0] addr_shift;
  int        addr_cnt = 0;
  int        wr_ptr = 0;
  int        rd_ptr = 0;
  int        busy_cnt = 0;
  bit        prev_we_n = 1'b1;
  bit        prev_re_n = 1'b1;

  // "ONFI" signature + revision byte
  function automatic bit [7:0] id_byte(int idx);
    case (idx % 5)
      0:       return 8'h4F;  // 'O'
      1:       return 8'h4E;  // 'N'
      2:       return 8'h46;  // 'F'
      3:       return 8'h49;  // 'I'
      default: return 8'h01;  // revision
    endcase
  endfunction

  // data-out driver: target drives IO only while CE# and RE# are low
  assign vif.io = (!vif.ce_n && !vif.re_n) ? out_byte : 8'hzz;
  // ready/busy
  assign vif.rb_n = (busy_cnt == 0);

  function automatic longint unsigned mkey(int blk, int pg, int idx);
    return (longint'(blk) * PAGES_PER_BLOCK * PAGE_SIZE)
         + (longint'(pg) * PAGE_SIZE) + idx;
  endfunction

  task automatic load_page(int blk, int pg);
    for (int i = 0; i < PAGE_SIZE; i++) begin
      longint unsigned k = mkey(blk, pg, i);
      page_buf[i] = mem.exists(k) ? mem[k] : 8'hFF;
    end
  endtask

  task automatic store_page(int blk, int pg);
    for (int i = 0; i < PAGE_SIZE; i++)
      mem[mkey(blk, pg, i)] = page_buf[i];
  endtask

  task automatic erase_block(int blk);
    for (int p = 0; p < PAGES_PER_BLOCK; p++)
      for (int i = 0; i < PAGE_SIZE; i++) begin
        longint unsigned k = mkey(blk, p, i);
        if (mem.exists(k)) mem.delete(k);
      end
  endtask

  function automatic bit [7:0] status_val();
    bit [7:0] s;
    s = status;
    s[6] = (busy_cnt == 0);  // RDY
    s[7] = vif.wp_n;         // write-protect status
    return s;
  endfunction

  always @(posedge vif.clk or negedge vif.rst_n) begin
    if (!vif.rst_n) begin
      out_sel    <= OUT_NONE;
      out_byte   <= 8'hFF;
      status     <= 8'hC0;
      addr_cnt   <= 0;
      wr_ptr     <= 0;
      rd_ptr     <= 0;
      busy_cnt   <= 0;
      prev_we_n  <= 1'b1;
      prev_re_n  <= 1'b1;
    end
    else begin
      prev_we_n <= vif.we_n;
      prev_re_n <= vif.re_n;

      // busy countdown (tR / tPROG / tBERS / tRST)
      if (busy_cnt > 0) busy_cnt <= busy_cnt - 1;

      // WE# rising edge: latch command / address / data-in
      if (!vif.ce_n && prev_we_n == 1'b0 && vif.we_n == 1'b1) begin
        if (vif.cle) begin
          cur_cmd  <= vif.io;
          addr_cnt <= 0;
          case (vif.io)
            8'h00: begin out_sel <= OUT_NONE; end            // read setup
            8'h30: begin                                     // read confirm
              load_page(addr_shift[7:0], addr_shift[15:8]);
              rd_ptr   <= 0;
              out_sel  <= OUT_PAGE;
              busy_cnt <= T_R;
              status[0] <= 1'b0;
            end
            8'h80: begin wr_ptr <= 0; out_sel <= OUT_NONE; end // program setup
            8'h10: begin                                     // program confirm
              if (!vif.wp_n) status[0] <= 1'b1;              // WP# violation -> FAIL
              else begin
                store_page(addr_shift[7:0], addr_shift[15:8]);
                status[0] <= 1'b0;
              end
              busy_cnt <= T_PROG;
            end
            8'h60: begin out_sel <= OUT_NONE; end            // erase setup
            8'hD0: begin                                     // erase confirm
              if (!vif.wp_n) status[0] <= 1'b1;
              else begin
                erase_block(addr_shift[7:0]);
                status[0] <= 1'b0;
              end
              busy_cnt <= T_BERS;
            end
            8'hFF: begin                                     // reset
              busy_cnt <= T_RST;
              status   <= 8'hC0;
              out_sel  <= OUT_NONE;
              rd_ptr   <= 0;
              wr_ptr   <= 0;
            end
            8'h70: begin out_sel <= OUT_STATUS; end          // read status
            8'h90: begin rd_ptr <= 0; end                    // read ID (addr follows)
            8'hEC: begin rd_ptr <= 0; end                    // read parameter (addr follows)
            8'hEF: begin wr_ptr <= 0; end                    // set features
            8'hEE: begin rd_ptr <= 0; end                    // get features
            default: ;
          endcase
        end
        else if (vif.ale) begin
          addr_shift <= {addr_shift[15:0], vif.io};
          addr_cnt   <= addr_cnt + 1;
          if (cur_cmd == 8'h90) begin out_sel <= OUT_ID;      rd_ptr <= 0; end
          if (cur_cmd == 8'hEC) begin out_sel <= OUT_PARAM;   rd_ptr <= 0; end
          if (cur_cmd == 8'hEE) begin out_sel <= OUT_FEATURE; rd_ptr <= 0; end
        end
        else begin
          // data-in byte
          if (cur_cmd == 8'hEF) begin
            if (wr_ptr == 0) feat_regs[addr_shift[7:0]] <= vif.io;
            wr_ptr <= wr_ptr + 1;
          end
          else if (wr_ptr < PAGE_SIZE) begin
            page_buf[wr_ptr] <= vif.io;
            wr_ptr <= wr_ptr + 1;
          end
        end
      end

      // RE# falling edge: present the current output byte
      if (!vif.ce_n && prev_re_n == 1'b1 && vif.re_n == 1'b0) begin
        case (out_sel)
          OUT_STATUS:  out_byte <= status_val();
          OUT_ID:      out_byte <= id_byte(rd_ptr);
          OUT_PARAM:   out_byte <= id_byte(rd_ptr % 4);
          OUT_FEATURE: out_byte <= feat_regs[addr_shift[7:0]];
          OUT_PAGE:    out_byte <= (rd_ptr < PAGE_SIZE) ? page_buf[rd_ptr] : 8'hFF;
          default:     out_byte <= 8'hFF;
        endcase
      end
      // RE# rising edge: advance output pointer
      if (!vif.ce_n && prev_re_n == 1'b0 && vif.re_n == 1'b1) begin
        if (out_sel == OUT_ID || out_sel == OUT_PARAM || out_sel == OUT_PAGE)
          rd_ptr <= rd_ptr + 1;
      end
    end
  end
endmodule : onfi_nand_model

//------------------------------------------------------------------------------
// Top-level testbench
//------------------------------------------------------------------------------
module tb_top;
  logic ddr_ck = 0, ddr_rst_n = 0;
  logic lpddr_ck = 0, lpddr_rst_n = 0;
  logic hbm_ck = 0, hbm_rst_n = 0;
  logic ufs_clk = 0, ufs_rst_n = 0;
  logic unipro_clk = 0, unipro_rst_n = 0;
  logic emmc_clk = 0, emmc_rst_n = 0;
  logic onfi_clk = 0, onfi_rst_n = 0;
  logic sd_clk = 0, sd_rst_n = 0;

  always #5  ddr_ck    = ~ddr_ck;
  always #5  lpddr_ck  = ~lpddr_ck;
  always #5  hbm_ck    = ~hbm_ck;
  always #10 ufs_clk   = ~ufs_clk;
  always #10 unipro_clk = ~unipro_clk;
  always #20 emmc_clk  = ~emmc_clk;
  always #50 onfi_clk  = ~onfi_clk;
  always #20 sd_clk    = ~sd_clk;

  initial begin
    #100;
    ddr_rst_n = 1;
    lpddr_rst_n = 1;
    hbm_rst_n = 1;
    ufs_rst_n = 1;
    unipro_rst_n = 1;
    emmc_rst_n = 1;
    onfi_rst_n = 1;
    sd_rst_n = 1;
  end

  ddr_if    ddr_if_inst    (.ck(ddr_ck), .ck_n(~ddr_ck), .rst_n(ddr_rst_n));
  lpddr_if  lpddr_if_inst  (.ck(lpddr_ck), .ck_n(~lpddr_ck), .cke(1'b1), .rst_n(lpddr_rst_n));
  hbm_if    hbm_if_inst    (.ck(hbm_ck), .ck_n(~hbm_ck), .rst_n(hbm_rst_n));
  ufs_if    ufs_if_inst    (.ref_clk(ufs_clk), .rst_n(ufs_rst_n));
  unipro_if unipro_if_inst (.clk(unipro_clk), .rst_n(unipro_rst_n));
  emmc_if   emmc_if_inst   (.clk(emmc_clk), .rst_n(emmc_rst_n));
  onfi_if   onfi_if_inst   (.clk(onfi_clk), .rst_n(onfi_rst_n));
  sd_if     sd_if_inst     (.clk(sd_clk), .rst_n(sd_rst_n));

  // ONFI NAND flash DUT (functional model)
  onfi_nand_model onfi_dut (.vif(onfi_if_inst));

  // ONFI SVA checkers bound to the ONFI bus
  onfi_compliance_checker onfi_sva (
    .clk   (onfi_if_inst.clk),
    .rst_n (onfi_if_inst.rst_n),
    .io    (onfi_if_inst.io),
    .cle   (onfi_if_inst.cle),
    .ale   (onfi_if_inst.ale),
    .ce_n  (onfi_if_inst.ce_n),
    .re_n  (onfi_if_inst.re_n),
    .we_n  (onfi_if_inst.we_n),
    .wp_n  (onfi_if_inst.wp_n),
    .rb_n  (onfi_if_inst.rb_n)
  );

  onfi_protocol_checker onfi_proto_chk (
    .clk   (onfi_if_inst.clk),
    .rst_n (onfi_if_inst.rst_n),
    .io    (onfi_if_inst.io),
    .cle   (onfi_if_inst.cle),
    .ale   (onfi_if_inst.ale),
    .ce_n  (onfi_if_inst.ce_n),
    .re_n  (onfi_if_inst.re_n),
    .we_n  (onfi_if_inst.we_n),
    .wp_n  (onfi_if_inst.wp_n),
    .rb_n  (onfi_if_inst.rb_n)
  );

  onfi_timing_checker onfi_timing_chk (
    .clk   (onfi_if_inst.clk),
    .rst_n (onfi_if_inst.rst_n),
    .cle   (onfi_if_inst.cle),
    .ale   (onfi_if_inst.ale),
    .ce_n  (onfi_if_inst.ce_n),
    .re_n  (onfi_if_inst.re_n),
    .we_n  (onfi_if_inst.we_n),
    .rb_n  (onfi_if_inst.rb_n)
  );

  onfi_error_checker onfi_err_chk (
    .clk   (onfi_if_inst.clk),
    .rst_n (onfi_if_inst.rst_n),
    .io    (onfi_if_inst.io),
    .cle   (onfi_if_inst.cle),
    .ale   (onfi_if_inst.ale),
    .ce_n  (onfi_if_inst.ce_n),
    .re_n  (onfi_if_inst.re_n),
    .we_n  (onfi_if_inst.we_n),
    .wp_n  (onfi_if_inst.wp_n)
  );

  onfi_data_integrity_checker onfi_di_chk (
    .clk   (onfi_if_inst.clk),
    .rst_n (onfi_if_inst.rst_n),
    .io    (onfi_if_inst.io),
    .ce_n  (onfi_if_inst.ce_n),
    .re_n  (onfi_if_inst.re_n),
    .we_n  (onfi_if_inst.we_n)
  );

  initial begin
    uvm_config_db#(virtual ddr_if)::set(null, "*.ddr_*", "vif", ddr_if_inst);
    uvm_config_db#(virtual lpddr_if)::set(null, "*.lpddr_*", "vif", lpddr_if_inst);
    uvm_config_db#(virtual hbm_if)::set(null, "*.hbm_*", "vif", hbm_if_inst);
    uvm_config_db#(virtual ufs_if)::set(null, "*.ufs_*", "vif", ufs_if_inst);
    uvm_config_db#(virtual unipro_if)::set(null, "*.unipro_*", "vif", unipro_if_inst);
    uvm_config_db#(virtual emmc_if)::set(null, "*.emmc_*", "vif", emmc_if_inst);
    uvm_config_db#(virtual onfi_if)::set(null, "*.onfi_*", "vif", onfi_if_inst);
    uvm_config_db#(virtual sd_if)::set(null, "*.sd_*", "vif", sd_if_inst);
    run_test();
  end

  initial begin
    $dumpfile("memory_uvm_vip.vcd");
    $dumpvars(0, tb_top);
  end

  initial begin
    #2000000;
    `uvm_fatal("TB_TOP", "Timeout!")
  end
endmodule : tb_top

`endif // TB_TOP_SV
