// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// hbm4_test.sv -- HBM4 UVM tests

`ifndef HBM4_TEST_SV
`define HBM4_TEST_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

class hbm4_base_test extends uvm_test;
  `uvm_component_utils(hbm4_base_test)
  hbm4_env env;
  function new(string name="hbm4_base_test", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = hbm4_env::type_id::create("env", this);
  endfunction
  task run_phase(uvm_phase phase);
    hbm4_regression_sequence seq;
    phase.raise_objection(this);
    seq = hbm4_regression_sequence::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Directed smoke test: write flow only
class hbm4_write_test extends hbm4_base_test;
  `uvm_component_utils(hbm4_write_test)
  function new(string name="hbm4_write_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    hbm4_write_seq seq;
    phase.raise_objection(this);
    seq = hbm4_write_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Directed smoke test: read flow + refresh flow
class hbm4_read_test extends hbm4_base_test;
  `uvm_component_utils(hbm4_read_test)
  function new(string name="hbm4_read_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    hbm4_read_seq    rd;
    hbm4_refresh_seq rf;
    phase.raise_objection(this);
    rd = hbm4_read_seq::type_id::create("rd");
    rf = hbm4_refresh_seq::type_id::create("rf");
    rd.start(env.agt.sqr);
    rf.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Stress test: long protocol-legal random stream
class hbm4_stress_test extends hbm4_base_test;
  `uvm_component_utils(hbm4_stress_test)
  function new(string name="hbm4_stress_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    hbm4_stress_seq seq;
    phase.raise_objection(this);
    seq = hbm4_stress_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
