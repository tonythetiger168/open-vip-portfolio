// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//============================================================================
//  MIPI Tests
//  mipi_cse_test is the deepened test: runs the full CSE directed sequence
//  library plus the regression mix. Sibling-protocol tests remain smoke
//  tests (their checkers are stubs).
//============================================================================
`ifndef MIPI_TESTS_SV
`define MIPI_TESTS_SV

import uvm_pkg::*;
`include "uvm_macros.svh"
import mipi_vip_pkg::*;

// mipi_env class (resolved via the scripts/Makefile +incdir list)
`include "mipi_env.sv"

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

  virtual task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    #1000;
    phase.drop_objection(this);
  endtask

  function void report_phase(uvm_phase phase);
    uvm_report_server server = uvm_report_server::get_server();
    int err_count = server.get_severity_count(UVM_ERROR);
    if (err_count == 0) `uvm_info(get_type_name(), "TEST PASSED", UVM_LOW)
    else `uvm_error(get_type_name(),
      $sformatf("TEST FAILED with %0d errors", err_count))
  endfunction
endclass

class mipi_csi2_test extends mipi_base_test;
  `uvm_component_utils(mipi_csi2_test)
  function new(string name = "mipi_csi2_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_dsi_test extends mipi_base_test;
  `uvm_component_utils(mipi_dsi_test)
  function new(string name = "mipi_dsi_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_dphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_dphy_test)
  function new(string name = "mipi_dphy_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_cphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_cphy_test)
  function new(string name = "mipi_cphy_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_mphy_test extends mipi_base_test;
  `uvm_component_utils(mipi_mphy_test)
  function new(string name = "mipi_mphy_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_unipro_test extends mipi_base_test;
  `uvm_component_utils(mipi_unipro_test)
  function new(string name = "mipi_unipro_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_digrf_test extends mipi_base_test;
  `uvm_component_utils(mipi_digrf_test)
  function new(string name = "mipi_digrf_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

class mipi_hsi_test extends mipi_base_test;
  `uvm_component_utils(mipi_hsi_test)
  function new(string name = "mipi_hsi_test", uvm_component parent = null); super.new(name, parent); endfunction
  virtual task run_phase(uvm_phase phase); phase.raise_objection(this); #2000; phase.drop_objection(this); endtask
endclass

// Deepened CSE test: full directed library + regression mix
class mipi_cse_test extends mipi_base_test;
  `uvm_component_utils(mipi_cse_test)

  function new(string name = "mipi_cse_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    `uvm_info(get_type_name(), "CSE deep regression start", UVM_LOW)
    begin cse_rd_seq s = cse_rd_seq::type_id::create("s");     s.start(env.agt.sqr); end
    begin cse_wr_reg_seq s = cse_wr_reg_seq::type_id::create("s"); s.start(env.agt.sqr); end
    begin cse_mem_seq s = cse_mem_seq::type_id::create("s");   s.start(env.agt.sqr); end
    begin cse_error_seq s = cse_error_seq::type_id::create("s"); s.start(env.agt.sqr); end
    begin cse_reset_seq s = cse_reset_seq::type_id::create("s"); s.start(env.agt.sqr); end
    begin cse_b2b_seq s = cse_b2b_seq::type_id::create("s");   s.start(env.agt.sqr); end
    begin cse_corner_seq s = cse_corner_seq::type_id::create("s"); s.start(env.agt.sqr); end
    begin cse_stress_seq s = cse_stress_seq::type_id::create("s"); s.num_trans = 32; s.start(env.agt.sqr); end
    begin cse_regression_seq s = cse_regression_seq::type_id::create("s"); s.num_iters = 3; s.start(env.agt.sqr); end
    `uvm_info(get_type_name(), "CSE deep regression complete", UVM_LOW)
    phase.drop_objection(this);
  endtask
endclass

`endif // MIPI_TESTS_SV
