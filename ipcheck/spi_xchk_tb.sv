// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// spi_xchk_tb.sv -- SPI_apb (open-ip-portfolio) through its documented
// register map (docs/ip/SPI.md) against a mode-0 controller written from
// the SPI rules (CPOL = 0, CPHA = 0, MSB first):
//   * the controller drives MOSI before each SCLK rising edge and samples
//     MISO on it; MISO must already hold its bit one PCLK before the edge
//     (setup) and the first bit must be valid before the first edge
//   * single bytes, three-byte frames under one CSn, a frame aborted by CSn
//     after three bits, SCLK toggling while CSn is high, SCLK at the
//     documented minimum (two PCLK high, two low) and slower
//   * the register contract: TX write / readback, RX, BYTE interrupt, W1C
`ifndef SEED
`define SEED 1
`endif
module spi_xchk_tb;
  int checks = 0, fails = 0, notes = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h53500200;
  localparam int N_WORDS = 7;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, TX = 12'h014, RX = 12'h018;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq, miso;
  logic sclk = 0, mosi = 0, csn = 1;
  always #5 PCLK = ~PCLK;

  SPI_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
               .PRDATA, .PREADY, .PSLVERR, .irq, .sclk, .mosi, .miso, .csn);

  `include "apb_bfm.svh"

  int bytes_irq = 0;
  always @(posedge PCLK) if (dut.u_core.irq) bytes_irq++;

  int half = 4;             // SCLK half period in PCLK clocks
  int setup_bad = 0;
  // one byte, MSB first; returns what MISO carried
  task automatic xfer(input logic [7:0] o, output logic [7:0] i, input int nbits = 8);
    logic pre;
    for (int k = 7; k > 7 - nbits; k--) begin
      mosi = o[k];
      repeat (half - 1) @(negedge PCLK);
      pre = miso;
      @(negedge PCLK);
      sclk = 1;                                   // rising edge: both sides sample
      i[k] = miso;
      if (pre !== miso) setup_bad++;
      repeat (half) @(negedge PCLK);
      sclk = 0;
    end
  endtask
  task automatic select();
    csn = 0;
    repeat (half) @(negedge PCLK);
  endtask
  task automatic deselect();
    repeat (half) @(negedge PCLK);
    csn = 1;
    repeat (2 * half) @(negedge PCLK);
  endtask

  logic [31:0] v, st;
  int seed = `SEED;
  initial begin
    logic [7:0] got;
    void'($urandom(seed));
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h1);
    apb_wr(IRQ_STATUS, 32'h1);

    // ---- single bytes both ways, at three SCLK speeds
    begin
      int bad_rx = 0, bad_tx = 0, bad_rb = 0, n = 0;
      for (int s = 0; s < 3; s++) begin
        half = s == 0 ? 2 : s == 1 ? 4 : 7;
        for (int j = 0; j < 8; j++) begin
          logic [7:0] o, t;
          o = 8'($urandom); t = 8'($urandom);
          if (j == 0) begin o = 8'h80; t = 8'h01; end
          if (j == 1) begin o = 8'h01; t = 8'h80; end
          apb_wr(TX, {24'h0, t});
          apb_rd(TX, v);
          if (v[7:0] != t) bad_rb++;
          select(); xfer(o, got); deselect();
          n++;
          apb_rd(RX, v);
          if (v[7:0] != o) bad_rx++;
          if (got != t) begin bad_tx++; $display("  miso %h exp %h half %0d", got, t, half); end
        end
      end
      chk(bad_rb == 0, "TX reads back the written byte");
      chk(bad_rx == 0, $sformatf("MOSI -> RX, MSB first, SCLK half period 2 / 4 / 7 PCLK (%0d wrong of %0d)", bad_rx, n));
      chk(bad_tx == 0, $sformatf("TX -> MISO, MSB first, sampled on SCLK rise (%0d wrong of %0d)", bad_tx, n));
      chk(setup_bad == 0, $sformatf("MISO stable one PCLK before each SCLK rise (%0d violations)", setup_bad));
      chk(bytes_irq == n, $sformatf("one BYTE interrupt per byte (%0d for %0d)", bytes_irq, n));
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && irq === 1'b1, "IRQ_STATUS.BYTE set and irq high");
      apb_wr(IRQ_STATUS, 32'h1);
      @(posedge PCLK);
      chk(irq === 1'b0, "irq low after W1C");
    end

    // ---- three bytes under one CSn
    begin
      logic [7:0] g [3];
      int b0;
      half = 3;
      b0 = bytes_irq;
      apb_wr(TX, 32'hC5);
      select();
      xfer(8'h12, g[0]); xfer(8'h34, g[1]); xfer(8'h56, g[2]);
      deselect();
      apb_rd(RX, v);
      chk(v[7:0] == 8'h56, "3-byte frame: RX holds the last byte");
      chk(bytes_irq == b0 + 3, "3-byte frame: three BYTE interrupts");
      chk(g[0] == 8'hC5 && g[1] == 8'hC5 && g[2] == 8'hC5, "3-byte frame: MISO repeats TX for every byte");
    end

    // ---- CSn raised after three bits: the next frame starts on a byte boundary
    begin
      int b0;
      b0 = bytes_irq;
      apb_wr(TX, 32'h96);
      select(); xfer(8'hE0, got, 3); deselect();
      chk(bytes_irq == b0, "aborted 3-bit frame: no BYTE interrupt");
      select(); xfer(8'h3B, got); deselect();
      apb_rd(RX, v);
      chk(v[7:0] == 8'h3B && bytes_irq == b0 + 1, "frame after the abort: aligned byte");
      chk(got == 8'h96, "frame after the abort: MISO from bit 7");
    end

    // ---- SCLK while CSn is high is ignored
    begin
      int b0;
      b0 = bytes_irq;
      xfer(8'hFF, got); xfer(8'hFF, got);
      repeat (4) @(negedge PCLK);
      apb_rd(RX, v);
      chk(bytes_irq == b0 && v[7:0] == 8'h3B, "SCLK with CSn high: no byte, RX unchanged");
      if (miso !== 1'bz) begin
        notes++;
        $display("  [NOTE] MISO is driven (%b) while CSn is high; a shared SPI bus needs it released", miso);
      end
    end

    $display("%s checks=%0d fails=%0d notes=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails, notes);
    $finish;
  end
  initial begin #(50_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
