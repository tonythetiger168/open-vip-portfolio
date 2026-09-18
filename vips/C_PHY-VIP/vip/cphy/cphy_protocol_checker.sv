// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// cphy_protocol_checker.sv -- C-PHY protocol checker (deepened)
// 3-phase symbol encoding rules (wire state must toggle every symbol)
`ifndef CPHY_PROTOCOL_CHECKER_SV
`define CPHY_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class cphy_protocol_checker extends uvm_component;
  `uvm_component_utils(cphy_protocol_checker)
  virtual mipi_vip_if vif;
  int sym_err, triplet_err, sym_cnt;

    logic [6:0] samp_sym;
  logic [2:0] samp_triplet;
  logic samp_sp;

covergroup cg_cphy;
    option.per_instance=1;
    cp_sym: coverpoint samp_sym { bins low={[0:42]}; bins mid={[43:85]}; bins high={[86:127]}; }
    cp_triplet: coverpoint samp_triplet { bins t[] = {[3'b001:3'b110]}; }
    cp_sp: coverpoint samp_sp { bins lp={0}; bins sp={1}; }
    cross_sym_triplet: cross cp_sym, cp_triplet;
  endgroup

  function new(string name="cphy_chk", uvm_component parent=null);
    super.new(name,parent);
    sym_err=0;triplet_err=0;sym_cnt=0;
    cg_cphy = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "C-PHY chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    logic [2:0] prev_triplet; bit prev_valid;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin prev_valid = 0; continue; end
      if (vif.cphy_symbol_valid) begin
        sym_cnt++;
        if ($isunknown(vif.cphy_symbol)) begin
          `uvm_error("CPHY_CHK", "C-PHY unknown symbol"); sym_err++;
        end
        // 3-phase rule: triplet must change between consecutive symbols
        if (prev_valid && (vif.triplet == prev_triplet)) begin
          `uvm_error("CPHY_CHK", "C-PHY triplet did not toggle"); triplet_err++;
        end
        prev_triplet = vif.triplet; prev_valid = 1;
        samp_sym = vif.symbol; samp_triplet = vif.triplet; samp_sp = vif.sp;
        cg_cphy.sample();
      end else prev_valid = 0;
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("CPHY_PROTOCOL_CHECKER_RPT",$sformatf("C-PHY Chk | SYM:%0d TRIPLET:%0d SYMS:%0d",sym_err,triplet_err,sym_cnt),UVM_LOW);
  endfunction
endclass
`endif
