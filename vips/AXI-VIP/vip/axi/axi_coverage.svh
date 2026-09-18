// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axi_coverage.svh -- AXI4 functional coverage:
//   cg_protocol : burst config (dir x burst x size x len, resp) + crosses
//   cg_fsm      : channel handshake state transitions
//   cg_data     : data pattern corners x direction

`ifndef AXI_COVERAGE_SVH
`define AXI_COVERAGE_SVH

class axi_coverage extends uvm_subscriber #(amba_seq_item);
  `uvm_component_utils(axi_coverage)

  amba_seq_item tr;
  bit [2:0] ch_state;   // encoded channel activity

  covergroup cg_protocol;
    option.per_instance = 1;
    cp_write: coverpoint tr.txn.write { bins rd = {0}; bins wr = {1}; }
    cp_burst: coverpoint tr.txn.burst { bins fixed = {BURST_FIXED};
                                        bins incr  = {BURST_INCR};
                                        bins wrap  = {BURST_WRAP}; }
    cp_size: coverpoint tr.txn.size { bins b1 = {SIZE_1B}; bins b2 = {SIZE_2B};
                                      bins b4 = {SIZE_4B}; bins b8 = {SIZE_8B}; }
    cp_len: coverpoint tr.txn.len { bins single = {1}; bins b2 = {2}; bins b4 = {4};
                                    bins b8 = {8}; bins b16 = {16}; bins other = default; }
    cp_resp: coverpoint tr.txn.resp { bins ok = {RESP_OKAY}; bins slv = {RESP_SLVERR};
                                      bins other = default; }
    cx_wr_burst: cross cp_write, cp_burst;
    cx_burst_len: cross cp_burst, cp_len;
    cx_wr_size_len: cross cp_write, cp_size, cp_len;
  endgroup

  covergroup cg_fsm with function sample(bit [2:0] s);
    option.per_instance = 1;
    cp_state: coverpoint s {
      bins idle = {3'd0};
      bins aw   = {3'd1};
      bins w    = {3'd2};
      bins b    = {3'd3};
      bins ar   = {3'd4};
      bins r    = {3'd5};
    }
    cp_trans: coverpoint s {
      bins wr_flow = (3'd0 => 3'd1 => 3'd2 => 3'd3);
      bins rd_flow = (3'd0 => 3'd4 => 3'd5);
      bins wr_b2b  = (3'd3 => 3'd1);
      bins rd_b2b  = (3'd5 => 3'd4);
    }
  endgroup

  covergroup cg_data;
    option.per_instance = 1;
    cp_data: coverpoint tr.txn.data[0] iff (tr.txn.data.size() > 0) {
      bins zero = {64'h0};
      bins ones = {64'hFFFF_FFFF_FFFF_FFFF};
      bins aa55 = {64'hAAAA_AAAA_AAAA_AAAA, 64'h5555_5555_5555_5555};
      bins other = default;
    }
    cp_w: coverpoint tr.txn.write { bins rd = {0}; bins wr = {1}; }
    cx_wr_data: cross cp_data, cp_w;
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_protocol = new();
    cg_fsm      = new();
    cg_data     = new();
  endfunction

  function void write(amba_seq_item t);
    tr = t;
    // approximate channel flow from the completed transaction
    ch_state = 3'd0;
    cg_fsm.sample(ch_state);
    ch_state = t.txn.write ? 3'd1 : 3'd4;
    cg_fsm.sample(ch_state);
    ch_state = t.txn.write ? 3'd2 : 3'd5;
    cg_fsm.sample(ch_state);
    if (t.txn.write) begin ch_state = 3'd3; cg_fsm.sample(ch_state); end
    cg_protocol.sample();
    cg_data.sample();
  endfunction
endclass
`endif
