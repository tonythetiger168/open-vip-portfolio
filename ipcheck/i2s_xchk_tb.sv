// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// i2s_xchk_tb.sv -- I2S_apb (open-ip-portfolio) through its documented
// register map (docs/ip/I2S.md) against an I2S bus master written from the
// Philips I2S bus specification: the master drives BCLK and WS (LRCK, 0 =
// left), changes WS and SDIN on BCLK falling edges with the MSB one BCLK
// after each WS transition, and samples SDOUT on BCLK rising edges.
//   * 16-bit slots (exact, each word's LSB in the first bit of the next
//     slot) and 32-bit slots (padding: TX sends 0, RX ignores the extra
//     bits), BCLK at the documented minimum (two clocks per phase) and at
//     three, SDOUT stable one clock before every BCLK rise at three
//   * RX_LEFT / RX_RIGHT, TX_LEFT / TX_RIGHT repeated every frame, FRAME
//     interrupt on every WS transition
`ifndef SEED
`define SEED 1
`endif
module i2s_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h49320200;
  localparam int N_WORDS = 9;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, TX_LEFT = 12'h014,
                          TX_RIGHT = 12'h018, RX_LEFT = 12'h01C, RX_RIGHT = 12'h020;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq, sdout;
  logic bclk = 0, lrck = 0, sdin = 0;
  always #5 PCLK = ~PCLK;

  I2S_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
               .PRDATA, .PREADY, .PSLVERR, .irq, .bclk, .lrck, .sdin, .sdout);

  `include "apb_bfm.svh"

  int frames_irq = 0;
  always @(posedge PCLK) if (dut.u_core.irq) frames_irq++;

  // ---------------- bus master ----------------
  int half = 3, setup_bad = 0;
  logic [31:0] v, st;
  int seed = `SEED;
  initial begin
    logic [31:0] gl, gr, gl2, gr2;
    logic t0;
    void'($urandom(seed));
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    apb_wr(IRQ_ENABLE, 32'h1);

    begin
      int bad_rx = 0, bad_tx = 0, n = 0;
      logic [15:0] pl, pr;                     // previous frame's samples
      for (int s = 0; s < 4; s++) begin
        int slot;
        slot = s < 2 ? 16 : 32;
        half = s % 2 == 0 ? 2 : 3;
        for (int j = 0; j < 6; j++) begin
          logic [15:0] l, r, tl, tr;
          l = 16'($urandom); r = 16'($urandom); tl = 16'($urandom); tr = 16'($urandom);
          if (j == 0) begin l = 16'h8001; r = 16'h7FFE; tl = 16'h8000; tr = 16'h0001; end
          apb_wr(TX_LEFT, {16'h0, tl});
          apb_wr(TX_RIGHT, {16'h0, tr});
          // the bits of a slot: [delay bit][DW data bits][padding]
          send_frame(slot, l, r, gl, gr, t0);
          send_frame(slot, l, r, gl, gr, t0);    // second frame: TX settled
          send_frame(slot, l, r, gl2, gr2, t0);  // its first bit ends the right word
          if (slot == 16) gr[16] = t0;           // right LSB, one BCLK after WS fell
          apb_rd(RX_LEFT, v);
          if (v[15:0] != l) begin bad_rx++; $display("  rx left %h exp %h slot %0d", v[15:0], l, slot); end
          apb_rd(RX_RIGHT, v);
          if (v[15:0] != r) begin bad_rx++; $display("  rx right %h exp %h slot %0d", v[15:0], r, slot); end
          if (gl[31:16] != tl || gr[31:16] != tr) begin
            bad_tx++; $display("  sdout %h %h exp %h %h slot %0d", gl[31:16], gr[31:16], tl, tr, slot);
          end
          if (slot == 32 && (gl[15:0] != 0 || gr[15:0] != 0)) begin
            bad_tx++; $display("  padding %h %h", gl[15:0], gr[15:0]);
          end
          n++;
        end
      end
      chk(bad_rx == 0, $sformatf("SDIN -> RX_LEFT / RX_RIGHT, MSB one BCLK after WS, 16- and 32-bit slots (%0d wrong of %0d frames)", bad_rx, n));
      chk(bad_tx == 0, $sformatf("TX_LEFT / TX_RIGHT -> SDOUT with the one-BCLK delay, zero padding (%0d wrong)", bad_tx));
      chk(setup_bad_h[3] == 0, $sformatf("SDOUT stable one PCLK before every BCLK rise at 3 clocks per phase (%0d)", setup_bad_h[3]));
      if (setup_bad_h[2] != 0)
        $display("  [NOTE] at the documented minimum of 2 clocks per BCLK phase SDOUT changes less than one clock before the BCLK rise (%0d of %0d bits): no setup margin for the receiver", setup_bad_h[2], 2 * 16 * 6 * 3 + 2 * 32 * 6 * 3);
      chk(frames_irq == 6 * n - 1, $sformatf("FRAME interrupt on every WS transition (%0d for %0d)", frames_irq, 6 * n - 1));
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && irq === 1'b1, "IRQ_STATUS.FRAME set, irq high");
      apb_wr(IRQ_STATUS, 32'h1);
      @(posedge PCLK);
      chk(irq === 1'b0, "irq low after W1C");
    end

    // TX registers are write-only (read 0); a partial write is PSLVERR
    begin
      logic [31:0] rd; bit err;
      apb_rd(TX_LEFT, v);
      chk(v == 0, "TX_LEFT reads 0");
      apb_xfer(1, TX_LEFT, 32'h1234, 4'h1, rd, err);
      chk(err, "TX_LEFT with PSTRB 0001: PSLVERR");
    end

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end

  // one stereo frame as a continuous bit stream: WS changes at bit 0 of a
  // slot and each word's MSB follows one BCLK later, so with 16-bit slots a
  // word's LSB lands in the first bit of the next slot (carry). Returns the
  // SDOUT bits after each WS change: g[31] is the bit one BCLK after it.
  logic carry_in = 0;
  int setup_bad_h [8];
  task automatic send_frame(input int slot, input logic [15:0] l, input logic [15:0] r,
                            output logic [31:0] gl, output logic [31:0] gr, output logic t0);
    gl = 0; gr = 0;
    for (int t = 0; t < 2 * slot; t++) begin
      logic pre;
      int pl, pr;
      bclk = 0;
      lrck = t >= slot;
      pl = t - 1; pr = t - slot - 1;
      if (t == 0) sdin = carry_in;
      else if (pl >= 0 && pl < 16) sdin = l[15 - pl];
      else if (pr >= 0 && pr < 16) sdin = r[15 - pr];
      else sdin = 1'b0;
      repeat (half - 1) @(negedge PCLK);
      pre = sdout;
      @(negedge PCLK);
      bclk = 1;
      if (pre !== sdout) begin setup_bad++; setup_bad_h[half]++; end
      if (t == 0) t0 = sdout;
      if (pl >= 0 && pl < 32) gl[31 - pl] = sdout;
      if (pr >= 0 && pr < 32) gr[31 - pr] = sdout;
      repeat (half) @(negedge PCLK);
    end
    carry_in = slot == 16 ? r[0] : 1'b0;
  endtask

  initial begin #(50_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
