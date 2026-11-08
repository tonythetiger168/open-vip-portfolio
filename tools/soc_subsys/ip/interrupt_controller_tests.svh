// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// interrupt_controller_tests.svh -- Interrupt_Controller-UVM-VIP functional
// tests (included by interrupt_controller_pkg.sv).
// Reference model (open-ip-portfolio specs/Interrupt_Controller.json):
//   PENDING = (irq_src | SW_SET) & ENABLE; cpu_irq = |PENDING;
//   CLAIM = {valid (bit 31), id (bits 4:0)} of the lowest pending source;
//   LOG_EN: each rising edge of a PENDING bit asks for one record
//   {ts[23:0], 3'b000, id} at LOG_BASE + 4 * (n mod LOG_WORDS); the lowest
//   waiting id is written first; edges of a source still waiting merge;
//   ts = free-running clock counter, taken when the record write starts.
// intc_model follows every APB write (a register write takes effect in the
// next clock) and the irq_src pins. Every clock it checks the cpu_irq pin;
// on every APB read it checks PENDING, CLAIM and STATE.cpu_irq; it records
// every pending edge (with its clock) for the record checks:
//   a record of source id with timestamp T needs an unrecorded edge of id
//   from clock T - 2 or before (the edge is seen in clock E, the record is
//   started in E + 1 at the earliest and its word is taken one clock later),
//   and consumes all of them (merged); no lower id may have an unrecorded
//   edge from T - 2 or before (priority); the address follows the ring.
/* TEST PLAN
- `interrupt_controller_pend_test`: 3000 clocks of random level changes on
  all 32 sources with random ENABLE and SW_SET writes, PENDING / CLAIM /
  STATE read in between: cpu_irq checked every clock, every read checked.
  Then an interrupt service loop: 20 rounds of random sources raised, and
  on cpu_irq the handler reads CLAIM, acknowledges that source (device level
  or SW_SET bit) and repeats until CLAIM.valid = 0: ids come out lowest
  first, each exactly once, cpu_irq drops; IRQ_STATUS.CPU sets again while a
  source is pending.
- `interrupt_controller_log_test`: the event log on an 8- or 5-word ring,
  sources toggling with random hold times under four AXI back-pressure
  settings: every record (address, id, timestamp window, priority, merge),
  LOG_WP = records written, every edge recorded once quiet; several sources
  rising in the same clock are written lowest id first; LOG_WORDS lowered
  below the stored slot restarts the ring at slot 0; LOG_EN 0 writes
  nothing; no AXI read, AXI ID 10, single-beat writes.
- `interrupt_controller_err_test`: ring in a SLVERR region: LOG_ERR
  interrupt, the word stays untouched, LOG_WP still counts; a clean ring
  after it works.
*/

class intc_model extends uvm_component;
  `uvm_component_utils(intc_model)
  virtual ssv_apb_if                   apb;
  virtual interrupt_controller_pins_if pins;
  uvm_reg_block                        rm;
  ssv_base_test                        tb;
  bit [11:0] a_en, a_sw, a_lctrl, a_lbase, a_pend, a_claim, a_state;
  int        b_cpu, b_len, b_lwords;
  bit [31:0] en, sw, lbase, pend_q; bit log_en; bit [15:0] lwords;
  longint    ts;                    // the IP's timestamp in the current clock
  longint    edges[32][$];          // unrecorded edges: the clock of each
  int unsigned n_edges, pin_errors, n_reads;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function bit [11:0] off(string n);
    return rm.get_reg_by_name(n).get_address();
  endfunction

  function void setup();
    uvm_reg st = rm.get_reg_by_name("STATE");
    a_en = off("ENABLE"); a_sw = off("SW_SET"); a_lctrl = off("LOG_CTRL"); a_lbase = off("LOG_BASE");
    a_pend = off("PENDING"); a_claim = off("CLAIM"); a_state = st.get_address();
    b_cpu = st.get_field_by_name("cpu_irq").get_lsb_pos();
    b_len = rm.get_reg_by_name("LOG_CTRL").get_field_by_name("log_en").get_lsb_pos();
    b_lwords = rm.get_reg_by_name("LOG_CTRL").get_field_by_name("log_words").get_lsb_pos();
  endfunction

  function bit [31:0] pending();
    return (pins.irq_src | sw) & en;
  endfunction

  static function bit [31:0] claim_of(bit [31:0] p);
    for (int i = 0; i < 32; i++) if (p[i]) return {1'b1, 26'd0, 5'(i)};
    return 0;
  endfunction

  function bit waiting_before(int id, longint t);
    return edges[id].size() > 0 && edges[id][0] <= t;
  endfunction

  function void reset();
    en = 0; sw = 0; lbase = 0; log_en = 0; lwords = 0; pend_q = 0; ts = 0;
    foreach (edges[i]) edges[i].delete();
  endfunction

  task run_phase(uvm_phase phase);
    reset();
    forever begin
      bit [31:0] p, f; bit wr, rd; bit [11:0] a; bit [31:0] d; bit [3:0] s;
      @(posedge apb.pclk);
      if (!apb.presetn) begin reset(); continue; end
      p = pending();
      if (pins.cpu_irq !== |p) begin
        pin_errors++;
        if (pin_errors <= 5)
          tb.sb_check(0, $sformatf("cpu_irq pin %0b, model %0b (PENDING %08h)", pins.cpu_irq, |p, p));
      end
      wr = apb.psel && apb.penable && apb.pready && apb.pwrite;
      rd = apb.psel && apb.penable && apb.pready && !apb.pwrite;
      a = apb.paddr; d = apb.pwdata; s = apb.pstrb;
      if (rd) begin
        if (a == a_pend)  begin tb.check_eq(apb.prdata, p, "PENDING"); n_reads++; end
        if (a == a_claim) begin tb.check_eq(apb.prdata, claim_of(p), "CLAIM"); n_reads++; end
        if (a == a_state) tb.sb_check(apb.prdata[b_cpu] == |p, "STATE.cpu_irq");
      end
      // edges of this clock ask for a record when the log is on
      if (log_en) begin
        f = p & ~pend_q;
        for (int i = 0; i < 32; i++) if (f[i]) begin edges[i].push_back(ts); n_edges++; end
      end else
        foreach (edges[i]) edges[i].delete();
      pend_q = p;
      ts++;
      if (wr) begin
        bit [31:0] lc = (32'(lwords) << b_lwords) | (32'(log_en) << b_len);
        if (a == a_en)    en    = timer_wdt_merge(en, d, s);
        if (a == a_sw)    sw    = timer_wdt_merge(sw, d, s);
        if (a == a_lbase) lbase = timer_wdt_merge(lbase, d, s);
        if (a == a_lctrl) begin lc = timer_wdt_merge(lc, d, s); log_en = lc[b_len]; lwords = 16'(lc >> b_lwords); end
      end
    end
  endtask

  static function bit [31:0] timer_wdt_merge(bit [31:0] old, bit [31:0] d, bit [3:0] s);
    for (int i = 0; i < 4; i++) if (s[i]) old[8*i +: 8] = d[8*i +: 8];
    return old;
  endfunction

  function int unsigned unrecorded();
    int unsigned n = 0;
    foreach (edges[i]) n += edges[i].size();
    return n;
  endfunction
endclass

class interrupt_controller_job_base_test extends interrupt_controller_base_test;
  `uvm_component_utils(interrupt_controller_job_base_test)
  intc_model   model;
  bit [31:0]   src;               // level of every source as this test drives it
  int unsigned rec_seen;
  int unsigned ring_slot;     // the IP's stored ring slot (reset: 0)

  // slot of the next record: 0 when the ring was lowered below the stored
  // slot; the stored slot then moves on from the slot used
  function int unsigned next_slot(int unsigned words);
    int unsigned ws = (ring_slot >= words) ? 0 : ring_slot;
    ring_slot = (ws + 1 >= words) ? 0 : ws + 1;
    return ws;
  endfunction

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    model = intc_model::type_id::create("model", this);
    model.tb = this;
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    model.apb = apb_vif; model.pins = pins; model.rm = rm;
    model.setup();
  endfunction

  task set_src(bit [31:0] v);
    @(negedge pins.clk);
    src = v; pins.irq_src = v;
  endtask

  task log_ctrl(bit en, bit [15:0] words);
    wr_fields("LOG_CTRL", '{"log_en", "log_words"}, '{en, words});
  endtask

  // every record written since the last call
  task check_records(bit [31:0] base, bit [15:0] words, string when, bit allow_err = 0);
    while (env.axi.mon.completed.size() > 0) begin
      axim_txn t = env.axi.mon.completed.pop_front();
      bit [31:0] exp_a = base + 4 * next_slot(words);
      bit [4:0] id = t.data[0][4:0];
      longint T = t.data[0][31:8];
      sb_check(t.write && t.beats() == 1, $sformatf("%s: record burst %s", when, t.convert2string()));
      check_eq(t.addr, exp_a, $sformatf("%s: record %0d address", when, rec_seen));
      check_eq(t.data[0][7:5], 0, $sformatf("%s: record %0d bits 7:5", when, rec_seen));
      if (!allow_err) check_eq(t.resp[0], AXI_OKAY, $sformatf("%s: record %0d response", when, rec_seen));
      sb_check(model.waiting_before(id, T - 2),
               $sformatf("%s: record %0d (id %0d, ts %0d) without an unrecorded edge of id %0d by clock %0d",
                         when, rec_seen, id, T, id, T - 2));
      for (int j = 0; j < id; j++)
        sb_check(!model.waiting_before(j, T - 2),
                 $sformatf("%s: record %0d is id %0d while id %0d waited since clock %0d", when, rec_seen, id,
                           j, model.edges[j].size() ? model.edges[j][0] : -1));
      while (model.edges[id].size() > 0 && model.edges[id][0] <= T - 2) void'(model.edges[id].pop_front());
      rec_seen++;
    end
  endtask

  // let the log drain, then check it all
  task drain(bit [31:0] base, bit [15:0] words, string when, bit allow_err = 0);
    bit [31:0] v;
    int unsigned n = 0;
    do begin clocks(40); check_records(base, words, when, allow_err); n++; end
    while (model.unrecorded() != 0 && n < 200);
    sb_check(model.unrecorded() == 0, $sformatf("%s: %0d edges never recorded", when, model.unrecorded()));
    clocks(4);   // LOG_WP counts a record two clocks after its B handshake
    check_records(base, words, when, allow_err);
    rd_field("STATE", "log_wp", v);
    check_eq(v, rec_seen & 16'hFFFF, {when, ": STATE.log_wp = records on AXI"});
  endtask
endclass

// testlist: interrupt_controller_pend_test 3
class interrupt_controller_pend_test extends interrupt_controller_job_base_test;
  `uvm_component_utils(interrupt_controller_pend_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] v, st;
    phase.raise_objection(this);
    wait_reset();
    set_src(0);
    // ---- random levels, enables and software interrupts
    for (int i = 0; i < 120; i++) begin
      case ($urandom_range(0, 5))
        0: wr("ENABLE", (i < 10) ? 32'hFFFF_FFFF : $urandom());
        1: wr("SW_SET", $urandom() & $urandom());
        2: rd("PENDING", v);
        3: rd("CLAIM", v);
        4: rd("STATE", v);
        default: set_src($urandom() & $urandom() & $urandom());
      endcase
      clocks($urandom_range(0, 20));
    end
    // ---- interrupt service loop
    wr("SW_SET", 0); set_src(0);
    wr("ENABLE", 32'hFFFF_FFFF);
    wr("IRQ_ENABLE", 32'h1 << irq_bit("CPU"));
    rd("IRQ_STATUS", st); clear_irq(st);
    for (int r = 0; r < 20; r++) begin
      bit [31:0] dev = $urandom() & $urandom(), swv = $urandom() & $urandom() & $urandom() & ~dev, want;
      int last = -1, served = 0;
      if (r == 0) begin dev = 32'h8000_0001; swv = 32'h0000_0100; end
      if (dev == 0 && swv == 0) dev = 32'h0040_0000;
      want = dev | swv;
      wr("SW_SET", swv);
      set_src(dev);
      wait_irq(st, $sformatf("isr %0d", r));
      forever begin
        rd("CLAIM", v);
        if (!v[31]) break;
        sb_check(int'(v[4:0]) > last, $sformatf("isr %0d: CLAIM %0d after %0d", r, v[4:0], last));
        sb_check(want[v[4:0]], $sformatf("isr %0d: CLAIM %0d was not raised", r, v[4:0]));
        last = v[4:0]; want[v[4:0]] = 0; served++;
        if (dev[v[4:0]]) begin dev[v[4:0]] = 0; set_src(dev); end
        else begin swv[v[4:0]] = 0; wr("SW_SET", swv); end
        clocks(2);
        sb_check(served < 40, "service loop does not end");
        if (served >= 40) break;
      end
      check_eq(want, 0, $sformatf("isr %0d: sources left unserved", r));
      clocks(2);
      rd("IRQ_STATUS", st);
      clear_irq(st);
      clocks(3);
      rd("IRQ_STATUS", st);
      sb_check(!st[irq_bit("CPU")], $sformatf("isr %0d: IRQ_STATUS.CPU sets again with nothing pending", r));
    end
    // ---- CPU is a level: it sets again while a source stays pending
    set_src(32'h0000_0010);
    clocks(3);
    rd("IRQ_STATUS", st); clear_irq(st); clocks(3);
    rd("IRQ_STATUS", st);
    sb_check(st[irq_bit("CPU")], "IRQ_STATUS.CPU does not set again while a source is pending");
    set_src(0); clocks(3);
    rd("IRQ_STATUS", st); clear_irq(st);
    sb_check(model.n_reads > 40, $sformatf("only %0d PENDING / CLAIM reads", model.n_reads));
    sb_check(env.axi.mon.n_wr == 0 && env.axi.mon.n_rd == 0, "AXI traffic with the log off");
    phase.drop_objection(this);
  endtask
endclass

// testlist: interrupt_controller_log_test 3
class interrupt_controller_log_test extends interrupt_controller_job_base_test;
  `uvm_component_utils(interrupt_controller_log_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // one toggling phase: sources flip with random hold times
  task toggle(int unsigned clks, bit [31:0] mask);
    int unsigned hold[32];
    foreach (hold[i]) hold[i] = $urandom_range(1, 60);
    repeat (clks) begin
      bit [31:0] nv = src;
      foreach (hold[i]) if (mask[i]) begin
        if (hold[i] == 0) begin nv[i] = ~nv[i]; hold[i] = $urandom_range(2, 80); end
        else hold[i]--;
      end
      set_src(nv);
    end
  endtask

  task run_phase(uvm_phase phase);
    bit [31:0] base; bit [15:0] words; bit [31:0] v;
    phase.raise_objection(this);
    wait_reset();
    set_src(0);
    wr("ENABLE", 32'hFFFF_FFFF);
    // the ring size stays the same within a run (the slot carries over
    // from phase to phase); it is 8 or 5 words depending on the seed
    words = $urandom_range(0, 1) ? 5 : 8;
    for (int ph = 0; ph < 8; ph++) begin
      base  = 32'h3000_0000 + 32'h1000 * ph;
      backpressure(ph);
      env.axi_cfg.clear_windows();
      env.axi_cfg.add_window(base, base + 4 * words, 0, 1, "ring");
      env.axi_cfg.check_windows = 1;
      wr("LOG_BASE", base);
      log_ctrl(1, words);
      toggle(600, (ph < 4) ? 32'h0000_FFFF : 32'hFFFF_FFFF);
      set_src(0);
      drain(base, words, $sformatf("phase %0d", ph));
      log_ctrl(0, words);
    end
    // ---- several sources rising in the same clock: lowest id first
    wr("LOG_BASE", 32'h3800_0000);
    log_ctrl(1, words);
    env.axi_cfg.clear_windows();
    env.axi_cfg.add_window(32'h3800_0000, 32'h3800_0000 + 4 * words, 0, 1, "ring");
    env.axi_cfg.set_backpressure(100, 0);
    begin
      int n0 = env.axi.mon.completed.size();
      bit [31:0] ids = 32'h8421_0A06;
      set_src(ids);
      clocks(200);
      sb_check(env.axi.mon.completed.size() - n0 == $countones(ids),
               $sformatf("%0d records for %0d simultaneous edges", env.axi.mon.completed.size() - n0, $countones(ids)));
      for (int k = 1; k < env.axi.mon.completed.size(); k++)
        sb_check(env.axi.mon.completed[k].data[0][4:0] > env.axi.mon.completed[k-1].data[0][4:0],
                 "simultaneous edges not written lowest id first");
      drain(32'h3800_0000, words, "simultaneous");
    end
    set_src(0);
    // ---- ring lowered below the stored slot: the next record goes to slot 0
    // and nothing is written past the new ring
    clocks(5);
    while (ring_slot < 3) begin
      set_src(32'h1); clocks(3); set_src(0);
      drain(32'h3800_0000, words, "fill to slot 3");
    end
    env.axi_cfg.clear_windows();
    env.axi_cfg.add_window(32'h3C00_0000, 32'h3C00_0008, 0, 1, "ring of 2");
    wr("LOG_BASE", 32'h3C00_0000);
    log_ctrl(1, 2);
    for (int k = 0; k < 5; k++) begin
      int unsigned slot_was = ring_slot;
      set_src(32'h1 << k); clocks(3); set_src(0);
      drain(32'h3C00_0000, 2, $sformatf("ring lowered to 2, record %0d (stored slot %0d)", k, slot_was));
    end
    // ---- LOG_EN 0: nothing written
    log_ctrl(0, words);
    clocks(5);
    begin
      int unsigned n0 = env.axi.mon.n_wr;
      toggle(300, 32'hFFFF_FFFF);
      set_src(0); clocks(20);
      check_eq(env.axi.mon.n_wr - n0, 0, "writes with LOG_EN 0");
    end
    sb_check(env.axi.mon.n_rd == 0, "the interrupt controller issued a read");
    sb_check(model.n_edges > 300, $sformatf("only %0d logged edges", model.n_edges));
    phase.drop_objection(this);
  endtask
endclass

// testlist: interrupt_controller_err_test 2
class interrupt_controller_err_test extends interrupt_controller_job_base_test;
  `uvm_component_utils(interrupt_controller_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] st;
    phase.raise_objection(this);
    wait_reset();
    set_src(0);
    env.axi_cfg.add_err_region(32'h3000_0000, 32'h3000_0010, AXI_SLVERR);
    for (int i = 0; i < 4; i++) mem().wr32(32'h3000_0000 + 4 * i, 32'hDEAD_0000 + i);
    wr("ENABLE", 32'hFFFF_FFFF);
    wr("LOG_BASE", 32'h3000_0000);
    log_ctrl(1, 4);
    wr("IRQ_ENABLE", 32'h1 << irq_bit("LOG_ERR"));
    rd("IRQ_STATUS", st); clear_irq(st);
    set_src(32'h0000_0003);
    wait_irq(st, "log error");
    sb_check(st[irq_bit("LOG_ERR")], "LOG_ERR not set");
    clear_irq(st);
    set_src(0);
    drain(32'h3000_0000, 4, "error ring", 1);
    for (int i = 0; i < 4; i++) check_eq(mem().rd32(32'h3000_0000 + 4 * i), 32'hDEAD_0000 + i, "record written into SLVERR");
    // clean ring: the slot carries on
    log_ctrl(0, 4);
    wr("LOG_BASE", 32'h3400_0000);
    log_ctrl(1, 4);
    rd("IRQ_STATUS", st); clear_irq(st);
    set_src(32'h0000_0030);
    clocks(100);
    set_src(0);
    drain(32'h3400_0000, 4, "clean ring");
    rd("IRQ_STATUS", st);
    sb_check(!st[irq_bit("LOG_ERR")], "LOG_ERR on a clean ring");
    phase.drop_objection(this);
  endtask
endclass
