// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// csi2_protocol_checker.sv -- CSI-2 protocol checker (deepened)
// Header ECC re-computation, payload CRC-16 re-computation, FS/FE framing
`ifndef CSI2_PROTOCOL_CHECKER_SV
`define CSI2_PROTOCOL_CHECKER_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class csi2_protocol_checker extends uvm_component;
  `uvm_component_utils(csi2_protocol_checker)
  virtual mipi_vip_if vif;
  int ecc_err, crc_err, seq_err;
  int fs_cnt, fe_cnt;

    logic [5:0] samp_pkt;
  logic [2:0] samp_vc;
  logic [15:0] samp_wc;

covergroup cg_csi2;
    option.per_instance=1;
    cp_pkt: coverpoint samp_pkt { bins fs={6'h00}; bins fe={6'h01}; bins ls={6'h02}; bins le={6'h03}; bins rgb={6'h0E,6'h1E,6'h2E}; bins raw={6'h28,6'h2A,6'h2B,6'h2C,6'h2D}; bins yuv={6'h18,6'h1F}; bins user={[6'h30:6'h37]}; bins null_b={6'h3A,6'h3B}; bins emb={6'h3C}; }
    cp_vc: coverpoint samp_vc { bins vc0={0}; bins vc1={1}; bins vc2={2}; bins vc3={3}; bins vc4_7={[4:7]}; }
    cp_wc: coverpoint samp_wc { bins wc_small={[1:255]}; bins wc_med={[256:1023]}; bins wc_large={[1024:4095]}; }
    cross_pkt_vc: cross cp_pkt, cp_vc;
  endgroup

  function new(string name="csi2_chk", uvm_component parent=null);
    super.new(name,parent);
    ecc_err=0;crc_err=0;seq_err=0;fs_cnt=0;fe_cnt=0;
    cg_csi2 = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual mipi_vip_if)::get(this, "", "vif",vif))
      `uvm_fatal("CONFIG", "CSI-2 chk: no vif");
  endfunction

  // procedural protocol checks, sampled from the bus waveform
  task run_phase(uvm_phase phase);
    logic [31:0] payload[$];
    logic [31:0] payload_arr[];
    bit fs_pending; int fs_age;
    forever begin
      @(vif.mon_cb);
      if (!vif.rst_n) begin fs_pending = 0; continue; end
      if (fs_pending) begin
        fs_age++;
        if (fs_age > 1000) begin
          `uvm_error("CSI2_CHK", "CSI-2 FS without FE"); seq_err++; fs_pending = 0;
        end
      end
      if (vif.mon_cb.valid && vif.mon_cb.ready && vif.mon_cb.sop) begin
        payload.delete();
        payload.push_back(vif.mon_cb.data);
        // header must carry a non-zero ECC field
        if (vif.mon_cb.ecc == 16'h0000) begin
          `uvm_error("CSI2_CHK", "CSI-2 ECC zero"); ecc_err++;
        end
        // re-compute header ECC
        if (vif.mon_cb.ecc != {8'h00, mipi_vip_pkg::mipi_calc_ecc({vif.mon_cb.word_count, vif.mon_cb.vc[1:0], vif.mon_cb.pkt_type})}) begin
          `uvm_warning("CSI2_CHK", "CSI-2 header ECC mismatch"); ecc_err++;
        end
        // long packets must carry a non-zero word count
        if (vif.mon_cb.pkt_type >= 6'h10 && vif.mon_cb.word_count == 0) begin
          `uvm_error("CSI2_CHK", "CSI-2 long packet with WC==0"); seq_err++;
        end
        if (vif.mon_cb.pkt_type == mipi_vip_pkg::PKT_FS) begin fs_cnt++; fs_pending = 1; fs_age = 0; end
        if (vif.mon_cb.pkt_type == mipi_vip_pkg::PKT_FE) begin fe_cnt++; fs_pending = 0; end
        samp_pkt = vif.mon_cb.pkt_type;
        samp_vc  = vif.mon_cb.vc;
        samp_wc  = vif.mon_cb.word_count;
        cg_csi2.sample();
        if (vif.mon_cb.eop) begin
          if (vif.mon_cb.crc == 32'h0) begin `uvm_error("CSI2_CHK", "CSI-2 CRC zero"); crc_err++; end
          payload_arr = payload;
          if (vif.mon_cb.crc[15:0] != mipi_vip_pkg::mipi_calc_crc16(payload_arr)) begin
            `uvm_warning("CSI2_CHK", "CSI-2 payload CRC mismatch"); crc_err++;
          end
        end else begin
          // gather payload beats until EOP
          forever begin
            @(vif.mon_cb);
            if (!(vif.mon_cb.valid && vif.mon_cb.ready)) continue;
            payload.push_back(vif.mon_cb.data);
            if (vif.mon_cb.eop) begin
              if (vif.mon_cb.crc == 32'h0) begin `uvm_error("CSI2_CHK", "CSI-2 CRC zero"); crc_err++; end
              payload_arr = payload;
          if (vif.mon_cb.crc[15:0] != mipi_vip_pkg::mipi_calc_crc16(payload_arr)) begin
                `uvm_warning("CSI2_CHK", "CSI-2 payload CRC mismatch"); crc_err++;
              end
              break;
            end
          end
        end
      end
    end
  endtask

  virtual function void report_phase(uvm_phase phase);
    `uvm_info("CSI2_PROTOCOL_CHECKER_RPT",$sformatf("CSI-2 Chk | ECC:%0d CRC:%0d Seq:%0d FS:%0d FE:%0d",ecc_err,crc_err,seq_err,fs_cnt,fe_cnt),UVM_LOW);
  endfunction
endclass
`endif
