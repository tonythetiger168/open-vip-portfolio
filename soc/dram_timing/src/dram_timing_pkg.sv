// SPDX-License-Identifier: Apache-2.0
// ============================================================================
// dram_timing_pkg -- DRAM channel timing model with named speed presets
// ----------------------------------------------------------------------------
// Gives an AXI (or any) memory slave responder the timing of one DRAM channel
// and its controller, chosen by the preset name a SoC spec carries
// (socgen memories[].timing: "lpddr4-3200", "ddr4-3200", "lpddr5-6400", ...).
// Plain SystemVerilog classes: no UVM, no bus package, so it drops into a
// UVM slave driver, a socgen memory model or a bare testbench alike.
//
// What one channel models (one x16 channel + its controller), taken from the
// phone SoC's lpddr5_pkg channel model and generalised over DRAM families:
//  * nbanks banks (bank groups where the family has them), one open row per
//    bank, 2 KB page; open-page (default) or closed-page (auto-precharge).
//  * Per access atom (one burst: BL8 x16 = 16 B for DDR4, BL16 x16 = 32 B
//    for LPDDR4 / LPDDR5): page hit / miss (bank closed) / conflict (other
//    row open), with tRCD, tRP, tRAS, tRRD, tFAW, tWR, tRTP, write-to-read
//    (tWTR) and read-to-write turnaround, tCCD, RL / WL, the burst time on
//    the data bus and a controller + PHY pipeline latency.
//  * Refresh: all-bank (REFab every tREFI, channel blocked for tRFCab) or
//    per-bank (LPDDR only: refpb_banks banks per REFpb, the banks in turn,
//    each blocked for tRFCpb). Refreshes are scheduled in time whether or not
//    traffic comes.
//  * Requests are served in arrival order (no FR-FCFS reordering); reads and
//    writes share the bank and bus state.
//  * Address mapping: the channel-select bits of the system address are
//    squeezed out (chan_lsb / chan_bits), then local[col_bits-1:0] column,
//    the next bank_bits bank (the top bg_bits of it the bank group), the rest
//    row.
//
// Timing values are representative of the JEDEC speed bins (JESD79-4 DDR4,
// JESD209-4 LPDDR4/4X, JESD209-5 LPDDR5/5X) for an 8 Gb x16 device, not a
// particular vendor datasheet. Times are in ns.
//
// Use:
//   dram_timing_cfg   c = dram_timing_cfg::preset("lpddr4-3200");
//   dram_timing_model m = new(c);
//   c.tck_port = 2.0;                       // the AXI port clock, ns
//   m.plan(now_ns, is_write, addr, beats, beat_bytes, avail, done);
//   // read beat i may go out at avail[i]; a write is complete at done
// ============================================================================
`ifndef DRAM_TIMING_PKG_SV
`define DRAM_TIMING_PKG_SV
package dram_timing_pkg;

  typedef enum int { DRAM_DDR4 = 0, DRAM_LPDDR4 = 1, DRAM_LPDDR5 = 2 } dram_family_e;
  typedef enum int { PAGE_OPEN = 0, PAGE_CLOSED = 1 } dram_page_policy_e;
  typedef enum int { REF_ALL_BANK = 0, REF_PER_BANK = 1 } dram_ref_mode_e;
  typedef enum int { PG_HIT = 0, PG_MISS = 1, PG_CONFLICT = 2 } dram_page_e;

  localparam int MAX_BANKS = 16;

  // ==========================================================================
  class dram_timing_cfg;
    string             name = "";
    dram_family_e      family = DRAM_LPDDR4;
    int unsigned       rate = 3200;           // MT/s
    int                channel = 0;
    dram_page_policy_e page_policy = PAGE_OPEN;
    dram_ref_mode_e    ref_mode    = REF_ALL_BANK;
    bit                refresh_en  = 1;
    bit                posted_writes = 1;     // write ack as soon as it is buffered

    // ---- system-address -> channel-local mapping ----
    longint unsigned dram_base = 64'h8000_0000;
    int unsigned     chan_lsb  = 12;          // first channel-select bit
    int unsigned     chan_bits = 0;           // log2(channels)

    // ---- geometry ----
    int unsigned col_bits    = 11;            // 2 KB page
    int unsigned bank_bits   = 3;
    int unsigned bg_bits     = 0;             // bank-group bits (top of the bank number)
    int unsigned atom_bytes  = 32;            // bytes per burst
    int unsigned refpb_banks = 1;             // banks per REFpb

    // ---- clocks ----
    real tck_port = 2.0;                      // the slave port's clock (AXI / NoC)
    real tck;                                 // DRAM CK
    // ---- timing ----
    real rl, wl, t_burst, t_ccd;
    real t_rcd, t_rp, t_ras, t_wr, t_rtp, t_rrd, t_faw, t_wtr, t_rtw;
    real t_refi, t_rfcab, t_rfcpb;
    real t_ctrl_rd = 20.0, t_ctrl_wr_ack = 8.0;   // controller + PHY pipelines

    function int unsigned nbanks();
      return 1 << bank_bits;
    endfunction

    // every preset name preset() knows
    static function void names(ref string n[$]);
      n = '{"ddr4-2400", "ddr4-3200", "lpddr4-3200", "lpddr4x-4266", "lpddr5-6400", "lpddr5x-8533"};
    endfunction

    static function bit known(string s);
      string n[$];
      names(n);
      foreach (n[i]) if (n[i] == s) return 1;
      return 0;
    endfunction

    // a configuration from a preset name; an unknown name gives null
    static function dram_timing_cfg preset(string s);
      dram_timing_cfg c = new();
      if (!c.set_preset(s)) return null;
      return c;
    endfunction

    function bit set_preset(string s);
      int rl_nck, wl_nck, bl;
      case (s)
        "ddr4-2400":    begin family = DRAM_DDR4;   rate = 2400; rl_nck = 16; wl_nck = 12; end
        "ddr4-3200":    begin family = DRAM_DDR4;   rate = 3200; rl_nck = 22; wl_nck = 16; end
        "lpddr4-3200":  begin family = DRAM_LPDDR4; rate = 3200; rl_nck = 28; wl_nck = 14; end
        "lpddr4x-4266": begin family = DRAM_LPDDR4; rate = 4266; rl_nck = 36; wl_nck = 18; end
        "lpddr5-6400":  begin family = DRAM_LPDDR5; rate = 6400; rl_nck = 17; wl_nck = 9;  end
        "lpddr5x-8533": begin family = DRAM_LPDDR5; rate = 8533; rl_nck = 23; wl_nck = 12; end
        default: return 0;
      endcase
      name = s;
      col_bits = 11;
      case (family)
        DRAM_DDR4: begin
          // x16: 2 bank groups x 4 banks, BL8; CK = data rate / 2
          bank_bits = 3; bg_bits = 1; bl = 8; refpb_banks = 1;
          tck = 2000.0 / rate;
          t_rcd = 13.75; t_rp = 13.75; t_ras = 32.0; t_wr = 15.0; t_rtp = 7.5;
          t_rrd = 6.4; t_faw = 30.0; t_wtr = 7.5; t_rtw = 7.5;
          t_refi = 7800.0; t_rfcab = 350.0; t_rfcpb = 350.0;
          t_ccd = 5 * tck;                      // tCCD_L
          ref_mode = REF_ALL_BANK;              // DDR4 has no per-bank refresh
        end
        DRAM_LPDDR4: begin
          // x16 channel: 8 banks, BL16; CK = data rate / 2
          bank_bits = 3; bg_bits = 0; bl = 16; refpb_banks = 1;
          tck = 2000.0 / rate;
          t_rcd = 18.0; t_rp = 18.0; t_ras = 42.0; t_wr = 18.0; t_rtp = 7.5;
          t_rrd = 10.0; t_faw = 40.0; t_wtr = 10.0; t_rtw = 10.0;
          t_refi = 3904.0; t_rfcab = 280.0; t_rfcpb = 140.0;
          t_ccd = 8 * tck;
        end
        default: begin
          // x16 channel in bank-group mode: 4 BG x 4 banks, BL16; CK = data rate / 8
          bank_bits = 4; bg_bits = 2; bl = 16; refpb_banks = 2;
          tck = 8000.0 / rate;
          t_rcd = 18.0; t_rp = 18.0; t_ras = 42.0; t_wr = 34.0; t_rtp = 7.5;
          t_rrd = 5.0; t_faw = 20.0; t_wtr = 12.0; t_rtw = 10.0;
          t_refi = 3906.0; t_rfcab = 280.0; t_rfcpb = 140.0;
          t_ccd = 0.0;                          // the burst time bounds it
        end
      endcase
      rl = rl_nck * tck;
      wl = wl_nck * tck;
      atom_bytes = bl * 16 / 8;
      t_burst = bl * 1000.0 / rate;             // bl beats at the data rate
      if (t_ccd < t_burst) t_ccd = t_burst;
      return 1;
    endfunction

    // zero-load read latency from request to the first data (ns), at the
    // slave port: a page hit (hit = 1) or a closed bank
    function real zero_load_ns(bit hit);
      return t_ctrl_rd + (hit ? 0.0 : t_rcd) + rl + t_burst;
    endfunction

    // channel-local byte address
    function longint unsigned local_addr(longint unsigned a);
      longint unsigned off = a - dram_base;
      longint unsigned lo  = off & ((64'd1 << chan_lsb) - 1);
      longint unsigned hi  = off >> (chan_lsb + chan_bits);
      return (hi << chan_lsb) | lo;
    endfunction
    function int unsigned bank_of(longint unsigned la);
      return int'((la >> col_bits) & ((64'd1 << bank_bits) - 1));
    endfunction
    function int unsigned bg_of(int unsigned b);
      return b >> (bank_bits - bg_bits);
    endfunction
    function int unsigned row_of(longint unsigned la);
      return int'(la >> (col_bits + bank_bits));
    endfunction

    function string convert2string();
      return $sformatf("%s ch%0d %s %s: tCK %.3f RL %.2f WL %.2f burst %.2f (%0d B) tRCD %.2f tRP %.2f tRAS %.1f tREFI %.0f tRFC %.0f ns",
                       name, channel, page_policy.name(), ref_mode.name(), tck, rl, wl, t_burst, atom_bytes,
                       t_rcd, t_rp, t_ras, t_refi, ref_mode == REF_ALL_BANK ? t_rfcab : t_rfcpb);
    endfunction
  endclass

  // ==========================================================================
  // dram_timing_model -- bank / bus / refresh state of one channel (ns)
  // ==========================================================================
  class dram_timing_model;
    dram_timing_cfg cfg;
    bit          b_open      [MAX_BANKS];
    int unsigned b_row       [MAX_BANKS];
    real         b_ready     [MAX_BANKS];   // earliest next RD/WR/ACT on this bank
    real         b_pre_ok    [MAX_BANKS];   // earliest PRE
    real         b_ref_until [MAX_BANKS];   // end of the last refresh of this bank
    real         act_hist[$];               // last four ACT times (tFAW)
    real         last_act = -1000.0;
    real         bus_free = 0.0;
    real         last_rd_cmd = -1000.0, last_wr_end = -1000.0;
    real         ref_block_until = 0.0;
    real         next_ref = 0.0;
    int unsigned next_pb = 0;

    // statistics
    longint unsigned n_access[2], n_page[3], n_ref, n_ref_stall;
    // the last access, for coverage or checks
    dram_page_e  last_page;
    int unsigned last_bank;
    bit          last_stalled;

    function new(dram_timing_cfg c);
      cfg = c;
      foreach (b_open[i]) begin
        b_open[i] = 0; b_row[i] = 0; b_ready[i] = 0.0; b_pre_ok[i] = 0.0; b_ref_until[i] = 0.0;
      end
      foreach (n_access[i]) n_access[i] = 0;
      foreach (n_page[i]) n_page[i] = 0;
      n_ref = 0; n_ref_stall = 0;
      // stagger the refresh phase of the channels
      next_ref = ref_interval() * (1.0 + (cfg.channel % 8) / 8.0);
    endfunction

    function real ref_interval();
      if (cfg.ref_mode == REF_ALL_BANK) return cfg.t_refi;
      return cfg.t_refi * cfg.refpb_banks / cfg.nbanks();
    endfunction

    static function real rmax(real a, real b);
      return (a > b) ? a : b;
    endfunction

    // apply every refresh due at or before t
    function void do_refresh(real t);
      if (!cfg.refresh_en) return;
      while (next_ref <= t) begin
        if (cfg.ref_mode == REF_ALL_BANK) begin
          real start = next_ref;
          for (int i = 0; i < cfg.nbanks(); i++) if (b_open[i]) start = rmax(start, b_pre_ok[i]);
          if (start > next_ref) start = start + cfg.t_rp;      // precharge-all first
          for (int i = 0; i < cfg.nbanks(); i++) begin
            b_open[i] = 0;
            b_ready[i] = rmax(b_ready[i], start + cfg.t_rfcab);
            b_ref_until[i] = start + cfg.t_rfcab;
          end
          ref_block_until = rmax(ref_block_until, start + cfg.t_rfcab);
        end else begin
          int unsigned step = cfg.nbanks() / cfg.refpb_banks;
          for (int unsigned k = 0; k < cfg.refpb_banks; k++) begin
            int unsigned b = next_pb + step * k;
            real start = next_ref;
            if (b_open[b]) start = rmax(start, b_pre_ok[b]) + cfg.t_rp;
            b_open[b] = 0;
            b_ready[b] = rmax(b_ready[b], start + cfg.t_rfcpb);
            b_ref_until[b] = start + cfg.t_rfcpb;
          end
          next_pb = (next_pb + 1) % step;
        end
        next_ref += ref_interval();
        n_ref++;
      end
    endfunction

    // one atom arriving at the DRAM scheduler at time t: returns when its
    // data starts on the DRAM bus; data_end is when it ends
    function real access(real t, bit wr, longint unsigned sys_addr, output real data_end);
      longint unsigned la = cfg.local_addr(sys_addr);
      int unsigned b = cfg.bank_of(la), r = cfg.row_of(la);
      real t0, t_act, t_cmd, d0;
      dram_page_e pg;
      bit stalled;

      do_refresh(t);
      t0 = t;
      if (cfg.ref_mode == REF_ALL_BANK && ref_block_until > t0) t0 = ref_block_until;
      stalled = b_ref_until[b] > t;
      t0 = rmax(t0, b_ready[b]);

      if (b_open[b] && b_row[b] == r) begin
        pg = PG_HIT;
        t_cmd = t0;
      end else begin
        real t_pre_done = t0;
        if (b_open[b]) begin
          pg = PG_CONFLICT;
          t_pre_done = rmax(t0, b_pre_ok[b]) + cfg.t_rp;
        end else
          pg = PG_MISS;
        t_act = rmax(t_pre_done, last_act + cfg.t_rrd);
        if (act_hist.size() >= 4) t_act = rmax(t_act, act_hist[0] + cfg.t_faw);
        act_hist.push_back(t_act);
        if (act_hist.size() > 4) void'(act_hist.pop_front());
        last_act = rmax(last_act, t_act);
        b_open[b] = 1; b_row[b] = r;
        b_pre_ok[b] = t_act + cfg.t_ras;
        t_cmd = t_act + cfg.t_rcd;
      end
      if (wr) t_cmd = rmax(t_cmd, last_rd_cmd + cfg.t_rtw);
      else    t_cmd = rmax(t_cmd, last_wr_end + cfg.t_wtr);
      d0 = rmax(t_cmd + (wr ? cfg.wl : cfg.rl), bus_free);
      data_end = d0 + cfg.t_burst;
      bus_free = data_end;
      if (wr) begin
        last_wr_end = data_end;
        b_pre_ok[b] = rmax(b_pre_ok[b], data_end + cfg.t_wr);
      end else begin
        last_rd_cmd = t_cmd;
        b_pre_ok[b] = rmax(b_pre_ok[b], t_cmd + cfg.t_rtp);
      end
      b_ready[b] = t_cmd + cfg.t_ccd;
      if (cfg.page_policy == PAGE_CLOSED) begin    // auto-precharge
        b_open[b]  = 0;
        b_ready[b] = rmax(b_ready[b], b_pre_ok[b] + cfg.t_rp);
      end

      n_access[wr]++;
      n_page[pg]++;
      if (stalled) n_ref_stall++;
      last_page = pg; last_bank = b; last_stalled = stalled;
      return d0;
    endfunction

    // plan a burst of beats (beat i at addr + i * beat_bytes, INCR): read
    // beat i may leave the slave at avail[i]; done is when the burst is
    // complete (the last read beat, or the write's last data in the DRAM)
    function void plan(real t, bit wr, longint unsigned addr, int unsigned beats, int unsigned beat_bytes,
                       ref real avail[], output real done);
      longint unsigned cur_atom = '1;
      real d0 = t, dend = t, tq;
      tq = t + (wr ? 0.0 : cfg.t_ctrl_rd / 2.0);   // request side of the pipeline
      avail = new[beats];
      for (int unsigned i = 0; i < beats; i++) begin
        longint unsigned a = addr + longint'(i) * beat_bytes;
        longint unsigned atom = a / cfg.atom_bytes;
        if (atom != cur_atom) begin
          d0 = access(tq, wr, a, dend);
          cur_atom = atom;
        end
        avail[i] = wr ? dend : d0 + cfg.t_burst + cfg.t_ctrl_rd / 2.0;
      end
      done = wr ? dend : avail[beats - 1];
    endfunction

    // the write response time for a write burst planned at t
    function real write_ack(real t, real done);
      return cfg.posted_writes ? t + cfg.t_ctrl_wr_ack : done + cfg.t_ctrl_wr_ack;
    endfunction

    // port clock cycles from now until t (0 when t has passed)
    function int unsigned cycles_until(real now, real t);
      if (t <= now) return 0;
      return int'($ceil((t - now) / cfg.tck_port));   // int'() of a real rounds, so ceil first
    endfunction

    function real hit_rate();
      longint unsigned n = n_page[PG_HIT] + n_page[PG_MISS] + n_page[PG_CONFLICT];
      return n ? 100.0 * n_page[PG_HIT] / n : 0.0;
    endfunction
  endclass
endpackage
`endif
