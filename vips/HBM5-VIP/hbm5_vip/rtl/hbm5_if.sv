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

// HBM5 Interface Definition
// Complex Protocol | 24 SVAs
`ifndef HBM5_IF_SV
`define HBM5_IF_SV

interface hbm5_if (input logic ck, input logic rst_n);
  logic        cs_n, act_n, ras_n, cas_n, we_n;
  logic [15:0] addr;
  logic [2:0]  bg;
  logic [1:0]  ba;
  logic [6:0]  ca;
  logic [63:0] dq;
  logic [7:0]  dm, dqs_t, dmi_t;
  logic        cke, odt, odt_ca, rdqs;
  logic [3:0]  bl;
  logic [1:0]  wck_ratio, dbim;
  logic        crc_en, ecc_en, pam4_en;
  logic [7:0]  crc, temp_sensor;
  logic [2:0]  pm_state;
  logic        refresh, vrefca_train, wck2ck_train;
  logic [3:0]  dfe_tap, speed_grade;
  logic [7:0]  latency_target;
  logic [31:0] bandwidth;
  logic [2:0]  stack_id;
  logic        same_bank_ref;
  logic [1:0]  fgr_mode;
  logic        lt_done;
  // ---- SVA checker compatibility aliases ----
  logic        dbis;            // DBI strobe activity derived from DBIM mode
  assign dbis = |dbim;
  logic [2:0]  pseudo_ch;       // pseudo-channel index derived from stack_id
  assign pseudo_ch = stack_id;
  logic [4:0]  data_width;      // configured data width per lane (fixed x16)
  assign data_width = 5'd16;
  int          tRCD, tRP, tRAS, tCL;
  clocking cb @(posedge ck);
    output cs_n, act_n, ras_n, cas_n, we_n, addr, bg, ba, ca;
    inout  dq, dm, dqs_t, dmi_t;
    output cke, odt, odt_ca;
    input  rdqs;
  endclocking
  modport DUT (clocking cb, input ck, rst_n);
  modport TB  (clocking cb, input ck, rst_n);
endinterface
`endif
