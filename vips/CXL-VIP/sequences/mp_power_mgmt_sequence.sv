// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Power Management Sequence
// Exercises ASPM L0s/L1 entry-exit windows via inter-TLP idle gaps and the
// pm_request/pm_state sideband between transaction bursts.
//============================================================================
`ifndef MP_POWER_MGMT_SEQUENCE_SV
`define MP_POWER_MGMT_SEQUENCE_SV
class mp_power_mgmt_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_power_mgmt_sequence)

  rand int num_idle_cycles;
  constraint c_idle { num_idle_cycles inside {[50:500]}; }

  function new(string name = "mp_power_mgmt_sequence");
    super.new(name);
  endfunction

  virtual task body();
    mp_sequence_item item;
    repeat (num_transactions) begin
      // short burst of traffic
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol;
                                   txn.length inside {[4:64]};
                                   txn.delay_cycles == 0; })
        `uvm_error("SEQ", "pm burst randomize failed")
      finish_item(item);
      // idle window models L0s/L1 residency before the next burst
      item = mp_sequence_item::type_id::create("item");
      start_item(item);
      if (!item.randomize() with { txn.protocol == target_protocol;
                                   txn.delay_cycles == num_idle_cycles; })
        `uvm_error("SEQ", "pm idle randomize failed")
      finish_item(item);
    end
  endtask
endclass
`endif
