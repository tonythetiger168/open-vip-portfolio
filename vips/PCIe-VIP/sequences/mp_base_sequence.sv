// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Base Sequence + directed sequence library
//============================================================================
`ifndef MP_BASE_SEQUENCE_SV
`define MP_BASE_SEQUENCE_SV
class mp_base_sequence extends uvm_sequence #(mp_sequence_item);
  `uvm_object_utils(mp_base_sequence)

  rand int num_transactions = 50;
  rand protocol_e target_protocol;

  constraint c_num_txn { num_transactions inside {[10:1000]}; }

  function new(string name = "mp_base_sequence");
    super.new(name);
  endfunction

  virtual task body();
    `uvm_info("SEQ", $sformatf("Starting %0d transactions for %s",
      num_transactions, target_protocol.name()), UVM_LOW)
    repeat (num_transactions) begin
      mp_sequence_item item;
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol; })
        `uvm_error("SEQ", "Randomization failed")
      finish_item(item);
    end
  endtask
endclass

//============================================================================
// Directed: back-to-back TLPs (no idle cycles between transactions)
//============================================================================
class mp_back_to_back_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_back_to_back_sequence)
  function new(string name = "mp_back_to_back_sequence"); super.new(name); endfunction
  virtual task body();
    mp_sequence_item item;
    repeat (num_transactions) begin
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol;
                                   txn.delay_cycles == 0;
                                   txn.length inside {[4:32]}; })
        `uvm_error("SEQ", "mp_back_to_back_sequence randomize failed")
      finish_item(item);
    end
  endtask
endclass

//============================================================================
// Directed: stress - large payloads across all traffic classes
//============================================================================
class mp_stress_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_stress_sequence)
  function new(string name = "mp_stress_sequence"); super.new(name); endfunction
  virtual task body();
    mp_sequence_item item;
    repeat (num_transactions) begin
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol;
                                   txn.length inside {[512:4096]};
                                   txn.tc inside {[0:7]}; })
        `uvm_error("SEQ", "mp_stress_sequence randomize failed")
      finish_item(item);
    end
  endtask
endclass

//============================================================================
// Directed: corner cases - min/max payload, boundary addresses, poisoned TLPs
//============================================================================
class mp_corner_case_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_corner_case_sequence)
  function new(string name = "mp_corner_case_sequence"); super.new(name); endfunction
  virtual task body();
    mp_sequence_item item;
    // minimum legal payload at address 0
    item = mp_sequence_item::type_id::create("item");
    start_item(item);
    if (!item.randomize() with { txn.protocol == target_protocol;
                                 txn.length == 4; txn.address == 64'h0; })
      `uvm_error("SEQ", "corner(min) randomize failed")
    finish_item(item);
    // maximum payload at top of the 32-bit address space
    item = mp_sequence_item::type_id::create("item");
    start_item(item);
    if (!item.randomize() with { txn.protocol == target_protocol;
                                 txn.length == 4096;
                                 txn.address[31:0] == 32'hFFFF_F000; })
      `uvm_error("SEQ", "corner(max) randomize failed")
    finish_item(item);
    // poisoned TLP
    item = mp_sequence_item::type_id::create("item");
    start_item(item);
    if (!item.randomize() with { txn.protocol == target_protocol; txn.ep == 1'b1; })
      `uvm_error("SEQ", "corner(poison) randomize failed")
    finish_item(item);
  endtask
endclass

//============================================================================
// Directed: reset behavior - one transaction issued right after reset release
//============================================================================
class mp_reset_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_reset_sequence)
  function new(string name = "mp_reset_sequence"); super.new(name); endfunction
  virtual task body();
    mp_sequence_item item;
    item = mp_sequence_item::type_id::create("item");
    start_item(item);
    if (!item.randomize() with { txn.protocol == target_protocol;
                                 txn.length == 4; txn.delay_cycles == 0; })
      `uvm_error("SEQ", "mp_reset_sequence randomize failed")
    finish_item(item);
  endtask
endclass
`endif
