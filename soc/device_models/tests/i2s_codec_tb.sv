// SPDX-License-Identifier: Apache-2.0
// i2s_codec_model against I2S_top (open-ip-portfolio, the slave).
// A: 32-bit slots, bclk = clk / 8. B: 16-bit slots (the LSB spills into the
// next slot's first bit), bclk = clk / 12.
module i2s_codec_tb;
  logic clk = 1'b0, rst_n = 1'b0;
  always #5 clk = ~clk;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask
  function automatic logic [15:0] adc(input int n, input bit ch);
    logic [31:0] x = (32'(n) * 32'h0001_0123) ^ (ch ? 32'h0000_A55A : 32'h0000_3C3C);
    return x[15:0];
  endfunction

  `define PAIR(N, SL, DV, FR) \
    logic bclk_``N, lrck_``N, sdin_``N, sdout_``N, dv_``N, dn_``N, wen_``N = 0, irq_``N; \
    logic [3:0] wa_``N = 0, ra_``N = 0; logic [15:0] wd_``N = 0, rdat_``N, dl_``N, dr_``N; logic [31:0] df_``N; \
    i2s_codec_model #(.SLOT(SL), .DIV(DV), .FRAMES(FR)) u_cod_``N (.clk(clk), .rst_n(rst_n), .en(1'b1), \
      .bclk(bclk_``N), .lrck(lrck_``N), .sdin(sdin_``N), .sdout(sdout_``N), .dac_valid(dv_``N), \
      .dac_left(dl_``N), .dac_right(dr_``N), .dac_frame(df_``N), .done(dn_``N)); \
    I2S_top u_i2s_``N (.clk(clk), .rst_n(rst_n), .bclk(bclk_``N), .lrck(lrck_``N), .sdin(sdin_``N), \
      .sdout(sdout_``N), .wen(wen_``N), .waddr(wa_``N), .wdata(wd_``N), .ren(1'b1), .raddr(ra_``N), \
      .rdata(rdat_``N), .irq(irq_``N)); \
    logic [15:0] gl_``N [int], gr_``N [int]; \
    always @(posedge clk) if (dv_``N) begin gl_``N[df_``N] = dl_``N; gr_``N[df_``N] = dr_``N; end
  `PAIR(a, 32, 8, 8)
  `PAIR(b, 16, 12, 8)

  task automatic wr(input bit b, input logic [3:0] a, input logic [15:0] d);
    @(negedge clk);
    if (!b) begin wen_a = 1; wa_a = a; wd_a = d; end else begin wen_b = 1; wa_b = a; wd_b = d; end
    @(negedge clk); wen_a = 0; wen_b = 0;
  endtask
  // rx words seen by the slave, sampled when each frame's right word is in
  logic [15:0] sl_a [int], sr_a [int], sl_b [int], sr_b [int];
  bit ok;
  initial begin
    repeat (3) @(posedge clk);
    rst_n = 1'b1;     // the codecs start bclk 1 clk later; frame 0 is sent before these land
    wr(0, 0, 16'hA1B2); wr(0, 1, 16'hC3D4); wr(1, 0, 16'h1357); wr(1, 1, 16'h2468);
    fork                                   // during frame 4 the next words change
      begin wait (u_cod_a.gc == 4 * 64); wr(0, 0, 16'h0F0F); wr(0, 1, 16'hF00F); end
      begin wait (u_cod_b.gc == 4 * 32); wr(1, 0, 16'h5AA5); wr(1, 1, 16'hFFFF); end
    join
    wait (dn_a && dn_b); repeat (40) @(posedge clk);
    ok = 1;
    for (int n = 1; n < 4; n++) if (!gl_a.exists(n) || gl_a[n] != 16'hA1B2 || gr_a[n] != 16'hC3D4) ok = 0;
    chk(ok, "A: DAC frames 1..3 carry the written words");
    chk(gl_a.exists(7) && gl_a[7] == 16'h0F0F && gr_a[7] == 16'hF00F, "A: new words reach the DAC");
    ok = 1;
    for (int n = 1; n < 4; n++) if (!gl_b.exists(n) || gl_b[n] != 16'h1357 || gr_b[n] != 16'h2468) ok = 0;
    chk(ok, "B: DAC frames 1..3 with 16-bit slots");
    chk(gl_b.exists(7) && gl_b[7] == 16'h5AA5 && gr_b[7] == 16'hFFFF, "B: new words reach the DAC");
    chk(gl_a.size() == 8 && gl_b.size() == 8, "8 DAC frames each");
    ra_a = 0; ra_b = 0; #1;
    chk(rdat_a == adc(7, 0) && rdat_b == adc(7, 0), "slave rx_left = the ADC left word of frame 7");
    ra_a = 1; ra_b = 1; #1;
    chk(rdat_a == adc(7, 1) && rdat_b == adc(7, 1), "slave rx_right = the ADC right word of frame 7");
    chk(sl_a.size() >= 6, "slave took every ADC frame (A)");
    ok = 1;
    foreach (sl_a[n]) if (sl_a[n] != adc(n, 0) || sr_a[n] != adc(n, 1)) ok = 0;
    foreach (sl_b[n]) if (sl_b[n] != adc(n, 0) || sr_b[n] != adc(n, 1)) ok = 0;
    chk(ok && sl_b.size() >= 6, "slave rx words match the ADC pattern frame by frame");
    chk(bclk_a && bclk_b, "bclk stops high after the last frame");
    if (fails == 0) $display("FUNC_PASS i2s_codec checks=%0d", checks);
    else            $display("FUNC_FAIL i2s_codec checks=%0d fails=%0d", checks, fails);
    $finish;
  end
  // sample the slave's rx registers one bclk period into each new frame (both words of the last frame are in)
  always @(posedge clk) begin
    if (rst_n && u_cod_a.gc % 64 == 1 && u_cod_a.ph == 7 && u_cod_a.gc > 64) begin
      sl_a[u_cod_a.gc / 64 - 1] = u_i2s_a.rx_left; sr_a[u_cod_a.gc / 64 - 1] = u_i2s_a.rx_right; end
    if (rst_n && u_cod_b.gc % 32 == 1 && u_cod_b.ph == 11 && u_cod_b.gc > 32) begin
      sl_b[u_cod_b.gc / 32 - 1] = u_i2s_b.rx_left; sr_b[u_cod_b.gc / 32 - 1] = u_i2s_b.rx_right; end
  end
  initial begin #2ms; $display("FUNC_FAIL i2s_codec timeout"); $finish; end
endmodule
