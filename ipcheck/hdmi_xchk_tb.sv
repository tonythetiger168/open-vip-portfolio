// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// hdmi_xchk_tb.sv -- HDMI_2_1_top (open-ip-portfolio) through an
// independent TMDS sink: the serial channels are framed on the clock
// channel, every 10-bit character is classified with xchk_ref_pkg (control
// tokens, guard bands, TERC4, DVI video decode) and checked:
//   * periods: 8-character preambles before video guard bands and data
//     islands, 2-character guard bands, nothing else in control periods
//   * CEA-861 VIC 1 timing from the decoded HSYNC/VSYNC and video periods:
//     800 x 525 total, hsync 96 / vsync 2 lines, 640 x 480 active,
//     back porch 48 + sync 96 before video, front porch 16
//   * the pixel source R = x, G = y, B = x ^ y in every active pixel
//   * DC balance of the video characters per channel and line
//   * data islands: header, subpackets and their BCH ECC and InfoFrame
//     checksum against pkt.hex (tools/run_ip_crosscheck.py)
//   * HPD loss: outputs quiet and irq
// The run covers one frame plus the start of the next (about 5 M clocks).
module hdmi_xchk_tb;
  import xchk_ref_pkg::*;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  logic clk = 0, rst_n = 0, hpd = 1;
  wire tmds_clk, hsync, vsync, de, irq;
  wire [2:0] tmds_d;
  always #5 clk = ~clk;

  HDMI_2_1_top dut (.clk, .rst_n, .hpd, .tmds_clk, .tmds_d, .hsync, .vsync, .de, .irq);

  logic [7:0] pkt [0:71];

  // ------------------------------------------------------------ framing
  logic [9:0] s0, s1, s2;
  logic cprev = 0;
  int bc = 0;
  bit run = 0;
  always @(posedge clk) if (rst_n && hpd && run) begin
    if (cprev && !tmds_clk) bc = 0; else bc++;
    cprev = tmds_clk;
    if (bc < 10) begin s0[bc] = tmds_d[0]; s1[bc] = tmds_d[1]; s2[bc] = tmds_d[2]; end
    if (bc == 9) character(s0, s1, s2);
  end

  // ------------------------------------------------------------ sink state
  typedef enum {P_CTRL, P_VGUARD, P_VIDEO, P_IGUARD, P_ISLAND, P_ITRAIL} per_t;
  per_t per = P_CTRL;
  int npix = 0;                 // characters since the start
  bit synced = 0;               // line numbers known (after the first VSYNC edge)
  int lines_in_frame = 0, nvideo_frame = -1;
  int vpre = 0, ipre = 0, ng = 0, x = 0, vline = -1, nvideo_lines = 0, nidx = 0, nisl = 0;
  int err_ctrl = 0, err_pre = 0, err_pix = 0, err_len = 0, err_isl = 0, max_disp = 0;
  int d0, d1, d2, c0, c1, c2, err_enc = 0;
  logic hs = 1, vs = 1, hs_p = 1, vs_p = 1;
  int hs_fall = -1, hs_rise = -1, vs_fall = -1, vs_rise = -1, vid_start = -1, vid_end = -1;
  int n_hper = 0, err_hper = 0, err_hsw = 0, n_vper = 0, err_vsw = 0, err_bp = 0, err_fp = 0, vper = 0;
  logic [31:0] hdr;
  logic [63:0] sp [0:3];

  function automatic int ones(input logic [9:0] q); return $countones(q); endfunction

  task automatic sync(input logic h, input logic v);
    hs = h; vs = v;
  endtask

  task automatic island_end();
    int b;
    bit ok;
    b = (hdr[7:0] == 8'h83) ? 36 : 0;
    ok = (hdr[7:0] == pkt[b]) && (hdr[15:8] == pkt[b + 1]) && (hdr[23:16] == pkt[b + 2]) && (hdr[31:24] == pkt[b + 3]);
    ok &= hdmi_bch({32'h0, hdr[23:0]}, 24) == hdr[31:24];
    for (int s = 0; s < 4; s++) begin
      for (int i = 0; i < 8; i++) ok &= sp[s][8 * i +: 8] == pkt[b + 4 + 8 * s + i];
      ok &= hdmi_bch(sp[s][55:0], 56) == sp[s][63:56];
    end
    begin
      logic [7:0] sum;
      sum = hdr[7:0] + hdr[15:8] + hdr[23:16];
      for (int i = 0; i < hdr[23:16] + 1 && i < 28; i++) sum += sp[i / 7][8 * (i % 7) +: 8];
      ok &= sum == 8'h00;
    end
    chk(ok, $sformatf("data island %0d (type %h): header, subpackets, BCH ECC and checksum", nisl, hdr[7:0]));
    nisl++;
  endtask

  task automatic character(input logic [9:0] a, input logic [9:0] b, input logic [9:0] c);
    logic [2:0] k0, k1, k2;
    logic [4:0] t0, t1, t2;
    k0 = tmds_ctl(a); k1 = tmds_ctl(b); k2 = tmds_ctl(c);
    t0 = terc4_dec(a); t1 = terc4_dec(b); t2 = terc4_dec(c);
    if (per == P_VIDEO && !(k0[2] && k1[2] && k2[2])) begin
      // active pixel
      logic [7:0] R, G, B;
      logic [17:0] e0, e1, e2;
      B = tmds_dec(a); G = tmds_dec(b); R = tmds_dec(c);
      // the exact character a DVI 1.0 encoder sends for the decoded value
      e0 = tmds_enc(B, c0); e1 = tmds_enc(G, c1); e2 = tmds_enc(R, c2);
      c0 = $signed(e0[17:10]); c1 = $signed(e1[17:10]); c2 = $signed(e2[17:10]);
      if (synced && (e0[9:0] !== a || e1[9:0] !== b || e2[9:0] !== c)) begin
        if (err_enc < 3) $display("  pixel (%0d,%0d): not the DVI 1.0 encoding", x, vline);
        err_enc++;
      end
      if (synced && (R !== x[7:0] || G !== vline[7:0] || B !== (x[7:0] ^ vline[7:0]))) begin
        if (err_pix < 3) $display("  pixel (%0d,%0d): RGB %h %h %h", x, vline, R, G, B);
        err_pix++;
      end
      d0 += ones(a) - 5; d1 += ones(b) - 5; d2 += ones(c) - 5;
      if (d0 > max_disp) max_disp = d0; if (-d0 > max_disp) max_disp = -d0;
      if (d1 > max_disp) max_disp = d1; if (-d1 > max_disp) max_disp = -d1;
      if (d2 > max_disp) max_disp = d2; if (-d2 > max_disp) max_disp = -d2;
      x++;
      hs = 1;
    end else if (per == P_VIDEO || per == P_CTRL) begin
      if (per == P_VIDEO) begin
        if (synced && x != 640) err_len++;
        vid_end = npix;
        per = P_CTRL;
      end
      if (k0[2] && k1[2] && k2[2]) begin
        sync(k0[0], k0[1]);
        if ({k2[1:0], k1[1:0]} == 4'b0001) begin vpre++; ipre = 0; end
        else if ({k2[1:0], k1[1:0]} == 4'b0101) begin ipre++; vpre = 0; end
        else begin vpre = 0; ipre = 0; end
      end else if (a == GB_VID_02 && b == GB_VID_1 && c == GB_VID_02) begin
        if (synced && vpre != 8) err_pre++;
        per = P_VGUARD; ng = 1; vpre = 0;
      end else if (b == GB_ISL_12 && c == GB_ISL_12 && t0[4] && t0[3:2] == 2'b11) begin
        if (synced && ipre != 8) err_pre++;
        sync(t0[0], t0[1]);
        per = P_IGUARD; ng = 1; ipre = 0;
      end else begin
        if (synced && err_ctrl < 3) $display("  character %0d: %b %b %b in a control period", npix, a, b, c);
        if (synced) err_ctrl++;
      end
    end else if (per == P_VGUARD) begin
      if (!(a == GB_VID_02 && b == GB_VID_1 && c == GB_VID_02)) err_pre++;
      per = P_VIDEO; x = 0; vline++; nvideo_lines++; d0 = 0; d1 = 0; d2 = 0; c0 = 0; c1 = 0; c2 = 0;
      vid_start = npix + 1;
      if (synced && vid_start - hs_fall != 144) err_bp++;
      if (synced && vid_end > vs_fall && hs_fall > vid_end && hs_fall - vid_end != 16) err_fp++;
    end else if (per == P_IGUARD) begin
      if (!(b == GB_ISL_12 && c == GB_ISL_12 && t0[4] && t0[3:2] == 2'b11)) err_isl++;
      sync(t0[0], t0[1]);
      per = P_ISLAND; nidx = 0; hdr = 0; sp[0] = 0; sp[1] = 0; sp[2] = 0; sp[3] = 0;
    end else if (per == P_ISLAND) begin
      if (synced && (!(t0[4] && t1[4] && t2[4]) || t0[3] != (nidx != 0))) err_isl++;
      sync(t0[0], t0[1]);
      hdr[nidx] = t0[2];
      for (int s = 0; s < 4; s++) begin sp[s][2 * nidx] = t1[s]; sp[s][2 * nidx + 1] = t2[s]; end
      nidx++;
      if (nidx == 32) begin per = P_ITRAIL; ng = 0; if (synced) island_end(); end
    end else begin                                   // trailing guard band
      if (!(b == GB_ISL_12 && c == GB_ISL_12 && t0[4] && t0[3:2] == 2'b11)) err_isl++;
      sync(t0[0], t0[1]);
      ng++;
      if (ng == 2) per = P_CTRL;
    end
    // sync edges (active low)
    if (hs_p && !hs) begin
      if (hs_fall >= 0 && synced) begin n_hper++; if (npix - hs_fall != 800) err_hper++; end
      hs_fall = npix;
    end
    if (!hs_p && hs) begin hs_rise = npix; if (synced && hs_rise - hs_fall != 96) err_hsw++; end
    if (vs_p && !vs) begin
      if (vs_fall >= 0) begin n_vper++; vper = npix - vs_fall; nvideo_frame = nvideo_lines; end
      vs_fall = npix; vline = -1;                // the next video period is line 0
      synced = 1; nvideo_lines = 0;
    end
    if (!vs_p && vs) begin vs_rise = npix; if (synced && vs_rise - vs_fall != 2 * 800) err_vsw++; end
    hs_p = hs; vs_p = vs;
    npix++;
  endtask

  initial begin
    $readmemh("pkt.hex", pkt);
    repeat (3) @(negedge clk);
    rst_n = 1;
    run = 1;
    // acquire on the first VSYNC, then one full frame and the next SPD island
    wait (n_vper == 1);
    repeat (1000 * 10) @(posedge clk);
    run = 0;
    chk(err_ctrl == 0, $sformatf("control periods carry only control tokens, preambles and guard bands (%0d bad)", err_ctrl));
    chk(err_pre == 0, $sformatf("8-character preamble before every guard band, 2 guard characters (%0d bad)", err_pre));
    chk(err_len == 0, $sformatf("every video period is 640 pixels (%0d bad)", err_len));
    chk(err_pix == 0, $sformatf("decoded pixels are R=x G=y B=x^y (%0d bad)", err_pix));
    chk(err_enc == 0, $sformatf("every video character is the DVI 1.0 encoding of its value (%0d bad)", err_enc));
    chk(max_disp <= 20, $sformatf("video characters DC balanced within a line (max |disparity| %0d bits/2)", max_disp));
    chk(n_hper > 500 && err_hper == 0, $sformatf("hsync period 800 characters (%0d of %0d bad)", err_hper, n_hper));
    chk(err_hsw == 0, $sformatf("hsync width 96 (%0d bad)", err_hsw));
    chk(err_bp == 0, $sformatf("video starts 144 characters after the hsync edge (%0d bad)", err_bp));
    chk(err_fp == 0, $sformatf("front porch 16 characters (%0d bad)", err_fp));
    chk(vper == 525 * 800, $sformatf("vsync period 525 lines (%0d characters)", vper));
    chk(err_vsw == 0, "vsync width 2 lines");
    chk(nisl >= 3 && err_isl == 0, $sformatf("data islands well formed (%0d islands, %0d bad characters)", nisl, err_isl));
    chk(nvideo_frame == 480, $sformatf("480 active lines per frame (%0d)", nvideo_frame));
    // HPD loss
    @(negedge clk); hpd = 0;
    repeat (5) @(negedge clk);
    begin
      int q;
      q = 0;
      repeat (40) begin @(negedge clk); if (tmds_d !== 3'b000 || tmds_clk !== 1'b0) q++; end
      chk(q == 0 && irq === 1'b1, "HPD low: TMDS outputs quiet, irq set");
    end
    if (fails == 0) $display("XCHK_PASS checks=%0d", checks);
    else            $display("XCHK_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
endmodule
