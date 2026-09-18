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
// can_sequences.svh

class can_base_sequence extends uvm_sequence #(can_transaction);
  `uvm_object_utils(can_base_sequence)
  function new(string name = "can_base_sequence");
    super.new(name);
  endfunction
endclass

class can_random_sequence extends can_base_sequence;
  `uvm_object_utils(can_random_sequence)
  rand int num_txns = 100;
  constraint c_num { num_txns inside {[10:500]}; }
  function new(string name = "can_random_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize()) `uvm_error("RANDFAIL", "CAN tx randomization failed")
      finish_item(tx);
    end
  endtask
endclass

class can_2_0_sequence extends can_base_sequence;
  `uvm_object_utils(can_2_0_sequence)
  rand int num_txns = 50;
  function new(string name = "can_2_0_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { can_type == can_transaction::CAN_2_0; fdf == 0; })
        `uvm_error("RANDFAIL", "CAN 2.0 randomization failed")
      finish_item(tx);
    end
  endtask
endclass

class can_fd_sequence extends can_base_sequence;
  `uvm_object_utils(can_fd_sequence)
  rand int num_txns = 50;
  function new(string name = "can_fd_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { can_type == can_transaction::CAN_FD; fdf == 1; dlc >= 9; })
        `uvm_error("RANDFAIL", "CAN FD randomization failed")
      finish_item(tx);
    end
  endtask
endclass

class can_tt_sequence extends can_base_sequence;
  `uvm_object_utils(can_tt_sequence)
  rand int num_txns = 30;
  function new(string name = "can_tt_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { can_type == can_transaction::CAN_TT; tt_trigger == 1; tt_slot inside {[1:128]}; })
        `uvm_error("RANDFAIL", "CAN TT randomization failed")
      finish_item(tx);
    end
  endtask
endclass

class can_error_inject_sequence extends can_base_sequence;
  `uvm_object_utils(can_error_inject_sequence)
  rand int num_txns = 20;
  function new(string name = "can_error_inject_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { with_error == 1; crc_error == 1; })
        `uvm_error("RANDFAIL", "CAN error inject randomization failed")
      finish_item(tx);
    end
  endtask
endclass

// Directed: back-to-back frames with minimal inter-frame space
class can_back_to_back_sequence extends can_base_sequence;
  `uvm_object_utils(can_back_to_back_sequence)
  rand int num_txns = 64;
  function new(string name = "can_back_to_back_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { can_type == can_transaction::CAN_2_0;
                                 frame_type == can_transaction::DATA_FRAME;
                                 dlc inside {[1:8]}; })
        `uvm_error("RANDFAIL", "CAN b2b randomization failed")
      finish_item(tx);
    end
  endtask
endclass

// Directed: remote transmission request frames
class can_remote_sequence extends can_base_sequence;
  `uvm_object_utils(can_remote_sequence)
  rand int num_txns = 20;
  function new(string name = "can_remote_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { frame_type == can_transaction::REMOTE_FRAME; dlc == 0; })
        `uvm_error("RANDFAIL", "CAN remote randomization failed")
      finish_item(tx);
    end
  endtask
endclass

// Corner case: arbitration extremes (ID 0x000 highest priority, ID max, ext max)
class can_arbitration_sequence extends can_base_sequence;
  `uvm_object_utils(can_arbitration_sequence)
  function new(string name = "can_arbitration_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    bit [28:0] ids[$] = '{29'h00000000, 29'h000007FF, 29'h1FFFFFFF, 29'h15555555, 29'h0AAAAAAA};
    foreach (ids[i]) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { id == ids[i]; ide == (i >= 2); })
        `uvm_error("RANDFAIL", "CAN arbitration randomization failed")
      finish_item(tx);
    end
  endtask
endclass

// Reset behavior: single frame issued right after reset release
class can_reset_sequence extends can_base_sequence;
  `uvm_object_utils(can_reset_sequence)
  function new(string name = "can_reset_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx = can_transaction::type_id::create("tx");
    start_item(tx);
    if (!tx.randomize() with { can_type == can_transaction::CAN_2_0; dlc == 1;
                               data == 64'hA5; })
      `uvm_error("RANDFAIL", "CAN reset randomization failed")
    finish_item(tx);
  endtask
endclass

// Stress: dense traffic with error injection enabled
class can_stress_sequence extends can_base_sequence;
  `uvm_object_utils(can_stress_sequence)
  rand int num_txns = 200;
  function new(string name = "can_stress_sequence");
    super.new(name);
  endfunction
  task body();
    can_transaction tx;
    repeat (num_txns) begin
      tx = can_transaction::type_id::create("tx");
      start_item(tx);
      if (!tx.randomize() with { with_error dist {0:=90, 1:=10}; })
        `uvm_error("RANDFAIL", "CAN stress randomization failed")
      finish_item(tx);
    end
  endtask
endclass

// Regression: weighted mix of all directed sequences
class can_regression_sequence extends can_base_sequence;
  `uvm_object_utils(can_regression_sequence)
  function new(string name = "can_regression_sequence");
    super.new(name);
  endfunction
  task body();
    can_2_0_sequence          c20 = can_2_0_sequence::type_id::create("c20");
    can_fd_sequence           cfd = can_fd_sequence::type_id::create("cfd");
    can_back_to_back_sequence b2b = can_back_to_back_sequence::type_id::create("b2b");
    can_remote_sequence       rtr = can_remote_sequence::type_id::create("rtr");
    can_arbitration_sequence  arb = can_arbitration_sequence::type_id::create("arb");
    can_error_inject_sequence err = can_error_inject_sequence::type_id::create("err");
    can_stress_sequence       st  = can_stress_sequence::type_id::create("st");
    c20.num_txns = 20; cfd.num_txns = 10; b2b.num_txns = 32;
    rtr.num_txns = 10; st.num_txns = 100;
    c20.start(m_sequencer); cfd.start(m_sequencer); b2b.start(m_sequencer);
    rtr.start(m_sequencer); arb.start(m_sequencer);
    err.start(m_sequencer); st.start(m_sequencer);
  endtask
endclass
