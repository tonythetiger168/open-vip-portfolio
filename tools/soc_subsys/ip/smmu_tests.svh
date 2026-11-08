// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// smmu_tests.svh -- SMMU-UVM-VIP functional tests (included by smmu_pkg.sv).
// The kit's manager BFM drives the upstream port (s_*) with virtual
// addresses; the kit's subordinate on the downstream port (m_*) holds the
// page table and the physical pages.
// Reference model (open-ip-portfolio specs/SMMU.json features):
//   PTE at PT_BASE + 4 * VA[31:12]: bit 0 VALID, bit 1 WRITABLE, 31:12 PPN;
//   PA = {PPN, VA[11:0]}; walks are single-beat reads, ID 15, AxPROT 3'b010.
//   4-entry fully associative TLB, round-robin fill on a successful walk,
//   CMD.tlb_inv empties it. A lookup that hits counts in HITS, one that walks
//   in MISSES (the re-lookup after a walk counts neither).
//   Fault (not VALID, walk error, write to a page that is not WRITABLE):
//   nothing forwarded, SLVERR upstream, FAULT_ADDR = VA, FAULT_INFO =
//   {walk_err, write, not_writable, not_valid}, FAULT interrupt.
//   CTRL.enable = 0: PA = VA, no walk, no fault.
/* TEST PLAN
- `smmu_bypass_test`: CTRL.enable = 0: 60 random reads and writes (1..16
  beats) reach m_* at the same address with the same ID; data both ways; no
  walk, HITS = MISSES = 0.
- `smmu_xlate_test`: 16 mapped pages (12 writable) at random VPNs and PPNs,
  300 random reads and writes (writes only to writable pages) under four
  back-pressure settings. Checks: upstream read data = memory at the PA,
  writes land at the PA and nowhere else (m_* address windows: page table
  read-only, each mapped page as its PTE allows), every walk is one beat at
  PT_BASE + 4 * VPN with ID 15 and AxPROT 3'b010, forwarded bursts keep the
  upstream ID, HITS and MISSES equal the TLB model, no fault.
- `smmu_fault_test`: read and write of an invalid page (FAULT_INFO 0001 /
  0101), write to a read-only page on a cold TLB and on a TLB hit (0110),
  walk into a SLVERR page table (1000 / 1100): SLVERR upstream on every beat,
  nothing but the walk on m_*, memory untouched, FAULT_ADDR, FAULT interrupt;
  a good access afterwards still works.
- `smmu_inv_test`: a cached translation survives a PTE change (TLB hit to the
  old PA) until CMD.tlb_inv, then the new PA is used; round-robin eviction:
  after 5 distinct pages the first one walks again.
*/

class smmu_job_base_test extends smmu_base_test;
  `uvm_component_utils(smmu_job_base_test)
  virtual axim_if  s_vif;
  ssv_axi_mgr_bfm  up;
  bit [31:0]       pt_base = 32'h0080_0000;
  // TLB model
  bit [19:0]       t_vpn[4];
  bit [19:0]       t_ppn[4];
  bit              t_v[4], t_w[4];
  int unsigned     t_rr, m_hits, m_misses;
  // page table as written to memory
  bit [31:0]       pte[bit [19:0]];

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual axim_if)::get(this, "", "axim_s_vif", s_vif))
      `uvm_fatal("NOVIF", "axim_s_vif not set")
    up = ssv_axi_mgr_bfm::type_id::create("up");
    up.vif = s_vif;
  endfunction

  function void configure_axi(axim_cfg c);
    super.configure_axi(c);
    c.expect_id = -1;    // forwarded bursts keep the upstream ID, walks use 15
  endfunction

  task start_up();
    up.init();
    wait_reset();
  endtask

  function void map(bit [19:0] vpn, bit [19:0] ppn, bit valid = 1, bit writable = 1);
    pte[vpn] = {ppn, 10'h0, writable, valid};
    mem().wr32(pt_base + 4 * vpn, pte[vpn]);
  endfunction

  function void tlb_inv_model();
    foreach (t_v[i]) t_v[i] = 0;
  endfunction

  // the model's view of one burst: returns 1 and the PA when it is forwarded,
  // 0 and the FAULT_INFO when it faults; updates the TLB and the counters
  function bit model(bit [31:0] va, bit write, output bit [31:0] pa, output bit [3:0] finfo, output bit walked);
    bit [19:0] vpn = va[31:12];
    bit [31:0] e;
    walked = 0;
    for (int pass = 0; pass < 2; pass++) begin
      for (int i = 0; i < 4; i++)
        if (t_v[i] && t_vpn[i] == vpn) begin
          if (!walked) m_hits++;
          if (write && !t_w[i]) begin finfo = 4'b0110; return 0; end
          pa = {t_ppn[i], va[11:0]};
          return 1;
        end
      if (walked) break;
      m_misses++;
      walked = 1;
      if (env.axi_cfg.resp_for(pt_base + 4 * vpn, 0) != AXI_OKAY) begin finfo = {1'b1, write, 2'b00}; return 0; end
      e = mem().rd32(pt_base + 4 * vpn);
      if (!e[0]) begin finfo = {1'b0, write, 2'b01}; return 0; end
      t_vpn[t_rr] = vpn; t_ppn[t_rr] = e[31:12]; t_w[t_rr] = e[1]; t_v[t_rr] = 1;
      t_rr = (t_rr + 1) % 4;
    end
    finfo = 4'b1111;   // unreachable
    return 0;
  endfunction

  function void allow(bit [31:0] lo, bit [31:0] hi, bit rd_ok, bit wr_ok, string tag);
    env.axi_cfg.add_window(lo, hi, rd_ok, wr_ok, tag);
  endfunction

  // one upstream burst with full checking against the model
  task access(bit [31:0] va, bit write, int unsigned beats, bit [3:0] id, output bit faulted);
    bit [31:0] pa, exp[$], d[$], got[$]; bit [3:0] s[$], finfo, fi; bit [1:0] resp, rr[$]; bit walked, fwd;
    bit [31:0] fa, irqs; bit [31:0] v;
    int unsigned n0 = env.axi.mon.completed.size();
    string tag = $sformatf("%s va=%08h beats=%0d id=%0d", write ? "WR" : "RD", va, beats, id);
    fwd = model(va, write, pa, finfo, walked);
    faulted = !fwd;
    if (write) begin
      for (int i = 0; i < beats; i++) begin d.push_back($urandom()); s.push_back(4'hF); end
      if (fwd) foreach (d[i]) exp.push_back(d[i]);
      up.write(id, va, beats - 1, 2, AXI_INCR, d, s, resp);
      sb_check(resp == (fwd ? AXI_OKAY : AXI_SLVERR), $sformatf("%s: BRESP %0d", tag, resp));
      if (fwd) check_words(pa, exp, {tag, " data at PA"});
    end else begin
      if (fwd) mem().get_words(pa, beats, exp);
      up.read(id, va, beats - 1, 2, AXI_INCR, got, rr);
      sb_check(got.size() == beats, $sformatf("%s: %0d beats", tag, got.size()));
      foreach (got[i]) begin
        sb_check(rr[i] == (fwd ? AXI_OKAY : AXI_SLVERR), $sformatf("%s beat %0d: RRESP %0d", tag, i, rr[i]));
        if (fwd && i < exp.size()) check_eq(got[i], exp[i], $sformatf("%s beat %0d data", tag, i));
      end
    end
    clocks(2);
    // what went out on m_*: an optional walk, then the forwarded burst
    begin
      int unsigned k = n0;
      if (walked) begin
        if (k < env.axi.mon.completed.size()) begin
          axim_txn w = env.axi.mon.completed[k];
          sb_check(!w.write && w.id == 4'hF && w.prot == 3'b010 && w.beats() == 1 && w.addr == pt_base + 4 * va[31:12],
                $sformatf("%s: walk %s, prot %0d", tag, w.convert2string(), w.prot));
          k++;
        end else sb_check(0, {tag, ": no walk on m_*"});
      end
      if (fwd) begin
        if (k < env.axi.mon.completed.size()) begin
          axim_txn f = env.axi.mon.completed[k];
          sb_check(f.write == write && f.id == id && f.addr == pa && f.beats() == beats,
                $sformatf("%s: forwarded %s, expected PA %08h", tag, f.convert2string(), pa));
          k++;
        end else sb_check(0, {tag, ": nothing forwarded"});
      end
      sb_check(k == env.axi.mon.completed.size(), $sformatf("%s: %0d unexpected bursts on m_*", tag,
                                                       env.axi.mon.completed.size() - k));
    end
    if (!fwd) begin
      wait_irq(irqs, tag);
      sb_check(irqs[irq_bit("FAULT")], {tag, ": FAULT interrupt not set"});
      rd("FAULT_ADDR", fa);
      check_eq(fa, va, {tag, " FAULT_ADDR"});
      rd("FAULT_INFO", v);
      check_eq(v, finfo, {tag, " FAULT_INFO"});
      clear_irq(irqs);
    end
  endtask

  task check_stats(string when);
    bit [31:0] h, m;
    rd_field("TLB_STATS", "hits", h);
    rd_field("TLB_STATS", "misses", m);
    check_eq(h, m_hits, {when, " HITS"});
    check_eq(m, m_misses, {when, " MISSES"});
  endtask

  function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    if (s_vif.chk_errors != 0)
      `uvm_error("SMMU_S_PORT", $sformatf("%0d AXI4 protocol errors on the subordinate port s_*", s_vif.chk_errors))
  endfunction

  task enable_xlate();
    wr("PT_BASE", pt_base);
    wr("CMD", 32'h1);
    tlb_inv_model();
    wr("IRQ_ENABLE", 32'h1);
    wr("CTRL", 32'h1);
  endtask
endclass

// testlist: smmu_bypass_test 2
class smmu_bypass_test extends smmu_job_base_test;
  `uvm_component_utils(smmu_bypass_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$], got[$], h; bit [3:0] s[$]; bit [1:0] resp, rr[$];
    phase.raise_objection(this);
    start_up();
    for (int i = 0; i < 60; i++) begin
      int unsigned beats = $urandom_range(1, 16);
      bit [31:0] va = 32'h5000_0000 + ($urandom_range(255) << 12) + 4 * $urandom_range(0, 1024 - beats);
      bit [3:0] id = $urandom_range(14);
      int unsigned n0 = env.axi.mon.completed.size();
      env.axi_cfg.set_backpressure(i % 2 ? 50 : 100, i % 3);
      if (i % 2) begin
        w.delete(); s.delete();
        for (int b = 0; b < beats; b++) begin w.push_back($urandom()); s.push_back(4'hF); end
        up.write(id, va, beats - 1, 2, AXI_INCR, w, s, resp);
        sb_check(resp == AXI_OKAY, "bypass write BRESP");
        check_words(va, w, "bypass write");
      end else begin
        fill_random(va, beats, w);
        up.read(id, va, beats - 1, 2, AXI_INCR, got, rr);
        foreach (w[b]) check_eq(got[b], w[b], $sformatf("bypass read %08h beat %0d", va, b));
      end
      clocks(2);
      sb_check(env.axi.mon.completed.size() == n0 + 1, "bypass: not exactly one burst on m_*");
      if (env.axi.mon.completed.size() == n0 + 1) begin
        axim_txn t = env.axi.mon.completed[n0];
        sb_check(t.addr == va && t.id == id && t.beats() == beats, $sformatf("bypass forwarded %s", t.convert2string()));
      end
    end
    rd("TLB_STATS", h);
    check_eq(h, 0, "TLB_STATS in bypass");
    phase.drop_objection(this);
  endtask
endclass

// testlist: smmu_xlate_test 3
class smmu_xlate_test extends smmu_job_base_test;
  `uvm_component_utils(smmu_xlate_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [19:0] vpns[$], ppns[$]; bit wrt[$]; bit f;
    phase.raise_objection(this);
    start_up();
    env.axi_cfg.check_windows = 1;
    allow(pt_base, pt_base + 32'h0040_0000, 1, 0, "page table");
    for (int i = 0; i < 16; i++) begin
      bit [19:0] v, p;
      v = 20'h40000 + i * 20'h400 + 20'($urandom_range(20'h3FF));   // distinct
      p = 20'h10000 + i * 20'h111;
      vpns.push_back(v); ppns.push_back(p); wrt.push_back(i < 12);
      map(v, p, 1, i < 12);
      allow({p, 12'h0}, {p, 12'h0} + 32'h1000, 1, i < 12, $sformatf("page %0d", i));
      for (int k = 0; k < 1024; k++) mem().wr32({p, 12'h0} + 4 * k, $urandom());
    end
    enable_xlate();
    for (int n = 0; n < 300; n++) begin
      int pg = (n % 10 < 7) ? $urandom_range(3) : $urandom_range(15);   // mostly a hot set of 4
      bit write = wrt[pg] && $urandom_range(1);
      int unsigned beats = $urandom_range(1, 16);
      bit [31:0] va = {vpns[pg], 12'h0} + 4 * $urandom_range(0, 1024 - beats);
      case (n % 4)
        0: env.axi_cfg.set_backpressure(100, 0);
        1: env.axi_cfg.set_backpressure(60, 3);
        2: env.axi_cfg.set_backpressure(30, 8);
        3: env.axi_cfg.set_backpressure(90, 1);
      endcase
      access(va, write, beats, 4'($urandom_range(14)), f);
      sb_check(!f, $sformatf("access %0d faulted", n));
      if (n % 50 == 49) check_stats($sformatf("after %0d accesses", n + 1));
    end
    sb_check(m_hits > 100 && m_misses > 10, $sformatf("TLB mix too thin: %0d hits, %0d misses", m_hits, m_misses));
    phase.drop_objection(this);
  endtask
endclass

// testlist: smmu_fault_test 2
class smmu_fault_test extends smmu_job_base_test;
  `uvm_component_utils(smmu_fault_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit f;
    phase.raise_objection(this);
    start_up();
    env.axi_cfg.check_windows = 1;
    allow(pt_base, pt_base + 32'h0040_0000, 1, 0, "page table");
    map(20'h40001, 20'h10001, 1, 1);  allow(32'h1000_1000, 32'h1000_2000, 1, 1, "rw page");
    map(20'h40002, 20'h10002, 1, 0);  allow(32'h1000_2000, 32'h1000_3000, 1, 0, "ro page");
    map(20'h40003, 20'h10003, 0, 1);  // not valid
    enable_xlate();
    access(32'h4000_3010, 0, 4, 4'h1, f);  sb_check(f, "read of an invalid page did not fault");
    access(32'h4000_3020, 1, 2, 4'h2, f);  sb_check(f, "write of an invalid page did not fault");
    access(32'h4000_2000, 1, 8, 4'h3, f);  sb_check(f, "write of a read-only page (cold) did not fault");
    access(32'h4000_2040, 0, 8, 4'h4, f);  sb_check(!f, "read of a read-only page faulted");
    access(32'h4000_2080, 1, 16, 4'h5, f); sb_check(f, "write of a read-only page (TLB hit) did not fault");
    access(32'h4000_1000, 1, 16, 4'h6, f); sb_check(!f, "write of a writable page faulted");
    // the page table entry of VPN 0x40009 sits in a SLVERR region: walk error
    env.axi_cfg.add_err_region(pt_base + 4 * 32'h40009, pt_base + 4 * 32'h40009 + 4, AXI_SLVERR);
    access(32'h4000_9100, 0, 3, 4'h7, f);  sb_check(f, "read with a walk error did not fault");
    access(32'h4000_9200, 1, 3, 4'h8, f);  sb_check(f, "write with a walk error did not fault");
    access(32'h4000_1100, 0, 5, 4'h9, f);  sb_check(!f, "good read after faults faulted");
    check_stats("end");
    sb_check(mem().written_outside(32'h1000_1000, 32'h1000_2000) == 0, "a faulting write reached memory");
    phase.drop_objection(this);
  endtask
endclass

// testlist: smmu_inv_test 1
class smmu_inv_test extends smmu_job_base_test;
  `uvm_component_utils(smmu_inv_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit f;
    phase.raise_objection(this);
    start_up();
    for (int i = 0; i < 6; i++) begin
      map(20'h40010 + i, 20'h10010 + i, 1, 1);
      for (int k = 0; k < 64; k++) mem().wr32({20'h10010 + i, 12'h0} + 4 * k, $urandom());
      for (int k = 0; k < 64; k++) mem().wr32({20'h20010 + i, 12'h0} + 4 * k, $urandom());
    end
    enable_xlate();
    access(32'h4001_0000, 0, 4, 4'h1, f);          // walk, fill entry 0
    map(20'h40010, 20'h20010, 1, 1);               // change the table, no invalidate
    access(32'h4001_0000, 0, 4, 4'h1, f);          // TLB hit: still the old PA (model agrees)
    wr("CMD", 32'h1); tlb_inv_model();
    access(32'h4001_0000, 0, 4, 4'h1, f);          // walks again: new PA
    // round robin: 5 distinct pages, then the first walks again
    wr("CMD", 32'h1); tlb_inv_model();
    for (int i = 0; i < 6; i++) access({20'h40010 + i, 12'h0}, 0, 2, 4'h2, f);
    access(32'h4001_1000, 0, 2, 4'h3, f);          // page 1 was evicted by page 5? model decides
    access(32'h4001_5000, 0, 2, 4'h3, f);
    check_stats("end");
    sb_check(m_misses >= 9, $sformatf("only %0d misses", m_misses));
    phase.drop_objection(this);
  endtask
endclass
