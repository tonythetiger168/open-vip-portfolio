// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Base Test
//============================================================================
`ifndef MP_BASE_TEST_SV
`define MP_BASE_TEST_SV
class mp_base_test extends uvm_test;
  `uvm_component_utils(mp_base_test)

  mp_env env;
  int unsigned num_transactions = 50;

  function new(string name = "mp_base_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = mp_env::type_id::create("env", this);
  endfunction

  virtual function void select_protocol_agent();
    // default: PCIe Gen5 only
    uvm_config_db#(bit)::set(this, "env", "enable_pcie_gen6", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl20", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_cxl30", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_ucie", 0);
    uvm_config_db#(bit)::set(this, "env", "enable_ualink", 0);
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
