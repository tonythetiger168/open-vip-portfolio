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
// can_checker.svh

class can_checker extends protocol_checker_base;
  `uvm_component_utils(can_checker)
  uvm_analysis_imp #(can_transaction, can_checker) analysis_export;
  int tx_count = 0;
  function new(string name, uvm_component parent);
    super.new(name, parent);
    analysis_export = new("analysis_export", this);
  endfunction
  function void write(can_transaction tx);
    tx_count++;
    check_id(tx);
    check_dlc(tx);
    check_rtr_data(tx);
    check_brs(tx);
    check_tt(tx);
    check_crc(tx);
    check_esi(tx);
  endfunction
  function void check_id(can_transaction tx);
    if (tx.ide == 0 && tx.id[28:11] != 0)
      check_protocol_error($sformatf("Standard ID 0x%0x has non-zero extended bits", tx.id));
    if (tx.ide == 1 && tx.id > 29'h1FFFFFFF)
      check_protocol_error($sformatf("Extended ID 0x%0x exceeds 29 bits", tx.id));
  endfunction
  function void check_dlc(can_transaction tx);
    if (tx.can_type == can_transaction::CAN_2_0 && tx.dlc > 8)
      check_protocol_error($sformatf("CAN 2.0 DLC %0d > 8", tx.dlc));
    if (tx.dlc > 15)
      check_protocol_error($sformatf("DLC %0d > 15", tx.dlc));
  endfunction
  function void check_rtr_data(can_transaction tx);
    if (tx.rtr == 1 && tx.dlc > 0)
      check_protocol_warning("Remote frame with non-zero DLC");
  endfunction
  function void check_brs(can_transaction tx);
    if (tx.can_type == can_transaction::CAN_2_0 && tx.brs == 1)
      check_protocol_error("BRS set in CAN 2.0 frame");
  endfunction
  function void check_tt(can_transaction tx);
    if (tx.can_type != can_transaction::CAN_TT && tx.tt_trigger == 1)
      check_protocol_warning("TT trigger set in non-TT frame");
    if (tx.can_type == can_transaction::CAN_TT && tx.tt_slot > 128)
      check_protocol_warning($sformatf("TT slot %0d > 128", tx.tt_slot));
  endfunction
  function void check_crc(can_transaction tx);
    if (tx.crc_error)
      check_protocol_error("CRC error detected");
  endfunction
  function void check_esi(can_transaction tx);
    if (tx.esi == 1 && tx.can_type == can_transaction::CAN_2_0)
      check_protocol_warning("ESI set in CAN 2.0 frame");
  endfunction
  task run_phase(uvm_phase phase); endtask
  function void report_phase(uvm_phase phase);
    `uvm_info("CAN_CHK", $sformatf("Checked %0d transactions, %0d errors, %0d warnings",
      tx_count, error_count, warning_count), UVM_LOW)
  endfunction
endclass
