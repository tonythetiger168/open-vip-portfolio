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

// LPDDR7 UVM Tests
`ifndef LPDDR7_TEST_SV
`define LPDDR7_TEST_SV

class lpddr7_base_test extends uvm_test;
  `uvm_component_utils(lpddr7_base_test)
  lpddr7_env env;
  int num_transactions = 100;
  function new(string name="lpddr7_base_test", uvm_component parent=null); super.new(name, parent); endfunction
  function void build_phase(uvm_phase phase); super.build_phase(phase); env = lpddr7_env::type_id::create("env", this); endfunction
  task run_phase(uvm_phase phase);
    lpddr7_base_sequence seq;
    phase.raise_objection(this);
    seq = lpddr7_base_sequence::type_id::create("seq");
    seq.num_transactions = num_transactions;
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Directed write/read traffic
class lpddr7_rw_test extends lpddr7_base_test;
  `uvm_component_utils(lpddr7_rw_test)
  function new(string name="lpddr7_rw_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    lpddr7_write_seq wr;
    lpddr7_read_seq  rd;
    phase.raise_objection(this);
    wr = lpddr7_write_seq::type_id::create("wr");
    rd = lpddr7_read_seq::type_id::create("rd");
    wr.start(env.agt.sqr);
    rd.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Back-to-back same-bank stress
class lpddr7_back_to_back_test extends lpddr7_base_test;
  `uvm_component_utils(lpddr7_back_to_back_test)
  function new(string name="lpddr7_back_to_back_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    lpddr7_back_to_back_seq seq;
    phase.raise_objection(this);
    seq = lpddr7_back_to_back_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Error injection (RD/WR without ACT)
class lpddr7_error_test extends lpddr7_base_test;
  `uvm_component_utils(lpddr7_error_test)
  function new(string name="lpddr7_error_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    lpddr7_error_seq seq;
    phase.raise_objection(this);
    seq = lpddr7_error_seq::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass

// Full regression mix
class lpddr7_regression_test extends lpddr7_base_test;
  `uvm_component_utils(lpddr7_regression_test)
  function new(string name="lpddr7_regression_test", uvm_component parent=null); super.new(name, parent); endfunction
  task run_phase(uvm_phase phase);
    lpddr7_regression_sequence seq;
    phase.raise_objection(this);
    seq = lpddr7_regression_sequence::type_id::create("seq");
    seq.start(env.agt.sqr);
    phase.drop_objection(this);
  endtask
endclass
`endif
