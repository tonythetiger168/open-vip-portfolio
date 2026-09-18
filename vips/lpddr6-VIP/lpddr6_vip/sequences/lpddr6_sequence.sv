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

// LPDDR6 UVM Sequence library
// Transaction + directed sequences:
//   base (random) / write / read / back-to-back / precharge+refresh /
//   error-inject (no-ACT access) / reset / corner / regression mix
`ifndef LPDDR6_SEQUENCE_SV
`define LPDDR6_SEQUENCE_SV

import uvm_pkg::*;

// Command encoding driven on {cs_n, act_n, ras_n, cas_n, we_n}
typedef enum bit [2:0] {
  LPDDR6_CMD_NOP = 3'd0,
  LPDDR6_CMD_ACT = 3'd1,   // activate row  (act_n=0)
  LPDDR6_CMD_RD  = 3'd2,   // read  column  (ras_n=1 cas_n=0 we_n=1)
  LPDDR6_CMD_WR  = 3'd3,   // write column  (ras_n=1 cas_n=0 we_n=0)
  LPDDR6_CMD_PRE = 3'd4,   // precharge     (ras_n=0 cas_n=1 we_n=0)
  LPDDR6_CMD_REF = 3'd5    // refresh       (ras_n=0 cas_n=0 we_n=1)
} lpddr6_cmd_e;

class lpddr6_transaction extends uvm_sequence_item;
  `uvm_object_utils(lpddr6_transaction)
  rand lpddr6_cmd_e cmd;
  rand bit [15:0] addr;          // column address on RD/WR, row on ACT
  rand bit [15:0] row;           // row address (ACT)
  rand bit [9:0]  col;           // column address (RD/WR)
  rand bit [63:0] data;          // write burst beat 0
  rand bit [63:0] data2;         // write burst beat 1
  rand bit        we_n;
  rand bit [2:0]  bg;
  rand bit [1:0]  ba;
  rand bit [4:0]  bl;   // widened to 5b: BL16 (16) does not fit in 4 bits
  bit [63:0]      rdata;         // read burst beat 0 (monitor/DUT)
  bit [63:0]      rdata2;        // read burst beat 1
  bit             no_act;        // error injection: skip ACT before RD/WR

  constraint c_bank { bg inside {[0:3]}; }
  constraint c_bl   { bl inside {5'd8, 5'd16}; }
  constraint c_cmd  { cmd dist { LPDDR6_CMD_RD := 40, LPDDR6_CMD_WR := 40,
                                 LPDDR6_CMD_PRE := 10, LPDDR6_CMD_REF := 5,
                                 LPDDR6_CMD_ACT := 5 }; }

  function new(string name="lpddr6_transaction"); super.new(name); endfunction

  function string convert2string();
    return $sformatf("cmd=%s bg=%0d ba=%0d row=0x%04h col=0x%03h data=0x%016h data2=0x%016h bl=%0d",
                     cmd.name(), bg, ba, row, col, data, data2, bl);
  endfunction

  function bit compare_bank_addr(lpddr6_transaction o);
    return (cmd == o.cmd) && (bg == o.bg) && (ba == o.ba) &&
           (row == o.row) && (col == o.col);
  endfunction
endclass

class lpddr6_base_sequence extends uvm_sequence #(lpddr6_transaction);
  `uvm_object_utils(lpddr6_base_sequence)
  rand int num_transactions = 1000;
  function new(string name="lpddr6_base_sequence"); super.new(name); endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("tr_%0d", i));
      start_item(tr);
      if(!tr.randomize()) `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Directed: write bursts (ACT + WR + data)
class lpddr6_write_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_write_seq)
  function new(string name="lpddr6_write_seq"); super.new(name); num_transactions = 50; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("wr_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd == LPDDR6_CMD_WR; }) `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Directed: read bursts (ACT + RD)
class lpddr6_read_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_read_seq)
  function new(string name="lpddr6_read_seq"); super.new(name); num_transactions = 50; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("rd_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd == LPDDR6_CMD_RD; }) `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Directed: back-to-back accesses to the same bank (row-hit / row-miss mix)
class lpddr6_back_to_back_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_back_to_back_seq)
  rand bit [2:0] tgt_bg;
  rand bit [1:0] tgt_ba;
  function new(string name="lpddr6_back_to_back_seq"); super.new(name); num_transactions = 64; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("b2b_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd inside {LPDDR6_CMD_RD, LPDDR6_CMD_WR};
                                bg == tgt_bg; ba == tgt_ba;
                                row inside {[16'h0000:16'h0010]}; })
        `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Directed: precharge + refresh maintenance traffic
class lpddr6_pre_ref_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_pre_ref_seq)
  function new(string name="lpddr6_pre_ref_seq"); super.new(name); num_transactions = 40; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("pre_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd inside {LPDDR6_CMD_PRE, LPDDR6_CMD_REF}; })
        `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Error injection: RD/WR without a preceding ACT (protocol violation probing)
class lpddr6_error_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_error_seq)
  function new(string name="lpddr6_error_seq"); super.new(name); num_transactions = 16; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("err_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd inside {LPDDR6_CMD_RD, LPDDR6_CMD_WR}; })
        `uvm_error("RAND", "Randomization failed")
      tr.no_act = 1;
      finish_item(tr);
    end
  endtask
endclass

// Reset behavior: single access issued right after reset release
class lpddr6_reset_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_reset_seq)
  function new(string name="lpddr6_reset_seq"); super.new(name); num_transactions = 1; endfunction
  task body();
    lpddr6_transaction tr = lpddr6_transaction::type_id::create("rst_tr");
    start_item(tr);
    if(!tr.randomize() with { cmd == LPDDR6_CMD_WR; data == 64'hDEAD_BEEF_CAFE_F00D; })
      `uvm_error("RAND", "Randomization failed")
    finish_item(tr);
  endtask
endclass

// Corner case: max burst length + address extremes
class lpddr6_corner_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_corner_seq)
  function new(string name="lpddr6_corner_seq"); super.new(name); num_transactions = 24; endfunction
  task body();
    lpddr6_transaction tr;
    bit [15:0] rows[$] = '{16'h0000, 16'hFFFF, 16'h5555, 16'hAAAA};
    bit [9:0]  cols[$] = '{10'h000, 10'h3FF, 10'h155, 10'h2AA};
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("cnr_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd inside {LPDDR6_CMD_RD, LPDDR6_CMD_WR};
                                bl == 5'd16;
                                row == rows[i % 4]; col == cols[i % 4]; })
        `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Stress: dense random traffic across all banks
class lpddr6_stress_seq extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_stress_seq)
  function new(string name="lpddr6_stress_seq"); super.new(name); num_transactions = 400; endfunction
  task body();
    lpddr6_transaction tr;
    for(int i=0; i<num_transactions; i++) begin
      tr = lpddr6_transaction::type_id::create($sformatf("st_%0d", i));
      start_item(tr);
      if(!tr.randomize() with { cmd inside {LPDDR6_CMD_RD, LPDDR6_CMD_WR};
                                row inside {[16'h0000:16'h00FF]}; })
        `uvm_error("RAND", "Randomization failed")
      finish_item(tr);
    end
  endtask
endclass

// Regression: weighted mix of all directed sequences
class lpddr6_regression_sequence extends lpddr6_base_sequence;
  `uvm_object_utils(lpddr6_regression_sequence)
  function new(string name="lpddr6_regression_sequence"); super.new(name); endfunction
  task body();
    lpddr6_write_seq       wr  = lpddr6_write_seq::type_id::create("wr");
    lpddr6_read_seq        rd  = lpddr6_read_seq::type_id::create("rd");
    lpddr6_back_to_back_seq b2b = lpddr6_back_to_back_seq::type_id::create("b2b");
    lpddr6_pre_ref_seq     pre = lpddr6_pre_ref_seq::type_id::create("pre");
    lpddr6_corner_seq      cnr = lpddr6_corner_seq::type_id::create("cnr");
    lpddr6_stress_seq      st  = lpddr6_stress_seq::type_id::create("st");
    wr.num_transactions = 30; rd.num_transactions = 30;
    b2b.num_transactions = 40; pre.num_transactions = 20;
    cnr.num_transactions = 16; st.num_transactions = 200;
    wr.start(m_sequencer); rd.start(m_sequencer); b2b.start(m_sequencer);
    pre.start(m_sequencer); cnr.start(m_sequencer); st.start(m_sequencer);
  endtask
endclass
`endif
