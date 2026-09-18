// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// cse_protocol_checker.sv -- CSE protocol checker (generic MAC-level)
`ifndef CSE_PROTOCOL_CHECKER_SV
`define CSE_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class cse_protocol_checker extends uvm_component;
  `uvm_component_utils(cse_protocol_checker)
  virtual mipi_vip_if vif;
  int proto_err, pkt_cnt;
  bit in_pkt;

    logic [5:0] samp_pkt;
  logic [2:0] samp_vc;

covergroup cg_cse;
    option.per_instance=1;
    cp_pkt: coverpoint samp_pkt { bins ctrl={[6'h00:6'h0F]}; bins data={[6'h10:6'h2F]}; bins user={[6'h30:6'h3F]}; }
    cp_vc: coverpoint samp_vc { bins vc0={0}; bins vc1={1}; bins vc2={2}; bins vc3={3}; bins vc4_7={[4:7]}; }
    cross_pkt_vc: cross cp_pkt, cp_vc;
  endgroup

  function new(string name="cse_chk", uvm_component parent=null);
    super.new(name,parent);
    proto_err=0; pkt_cnt=0; in_pkt=0;
    cg_cse = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif", vif))
      `uvm_fatal("CONFIG", "CSE chk: no vif");
  endfunction

  // procedural protocol checks (concurrent assertions live in the SVA module)
  task run_phase(uvm_phase phase);
    int unsigned sop_cycle, cyc;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin in_pkt = 0; continue; end
      cyc++;
      // no X on data when valid
      if (vif.mon_cb.valid && $isunknown(vif.mon_cb.data)) begin
        `uvm_error("CSE_PROTOCOL_CHECKER", "CSE X on data when valid"); proto_err++;
      end
      // SOP must be followed by EOP (packet timeout watchdog)
      if (vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.sop) begin
        in_pkt = 1; sop_cycle = cyc; pkt_cnt++;
      end
      if (vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.eop) in_pkt = 0;
      if (in_pkt && (cyc - sop_cycle) > 100000) begin
        `uvm_error("CSE_PROTOCOL_CHECKER", "CSE SOP without EOP (timeout)"); proto_err++;
        in_pkt = 0;
      end
      // sample coverage on accepted beats
      if (vif.mon_cb.valid && vif.mon_cb.ready) begin
        samp_pkt = vif.mon_cb.pkt_type;
        samp_vc  = vif.mon_cb.vc;
        cg_cse.sample();
      end
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("CSE_PROTOCOL_CHECKER_RPT", $sformatf("CSE Chk | ERR:%0d PKT:%0d", proto_err, pkt_cnt), UVM_LOW);
  endfunction
endclass
`endif
