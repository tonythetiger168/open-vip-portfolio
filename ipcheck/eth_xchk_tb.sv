// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// eth_xchk_tb.sv -- Ethernet_top (open-ip-portfolio) against IEEE 802.3
// frames built by tools/run_ip_crosscheck.py (FCS from zlib.crc32):
//   transmit  tx_in.hex host frames -> tx_exp.hex wire bytes (preamble, SFD,
//             padding to 60 bytes, FCS LSB first), >= 12 idle byte times
//   receive   rx_stim.hex wire bytes -> rx_exp.hex host bytes and
//             rx_rec.hex {accepted, rx_stat, len} per frame
//   PAUSE     the last received frame is a PAUSE with PAUSE_Q quanta
// One byte per clock (cfg_div = 0).
`ifndef NTX
`define NTX 1
`endif
`ifndef NRX
`define NRX 1
`endif
`ifndef PAUSE_Q
`define PAUSE_Q 1
`endif
module eth_xchk_tb;
  import xchk_ref_pkg::*;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  logic clk = 0, rst_n = 0;
  logic [47:0] cfg_mac = 48'h020000A1B2C3;
  logic cfg_promisc = 0, cfg_pause_en = 1;
  logic tx_valid = 0, tx_last = 0;
  logic [7:0] tx_data = 0;
  wire tx_ready, tx_done, tx_underrun, tx_paused;
  wire [7:0] gtxd;
  wire gtx_en, gtx_er;
  logic [7:0] grxd = 0;
  logic grx_dv = 0, grx_er = 0;
  wire rx_valid, rx_last, rx_frag;
  wire [7:0] rx_data;
  wire [3:0] rx_stat;
  always #5 clk = ~clk;

  Ethernet_top dut (.clk, .rst_n, .cfg_div(5'd0), .cfg_mac, .cfg_promisc, .cfg_pause_en,
                    .tx_valid, .tx_ready, .tx_data, .tx_last, .tx_done, .tx_underrun, .tx_paused,
                    .gtxd, .gtx_en, .gtx_er, .grxd, .grx_dv, .grx_er,
                    .rx_valid, .rx_data, .rx_last, .rx_stat, .rx_frag);

  logic [7:0] tx_in  [0:65535];
  logic [7:0] tx_exp [0:65535];
  logic [7:0] tx_rec [0:4 * `NTX - 1];
  logic [11:0] rx_stim [0:65535];
  logic [7:0] rx_exp [0:65535];
  logic [7:0] rx_rec [0:4 * `NRX - 1];

  // ---------------- wire monitor: one queue entry per byte while gtx_en
  logic [8:0] wq [$];                 // {gtx_er, gtxd}
  int idle_run = 100, min_gap = 100, ndone = 0, nunder = 0, nframes = 0;
  always @(posedge clk) begin
    if (gtx_en) begin
      if (idle_run > 0 && idle_run < 100 && nframes > 0 && idle_run < min_gap) min_gap = idle_run;
      if (idle_run > 0) nframes++;
      idle_run = 0;
      wq.push_back({gtx_er, gtxd});
    end else if (idle_run < 100) idle_run++;
    if (tx_done) ndone++;
    if (tx_underrun) nunder++;
  end
  // ---------------- host receive monitor
  logic [7:0] rq [$];
  logic [3:0] last_stat;
  int nlast = 0, nfrag = 0;
  always @(posedge clk) begin
    if (rx_valid) rq.push_back(rx_data);
    if (rx_valid && rx_last) begin nlast++; last_stat = rx_stat; end
    if (rx_frag) nfrag++;
  end

  // host transmit side: the byte for the next tx_ready is always presented
  int tp = 0, tend = 0;
  always @(posedge clk) if (tx_ready && tx_valid) tp <= tp + 1;
  always @* begin
    tx_data = tx_in[tp];
    tx_last = (tp == tend - 1);
    tx_valid = (tp < tend);
  end

  initial begin
    int ep, n0, flen, wlen, bad, rp, xp, fr, acc, plen;
    logic [8:0] lastw;
    ep = 0;
    $readmemh("tx_in.hex", tx_in);
    $readmemh("tx_exp.hex", tx_exp);
    $readmemh("tx_rec.hex", tx_rec);
    $readmemh("rx_stim.hex", rx_stim);
    $readmemh("rx_exp.hex", rx_exp);
    $readmemh("rx_rec.hex", rx_rec);
    repeat (3) @(negedge clk);
    rst_n = 1;
    repeat (3) @(negedge clk);

    // ---------------- transmit
    for (int f = 0; f < `NTX; f++) begin
      flen = {tx_rec[4 * f], tx_rec[4 * f + 1]};
      wlen = {tx_rec[4 * f + 2], tx_rec[4 * f + 3]};
      n0 = ndone;
      wq.delete();
      @(negedge clk); tend = tp + flen;
      while (ndone == n0) @(negedge clk);
      repeat (14) @(negedge clk);
      bad = 0;
      for (int i = 0; i < wlen; i++) if (i >= wq.size() || wq[i] !== {1'b0, tx_exp[ep + i]}) bad++;
      chk(bad == 0 && wq.size() == wlen,
          $sformatf("TX frame %0d (%0d bytes): wire matches 802.3 encoding (%0d bad, %0d/%0d bytes)",
                    f, flen, bad, wq.size(), wlen));
      ep += wlen;
    end
    chk(min_gap >= 12, $sformatf("inter-frame gap >= 12 byte times (min %0d)", min_gap));
    // underrun: the host stops after 20 bytes
    n0 = nunder;
    wq.delete();
    @(negedge clk); tend = tp + 1000;
    repeat (8 + 20) @(posedge clk);
    @(negedge clk); tend = tp;
    repeat (30) @(negedge clk);
    chk(nunder == n0 + 1, "underrun pulses tx_underrun");
    lastw = wq.size() ? wq[wq.size() - 1] : 9'h0;
    chk(lastw[8] === 1'b1, "underrun ends the frame with gtx_er");

    // ---------------- receive
    rp = 0; xp = 0; fr = 0;
    while (rx_stim[rp] !== 12'h7FF) begin
      if (rx_stim[rp] == 12'h400) begin
        acc = rx_rec[4 * fr];
        plen = {rx_rec[4 * fr + 2], rx_rec[4 * fr + 3]};
        if (acc) begin
          bad = 0;
          for (int i = 0; i < plen; i++) if (i >= rq.size() || rq[i] !== rx_exp[xp + i]) bad++;
          chk(bad == 0 && rq.size() == plen && nlast == 1,
              $sformatf("RX frame %0d: %0d bytes delivered without FCS (%0d bad, got %0d)", fr, plen, bad, rq.size()));
          chk(last_stat === rx_rec[4 * fr + 1][3:0],
              $sformatf("RX frame %0d: rx_stat %b, expected %b", fr, last_stat, rx_rec[4 * fr + 1][3:0]));
          xp += plen;
        end else
          chk(rq.size() == 0 && nlast == 0, $sformatf("RX frame %0d: not delivered", fr));
        rq.delete(); nlast = 0; fr++;
      end else begin
        @(negedge clk);
        grx_dv = rx_stim[rp][8]; grx_er = rx_stim[rp][9]; grxd = rx_stim[rp][7:0];
      end
      rp++;
    end
    @(negedge clk); grx_dv = 0; grx_er = 0;
    chk(fr == `NRX, "all receive checkpoints reached");
    chk(nfrag >= 1, "bad preamble reported as rx_frag");

    // ---------------- PAUSE: the last frame paused the transmitter
    begin
      int np, t0;
      np = 0;
      while (tx_paused) begin @(negedge clk); np++; end
      // the PAUSE was accepted at the end of the frame, about 16 byte times ago
      chk(np > 0 && np <= `PAUSE_Q * 64 && np >= `PAUSE_Q * 64 - 24,
          $sformatf("PAUSE holds the transmitter for quanta x 64 byte times (%0d left)", np));
    end
    if (fails == 0) $display("XCHK_PASS checks=%0d", checks);
    else            $display("XCHK_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
  initial begin #20000000; $display("XCHK_FAIL timeout"); $finish; end
endmodule
