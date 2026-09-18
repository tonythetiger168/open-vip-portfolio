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

// LPDDR6 Sequencer + Agent
`ifndef LPDDR6_AGENT_SV
`define LPDDR6_AGENT_SV

typedef class lpddr6_driver;
typedef class lpddr6_monitor;

class lpddr6_sequencer extends uvm_sequencer #(lpddr6_transaction);
  `uvm_component_utils(lpddr6_sequencer)
  function new(string name="lpddr6_sequencer", uvm_component parent=null);
    super.new(name, parent);
  endfunction
endclass

class lpddr6_agent extends uvm_agent;
  `uvm_component_utils(lpddr6_agent)
  lpddr6_sequencer sqr;
  lpddr6_driver    drv;
  lpddr6_monitor   mon;
  uvm_analysis_port #(lpddr6_transaction) ap;

  function new(string name="lpddr6_agent", uvm_component parent=null);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon = lpddr6_monitor::type_id::create("mon", this);
    if (get_is_active() == UVM_ACTIVE) begin
      sqr = lpddr6_sequencer::type_id::create("sqr", this);
      drv = lpddr6_driver::type_id::create("drv", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE)
      drv.seq_item_port.connect(sqr.seq_item_export);
    mon.ap.connect(ap);
  endfunction
endclass
`endif
