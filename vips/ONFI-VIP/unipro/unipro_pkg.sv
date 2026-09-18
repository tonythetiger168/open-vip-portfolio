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
//------------------------------------------------------------------------------
// UNIPRO stub package (minimal sibling protocol for the multi-protocol
// memory_env). Only the ONFI protocol is deepened in this VIP; this stub
// provides the class/sequence API consumed by memory_env_pkg,
// memory_coverage_pkg and memory_test_pkg, plus a pass-through driver that
// publishes items so scoreboard/coverage plumbing stays live.
//------------------------------------------------------------------------------
`ifndef UNIPRO_PKG_SV
`define UNIPRO_PKG_SV

package unipro_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"

  class unipro_seq_item extends uvm_sequence_item;
    `uvm_object_utils(unipro_seq_item)
    rand int unsigned cmd_type;
    rand bit [31:0]   addr;
    rand bit [63:0]   data;

    constraint c_cmd { cmd_type inside {[0:15]}; }

    function new(string name = "unipro_seq_item");
      super.new(name);
    endfunction

    function string convert2string();
      return $sformatf("UNIPRO cmd=%0d addr=0x%0h data=0x%0h", cmd_type, addr, data);
    endfunction
  endclass : unipro_seq_item

  class unipro_cfg extends uvm_object;
    `uvm_object_utils(unipro_cfg)
    uvm_active_passive_enum is_active = UVM_ACTIVE;
    bit has_coverage = 1;

    function new(string name = "unipro_cfg");
      super.new(name);
    endfunction
  endclass : unipro_cfg

  class unipro_sequencer extends uvm_sequencer #(unipro_seq_item);
    `uvm_component_utils(unipro_sequencer)
    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction
  endclass : unipro_sequencer

  // pass-through driver: publishes expected items to drv_ap so the
  // scoreboard / coverage plumbing of memory_env stays exercised.
  class unipro_driver extends uvm_driver #(unipro_seq_item);
    `uvm_component_utils(unipro_driver)
    unipro_cfg cfg;
    uvm_analysis_port #(unipro_seq_item) drv_ap;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      drv_ap = new("drv_ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(unipro_cfg)::get(this, "", "cfg", cfg))
        cfg = unipro_cfg::type_id::create("cfg");
    endfunction

    task run_phase(uvm_phase phase);
      forever begin
        seq_item_port.get_next_item(req);
        #20;
        drv_ap.write(req);
        seq_item_port.item_done();
      end
    endtask
  endclass : unipro_driver

  class unipro_monitor extends uvm_monitor;
    `uvm_component_utils(unipro_monitor)
    uvm_analysis_port #(unipro_seq_item) item_collected_port;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      item_collected_port = new("item_collected_port", this);
    endfunction

    task run_phase(uvm_phase phase);
      // stub protocol: transactions arrive via the driver pass-through link
      forever #1000;
    endtask
  endclass : unipro_monitor

  class unipro_agent extends uvm_agent;
    `uvm_component_utils(unipro_agent)
    unipro_sequencer sqr;
    unipro_driver    drv;
    unipro_monitor   mon;
    unipro_cfg       cfg;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(unipro_cfg)::get(this, "", "cfg", cfg))
        cfg = unipro_cfg::type_id::create("cfg");
      mon = unipro_monitor::type_id::create("mon", this);
      if (cfg.is_active == UVM_ACTIVE) begin
        sqr = unipro_sequencer::type_id::create("sqr", this);
        drv = unipro_driver::type_id::create("drv", this);
      end
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (cfg.is_active == UVM_ACTIVE) begin
        drv.seq_item_port.connect(sqr.seq_item_export);
        // pass-through: driver traffic is re-published on the monitor port
        drv.drv_ap.connect(mon.item_collected_port);
      end
    endfunction
  endclass : unipro_agent

  class unipro_base_seq extends uvm_sequence #(unipro_seq_item);
    `uvm_object_utils(unipro_base_seq)

    function new(string name = "unipro_base_seq");
      super.new(name);
    endfunction

    task send_item(unipro_seq_item item);
      start_item(item);
      finish_item(item);
    endtask
  endclass : unipro_base_seq

  class unipro_rw_seq extends unipro_base_seq;
    `uvm_object_utils(unipro_rw_seq)
    int num_trans = 30;

    function new(string name = "unipro_rw_seq");
      super.new(name);
    endfunction

    task body();
      unipro_seq_item it;
      repeat (num_trans) begin
        it = unipro_seq_item::type_id::create("it");
        if (!it.randomize())
          `uvm_error(get_type_name(), "unipro_rw_seq randomize failed")
        send_item(it);
      end
    endtask
  endclass : unipro_rw_seq

  class unipro_sweep_seq extends unipro_base_seq;
    `uvm_object_utils(unipro_sweep_seq)
    int num_trans = 16;

    function new(string name = "unipro_sweep_seq");
      super.new(name);
    endfunction

    task body();
      for (int c = 0; c < num_trans; c++) begin
        unipro_seq_item it = unipro_seq_item::type_id::create("it");
        it.cmd_type = c;
        it.addr     = c * 16;
        it.data     = 64'hA5A5_0000 + c;
        send_item(it);
      end
    endtask
  endclass : unipro_sweep_seq

  class unipro_cov_msg_seq extends unipro_sweep_seq;
    `uvm_object_utils(unipro_cov_msg_seq)
    function new(string name = "unipro_cov_msg_seq");
      super.new(name);
    endfunction
  endclass : unipro_cov_msg_seq

  class unipro_cov_cport_seq extends unipro_sweep_seq;
    `uvm_object_utils(unipro_cov_cport_seq)
    function new(string name = "unipro_cov_cport_seq");
      super.new(name);
    endfunction
  endclass : unipro_cov_cport_seq

endpackage : unipro_pkg

`endif // UNIPRO_PKG_SV
