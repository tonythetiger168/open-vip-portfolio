// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Regression Sequence
// Orchestrates all directed sequences as a weighted regression mix
//============================================================================
`ifndef MP_REGRESSION_SEQUENCE_SV
`define MP_REGRESSION_SEQUENCE_SV
class mp_regression_sequence extends mp_base_sequence;
  `uvm_object_utils(mp_regression_sequence)

  function new(string name = "mp_regression_sequence");
    super.new(name);
  endfunction

  virtual task body();
    mp_random_sequence       rnd  = mp_random_sequence::type_id::create("rnd");
    mp_back_to_back_sequence b2b  = mp_back_to_back_sequence::type_id::create("b2b");
    mp_stress_sequence       str  = mp_stress_sequence::type_id::create("str");
    mp_corner_case_sequence  cor  = mp_corner_case_sequence::type_id::create("cor");
    mp_error_inject_sequence err  = mp_error_inject_sequence::type_id::create("err");
    rnd.num_transactions = 40; b2b.num_transactions = 30;
    str.num_transactions = 10; err.num_transactions = 15;
    rnd.target_protocol  = target_protocol;
    b2b.target_protocol  = target_protocol;
    str.target_protocol  = target_protocol;
    cor.target_protocol  = target_protocol;
    err.target_protocol  = target_protocol;
    `uvm_info("SEQ", "Starting regression mix: random/b2b/stress/corner/error", UVM_LOW)
    rnd.start(m_sequencer);
    b2b.start(m_sequencer);
    str.start(m_sequencer);
    cor.start(m_sequencer);
    err.start(m_sequencer);
  endtask
endclass
`endif
