// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// unipro_protocol_checker.sv -- UniPro protocol checker (deepened)
// SOF/EOF framing, TC/CPort legality, credit flow control, NACK/replay
`ifndef UNIPRO_PROTOCOL_CHECKER_SV
`define UNIPRO_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class unipro_protocol_checker extends uvm_component;
  `uvm_component_utils(unipro_protocol_checker)
  virtual mipi_vip_if vif;
  int frame_err, credit_err, nack_cnt;

    logic [2:0] samp_tc;
  logic [3:0] samp_cport;
  logic [1:0] samp_frame;
  logic samp_nack;

covergroup cg_unipro;
    option.per_instance=1;
    cp_tc: coverpoint samp_tc { bins tc0={0}; bins tc1={1}; bins tc2_7={[2:7]}; }
    cp_cport: coverpoint samp_cport { bins low={[0:7]}; bins high={[8:15]}; }
    cp_frame: coverpoint samp_frame { bins sof={2'b10}; bins eof={2'b01}; bins mid={2'b00}; }
    cp_nack: coverpoint samp_nack { bins ack={0}; bins nack={1}; }
    cross_tc_cport: cross cp_tc, cp_cport;
  endgroup

  function new(string name="unipro_chk", uvm_component parent=null);
    super.new(name,parent);
    frame_err=0;credit_err=0;nack_cnt=0;
    cg_unipro = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "UniPro chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    bit in_frame;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin in_frame = 0; continue; end
      // legal traffic class
      if (vif.unipro_valid && vif.unipro_tc > 3'd7) begin
        `uvm_error("UNIPRO_CHK", "UniPro illegal TC"); frame_err++;
      end
      // SOF must be terminated by EOF before the next SOF
      if ($rose(vif.sof)) begin
        if (in_frame) begin
          `uvm_error("UNIPRO_CHK", "UniPro overlapping SOF"); frame_err++;
        end
        in_frame = 1;
        // data frames require available credits on the TC
        if (vif.credit == 8'd0) begin
          `uvm_error("UNIPRO_CHK", "UniPro frame with zero credit"); credit_err++;
        end
      end
      if (vif.eof) in_frame = 0;
      if (vif.nack) nack_cnt++;
      samp_tc = vif.unipro_tc; samp_cport = vif.unipro_cport;
      samp_frame = {vif.sof, vif.eof}; samp_nack = vif.nack;
      cg_unipro.sample();
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("UNIPRO_PROTOCOL_CHECKER_RPT",$sformatf("UniPro Chk | FRAME:%0d CREDIT:%0d NACK:%0d",frame_err,credit_err,nack_cnt),UVM_LOW);
  endfunction
endclass
`endif
