// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// dsi_protocol_checker.sv -- DSI protocol checker (deepened)
// ECC re-computation, BTA/TE link-layer rules, video-mode events
`ifndef DSI_PROTOCOL_CHECKER_SV
`define DSI_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class dsi_protocol_checker extends uvm_component;
  `uvm_component_utils(dsi_protocol_checker)
  virtual mipi_vip_if vif;
  int ecc_err, crc_err, bta_err;

    logic [5:0] samp_pkt;
  logic [2:0] samp_vc;
  logic samp_bta;

covergroup cg_dsi;
    option.per_instance=1;
    cp_pkt: coverpoint samp_pkt { bins sync={[6'h00:6'h0F]}; bins video={[6'h10:6'h2F]}; bins cmd={[6'h30:6'h3F]}; }
    cp_vc: coverpoint samp_vc { bins vc0={0}; bins vc1={1}; bins vc2={2}; bins vc3={3}; }
    cp_bta: coverpoint samp_bta { bins idle={0}; bins bta={1}; }
    cross_pkt_vc: cross cp_pkt, cp_vc;
    cross_pkt_bta: cross cp_pkt, cp_bta;
  endgroup

  function new(string name="dsi_chk", uvm_component parent=null);
    super.new(name,parent);
    ecc_err=0;crc_err=0;bta_err=0;
    cg_dsi = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "DSI chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) continue;
      // BTA and TE are LP-mode link-layer events
      if (vif.bta && !vif.lp_mode) begin
        `uvm_error("DSI_CHK", "DSI BTA outside LP mode"); bta_err++;
      end
      if (vif.te && !vif.vsync) begin
        `uvm_error("DSI_CHK", "DSI TE without VSYNC"); bta_err++;
      end
      if (vif.ack && !vif.lp_mode) begin
        `uvm_error("DSI_CHK", "DSI ACK outside LP mode"); bta_err++;
      end
      if (vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.sop) begin
        if (vif.mon_cb.ecc == 16'h0000) begin
          `uvm_error("DSI_CHK", "DSI ECC zero"); ecc_err++;
        end
        if (vif.mon_cb.ecc != {8'h00, mipi_vip_pkg::mipi_calc_ecc({vif.mon_cb.word_count, vif.mon_cb.vc[1:0], vif.mon_cb.pkt_type})}) begin
          `uvm_warning("DSI_CHK", "DSI header ECC mismatch"); ecc_err++;
        end
        samp_pkt = vif.mon_cb.pkt_type;
        samp_vc  = vif.mon_cb.vc;
        samp_bta = vif.bta;
        cg_dsi.sample();
      end
      if (vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.eop && vif.mon_cb.crc == 32'h0) begin
        `uvm_error("DSI_CHK", "DSI CRC zero"); crc_err++;
      end
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("DSI_PROTOCOL_CHECKER_RPT",$sformatf("DSI Chk | ECC:%0d CRC:%0d BTA:%0d",ecc_err,crc_err,bta_err),UVM_LOW);
  endfunction
endclass
`endif
