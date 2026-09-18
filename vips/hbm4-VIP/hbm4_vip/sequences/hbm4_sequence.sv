// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_sequence.sv -- HBM4 transaction and directed sequence library
//
// Command truth table (DDR-style encoding driven on the CA bus):
//   ACT : cs_n=0 act_n=0                      row on addr, bank on {bg,ba}
//   RD  : cs_n=0 act_n=1 ras_n=1 cas_n=0 we_n=1  col on addr
//   WR  : cs_n=0 act_n=1 ras_n=1 cas_n=0 we_n=0  col on addr
//   PRE : cs_n=0 act_n=1 ras_n=0 cas_n=1 we_n=0
//   REF : cs_n=0 act_n=1 ras_n=0 cas_n=0 we_n=1
//   NOP : cs_n=0 act_n=1 ras_n=1 cas_n=1 we_n=1  (wait state)
// HBM4 stacked DRAM: 2048-bit interface, doubled pseudo-channels vs HBM3, stack_id up to 16Hi.

`ifndef HBM4_SEQUENCE_SV
`define HBM4_SEQUENCE_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

typedef enum bit [2:0] {
  HBM4_CMD_NOP, HBM4_CMD_ACT, HBM4_CMD_RD, HBM4_CMD_WR, HBM4_CMD_PRE, HBM4_CMD_REF
} hbm4_cmd_e;

class hbm4_transaction extends uvm_sequence_item;
  `uvm_object_utils(hbm4_transaction)
  rand hbm4_cmd_e   cmd;
  rand bit [15:0]  addr;      // legacy combined address field (kept for API compatibility)
  rand bit [63:0]  data;      // write data
  rand bit         we_n;      // legacy direction field (kept for API compatibility)
  rand bit [2:0]   bg;        // bank group
  rand bit [1:0]   ba;        // bank address
  rand bit [3:0]   bl;        // burst length setting
  rand bit [15:0]  row;       // DRAM row address (ACT)
  rand bit [9:0]   col;       // DRAM column address (RD/WR)
  rand bit [2:0]   stack_id;  // HBM stack / pseudo-channel select; die select on GDDR/LPDDR
       bit [63:0]  rdata;     // read data sampled from the bus (driver/monitor)

  constraint c_bl  { bl inside {4'd1, 4'd2, 4'd3}; }
  constraint c_cmd { cmd inside {HBM4_CMD_ACT, HBM4_CMD_RD, HBM4_CMD_WR, HBM4_CMD_PRE, HBM4_CMD_REF}; }

  function new(string name="hbm4_transaction"); super.new(name); endfunction

  function string convert2string();
    return $sformatf("cmd=%s bg=%0d ba=%0d stack=%0d row=0x%04h col=0x%03h data=0x%016h rdata=0x%016h",
                     cmd.name(), bg, ba, stack_id, row, col, data, rdata);
  endfunction
endclass

class hbm4_base_sequence extends uvm_sequence #(hbm4_transaction);
  `uvm_object_utils(hbm4_base_sequence)
  rand int num_transactions = 1000;
  function new(string name="hbm4_base_sequence"); super.new(name); endfunction

  // Helper: send one fully-specified command item
  task automatic do_item(hbm4_cmd_e c, bit [15:0] r = 0, bit [9:0] cl = 0,
                         bit [2:0] g = 0, bit [1:0] b = 0,
                         bit [63:0] d = 0, bit [2:0] s = 0);
    hbm4_transaction tr = hbm4_transaction::type_id::create("tr");
    start_item(tr);
    tr.cmd = c; tr.row = r; tr.col = cl; tr.bg = g; tr.ba = b;
    tr.data = d; tr.stack_id = s;
    tr.we_n = (c == HBM4_CMD_RD);
    tr.addr = (c == HBM4_CMD_ACT) ? r : {6'b0, cl};
    finish_item(tr);
  endtask

  task body();
    hbm4_transaction tr;
    for (int i = 0; i < num_transactions; i++) begin
      tr = hbm4_transaction::type_id::create($sformatf("tr_%0d", i));
      start_item(tr);
      if (!tr.randomize()) `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Directed: normal write flow -- ACT, burst of WR to the open row, PRE
class hbm4_write_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_write_seq)
  function new(string name="hbm4_write_seq"); super.new(name); num_transactions = 16; endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      bit [2:0] g = $urandom_range(0, 3);
      bit [1:0] b = $urandom_range(0, 3);
      bit [15:0] r = $urandom();
      int nwr = $urandom_range(1, 4);
      do_item(HBM4_CMD_ACT, r, 0, g, b);
      for (int k = 0; k < nwr; k++)
        do_item(HBM4_CMD_WR, r, k * 10'h8, g, b, {$urandom(), $urandom()});
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
    end
  endtask
endclass

// Directed: normal read flow -- ACT, burst of RD from the open row, PRE
class hbm4_read_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_read_seq)
  function new(string name="hbm4_read_seq"); super.new(name); num_transactions = 16; endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      bit [2:0] g = $urandom_range(0, 3);
      bit [1:0] b = $urandom_range(0, 3);
      bit [15:0] r = $urandom();
      int nrd = $urandom_range(1, 4);
      do_item(HBM4_CMD_ACT, r, 0, g, b);
      for (int k = 0; k < nrd; k++)
        do_item(HBM4_CMD_RD, r, k * 10'h8, g, b);
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
    end
  endtask
endclass

// Directed: refresh flow -- traffic punctuated by REF commands (tRFC apart)
class hbm4_refresh_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_refresh_seq)
  function new(string name="hbm4_refresh_seq"); super.new(name); num_transactions = 8; endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      bit [2:0] g = $urandom_range(0, 3);
      bit [1:0] b = $urandom_range(0, 3);
      bit [15:0] r = $urandom();
      do_item(HBM4_CMD_ACT, r, 0, g, b);
      do_item(HBM4_CMD_WR, r, 10'h0, g, b, {$urandom(), $urandom()});
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
      do_item(HBM4_CMD_REF);
    end
  endtask
endclass

// Directed: bank conflict -- same bank, alternating rows (page misses,
// forces repeated PRE/ACT turnaround on one bank)
class hbm4_bank_conflict_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_bank_conflict_seq)
  function new(string name="hbm4_bank_conflict_seq"); super.new(name); num_transactions = 16; endfunction
  task body();
    bit [2:0] g = 2;
    bit [1:0] b = 1;
    for (int i = 0; i < num_transactions; i++) begin
      bit [15:0] r = (i % 2) ? 16'hAAAA : 16'h5555;
      do_item(HBM4_CMD_ACT, r, 0, g, b);
      do_item(HBM4_CMD_RD, r, 10'h10, g, b);
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
    end
  endtask
endclass

// Directed: back-to-back -- one ACT, then a long alternating RD/WR stream
// to the open row (page hits, minimum bus idle), then PRE
class hbm4_back_to_back_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_back_to_back_seq)
  function new(string name="hbm4_back_to_back_seq"); super.new(name); num_transactions = 8; endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      bit [2:0] g = $urandom_range(0, 3);
      bit [1:0] b = $urandom_range(0, 3);
      bit [15:0] r = $urandom();
      do_item(HBM4_CMD_ACT, r, 0, g, b);
      for (int k = 0; k < 16; k++) begin
        if (k % 2) do_item(HBM4_CMD_RD, r, k[9:0] * 10'h4, g, b);
        else       do_item(HBM4_CMD_WR, r, k[9:0] * 10'h4, g, b, {$urandom(), $urandom()});
      end
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
    end
  endtask
endclass

// Directed: stress -- long randomized but protocol-legal command stream:
// a bank-state model ensures RD/WR only hit open banks, PRE only closes
// open banks, and REF is only issued with all banks precharged
class hbm4_stress_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_stress_seq)
  function new(string name="hbm4_stress_seq"); super.new(name); num_transactions = 500; endfunction
  task body();
    bit        is_open [32];
    bit [15:0] open_row[32];
    int        n_open = 0;
    for (int i = 0; i < 32; i++) begin is_open[i] = 0; open_row[i] = 0; end
    for (int i = 0; i < num_transactions; i++) begin
      int idx  = $urandom_range(0, 31);
      int pick = $urandom_range(0, 99);
      bit [2:0] g = idx[4:2];
      bit [1:0] b = idx[1:0];
      if (!is_open[idx]) begin
        if (pick < 8 && n_open == 0) begin
          do_item(HBM4_CMD_REF);                       // legal: all banks closed
        end
        else begin
          bit [15:0] r = $urandom();
          do_item(HBM4_CMD_ACT, r, 0, g, b);
          is_open[idx] = 1; open_row[idx] = r; n_open++;
        end
      end
      else begin
        if (pick < 40) begin
          do_item(HBM4_CMD_RD, open_row[idx], $urandom_range(0, 1023), g, b);
        end
        else if (pick < 80) begin
          do_item(HBM4_CMD_WR, open_row[idx], $urandom_range(0, 1023), g, b,
                  {$urandom(), $urandom()});
        end
        else begin
          do_item(HBM4_CMD_PRE, 0, 0, g, b);           // close bank (maybe row switch)
          is_open[idx] = 0; n_open--;
          if (pick >= 95) begin
            bit [15:0] r = $urandom();
            do_item(HBM4_CMD_ACT, r, 0, g, b);
            is_open[idx] = 1; open_row[idx] = r; n_open++;
          end
        end
      end
    end
    // Drain: precharge every open bank so the test ends in a clean state
    for (int i = 0; i < 32; i++)
      if (is_open[i]) do_item(HBM4_CMD_PRE, 0, 0, i[4:2], i[1:0]);
  endtask
endclass

// Directed: corner cases -- all-zero / all-one row and column addresses,
// boundary banks and stacks, single-beat accesses at minimum spacing
class hbm4_corner_seq extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_corner_seq)
  function new(string name="hbm4_corner_seq"); super.new(name); endfunction
  task body();
    bit [15:0] rows[4] = '{16'h0000, 16'hFFFF, 16'h0001, 16'hFFFE};
    bit [9:0]  cols[4] = '{10'h000, 10'h3FF, 10'h001, 10'h3FE};
    for (int i = 0; i < 4; i++) begin
      bit [2:0] g = i[2:0];
      bit [1:0] b = i[1:0];
      do_item(HBM4_CMD_ACT, rows[i], 0, g, b, 0, i[2:0]);
      do_item(HBM4_CMD_WR, rows[i], cols[i], g, b, {32'hDEAD_BEEF, 32'h0 + i}, i[2:0]);
      do_item(HBM4_CMD_RD, rows[i], cols[i], g, b, 0, i[2:0]);
      do_item(HBM4_CMD_PRE, 0, 0, g, b);
    end
    do_item(HBM4_CMD_REF);
  endtask
endclass

class hbm4_random_sequence extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_random_sequence)
  function new(string name="hbm4_random_sequence"); super.new(name); num_transactions = 50; endfunction
endclass

// Regression: weighted mix of all directed sequences
class hbm4_regression_sequence extends hbm4_base_sequence;
  `uvm_object_utils(hbm4_regression_sequence)
  function new(string name="hbm4_regression_sequence"); super.new(name); endfunction
  task body();
    hbm4_write_seq         wr  = hbm4_write_seq::type_id::create("wr");
    hbm4_read_seq          rd  = hbm4_read_seq::type_id::create("rd");
    hbm4_refresh_seq       rf  = hbm4_refresh_seq::type_id::create("rf");
    hbm4_bank_conflict_seq bc  = hbm4_bank_conflict_seq::type_id::create("bc");
    hbm4_back_to_back_seq  b2b = hbm4_back_to_back_seq::type_id::create("b2b");
    hbm4_corner_seq        cn  = hbm4_corner_seq::type_id::create("cn");
    hbm4_stress_seq        st  = hbm4_stress_seq::type_id::create("st");
    wr.num_transactions  = 12; rd.num_transactions  = 12; rf.num_transactions = 6;
    bc.num_transactions  = 12; b2b.num_transactions = 6;  st.num_transactions = 200;
    wr.start(m_sequencer);
    rd.start(m_sequencer);
    rf.start(m_sequencer);
    bc.start(m_sequencer);
    b2b.start(m_sequencer);
    cn.start(m_sequencer);
    st.start(m_sequencer);
  endtask
endclass
`endif
