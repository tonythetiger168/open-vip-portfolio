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
// can_coverage.svh

class can_coverage extends coverage_collector_base;
  `uvm_component_utils(can_coverage)
  uvm_analysis_imp #(can_transaction, can_coverage) analysis_export;

  can_transaction tx;

  covergroup can_type_cg;
    option.per_instance = 1;
    type_cp: coverpoint tx.can_type {
      bins can_2_0 = {can_transaction::CAN_2_0};
      bins can_fd  = {can_transaction::CAN_FD};
      bins can_tt  = {can_transaction::CAN_TT};
    }
    frame_cp: coverpoint tx.frame_type {
      bins data    = {can_transaction::DATA_FRAME};
      bins remote  = {can_transaction::REMOTE_FRAME};
      bins error   = {can_transaction::ERROR_FRAME};
      bins overload = {can_transaction::OVERLOAD_FRAME};
    }
    ide_cp: coverpoint tx.ide;
    dlc_cp: coverpoint tx.dlc {
      bins dlc_0_4 = {[0:4]};
      bins dlc_5_8 = {[5:8]};
      bins dlc_fd  = {[9:15]};
    }
    brs_cp: coverpoint tx.brs;
    esi_cp: coverpoint tx.esi;
    error_cp: coverpoint tx.with_error;
    cx_type_frame: cross type_cp, frame_cp;
    cx_type_dlc: cross type_cp, dlc_cp;
    cx_ide_error: cross ide_cp, error_cp;
  endgroup

  covergroup can_error_cg;
    option.per_instance = 1;
    stuff_err_cp: coverpoint tx.stuff_error;
    crc_err_cp:   coverpoint tx.crc_error;
    form_err_cp:  coverpoint tx.form_error;
    ack_err_cp:   coverpoint tx.ack_error;
    cx_stuff_crc: cross stuff_err_cp, crc_err_cp;
  endgroup

  // FSM transition coverage: frame-type sequences on the bus
  covergroup can_fsm_cg;
    option.per_instance = 1;
    frame_trans_cp: coverpoint tx.frame_type {
      bins data_data   = (can_transaction::DATA_FRAME   => can_transaction::DATA_FRAME);
      bins data_remote = (can_transaction::DATA_FRAME   => can_transaction::REMOTE_FRAME);
      bins remote_data = (can_transaction::REMOTE_FRAME => can_transaction::DATA_FRAME);
      bins data_error  = (can_transaction::DATA_FRAME   => can_transaction::ERROR_FRAME);
      bins error_data  = (can_transaction::ERROR_FRAME  => can_transaction::DATA_FRAME);
    }
    type_trans_cp: coverpoint tx.can_type {
      bins c20_fd  = (can_transaction::CAN_2_0 => can_transaction::CAN_FD);
      bins fd_c20  = (can_transaction::CAN_FD  => can_transaction::CAN_2_0);
      bins c20_c20 = (can_transaction::CAN_2_0 => can_transaction::CAN_2_0);
      bins fd_fd   = (can_transaction::CAN_FD  => can_transaction::CAN_FD);
    }
    cx_frame_type: cross frame_trans_cp, type_trans_cp;
  endgroup

  // Data pattern coverage: payload corners x DLC
  covergroup can_data_cg;
    option.per_instance = 1;
    data0_cp: coverpoint tx.data[7:0] iff (tx.data_len > 0) {
      bins zero = {8'h00};
      bins ones = {8'hFF};
      bins aa   = {8'hAA};
      bins five5= {8'h55};
      bins other = default;
    }
    dlc_cp: coverpoint tx.dlc {
      bins d0     = {0};
      bins d1_4   = {[1:4]};
      bins d5_8   = {[5:8]};
      bins d9_15  = {[9:15]};
    }
    cx_data_dlc: cross data0_cp, dlc_cp;
  endgroup

  int sample_count = 0;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    analysis_export = new("analysis_export", this);
    can_type_cg = new();
    can_error_cg = new();
    can_fsm_cg = new();
    can_data_cg = new();
  endfunction
  function void write(can_transaction tx_);
    tx = tx_;
    sample_coverage(tx);
  endfunction
  virtual function void sample_coverage(uvm_sequence_item tx_);
    can_transaction ctx;
    if (!$cast(ctx, tx_)) return;
    tx = ctx;
    can_type_cg.sample();
    can_error_cg.sample();
    can_fsm_cg.sample();
    can_data_cg.sample();
    sample_count++;
  endfunction
  function void report_phase(uvm_phase phase);
    `uvm_info("CAN_COV", $sformatf("Sampled %0d transactions", sample_count), UVM_LOW)
    `uvm_info("CAN_COV", $sformatf("Type coverage = %0.2f%%", can_type_cg.get_coverage()), UVM_LOW)
  endfunction
endclass
