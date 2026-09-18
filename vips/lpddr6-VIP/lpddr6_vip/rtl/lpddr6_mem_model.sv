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

// LPDDR6 functional memory DUT model (pure RTL, no UVM).
// Tracks one open row per bank, stores write bursts, returns read bursts
// after tCL. 2-beat representative burst, matching the VIP driver.
// Physical store is a 64K-word window over {bank, row[5:0], col[5:0]}.
`ifndef LPDDR6_MEM_MODEL_SV
`define LPDDR6_MEM_MODEL_SV

module lpddr6_mem_model (
  input  logic        ck,
  input  logic        rst_n,
  input  logic        cs_n,
  input  logic        act_n,
  input  logic        ras_n,
  input  logic        cas_n,
  input  logic        we_n,
  input  logic [15:0] addr,
  input  logic [2:0]  bg,
  input  logic [1:0]  ba,
  inout  wire  [63:0] dq,
  input  int          tRCD,
  input  int          tRP,
  input  int          tRAS,
  input  int          tCL
);
  localparam int NUM_BANKS = 16;      // {bg[1:0], ba} -> 16 banks (bg[2] folded)
  localparam int CL_DFLT   = 6;

  logic [63:0] mem  [0:65535];        // {bank, row[5:0], col[5:0]} window
  logic        mval [0:65535];
  logic [15:0] open_row [NUM_BANKS];
  logic        row_open [NUM_BANKS];

  logic [63:0] dq_o;
  logic        dq_oe;
  logic [63:0] rd_buf [2];
  int          rd_cnt;
  int          wr_beat;
  logic [3:0]  wr_bank;
  logic [15:0] wr_row;
  logic [9:0]  wr_col;
  logic [3:0]  rd_bank;
  logic [15:0] rd_row;
  logic [9:0]  rd_col;
  logic [15:0] midx;

  assign dq = dq_oe ? dq_o : 64'hzzzz_zzzz_zzzz_zzzz;

  function automatic logic [3:0] bank_id(input logic [2:0] g, input logic [1:0] b);
    return {g[1:0], b};
  endfunction

  function automatic logic [15:0] mem_idx(input logic [3:0] b,
                                          input logic [15:0] r,
                                          input logic [9:0]  c);
    return {b, r[5:0], c[5:0]};
  endfunction

  integer i;
  initial begin
    dq_oe = 0; dq_o = '0; rd_cnt = 0; wr_beat = 0;
    for (i = 0; i < NUM_BANKS; i = i + 1) begin row_open[i] = 0; open_row[i] = '0; end
    for (i = 0; i < 65536; i = i + 1) mval[i] = 0;
  end

  always @(posedge ck or negedge rst_n) begin
    if (!rst_n) begin
      dq_oe <= 0; rd_cnt <= 0; wr_beat <= 0;
      for (i = 0; i < NUM_BANKS; i = i + 1) row_open[i] <= 0;
    end else begin
      // read data return (2 beats), tCL counted by rd_cnt
      if (rd_cnt > 0) begin
        rd_cnt <= rd_cnt - 1;
        if (rd_cnt == 2) begin dq_oe <= 1; dq_o <= rd_buf[0]; end
        if (rd_cnt == 1) begin dq_o <= rd_buf[1]; end
      end else if (dq_oe) begin
        dq_oe <= 0;
      end

      // write burst beats (2 beats following WR command)
      if (wr_beat > 0) begin
        midx = mem_idx(wr_bank, wr_row, wr_col + ((wr_beat == 1) ? 10'd1 : 10'd0));
        mem[midx]  <= dq;
        mval[midx] <= 1'b1;
        wr_beat <= wr_beat - 1;
      end

      if (cs_n === 1'b0) begin
        if (act_n === 1'b0) begin                       // ACT
          row_open[bank_id(bg, ba)] <= 1'b1;
          open_row[bank_id(bg, ba)] <= addr;
        end else if (ras_n === 1'b1 && cas_n === 1'b0 && we_n === 1'b0) begin
          // WR
          wr_bank <= bank_id(bg, ba);
          wr_row  <= open_row[bank_id(bg, ba)];
          wr_col  <= addr[9:0];
          wr_beat <= 2;
        end else if (ras_n === 1'b1 && cas_n === 1'b0 && we_n === 1'b1) begin
          // RD
          rd_bank = bank_id(bg, ba);
          rd_row  = open_row[rd_bank];
          rd_col  = addr[9:0];
          if (row_open[rd_bank]) begin
            rd_buf[0] <= mval[mem_idx(rd_bank, rd_row, rd_col)] ?
                         mem[mem_idx(rd_bank, rd_row, rd_col)] : 64'hBAD0_BAD0_0000_0000;
            rd_buf[1] <= mval[mem_idx(rd_bank, rd_row, rd_col + 10'd1)] ?
                         mem[mem_idx(rd_bank, rd_row, rd_col + 10'd1)] : 64'hBAD0_BAD0_1111_1111;
          end else begin
            rd_buf[0] <= 64'hDEAD_0000_0000_0000;
            rd_buf[1] <= 64'hDEAD_1111_1111_1111;
          end
          rd_cnt <= (tCL > 0 ? tCL : CL_DFLT) + 1;
        end else if (ras_n === 1'b0 && cas_n === 1'b1 && we_n === 1'b0) begin
          // PRE
          row_open[bank_id(bg, ba)] <= 1'b0;
        end else if (ras_n === 1'b0 && cas_n === 1'b0 && we_n === 1'b1) begin
          // REF: close all banks
          for (i = 0; i < NUM_BANKS; i = i + 1) row_open[i] <= 1'b0;
        end
      end
    end
  end
endmodule
`endif
