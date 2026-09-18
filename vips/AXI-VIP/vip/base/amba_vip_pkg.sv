// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//============================================================================
// AMBA VIP Package
// Protocols: AXI4/AXI4-Lite/AXI4-Stream, AHB5/APB4
//============================================================================
`ifndef AMBA_VIP_PKG_SV
`define AMBA_VIP_PKG_SV

// Tiered SVA compliance checker (L1/L2/L3/L4) and protocol checkers: the SVA
// content lives in modules (class-scope concurrent assertions are illegal per
// IEEE 1800); thin class shells remain. Included at compilation-unit scope,
// outside and before the package, so amba_env / top_tb can see them.
`include "sva/axi_compliance_checker.sv"
`include "ahb_protocol_checker.sv"
`include "apb_protocol_checker.sv"
`include "axi_protocol_checker.sv"

package amba_vip_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  typedef enum int { AXI4=0, AXI4_LITE=1, AXI4_STREAM=2, AHB5=3, APB4=4, AMBA_MAX=5 } amba_protocol_e;
  typedef enum logic [1:0] { BURST_FIXED=2'b00, BURST_INCR=2'b01, BURST_WRAP=2'b10, BURST_RSVD=2'b11 } axburst_e;
  typedef enum logic [2:0] { SIZE_1B=3'b000, SIZE_2B=3'b001, SIZE_4B=3'b010, SIZE_8B=3'b011,
                             SIZE_16B=3'b100, SIZE_32B=3'b101, SIZE_64B=3'b110, SIZE_128B=3'b111 } axsize_e;
  typedef enum logic [1:0] { RESP_OKAY=2'b00, RESP_EXOKAY=2'b01, RESP_SLVERR=2'b10, RESP_DECERR=2'b11 } resp_e;
  typedef enum logic [2:0] { AHB_IDLE=3'b000, AHB_BUSY=3'b001, AHB_NONSEQ=3'b010, AHB_SEQ=3'b011 } htrans_e;

  class amba_txn extends uvm_object;
    `uvm_object_utils(amba_txn)
    rand amba_protocol_e protocol;
    rand logic [31:0]   addr;
    rand logic [63:0]   data[];
    rand int            len;
    rand axburst_e      burst;
    rand axsize_e       size;
    rand logic [3:0]    cache;
    rand logic [2:0]    prot;
    rand resp_e         resp;
    rand bit            excl;
    rand int            delay;
    rand bit            write;   // 1 = write, 0 = read

    constraint c_len  { len inside {[1:16]}; }
    constraint c_data { data.size() == len; }
    constraint c_resp { resp dist { RESP_OKAY := 90, RESP_SLVERR := 10 }; }

    function new(string name = "amba_txn");
      super.new(name);
    endfunction

    virtual function string convert2string();
      return $sformatf("%s %s addr=0x%08X len=%0d burst=%s resp=%s",
                       protocol.name(), write ? "WR" : "RD", addr, len,
                       burst.name(), resp.name());
    endfunction
  endclass

  class amba_seq_item extends uvm_sequence_item;
    `uvm_object_utils(amba_seq_item)
    rand amba_txn txn;
    function new(string name = "amba_seq_item");
      super.new(name);
      txn = amba_txn::type_id::create("txn");
    endfunction
    virtual function string convert2string();
      return txn.convert2string();
    endfunction
  endclass

  class amba_cov extends uvm_subscriber #(amba_seq_item);
    `uvm_component_utils(amba_cov)
    amba_protocol_e protocol;
    axburst_e burst;
    axsize_e size;
    int len;
    resp_e resp;
    logic clk;
    covergroup cg_axi;
      option.per_instance = 1;
      cp_prot: coverpoint protocol { bins axi4 = {AXI4}; bins lite = {AXI4_LITE};
                                     bins stream = {AXI4_STREAM}; bins ahb = {AHB5}; bins apb = {APB4}; }
      cp_burst: coverpoint burst { bins fixed = {BURST_FIXED}; bins incr = {BURST_INCR}; bins wrap = {BURST_WRAP}; }
      cp_size: coverpoint size { bins b1 = {SIZE_1B}; bins b4 = {SIZE_4B}; bins b8 = {SIZE_8B};
                                 bins b16 = {SIZE_16B}; bins b64 = {SIZE_64B}; bins b128 = {SIZE_128B}; }
      cp_len: coverpoint len { bins single = {1}; bins burst4 = {[2:4]}; bins burst8 = {[5:8]}; bins burst16 = {[9:16]}; }
      cp_resp: coverpoint resp { bins ok = {RESP_OKAY}; bins slv = {RESP_SLVERR};
                                 // REACHABILITY: RESP_EXOKAY / RESP_DECERR can never be observed in
                                 // this TB: AHB hresp and APB pslverr are 1-bit (OKAY/ERROR only) and
                                 // the AXI DUT model drives only OKAY/SLVERR on bresp/rresp.
                                 ignore_bins ex  = {RESP_EXOKAY};
                                 ignore_bins dec = {RESP_DECERR}; }
      cross_burst_len: cross cp_burst, cp_len;
      cross_prot_size: cross cp_prot, cp_size;
    endgroup
    function new(string name = "amba_cov", uvm_component parent = null);
      super.new(name, parent);
      cg_axi = new();
    endfunction
    // uvm_subscriber write: sample observed (monitor-decoded) transactions
    function void write(amba_seq_item item);
      sample(item.txn);
    endfunction
    function void sample(amba_txn t);
      protocol = t.protocol;
      burst    = t.burst;
      size     = t.size;
      len      = t.len;
      resp     = t.resp;
      cg_axi.sample();
    endfunction
    function real get_cov();
      return cg_axi.get_coverage();
    endfunction
  endclass

  `uvm_analysis_imp_decl(_exp)
  `uvm_analysis_imp_decl(_obs)

  // End-to-end scoreboard: compares driver-issued (expected) transactions
  // against monitor-decoded (observed) transactions.
  class amba_sb extends uvm_scoreboard;
    `uvm_component_utils(amba_sb)
    uvm_analysis_imp     #(amba_seq_item, amba_sb) analysis_imp;  // legacy counting port
    uvm_analysis_imp_exp #(amba_seq_item, amba_sb) exp_ap;
    uvm_analysis_imp_obs #(amba_seq_item, amba_sb) obs_ap;

    int txn_cnt, err_cnt;
    int unsigned n_matches = 0, n_mismatches = 0;
    amba_seq_item exp_q[$], obs_q[$];

    function new(string name = "amba_sb", uvm_component parent = null);
      super.new(name, parent);
      analysis_imp = new("analysis_imp", this);
      exp_ap = new("exp_ap", this);
      obs_ap = new("obs_ap", this);
    endfunction

    virtual function void write(amba_seq_item item);
      txn_cnt++;
      if (item.txn.resp inside {RESP_SLVERR, RESP_DECERR}) err_cnt++;
    endfunction

    virtual function void write_exp(amba_seq_item item);
      exp_q.push_back(item);
      check();
    endfunction

    virtual function void write_obs(amba_seq_item item);
      obs_q.push_back(item);
      check();
    endfunction

    virtual function void check();
      while (exp_q.size() && obs_q.size()) begin
        amba_seq_item e = exp_q.pop_front();
        amba_seq_item o = obs_q.pop_front();
        bit ok = (e.txn.addr == o.txn.addr) && (e.txn.len == o.txn.len) &&
                 (e.txn.write == o.txn.write);
        if (ok && e.txn.write)
          foreach (e.txn.data[i])
            if (e.txn.data[i] !== o.txn.data[i]) ok = 0;
        if (ok) n_matches++;
        else begin
          n_mismatches++;
          `uvm_error("SB", $sformatf("mismatch exp{%s} obs{%s}",
                     e.convert2string(), o.convert2string()))
        end
      end
    endfunction

    virtual function void report_phase(uvm_phase phase);
      `uvm_info("SB", $sformatf("TXN:%0d ERR:%0d", txn_cnt, err_cnt), UVM_LOW)
      `uvm_info("SB", $sformatf("amba scoreboard: n_matches=%0d n_mismatches=%0d",
                n_matches, n_mismatches), UVM_LOW)
      if (n_mismatches) `uvm_error("SB", "end-to-end n_mismatches detected")
    endfunction
  endclass

  // Deepened AHB5 master UVC (sequencer/driver/monitor/agent/coverage/sequences)
  `include "axi_sequencer.svh"
  `include "axi_driver.svh"
  `include "axi_monitor.svh"
  `include "axi_agent.svh"
  `include "axi_coverage.svh"
  `include "axi_sequences.svh"

  // Tiered SVA compliance checker (L1/L2/L3/L4)
  `include "sva/axi_compliance_checker.sv"

endpackage
`endif
