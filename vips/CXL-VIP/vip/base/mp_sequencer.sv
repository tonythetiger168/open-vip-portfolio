// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Sequencer
//============================================================================
`ifndef MP_SEQUENCER_SV
`define MP_SEQUENCER_SV
class mp_sequencer extends uvm_sequencer #(mp_sequence_item);
  `uvm_component_utils(mp_sequencer)
  protocol_e       protocol;
  protocol_cfg_t   cfg;

  function new(string name = "mp_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(protocol_e)::get(this, "", "protocol", protocol))
      protocol = PROTO_PCIE_GEN5;
  endfunction
endclass
`endif
