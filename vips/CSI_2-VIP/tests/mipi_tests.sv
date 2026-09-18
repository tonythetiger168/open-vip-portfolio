// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mipi_tests.sv -- MIPI Tests (CSI-2)
//============================================================================

`ifndef MIPI_TESTS_SV
`define MIPI_TESTS_SV

class mipi_base_test extends uvm_test;
  `uvm_component_utils(mipi_base_test)

  mipi_env env;

  function new(string name = "mipi_base_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = mipi_env::type_id::create("env", this);
  endfunction

  // start a sequence on the VIP agent sequencer
  virtual task run_seq(mipi_base_sequence seq);
    seq.start(env.agt.sqr);
  endtask

  virtual task run_phase(uvm_phase phase);
    mipi_base_sequence seq = mipi_base_sequence::type_id::create("seq");
    phase.raise_objection(this);
    seq.num_txns = 10;
    run_seq(seq);
    #1000;
    phase.drop_objection(this);
  endtask
endclass

// Directed-sequence smoke test (CSI-2 normal traffic)
class mipi_csi2_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_test)
  function new(string name = "mipi_csi2_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    mipi_normal_seq      nrm = mipi_normal_seq::type_id::create("nrm");
    mipi_back_to_back_seq b2b = mipi_back_to_back_seq::type_id::create("b2b");
    mipi_corner_seq      cor = mipi_corner_seq::type_id::create("cor");
    phase.raise_objection(this);
    nrm.num_txns = 8; b2b.num_txns = 8;
    run_seq(nrm); run_seq(b2b); run_seq(cor);
    #2000;
    phase.drop_objection(this);
  endtask
endclass

// Error-injection test: corrupted ECC/CRC must be caught by monitor + SB
class mipi_csi2_error_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_error_test)
  function new(string name = "mipi_csi2_error_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    mipi_error_seq err = mipi_error_seq::type_id::create("err");
    phase.raise_objection(this);
    err.num_txns = 8;
    run_seq(err);
    #2000;
    phase.drop_objection(this);
  endtask
endclass

// Reset test: traffic immediately after reset release
class mipi_csi2_reset_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_reset_test)
  function new(string name = "mipi_csi2_reset_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    mipi_reset_seq rst = mipi_reset_seq::type_id::create("rst");
    mipi_normal_seq nrm = mipi_normal_seq::type_id::create("nrm");
    phase.raise_objection(this);
    run_seq(rst);
    nrm.num_txns = 4;
    run_seq(nrm);
    #2000;
    phase.drop_objection(this);
  endtask
endclass

// Stress test
class mipi_csi2_stress_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_stress_test)
  function new(string name = "mipi_csi2_stress_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    mipi_stress_seq str = mipi_stress_seq::type_id::create("str");
    phase.raise_objection(this);
    str.num_txns = 20;
    run_seq(str);
    #5000;
    phase.drop_objection(this);
  endtask
endclass

// Full regression: weighted mix of every directed sequence
class mipi_csi2_regression_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_regression_test)
  function new(string name = "mipi_csi2_regression_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    mipi_regression_sequence reg_seq = mipi_regression_sequence::type_id::create("reg_seq");
    phase.raise_objection(this);
    run_seq(reg_seq);
    #5000;
    phase.drop_objection(this);
  endtask
endclass

// Legacy protocol smoke tests (kept API): each runs the base random sequence
// (mipi_csi2_test is the full directed-sequence test above; the legacy
//  duplicate shell is omitted -- duplicate class definitions are illegal)
class mipi_dsi_test extends mipi_base_test;
  `uvm_component_utils(mipi_dsi_test)
  function new(string name = "mipi_dsi_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_dphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_dphy_test)
  function new(string name = "mipi_dphy_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_cphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_cphy_test)
  function new(string name = "mipi_cphy_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_mphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_mphy_test)
  function new(string name = "mipi_mphy_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_unipro_test extends mipi_base_test;
  `uvm_component_utils(mipi_unipro_test)
  function new(string name = "mipi_unipro_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_digrf_test extends mipi_base_test;
  `uvm_component_utils(mipi_digrf_test)
  function new(string name = "mipi_digrf_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_hsi_test extends mipi_base_test;
  `uvm_component_utils(mipi_hsi_test)
  function new(string name = "mipi_hsi_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
class mipi_cse_test extends mipi_base_test;
  `uvm_component_utils(mipi_cse_test)
  function new(string name = "mipi_cse_test", uvm_component parent = null); super.new(name, parent); endfunction
endclass
`endif
