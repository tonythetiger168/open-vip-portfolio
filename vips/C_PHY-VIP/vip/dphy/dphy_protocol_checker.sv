// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// dphy_protocol_checker.sv -- D-PHY protocol checker (deepened)
// LP/HS state machine legality, HS request handshake, ULPS/escape modes
`ifndef DPHY_PROTOCOL_CHECKER_SV
`define DPHY_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class dphy_protocol_checker extends uvm_component;
  `uvm_component_utils(dphy_protocol_checker)
  virtual mipi_vip_if vif;
  int lp_err, hs_err, ulps_cnt;

    logic [2:0] samp_lp;
  logic samp_hs, samp_ulps;

covergroup cg_dphy;
    option.per_instance=1;
    cp_lp: coverpoint samp_lp { bins hs_req={3'b000}; bins lp01={3'b001}; bins lp10={3'b010}; bins lp11={3'b011}; bins ulps={3'b101}; }
    cp_hs: coverpoint samp_hs { bins lp={0}; bins hs={1}; }
    cp_ulps: coverpoint samp_ulps { bins off={0}; bins on={1}; }
    cross_lp_hs: cross cp_lp, cp_hs;
  endgroup

  function new(string name="dphy_chk", uvm_component parent=null);
    super.new(name,parent);
    lp_err=0;hs_err=0;ulps_cnt=0;
    cg_dphy = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "D-PHY chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    int hs_wait; bit hs_pending;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin hs_pending = 0; continue; end
      // HS data only while in HS mode
      if (vif.hs_data != 8'h00 && !vif.hs_mode) begin
        `uvm_error("DPHY_CHK", "D-PHY HS data outside HS mode"); hs_err++;
      end
      // HS request must be acknowledged within 100 cycles
      if (vif.dphy_hs_rqst && !hs_pending) begin hs_pending = 1; hs_wait = 0; end
      if (hs_pending) begin
        hs_wait++;
        if (vif.dphy_hs_rdy) hs_pending = 0;
        else if (hs_wait > 100) begin
          `uvm_error("DPHY_CHK", "D-PHY HS request not acknowledged"); hs_err++; hs_pending = 0;
        end
      end
      // legal LP state encoding
      if (!(vif.lp_state inside {3'b000,3'b001,3'b010,3'b011,3'b101})) begin
        `uvm_error("DPHY_CHK", "D-PHY illegal LP state"); lp_err++;
      end
      if (vif.ulps) ulps_cnt++;
      samp_lp = vif.lp_state; samp_hs = vif.hs_mode; samp_ulps = vif.ulps;
      cg_dphy.sample();
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("DPHY_PROTOCOL_CHECKER_RPT",$sformatf("D-PHY Chk | LP:%0d HS:%0d ULPS:%0d",lp_err,hs_err,ulps_cnt),UVM_LOW);
  endfunction
endclass
`endif
