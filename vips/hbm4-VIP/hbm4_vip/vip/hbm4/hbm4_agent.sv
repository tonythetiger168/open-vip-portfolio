// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_agent.sv -- HBM4 UVM agent (sequencer + driver + monitor)

`ifndef HBM4_AGENT_SV
`define HBM4_AGENT_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
typedef class hbm4_driver;
typedef class hbm4_monitor;

class hbm4_agent extends uvm_agent;
  `uvm_component_utils(hbm4_agent)
  uvm_sequencer #(hbm4_transaction) sqr;
  hbm4_driver  drv;
  hbm4_monitor mon;

  function new(string name, uvm_component parent); super.new(name, parent); endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    sqr = uvm_sequencer #(hbm4_transaction)::type_id::create("sqr", this);
    drv = hbm4_driver::type_id::create("drv", this);
    mon = hbm4_monitor::type_id::create("mon", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    drv.seq_item_port.connect(sqr.seq_item_export);
  endfunction
endclass
`endif
