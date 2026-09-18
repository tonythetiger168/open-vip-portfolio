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

// LPDDR7 Sequencer + Agent
`ifndef LPDDR7_AGENT_SV
`define LPDDR7_AGENT_SV

typedef class lpddr7_driver;
typedef class lpddr7_monitor;

class lpddr7_sequencer extends uvm_sequencer #(lpddr7_transaction);
  `uvm_component_utils(lpddr7_sequencer)
  function new(string name="lpddr7_sequencer", uvm_component parent=null);
    super.new(name, parent);
  endfunction
endclass

class lpddr7_agent extends uvm_agent;
  `uvm_component_utils(lpddr7_agent)
  lpddr7_sequencer sqr;
  lpddr7_driver    drv;
  lpddr7_monitor   mon;
  uvm_analysis_port #(lpddr7_transaction) ap;

  function new(string name="lpddr7_agent", uvm_component parent=null);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon = lpddr7_monitor::type_id::create("mon", this);
    if (get_is_active() == UVM_ACTIVE) begin
      sqr = lpddr7_sequencer::type_id::create("sqr", this);
      drv = lpddr7_driver::type_id::create("drv", this);
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
