// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axi_sequences.svh -- AXI4 sequence library:
//   base / single / incr burst / wrap burst / back-to-back /
//   error-inject (SLVERR region) / reset / stress / regression mix

`ifndef AXI_SEQUENCES_SVH
`define AXI_SEQUENCES_SVH

class axi_base_sequence extends uvm_sequence #(amba_seq_item);
  `uvm_object_utils(axi_base_sequence)
  int num_txns = 20;
  function new(string name = "axi_base_sequence");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.addr[2:0] == 3'b000;
                                    txn.addr[31:24] != 8'hEE;
                                    txn.size == SIZE_8B; });
      finish_item(item);
    end
  endtask
endclass

// Directed: single-beat transfers
class axi_single_seq extends axi_base_sequence;
  `uvm_object_utils(axi_single_seq)
  function new(string name = "axi_single_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4; txn.len == 1;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: INCR bursts (4/8/16 beats)
class axi_incr_burst_seq extends axi_base_sequence;
  `uvm_object_utils(axi_incr_burst_seq)
  function new(string name = "axi_incr_burst_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.burst == BURST_INCR;
                                    txn.len inside {4, 8, 16};
                                    txn.addr[3:0] == 4'h0;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: WRAP bursts (cache-line corner case)
class axi_wrap_burst_seq extends axi_base_sequence;
  `uvm_object_utils(axi_wrap_burst_seq)
  function new(string name = "axi_wrap_burst_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.burst == BURST_WRAP;
                                    txn.len inside {2, 4, 8, 16};
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Directed: back-to-back transfers with zero gap
class axi_back_to_back_seq extends axi_base_sequence;
  `uvm_object_utils(axi_back_to_back_seq)
  function new(string name = "axi_back_to_back_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.len inside {[1:2]};
                                    txn.delay == 0;
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Error injection: SLVERR region (0xEE00_0000)
class axi_error_inject_seq extends axi_base_sequence;
  `uvm_object_utils(axi_error_inject_seq)
  function new(string name = "axi_error_inject_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.addr[31:24] == 8'hEE;
                                    txn.len == 1; });
      finish_item(item);
    end
  endtask
endclass

// Reset behavior: transfer right after reset release
class axi_reset_seq extends axi_base_sequence;
  `uvm_object_utils(axi_reset_seq)
  function new(string name = "axi_reset_seq");
    super.new(name);
  endfunction
  task body();
    amba_seq_item item = amba_seq_item::type_id::create("item");
    start_item(item);
    void'(item.randomize() with { txn.protocol == AXI4; txn.len == 1;
                                  txn.addr[31:24] != 8'hEE; });
    finish_item(item);
  endtask
endclass

// Stress: high-volume random bursts
class axi_stress_seq extends axi_base_sequence;
  `uvm_object_utils(axi_stress_seq)
  function new(string name = "axi_stress_seq");
    super.new(name);
    num_txns = 100;
  endfunction
  task body();
    amba_seq_item item;
    repeat (num_txns) begin
      item = amba_seq_item::type_id::create("item");
      start_item(item);
      void'(item.randomize() with { txn.protocol == AXI4;
                                    txn.len inside {[4:16]};
                                    txn.addr[31:24] != 8'hEE; });
      finish_item(item);
    end
  endtask
endclass

// Random sequence (compatibility name)
class axi_random_sequence extends axi_base_sequence;
  `uvm_object_utils(axi_random_sequence)
  function new(string name = "axi_random_sequence");
    super.new(name);
    num_txns = 50;
  endfunction
endclass

// Regression: weighted mix of all directed sequences
class axi_regression_sequence extends axi_base_sequence;
  `uvm_object_utils(axi_regression_sequence)
  function new(string name = "axi_regression_sequence");
    super.new(name);
  endfunction
  task body();
    axi_single_seq       sgl = axi_single_seq::type_id::create("sgl");
    axi_incr_burst_seq   inc = axi_incr_burst_seq::type_id::create("inc");
    axi_wrap_burst_seq   wrp = axi_wrap_burst_seq::type_id::create("wrp");
    axi_back_to_back_seq b2b = axi_back_to_back_seq::type_id::create("b2b");
    axi_error_inject_seq err = axi_error_inject_seq::type_id::create("err");
    axi_stress_seq       str = axi_stress_seq::type_id::create("str");
    sgl.num_txns = 20; inc.num_txns = 15; wrp.num_txns = 10;
    b2b.num_txns = 20; err.num_txns = 5;  str.num_txns = 40;
    sgl.start(m_sequencer); inc.start(m_sequencer);
    wrp.start(m_sequencer); b2b.start(m_sequencer);
    err.start(m_sequencer); str.start(m_sequencer);
  endtask
endclass
`endif
