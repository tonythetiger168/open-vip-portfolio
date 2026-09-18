// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Random Regression Test: directed random traffic on the Random Regression agent
//============================================================================
`ifndef MP_RANDOM_REGRESSION_TEST_SV
`define MP_RANDOM_REGRESSION_TEST_SV
class mp_random_regression_test extends mp_base_test;
  `uvm_component_utils(mp_random_regression_test)

  function new(string name = "mp_random_regression_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    select_protocol_agent();
    super.build_phase(phase);
  endfunction

  virtual task run_phase(uvm_phase phase);
    mp_regression_sequence seq;
    phase.raise_objection(this);
    seq = mp_regression_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.target_protocol  = PROTO_CXL_20;
    seq.start(env.cxl20_agent.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
