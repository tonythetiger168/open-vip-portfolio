// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// timer_wdt_tests.svh -- Timer_WDT-UVM-VIP functional tests (included by
// timer_wdt_pkg.sv).
//
// timer_wdt_model is a clock-exact reference model of the tick, timer and
// watchdog (open-ip-portfolio specs/Timer_WDT.json features):
//   tick once every PRESCALE + 1 clocks, COUNT counts ticks; TIMER fires every
//   PERIOD + 1 ticks (CTRL.tmr_en; PERIOD lowered below the running count
//   ends the period at the next tick); WDT_COUNT loads WDT_LOAD, counts down per
//   tick, CMD.kick reloads; at 0 BARK fires and it reloads; at 0 again
//   without a kick wdt_reset goes high until a kick or wdt_en = 0.
// It follows every APB write on the same clock edge as the wrapper (a
// register write or a CMD pulse takes effect in the next clock) and checks,
// every clock, the wdt_reset pin; on every APB read, COUNT, WDT_COUNT,
// WDT_STATE and the TIMER / BARK bits of IRQ_STATUS; and every timestamp
// record the IP writes over AXI: one single-beat write per record, at
// TS_BASE + 4 * (record number mod TS_WORDS), holding the COUNT of a timer
// event, events in order (a record may only be skipped while the previous
// one is still being written, and then TS_MISSED counts it).
/* TEST PLAN
- `timer_wdt_timer_test`: prescale 0, 1, 3, 7 and period 0, 1, 5, 23 with
  timestamp records into an 8- and a 5-word ring, the timer stopped and
  restarted, prescale and PERIOD changed on the fly (also below the
  running count); 12 phases of 600..2500 clocks. The
  model checks COUNT, IRQ_STATUS.TIMER and every record (address, data,
  order); TS_WP + TS_MISSED = recorded events, no record missed with an idle
  bus.
- `timer_wdt_wdt_test`: watchdog with WDT_LOAD 20, 10, 60 and prescale 0 / 2:
  kicked in time for a long run (no BARK, no bite), then left alone: BARK,
  then wdt_reset high one timeout later (pin checked every clock); a kick
  drops wdt_reset; wdt_en = 0 drops it; BARK again after re-enabling.
- `timer_wdt_ts_test`: records under heavy AXI back-pressure with period 0
  (events faster than records): TS_MISSED counts the skipped events and
  TS_WP + TS_MISSED = events; a record into a SLVERR region sets TS_ERR.
  The IP never reads (no AR at all) and writes with ID 11.
*/

class timer_wdt_model extends uvm_component;
  `uvm_component_utils(timer_wdt_model)
  virtual ssv_apb_if        apb;
  virtual timer_wdt_pins_if pins;
  uvm_reg_block             rm;
  ssv_base_test             tb;     // for sb_check()
  // register offsets
  bit [11:0] a_ctrl, a_period, a_tsbase, a_tswords, a_wdtload, a_cmd, a_count, a_wdtcount, a_wdtstate, a_irqst, a_tsstate;
  int        b_timer, b_bark;
  // registers (as the core sees them)
  bit [15:0] prescale; bit tmr_en, ts_en, wdt_en;
  bit [31:0] period, ts_base, wdt_load; bit [15:0] ts_words; bit kick;
  // core state
  bit [15:0] pre; bit [31:0] count, tcnt, wdt_count; bit barked, wdt_reset;
  bit [2:0]  irq_status;
  // events
  bit [31:0] ev_count[$];        // COUNT of every timer event that asked for a record
  int unsigned n_tmr, n_bark, n_bite, n_rec_events;
  int unsigned pin_errors;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function bit [11:0] off(string n);
    return rm.get_reg_by_name(n).get_address();
  endfunction

  function void setup();
    a_ctrl = off("CTRL"); a_period = off("PERIOD"); a_tsbase = off("TS_BASE"); a_tswords = off("TS_WORDS");
    a_wdtload = off("WDT_LOAD"); a_cmd = off("CMD"); a_count = off("COUNT"); a_wdtcount = off("WDT_COUNT");
    a_wdtstate = off("WDT_STATE"); a_irqst = off("IRQ_STATUS"); a_tsstate = off("TS_STATE");
    b_timer = rm.get_reg_by_name("IRQ_STATUS").get_field_by_name("TIMER").get_lsb_pos();
    b_bark  = rm.get_reg_by_name("IRQ_STATUS").get_field_by_name("BARK").get_lsb_pos();
  endfunction

  static function bit [31:0] merge(bit [31:0] old, bit [31:0] d, bit [3:0] s);
    for (int i = 0; i < 4; i++) if (s[i]) old[8*i +: 8] = d[8*i +: 8];
    return old;
  endfunction

  function void reset();
    prescale = 0; tmr_en = 0; ts_en = 0; wdt_en = 0; period = 0; ts_base = 0; wdt_load = 0; ts_words = 0; kick = 0;
    pre = 0; count = 0; tcnt = 0; wdt_count = 0; barked = 0; wdt_reset = 0; irq_status = 0;
  endfunction

  task run_phase(uvm_phase phase);
    bit [31:0] ctrl_r = 0;
    reset();
    forever begin
      bit tick, t_irq, b_irq, wr, rd;
      bit [11:0] a; bit [31:0] d; bit [3:0] s;
      @(posedge apb.pclk);
      if (!apb.presetn) begin reset(); ctrl_r = 0; continue; end
      // ---- compare what the IP shows in this clock (pre-edge values)
      if (pins.wdt_reset !== wdt_reset) begin
        pin_errors++;
        if (pin_errors <= 5)
          tb.sb_check(0, $sformatf("wdt_reset pin %0b, model %0b (COUNT %0d)", pins.wdt_reset, wdt_reset, count));
      end
      wr = apb.psel && apb.penable && apb.pready && apb.pwrite;
      rd = apb.psel && apb.penable && apb.pready && !apb.pwrite;
      a = apb.paddr; d = apb.pwdata; s = apb.pstrb;
      if (rd) begin
        if (a == a_count)     tb.check_eq(apb.prdata, count, "COUNT");
        if (a == a_wdtcount)  tb.check_eq(apb.prdata, wdt_count, "WDT_COUNT");
        if (a == a_wdtstate)  tb.check_eq(apb.prdata, {31'h0, wdt_reset}, "WDT_STATE");
        if (a == a_irqst) begin
          tb.sb_check(apb.prdata[b_timer] == irq_status[0], $sformatf("IRQ_STATUS.TIMER %0b, model %0b", apb.prdata[b_timer], irq_status[0]));
          tb.sb_check(apb.prdata[b_bark] == irq_status[1], $sformatf("IRQ_STATUS.BARK %0b, model %0b", apb.prdata[b_bark], irq_status[1]));
        end
      end
      // ---- the core's next state from this clock's inputs
      tick  = (pre >= prescale);
      t_irq = tmr_en && tick && tcnt >= period;
      b_irq = wdt_en && tick && wdt_count == 0 && !barked && !kick;
      if (t_irq) begin
        n_tmr++;
        if (ts_en && ts_words != 0) begin ev_count.push_back(count); n_rec_events++; end
      end
      if (b_irq) n_bark++;
      pre = tick ? 16'd0 : pre + 16'd1;
      if (!tmr_en) tcnt = 0;
      else if (tick) tcnt = (tcnt >= period) ? 32'd0 : tcnt + 32'd1;
      if (tick) count = count + 1;
      if (!wdt_en) begin wdt_count = wdt_load; barked = 0; wdt_reset = 0; end
      else if (kick) begin wdt_count = wdt_load; barked = 0; wdt_reset = 0; end
      else if (tick) begin
        if (wdt_count == 0) begin
          wdt_count = wdt_load;
          if (barked && !wdt_reset) n_bite++;
          if (barked) wdt_reset = 1;
          barked = 1;
        end else wdt_count = wdt_count - 1;
      end
      // IRQ_STATUS: W1C at this edge, the set of this clock wins
      if (wr && a == a_irqst) irq_status &= ~d[2:0];
      if (t_irq) irq_status[0] = 1;
      if (b_irq) irq_status[1] = 1;
      // ---- register writes take effect in the next clock
      kick = 0;
      if (wr) begin
        if (a == a_ctrl) begin
          ctrl_r = merge(ctrl_r, d, s) & 32'h7_FFFF;
          prescale = ctrl_r[15:0]; tmr_en = ctrl_r[16]; ts_en = ctrl_r[17]; wdt_en = ctrl_r[18];
        end
        if (a == a_period)   period   = merge(period, d, s);
        if (a == a_tsbase)   ts_base  = merge(ts_base, d, s);
        if (a == a_tswords)  ts_words = merge({16'h0, ts_words}, d, s);
        if (a == a_wdtload)  wdt_load = merge(wdt_load, d, s);
        if (a == a_cmd)      kick     = d[0] & s[0];
      end
    end
  endtask
endclass

class timer_wdt_job_base_test extends timer_wdt_base_test;
  `uvm_component_utils(timer_wdt_job_base_test)
  timer_wdt_model model;
  int unsigned    rec_seen;   // records checked so far (slot of the next one)
  int unsigned ring_slot;     // the IP's stored ring slot (reset: 0)

  // slot of the next record: 0 when the ring was lowered below the stored
  // slot; the stored slot then moves on from the slot used
  function int unsigned next_slot(int unsigned words);
    int unsigned ws = (ring_slot >= words) ? 0 : ring_slot;
    ring_slot = (ws + 1 >= words) ? 0 : ws + 1;
    return ws;
  endfunction
  int unsigned    ev_ptr;     // next model event a record may match

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    model = timer_wdt_model::type_id::create("model", this);
    model.tb = this;
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    model.apb = apb_vif; model.pins = pins; model.rm = rm;
    model.setup();
  endfunction

  task ctrl(bit [15:0] prescale, bit tmr_en, bit ts_en, bit wdt_en);
    wr("CTRL", {13'h0, wdt_en, ts_en, tmr_en, prescale});
  endtask

  // check every record written since the last call
  task check_records(bit [31:0] base, bit [15:0] words, string when);
    while (env.axi.mon.completed.size() > 0) begin
      axim_txn t = env.axi.mon.completed.pop_front();
      bit [31:0] exp_a = base + 4 * next_slot(words);
      bit found = 0;
      sb_check(t.write && t.beats() == 1, $sformatf("%s: record burst %s", when, t.convert2string()));
      check_eq(t.addr, exp_a, $sformatf("%s: record %0d address", when, rec_seen));
      // the record holds the COUNT of the oldest event not yet recorded,
      // or of a later one if the ones before it were missed
      while (ev_ptr < model.ev_count.size()) begin
        if (model.ev_count[ev_ptr++] == t.data[0]) begin found = 1; break; end
      end
      sb_check(found, $sformatf("%s: record %0d holds %0d, not the COUNT of a pending timer event", when, rec_seen, t.data[0]));
      rec_seen++;
    end
  endtask

  task ts_state(output bit [31:0] wp, output bit [31:0] missed);
    rd_field("TS_STATE", "ts_wp", wp);
    rd_field("TS_STATE", "ts_missed", missed);
  endtask

  task sample_regs();
    bit [31:0] v;
    rd("COUNT", v); rd("WDT_COUNT", v); rd("WDT_STATE", v); rd("IRQ_STATUS", v);
  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("TMR_MODEL", $sformatf("timer events %0d (record requests %0d), barks %0d, bites %0d, records checked %0d",
                                     model.n_tmr, model.n_rec_events, model.n_bark, model.n_bite, rec_seen), UVM_LOW)
    super.report_phase(phase);
  endfunction
endclass

// testlist: timer_wdt_timer_test 2
class timer_wdt_timer_test extends timer_wdt_job_base_test;
  `uvm_component_utils(timer_wdt_timer_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [15:0] pres[$] = '{0, 1, 3, 7, 0, 2};
    bit [31:0] pers[$] = '{0, 1, 5, 23, 3, 9};
    bit [31:0] wp, missed, v;
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.check_windows = 1;
    env.axi_cfg.add_window(32'h3000_0000, 32'h3000_0020, 0, 1, "ring");
    wr("TS_BASE", 32'h3000_0000);
    wr("TS_WORDS", 8);
    wr("IRQ_ENABLE", 32'h0);
    for (int ph = 0; ph < 12; ph++) begin
      bit [15:0] p = pres[ph % 6];
      wr("PERIOD", pers[(ph * 5) % 6]);
      if (ph == 6) begin
        // stop, then restart the timer: the period counter starts again
        ctrl(p, 0, 1, 0); clocks(37);
      end
      ctrl(p, 1, 1, 0);
      for (int k = 0; k < 6 + ph; k++) begin
        clocks($urandom_range(80, 300));
        sample_regs();
        if (k == 3) begin rd("IRQ_STATUS", v); clear_irq(v); end
      end
      check_records(32'h3000_0000, 8, $sformatf("phase %0d", ph));
    end
    ctrl(0, 0, 0, 0);
    clocks(50);
    check_records(32'h3000_0000, 8, "end");
    ts_state(wp, missed);
    check_eq(wp, rec_seen, "TS_STATE.ts_wp = records seen on AXI");
    check_eq(wp + missed, model.n_rec_events, "TS_WP + TS_MISSED = record requests");
    sb_check(model.n_tmr > 100, $sformatf("only %0d timer events", model.n_tmr));
    sb_check(env.axi.mon.n_rd == 0, "the timer issued a read");
    phase.drop_objection(this);
  endtask
endclass

// testlist: timer_wdt_wdt_test 2
class timer_wdt_wdt_test extends timer_wdt_job_base_test;
  `uvm_component_utils(timer_wdt_wdt_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task wait_pin(bit level, int unsigned max_clk, string what);
    int unsigned n = 0;
    while (pins.wdt_reset !== level && n < max_clk) begin clocks(1); n++; end
    sb_check(pins.wdt_reset === level, $sformatf("%s: wdt_reset not %0b within %0d clocks", what, level, max_clk));
  endtask
  task run_phase(uvm_phase phase);
    bit [31:0] loads[$] = '{20, 10, 60};
    bit [31:0] v;
    phase.raise_objection(this);
    wait_reset();
    wr("IRQ_ENABLE", 32'h1 << irq_bit("BARK"));
    foreach (loads[i]) begin
      bit [15:0] p = (i == 1) ? 2 : 0;
      int unsigned to = (loads[i] + 1) * (p + 1);     // clocks per timeout
      int unsigned b0 = model.n_bark, t0 = model.n_bite;
      wr("WDT_LOAD", loads[i]);
      ctrl(p, 0, 0, 1);
      // kicked in time: no bark
      for (int k = 0; k < 15; k++) begin
        clocks(to / 3);                 // a kick (3 clocks of APB) well inside the timeout
        wr("CMD", 32'h1);
        if (to > 40) sample_regs();
      end
      sb_check(model.n_bark == b0, $sformatf("load %0d: BARK while kicked in time", loads[i]));
      // left alone: bark, then bite
      wait_pin(1, 4 * to + 100, $sformatf("load %0d unkicked", loads[i]));
      sb_check(model.n_bark == b0 + 1 && model.n_bite == t0 + 1,
            $sformatf("load %0d: %0d barks, %0d bites", loads[i], model.n_bark - b0, model.n_bite - t0));
      rd("IRQ_STATUS", v);
      sb_check(v[irq_bit("BARK")], "BARK not in IRQ_STATUS");
      clear_irq(v);
      sample_regs();
      wr("CMD", 32'h1);                 // a kick drops the reset request
      wait_pin(0, 5, "after a kick");
      wait_pin(1, 4 * to + 100, "bite again");
      ctrl(p, 0, 0, 0);                 // disabling drops it too
      wait_pin(0, 5, "after wdt_en = 0");
      clocks(3 * to);
      sb_check(pins.wdt_reset === 1'b0, "wdt_reset while the watchdog is off");
      sample_regs();
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: timer_wdt_ts_test 2
class timer_wdt_ts_test extends timer_wdt_job_base_test;
  `uvm_component_utils(timer_wdt_ts_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] wp, missed, st;
    phase.raise_objection(this);
    wait_reset();
    // events every tick, slow bus: records get missed
    env.axi_cfg.set_backpressure(20, 12);
    wr("TS_BASE", 32'h3000_0100);
    wr("TS_WORDS", 5);
    wr("PERIOD", 0);
    ctrl(1, 1, 1, 0);
    for (int k = 0; k < 10; k++) begin clocks(200); sample_regs(); end
    ctrl(1, 0, 1, 0);
    clocks(200);
    check_records(32'h3000_0100, 5, "back-pressure");
    ts_state(wp, missed);
    sb_check(missed > 0, "no TS_MISSED under back-pressure with an event every tick");
    check_eq(wp, rec_seen, "TS_WP = records seen");
    check_eq(wp + missed, model.n_rec_events, "TS_WP + TS_MISSED = record requests");
    // a record into a SLVERR region: TS_ERR
    env.axi_cfg.set_backpressure(100, 0);
    env.axi_cfg.add_err_region(32'h3000_0100, 32'h3000_0200, AXI_SLVERR);
    wr("IRQ_ENABLE", 32'h1 << irq_bit("TS_ERR"));
    rd("IRQ_STATUS", st); clear_irq(st);
    wr("PERIOD", 50);
    ctrl(0, 1, 1, 0);
    wait_irq(st, "TS_ERR");
    sb_check(st[irq_bit("TS_ERR")], "TS_ERR not set by a record write that got SLVERR");
    ctrl(0, 0, 0, 0);
    clocks(100);
    env.axi.mon.completed.delete();
    sb_check(env.axi.mon.n_rd == 0, "the timer issued a read");
    phase.drop_objection(this);
  endtask
endclass
