// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_agent.svh -- APB4 master agent (sequencer + driver + monitor)

`ifndef APB_AGENT_SVH
`define APB_AGENT_SVH

class apb_agent extends uvm_agent;
  `uvm_component_utils(apb_agent)
  apb_sequencer sqr;
  apb_driver    drv;
  apb_monitor   mon;
  uvm_analysis_port #(amba_seq_item) ap;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon = apb_monitor::type_id::create("mon", this);
    if (get_is_active() == UVM_ACTIVE) begin
      sqr = apb_sequencer::type_id::create("sqr", this);
      drv = apb_driver::type_id::create("drv", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE)
      drv.seq_item_port.connect(sqr.seq_item_export);
    mon.ap.connect(ap);
  endfunction
endclass
`endif
