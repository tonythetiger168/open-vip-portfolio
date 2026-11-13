// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// isp_tests.svh -- ISP-UVM-VIP functional tests (included by isp_pkg.sv).
// Reference model (open-ip-portfolio specs/ISP.json features): four 8-bit
// pixels per word, byte 0 first; the job writes LEN words at DST;
//   out = min(255, (max(0, p - BLACK) * GAIN) >> 4), GAIN unsigned Q4.4;
//   SRC_SEL 0 test pattern: pixel b of word x of line y = ((4x + b + y) mod 256)
//     ^ SEED, LINE_WORDS words per line (x restarts when x + 1 >= LINE_WORDS);
//   SRC_SEL 1 sensor stream sns_valid / sns_data / sns_ready, one word per
//     beat (sns_ready only while a job can take a word);
//   STAT_SUM = sum of all output pixels of the frame.
// isp_sensor_drv plays a camera sensor: it offers queued words on
// sns_valid / sns_data with random gaps, holds a word until sns_ready, and
// records every word the ISP took; it also flags sns_ready outside a job.
/* TEST PLAN
- `isp_tpg_test`: 24 test-pattern frames: SEED 0, 0xFF and random; BLACK 0,
  255 and random; GAIN 16 (1.0), 0, 1, 255 and random (clipping to 255);
  LINE_WORDS 0, 1, 7, 160 (640 px), 480 (1080p line) and 1920 (8K line),
  lengths that end mid-line; four back-pressure settings. Every output word,
  STAT_SUM, STATUS, DONE / ERR, no AXI read at all, writes inside DST only,
  AXI ID 3.
- `isp_sensor_test`: 16 frames from the sensor stream with the sensor
  sending continuously, in bursts, and with long gaps: the ISP takes exactly
  LEN words (the rest stay queued for the next job), output = the model of
  the words taken in order, STAT_SUM, sns_ready never high outside a job.
- `isp_err_test`: a frame written across a SLVERR and a DECERR region (those
  words untouched): DONE + ERR, STATUS.err; a clean frame clears it.
*/

class isp_sensor_drv extends uvm_component;
  `uvm_component_utils(isp_sensor_drv)
  virtual isp_pins_if pins;
  bit [31:0]   q[$];          // words still to offer
  bit [31:0]   taken[$];      // words the ISP took
  int unsigned gap_pct = 0;   // chance of an idle clock between words
  bit          job_on;        // set by the test while a job may take words
  int unsigned ready_outside;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    pins.sns_valid = 0; pins.sns_data = 0;
    forever begin
      bit hs;
      @(posedge pins.clk);
      hs = pins.sns_valid && pins.sns_ready;
      if (hs) begin
        taken.push_back(pins.sns_data);
        void'(q.pop_front());
      end
      if (pins.sns_ready && !job_on) ready_outside++;
      @(negedge pins.clk);
      if (pins.sns_valid && !hs) ;                    // a shown word stays until it is taken
      else if (q.size() > 0 && axim_pct(100 - gap_pct)) begin
        pins.sns_valid = 1; pins.sns_data = q[0];
      end else
        pins.sns_valid = 0;
    end
  endtask
endclass

class isp_job_base_test extends isp_base_test;
  `uvm_component_utils(isp_job_base_test)
  isp_sensor_drv sns;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    sns = isp_sensor_drv::type_id::create("sns", this);
    job_fcov_bins();
    fcov_bins("source", '{"test_pattern", "sensor"});
    fcov_bins("gain", '{"zero", "below_unity", "unity", "above_unity"});
    fcov_bins("black", '{"zero", "nonzero"});
    fcov_bins("clip", '{"none", "clipped"});
    fcov_bins("line_words", '{"0_whole_frame", "1", "2_159", "160_479_vga", "480_1919_1080p", "1920_up_8k"});
    fcov_bins("sensor_flow", '{"continuous", "gaps", "long_gaps"});
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    sns.pins = pins;
  endfunction

  static function bit [31:0] isp_px(bit [31:0] raw, bit [7:0] black, bit [7:0] gain, ref bit [31:0] sum);
    bit [31:0] o;
    for (int b = 0; b < 4; b++) begin
      int unsigned d = (raw[8*b +: 8] > black) ? raw[8*b +: 8] - black : 0;
      int unsigned g = (d * gain) >> 4;
      o[8*b +: 8] = (g > 255) ? 8'hFF : 8'(g);
      sum += o[8*b +: 8];
    end
    return o;
  endfunction

  static function void tpg(int unsigned len, int unsigned line_words, bit [7:0] seed, ref bit [31:0] raw[$]);
    int unsigned x = 0, y = 0;
    raw.delete();
    for (int unsigned i = 0; i < len; i++) begin
      bit [31:0] w;
      for (int b = 0; b < 4; b++) w[8*b +: 8] = (8'(4 * x) + 8'(b) + 8'(y)) ^ seed;
      raw.push_back(w);
      if (x + 1 >= line_words) begin x = 0; y++; end else x++;
    end
  endfunction

  task frame(string tag, bit sensor, bit [31:0] dst, int unsigned len, int unsigned line_words,
             bit [7:0] seed, bit [7:0] black, bit [7:0] gain);
    bit [31:0] raw[$], exp[$], sum = 0, v;
    if (sensor) begin
      sns.taken.delete();
      sns.job_on = 1;
    end else tpg(len, line_words, seed, raw);
    wr_fields("CTRL", '{"src_sel", "seed", "black", "gain"}, '{sensor, seed, black, gain});
    wr("LINE", line_words);
    if (sensor) begin
      // the words the ISP will take are the next LEN queued ones
      for (int unsigned i = 0; i < len && i < sns.q.size(); i++) raw.push_back(sns.q[i]);
    end
    foreach (raw[i]) exp.push_back(isp_px(raw[i], black, gain, sum));
    fcov("source", sensor ? "sensor" : "test_pattern");
    fcov("gain", (gain == 0) ? "zero" : (gain < 16) ? "below_unity" : (gain == 16) ? "unity" : "above_unity");
    fcov("black", black ? "nonzero" : "zero");
    begin
      bit clipped = 0;
      foreach (raw[i]) for (int b = 0; b < 4; b++)
        if (raw[i][8*b +: 8] > black && ((raw[i][8*b +: 8] - black) * gain) >> 4 > 255) clipped = 1;
      fcov("clip", clipped ? "clipped" : "none");
    end
    if (!sensor)
      fcov("line_words", (line_words == 0) ? "0_whole_frame" : (line_words == 1) ? "1" : (line_words < 160) ? "2_159" :
                         (line_words < 480) ? "160_479_vga" : (line_words < 1920) ? "480_1919_1080p" : "1920_up_8k");
    else fcov("sensor_flow", (sns.gap_pct == 0) ? "continuous" : (sns.gap_pct < 50) ? "gaps" : "long_gaps");
    run_job(tag, 0, dst, len, exp, 0, 0);
    if (sensor) begin
      sns.job_on = 0;
      sb_check(sns.taken.size() == len, $sformatf("%s: the ISP took %0d sensor words, LEN %0d", tag, sns.taken.size(), len));
    end
    rd("STAT_SUM", v);
    check_eq(v, sum, {tag, " STAT_SUM"});
  endtask

  function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    if (sns.ready_outside != 0)
      `uvm_error("ISP_SNS", $sformatf("sns_ready high in %0d clocks outside a job", sns.ready_outside))
  endfunction
endclass

// testlist: isp_tpg_test 3
class isp_tpg_test extends isp_job_base_test;
  `uvm_component_utils(isp_tpg_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lws[$] = '{0, 1, 7, 160, 480, 1920};
    bit [7:0] gains[$] = '{8'd16, 8'd0, 8'd1, 8'd255};
    bit [7:0] blacks[$] = '{8'd0, 8'd255};
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 24; i++) begin
      int unsigned lw = lws[i % lws.size()];
      int unsigned len = (lw >= 160) ? lw * 2 + $urandom_range(1, lw - 1) :
                         (i < 3) ? ((i == 0) ? 9 : (i == 1) ? 16 : 1) : $urandom_range(1, 700);
      bit [7:0] seed = (i == 0) ? 8'h00 : (i == 1) ? 8'hFF : 8'($urandom());
      bit [7:0] black = (i < 2) ? blacks[i] : 8'($urandom_range(0, 64));
      bit [7:0] gain = (i < gains.size()) ? gains[i] : 8'($urandom());
      backpressure(i);
      frame($sformatf("tpg %0d lw=%0d len=%0d g=%0d b=%0d", i, lw, len, gain, black), 0,
            rand_addr(32'h2000_0000, 32'h0004_0000, len), len, lw, seed, black, gain);
    end
    sb_check(env.axi.mon.n_rd == 0, "the ISP issued a read");
    phase.drop_objection(this);
  endtask
endclass

// testlist: isp_sensor_test 3
class isp_sensor_test extends isp_job_base_test;
  `uvm_component_utils(isp_sensor_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 16; i++) begin
      int unsigned len = $urandom_range(1, 500);
      int unsigned extra = $urandom_range(0, 20);
      while (sns.q.size() < len + extra) sns.q.push_back($urandom());
      sns.gap_pct = (i % 3 == 0) ? 0 : (i % 3 == 1) ? 30 : 85;
      backpressure(i);
      frame($sformatf("sensor %0d len=%0d gap=%0d%%", i, len, sns.gap_pct), 1, 32'h2000_0000 + 32'h4000 * (i % 4),
            len, 0, 0, 8'($urandom_range(0, 40)), 8'($urandom_range(8, 64)));
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: isp_err_test 2
class isp_err_test extends isp_job_base_test;
  `uvm_component_utils(isp_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h2000_0040, 32'h2000_0080, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0200, 32'h2000_0210, AXI_DECERR);
    for (int i = 0; i < 256; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'h1234_0000 + i);
    frame("error frame", 0, 32'h2000_0000, 200, 16, 8'h3C, 8'd10, 8'd20);
    frame("clean", 0, 32'h2800_0000, 50, 10, 8'h00, 8'd0, 8'd16);
    phase.drop_objection(this);
  endtask
endclass
