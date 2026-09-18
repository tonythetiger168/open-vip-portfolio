// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM sequence library -- transaction, base sequence and directed
// sequences (R/W, refresh, bank conflict, back-to-back, page hit/miss corner
// cases, stress, regression). All sequences issue protocol-legal command
// orderings (ACT before RD/WR, PRE before re-ACT, REF with banks closed).
`ifndef HBM5_SEQUENCE_SV
`define HBM5_SEQUENCE_SV

import uvm_pkg::*;

// Bank state tracked by the monitor, sampled by functional coverage
typedef enum {B_IDLE, B_ACTIVE} bank_state_e;

class hbm5_transaction extends uvm_sequence_item;
  `uvm_object_utils(hbm5_transaction)

  typedef enum {ACT, READ, WRITE, PRE, REF, NOP} cmd_e;

  rand cmd_e        cmd = NOP;
  rand bit [15:0]   addr;      // ACT: row address; RD/WR: column address
  rand bit [63:0]   data;
  rand bit          we_n;
  rand bit [2:0]    bg;
  rand bit [1:0]    ba;
  rand bit [4:0]    bl;   // widened to 5b: BL16 (16) does not fit in 4 bits
        bit [63:0]  rdata[];   // read data sampled by the driver
        bit         page_hit;  // filled in by the monitor
        bank_state_e bstate;   // bank state before this command (monitor)

  constraint c_bl   { bl inside {8, 16}; }
  constraint c_bg   { bg inside {[0:7]}; }  // full 3b BG range (monitor bank_active[32]=8BGx4BA)
  constraint c_col  { (cmd inside {READ, WRITE}) -> addr[2:0] == 3'b000; }

  function new(string name = "hbm5_transaction");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("HBM5 %s: bg=%0d ba=%0d addr=0x%0h bl=%0d",
                     cmd.name(), bg, ba, addr, bl);
  endfunction
endclass

// Base: random-but-legal ACT -> RD/WR -> PRE rounds, REF every 8th round
class hbm5_base_sequence extends uvm_sequence #(hbm5_transaction);
  `uvm_object_utils(hbm5_base_sequence)
  rand int num_transactions = 1000;
  rand bit [15:0] row;
  rand bit [15:0] col;
  rand bit [2:0]  bg_n;
  rand bit [1:0]  ba_n;
  rand bit        rd_not_wr;
  constraint c_bg_n { bg_n inside {[0:7]}; }  // full 3b BG range
  constraint c_col  { col[2:0] == 3'b000; }
  function new(string name = "hbm5_base_sequence");
    super.new(name);
  endfunction
  // issue one command item
  task issue(hbm5_transaction::cmd_e c, bit [15:0] a, bit [2:0] g, bit [1:0] b);
    hbm5_transaction tr = hbm5_transaction::type_id::create("tr");
    start_item(tr);
    void'(tr.randomize() with { cmd == c; addr == a; bg == g; ba == b; });
    finish_item(tr);
  endtask
  task body();
    int rounds = num_transactions / 3;
    for (int i = 0; i < rounds; i++) begin
      void'(hbm5_base_sequence'(this).randomize(row, col, bg_n, ba_n, rd_not_wr));
      if (i % 8 == 7) issue(hbm5_transaction::REF, 16'h0, 3'h0, 2'h0);
      issue(hbm5_transaction::ACT, row, bg_n, ba_n);
      issue(rd_not_wr ? hbm5_transaction::READ : hbm5_transaction::WRITE,
            col, bg_n, ba_n);
      issue(hbm5_transaction::PRE, 16'h0, bg_n, ba_n);
    end
  endtask
endclass

// Helper: single ACT->access->PRE round to one bank/row
class hbm5_rw_round_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_rw_round_seq)
  function new(string name = "hbm5_rw_round_seq");
    super.new(name);
  endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      void'(hbm5_base_sequence'(this).randomize(row, col, bg_n, ba_n, rd_not_wr));
      issue(hbm5_transaction::ACT, row, bg_n, ba_n);
      issue(rd_not_wr ? hbm5_transaction::READ : hbm5_transaction::WRITE,
            col, bg_n, ba_n);
      issue(hbm5_transaction::PRE, 16'h0, bg_n, ba_n);
    end
  endtask
endclass

// 1) Directed: write rounds (normal write traffic)
class hbm5_write_seq extends hbm5_rw_round_seq;
  `uvm_object_utils(hbm5_write_seq)
  constraint c_wr { rd_not_wr == 0; }
  function new(string name = "hbm5_write_seq");
    super.new(name);
    num_transactions = 20;
  endfunction
endclass

// 2) Directed: read rounds (normal read traffic)
class hbm5_read_seq extends hbm5_rw_round_seq;
  `uvm_object_utils(hbm5_read_seq)
  constraint c_rd { rd_not_wr == 1; }
  function new(string name = "hbm5_read_seq");
    super.new(name);
    num_transactions = 20;
  endfunction
endclass

// 3) Directed: refresh traffic (banks are closed between rounds)
class hbm5_refresh_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_refresh_seq)
  function new(string name = "hbm5_refresh_seq");
    super.new(name);
    num_transactions = 8;
  endfunction
  task body();
    for (int i = 0; i < num_transactions; i++)
      issue(hbm5_transaction::REF, 16'h0, 3'h0, 2'h0);
  endtask
endclass

// 4) Directed: bank conflict -- repeated ACT to the SAME bank forces
//    PRE/ACT turnaround (tRP + tRCD pressure)
class hbm5_bank_conflict_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_bank_conflict_seq)
  function new(string name = "hbm5_bank_conflict_seq");
    super.new(name);
    num_transactions = 10;
  endfunction
  task body();
    bit [15:0] crow = 16'h0100;
    void'(hbm5_base_sequence'(this).randomize(bg_n, ba_n));
    for (int i = 0; i < num_transactions; i++) begin
      issue(hbm5_transaction::ACT, crow, bg_n, ba_n);
      issue(hbm5_transaction::WRITE, 16'h0, bg_n, ba_n);
      issue(hbm5_transaction::PRE, 16'h0, bg_n, ba_n);
      crow = crow + 16'h100;    // next conflict on a new row, same bank
    end
  endtask
endclass

// 5) Directed: back-to-back accesses across different banks (no PRE between,
//    exploits inter-bank parallelism)
class hbm5_back_to_back_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_back_to_back_seq)
  function new(string name = "hbm5_back_to_back_seq");
    super.new(name);
    num_transactions = 8;
  endfunction
  task body();
    bit [15:0] crow = 16'h2000;
    for (int i = 0; i < num_transactions; i++) begin
      for (int b = 0; b < 4; b++)        // activate 4 banks back-to-back
        issue(hbm5_transaction::ACT, crow, 3'h0, b[1:0]);
      for (int b = 0; b < 4; b++) begin  // hammer open banks back-to-back
        issue(hbm5_transaction::WRITE, 16'h0, 3'h0, b[1:0]);
        issue(hbm5_transaction::READ, 16'h0, 3'h0, b[1:0]);
      end
      for (int b = 0; b < 4; b++)
        issue(hbm5_transaction::PRE, 16'h0, 3'h0, b[1:0]);
      crow = crow + 16'h400;
    end
  endtask
endclass

// 6) Corner case: page hit -- one ACT, many RD/WR to the SAME open row
class hbm5_page_hit_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_page_hit_seq)
  function new(string name = "hbm5_page_hit_seq");
    super.new(name);
    num_transactions = 6;
  endfunction
  task body();
    for (int i = 0; i < num_transactions; i++) begin
      void'(hbm5_base_sequence'(this).randomize(row, col, bg_n, ba_n));
      issue(hbm5_transaction::ACT, row, bg_n, ba_n);
      for (int k = 0; k < 4; k++) begin  // column sweep on the open page
        void'(hbm5_base_sequence'(this).randomize(col, rd_not_wr));
        issue(rd_not_wr ? hbm5_transaction::READ : hbm5_transaction::WRITE,
              col, bg_n, ba_n);
      end
      issue(hbm5_transaction::PRE, 16'h0, bg_n, ba_n);
    end
  endtask
endclass

// 7) Corner case: page miss -- every access targets a different row, forcing
//    PRE + ACT per access
class hbm5_page_miss_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_page_miss_seq)
  function new(string name = "hbm5_page_miss_seq");
    super.new(name);
    num_transactions = 10;
  endfunction
  task body();
    bit [15:0] crow = 16'h0;
    void'(hbm5_base_sequence'(this).randomize(bg_n, ba_n));
    for (int i = 0; i < num_transactions; i++) begin
      void'(hbm5_base_sequence'(this).randomize(col, rd_not_wr));
      issue(hbm5_transaction::ACT, crow, bg_n, ba_n);
      issue(rd_not_wr ? hbm5_transaction::READ : hbm5_transaction::WRITE,
            col, bg_n, ba_n);
      issue(hbm5_transaction::PRE, 16'h0, bg_n, ba_n);
      crow = crow + 16'h311;    // every round misses: new row, same bank
    end
  endtask
endclass

// 8) Stress: long legal mix of rounds with random geometry and direction
class hbm5_stress_seq extends hbm5_rw_round_seq;
  `uvm_object_utils(hbm5_stress_seq)
  function new(string name = "hbm5_stress_seq");
    super.new(name);
    num_transactions = 200;
  endfunction
endclass

// Regression: weighted mix of every directed sequence
class hbm5_regression_seq extends hbm5_base_sequence;
  `uvm_object_utils(hbm5_regression_seq)
  function new(string name = "hbm5_regression_seq");
    super.new(name);
  endfunction
  task body();
    hbm5_write_seq         wr   = hbm5_write_seq::type_id::create("wr");
    hbm5_read_seq          rd   = hbm5_read_seq::type_id::create("rd");
    hbm5_refresh_seq       refs = hbm5_refresh_seq::type_id::create("refs");
    hbm5_bank_conflict_seq bc   = hbm5_bank_conflict_seq::type_id::create("bc");
    hbm5_back_to_back_seq  b2b  = hbm5_back_to_back_seq::type_id::create("b2b");
    hbm5_page_hit_seq      hit  = hbm5_page_hit_seq::type_id::create("hit");
    hbm5_page_miss_seq     miss = hbm5_page_miss_seq::type_id::create("miss");
    wr.num_transactions   = 10; rd.num_transactions  = 10;
    refs.num_transactions = 4;  bc.num_transactions  = 5;
    b2b.num_transactions  = 4;  hit.num_transactions = 4;
    miss.num_transactions = 5;
    wr.start(m_sequencer);
    rd.start(m_sequencer);
    hit.start(m_sequencer);
    miss.start(m_sequencer);
    bc.start(m_sequencer);
    b2b.start(m_sequencer);
    refs.start(m_sequencer);
  endtask
endclass
`endif
