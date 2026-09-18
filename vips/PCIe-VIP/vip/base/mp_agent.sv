// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Agent
//============================================================================
`ifndef MP_AGENT_SV
`define MP_AGENT_SV
class mp_agent extends uvm_agent;
  `uvm_component_utils(mp_agent)

  mp_sequencer    sqr;
  mp_driver       drv;
  mp_monitor      mon;
  protocol_e      protocol;
  protocol_cfg_t  cfg;
  bit             is_active = 1;  // UVM_ACTIVE / UVM_PASSIVE

  function new(string name = "mp_agent", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(protocol_e)::get(this, "", "protocol", protocol))
      protocol = PROTO_PCIE_GEN5;
    if (!uvm_config_db#(bit)::get(this, "", "is_active", is_active))
      is_active = 1;

    // Create monitor (always present)
    mon = mp_monitor::type_id::create("mon", this);

    // Create sequencer and driver only for active agents
    if (is_active) begin
      sqr = mp_sequencer::type_id::create("sqr", this);
      drv = mp_driver::type_id::create("drv", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (is_active)
      drv.seq_item_port.connect(sqr.seq_item_export);
  endfunction

  function void end_of_elaboration_phase(uvm_phase phase);
    super.end_of_elaboration_phase(phase);
    if (sqr != null) uvm_config_db#(protocol_e)::set(sqr, "", "protocol", protocol);
    if (drv != null) uvm_config_db#(protocol_e)::set(drv, "", "protocol", protocol);
    if (mon != null) uvm_config_db#(protocol_e)::set(mon, "", "protocol", protocol);
    if (drv != null) uvm_config_db#(protocol_cfg_t)::set(drv, "", "cfg", cfg);
    if (mon != null) uvm_config_db#(protocol_cfg_t)::set(mon, "", "cfg", cfg);
  endfunction
endclass
`endif
