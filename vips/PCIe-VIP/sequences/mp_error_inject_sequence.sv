// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Error Injection Sequence
// Injects poisoned TLPs (EP), ECRC/LCRC-tagged errors and malformed fields
//============================================================================
`ifndef MP_ERROR_INJECT_SEQUENCE_SV
`define MP_ERROR_INJECT_SEQUENCE_SV
class mp_error_inject_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_error_inject_sequence)

  function new(string name = "mp_error_inject_sequence");
    super.new(name);
  endfunction

  virtual task body();
    mp_sequence_item item;
    // poisoned TLPs
    repeat (num_transactions / 3 + 1) begin
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol; txn.ep == 1'b1; })
        `uvm_error("SEQ", "error(ep) randomize failed")
      finish_item(item);
    end
    // explicit error injection flag
    repeat (num_transactions / 3 + 1) begin
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol;
                                   txn.inject_error == 1'b1; })
        `uvm_error("SEQ", "error(inject) randomize failed")
      finish_item(item);
    end
    // TLP digest (TD/ECRC) stress
    repeat (num_transactions / 3 + 1) begin
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol; txn.td == 1'b1; })
        `uvm_error("SEQ", "error(td) randomize failed")
      finish_item(item);
    end
  endtask
endclass
`endif
