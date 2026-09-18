// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_sequences.svh -- APB4 sequence library:
//   base / write / read / back-to-back / wait-state / error-inject /
//   reset / stress / regression mix

`ifndef APB_SEQUENCES_SVH
`define APB_SEQUENCES_SVH

class apb_base_sequence extends uvm_sequence #(amba_seq_item);
  `uvm_object_utils(apb_base_sequence)
  int num_txns = 20;
  function new(string name = "apb_base_sequence");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4;
                                    txn.addr[1:0] == 2'b00;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: write bursts to the register bank
class apb_write_seq extends apb_base_sequence;
  `uvm_object_utils(apb_write_seq)
  function new(string name = "apb_write_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4; txn.write == 1;
                                    txn.addr[1:0] == 2'b00;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: read bursts of varying length
class apb_read_seq extends apb_base_sequence;
  `uvm_object_utils(apb_read_seq)
  function new(string name = "apb_read_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4; txn.write == 0;
                                    txn.len inside {[1:8]};
                                    txn.addr[1:0] == 2'b00;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: back-to-back single transfers with zero gap
class apb_back_to_back_seq extends apb_base_sequence;
  `uvm_object_utils(apb_back_to_back_seq)
  function new(string name = "apb_back_to_back_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4; txn.len == 1;
                                    txn.delay == 0;
                                    txn.addr[1:0] == 2'b00;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: wait-state region accesses (PREADY delayed, paddr[7:4]==4'hF)
class apb_wait_state_seq extends apb_base_sequence;
  `uvm_object_utils(apb_wait_state_seq)
  function new(string name = "apb_wait_state_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4;
                                    txn.addr[7:4] == 4'hF;
                                    txn.addr[1:0] == 2'b00;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Error injection: PSLVERR region (0xEE00_0000)
class apb_error_inject_seq extends apb_base_sequence;
  `uvm_object_utils(apb_error_inject_seq)
  function new(string name = "apb_error_inject_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == APB4;
                                    txn.addr[31:24] == 8'hEE;
                                    txn.len == 1; });
      finish_item(item);
    end
  endtask
endclass

// Reset behavior: single transfer right after reset release
class apb_reset_seq extends apb_base_sequence;
  `uvm_object_utils(apb_reset_seq)
  function new(string name = "apb_reset_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item = amba_seq_item::type_id::create("item");
    start_item(item);
    void'(item.randomize() with { txn.protocol == APB4; txn.len == 1;
                                  txn.addr[1:0] == 2'b00;
                                  txn.addr[31:24] != 8'hEE; });
    finish_item(item);
  endtask
endclass

// Stress: high-volume random bursts
class apb_stress_seq extends apb_base_sequence;
  `uvm_object_utils(apb_stress_seq)
  function new(string name = "apb_stress_seq");
    super.new(name);
    num_txns = 100;
  endfunction
endclass

// Random sequence (compatibility name)
class apb_random_sequence extends apb_base_sequence;
  `uvm_object_utils(apb_random_sequence)
  function new(string name = "apb_random_sequence");
    super.new(name);
    num_txns = 50;
  endfunction
endclass

// Regression: weighted mix of all directed sequences
class apb_regression_sequence extends apb_base_sequence;
  `uvm_object_utils(apb_regression_sequence)
  function new(string name = "apb_regression_sequence");
    super.new(name);
  endfunction
  task body();
    apb_write_seq        wr  = apb_write_seq::type_id::create("wr");
    apb_read_seq         rd  = apb_read_seq::type_id::create("rd");
    apb_back_to_back_seq b2b = apb_back_to_back_seq::type_id::create("b2b");
    apb_wait_state_seq   ws  = apb_wait_state_seq::type_id::create("ws");
    apb_error_inject_seq err = apb_error_inject_seq::type_id::create("err");
    apb_stress_seq       str = apb_stress_seq::type_id::create("str");
    wr.num_txns = 20; rd.num_txns = 20; b2b.num_txns = 20;
    ws.num_txns = 10; err.num_txns = 5; str.num_txns = 40;
    wr.start(m_sequencer);  rd.start(m_sequencer);
    b2b.start(m_sequencer); ws.start(m_sequencer);
    err.start(m_sequencer); str.start(m_sequencer);
  endtask
endclass
`endif
