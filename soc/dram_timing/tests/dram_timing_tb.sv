// SPDX-License-Identifier: Apache-2.0
// Self-checking test of dram_timing_pkg: presets, page hit / miss /
// conflict latency, burst planning, turnaround, tFAW, refresh (all-bank and
// per-bank), closed page, channel squeeze-out and port-cycle rounding.
// Prints the zero-load latency of every preset (for socgen access_cycles).
module dram_timing_tb;
  import dram_timing_pkg::*;

  int checks = 0, fails = 0;

  function automatic void chk(bit ok, string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endfunction
  function automatic bit near(real a, real b);
    return (a - b) < 0.001 && (b - a) < 0.001;
  endfunction

  initial begin
    dram_timing_cfg   c;
    dram_timing_model m;
    real av[], done, dend, d0, t5;
    string n[$];

    chk(dram_timing_cfg::preset("ddr3-1600") == null, "unknown preset: null");
    chk(!dram_timing_cfg::known("lpddr4") && dram_timing_cfg::known("lpddr4-3200"), "known()");

    // ---------------- LPDDR4-3200 ----------------
    c = dram_timing_cfg::preset("lpddr4-3200");
    chk(c != null && c.family == DRAM_LPDDR4 && c.rate == 3200, "lpddr4-3200 preset");
    chk(near(c.tck, 0.625) && near(c.rl, 17.5) && near(c.wl, 8.75) && near(c.t_burst, 5.0) && c.atom_bytes == 32 &&
        c.nbanks() == 8, "lpddr4-3200: tCK 0.625, RL 28 nCK, WL 14 nCK, BL16 32 B, 8 banks");
    c.refresh_en = 0;
    m = new(c);
    m.plan(1000.0, 0, 64'h8000_0000, 1, 32, av, done);
    chk(m.last_page == PG_MISS && near(av[0] - 1000.0, c.zero_load_ns(0)) && near(c.zero_load_ns(0), 60.5),
        "first read: bank closed, 60.5 ns = ctrl + tRCD + RL + burst");
    m.plan(2000.0, 0, 64'h8000_0040, 1, 32, av, done);
    chk(m.last_page == PG_HIT && near(av[0] - 2000.0, 42.5), "same row: page hit, 42.5 ns");
    m.plan(3000.0, 0, 64'h8000_0000 + (64'd1 << 14), 1, 32, av, done);
    chk(m.last_page == PG_CONFLICT && m.last_bank == 0 && near(av[0] - 3000.0, 60.5 + 18.0),
        "other row, same bank: conflict, + tRP");
    m.plan(4000.0, 0, 64'h8000_0800, 1, 32, av, done);
    chk(m.last_page == PG_MISS && m.last_bank == 1, "next 2 KB: bank 1, miss");
    // a 128-byte burst of 16-byte beats: four atoms, one per 2 beats, tCCD apart
    m.plan(5000.0, 0, 64'h8000_0800, 8, 16, av, done);
    chk(m.last_page == PG_HIT && near(av[1], av[0]) && near(av[2] - av[0], 5.0) && near(av[7] - av[0], 15.0) &&
        near(done, av[7]), "8 x 16 B read: 4 page hits, a burst time apart");
    // write then an immediate read: tWTR after the write data
    m.plan(6000.0, 1, 64'h8000_0800, 2, 16, av, dend);
    chk(near(dend, 6000.0 + 8.75 + 5.0), "write: data in the DRAM after WL + burst");
    chk(near(m.write_ack(6000.0, dend), 6008.0), "posted write ack after the controller pipeline");
    c.posted_writes = 0;
    chk(near(m.write_ack(6000.0, dend), dend + 8.0), "non-posted write ack after the data");
    c.posted_writes = 1;
    d0 = m.access(6000.0, 0, 64'h8000_0800, dend);
    chk(near(d0, 6013.75 + 10.0 + 17.5), "read after write: tWTR, then RL");
    // tFAW: five activates at once to five banks
    m = new(c);
    for (int b = 0; b < 4; b++) void'(m.access(100.0, 0, 64'h8000_0000 + 64'(b) * 2048, dend));
    t5 = m.access(100.0, 0, 64'h8000_0000 + 4 * 2048, dend);
    chk(near(m.act_hist[3], 100.0 + 40.0) && near(t5, 140.0 + 18.0 + 17.5), "fifth ACT waits for tFAW (40 ns)");
    chk(near(m.act_hist[1] - m.act_hist[0], 10.0), "ACT to ACT: tRRD (10 ns)");
    // closed page: the same row twice is two misses
    c.page_policy = PAGE_CLOSED;
    m = new(c);
    void'(m.access(100.0, 0, 64'h8000_0000, dend));
    void'(m.access(500.0, 0, 64'h8000_0040, dend));
    chk(m.last_page == PG_MISS && m.n_page[PG_HIT] == 0, "closed page: no hits");
    c.page_policy = PAGE_OPEN;

    // ---------------- refresh ----------------
    c.refresh_en = 1;
    c.ref_mode = REF_ALL_BANK;
    m = new(c);
    chk(near(m.next_ref, 3904.0), "channel 0: first REFab at tREFI");
    d0 = m.access(3905.0, 0, 64'h8000_0000, dend);
    chk(m.last_stalled && d0 >= 3904.0 + 280.0 + 18.0 + 17.5 - 0.001 && m.n_ref == 1,
        "an access during REFab waits for tRFCab");
    c.ref_mode = REF_PER_BANK;
    m = new(c);
    chk(near(m.ref_interval(), 488.0), "REFpb every tREFI / 8 banks");
    d0 = m.access(489.0, 0, 64'h8000_0000, dend);
    chk(m.last_stalled && near(d0, 488.0 + 140.0 + 18.0 + 17.5), "bank 0 in REFpb: waits tRFCpb");
    d0 = m.access(489.0, 0, 64'h8000_0800, dend);
    chk(!m.last_stalled, "bank 1 is not refreshed then");
    c.channel = 4;
    m = new(c);
    chk(near(m.next_ref, 488.0 * 1.5), "channel 4: refresh phase staggered");

    // ---------------- DDR4-3200 ----------------
    c = dram_timing_cfg::preset("ddr4-3200");
    chk(c.family == DRAM_DDR4 && near(c.tck, 0.625) && near(c.rl, 13.75) && near(c.wl, 10.0) && c.atom_bytes == 16 &&
        near(c.t_burst, 2.5) && near(c.t_ccd, 3.125) && c.nbanks() == 8 && c.ref_mode == REF_ALL_BANK,
        "ddr4-3200: CL 22, CWL 16, BL8 16 B, tCCD_L 5 nCK, 8 banks, REFab only");
    chk(c.bg_of(c.bank_of(c.local_addr(64'h8000_0000 + 4 * 2048))) == 1, "ddr4: bank 4 is in bank group 1");
    c.refresh_en = 0;
    m = new(c);
    m.plan(100.0, 0, 64'h8000_0000, 4, 16, av, done);
    chk(near(av[0] - 100.0, c.zero_load_ns(0)) && near(av[1] - av[0], 3.125) && near(av[3] - av[0], 9.375),
        "ddr4 4 x 16 B: one atom per beat, tCCD_L apart");

    // ---------------- LPDDR5-6400 (the phone preset) ----------------
    c = dram_timing_cfg::preset("lpddr5-6400");
    chk(near(c.tck, 1.25) && near(c.rl, 21.25) && near(c.t_burst, 2.5) && c.nbanks() == 16 && c.refpb_banks == 2,
        "lpddr5-6400: same numbers as lpddr5_pkg LP5_6400");
    c.ref_mode = REF_PER_BANK;
    m = new(c);
    chk(near(m.ref_interval(), 3906.0 / 8), "lpddr5 REFpb on a bank pair every tREFI / 8");

    // ---------------- mapping and port cycles ----------------
    c = dram_timing_cfg::preset("lpddr4-3200");
    c.chan_bits = 1;
    chk(c.local_addr(64'h8000_1000) == 64'h0 && c.local_addr(64'h8000_2000) == 64'h1000, "channel bit squeezed out");
    m = new(c);
    chk(m.cycles_until(10.0, 15.0) == 3 && m.cycles_until(10.0, 14.0) == 2 && m.cycles_until(10.0, 9.0) == 0,
        "port cycles round up at tck_port 2 ns");

    // ---------------- table ----------------
    dram_timing_cfg::names(n);
    $display("preset        hit_ns  miss_ns  miss_cycles@2ns");
    foreach (n[i]) begin
      c = dram_timing_cfg::preset(n[i]);
      chk(c != null && c.zero_load_ns(1) < c.zero_load_ns(0), {n[i], ": preset loads"});
      $display("%-12s  %6.2f  %7.2f  %0d", n[i], c.zero_load_ns(1), c.zero_load_ns(0),
               int'($ceil(c.zero_load_ns(0) / 2.0)));
    end

    if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
    else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
endmodule
