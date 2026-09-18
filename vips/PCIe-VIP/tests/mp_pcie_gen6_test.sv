// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// PCIe Gen6 Test: directed random traffic on the PCIe Gen6 agent
//============================================================================
`ifndef MP_PCIE_GEN6_TEST_SV
`define MP_PCIE_GEN6_TEST_SV
class mp_pcie_gen6_test extends mp_base_test;
  `uvm_component_utils(mp_pcie_gen6_test)

  function new(string name = "mp_pcie_gen6_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    uvm_config_db#(bit)::set(this, "env", "enable_pcie_gen5", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_pcie_gen6", 1);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl20", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl30", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_ucie", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_ualink", 0);
    super.build_phase(phase);
  endfunction

  virtual task run_phase(uvm_phase phase);
    mp_random_sequence seq;
    phase.raise_objection(this);
    seq = mp_random_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.target_protocol  = PROTO_PCIE_GEN6;
    seq.start(env.pcie_gen6_agent.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
