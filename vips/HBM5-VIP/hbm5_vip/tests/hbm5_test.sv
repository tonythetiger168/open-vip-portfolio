// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// HBM5 UVM tests
`ifndef HBM5_TEST_SV
`define HBM5_TEST_SV

class hbm5_base_test extends uvm_test;
  `uvm_component_utils(hbm5_base_test)
  hbm5_env env;
  function new(string name = "hbm5_base_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = hbm5_env::type_id::create("env", this);
  endfunction
  task run_phase(uvm_phase phase);
    hbm5_base_sequence seq;
    phase.raise_objection(this);
    seq = hbm5_base_sequence::type_id::create("seq");
    seq.num_transactions = 100;
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Directed regression: every directed sequence in turn
class hbm5_directed_test extends hbm5_base_test;
  `uvm_component_utils(hbm5_directed_test)
  function new(string name = "hbm5_directed_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    hbm5_regression_seq seq;
    phase.raise_objection(this);
    seq = hbm5_regression_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Stress: long randomized command mix
class hbm5_stress_test extends hbm5_base_test;
  `uvm_component_utils(hbm5_stress_test)
  function new(string name = "hbm5_stress_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    hbm5_stress_seq seq;
    phase.raise_objection(this);
    seq = hbm5_stress_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
