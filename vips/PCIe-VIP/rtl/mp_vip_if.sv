// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Multi-Protocol Interface
// Supports: PCIe, CXL, UCIe, UALink
//============================================================================
`ifndef MP_VIP_IF_SV
`define MP_VIP_IF_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import mp_vip_pkg::*;

interface mp_vip_if #(parameter int DATA_WIDTH = 512,
                      parameter int LANE_COUNT = 16,
                      parameter int PROTOCOL   = 0)
                     (input logic clk, input logic rst_n);

  //========================================================================
  // Common Signals
  //========================================================================
  logic                   valid;
  logic                   ready;
  logic [DATA_WIDTH-1:0]  data;
  logic [LANE_COUNT-1:0]  lane_valid;
  logic                   sop;      // Start of Packet
  logic                   eop;      // End of Packet
  logic [7:0]             be;       // Byte Enable

  //========================================================================
  // Protocol-Specific Signals
  //========================================================================
  // PCIe/CXL Signals
  logic [15:0]            requester_id;
  logic [15:0]            completer_id;
  logic [7:0]             tag;
  logic [2:0]             tc;       // Traffic Class
  logic                   ep;       // Error Poisoned
  logic                   td;       // TLP Digest
  logic [1:0]             attr;
  logic [9:0]             length_dw;

  // UCIe Signals
  logic [7:0]             ucie_credits;
  logic [3:0]             ucie_vc;    // Virtual Channel
  logic                   ucie_adapt;

  // UALink Signals
  logic [3:0]             ualink_vc;
  logic [1:0]             ualink_qos;
  logic                   ualink_flit_mode;

  // Link State
  link_state_e            link_state;
  logic                   link_up;

  // Error Signals
  logic                   ecrc_error;
  logic                   lcrc_error;
  logic                   framing_error;
  logic                   protocol_error;

  // Power Management
  logic                   pm_request;
  logic [2:0]             pm_state;

  //========================================================================
  // SVA compliance checker compatibility aliases
  // (fields not broken out as dedicated pins are derived or tied here)
  //========================================================================
  logic [4:0]             tlp_type;         // approximated from traffic class
  assign tlp_type = {2'b00, tc};
  logic                   completion_valid; // completion observed at packet end
  assign completion_valid = eop;
  logic [7:0]             fc_credit;        // flow-control credits
  assign fc_credit = ucie_credits;
  logic [31:0]            ecrc;             // ECRC digest presence (flag-based)
  assign ecrc = {31'h0, ~ecrc_error};
  logic                   nak_received;     // NAK inferred from LCRC error
  assign nak_received = lcrc_error;
  logic                   replay_valid;     // replayed TLP on the wire
  assign replay_valid = valid;
  logic [1:0]             aspm_state;       // ASPM state from pm_state LSBs
  assign aspm_state = pm_state[1:0];
  logic                   drs_msg;          // DRS message (not modeled)
  assign drs_msg = 1'b0;
  logic [2:0]             link_speed;       // current link speed (Gen3 model)
  assign link_speed = 3'b011;

  //========================================================================
  // PIPE PHY Layer Signals (PCIe/CXL Physical Layer)
  //========================================================================
  logic [31:0]            pipe_tx_data;
  logic [3:0]             pipe_tx_data_k;
  logic                   pipe_tx_detect_rx;
  logic                   pipe_tx_elecidle;
  logic [2:0]             pipe_tx_deemph;
  logic [1:0]             pipe_tx_margin;
  logic                   pipe_tx_swing;
  logic                   pipe_tx_sync;
  logic [31:0]            pipe_rx_data;
  logic [3:0]             pipe_rx_data_k;
  logic                   pipe_rx_valid;
  logic                   pipe_rx_elecidle;
  logic [2:0]             pipe_rx_status;
  logic                   pipe_rx_sync;
  logic                   pipe_phy_status;
  logic                   pipe_phy_ready;
  logic [1:0]             pipe_power_down;
  logic                   pipe_tx_clk;
  logic                   pipe_rx_clk;
  logic                   pipe_tx_compliance;
  logic                   pipe_tx_burst;

  logic [7:0]             idle_count;       // idle symbol count (electrical idle)
  assign idle_count = {7'h0, pipe_tx_elecidle};

  // LTSSM
  logic [4:0]             ltssm_state;
  logic                   ltssm_detect_quiet;
  logic                   ltssm_detect_active;
  logic                   ltssm_polling_active;
  logic                   ltssm_polling_config;
  logic                   ltssm_config_linkwidth;
  logic                   ltssm_config_lanenum;
  logic                   ltssm_config_complete;

  //========================================================================
  // Clocking Blocks
  //========================================================================
  clocking driver_cb @(posedge clk);
    output valid, data, lane_valid, sop, eop, be;
    output requester_id, completer_id, tag, tc, ep, td, attr, length_dw;
    output ucie_credits, ucie_vc, ucie_adapt;
    output ualink_vc, ualink_qos, ualink_flit_mode;
    output pm_request, pm_state;
    input  ready, link_up, link_state;
    input  ecrc_error, lcrc_error, framing_error, protocol_error;
  endclocking

  clocking monitor_cb @(posedge clk);
    input  valid, ready, data, lane_valid, sop, eop, be;
    input  requester_id, completer_id, tag, tc, ep, td, attr, length_dw;
    input  ucie_credits, ucie_vc, ucie_adapt;
    input  ualink_vc, ualink_qos, ualink_flit_mode;
    input  link_up, link_state;
    input  ecrc_error, lcrc_error, framing_error, protocol_error;
    input  pm_request, pm_state;
  endclocking

  //========================================================================
  // Modports
  //========================================================================
  modport driver_mp  (clocking driver_cb,  input clk, rst_n);
  modport monitor_mp (clocking monitor_cb, input clk, rst_n);

  //========================================================================
  // Assertion: Valid-Ready Handshake
  //========================================================================
  property p_valid_ready_handshake;
    @(posedge clk) disable iff (!rst_n) valid |-> ##[1:100] ready;
  endproperty
  assert_valid_ready: assert property(p_valid_ready_handshake)
    else `uvm_error("MP_IF", "Valid-Ready handshake timeout")

  //========================================================================
  // Assertion: SOP-EOP Alignment
  //========================================================================
  property p_sop_eop_alignment;
    @(posedge clk) disable iff (!rst_n) sop |-> !eop ##[1:16] eop;
  endproperty
  assert_sop_eop: assert property(p_sop_eop_alignment)
    else `uvm_error("MP_IF", "SOP-EOP alignment violation")

  //========================================================================
  // Assertion: Link State Validity
  //========================================================================
  property p_link_state_valid;
    @(posedge clk) disable iff (!rst_n)
      link_state inside {LINK_RESET, LINK_DETECT, LINK_POLLING, LINK_CONFIG,
                         LINK_L0, LINK_L0S, LINK_L1, LINK_L2, LINK_RECOVERY,
                         LINK_DISABLED, LINK_LOOPBACK, LINK_HOT_RESET};
  endproperty
  assert_link_state: assert property(p_link_state_valid)
    else `uvm_error("MP_IF", "Invalid link state detected")

  //========================================================================
  // Coverage: Interface Activity
  //========================================================================
  covergroup cg_interface_activity @(posedge clk);
    option.per_instance = 1;
    cp_valid: coverpoint valid { bins inactive = {0}; bins active = {1}; }
    cp_ready: coverpoint ready { bins inactive = {0}; bins active = {1}; }
    cp_handshake: coverpoint {valid, ready} {
      bins idle       = {2'b00};
      bins wait_ready = {2'b10};
      bins transfer   = {2'b11};
      bins wait_valid = {2'b01};
    }
    cp_link_state: coverpoint link_state;
    cp_error: coverpoint {ecrc_error, lcrc_error, framing_error, protocol_error} {
      bins no_error  = {4'b0000};
      bins ecrc_err  = {4'b1000};
      bins lcrc_err  = {4'b0100};
      bins frame_err = {4'b0010};
      bins proto_err = {4'b0001};
    }
    cross_hs_state: cross cp_handshake, cp_link_state;
  endgroup

  cg_interface_activity cg_act = new();

endinterface
`endif
