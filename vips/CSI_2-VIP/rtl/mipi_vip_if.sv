// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mipi_vip_if.sv -- MIPI Interface
// CSI-2 / DSI / D-PHY / C-PHY / M-PHY / UniPro / DigRF / HSI / CSE
// Deepened for: CSI-2 (adds lane FSM state + CSI-2-specific status signals)
//============================================================================

`ifndef MIPI_VIP_IF_SV
`define MIPI_VIP_IF_SV

interface mipi_vip_if #(parameter int DATA_WIDTH=32, parameter int LANE_COUNT=4)
  (input logic clk, input logic rst_n);
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import mipi_vip_pkg::*;

  // MAC Layer
  logic [DATA_WIDTH-1:0] data;
  logic valid;
  logic ready;
  logic sop;
  logic eop;
  logic [5:0] pkt_type;
  logic [2:0] vc;
  logic [15:0] word_count;
  logic [15:0] ecc;
  logic [31:0] crc;

  // Lane FSM state (driven by the VIP driver, observed by monitor/coverage)
  mipi_lane_state_e lane_state;

  // D-PHY Layer
  logic dphy_clk_p, dphy_clk_n;
  logic [LANE_COUNT-1:0] dphy_data_p, dphy_data_n;
  logic dphy_lp_dir;
  logic [LANE_COUNT-1:0] dphy_lp_rx_p, dphy_lp_rx_n;
  logic dphy_hs_rqst;
  logic dphy_hs_rdy;

  // C-PHY Layer (3-phase symbol)
  logic [LANE_COUNT-1:0] cphy_tx_p, cphy_tx_n;
  logic [LANE_COUNT*16-1:0] cphy_symbol;
  logic cphy_symbol_valid;

  // M-PHY Layer
  logic [LANE_COUNT-1:0] mphy_tx_p, mphy_tx_n;
  logic mphy_pwm_mode;
  logic [3:0] mphy_gear;
  logic mphy_series_a, mphy_series_b;
  logic mphy_ls_mode;
  logic mphy_hs_mode;
  logic mphy_ready;

  // UniPro Layer
  logic [7:0] unipro_data;
  logic unipro_valid;
  logic unipro_ready;
  logic [3:0] unipro_cport;
  logic [2:0] unipro_tc;

  // DigRFv4 Layer
  logic [11:0] digrf_i, digrf_q;
  logic digrf_valid;
  logic digrf_frame_sync;
  logic [3:0] digrf_antenna;

  // HSI Layer
  logic [7:0] hsi_data;
  logic hsi_valid;
  logic hsi_ready;
  logic [3:0] hsi_channel;
  logic hsi_wake;

  // CSE Layer
  logic [7:0] cse_data;
  logic cse_valid;
  logic cse_ready;
  logic [3:0] cse_cmd;
  logic cse_irq;

  // Protocol status signals (deepened; union used by the tiered SVA checkers)
  // CSI-2 / DSI MAC-layer status
  logic [5:0]  data_type;
  logic [15:0] wc;
  logic        ecc_ok, crc_ok;
  logic [LANE_COUNT-1:0] lane_active;
  logic        ulps, escape, hs_req, hs_mode, cal_done;
  logic [2:0]  lp_state;
  // DSI link-layer status
  logic        lp_mode, bta, te, ack, error_report, vsync, hsync;
  // D-PHY status
  logic [7:0]  hs_data;
  logic        term_en, clk_lane, skew_cal;
  int          lane_count;
  // C-PHY status
  logic [6:0]  symbol;
  logic [2:0]  triplet;
  logic        sp, alp;
  logic [31:0] bandwidth;
  // M-PHY status
  logic [2:0]  gear;
  logic [1:0]  mode;
  logic [2:0]  pwr_state;
  logic        hs_burst, pwm_burst, sync, hibern8, stall, save;
  // UniPro status
  logic [2:0]  cp_state;
  logic [2:0]  tc;
  logic        nack, sof, eof;
  logic [7:0]  credit;
  logic [2:0]  pwr_mode;

  // Clocking
  clocking drv_cb @(posedge clk);
    output data, valid, sop, eop, pkt_type, vc, word_count, ecc, crc;
    output dphy_lp_dir, dphy_hs_rqst;
    output cphy_symbol, cphy_symbol_valid;
    output mphy_pwm_mode, mphy_gear, mphy_series_a, mphy_series_b;
    output unipro_data, unipro_valid, unipro_cport, unipro_tc;
    output digrf_i, digrf_q, digrf_valid, digrf_frame_sync, digrf_antenna;
    output hsi_data, hsi_valid, hsi_channel, hsi_wake;
    output cse_data, cse_valid, cse_cmd;
    input ready, dphy_hs_rdy, mphy_ready, unipro_ready, hsi_ready, cse_ready;
  endclocking

  clocking mon_cb @(posedge clk);
    input data, valid, ready, sop, eop, pkt_type, vc, word_count, ecc, crc;
    input dphy_clk_p, dphy_clk_n, dphy_data_p, dphy_data_n, dphy_lp_dir, dphy_hs_rqst, dphy_hs_rdy;
    input cphy_tx_p, cphy_tx_n, cphy_symbol, cphy_symbol_valid;
    input mphy_tx_p, mphy_tx_n, mphy_pwm_mode, mphy_gear, mphy_series_a, mphy_series_b, mphy_ls_mode, mphy_hs_mode, mphy_ready;
    input unipro_data, unipro_valid, unipro_ready, unipro_cport, unipro_tc;
    input digrf_i, digrf_q, digrf_valid, digrf_frame_sync, digrf_antenna;
    input hsi_data, hsi_valid, hsi_ready, hsi_channel, hsi_wake;
    input cse_data, cse_valid, cse_ready, cse_cmd, cse_irq;
  endclocking

  modport driver_mp (clocking drv_cb, input clk, rst_n);
  modport monitor_mp (clocking mon_cb, input clk, rst_n);

  // Assertions
  property p_dphy_hs_rqst;
    @(posedge clk) disable iff(!rst_n) dphy_hs_rqst |-> ##[1:100] dphy_hs_rdy;
  endproperty
  assert_dphy_hs: assert property(p_dphy_hs_rqst) else `uvm_error("MIPI_IF", "D-PHY HS request timeout");

  property p_cphy_symbol;
    @(posedge clk) disable iff(!rst_n) cphy_symbol_valid |-> cphy_symbol != 0;
  endproperty
  assert_cphy_sym: assert property(p_cphy_symbol) else `uvm_error("MIPI_IF", "C-PHY invalid symbol");

  property p_mphy_gear;
    @(posedge clk) disable iff(!rst_n) mphy_hs_mode |-> mphy_gear inside {[4'd1:4'd5]};
  endproperty
  assert_mphy_gear: assert property(p_mphy_gear) else `uvm_error("MIPI_IF", "M-PHY invalid gear");

  property p_unipro_tc;
    @(posedge clk) disable iff(!rst_n) unipro_valid |-> unipro_tc inside {[3'd0:3'd7]};
  endproperty
  assert_unipro_tc: assert property(p_unipro_tc) else `uvm_error("MIPI_IF", "UniPro TC invalid");

  property p_digrf_frame;
    @(posedge clk) disable iff(!rst_n) digrf_frame_sync |-> digrf_valid;
  endproperty
  assert_digrf: assert property(p_digrf_frame) else `uvm_error("MIPI_IF", "DigRF frame sync without valid");

  property p_hsi_wake;
    @(posedge clk) disable iff(!rst_n) hsi_wake |-> ##[1:10] hsi_valid;
  endproperty
  assert_hsi_wake: assert property(p_hsi_wake) else `uvm_error("MIPI_IF", "HSI wake timeout");

  property p_cse_cmd;
    @(posedge clk) disable iff(!rst_n) cse_valid |-> cse_cmd inside {[4'd0:4'd15]};
  endproperty
  assert_cse_cmd: assert property(p_cse_cmd) else `uvm_error("MIPI_IF", "CSE invalid command");

  // Coverage
  covergroup cg_mipi_if @(posedge clk);
    option.per_instance=1;
    cp_pkt: coverpoint pkt_type { bins fs={PKT_FS}; bins fe={PKT_FE}; bins data={[PKT_RGB565:PKT_RAW14]}; bins ctrl={[PKT_NULL:PKT_EMBEDDED]}; }
    cp_vc: coverpoint vc { bins vc0={0}; bins vc1={1}; bins vc2={2}; bins vc3={3}; bins vc4_7={[4:7]}; }
    cp_dphy_hs: coverpoint dphy_hs_rqst { bins off={0}; bins on={1}; }
    cp_mphy_mode: coverpoint {mphy_ls_mode,mphy_hs_mode} { bins ls={2'b10}; bins hs={2'b01}; bins pwm={2'b00}; }
    cp_unipro: coverpoint unipro_valid { bins off={0}; bins on={1}; }
    cp_digrf: coverpoint digrf_valid { bins off={0}; bins on={1}; }
    cp_hsi: coverpoint hsi_valid { bins off={0}; bins on={1}; }
    cp_cse: coverpoint cse_valid { bins off={0}; bins on={1}; }
    cross_pkt_vc: cross cp_pkt, cp_vc;
  endgroup

  initial begin
    cg_mipi_if cg = new();
  end

endinterface
`endif
