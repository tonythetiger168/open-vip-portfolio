// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
//============================================================================
// Top-Level Testbench
// Instantiates all protocol interfaces and DUT stub
//============================================================================
`ifndef TOP_TB_SV
`define TOP_TB_SV
`include "uvm_macros.svh"
import uvm_pkg::*;
import mp_vip_pkg::*;

module top_tb;
  // Clock and reset
  logic clk = 0;
  logic rst_n;

  always #2ns clk = ~clk; // 250MHz

  initial begin
    rst_n = 0;
    #100ns;
    rst_n = 1;
  end

  // Interfaces
  // NOTE: all agents/monitors handle `virtual mp_vip_if` with the default
  // parameterization, so every instance uses the defaults (protocol selection
  // is passed to the agents via uvm_config_db protocol_e instead).
  mp_vip_if pcie5_if(clk, rst_n);  // PROTO_PCIE_GEN5
  mp_vip_if pcie6_if(clk, rst_n);  // PROTO_PCIE_GEN6
  mp_vip_if cxl20_if(clk, rst_n);  // PROTO_CXL_20
  mp_vip_if cxl30_if(clk, rst_n);  // PROTO_CXL_30
  mp_vip_if ucie_if(clk, rst_n);   // PROTO_UCIE
  mp_vip_if ualink_if(clk, rst_n); // PROTO_UALINK

  // DUT instantiation (link + ready model)
  mp_dut dut (
    .clk(clk), .rst_n(rst_n),
    .pcie5_if(pcie5_if),
    .pcie6_if(pcie6_if),
    .cxl20_if(cxl20_if),
    .cxl30_if(cxl30_if),
    .ucie_if(ucie_if),
    .ualink_if(ualink_if)
  );

  // Functional endpoint memory models (closed loop driver->DUT->monitor)
  mp_endpoint_mem_model pcie5_ep_mem (.vif(pcie5_if));
  mp_endpoint_mem_model cxl20_ep_mem (.vif(cxl20_if));

  // Tiered SVA compliance checker bound to the PCIe Gen5 link
  pcie_compliance_checker pcie_sva_chk (.vif(pcie5_if));

  initial begin
    // Pass interfaces to UVM
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "pcie5_vif", pcie5_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "pcie6_vif", pcie6_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "cxl20_vif", cxl20_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "cxl30_vif", cxl30_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "ucie_vif", ucie_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*", "ualink_vif", ualink_if);
    // Per-agent vif bindings
    uvm_config_db#(virtual mp_vip_if)::set(null, "*pcie_gen5_agent*", "vif", pcie5_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*pcie_gen6_agent*", "vif", pcie6_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*cxl20_agent*", "vif", cxl20_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*cxl30_agent*", "vif", cxl30_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*ucie_agent*", "vif", ucie_if);
    uvm_config_db#(virtual mp_vip_if)::set(null, "*ualink_agent*", "vif", ualink_if);
    run_test();
  end
endmodule

//============================================================================
// DUT: link training + ready/valid flow control model
//============================================================================
module mp_dut (
  input logic clk,
  input logic rst_n,
  mp_vip_if pcie5_if,
  mp_vip_if pcie6_if,
  mp_vip_if cxl20_if,
  mp_vip_if cxl30_if,
  mp_vip_if ucie_if,
  mp_vip_if ualink_if
);
  // LTSSM walk: RESET -> DETECT -> POLLING -> CONFIG -> L0 after reset
  task automatic train_link(virtual mp_vip_if vif);
    vif.link_state  = LINK_RESET;
    vif.ltssm_state = 5'h00;
    vif.link_up     = 0;
    @(posedge rst_n);
    repeat (2) @(posedge clk);
    vif.link_state  = LINK_DETECT;
    vif.ltssm_state = 5'h01;
    repeat (2) @(posedge clk);
    vif.link_state  = LINK_POLLING;
    vif.ltssm_state = 5'h02;
    repeat (2) @(posedge clk);
    vif.link_state  = LINK_CONFIG;
    vif.ltssm_state = 5'h03;
    repeat (2) @(posedge clk);
    vif.link_state  = LINK_L0;
    vif.ltssm_state = 5'h10;
    vif.link_up     = 1;
  endtask

  initial fork
    train_link(pcie5_if);
    train_link(pcie6_if);
    train_link(cxl20_if);
    train_link(cxl30_if);
    train_link(ucie_if);
    train_link(ualink_if);
  join

  // Loopback: ready follows valid with small delay
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pcie5_if.ready <= 0; pcie6_if.ready <= 0;
      cxl20_if.ready <= 0; cxl30_if.ready <= 0;
      ucie_if.ready <= 0; ualink_if.ready <= 0;
    end else begin
      pcie5_if.ready <= #1ns pcie5_if.valid;
      pcie6_if.ready <= #1ns pcie6_if.valid;
      cxl20_if.ready <= #1ns cxl20_if.valid;
      cxl30_if.ready <= #1ns cxl30_if.valid;
      ucie_if.ready  <= #1ns ucie_if.valid;
      ualink_if.ready<= #1ns ualink_if.valid;
    end
  end
endmodule

//============================================================================
// Functional PCIe/CXL endpoint model: snoops TLP traffic, stores memory-write
// payloads into an associative memory, counts read/write TLPs. Passive on the
// bus (ready handshake is provided by mp_dut), so driver->DUT->monitor forms
// a closed loop without multi-driver conflicts.
//============================================================================
module mp_endpoint_mem_model (mp_vip_if vif);
  bit [31:0] mem [bit [63:0]];
  int unsigned wr_count = 0, rd_count = 0;
  bit [63:0] cur_addr;
  bit        in_tlp = 0;

  always @(posedge vif.clk) begin
    if (!vif.rst_n) begin
      in_tlp <= 0;
    end else if (vif.valid) begin
      if (vif.sop) begin
        cur_addr <= vif.data[127:64];
        in_tlp   <= !vif.eop;
        if (vif.eop) begin
          mem[vif.data[127:64]] = vif.data[31:0];
          wr_count++;
        end
      end else begin
        mem[cur_addr] = vif.data[31:0];
        cur_addr <= cur_addr + 4;
        if (vif.eop) begin
          in_tlp <= 0;
          wr_count++;
        end
      end
    end
  end

  final begin
    $display("MP_ENDPOINT_MEM_MODEL: tlp_writes=%0d mem_entries=%0d",
             wr_count, mem.num());
  end
endmodule
`endif
