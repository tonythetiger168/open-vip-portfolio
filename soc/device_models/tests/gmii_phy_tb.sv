// SPDX-License-Identifier: Apache-2.0
// gmii_phy_model against Ethernet_top (open-ip-portfolio).
// A: byte time 2 clocks, two originated frames, then a SoC frame echoed back.
// B: byte time 5 clocks, two SoC frames back to back: the first is echoed,
//    the second arrives while the echo is going out and is dropped.
module gmii_phy_tb;
  logic clk = 1'b0, rst_n = 1'b0;
  always #4 clk = ~clk;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask
  localparam logic [47:0] SOC = 48'h02_00_5E_10_00_01, PHY = 48'h02_00_5E_10_00_99;

  // one MAC + PHY pair
  `define PAIR(N, D, G) \
    logic tv_``N = 0, tr_``N, tl_``N = 0, td_``N, tu_``N, tp_``N; logic [7:0] tx_``N = 0; \
    logic [7:0] gtxd_``N, grxd_``N; logic gtxen_``N, gtxer_``N, grxdv_``N, grxer_``N; \
    logic rv_``N, rl_``N, rf_``N; logic [7:0] rd_``N; logic [3:0] rs_``N; \
    logic [15:0] good_``N, bad_``N, txf_``N, drop_``N; \
    Ethernet_top u_mac_``N (.clk(clk), .rst_n(rst_n), .cfg_div(5'(D)), .cfg_mac(SOC), .cfg_promisc(1'b0), \
      .cfg_pause_en(1'b1), .tx_valid(tv_``N), .tx_ready(tr_``N), .tx_data(tx_``N), .tx_last(tl_``N), \
      .tx_done(td_``N), .tx_underrun(tu_``N), .tx_paused(tp_``N), .gtxd(gtxd_``N), .gtx_en(gtxen_``N), \
      .gtx_er(gtxer_``N), .grxd(grxd_``N), .grx_dv(grxdv_``N), .grx_er(grxer_``N), .rx_valid(rv_``N), \
      .rx_data(rd_``N), .rx_last(rl_``N), .rx_stat(rs_``N), .rx_frag(rf_``N)); \
    gmii_phy_model #(.DIV(D), .GEN_N(G), .GEN_LEN(50), .PHY_MAC(PHY), .DST_MAC(SOC)) u_phy_``N ( \
      .clk(clk), .rst_n(rst_n), .gtxd(gtxd_``N), .gtx_en(gtxen_``N), .gtx_er(gtxer_``N), .grxd(grxd_``N), \
      .grx_dv(grxdv_``N), .grx_er(grxer_``N), .rx_good(good_``N), .rx_bad(bad_``N), .tx_frames(txf_``N), \
      .echo_drop(drop_``N)); \
    byte unsigned cur_``N [$]; byte unsigned fr_``N [$][$]; logic [3:0] st_``N [$]; \
    always @(posedge clk) if (rv_``N) begin \
      cur_``N.push_back(rd_``N); \
      if (rl_``N) begin fr_``N.push_back(cur_``N); st_``N.push_back(rs_``N); cur_``N.delete(); end \
    end
  `PAIR(a, 1, 2)
  `PAIR(b, 4, 0)

  // a SoC frame to the PHY: DA = PHY, SA = SOC, type 0x0800, n payload bytes
  function automatic void soc_frame(ref byte unsigned f [$], input int n, input int seed);
    f.delete();
    for (int i = 0; i < 6; i++) f.push_back(PHY[8 * (5 - i) +: 8]);
    for (int i = 0; i < 6; i++) f.push_back(SOC[8 * (5 - i) +: 8]);
    f.push_back(8'h08); f.push_back(8'h00);
    for (int i = 0; i < n; i++) f.push_back(8'(i * 7 + seed));
  endfunction
  // the echo: DA and SA swapped
  function automatic void swapped(ref byte unsigned f [$], ref byte unsigned e [$]);
    e = f;
    for (int i = 0; i < 6; i++) begin e[i] = f[i + 6]; e[i + 6] = f[i]; end
  endfunction
  task automatic send_a(ref byte unsigned f [$]);
    foreach (f[i]) begin
      tv_a = 1; tx_a = f[i]; tl_a = (i == f.size() - 1);
      do @(posedge clk); while (!tr_a);
      #1;
    end
    tv_a = 0; tl_a = 0;
  endtask
  task automatic send_b(ref byte unsigned f [$]);
    foreach (f[i]) begin
      tv_b = 1; tx_b = f[i]; tl_b = (i == f.size() - 1);
      do @(posedge clk); while (!tr_b);
      #1;
    end
    tv_b = 0; tl_b = 0;
  endtask
  function automatic bit same(ref byte unsigned x [$], ref byte unsigned y [$]);
    if (x.size() != y.size()) return 0;
    foreach (x[i]) if (x[i] != y[i]) return 0;
    return 1;
  endfunction

  byte unsigned f1 [$], f2 [$], e [$], g [$];
  bit ok;
  initial begin
    repeat (3) @(posedge clk); rst_n = 1'b1;
    // A: the two originated frames reach the SoC
    wait (fr_a.size() == 2);
    ok = 1;
    for (int k = 0; k < 2; k++) begin
      g.delete();
      for (int i = 0; i < 6; i++) g.push_back(SOC[8 * (5 - i) +: 8]);
      for (int i = 0; i < 6; i++) g.push_back(PHY[8 * (5 - i) +: 8]);
      g.push_back(8'h00); g.push_back(8'd50);
      for (int i = 0; i < 50; i++) g.push_back(8'(i) ^ 8'(k * 29));
      if (!same(fr_a[k], g) || st_a[k] != 4'h0) ok = 0;
    end
    chk(ok, "A: two originated frames received by the MAC, good FCS");
    // A: a SoC frame is echoed back
    soc_frame(f1, 100, 3);
    send_a(f1);
    wait (fr_a.size() == 3);
    swapped(f1, e);
    chk(same(fr_a[2], e) && st_a[2] == 4'h0, "A: SoC frame echoed with DA / SA swapped");
    chk(good_a == 16'd1 && bad_a == 16'd0 && txf_a == 16'd3 && drop_a == 16'd0, "A: PHY counters");
    // A: a short SoC frame comes back padded to 60 bytes by the MAC
    soc_frame(f2, 10, 9);
    send_a(f2);
    wait (fr_a.size() == 4);
    swapped(f2, e); while (e.size() < 60) e.push_back(8'h00);
    chk(same(fr_a[3], e) && st_a[3] == 4'h0, "A: short frame echoed with the MAC's padding");
    // B: back to back, the second is dropped
    soc_frame(f1, 200, 1); soc_frame(f2, 64, 5);
    send_b(f1); send_b(f2);
    wait (fr_b.size() == 1);
    repeat (5000) @(posedge clk);
    swapped(f1, e);
    chk(fr_b.size() == 1 && same(fr_b[0], e) && st_b[0] == 4'h0, "B: first frame echoed at 5-clock byte time");
    chk(good_b == 16'd2 && drop_b == 16'd1 && txf_b == 16'd1, "B: second frame dropped while the echo was busy");
    // B: after the echo, the next frame is echoed again
    soc_frame(f2, 64, 11);
    send_b(f2);
    wait (fr_b.size() == 2);
    swapped(f2, e);
    chk(same(fr_b[1], e) && st_b[1] == 4'h0, "B: next frame echoed");
    if (fails == 0) $display("FUNC_PASS gmii_phy checks=%0d", checks);
    else            $display("FUNC_FAIL gmii_phy checks=%0d fails=%0d", checks, fails);
    $finish;
  end
  initial begin #20ms; $display("FUNC_FAIL gmii_phy timeout"); $finish; end
endmodule
