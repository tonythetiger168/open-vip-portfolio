// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// gpu_tests.svh -- GPU-UVM-VIP functional tests (included by gpu_pkg.sv).
// Reference model (open-ip-portfolio specs/GPU.json features): one RGBA8888
// pixel per word, channel c = bits 8c+7:8c;
//   MODE 0 COPY: dst = src;  MODE 1 FILL: dst = COLOR, no reads;
//   MODE 2 BLEND: dst.c = (src.c * A + COLOR.c * (256 - A)) >> 8, A = min(ALPHA, 256);
//   MODE 3 INVERT: dst = {src[31:24], ~src[23:0]};
//   PIXELS = pixels written by the last job.
// Surfaces are LEN pixels long, so any frame size works: the tests use
// line-sized jobs of real resolutions (an 8K line is 7680 pixels).
/* TEST PLAN
- `gpu_ops_test`: 40 jobs cycling COPY / FILL / BLEND / INVERT, ALPHA 0, 1,
  128, 255, 256, 300 (clamped to 256) and random, random COLOR, lengths 1,
  16, 17, random up to 900, and line lengths 640, 1920 and 7680 (8K); four
  back-pressure settings; addresses near 4 KB boundaries. Every output
  pixel, PIXELS, STATUS, DONE / ERR, read / write counts (FILL reads
  nothing), windows, AXI ID 1.
- `gpu_err_test`: COPY from a SLVERR region (those pixels read as 0), BLEND
  into a DECERR region (untouched), FILL across a SLVERR region: DONE + ERR,
  STATUS.err; a clean job clears it.
*/

class gpu_job_base_test extends gpu_base_test;
  `uvm_component_utils(gpu_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  static function bit [31:0] op(bit [1:0] mode, bit [31:0] s, bit [31:0] color, int unsigned alpha);
    bit [31:0] o;
    int unsigned a = (alpha > 256) ? 256 : alpha;
    case (mode)
      0: o = s;
      1: o = color;
      2: for (int c = 0; c < 4; c++) o[8*c +: 8] = 8'((s[8*c +: 8] * a + color[8*c +: 8] * (256 - a)) >> 8);
      3: o = {s[31:24], ~s[23:0]};
    endcase
    return o;
  endfunction

  task job(string tag, bit [1:0] mode, bit [31:0] src, bit [31:0] dst, int unsigned len,
           bit [31:0] color, int unsigned alpha);
    bit [31:0] in[$], exp[$], v; bit rerr = 0;
    if (mode != 1) job_input(src, len, in, rerr);
    for (int unsigned i = 0; i < len; i++) exp.push_back(op(mode, (mode == 1) ? 32'h0 : in[i], color, alpha));
    wr_fields("CTRL", '{"mode", "alpha"}, '{mode, alpha});
    wr("COLOR", color);
    run_job(tag, src, dst, len, exp, rerr, (mode == 1) ? 0 : len);
    rd("PIXELS", v);
    check_eq(v, len, {tag, " PIXELS"});
  endtask
endclass

// testlist: gpu_ops_test 3
class gpu_ops_test extends gpu_job_base_test;
  `uvm_component_utils(gpu_ops_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned alphas[$] = '{0, 1, 128, 255, 256, 300};
    int unsigned lens[$] = '{1, 16, 17, 640, 1920, 7680};
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 40; i++) begin
      bit [1:0] mode = i % 4;
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 900);
      int unsigned alpha = (i < alphas.size()) ? alphas[i] : $urandom_range(0, 511);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0004_0000, len);
      bit [31:0] dst = rand_addr(32'h2000_0000, 32'h0004_0000, len);
      if (i < 6) mode = 2;   // the alpha corners with BLEND
      backpressure(i);
      if (mode != 1) fill_random(src, len, w);
      job($sformatf("job %0d mode=%0d len=%0d alpha=%0d", i, mode, len, alpha), mode, src, dst, len, $urandom(), alpha);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: gpu_err_test 2
class gpu_err_test extends gpu_job_base_test;
  `uvm_component_utils(gpu_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0040, 32'h1000_0080, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0140, AXI_DECERR);
    env.axi_cfg.add_err_region(32'h3000_0200, 32'h3000_0280, AXI_SLVERR);
    fill_random(32'h1000_0000, 512, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hABCD_0000 + i);
    job("copy read error", 0, 32'h1000_0000, 32'h2400_0000, 64, 0, 0);
    job("blend write error", 2, 32'h1000_0400, 32'h2000_0000, 128, 32'h8040_2010, 100);
    job("fill write error", 1, 0, 32'h3000_0100, 128, 32'h1122_3344, 0);
    job("clean", 3, 32'h1000_0400, 32'h2800_0000, 50, 0, 0);
    phase.drop_objection(this);
  endtask
endclass
