// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_sequencer.svh -- APB4 master sequencer

`ifndef APB_SEQUENCER_SVH
`define APB_SEQUENCER_SVH

class apb_sequencer extends uvm_sequencer #(amba_seq_item);
  `uvm_component_utils(apb_sequencer)
  function new(string name = "apb_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
`endif
