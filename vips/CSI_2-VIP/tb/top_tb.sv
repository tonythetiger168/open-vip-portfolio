// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// top_tb.sv -- MIPI Top-Level Testbench (CSI-2)
// Closed loop: VIP driver -> mipi_vip_if -> functional CSI-2 DUT model
//============================================================================

`ifndef TOP_TB_SV
`define TOP_TB_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

module top_tb;
  logic clk = 0, rst_n;
  always #2ns clk = ~clk;
  initial begin rst_n = 0; #100ns; rst_n = 1; end

  mipi_vip_if #(.DATA_WIDTH(32), .LANE_COUNT(4)) vif(clk, rst_n);

  mipi_dut dut(.vif(vif));

  // Tiered SVA compliance checker (module form)
  csi_2_compliance_checker u_csi2_sva_chk (.vif(vif));

  initial begin
    uvm_config_db#(virtual mipi_vip_if)::set(null, "*", "vif", vif);
    run_test();
  end
endmodule

//--------------------------------------------------------------------------
// Functional CSI-2 DUT model (protocol sink / PHY loopback endpoint):
//  - handshakes the MAC bus (ready follows valid)
//  - returns PHY-level responses (HS ready, termination, calibration done)
//  - decodes the packet header/payload and re-computes ECC/CRC-16,
//    driving ecc_ok/crc_ok status back onto the interface (closed loop)
//--------------------------------------------------------------------------
module mipi_dut(mipi_vip_if vif);
  import mipi_vip_pkg::*;

  // packet capture state
  logic [15:0] cap_wc;
  logic [31:0] cap_data[$];
  int unsigned rx_pkts = 0;

  // handshake + PHY responses (original behavior, kept) + status responses
  always_ff @(posedge vif.clk or negedge vif.rst_n) begin
    if (!vif.rst_n) begin
      vif.ready <= 0; vif.dphy_hs_rdy <= 0; vif.mphy_ready <= 0;
      vif.unipro_ready <= 0; vif.hsi_ready <= 0; vif.cse_ready <= 0;
      vif.term_en <= 0; vif.cal_done <= 0; vif.ack <= 0;
      vif.error_report <= 0; vif.lane_count <= 4;
    end else begin
      vif.ready         <= #1ns vif.valid;
      vif.dphy_hs_rdy   <= #1ns vif.dphy_hs_rqst;
      vif.mphy_ready    <= #1ns vif.mphy_hs_mode;
      vif.unipro_ready  <= #1ns vif.unipro_valid;
      vif.hsi_ready     <= #1ns vif.hsi_valid;
      vif.cse_ready     <= #1ns vif.cse_valid;
      // PHY status responses (termination, deskew/calibration, DSI ack)
      vif.term_en       <= #1ns vif.hs_mode;
      vif.cal_done      <= #1ns (vif.lane_state == ST_LP11);
      vif.ack           <= #1ns vif.bta;
      vif.error_report  <= #1ns (vif.bta && (vif.ecc_ok === 1'b0));
      vif.lane_count    <= 4;
    end
  end

  // packet decoder + integrity status
  always_ff @(posedge vif.clk or negedge vif.rst_n) begin : decoder
    if (!vif.rst_n) begin : dec_reset
      cap_data.delete();
      rx_pkts <= 0;
      vif.ecc_ok <= 0; vif.crc_ok <= 0;
    end else if (vif.valid && vif.ready) begin : dec_beat
      if (vif.sop) begin : dec_sop
        cap_wc = vif.word_count;
        cap_data.delete();
        cap_data.push_back(vif.data);
        // re-compute header ECC and report status (closed loop)
        vif.ecc_ok <= (vif.ecc == {8'h00, mipi_calc_ecc({vif.word_count, vif.vc[1:0], vif.pkt_type})});
      end else begin : dec_payload
        cap_data.push_back(vif.data);
      end
      if (vif.eop) begin : dec_eop
        logic [15:0] exp_crc;
        logic [31:0] words[];
        words = new[cap_data.size()];
        foreach (cap_data[i]) words[i] = cap_data[i];
        exp_crc = mipi_calc_crc16(words);
        rx_pkts <= rx_pkts + 1;
        // re-compute payload CRC-16 and report status (closed loop)
        vif.crc_ok <= (vif.crc[15:0] == exp_crc);
      end
    end
  end
endmodule
`endif
