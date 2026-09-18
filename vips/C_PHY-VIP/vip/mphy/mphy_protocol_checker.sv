// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// mphy_protocol_checker.sv -- M-PHY protocol checker (deepened)
// Gear/Series configuration, SYNC->BURST sequencing, Hibern8 power states
`ifndef MPHY_PROTOCOL_CHECKER_SV
`define MPHY_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class mphy_protocol_checker extends uvm_component;
  `uvm_component_utils(mphy_protocol_checker)
  virtual mipi_vip_if vif;
  int gear_err, seq_err, hibern8_cnt;

    logic [3:0] samp_gear;
  logic [1:0] samp_mode;
  logic [2:0] samp_pwr;

covergroup cg_mphy;
    option.per_instance=1;
    cp_gear: coverpoint samp_gear { bins g1={1}; bins g2={2}; bins g3={3}; bins g4={4}; bins g5={5}; }
    cp_mode: coverpoint samp_mode { bins pwm={2'b01}; bins hs={2'b10}; }
    cp_pwr: coverpoint samp_pwr { bins active={3'b000}; bins stall={3'b010}; bins save={3'b011}; bins hibern8={3'b101}; }
    cross_gear_mode: cross cp_gear, cp_mode;
  endgroup

  function new(string name="mphy_chk", uvm_component parent=null);
    super.new(name,parent);
    gear_err=0;seq_err=0;hibern8_cnt=0;
    cg_mphy = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "M-PHY chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    logic [3:0] prev_gear; bit prev_sync, prev2_sync;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin prev_sync = 0; prev2_sync = 0; continue; end
      // legal gears in HS mode
      if (vif.mphy_hs_mode && !(vif.mphy_gear inside {[4'd1:4'd5]})) begin
        `uvm_error("MPHY_CHK", "M-PHY illegal gear"); gear_err++;
      end
      // gear changes only legal outside bursts
      if (vif.mphy_gear !== prev_gear && (vif.hs_burst || vif.pwm_burst)) begin
        `uvm_error("MPHY_CHK", "M-PHY gear changed during burst"); gear_err++;
      end
      // a burst must be preceded by a SYNC pattern
      if ($rose(vif.hs_burst) && !(prev_sync || prev2_sync)) begin
        `uvm_error("MPHY_CHK", "M-PHY burst without SYNC"); seq_err++;
      end
      if (vif.hibern8) hibern8_cnt++;
      prev2_sync = prev_sync; prev_sync = vif.sync; prev_gear = vif.mphy_gear;
      samp_gear = vif.mphy_gear; samp_mode = vif.mode; samp_pwr = vif.pwr_state;
      cg_mphy.sample();
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("MPHY_PROTOCOL_CHECKER_RPT",$sformatf("M-PHY Chk | GEAR:%0d SEQ:%0d HIBERN8:%0d",gear_err,seq_err,hibern8_cnt),UVM_LOW);
  endfunction
endclass
`endif
