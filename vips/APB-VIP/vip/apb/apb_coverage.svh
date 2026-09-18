// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// apb_coverage.svh -- APB4 functional coverage:
//   cg_protocol : transfer config (dir x prot x resp, burst len) + crosses
//   cg_fsm      : PSEL/PENABLE bus-state transitions
//   cg_data     : data pattern corners x direction

`ifndef APB_COVERAGE_SVH
`define APB_COVERAGE_SVH

class apb_coverage extends uvm_subscriber #(amba_seq_item);
  `uvm_component_utils(apb_coverage)

  amba_seq_item tr;
  bit [1:0] bus_state;   // {psel, penable}

  covergroup cg_protocol;
    option.per_instance = 1;
    cp_write: coverpoint tr.txn.write { bins rd = {0}; bins wr = {1}; }
    cp_prot: coverpoint tr.txn.prot { bins normal = {3'b000}; bins priv = {3'b001};
                                      bins secure = {3'b010}; bins other = default; }
    cp_len: coverpoint tr.txn.len { bins single = {1}; bins short = {[2:4]};
                                    bins mid = {[5:8]}; bins long = {[9:16]}; }
    cp_resp: coverpoint tr.txn.resp { bins ok = {RESP_OKAY}; bins err = {RESP_SLVERR}; }
    cx_wr_prot: cross cp_write, cp_prot;
    cx_wr_len:  cross cp_write, cp_len;
    cx_wr_resp: cross cp_write, cp_resp;
  endgroup

  covergroup cg_fsm with function sample(bit [1:0] s);
    option.per_instance = 1;
    cp_state: coverpoint s {
      bins idle   = {2'b00};
      bins setup  = {2'b10};
      bins access = {2'b11};
    }
    cp_trans: coverpoint s {
      bins to_setup   = (2'b00 => 2'b10);
      bins to_access  = (2'b10 => 2'b11);
      bins complete   = (2'b11 => 2'b00);
      bins b2b_setup  = (2'b11 => 2'b10);
      bins wait_state = (2'b11 => 2'b11);
    }
  endgroup

  covergroup cg_data;
    option.per_instance = 1;
    cp_data: coverpoint tr.txn.data[0][31:0] iff (tr.txn.data.size() > 0) {
      bins zero = {32'h0};
      bins ones = {32'hFFFF_FFFF};
      bins aa55 = {32'hAAAA_AAAA, 32'h5555_5555};
      bins other = default;
    }
    cp_w: coverpoint tr.txn.write { bins rd = {0}; bins wr = {1}; }
    cx_wr_data: cross cp_data, cp_w;
  endgroup

  virtual amba_vip_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_protocol = new();
    cg_fsm      = new();
    cg_data     = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    void'(uvm_config_db#(virtual amba_vip_if)::get(this, "", "vif", vif));
  endfunction

  function void write(amba_seq_item t);
    tr = t;
    bus_state = (vif != null) ? {vif.psel, vif.penable} : 2'b00;
    cg_protocol.sample();
    cg_fsm.sample(bus_state);
    cg_data.sample();
  endfunction
endclass
`endif
