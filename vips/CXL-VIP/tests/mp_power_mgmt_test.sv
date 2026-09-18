// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Power Management Test: directed random traffic on the Power Management agent
//============================================================================
`ifndef MP_POWER_MGMT_TEST_SV
`define MP_POWER_MGMT_TEST_SV
class mp_power_mgmt_test extends mp_base_test;
  `uvm_component_utils(mp_power_mgmt_test)

  function new(string name = "mp_power_mgmt_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    select_protocol_agent();
    super.build_phase(phase);
  endfunction

  virtual task run_phase(uvm_phase phase);
    mp_power_mgmt_sequence seq;
    phase.raise_objection(this);
    seq = mp_power_mgmt_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.target_protocol  = PROTO_CXL_20;
    seq.start(env.cxl20_agent.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
