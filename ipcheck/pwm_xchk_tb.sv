// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// pwm_xchk_tb.sv -- PWM_apb (open-ip-portfolio) through its documented
// register map (docs/ip/PWM.md). The expected waveform is computed here
// from the documented rule (period P clocks, output high for the first
// min(D, P) clocks of each period, PERIOD_END in the last clock, P = 0 holds
// the output low) and compared clock by clock over four periods:
//   * duty 0 %, 100 %, D > P, P = 1, P = 2, random P / D
//   * pwm_n_out the complement of pwm_out in every clock
//   * PERIOD / DUTY are write-only (read 0) and need a full-word write
module pwm_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam logic [31:0] ID_VALUE = 32'h50570200;
  localparam int N_WORDS = 7;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, PERIOD = 12'h014, DUTY = 12'h018;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq, pwm_out, pwm_n_out;
  always #5 PCLK = ~PCLK;

  PWM_apb dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE, .PADDR, .PWDATA, .PSTRB,
               .PRDATA, .PREADY, .PSLVERR, .irq, .pwm_out, .pwm_n_out);

  `include "apb_bfm.svh"

  int compl_bad = 0;
  always @(negedge PCLK) if (PRESETN && pwm_n_out !== ~pwm_out) compl_bad++;

  // four periods clock by clock, aligned on the PERIOD_END clock
  task automatic measure(input int p, input int d, output int bad);
    int t, hi;
    bad = 0;
    hi = d < p ? d : p;
    t = 0;
    while (!dut.u_core.irq && t < 4 * p + 10) begin @(negedge PCLK); t++; end
    if (!dut.u_core.irq) bad = 1000;
    else for (int k = 0; k < 4 * p; k++) begin
      int c;
      @(negedge PCLK);
      c = k % p;                                   // count within the period
      if (pwm_out !== (c < hi)) bad++;
      if (dut.u_core.irq !== (c == p - 1)) bad++;
    end
  endtask

  logic [31:0] v, st;
  bit err;
  initial begin
    int bad;
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    apb_common_checks();
    chk(pwm_out === 1'b0 && pwm_n_out === 1'b1, "after reset (PERIOD 0): pwm_out low, pwm_n_out high");

    begin
      int n = 0, nbad = 0;
      for (int i = 0; i < 16; i++) begin
        int p, d;
        case (i)
          0: begin p = 10; d = 3; end
          1: begin p = 10; d = 0; end
          2: begin p = 10; d = 10; end
          3: begin p = 10; d = 15; end
          4: begin p = 1; d = 1; end
          5: begin p = 1; d = 0; end
          6: begin p = 2; d = 1; end
          7: begin p = 100; d = 37; end
          default: begin p = $urandom_range(3, 60); d = $urandom_range(0, p + 4); end
        endcase
        apb_wr(PERIOD, p);
        apb_wr(DUTY, d);
        measure(p, d, bad);
        if (bad) begin nbad++; $display("  P %0d D %0d: %0d clocks wrong", p, d, bad); end
        n++;
      end
      chk(nbad == 0, $sformatf("16 PERIOD / DUTY settings, 4 periods each, clock by clock (%0d wrong)", nbad));
      chk(compl_bad == 0, "pwm_n_out is the complement of pwm_out in every clock");
    end

    // ---- PERIOD_END interrupt through the wrapper
    apb_wr(IRQ_STATUS, 32'h1);
    apb_wr(IRQ_ENABLE, 32'h1);
    apb_wr(PERIOD, 20);
    apb_wr(DUTY, 5);
    repeat (25) @(negedge PCLK);
    apb_rd(IRQ_STATUS, st);
    chk(st[0] && irq === 1'b1, "PERIOD_END set and irq high");

    // ---- PERIOD 0 stops: output low, no PERIOD_END
    begin
      int hi = 0, ends = 0;
      apb_wr(PERIOD, 0);
      apb_wr(IRQ_STATUS, 32'h1);
      repeat (50) begin @(negedge PCLK); hi += pwm_out; ends += dut.u_core.irq; end
      apb_rd(IRQ_STATUS, st);
      chk(hi == 0 && ends == 0 && st[0] == 0, "PERIOD 0: output held low, no PERIOD_END");
      chk(pwm_n_out === 1'b1, "PERIOD 0: pwm_n_out high");
    end

    // ---- write-only registers, full-word writes
    begin
      logic [31:0] rd;
      apb_rd(PERIOD, v);
      chk(v == 0, "PERIOD reads 0");
      apb_rd(DUTY, v);
      chk(v == 0, "DUTY reads 0");
      apb_xfer(1, PERIOD, 32'd8, 4'h1, rd, err);
      repeat (20) @(negedge PCLK);
      chk(err && pwm_out === 1'b0, "PERIOD with PSTRB 0001: PSLVERR, still stopped");
      apb_wr(PERIOD, 32'h0001_0000);                 // 65536: wide counter
      apb_wr(DUTY, 32'h0000_8000);
      repeat (40) @(negedge PCLK);
      chk(pwm_out === 1'b1, "32-bit PERIOD 65536 / DUTY 32768: high in the first half");
    end

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(10_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
