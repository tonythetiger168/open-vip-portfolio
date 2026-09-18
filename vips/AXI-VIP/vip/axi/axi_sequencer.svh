// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axi_sequencer.svh -- AXI4 master sequencer

`ifndef AXI_SEQUENCER_SVH
`define AXI_SEQUENCER_SVH

class axi_sequencer extends uvm_sequencer #(amba_seq_item);
  `uvm_component_utils(axi_sequencer)
  function new(string name = "axi_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
`endif
