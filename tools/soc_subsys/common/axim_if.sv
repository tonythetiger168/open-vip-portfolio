// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axim_if.sv -- AXI4 manager-port interface (32-bit address and data, 4-bit
// ID) for the AXI master port ("m_" pins) of the open-ip-portfolio IPs.
//
// The IP is the manager; the testbench side (axim_subordinate in ssv_pkg) is
// the subordinate. Signal names are the IP's pin names without the "m_"
// prefix, so a bench connects .m_awaddr(axi.awaddr) and so on.
//
// The interface carries its own cycle-level protocol checker (AMBA AXI4,
// IHI 0022, A3.2 handshake rules):
//   CHK_STABLE_<ch>  VALID, once high, stays high until READY, and the
//                    payload of that channel does not change meanwhile
//                    (AW, W, AR from the manager; B, R from the subordinate)
//   CHK_RESET        no VALID while ARESETn is low
//   CHK_UNKNOWN      no X/Z on a VALID, or on a payload while its VALID is high
// A failure prints "AXIM_CHK_ERROR <rule> ..." and increments chk_errors
// (per rule in chk_rule_errors); the UVM monitor turns new failures into
// UVM errors. chk_en = 0 turns the checker off (negative tests switch it off
// around an injected violation that only the transaction checks look at).
// Procedural code rather than SVA, so the same checks run on Verilator
// without --assert, on Icarus and on the commercial simulators.

interface axim_if (input logic aclk, input logic aresetn);
  // write address
  logic [3:0]  awid;
  logic [31:0] awaddr;
  logic [7:0]  awlen;
  logic [2:0]  awsize;
  logic [1:0]  awburst;
  logic [2:0]  awprot;
  logic        awvalid;
  logic        awready;
  // write data
  logic [31:0] wdata;
  logic [3:0]  wstrb;
  logic        wlast;
  logic        wvalid;
  logic        wready;
  // write response
  logic [3:0]  bid;
  logic [1:0]  bresp;
  logic        bvalid;
  logic        bready;
  // read address
  logic [3:0]  arid;
  logic [31:0] araddr;
  logic [7:0]  arlen;
  logic [2:0]  arsize;
  logic [1:0]  arburst;
  logic [2:0]  arprot;
  logic        arvalid;
  logic        arready;
  // read data
  logic [3:0]  rid;
  logic [31:0] rdata;
  logic [1:0]  rresp;
  logic        rlast;
  logic        rvalid;
  logic        rready;

  // ---------------------------------------------------------------- checker
  bit          chk_en = 1'b1;
  int unsigned chk_errors = 0;
  int unsigned chk_rule_errors[string];
  string       chk_last = "";

  function automatic void chk_fail(string rule, string msg);
    chk_errors++;
    if (chk_rule_errors.exists(rule)) chk_rule_errors[rule]++;
    else chk_rule_errors[rule] = 1;
    chk_last = {rule, ": ", msg};
    $display("AXIM_CHK_ERROR %s @%0t: %s", rule, $time, msg);
  endfunction

  function automatic int unsigned rule_count(string rule);
    return chk_rule_errors.exists(rule) ? chk_rule_errors[rule] : 0;
  endfunction

  // previous-cycle copies (handshake rules compare against the last edge)
  logic        p_awvalid, p_awready, p_wvalid, p_wready, p_bvalid, p_bready;
  logic        p_arvalid, p_arready, p_rvalid, p_rready;
  logic [51:0] p_aw, p_ar;
  logic [36:0] p_w;
  logic [5:0]  p_b;
  logic [38:0] p_r;
  wire  [51:0] c_aw = {awid, awaddr, awlen, awsize, awburst, awprot};
  wire  [51:0] c_ar = {arid, araddr, arlen, arsize, arburst, arprot};
  wire  [36:0] c_w  = {wdata, wstrb, wlast};
  wire  [5:0]  c_b  = {bid, bresp};
  wire  [38:0] c_r  = {rid, rdata, rresp, rlast};

  bit primed = 1'b0;   // one clock out of reset before the stability rules apply

  always @(posedge aclk) begin
    if (!aresetn) begin
      primed <= 1'b0;
      if (chk_en && (awvalid === 1'b1 || wvalid === 1'b1 || arvalid === 1'b1))
        chk_fail("CHK_RESET", "manager VALID high during reset");
      if (chk_en && (bvalid === 1'b1 || rvalid === 1'b1))
        chk_fail("CHK_RESET", "subordinate VALID high during reset");
    end else begin
      if (chk_en) begin
        if ($isunknown({awvalid, wvalid, bvalid, arvalid, rvalid, awready, wready, bready, arready, rready}))
          chk_fail("CHK_UNKNOWN", "X/Z on a VALID or READY");
        if (awvalid === 1'b1 && $isunknown(c_aw)) chk_fail("CHK_UNKNOWN", "X/Z on AW payload");
        if (wvalid  === 1'b1 && $isunknown(c_w))  chk_fail("CHK_UNKNOWN", "X/Z on W payload");
        if (arvalid === 1'b1 && $isunknown(c_ar)) chk_fail("CHK_UNKNOWN", "X/Z on AR payload");
        if (bvalid  === 1'b1 && $isunknown(c_b))  chk_fail("CHK_UNKNOWN", "X/Z on B payload");
        if (rvalid  === 1'b1 && $isunknown(c_r))  chk_fail("CHK_UNKNOWN", "X/Z on R payload");
      end
      if (chk_en && primed) begin
        if (p_awvalid && !p_awready) begin
          if (!awvalid)       chk_fail("CHK_STABLE_AW", "AWVALID dropped before AWREADY");
          else if (c_aw != p_aw) chk_fail("CHK_STABLE_AW", $sformatf("AW payload changed while waiting (addr %h -> %h)", p_aw[47:16], awaddr));
        end
        if (p_wvalid && !p_wready) begin
          if (!wvalid)        chk_fail("CHK_STABLE_W", "WVALID dropped before WREADY");
          else if (c_w != p_w) chk_fail("CHK_STABLE_W", "W payload changed while waiting");
        end
        if (p_arvalid && !p_arready) begin
          if (!arvalid)       chk_fail("CHK_STABLE_AR", "ARVALID dropped before ARREADY");
          else if (c_ar != p_ar) chk_fail("CHK_STABLE_AR", $sformatf("AR payload changed while waiting (addr %h -> %h)", p_ar[47:16], araddr));
        end
        if (p_bvalid && !p_bready) begin
          if (!bvalid)        chk_fail("CHK_STABLE_B", "BVALID dropped before BREADY");
          else if (c_b != p_b) chk_fail("CHK_STABLE_B", "B payload changed while waiting");
        end
        if (p_rvalid && !p_rready) begin
          if (!rvalid)        chk_fail("CHK_STABLE_R", "RVALID dropped before RREADY");
          else if (c_r != p_r) chk_fail("CHK_STABLE_R", "R payload changed while waiting");
        end
      end
      primed <= 1'b1;
    end
    p_awvalid <= awvalid; p_awready <= awready; p_aw <= c_aw;
    p_wvalid  <= wvalid;  p_wready  <= wready;  p_w  <= c_w;
    p_bvalid  <= bvalid;  p_bready  <= bready;  p_b  <= c_b;
    p_arvalid <= arvalid; p_arready <= arready; p_ar <= c_ar;
    p_rvalid  <= rvalid;  p_rready  <= rready;  p_r  <= c_r;
  end
endinterface
