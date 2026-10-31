// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// ddr_xchk_tb.sv -- DDR4_Lite_top, or LPDDR5X_Lite_top with +define+LPDDR
// (open-ip-portfolio), driven through the documented front-end
// (docs/ip/DDR4_Lite.md, docs/ip/LPDDR5X_Lite.md) and observed on the DRAM
// pins by ddr_pin_mon (JESD79-4 command truth table and timing rules):
//   * random READ / WRITE line traffic over every bank, rows chosen to give
//     page hits, misses and conflicts, manual and automatic refresh; the
//     front-end read data is checked against a reference memory kept here
//     by host address, the pin bursts against the monitor's shadow array
//   * latency: read data CL and write data CWL clocks after the command at
//     the reset MR values; MR writes, MR0 bit 7 self-clearing, a raised CL
//     field moves the read data later and the data stays right
//   * refresh: every bank refreshed within the documented interval (and
//     within the JEDEC limit of nine intervals), manual REFRESH adds one
//   * rejected commands and out-of-range addresses: hdone next clock and the
//     sticky irq, which stays low through all legal traffic
//   * LPDDR: per-bank REF, REFRESH one bank, the two FSP MR sets, WCK
`ifndef SEED
`define SEED 1
`endif
`ifndef NOPS
`define NOPS 600
`endif
module ddr_xchk_tb;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

`ifdef LPDDR
  localparam int NB = 8, BW = 3, ROWLO = 10;
`else
  localparam int NB = 4, BW = 2, ROWLO = 9;
`endif
  localparam int T_RCD = 6, T_RP = 6, T_RC = 24, T_RAS = 16, T_RRD = 3, T_WR = 8, T_WTR = 4,
                 T_RFC = 40, T_RFC_PB = 20, T_REFI = 1000, CL = 11, CWL = 8;

  logic clk = 0, rst_n = 0;
  always #5 clk = ~clk;
  logic hvalid = 0;
  logic [2:0] hcmd = 0;
  logic [31:0] haddr = 0;
  logic [15:0] hwdata = 0;
  wire hready, hdone, irq;
  wire [15:0] hrdata;
  wire [127:0] rdline;
  wire ck_t, ck_c, cke, cs_n, act_n, ras_n, cas_n, we_n;
  wire [BW-1:0] ba;
  wire [13:0] addr;
  wire [15:0] dq;
  wire [1:0] dqs;
  wire trace_valid;
  wire [31:0] trace_addr;

`ifdef LPDDR
  wire fsp, wck_t, wck_c;
  wire [3:0] trace_cmd;
  LPDDR5X_Lite_top #(.T_RCD(T_RCD), .T_RP(T_RP), .T_RC(T_RC), .T_RAS(T_RAS), .T_RRD(T_RRD),
      .T_WR(T_WR), .T_WTR(T_WTR), .T_RFC(T_RFC), .T_RFC_PB(T_RFC_PB), .T_REFI(T_REFI), .CL(CL), .CWL(CWL))
    dut (.clk, .rst_n, .hvalid, .hready, .hcmd, .haddr, .hwdata, .hrdata, .rdline, .hdone, .irq, .fsp,
         .ck_t, .ck_c, .cke, .wck_t, .wck_c, .cs_n, .act_n, .ras_n, .cas_n, .we_n, .ba, .addr, .dq, .dqs,
         .trace_valid, .trace_cmd, .trace_addr);
`else
  wire [2:0] trace_cmd;
  DDR4_Lite_top #(.T_RCD(T_RCD), .T_RP(T_RP), .T_RC(T_RC), .T_RAS(T_RAS), .T_RRD(T_RRD),
      .T_WR(T_WR), .T_WTR(T_WTR), .T_RFC(T_RFC), .T_REFI(T_REFI), .CL(CL), .CWL(CWL))
    dut (.clk, .rst_n, .hvalid, .hready, .hcmd, .haddr, .hwdata, .hrdata, .rdline, .hdone, .irq,
         .ck_t, .ck_c, .cke, .cs_n, .act_n, .ras_n, .cas_n, .we_n, .ba, .addr, .dq, .dqs,
         .trace_valid, .trace_cmd, .trace_addr);
`endif

  ddr_pin_mon #(.NB(NB), .T_RCD(T_RCD), .T_RP(T_RP), .T_RC(T_RC), .T_RAS(T_RAS), .T_RRD(T_RRD),
      .T_WR(T_WR), .T_WTR(T_WTR), .T_RFC(T_RFC), .T_RFC_PB(T_RFC_PB),
`ifdef LPDDR
      .PB_REF(1)
`else
      .PB_REF(0)
`endif
    ) mon (.clk(ck_t), .rst_n, .cs_n, .act_n, .ras_n, .cas_n, .we_n, .ba(3'(ba)), .addr, .dq, .dqs);

  // ---------------- front-end ----------------
  logic [15:0] hist [8];
  int irq_rise = 0;
  logic irq_d = 0;
  always @(posedge clk) begin
    #1;
    for (int i = 0; i < 7; i++) hist[i] = hist[i + 1];
    hist[7] = hrdata;
    if (irq && !irq_d) irq_rise++;
    irq_d = irq;
  end
  function automatic logic [31:0] ha(input int b, input int r, input int l);
    return (32'(r) << ROWLO) | (32'(b) << 7) | (32'(l) << 4);
  endfunction
  // one front-end command; returns the 8 read beats (or the MRR value in rd[7])
  task automatic op(input logic [2:0] c, input logic [31:0] a, input logic [127:0] wl,
                    output logic [127:0] rl, output int lat_done);
    int t0;
    @(negedge clk);
    hvalid = 1; hcmd = c; haddr = a; hwdata = wl[15:0];
    while (!hready) @(negedge clk);
    @(negedge clk);                                  // taken at the edge before
    t0 = mon.cyc;
    if (c == 3'd2) for (int i = 0; i < 8; i++) begin
      hwdata = wl[16 * i +: 16];
      @(negedge clk);
    end
    hvalid = 0; hcmd = 0;
    while (!hdone) @(negedge clk);
    lat_done = mon.cyc - t0;
    rl = {hist[7], hist[6], hist[5], hist[4], hist[3], hist[2], hist[1], hist[0]};
  endtask

  logic [127:0] refm [0:32767];            // host line haddr[18:4]
  initial for (int i = 0; i < 32768; i++) refm[i] = '0;
  int rd_bad = 0, nops = 0;
  task automatic wr_line(input int b, input int r, input int l, input logic [127:0] d);
    logic [127:0] x; int t;
    op(3'd2, ha(b, r, l), d, x, t);
    refm[ha(b, r, l) >> 4] = d;
  endtask
  task automatic rd_line(input int b, input int r, input int l);
    logic [127:0] x, e; int t;
    op(3'd1, ha(b, r, l), '0, x, t);
    e = refm[ha(b, r, l) >> 4];
    if (x !== e || rdline !== e) begin
      rd_bad++;
      if (rd_bad <= 5) $display("  read b%0d r%0d l%0d: %h, expected %h", b, r, l, x, e);
    end
    nops++;
  endtask
  function automatic logic [127:0] rnd128();
    return {$urandom, $urandom, $urandom, $urandom};
  endfunction
  task automatic mrw(input int i, input logic [7:0] v);
    logic [127:0] x; int t;
    op(3'd3, 32'(i), {120'h0, v}, x, t);
  endtask
  task automatic mrr(input int i, output logic [7:0] v);
    logic [127:0] x; int t;
    op(3'd4, 32'(i), '0, x, t);
    v = x[119:112];                      // hrdata in the hdone clock
  endtask

  // random traffic over every bank; rows from a small set for hits / conflicts
  task automatic traffic(input int n);
    for (int i = 0; i < n; i++) begin
      int b, r, l;
      b = $urandom_range(NB - 1);
      r = $urandom_range(3);
      if (r == 3) r = $urandom_range(511);
      l = $urandom_range(7);
      if ($urandom_range(1)) wr_line(b, r, l, rnd128());
      else rd_line(b, r, l);
    end
  endtask

`ifdef LPDDR
  int wck_bad = 0;
  always @(negedge clk) if (rst_n) begin
    if (wck_c !== ~wck_t) wck_bad++;
    if (mon.win_kind == 2 && wck_t !== 1'b1) wck_bad++;           // rests high during reads
  end
  logic wck_prev;
  always @(negedge clk) begin
    if (rst_n && mon.win_kind == 1 && wck_t === wck_prev) wck_bad++; // toggles every write beat
    wck_prev = wck_t;
  end
`endif

  int seed = `SEED;
  initial begin
    logic [7:0] v;
    logic [127:0] x;
    int t, r0, lat0;
    void'($urandom(seed));
    repeat (5) @(negedge clk);
    rst_n = 1;
    repeat (3) @(negedge clk);
    chk(cke === 1'b1 && cs_n === 1'b1 && dq === 16'hzzzz, "after reset: CKE high, no command, DQ released");

    // ---- every bank, first and last row and line, then random traffic
    for (int b = 0; b < NB; b++) begin
      wr_line(b, 0, 0, rnd128());
      wr_line(b, 511, 7, rnd128());
    end
    for (int b = 0; b < NB; b++) begin
      rd_line(b, 0, 0);
      rd_line(b, 511, 7);
      rd_line(b, 5, 3);                                          // never written: zero
    end
    traffic(`NOPS);
    chk(rd_bad == 0, $sformatf("%0d front-end reads match the reference memory (%0d wrong)", nops, rd_bad));
    chk(mon.data_bad == 0, $sformatf("pin bursts: 8 beats, one DQS toggle each, reads match the written bursts (%0d errors)", mon.data_bad));
    chk(mon.viol == 0, $sformatf("pin timing and command rules (%0d violations)", mon.viol));
    begin
      int bad_rd = 0, bad_wr = 0;
      for (int i = 0; i < mon.lat_rd.size(); i++) if (mon.lat_rd[i] != CL) bad_rd++;
      for (int i = 0; i < mon.lat_wr.size(); i++) if (mon.lat_wr[i] != CWL) bad_wr++;
      chk(bad_rd == 0 && mon.lat_rd.size() > 100, $sformatf("read data exactly CL = %0d clocks after RD (%0d of %0d off, first %0d)",
          CL, bad_rd, mon.lat_rd.size(), mon.lat_rd.size() ? mon.lat_rd[0] : -1));
      chk(bad_wr == 0 && mon.lat_wr.size() > 100, $sformatf("write data exactly CWL = %0d clocks after WR (%0d of %0d off, first %0d)",
          CWL, bad_wr, mon.lat_wr.size(), mon.lat_wr.size() ? mon.lat_wr[0] : -1));
    end
    chk(mon.nact > 50 && mon.npre > 20, $sformatf("traffic opened and closed rows (%0d ACT, %0d PRE)", mon.nact, mon.npre));

    // ---- refresh
    begin
      int w;
`ifdef LPDDR
      int lim = 8 * T_REFI + 300;
`else
      int lim = T_REFI + 300;
`endif
      w = mon.worst_gap();
      chk(w <= lim, $sformatf("every bank refreshed within %0d clocks (worst gap %0d)", lim, w));
      chk(w <= 9 * (lim - 300), "within the JEDEC limit of nine refresh intervals");
      r0 = mon.nref;
      op(3'd5, 0, '0, x, t);
      chk(mon.nref == r0 + 1, "REFRESH command: one REF on the pins");
    end
    chk(irq === 1'b0 && irq_rise == 0, "irq stays low through legal traffic");

    // ---- mode registers
    begin
      bit ok = 1;
      int m0;
      mrr(0, v);
      m0 = v;
      for (int i = 2; i < 8; i++) begin mrw(i, 8'(8'h30 + i)); end
      for (int i = 2; i < 8; i++) begin mrr(i, v); if (v != 8'(8'h30 + i)) ok = 0; end
      chk(ok, "MR2..MR7 write and read back");
`ifndef LPDDR
      mrw(0, 8'h80 | 8'(m0));                                   // LPDDR has no DLL
      mrr(0, v);
      chk(v == m0, $sformatf("MR0 bit 7 (DLL reset) self-clears, CL field kept (%h)", v));
`endif
      lat0 = mon.lat_rd.size();
      mrw(0, 8'(m0 + 3));
      rd_bad = 0; nops = 0;
      traffic(40);
      begin
        bit same = 1;
        int l;
        l = mon.lat_rd[mon.lat_rd.size() - 1];
        for (int i = lat0; i < mon.lat_rd.size(); i++) if (mon.lat_rd[i] != l) same = 0;
        chk(same && l == CL + 3, $sformatf("CL field + 3: every read 3 clocks later (%0d)", l));
      end
      chk(rd_bad == 0 && mon.data_bad == 0 && mon.viol == 0, "traffic correct at the raised CL");
      if (mon.nmrs == 0)
        $display("  [NOTE] MRW changes CL / CWL without an MRS command on the pins: a DRAM device would keep its old latency");
      mrw(0, 8'(m0));
    end

`ifdef LPDDR
    // ---- frequency set points, per-bank refresh, WCK
    begin
      int lb, n0;
      logic [127:0] y;
      op(3'd7, 0, 128'h1, y, t);
      chk(fsp === 1'b1, "FSPW 1: fsp output 1");
      mrr(0, v);
      chk(v == 8'(CL - 5) || v == 8'(CL), $sformatf("FSP1 MR0 at its reset value (%h)", v));
      mrw(0, 8'(v + 2));
      lb = mon.lat_rd.size();
      traffic(20);
      chk(mon.lat_rd[mon.lat_rd.size() - 1] == CL + 2, "FSP1 with CL field + 2: reads 2 clocks later");
      op(3'd7, 0, 128'h0, y, t);
      lb = mon.lat_rd.size();
      traffic(20);
      chk(mon.lat_rd[mon.lat_rd.size() - 1] == CL && fsp === 1'b0, "back to FSP0: original CL");
      n0 = mon.nrefpb;
      op(3'd6, ha(5, 0, 0), '0, y, t);
      chk(mon.nrefpb == n0 + 1, "REFRESH one bank: one per-bank REF on the pins");
      chk(mon.nrefpb > 10, $sformatf("automatic per-bank refresh (%0d REFpb)", mon.nrefpb));
      chk(wck_bad == 0, $sformatf("WCK: complement pair, toggling every write beat, high during reads (%0d errors)", wck_bad));
      chk(rd_bad == 0 && mon.data_bad == 0 && mon.viol == 0, "traffic correct after the FSP switches");
    end
`endif

    // ---- rejected commands (the irq is sticky, so these come last)
    begin
      int t1;
`ifdef LPDDR
      op(3'd1, 32'h0008_0000, '0, x, t1);                       // haddr[31:19] != 0
`else
      op(3'd1, 32'h0004_0000, '0, x, t1);                       // haddr[31:18] != 0
`endif
      @(negedge clk);
      chk(t1 <= 1 && irq === 1'b1, $sformatf("READ outside the address range: done next clock, irq (%0d)", t1));
`ifndef LPDDR
      op(3'd6, 0, '0, x, t1);
      chk(t1 <= 1, "hcmd 6 rejected: done next clock");
`endif
      chk(mon.viol == 0, "no pin activity from rejected commands");
    end

    $display("  pins: %0d ACT %0d RD %0d WR %0d PRE %0d PREA %0d REF %0d REFpb %0d MRS, %0d clocks",
             mon.nact, mon.nrd, mon.nwr, mon.npre, mon.nprea, mon.nref, mon.nrefpb, mon.nmrs, mon.cyc);
    $display("%s checks=%0d fails=%0d", fails ? "XCHK_FAIL" : "XCHK_PASS", checks, fails);
    $finish;
  end
  initial begin #(200_000_000); $display("XCHK_FAIL checks=%0d timeout", checks); $finish; end
endmodule
