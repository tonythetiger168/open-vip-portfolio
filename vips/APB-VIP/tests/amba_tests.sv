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
// AMBA Tests (APB4 deepened: each test launches a directed APB sequence)
//============================================================================
`ifndef AMBA_TESTS_SV
`define AMBA_TESTS_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import amba_vip_pkg::*;

class amba_base_test extends uvm_test;
  `uvm_component_utils(amba_base_test)
  amba_env env;
  function new(string name = "amba_base_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = amba_env::type_id::create("env", this);
  endfunction
  virtual task run_phase(uvm_phase phase);
    apb_base_sequence seq = apb_base_sequence::type_id::create("seq");
    phase.raise_objection(this);
    seq.start(env.agt.sqr);
    #1000ns;
    phase.drop_objection(this);
  endtask
endclass

// Regression mix of all directed APB sequences
class amba_axi_test extends amba_base_test;
  `uvm_component_utils(amba_axi_test)
  function new(string name = "amba_axi_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    apb_regression_sequence seq = apb_regression_sequence::type_id::create("seq");
    phase.raise_objection(this);
    seq.start(env.agt.sqr);
    #2000ns;
    phase.drop_objection(this);
  endtask
endclass

// Back-to-back + burst stress
class amba_apb_test extends amba_base_test;
  `uvm_component_utils(amba_apb_test)
  function new(string name = "amba_apb_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    apb_write_seq   inc = apb_write_seq::type_id::create("inc");
    apb_back_to_back_seq b2b = apb_back_to_back_seq::type_id::create("b2b");
    apb_read_seq   wrp = apb_read_seq::type_id::create("wrp");
    phase.raise_objection(this);
    inc.start(env.agt.sqr);
    wrp.start(env.agt.sqr);
    b2b.start(env.agt.sqr);
    #2000ns;
    phase.drop_objection(this);
  endtask
endclass

// Error-injection (HRESP ERROR region) + reset behavior
class amba_apb_test extends amba_base_test;
  `uvm_component_utils(amba_apb_test)
  function new(string name = "amba_apb_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  virtual task run_phase(uvm_phase phase);
    apb_error_inject_seq err = apb_error_inject_seq::type_id::create("err");
    apb_reset_seq        rst = apb_reset_seq::type_id::create("rst");
    phase.raise_objection(this);
    err.start(env.agt.sqr);
    rst.start(env.agt.sqr);
    #2000ns;
    phase.drop_objection(this);
  endtask
endclass
`endif
