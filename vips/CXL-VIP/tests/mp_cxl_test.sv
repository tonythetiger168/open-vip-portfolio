// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// CXL 2.0/3.0 Test: directed random traffic on the CXL 2.0/3.0 agent
//============================================================================
`ifndef MP_CXL_TEST_SV
`define MP_CXL_TEST_SV
class mp_cxl_test extends mp_base_test;
  `uvm_component_utils(mp_cxl_test)

  function new(string name = "mp_cxl_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    uvm_config_db#(bit)::set(this, "env", "enable_pcie_gen5", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_pcie_gen6", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl20", 1);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl30", 1);
    uvm_config_db#(bit)::set(this, "env", "enable_ucie", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_ualink", 0);
    super.build_phase(phase);
  endfunction

  virtual task run_phase(uvm_phase phase);
    mp_random_sequence seq;
    phase.raise_objection(this);
    seq = mp_random_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.target_protocol  = PROTO_CXL_20;
    seq.start(env.cxl20_agent.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
