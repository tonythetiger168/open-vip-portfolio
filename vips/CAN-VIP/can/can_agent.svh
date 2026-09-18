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
// can_agent.svh

class can_agent extends uvm_agent;
  `uvm_component_utils(can_agent)
  can_sequencer  sqr;
  can_driver     drv;
  can_monitor    mon;
  can_checker    chk;
  can_coverage   cov;
  can_config     cfg;
  uvm_analysis_port #(can_transaction) ap;
  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(can_config)::get(this, "", "cfg", cfg))
      cfg = can_config::type_id::create("cfg");
    mon = can_monitor::type_id::create("mon", this);
    if (get_is_active() == UVM_ACTIVE) begin
      sqr = can_sequencer::type_id::create("sqr", this);
      drv = can_driver::type_id::create("drv", this);
    end
    if (cfg.enable_checker)  chk = can_checker::type_id::create("chk", this);
    if (cfg.enable_coverage) cov = can_coverage::type_id::create("cov", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE)
      drv.seq_item_port.connect(sqr.seq_item_export);
    mon.ap.connect(ap);
    if (cfg.enable_checker)  mon.ap.connect(chk.analysis_export);
    if (cfg.enable_coverage) mon.ap.connect(cov.analysis_export);
  endfunction
endclass
