// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// audio_dsp_tests.svh -- Audio_DSP-UVM-VIP functional tests (included by
// audio_dsp_pkg.sv).
// Reference model (open-ip-portfolio specs/Audio_DSP.json features):
//   one stereo frame per word: left = bits 15:0, right = bits 31:16, signed;
//   CTRL.mix 1: both channels take (L + R) >>> 1 (17-bit sum);
//   y = sat16((x * GAIN) >>> 8), GAIN_L / GAIN_R signed Q8.8 (256 = 0 dB);
//   CTRL.mute 1: y = 0 (no clip counted);
//   METER.peak = largest |y| of the job (|-32768| = 0x8000);
//   METER.clips = saturated output samples (saturating at 0xFFFF).
/* TEST PLAN
- `audio_dsp_gain_test`: 32 jobs: gains 0 dB, -6 dB, +6 dB, x0, -1 (phase
  invert), the extremes 0x7FFF and 0x8000, and random; random PCM with full
  scale and near-full-scale frames mixed in so clipping happens both ways;
  lengths 0, 1, 16, 17 and random up to 600 frames; four back-pressure
  settings. Checks every output frame, METER.peak and METER.clips, STATUS,
  DONE / ERR, read / write word counts and windows, AXI ID 8.
- `audio_dsp_mix_mute_test`: mono downmix with equal and different channel
  gains (both channels must come from (L + R) >>> 1, including the odd-sum
  rounding toward minus infinity and L = R = -32768), and mute (output 0,
  peak 0, clips 0, even with gains that would clip).
- `audio_dsp_err_test`: SLVERR in the source (those frames read as 0 and give
  0 out), DECERR in the destination (frames untouched): DONE + ERR,
  STATUS.err; the next clean job clears it.
*/

class audio_dsp_job_base_test extends audio_dsp_base_test;
  `uvm_component_utils(audio_dsp_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    job_fcov_bins();
    fcov_bins("mix", '{"stereo", "mono_mix"});
    fcov_bins("mute", '{"off", "on"});
    fcov_bins("gain", '{"zero", "negative", "below_unity", "unity", "above_unity"});
    fcov_bins("saturation", '{"none", "clipped"});
  endfunction

  static function void dsp(bit [31:0] in[$], bit [15:0] gl, bit [15:0] gr, bit mix, bit mute,
                           ref bit [31:0] out[$], output bit [15:0] peak, output int unsigned clips);
    out.delete(); peak = 0; clips = 0;
    foreach (in[i]) begin
      int x[2], g[2], y[2];
      bit [31:0] o;
      x[0] = $signed(in[i][15:0]);
      x[1] = $signed(in[i][31:16]);
      if (mix) begin
        int m = x[0] + x[1];
        m = (m >= 0) ? (m / 2) : -((-m + 1) / 2);      // arithmetic shift: floor
        x[0] = m; x[1] = m;
      end
      g[0] = $signed(gl); g[1] = $signed(gr);
      for (int c = 0; c < 2; c++) begin
        longint p = longint'(x[c]) * longint'(g[c]);
        p = (p >= 0) ? (p / 256) : -((-p + 255) / 256);  // >>> 8: floor
        if (mute) y[c] = 0;
        else if (p > 32767) begin y[c] = 32767; clips++; end
        else if (p < -32768) begin y[c] = -32768; clips++; end
        else y[c] = int'(p);
        o[16*c +: 16] = 16'(y[c]);
        if (((y[c] < 0) ? -y[c] : y[c]) > peak) peak = 16'((y[c] < 0) ? -y[c] : y[c]);
      end
      out.push_back(o);
    end
    if (clips > 32'hFFFF) clips = 32'hFFFF;
  endfunction

  task job(string tag, bit [31:0] src, bit [31:0] dst, int unsigned len, bit [15:0] gl, bit [15:0] gr,
           bit mix, bit mute);
    bit [31:0] in[$], out[$], v; bit rerr; bit [15:0] pk; int unsigned cl;
    job_input(src, len, in, rerr);
    dsp(in, gl, gr, mix, mute, out, pk, cl);
    fcov("mix", mix ? "mono_mix" : "stereo");
    fcov("mute", mute ? "on" : "off");
    for (int c = 0; c < 2; c++) begin
      bit [15:0] g = c ? gr : gl;
      fcov("gain", (g == 0) ? "zero" : g[15] ? "negative" : (g < 16'h0100) ? "below_unity" :
                   (g == 16'h0100) ? "unity" : "above_unity");
    end
    fcov("saturation", (cl != 0) ? "clipped" : "none");
    wr("GAIN", {gr, gl});
    wr("CTRL", {30'h0, mute, mix});
    run_job(tag, src, dst, len, out, rerr);
    rd_field("METER", "peak", v);
    check_eq(v, pk, {tag, " METER.peak"});
    rd_field("METER", "clips", v);
    check_eq(v, cl, {tag, " METER.clips"});
  endtask

  // random PCM with a share of full-scale and near-full-scale samples
  function void pcm(bit [31:0] base, int unsigned len, ref bit [31:0] w[$]);
    bit [15:0] edge_s[6] = '{16'h7FFF, 16'h8000, 16'h7FFE, 16'h8001, 16'h0000, 16'hFFFF};
    w.delete();
    for (int unsigned i = 0; i < len; i++) begin
      bit [15:0] l = $urandom(), r = $urandom();
      if ($urandom_range(4) == 0) l = edge_s[$urandom_range(5)];
      if ($urandom_range(4) == 0) r = edge_s[$urandom_range(5)];
      w.push_back({r, l});
    end
    mem().load_words(base, w);
  endfunction
endclass

// testlist: audio_dsp_gain_test 3
class audio_dsp_gain_test extends audio_dsp_job_base_test;
  `uvm_component_utils(audio_dsp_gain_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [15:0] gains[$] = '{16'd256, 16'd128, 16'd512, 16'd0, 16'hFF00, 16'h7FFF, 16'h8000};
    int unsigned lens[$] = '{0, 1, 16, 17};
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 32; i++) begin
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 600);
      bit [15:0] gl = (i < gains.size()) ? gains[i] : $urandom();
      bit [15:0] gr = (i < gains.size()) ? gains[gains.size() - 1 - i] : $urandom_range(0, 1023);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0001_0000, len);
      bit [31:0] dst = rand_addr(32'h2000_0000, 32'h0001_0000, len);
      backpressure(i);
      pcm(src, len, w);
      job($sformatf("job %0d len=%0d gain=%04h/%04h", i, len, gl, gr), src, dst, len, gl, gr, 0, 0);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: audio_dsp_mix_mute_test 2
class audio_dsp_mix_mute_test extends audio_dsp_job_base_test;
  `uvm_component_utils(audio_dsp_mix_mute_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    // directed downmix corner frames: odd sums (both signs), both full scale
    w = '{32'h0001_0000, 32'hFFFF_0000, 32'h8000_8000, 32'h7FFF_7FFF, 32'h8000_7FFF, 32'h0003_FFFE};
    mem().load_words(32'h1000_0000, w);
    job("mix corners", 32'h1000_0000, 32'h2000_0000, w.size(), 16'd256, 16'd256, 1, 0);
    for (int i = 0; i < 12; i++) begin
      int unsigned len = $urandom_range(1, 400);
      backpressure(i);
      pcm(32'h1000_1000, len, w);
      job($sformatf("mix %0d", i), 32'h1000_1000, 32'h2000_4000, len, $urandom_range(0, 1024), $urandom(), 1, 0);
      job($sformatf("mute %0d", i), 32'h1000_1000, 32'h2000_8000, len, 16'h7FFF, 16'h7FFF, i % 2, 1);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: audio_dsp_err_test 2
class audio_dsp_err_test extends audio_dsp_job_base_test;
  `uvm_component_utils(audio_dsp_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0040, 32'h1000_0080, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0140, AXI_DECERR);
    pcm(32'h1000_0000, 256, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hFACE_0000 + i);
    job("read error", 32'h1000_0000, 32'h2400_0000, 64, 16'd300, 16'd200, 0, 0);
    job("write error", 32'h1000_0200, 32'h2000_0000, 128, 16'd256, 16'd256, 1, 0);
    job("clean", 32'h1000_0200, 32'h2800_0000, 30, 16'd256, 16'd256, 0, 0);
    phase.drop_objection(this);
  endtask
endclass
