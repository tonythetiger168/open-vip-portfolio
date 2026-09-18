// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// PCIe Gen5 Test: directed random traffic on the PCIe Gen5 agent
//============================================================================
`ifndef MP_PCIE_GEN5_TEST_SV
`define MP_PCIE_GEN5_TEST_SV
class mp_pcie_gen5_test extends mp_base_test;
  `uvm_component_utils(mp_pcie_gen5_test)

  function new(string name = "mp_pcie_gen5_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    select_protocol_agent();
    super.build_phase(phase);
  endfunction

  virtual task run_phase(uvm_phase phase);
    mp_random_sequence seq;
    phase.raise_objection(this);
    seq = mp_random_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.target_protocol  = PROTO_PCIE_GEN5;
    seq.start(env.pcie_gen5_agent.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
