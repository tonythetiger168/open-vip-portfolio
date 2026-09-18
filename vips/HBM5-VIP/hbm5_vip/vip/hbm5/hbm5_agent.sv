// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM agent -- sequencer + driver + monitor
`ifndef HBM5_AGENT_SV
`define HBM5_AGENT_SV

import uvm_pkg::*;
typedef class hbm5_driver;
typedef class hbm5_monitor;

class hbm5_sequencer extends uvm_sequencer #(hbm5_transaction);
  `uvm_component_utils(hbm5_sequencer)
  function new(string name = "hbm5_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass

class hbm5_agent extends uvm_agent;
  `uvm_component_utils(hbm5_agent)
  hbm5_sequencer sqr;
  hbm5_driver    drv;
  hbm5_monitor   mon;

  function new(string name = "hbm5_agent", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon = hbm5_monitor::type_id::create("mon", this);
    if (is_active == UVM_ACTIVE) begin
      sqr = hbm5_sequencer::type_id::create("sqr", this);
      drv = hbm5_driver::type_id::create("drv", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (is_active == UVM_ACTIVE)
      drv.seq_item_port.connect(sqr.seq_item_export);
  endfunction
endclass
`endif
