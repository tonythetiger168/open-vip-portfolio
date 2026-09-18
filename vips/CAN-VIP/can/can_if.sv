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
// can_if.sv
// CAN 2.0 / CAN FD / CAN TT Interface

interface can_if (input logic clk, input logic rst_n);
  // Physical layer (differential)
  logic can_tx;
  logic can_rx;
  logic can_en;
  // Arbitration
  logic [10:0] id_std;
  logic [28:0] id_ext;
  logic        ide;       // 0=standard, 1=extended
  logic        rtr;       // remote transmission request
  // Data
  logic [7:0]  data[];
  logic [3:0]  dlc;       // data length code
  logic [14:0] crc;
  logic        crc_delim;
  logic        ack_slot;
  logic        ack_delim;
  // CAN FD specific
  logic        fdf;       // FD frame
  logic        brs;       // bit rate switch
  logic        esi;       // error state indicator
  // CAN TT specific
  logic        tt_trigger;
  logic [15:0] tt_cycle;
  logic [7:0]  tt_slot;
  // Error
  logic        error_frame;
  logic [2:0]  error_count_tx;
  logic [2:0]  error_count_rx;
  logic        bus_off;

  // Frame status (driven by the CAN node model via the DUT modport;
  // referenced by the modports/clocking blocks above and by the SVA
  // compliance checker)
  logic        sof;
  logic        crc_ok;
  logic        overload_frame;

  modport DUT (
    input  clk, rst_n, can_rx, can_en,
    output can_tx, id_std, id_ext, ide, rtr, dlc, crc, crc_delim,
    output ack_slot, ack_delim, fdf, brs, esi, tt_trigger, tt_cycle,
    output tt_slot, error_frame, error_count_tx, error_count_rx, bus_off,
    output sof, crc_ok, overload_frame
  );

  modport TB (
    input  clk, rst_n, can_tx, id_std, id_ext, ide, rtr, dlc, crc,
    input  crc_delim, ack_slot, ack_delim, fdf, brs, esi, tt_trigger,
    input  tt_cycle, tt_slot, error_frame, error_count_tx, error_count_rx, bus_off,
    input  sof, crc_ok, overload_frame,
    output can_rx, can_en
  );

  clocking mon_cb @(posedge clk);
    input can_tx, can_rx, id_std, id_ext, ide, rtr, dlc, fdf, brs, esi;
    input tt_trigger, tt_cycle, tt_slot, error_frame, bus_off;
    input sof, crc_ok, overload_frame;
  endclocking

  clocking drv_cb @(posedge clk);
    output can_rx, can_en;
    input  can_tx, bus_off;
  endclocking
endinterface
