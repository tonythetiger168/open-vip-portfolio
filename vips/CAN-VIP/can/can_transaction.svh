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
// can_transaction.svh

class can_transaction extends uvm_sequence_item;
  `uvm_object_utils(can_transaction)

  typedef enum bit [1:0] {
    CAN_2_0 = 2'd0,
    CAN_FD  = 2'd1,
    CAN_TT  = 2'd2
  } can_type_e;

  typedef enum bit [2:0] {
    DATA_FRAME   = 3'd0,
    REMOTE_FRAME = 3'd1,
    ERROR_FRAME  = 3'd2,
    OVERLOAD_FRAME = 3'd3
  } can_frame_type_e;

  rand can_type_e      can_type;
  rand can_frame_type_e frame_type;
  rand bit [28:0]      id;
  rand bit             ide;       // 0=11-bit, 1=29-bit
  rand bit [3:0]       dlc;
  rand bit [63:0]      data;      // up to 64 bytes for CAN FD
  rand int             data_len;
  rand bit             rtr;
  rand bit             fdf;       // FD format
  rand bit             brs;       // bit rate switch
  rand bit             esi;       // error state indicator
  rand bit [14:0]      crc;
  rand bit             tt_trigger;
  rand bit [15:0]      tt_cycle;
  rand bit [7:0]       tt_slot;
  rand bit             with_error;
  rand bit             stuff_error;
  rand bit             crc_error;
  rand bit             form_error;
  rand bit             ack_error;

  constraint c_ide {
    if (can_type == CAN_2_0) ide dist {0:=70, 1:=30};
    else                     ide dist {0:=50, 1:=50};
  }
  constraint c_id {
    if (ide == 0) id[28:11] == 0;
    else          id inside {[0:536870911]};
  }
  constraint c_dlc {
    if (can_type == CAN_2_0)      dlc inside {[0:8]};
    else if (can_type == CAN_FD)  dlc inside {[0:15]};
    else                          dlc inside {[0:15]};
  }
  constraint c_data_len {
    if (can_type == CAN_2_0)      data_len == (dlc <= 8 ? dlc : 8);
    else if (dlc <= 8)            data_len == dlc;
    else if (dlc == 9)            data_len == 12;
    else if (dlc == 10)           data_len == 16;
    else if (dlc == 11)           data_len == 20;
    else if (dlc == 12)           data_len == 24;
    else if (dlc == 13)           data_len == 32;
    else if (dlc == 14)           data_len == 48;
    else if (dlc == 15)           data_len == 64;
  }
  constraint c_rtr {
    if (frame_type == REMOTE_FRAME) rtr == 1;
    else                            rtr == 0;
  }
  constraint c_fdf {
    if (can_type == CAN_2_0) fdf == 0;
    else                     fdf == 1;
  }
  constraint c_brs {
    if (can_type == CAN_2_0) brs == 0;
    else                     brs dist {0:=30, 1:=70};
  }
  constraint c_esi {
    esi dist {0:=90, 1:=10};
  }
  constraint c_error {
    with_error dist {0:=95, 1:=5};
    stuff_error dist {0:=98, 1:=2};
    crc_error   dist {0:=98, 1:=2};
    form_error  dist {0:=98, 1:=2};
    ack_error   dist {0:=98, 1:=2};
  }
  constraint c_tt {
    if (can_type == CAN_TT) tt_trigger == 1;
    else                     tt_trigger == 0;
  }

  function new(string name = "can_transaction");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("CAN: type=%s frame=%s id=0x%0x ide=%b dlc=%0d len=%0d rtr=%b fdf=%b brs=%b esi=%b tt=%b err=%b",
      can_type.name(), frame_type.name(), id, ide, dlc, data_len, rtr, fdf, brs, esi, tt_trigger, with_error);
  endfunction
endclass
