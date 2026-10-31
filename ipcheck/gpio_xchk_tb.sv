// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// gpio_xchk_tb.sv -- GPIO_apb (open-ip-portfolio) through its documented
// register map (docs/ip/GPIO.md), with the pins on a board model: each pin
// can be driven from outside or left floating, and every pin level is
// checked as 0, 1 or high impedance (never X, which would be contention).
//   * OE / OUT drive only the enabled pins, released pins float
//   * IN shows the pin levels (own outputs and external drivers)
//   * OUT needs a full-word write (PSTRB 4'hF), a partial one is PSLVERR
//   * HIGH interrupt is level: it sets again after W1C while a pin is high
module gpio_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h47500200;
  localparam int N_WORDS = 8;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, OE = 12'h014,
                          OUT = 12'h018, IN = 12'h01C;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq;
  always #5 PCLK = ~PCLK;

  wire [7:0] gpio;
  logic [7:0] ext_en = 0, ext_val = 0;
  for (genvar i = 0; i < 8; i++) begin : g_board
    assign gpio[i] = ext_en[i] ? ext_val[i] : 1'bz;
  end

  GPIO_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
                .PRDATA, .PREADY, .PSLVERR, .irq, .gpio);

  `include "apb_bfm.svh"

  // expected pin levels for a given OE / OUT and board state
  function automatic logic [7:0] pins(input logic [7:0] oe, input logic [7:0] o);
    for (int i = 0; i < 8; i++) pins[i] = oe[i] ? o[i] : ext_val[i];
  endfunction
  int contention = 0;
  always @(gpio) if (PRESETN) for (int i = 0; i < 8; i++) if (gpio[i] === 1'bx) contention++;

  logic [31:0] v, st;
  bit err;
  initial begin
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    chk(gpio === 8'hzz, "after reset every pin is released");

    // ---- outputs
    apb_wr(OUT, 32'hA5);
    apb_rd(OUT, v);
    chk(v[7:0] == 8'hA5, "OUT reads back");
    chk(gpio === 8'hzz, "OUT alone does not drive (OE = 0)");
    apb_wr(OE, 32'hFF);
    @(negedge PCLK);
    chk(gpio === 8'hA5, "OE = 0xFF: all pins show OUT");
    apb_rd(IN, v);
    chk(v[7:0] == 8'hA5, "IN reads the driven levels");

    // ---- mixed directions with external drivers on the inputs
    begin
      int bad = 0;
      for (int i = 0; i < 40; i++) begin
        logic [7:0] oe, o;
        oe = 8'($urandom); o = 8'($urandom);
        ext_en = ext_en & ~oe;                    // board releases before the IP drives
        apb_wr(OE, {24'h0, oe});
        apb_wr(OUT, {24'h0, o});
        ext_en = ~oe; ext_val = 8'($urandom);
        @(negedge PCLK);
        if (gpio !== pins(oe, o)) bad++;
        apb_rd(IN, v);
        if (v[7:0] != pins(oe, o)) bad++;
      end
      chk(bad == 0, "40 random OE / OUT / external patterns: pins and IN as expected");
      chk(contention == 0, "no pin ever driven both ways (no X)");
    end

    // ---- released pin floats as soon as OE drops
    begin
      ext_en = 8'h00;
      apb_wr(OE, 32'hFF);
      apb_wr(OUT, 32'h3C);
      apb_wr(OE, 32'hF0);
      @(negedge PCLK);
      chk(gpio === 8'b0011_zzzz, $sformatf("OE 0xF0: low nibble floats, high nibble driven (%b)", gpio));
    end

    // ---- OUT partial write
    begin
      logic [31:0] rd;
      apb_xfer(1, OUT, 32'h0000_00FF, 4'h1, rd, err);
      apb_rd(OUT, v);
      chk(err && v[7:0] == 8'h3C, "OUT with PSTRB 0001: PSLVERR, OUT unchanged");
    end

    // ---- HIGH interrupt, level
    begin
      apb_wr(OE, 32'h00);
      ext_en = 8'hFF; ext_val = 8'h00;
      repeat (3) @(negedge PCLK);
      apb_wr(IRQ_STATUS, 32'h1);
      apb_wr(IRQ_ENABLE, 32'h1);
      apb_rd(IRQ_STATUS, st);
      chk(st[0] == 0 && irq === 1'b0, "all pins low: HIGH clear, irq low");
      ext_val = 8'h10;
      repeat (3) @(negedge PCLK);
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && irq === 1'b1, "a pin high: HIGH set, irq high");
      apb_wr(IRQ_STATUS, 32'h1);
      apb_rd(IRQ_STATUS, st);
      chk(st[0], "pin still high: HIGH sets again after W1C (level)");
      ext_val = 8'h00;
      repeat (3) @(negedge PCLK);
      apb_wr(IRQ_STATUS, 32'h1);
      apb_rd(IRQ_STATUS, st);
      chk(!st[0] && irq === 1'b0, "pins low again: HIGH stays clear after W1C");
      // a one-clock pulse is still seen (sampled every PCLK)
      @(negedge PCLK); ext_val = 8'h01; @(negedge PCLK); ext_val = 8'h00;
      repeat (3) @(negedge PCLK);
      apb_rd(IRQ_STATUS, st);
      chk(st[0], "a one-PCLK high pulse sets HIGH");
      apb_wr(IRQ_ENABLE, 32'h0);
      @(negedge PCLK);
      chk(irq === 1'b0, "IRQ_ENABLE = 0 masks irq");
    end

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(10_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
