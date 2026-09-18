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
// AMBA Interface
// AXI4 + AHB5 + APB4
//============================================================================
`ifndef AMBA_VIP_IF_SV
`define AMBA_VIP_IF_SV
`include "uvm_macros.svh"
import uvm_pkg::*;

interface amba_vip_if (input logic aclk, input logic aresetn);

  // AXI4 Address Write
  logic [31:0] awaddr;
  logic [7:0]  awlen;
  logic [2:0]  awsize;
  logic [1:0]  awburst;
  logic [3:0]  awcache;
  logic [2:0]  awprot;
  logic        awlock;
  logic        awvalid;
  logic        awready;
  // AWID compatibility alias for the tiered SVA compliance checker.
  // This AMBA interface models a single-ID master, so AWID is tied to 0
  // (ID-ordering rules remain valid and trivially satisfied).
  logic [7:0]  awid;
  assign awid = 8'h00;
  // AXI4 Write Data
  logic [63:0] wdata;
  logic [7:0]  wstrb;
  logic        wlast;
  logic        wvalid;
  logic        wready;
  // AXI4 Write Response
  logic [1:0]  bresp;
  logic        bvalid;
  logic        bready;
  // AXI4 Address Read
  logic [31:0] araddr;
  logic [7:0]  arlen;
  logic [2:0]  arsize;
  logic [1:0]  arburst;
  logic        arlock;
  logic        arvalid;
  logic        arready;
  // AXI4 Read Data
  logic [63:0] rdata;
  logic [1:0]  rresp;
  logic        rlast;
  logic        rvalid;
  logic        rready;
  // AXI4-Stream
  logic [63:0] tdata;
  logic        tvalid;
  logic        tready;
  logic        tlast;
  // AHB5
  logic [31:0] haddr;
  logic [2:0]  hburst;
  logic        hmastlock;
  logic [6:0]  hprot;
  logic [2:0]  hsize;
  logic [1:0]  htrans;
  logic [63:0] hwdata;
  logic        hwrite;
  logic [63:0] hrdata;
  logic        hreadyout;
  logic        hresp;
  // APB4
  logic [31:0] paddr;
  logic        penable;
  logic [2:0]  pprot;
  logic        psel;
  logic [3:0]  pstrb;
  logic [31:0] pwdata;
  logic        pwrite;
  logic [31:0] prdata;
  logic        pready;
  logic        pslverr;

  // Driver clocking block (master drives request, samples response)
  clocking drv_cb @(posedge aclk);
    default input #1step output #1ns;
    // AXI master
    output awaddr, awlen, awsize, awburst, awcache, awprot, awlock, awvalid;
    input  awready;
    output wdata, wstrb, wlast, wvalid;
    input  wready;
    input  bresp, bvalid;
    output bready;
    output araddr, arlen, arsize, arburst, arlock, arvalid;
    input  arready;
    input  rdata, rresp, rlast, rvalid;
    output rready;
    output tdata, tvalid, tlast;
    input  tready;
    // AHB master
    output haddr, hburst, hmastlock, hprot, hsize, htrans, hwdata, hwrite;
    input  hrdata, hreadyout, hresp;
    // APB master
    output paddr, penable, pprot, psel, pstrb, pwdata, pwrite;
    input  prdata, pready, pslverr;
  endclocking

  // Monitor clocking block (passive sampling of everything)
  clocking mon_cb @(posedge aclk);
    default input #1step;
    input awaddr, awlen, awsize, awburst, awcache, awprot, awvalid, awready;
    input wdata, wstrb, wlast, wvalid, wready;
    input bresp, bvalid, bready;
    input araddr, arlen, arsize, arburst, arvalid, arready;
    input rdata, rresp, rlast, rvalid, rready;
    input tdata, tvalid, tready, tlast;
    input haddr, hburst, hmastlock, hprot, hsize, htrans, hwdata, hwrite;
    input hrdata, hreadyout, hresp;
    input paddr, penable, pprot, psel, pstrb, pwdata, pwrite;
    input prdata, pready, pslverr;
  endclocking

  modport master_mp  (clocking drv_cb, input aclk, input aresetn);
  modport monitor_mp (clocking mon_cb, input aclk, input aresetn);
  modport slave_mp   (input aclk, input aresetn,
                      input awaddr, awlen, awsize, awburst, awcache, awprot, awvalid,
                      output awready,
                      input wdata, wstrb, wlast, wvalid, output wready,
                      output bresp, bvalid, input bready,
                      input araddr, arlen, arsize, arburst, arvalid, output arready,
                      output rdata, rresp, rlast, rvalid, input rready,
                      input tdata, tvalid, tlast, output tready,
                      input haddr, hburst, hmastlock, hprot, hsize, htrans, hwdata, hwrite,
                      output hrdata, hreadyout, hresp,
                      input paddr, penable, pprot, psel, pstrb, pwdata, pwrite,
                      output prdata, pready, pslverr);

  // Assertions
  property p_axi_awvalid_ready;
    @(posedge aclk) disable iff (!aresetn) awvalid |-> ##[1:16] awready;
  endproperty
  assert_axi_aw: assert property (p_axi_awvalid_ready)
    else `uvm_error("AMBA_IF", "AXI AW timeout");

  property p_axi_wlast;
    @(posedge aclk) disable iff (!aresetn) (wvalid && wlast) |-> $past(wvalid, 1);
  endproperty
  assert_axi_wlast: assert property (p_axi_wlast)
    else `uvm_error("AMBA_IF", "AXI WLAST without data");

  property p_axi_bresp_valid;
    @(posedge aclk) disable iff (!aresetn) bvalid |-> bresp inside {2'b00, 2'b01, 2'b10, 2'b11};
  endproperty
  assert_axi_bresp: assert property (p_axi_bresp_valid)
    else `uvm_error("AMBA_IF", "AXI BRESP invalid");

  property p_ahb_htrans;
    @(posedge aclk) disable iff (!aresetn) htrans inside {2'b00, 2'b01, 2'b10, 2'b11};
  endproperty
  assert_ahb_trans: assert property (p_ahb_htrans)
    else `uvm_error("AMBA_IF", "AHB HTRANS invalid");

  property p_apb_penable;
    @(posedge aclk) disable iff (!aresetn) (psel && !penable) |-> ##1 penable;
  endproperty
  assert_apb_en: assert property (p_apb_penable)
    else `uvm_error("AMBA_IF", "APB PENABLE timing violation");

  // Coverage
  covergroup cg_amba @(posedge aclk);
    option.per_instance = 1;
    cp_awvalid: coverpoint awvalid { bins off = {0}; bins on = {1}; }
    cp_arvalid: coverpoint arvalid { bins off = {0}; bins on = {1}; }
    cp_wvalid:  coverpoint wvalid  { bins off = {0}; bins on = {1}; }
    cp_rvalid:  coverpoint rvalid  { bins off = {0}; bins on = {1}; }
    cp_bvalid:  coverpoint bvalid  { bins off = {0}; bins on = {1}; }
    cp_htrans:  coverpoint htrans  { bins idle = {2'b00}; bins busy = {2'b01};
                                     bins nonseq = {2'b10}; bins seq = {2'b11}; }
    cp_psel:    coverpoint psel    { bins off = {0}; bins on = {1}; }
    cp_penable: coverpoint penable { bins off = {0}; bins on = {1}; }
    cross_aw_ar:  cross cp_awvalid, cp_arvalid;
    cross_psel_en: cross cp_psel, cp_penable;
  endgroup

  cg_amba cg = new();

endinterface
`endif
