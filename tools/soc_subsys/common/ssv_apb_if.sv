// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_apb_if.sv -- APB4 register port of an open-ip-portfolio <P>_apb wrapper
// (32-bit data, 12-bit byte address, PSTRB, no PPROT) plus the wrapper's
// level-high irq output. The testbench is the APB requester.

interface ssv_apb_if (input logic pclk, input logic presetn);
  logic        psel;
  logic        penable;
  logic        pwrite;
  logic [11:0] paddr;
  logic [31:0] pwdata;
  logic [3:0]  pstrb;
  logic [31:0] prdata;
  logic        pready;
  logic        pslverr;
  logic        irq;      // <P>_apb.irq = |(IRQ_STATUS & IRQ_ENABLE)

  int unsigned chk_errors = 0;
  // APB4 (IHI 0024) 2.1 / 3.x: PENABLE only in the access phase, and the
  // address, control and write data stay stable from setup to completion.
  logic        p_psel, p_penable, p_pready;
  logic [48:0] p_ctl;
  wire  [48:0] c_ctl = {pwrite, paddr, pwdata, pstrb};
  always @(posedge pclk) begin
    if (presetn) begin
      if (penable && !psel) begin
        chk_errors++; $display("APB_CHK_ERROR @%0t: PENABLE without PSEL", $time);
      end
      if (p_psel && !(p_penable && p_pready) && psel && c_ctl != p_ctl) begin
        chk_errors++; $display("APB_CHK_ERROR @%0t: control changed inside a transfer", $time);
      end
      if (p_psel && !p_penable && psel && !penable) begin
        chk_errors++; $display("APB_CHK_ERROR @%0t: setup phase longer than one clock", $time);
      end
    end
    p_psel <= psel; p_penable <= penable; p_pready <= pready; p_ctl <= c_ctl;
  end
endinterface
