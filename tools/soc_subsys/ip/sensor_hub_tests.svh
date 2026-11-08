// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// sensor_hub_tests.svh -- Sensor_Hub-UVM-VIP functional tests (included by
// sensor_hub_pkg.sv).
// Reference model (open-ip-portfolio specs/Sensor_Hub.json features):
//   16-bit unsigned samples arrive on sns_valid / sns_data and are taken only
//   while the job still needs words;
//   avg = (sum of 2^AVG_LOG2 consecutive samples) >> AVG_LOG2, two averages
//   per word, the first in bits 15:0; LEN words are written at DST; a word
//   that finds the write FIFO full is dropped and counted in SAMPLE.drops;
//   WAKE fires when an average > THRESHOLD and WAKE_EN is 1, at most once per
//   job; SAMPLE.last_avg = the latest average.
// sensor_hub_stream drives the samples (every clock, or with random gaps)
// and records, clock by clock, what it offered; the test replays that record
// through the model from the clock the job starts (two clocks after the CMD
// write), so the expected words are exact.
/* TEST PLAN
- `sensor_hub_avg_test`: 20 jobs: AVG_LOG2 0..7, samples random, full scale
  0xFFFF (the 23-bit sum must not overflow at 128 x 0xFFFF), ramps; sensor
  valid every clock and with 50 % gaps; LEN 1, 16, 17 and random up to 300;
  no AXI back-pressure (no drops): every word, last_avg, drops = 0, STATUS,
  DONE / ERR, no AXI read, AXI ID 9.
- `sensor_hub_wake_test`: WAKE_EN 0 never wakes; WAKE_EN 1 wakes exactly once
  per job when an average crosses THRESHOLD (and not when the averages stay
  at or below it, including an average exactly at THRESHOLD),
  IRQ_STATUS.WAKE against the model.
- `sensor_hub_drop_test`: heavy AXI back-pressure with a sample every clock:
  words that find the FIFO full are dropped; the words written are, in
  order, a subsequence of the words formed, formed = LEN + drops, and drops
  = SAMPLE.drops > 0.
- `sensor_hub_err_test`: words written into a SLVERR region (untouched):
  DONE + ERR, STATUS.err; a clean job clears it.
*/

class sensor_hub_stream extends uvm_component;
  `uvm_component_utils(sensor_hub_stream)
  virtual sensor_hub_pins_if pins;
  virtual ssv_apb_if apb;
  bit [11:0]   cmd_addr;
  int unsigned gap_pct = 0;
  int unsigned kind = 0;           // 0 random, 1 full scale, 2 ramp, 3 low (below any threshold), 4 step up after 40, 5 constant 500
  longint      cyc, start_cyc = -1;
  bit [15:0]   offered[$];         // sample offered in each clock since the job started (valid only)
  int unsigned n_shown;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function bit [15:0] next_sample();
    n_shown++;
    case (kind)
      1: return 16'hFFFF;
      2: return 16'(n_shown * 37);
      3: return 16'($urandom_range(0, 100));
      4: return (n_shown < 40) ? 16'($urandom_range(0, 100)) : 16'($urandom_range(900, 1000));
      5: return 16'd500;                 // every average is exactly 500
      default: return 16'($urandom());
    endcase
  endfunction

  task run_phase(uvm_phase phase);
    pins.sns_valid = 0; pins.sns_data = 0;
    forever begin
      @(posedge pins.clk);
      cyc++;
      if (apb.psel && apb.penable && apb.pready && apb.pwrite && apb.paddr == cmd_addr && apb.pwdata[0]) begin
        start_cyc = cyc + 2;           // the core is busy from two edges on
        offered.delete();
        n_shown = 0;
      end
      if (start_cyc >= 0 && cyc >= start_cyc && pins.sns_valid) offered.push_back(pins.sns_data);
      @(negedge pins.clk);
      if (axim_pct(100 - gap_pct)) begin pins.sns_valid = 1; pins.sns_data = next_sample(); end
      else pins.sns_valid = 0;
    end
  endtask
endclass

class sensor_hub_job_base_test extends sensor_hub_base_test;
  `uvm_component_utils(sensor_hub_job_base_test)
  sensor_hub_stream sns;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    sns = sensor_hub_stream::type_id::create("sns", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    sns.pins = pins; sns.apb = apb_vif;
    sns.cmd_addr = r("CMD").get_address();
  endfunction

  // words formed from the offered samples until `len` words (no drops)
  static function void model(bit [15:0] s[$], int unsigned k, int unsigned len, int unsigned max_words,
                             bit wake_en, bit [15:0] thr, ref bit [31:0] words[$], output bit [15:0] last_avg,
                             output int wake_at);
    longint unsigned acc = 0; int unsigned cnt = 0; bit half = 0; bit [15:0] lo;
    words.delete(); wake_at = -1; last_avg = 0;
    foreach (s[i]) begin
      if (words.size() >= max_words) break;
      acc += s[i]; cnt++;
      if (cnt == (1 << k)) begin
        bit [15:0] avg = 16'(acc >> k);
        last_avg = avg;
        if (wake_en && wake_at < 0 && avg > thr) wake_at = i;
        if (!half) lo = avg; else words.push_back({avg, lo});
        half = ~half; acc = 0; cnt = 0;
      end
    end
  endfunction

  task job(string tag, bit [31:0] dst, int unsigned len, int unsigned k, bit wake_en, bit [15:0] thr,
           bit expect_drops = 0);
    bit [31:0] words[$], v, st, got[$]; bit [15:0] la; int wk; bit rerr = 0;
    int unsigned drops;
    wr_fields("CTRL", '{"avg_log2", "wake_en", "threshold"}, '{k, wake_en, thr});
    wr("IRQ_ENABLE", 0);
    rd("IRQ_STATUS", st); clear_irq(st);
    if (!expect_drops) begin
      // run_job needs the expected words up front: the offered stream is
      // only known afterwards, so start the job by hand here
      wr("DST_ADDR", dst); wr("LEN", len);
      env.axi_cfg.clear_windows();
      env.axi_cfg.add_window(dst, dst + 4 * len, 0, 1, "dst");
      env.axi_cfg.check_windows = 1;
      env.axi.mon.clear(); mem().clear_written();
      wr("IRQ_ENABLE", (32'h1 << irq_bit("DONE")) | (32'h1 << irq_bit("ERR")));
      wr("CMD", 1);
      wait_irq(st, tag);
      sb_check(st[irq_bit("DONE")], {tag, ": DONE not set"});
      clear_irq(st);
      clocks(4);
      model(sns.offered, k, len, len, wake_en, thr, words, la, wk);
      foreach (words[i]) if (env.axi_cfg.resp_for(dst + 4 * i, 1) != AXI_OKAY) begin
        rerr = 1; words[i] = mem().rd32(dst + 4 * i);
      end
      sb_check(st[irq_bit("ERR")] == rerr, {tag, ": ERR"});
      check_words(dst, words, tag);
      sb_check(mem().written_outside(dst, dst + 4 * len) == 0, {tag, ": written outside DST"});
      rd_field("SAMPLE", "last_avg", v);
      check_eq(v, la, {tag, " last_avg"});
      rd_field("SAMPLE", "drops", v);
      check_eq(v, 0, {tag, " drops"});
      rd_field("STATUS", "err", v);
      check_eq(v, rerr, {tag, " STATUS.err"});
      sb_check(st[irq_bit("WAKE")] == (wk >= 0), $sformatf("%s: WAKE=%0d, model %0d", tag, st[irq_bit("WAKE")], wk >= 0));
      env.axi_cfg.check_windows = 0;
    end else begin
      int unsigned j = 0;
      wr("DST_ADDR", dst); wr("LEN", len);
      env.axi.mon.clear(); mem().clear_written();
      wr("IRQ_ENABLE", 32'h1 << irq_bit("DONE"));
      wr("CMD", 1);
      wait_irq(st, tag);
      clear_irq(st);
      clocks(4);
      rd_field("SAMPLE", "drops", v);
      drops = v;
      model(sns.offered, k, len, len + drops, 0, 0, words, la, wk);
      sb_check(words.size() == len + drops, $sformatf("%s: %0d words formed, LEN + drops = %0d", tag, words.size(), len + drops));
      mem().get_words(dst, len, got);
      foreach (got[i]) begin
        while (j < words.size() && words[j] != got[i]) j++;
        sb_check(j < words.size(), $sformatf("%s: written word %0d (%08h) is not the next formed word", tag, i, got[i]));
        j++;
      end
      sb_check(drops > 0, {tag, ": no drop under heavy back-pressure"});
    end
  endtask
endclass

// testlist: sensor_hub_avg_test 3
class sensor_hub_avg_test extends sensor_hub_job_base_test;
  `uvm_component_utils(sensor_hub_avg_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lens[$] = '{1, 16, 17};
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 20; i++) begin
      int unsigned k = i % 8;
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 300 >> (k / 2));
      sns.kind = (i % 5 == 1) ? 1 : (i % 5 == 2) ? 2 : 0;
      sns.gap_pct = (i % 2) ? 50 : 0;
      job($sformatf("avg %0d k=%0d len=%0d kind=%0d", i, k, len, sns.kind),
          rand_addr(32'h2000_0000, 32'h0001_0000, len), len, k, 0, 0);
    end
    sb_check(env.axi.mon.n_rd == 0, "the sensor hub issued a read");
    phase.drop_objection(this);
  endtask
endclass

// testlist: sensor_hub_wake_test 2
class sensor_hub_wake_test extends sensor_hub_job_base_test;
  `uvm_component_utils(sensor_hub_wake_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    sns.gap_pct = 20;
    sns.kind = 4; job("step, wake on", 32'h2000_0000, 60, 2, 1, 16'd500);
    sns.kind = 4; job("step, wake off", 32'h2000_1000, 60, 2, 0, 16'd500);
    sns.kind = 3; job("low, wake on", 32'h2000_2000, 60, 1, 1, 16'd100);   // avg <= 100: never > threshold
    sns.kind = 5; job("avg = threshold: no wake", 32'h2000_5000, 20, 1, 1, 16'd500);
    sns.kind = 5; job("avg = threshold + 1: wake", 32'h2000_6000, 20, 1, 1, 16'd499);
    sns.kind = 1; job("full scale, k=7", 32'h2000_3000, 8, 7, 1, 16'hFFFE);
    sns.kind = 0; job("random, wake once", 32'h2000_4000, 100, 0, 1, 16'h8000);
    phase.drop_objection(this);
  endtask
endclass

// testlist: sensor_hub_drop_test 2
class sensor_hub_drop_test extends sensor_hub_job_base_test;
  `uvm_component_utils(sensor_hub_drop_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    sns.gap_pct = 0; sns.kind = 0;
    env.axi_cfg.set_backpressure(5, 30);
    job("drops", 32'h2000_0000, 200, 0, 0, 0, 1);
    env.axi_cfg.set_backpressure(100, 0);
    job("no drops after", 32'h2000_8000, 50, 1, 0, 0);
    phase.drop_objection(this);
  endtask
endclass

// testlist: sensor_hub_err_test 2
class sensor_hub_err_test extends sensor_hub_job_base_test;
  `uvm_component_utils(sensor_hub_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h2000_0040, 32'h2000_0080, AXI_SLVERR);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'h0F0F_0000 + i);
    job("write error", 32'h2000_0000, 100, 1, 0, 0);
    job("clean", 32'h2800_0000, 30, 1, 0, 0);
    phase.drop_objection(this);
  endtask
endclass
