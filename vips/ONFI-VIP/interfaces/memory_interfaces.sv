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
// Memory/Storage Protocol Interfaces with UVM Clocking Blocks
// 8 Protocols: DDR4/5, LPDDR4/5/6, HBM2/2E/3, UFS, UniPro, eMMC, ONFI, SD/SDIO
//------------------------------------------------------------------------------
`ifndef MEMORY_INTERFACES_SV
`define MEMORY_INTERFACES_SV

interface ddr_if #(
  parameter ADDR_WIDTH = 17,
  parameter DATA_WIDTH = 64,
  parameter DQ_WIDTH   = 64,
  parameter DQS_WIDTH  = 8
)(
  input logic ck,
  input logic ck_n,
  input logic rst_n
);
  // Command/Address
  logic [ADDR_WIDTH-1:0] addr;
  logic [2:0]            ba;      // Bank address
  logic [1:0]            bg;      // Bank group (DDR5)
  logic                  ras_n;   // Row address strobe
  logic                  cas_n;   // Column address strobe
  logic                  we_n;    // Write enable
  logic                  cs_n;    // Chip select
  logic                  cke;     // Clock enable
  logic                  odt;     // On-die termination
  logic                  act_n;   // Activation command (DDR4)
  // Data
  logic [DQ_WIDTH-1:0]   dq;
  logic [DQS_WIDTH-1:0]  dqs;
  logic [DQS_WIDTH-1:0]  dqs_n;
  logic [DATA_WIDTH/8-1:0] dm;    // Data mask
  // Timing parameters (for VIP reference)
  int tRCD = 15;  // RAS to CAS delay
  int tRP  = 15;  // Row precharge time
  int tRAS = 35;  // Row active time
  int tRC  = 50;  // Row cycle time
  int tCL  = 15;  // CAS latency
  int tCWL = 14;  // CAS write latency

  clocking drv_cb @(posedge ck);
    default input #0.5 output #0.5;
    output addr, ba, bg, ras_n, cas_n, we_n, cs_n, cke, odt, act_n;
    inout  dq, dqs, dqs_n, dm;
  endclocking

  clocking mon_cb @(posedge ck);
    default input #0.5 output #0.5;
    input addr, ba, bg, ras_n, cas_n, we_n, cs_n, cke, odt, act_n;
    input dq, dqs, dqs_n, dm;
  endclocking

  modport driver  (clocking drv_cb, input ck, ck_n, rst_n);
  modport monitor (clocking mon_cb, input ck, ck_n, rst_n);
endinterface : ddr_if

interface lpddr_if #(
  parameter ADDR_WIDTH = 16,
  parameter DATA_WIDTH = 32,
  parameter CA_WIDTH   = 6
)(
  input logic ck,
  input logic ck_n,
  input logic cke,
  input logic rst_n
);
  // Command/Address (CA bus is shared)
  logic [CA_WIDTH-1:0] ca;
  logic                cs;  // Chip select
  // Data
  logic [DATA_WIDTH-1:0]   dq;
  logic [DATA_WIDTH/8-1:0] dqs;
  logic [DATA_WIDTH/8-1:0] dqs_n;
  logic [DATA_WIDTH/8-1:0] dm;
  // LPDDR-specific signals
  logic                  dmi;   // Data mask/inversion
  // Timing
  int tRCD = 18;
  int tRP  = 18;
  int tRAS = 42;
  int tCL  = 22;
  int tCWL = 11;

  clocking drv_cb @(posedge ck);
    default input #0.5 output #0.5;
    output ca, cs;
    inout  dq, dqs, dqs_n, dm, dmi;
  endclocking

  clocking mon_cb @(posedge ck);
    default input #0.5 output #0.5;
    input ca, cs;
    input dq, dqs, dqs_n, dm, dmi;
  endclocking

  modport driver  (clocking drv_cb, input ck, ck_n, cke, rst_n);
  modport monitor (clocking mon_cb, input ck, ck_n, cke, rst_n);
endinterface : lpddr_if

interface hbm_if #(
  parameter ADDR_WIDTH = 34,
  parameter DATA_WIDTH = 128,
  parameter CHANNELS   = 8
)(
  input logic ck,
  input logic ck_n,
  input logic rst_n
);
  // HBM uses pseudo-channel architecture
  logic [ADDR_WIDTH-1:0] addr;
  logic [2:0]            cid;     // Channel ID
  logic [1:0]            ba;      // Bank address
  logic                  cs_n;
  logic                  cke;
  logic                  ras_n;
  logic                  cas_n;
  logic                  we_n;
  // Data (wide bus)
  logic [DATA_WIDTH-1:0]   dq;
  logic [DATA_WIDTH/8-1:0] dqs;
  logic [DATA_WIDTH/8-1:0] dqs_n;
  logic [DATA_WIDTH/8-1:0] dm;
  // HBM-specific
  logic                  par;   // Parity
  // Timing
  int tRCD = 14;
  int tRP  = 14;
  int tRAS = 34;
  int tCL  = 14;
  int tCWL = 8;

  clocking drv_cb @(posedge ck);
    default input #0.5 output #0.5;
    output addr, cid, ba, cs_n, cke, ras_n, cas_n, we_n, par;
    inout  dq, dqs, dqs_n, dm;
  endclocking

  clocking mon_cb @(posedge ck);
    default input #0.5 output #0.5;
    input addr, cid, ba, cs_n, cke, ras_n, cas_n, we_n, par;
    input dq, dqs, dqs_n, dm;
  endclocking

  modport driver  (clocking drv_cb, input ck, ck_n, rst_n);
  modport monitor (clocking mon_cb, input ck, ck_n, rst_n);
endinterface : hbm_if

interface ufs_if #(
  parameter DATA_WIDTH = 8,
  parameter LANE_COUNT = 2
)(
  input logic ref_clk,
  input logic rst_n
);
  // M-PHY based interface
  logic [LANE_COUNT-1:0] tx_dp;
  logic [LANE_COUNT-1:0] tx_dn;
  logic [LANE_COUNT-1:0] rx_dp;
  logic [LANE_COUNT-1:0] rx_dn;
  // UFS application layer
  logic [DATA_WIDTH-1:0] data_out;
  logic                  data_out_valid;
  logic [DATA_WIDTH-1:0] data_in;
  logic                  data_in_valid;
  logic [7:0]            task_tag;
  logic [15:0]           data_length;

  // UPIU (UFS Protocol Information Unit) types (6-bit per UFS spec)
  typedef enum logic [5:0] {
    UPIU_NOP_OUT     = 6'h00,
    UPIU_COMMAND     = 6'h01,
    UPIU_DATA_OUT    = 6'h02,
    UPIU_TASK_MGT    = 6'h04,
    UPIU_QUERY_REQ   = 6'h16,
    UPIU_NOP_IN      = 6'h20,
    UPIU_RESPONSE    = 6'h21,
    UPIU_DATA_IN     = 6'h22,
    UPIU_TASK_MGT_RSP= 6'h24,
    UPIU_QUERY_RSP   = 6'h36,
    UPIU_READY_XFER  = 6'h31,
    UPIU_REJECT      = 6'h3F
  } upiu_t;

  clocking drv_cb @(posedge ref_clk);
    default input #1 output #1;
    output tx_dp, tx_dn, data_out, data_out_valid, task_tag, data_length;
    input  rx_dp, rx_dn, data_in, data_in_valid;
  endclocking

  clocking mon_cb @(posedge ref_clk);
    default input #1 output #1;
    input tx_dp, tx_dn, rx_dp, rx_dn;
    input data_out, data_out_valid, data_in, data_in_valid, task_tag, data_length;
  endclocking

  modport driver  (clocking drv_cb, input ref_clk, rst_n);
  modport monitor (clocking mon_cb, input ref_clk, rst_n);
endinterface : ufs_if

interface unipro_if #(
  parameter DATA_WIDTH = 8,
  parameter LANE_COUNT = 2
)(
  input logic clk,
  input logic rst_n
);
  // UniPro uses M-PHY physical layer
  logic [LANE_COUNT-1:0] tx_dp;
  logic [LANE_COUNT-1:0] tx_dn;
  logic [LANE_COUNT-1:0] rx_dp;
  logic [LANE_COUNT-1:0] rx_dn;
  // L2 CAP (Credit-based flow control)
  logic [7:0]            tx_cred;
  logic [7:0]            rx_cred;
  logic                  tx_cred_valid;
  logic                  rx_cred_valid;
  // L3 PA (Protocol Adapter)
  logic [DATA_WIDTH-1:0] tx_data;
  logic                  tx_data_valid;
  logic [DATA_WIDTH-1:0] rx_data;
  logic                  rx_data_valid;
  // CPort ID
  logic [4:0]            cportid;

  // UniPro message types
  typedef enum logic [3:0] {
    UNI_NOP     = 4'h0,
    UNI_DATA    = 4'h1,
    UNI_CTRL    = 4'h2,
    UNI_CREDIT  = 4'h3,
    UNI_ERROR   = 4'hF
  } unipro_msg_t;

  clocking drv_cb @(posedge clk);
    default input #1 output #1;
    output tx_dp, tx_dn, tx_cred, tx_cred_valid, tx_data, tx_data_valid, cportid;
    input  rx_dp, rx_dn, rx_cred, rx_cred_valid, rx_data, rx_data_valid;
  endclocking

  clocking mon_cb @(posedge clk);
    default input #1 output #1;
    input tx_dp, tx_dn, rx_dp, rx_dn;
    input tx_cred, tx_cred_valid, rx_cred, rx_cred_valid;
    input tx_data, tx_data_valid, rx_data, rx_data_valid, cportid;
  endclocking

  modport driver  (clocking drv_cb, input clk, rst_n);
  modport monitor (clocking mon_cb, input clk, rst_n);
endinterface : unipro_if

interface emmc_if #(
  parameter DATA_WIDTH = 8
)(
  input logic clk,
  input logic rst_n
);
  // eMMC uses MMC interface
  logic [DATA_WIDTH-1:0] cmd;
  logic                  cmd_valid;
  logic [DATA_WIDTH-1:0] data;
  logic                  data_valid;
  logic                  data_read;
  logic [6:0]            cmd_index;
  logic [31:0]           cmd_arg;
  logic [6:0]            resp;
  logic                  resp_valid;
  logic                  busy;

  // eMMC command types
  typedef enum logic [5:0] {
    CMD0_GO_IDLE        = 6'd0,
    CMD1_SEND_OP_COND   = 6'd1,
    CMD2_ALL_SEND_CID   = 6'd2,
    CMD3_SET_REL_ADDR   = 6'd3,
    CMD6_SWITCH         = 6'd6,
    CMD8_SEND_EXT_CSD   = 6'd8,
    CMD17_READ_SINGLE   = 6'd17,
    CMD18_READ_MULTIPLE = 6'd18,
    CMD24_WRITE_SINGLE  = 6'd24,
    CMD25_WRITE_MULTIPLE= 6'd25,
    CMD35_ERASE_GRP_START=6'd35,
    CMD36_ERASE_GRP_END = 6'd36,
    CMD38_ERASE         = 6'd38
  } emmc_cmd_t;

  // Bus widths
  typedef enum logic [1:0] {
    BW_1BIT = 2'b00,
    BW_4BIT = 2'b01,
    BW_8BIT = 2'b10,
    BW_RSVD = 2'b11
  } emmc_bw_t;

  clocking drv_cb @(posedge clk);
    default input #1 output #1;
    output cmd, cmd_valid, data, data_valid, data_read, cmd_index, cmd_arg;
    input  resp, resp_valid, busy;
  endclocking

  clocking mon_cb @(posedge clk);
    default input #1 output #1;
    input cmd, cmd_valid, data, data_valid, data_read, cmd_index, cmd_arg;
    input resp, resp_valid, busy;
  endclocking

  modport driver  (clocking drv_cb, input clk, rst_n);
  modport monitor (clocking mon_cb, input clk, rst_n);
endinterface : emmc_if

interface onfi_if #(
  parameter DATA_WIDTH = 8,
  parameter ADDR_WIDTH = 16
)(
  input logic clk,
  input logic rst_n
);
  // ONFI (Open NAND Flash Interface)
  // io is a bidirectional data bus: host drives it during cmd/addr/data-in
  // cycles, the NAND target drives it during data-out (RE#) cycles.
  tri  [DATA_WIDTH-1:0] io;
  logic                  cle;    // Command latch enable
  logic                  ale;    // Address latch enable
  logic                  ce_n;   // Chip enable
  logic                  re_n;   // Read enable
  logic                  we_n;   // Write enable
  logic                  wp_n;   // Write protect
  logic                  rb_n;   // Ready/busy

  // ONFI commands
  typedef enum logic [7:0] {
    ONFI_READ_ID        = 8'h90,
    ONFI_READ_STATUS    = 8'h70,
    ONFI_READ_PAGE      = 8'h00,
    ONFI_READ_PAGE_CONFIRM = 8'h30,
    ONFI_PROGRAM_PAGE   = 8'h80,
    ONFI_PROGRAM_CONFIRM= 8'h10,
    ONFI_ERASE_BLOCK    = 8'h60,
    ONFI_ERASE_CONFIRM  = 8'hD0,
    ONFI_RESET          = 8'hFF,
    ONFI_READ_PARAMETER = 8'hEC,
    ONFI_SET_FEATURES   = 8'hEF,
    ONFI_GET_FEATURES   = 8'hEE
  } onfi_cmd_t;

  // Status register bits
  typedef enum logic [7:0] {
    STAT_FAIL       = 8'h01,
    STAT_FAILC      = 8'h02,
    STAT_CSP        = 8'h08,
    STAT_VSP        = 8'h10,
    STAT_ARDY       = 8'h20,
    STAT_RDY        = 8'h40,
    STAT_WP         = 8'h80
  } onfi_status_t;

  clocking drv_cb @(posedge clk);
    default input #1 output #1;
    inout  io;
    output cle, ale, ce_n, re_n, we_n, wp_n;
    input  rb_n;
  endclocking

  clocking mon_cb @(posedge clk);
    default input #1 output #1;
    input io, cle, ale, ce_n, re_n, we_n, wp_n, rb_n;
  endclocking

  modport driver  (clocking drv_cb, input clk, rst_n);
  modport monitor (clocking mon_cb, input clk, rst_n);
endinterface : onfi_if

interface sd_if #(
  parameter DATA_WIDTH = 4
)(
  input logic clk,
  input logic rst_n
);
  // SD/SDIO interface
  logic                  cmd;
  logic [DATA_WIDTH-1:0] dat;
  logic                  cmd_dir;  // 0=host->card, 1=card->host
  logic [DATA_WIDTH-1:0] dat_dir;

  // SD command types
  typedef enum logic [5:0] {
    SD_CMD0_GO_IDLE       = 6'd0,
    SD_CMD2_ALL_SEND_CID  = 6'd2,
    SD_CMD3_SEND_REL_ADDR = 6'd3,
    SD_CMD6_SWITCH_FUNC   = 6'd6,
    SD_CMD7_SELECT_CARD   = 6'd7,
    SD_CMD8_SEND_IF_COND  = 6'd8,
    SD_CMD9_SEND_CSD      = 6'd9,
    SD_CMD13_SEND_STATUS  = 6'd13,
    SD_CMD16_SET_BLOCKLEN = 6'd16,
    SD_CMD17_READ_SINGLE  = 6'd17,
    SD_CMD18_READ_MULTIPLE= 6'd18,
    SD_CMD24_WRITE_SINGLE = 6'd24,
    SD_CMD25_WRITE_MULTIPLE=6'd25,
    SD_CMD55_APP_CMD      = 6'd55,
    SD_ACMD6_SET_BUS_WIDTH= 6'd56,  // ACMD6 (after CMD55); unique encoding
    SD_ACMD41_SD_SEND_OP  = 6'd41,
    SD_CMD52_IO_RW_DIRECT = 6'd52,
    SD_CMD53_IO_RW_EXTENDED=6'd53
  } sd_cmd_t;

  // Response types
  typedef enum logic [1:0] {
    RSP_NONE = 2'b00,
    RSP_R1   = 2'b01,
    RSP_R2   = 2'b10,
    RSP_R3   = 2'b11
  } sd_rsp_t;

  // Transfer modes
  typedef enum logic {
    TM_BLOCK     = 1'b0,
    TM_STREAM    = 1'b1
  } sd_tm_t;

  clocking drv_cb @(posedge clk);
    default input #1 output #1;
    output cmd, dat, cmd_dir, dat_dir;
  endclocking

  clocking mon_cb @(posedge clk);
    default input #1 output #1;
    input cmd, dat, cmd_dir, dat_dir;
  endclocking

  modport driver  (clocking drv_cb, input clk, rst_n);
  modport monitor (clocking mon_cb, input clk, rst_n);
endinterface : sd_if

`endif // MEMORY_INTERFACES_SV
