// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// uart_xchk_tb.sv -- UART_apb (open-ip-portfolio) through its documented
// register map (docs/ip/UART.md) against an 8N1 line model written from
// the asynchronous-serial rules, not from the RTL:
//   * the line receiver samples txd at bit centres of the nominal baud
//     (1e9 / BAUD ns) and times every edge against it (start bit 0, eight
//     data bits LSB first, stop bit 1, cumulative error under 2 %)
//   * the line driver sends frames at -2.5 .. +2.5 % of the nominal baud,
//     back to back, with framing errors, a break and a start-bit glitch
//   * the register contract: TXDATA_DONE / TXDATA_OVF, RXDATA pop,
//     RXDATA_AVAIL / RXDATA_OVF, CORE, W1C, irq = |(IRQ_STATUS & IRQ_ENABLE)
`ifndef SEED
`define SEED 1
`endif
module uart_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  localparam int CLK_FREQ = 50_000_000, BAUD = 115_200;
  localparam real TCLK = 20.0;                   // ns
  localparam real TBIT = 1.0e9 / BAUD;           // nominal bit time, ns
  localparam logic [31:0] ID_VALUE = 32'h55410200;
  localparam int N_WORDS = 7;
  localparam logic [11:0] IRQ_STATUS = 12'h004, IRQ_ENABLE = 12'h008, FLAGS = 12'h00C,
                          TXDATA = 12'h014, RXDATA = 12'h018;

  logic PCLK = 0, PRESETN = 0;
  logic PSEL = 0, PENABLE = 0, PWRITE = 0;
  logic [11:0] PADDR = 0;
  logic [31:0] PWDATA = 0;
  logic [3:0] PSTRB = 0;
  wire [31:0] PRDATA;
  wire PREADY, PSLVERR, irq, txd;
  logic rxd = 1;
  always #(TCLK / 2) PCLK = ~PCLK;

  UART_apb #(.CLK_FREQ(CLK_FREQ), .BAUD(BAUD)) dut (.PCLK, .PRESETN, .PSEL, .PENABLE, .PWRITE,
      .PADDR, .PWDATA, .PSTRB, .PRDATA, .PREADY, .PSLVERR, .irq, .rxd, .txd);

  `include "apb_bfm.svh"

  // ---------------- line receiver on txd (nominal baud) ----------------
  logic [7:0] tx_got [$];
  int tx_bad_frame = 0, tx_bad_timing = 0, tx_edges = 0;
  real tx_worst = 0.0;
  bit tx_mon_on = 0;
  initial begin
    forever begin
      real t0, te;
      logic [7:0] b;
      bit ok;
      @(negedge txd);
      if (tx_mon_on) begin
        t0 = $realtime;
        ok = 1;
        #(TBIT / 2);
        if (txd !== 1'b0) ok = 0;                        // start bit centre
        for (int i = 0; i < 8; i++) begin #(TBIT); b[i] = txd; end
        #(TBIT);
        if (txd !== 1'b1) ok = 0;                        // stop bit centre
        if (!ok) tx_bad_frame++;
        else tx_got.push_back(b);
      end
    end
  end
  // every txd edge inside a frame must sit within 2 % (cumulative) of k * TBIT
  real fr_t0 = -1.0;
  always @(txd) if (tx_mon_on && PRESETN) begin
    real dt, k, err;
    if (txd === 1'b0 && (fr_t0 < 0 || $realtime - fr_t0 > 9.6 * TBIT)) fr_t0 = $realtime;
    else if (fr_t0 >= 0) begin
      dt = $realtime - fr_t0;
      k = $floor(dt / TBIT + 0.5);
      err = (dt - k * TBIT);
      if (err < 0) err = -err;
      tx_edges++;
      if (k > 0 && err / (k * TBIT) > tx_worst) tx_worst = err / (k * TBIT);
      if (k > 0 && err > 0.02 * k * TBIT + TCLK) tx_bad_timing++;
    end
  end

  // ---------------- line driver on rxd ----------------
  task automatic send(input logic [7:0] b, input real ppm_err = 0.0, input bit stop = 1);
    real tb;
    tb = TBIT * (1.0 + ppm_err);
    rxd = 0; #(tb);
    for (int i = 0; i < 8; i++) begin rxd = b[i]; #(tb); end
    rxd = stop; #(tb);
    rxd = 1;
  endtask

  int core_irqs = 0;
  always @(posedge PCLK) if (dut.u_core.irq) core_irqs++;

  task automatic clear_irqs();
    apb_wr(IRQ_STATUS, 32'h1F);
  endtask

  logic [31:0] v, st;
  logic [7:0] sent [$];
  int seed = `SEED;
  initial begin
    void'($urandom(seed));
    repeat (5) @(posedge PCLK);
    PRESETN = 1;
    repeat (3) @(posedge PCLK);
    chk(txd === 1'b1, "txd idles high after reset");
    apb_common_checks();
    apb_rd(FLAGS, v);
    chk(v == 0, "FLAGS reset 0");
    apb_rd(RXDATA, v);
    chk(v == 0, "RXDATA reset 0");
    apb_wr(IRQ_ENABLE, 32'h1F);
    apb_rd(IRQ_ENABLE, v);
    chk(v == 32'h1F, "IRQ_ENABLE RW");
    clear_irqs();
    tx_mon_on = 1;

    // ---- transmit: 24 random bytes plus 0x00 / 0xFF / 0x55 / 0xAA, polled on FLAGS
    begin
      logic [7:0] b;
      for (int i = 0; i < 28; i++) begin
        b = i == 0 ? 8'h00 : i == 1 ? 8'hFF : i == 2 ? 8'h55 : i == 3 ? 8'hAA : 8'($urandom);
        do apb_rd(FLAGS, v); while (v[0]);
        apb_wr(TXDATA, {24'h0, b});
        sent.push_back(b);
      end
      #(22 * TBIT);
      chk(tx_got.size() == sent.size() && tx_bad_frame == 0,
          $sformatf("TX: %0d of %0d frames received at the nominal baud, %0d malformed",
                    tx_got.size(), sent.size(), tx_bad_frame));
      begin
        int bad = 0;
        foreach (sent[i]) if (i >= tx_got.size() || tx_got[i] != sent[i]) bad++;
        chk(bad == 0, $sformatf("TX: bytes LSB first, start 0 / stop 1 (%0d wrong)", bad));
      end
      chk(tx_bad_timing == 0 && tx_edges > 100,
          $sformatf("TX: every edge within 2 %% of the nominal bit grid (worst %0.2f %%, %0d edges)",
                    100.0 * tx_worst, tx_edges));
      apb_rd(IRQ_STATUS, st);
      chk(st[1] && !st[2], "TX: TXDATA_DONE set, no TXDATA_OVF when polled");
      chk(irq === 1'b1, "irq high with an enabled status bit");
      clear_irqs();
      @(posedge PCLK);
      chk(irq === 1'b0, "irq low after W1C");
    end

    // ---- TXDATA overflow: two writes back to back while the first is held
    begin
      tx_got.delete(); sent.delete();
      #(TBIT);
      apb_wr(TXDATA, 32'h3C);
      apb_wr(TXDATA, 32'hC3);
      apb_wr(TXDATA, 32'h99);
      apb_rd(IRQ_STATUS, st);
      #(25 * TBIT);
      chk(st[2], "TXDATA write while full sets TXDATA_OVF");
      chk(tx_got.size() == 2 && tx_got[0] == 8'h3C && tx_got[1] == 8'hC3,
          $sformatf("TX: the held byte and the next one go out, the dropped one does not (%0d frames: %h %h)",
                    tx_got.size(), tx_got.size() > 0 ? tx_got[0] : 8'h0, tx_got.size() > 1 ? tx_got[1] : 8'h0));
      clear_irqs();
    end

    // ---- receive at -2.5 .. +2.5 % of the nominal baud
    begin
      real e;
      int bad = 0;
      for (int k = 0; k < 5; k++) for (int i = 0; i < 6; i++) begin
        logic [7:0] b;
        e = k == 0 ? -0.025 : k == 1 ? -0.01 : k == 2 ? 0.0 : k == 3 ? 0.01 : 0.025;
        b = 8'($urandom);
        send(b, e);
        #(TBIT);
        apb_rd(FLAGS, v);
        if (!v[1]) bad++;
        apb_rd(RXDATA, v);
        if (v[7:0] != b) begin bad++; $display("  rx %h exp %h at %0.3f", v[7:0], b, e); end
        apb_rd(FLAGS, v);
        if (v[1]) bad++;
      end
      chk(bad == 0, $sformatf("RX: 30 frames at -2.5 .. +2.5 %% baud, FLAGS.RXDATA_AVAIL then pop (%0d errors)", bad));
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && st[3] && !st[4], "RX: CORE and RXDATA_AVAIL set, no RXDATA_OVF");
      clear_irqs();
    end

    // ---- back to back (no idle), 2 % fast
    begin
      logic [7:0] a, b;
      a = 8'h81; b = 8'h7E;
      send(a, 0.02);
      fork
        send(b, 0.02);
        begin
          // RXDATA is read while the second frame arrives
          #(3 * TBIT);
          apb_rd(RXDATA, v);
        end
      join
      #(TBIT);
      chk(v[7:0] == a, "RX back to back: first byte");
      apb_rd(RXDATA, v);
      chk(v[7:0] == b, "RX back to back: second byte");
      clear_irqs();
    end

    // ---- overflow: the second byte arrives before the first is read
    begin
      send(8'h11); #(TBIT);
      send(8'h22); #(TBIT);
      apb_rd(IRQ_STATUS, st);
      chk(st[4], "RX: byte arriving while RXDATA is full sets RXDATA_OVF");
      apb_rd(RXDATA, v);
      chk(v[7:0] == 8'h11, "RX overflow: RXDATA keeps the first byte");
      apb_rd(FLAGS, v);
      chk(!v[1], "RX overflow: nothing left after the pop");
      clear_irqs();
    end

    // ---- framing error, then recovery
    begin
      int c0;
      c0 = core_irqs;
      send(8'h5A, 0.0, 0);
      #(2 * TBIT);
      apb_rd(FLAGS, v);
      chk(!v[1], "RX framing error (stop bit 0): no byte delivered");
      chk(core_irqs == c0 + 1, "RX framing error: one CORE interrupt");
      apb_rd(IRQ_STATUS, st);
      chk(st[0] && !st[3], "RX framing error: CORE set, RXDATA_AVAIL not");
      clear_irqs();
      send(8'hA7); #(TBIT);
      apb_rd(RXDATA, v);
      chk(v[7:0] == 8'hA7, "RX recovers after a framing error");
    end

    // ---- break: line low for two frame times
    begin
      rxd = 0; #(20 * TBIT); rxd = 1; #(2 * TBIT);
      apb_rd(FLAGS, v);
      chk(!v[1], "RX break: no byte delivered");
      clear_irqs();
      send(8'h3E); #(TBIT);
      apb_rd(RXDATA, v);
      chk(v[7:0] == 8'h3E, "RX recovers after a break");
    end

    // ---- start-bit glitch shorter than half a bit
    begin
      int c0;
      clear_irqs();
      c0 = core_irqs;
      rxd = 0; #(0.3 * TBIT); rxd = 1; #(12 * TBIT);
      apb_rd(FLAGS, v);
      chk(!v[1] && core_irqs == c0, "RX: a 0.3-bit low pulse is not a start bit");
      send(8'hC6); #(TBIT);
      apb_rd(RXDATA, v);
      chk(v[7:0] == 8'hC6, "RX after the glitch");
    end

    // ---- loopback: txd into rxd at the IP's own baud
    begin
      int bad = 0;
      force rxd = txd;
      clear_irqs();
      for (int i = 0; i < 8; i++) begin
        logic [7:0] b;
        b = 8'($urandom);
        apb_wr(TXDATA, {24'h0, b});
        #(11 * TBIT);
        apb_rd(RXDATA, v);
        if (v[7:0] != b) bad++;
      end
      release rxd;
      chk(bad == 0, "loopback txd -> rxd: 8 bytes");
    end

    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(3e9); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
