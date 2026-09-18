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

// HBM4 Interface Definition
// Complex Protocol | 22 SVAs
`ifndef HBM4_IF_SV
`define HBM4_IF_SV

interface hbm4_if (input logic ck, input logic rst_n);
  // Command/Address
  logic        cs_n;
  logic        act_n;
  logic        ras_n;
  logic        cas_n;
  logic        we_n;
  logic [15:0] addr;
  logic [2:0]  bg;
  logic [1:0]  ba;
  logic [6:0]  ca;

  // Data
  logic [63:0] dq;
  logic [7:0]  dm;
  logic [7:0]  dqs_t;
  logic [7:0]  dmi_t;

  // Control
  logic        cke;
  logic        odt;
  logic        odt_ca;
  logic        rdqs;

  // Configuration/Status
  logic [3:0]  bl;
  logic [1:0]  wck_ratio;
  logic [1:0]  dbim;
  logic        crc_en;
  logic [7:0]  crc;
  logic [2:0]  pm_state;
  logic        refresh;
  logic        vrefca_train;
  logic [7:0]  temp_sensor;
  logic [3:0]  dfe_tap;
  logic        ecc_en;
  logic        pam4_en;
  logic [2:0]  stack_id;
  logic        same_bank_ref;
  logic [1:0]  fgr_mode;
  logic        wck2ck_train;
  logic [3:0]  speed_grade;
  logic [7:0]  latency_target;
  logic [31:0] bandwidth;

  // Deepening support signals (referenced by checkers/model)
  logic        dbis;        // DBI status
  logic [7:0]  temp;        // junction temperature (deg C)
  logic [4:0]  data_width;  // configured data width per byte lane
  logic        pseudo_ch;   // pseudo-channel select

  // Timing parameters
  int          tRCD;
  int          tRP;
  int          tRAS;
  int          tCL;

  // Clocking blocks
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
