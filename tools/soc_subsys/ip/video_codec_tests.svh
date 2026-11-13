// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// video_codec_tests.svh -- Video_Codec-UVM-VIP functional tests (included by
// video_codec_pkg.sv).
// Reference model (open-ip-portfolio specs/Video_Codec.json features): four
// 8-bit samples per word, byte 0 first, LEN words SRC -> DST;
//   predictor = previous sample of the job (mod 256); 128 for the first
//   sample of the job and, when LINE_WORDS != 0, of every line of LINE_WORDS
//   words;
//   MODE 0 ENCODE: out = (x - pred) mod 256;
//   MODE 1 DECODE: out = (in + pred) mod 256, pred = the decoded sample;
//   ZEROS = zero residuals (ENCODE: output bytes, DECODE: input bytes),
//   saturating; CHECKSUM = 32-bit sum of the frame words (ENCODE: input,
//   DECODE: output).
// LINE_WORDS and LEN carry the frame geometry, so any resolution works; the
// tests include 1080p and 8K line widths (480 and 1920 words).
/* TEST PLAN
- `video_codec_roundtrip_test`: 16 frames: ENCODE, then DECODE the residual
  into a third buffer: every word of both jobs against the model, the
  decoded frame = the original, ZEROS and CHECKSUM of both jobs, CHECKSUM
  equal in both directions. Frames: random, flat (all ZEROS), ramps, and
  smooth images; LINE_WORDS 0, 1, 7, 480 (1920 px) and 1920 (7680 px, 8K)
  with lengths that end mid-line; four back-pressure settings.
- `video_codec_err_test`: ENCODE from a SLVERR region (those words read as
  0), DECODE into a DECERR region (untouched): DONE + ERR, STATUS.err; a
  clean job clears it.
*/

class video_codec_job_base_test extends video_codec_base_test;
  `uvm_component_utils(video_codec_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    job_fcov_bins();
    fcov_bins("mode", '{"encode", "decode"});
    fcov_bins("line_words", '{"0_whole_frame", "1", "2_479", "480_1919_1080p", "1920_up_8k"});
  endfunction

  static function void dpcm(bit [31:0] in[$], bit decode, int unsigned line_words, ref bit [31:0] out[$],
                            output int unsigned zeros, output bit [31:0] sum);
    bit [7:0] pred;
    out.delete(); zeros = 0; sum = 0;
    foreach (in[i]) begin
      bit [31:0] o;
      if (i == 0 || (line_words != 0 && i % line_words == 0)) pred = 8'd128;
      for (int b = 0; b < 4; b++) begin
        bit [7:0] x = in[i][8*b +: 8];
        if (!decode) begin
          o[8*b +: 8] = x - pred; pred = x;
          if (o[8*b +: 8] == 0) zeros++;
        end else begin
          o[8*b +: 8] = x + pred; pred = o[8*b +: 8];
          if (x == 0) zeros++;
        end
      end
      out.push_back(o);
      sum += decode ? o : in[i];
    end
    if (zeros > 32'hFFFF) zeros = 32'hFFFF;
  endfunction

  task job(string tag, bit decode, bit [31:0] src, bit [31:0] dst, int unsigned len, int unsigned line_words,
           output bit [31:0] csum);
    bit [31:0] in[$], out[$], v, sum; bit rerr; int unsigned z;
    job_input(src, len, in, rerr);
    dpcm(in, decode, line_words, out, z, sum);
    wr("CTRL", decode);
    fcov("mode", decode ? "decode" : "encode");
    fcov("line_words", (line_words == 0) ? "0_whole_frame" : (line_words == 1) ? "1" : (line_words < 480) ? "2_479" :
                       (line_words < 1920) ? "480_1919_1080p" : "1920_up_8k");
    wr("LINE", line_words);
    run_job(tag, src, dst, len, out, rerr);
    rd("ZEROS", v);
    check_eq(v, z, {tag, " ZEROS"});
    rd("CHECKSUM", csum);
    check_eq(csum, sum, {tag, " CHECKSUM"});
  endtask

  function void frame(int unsigned kind, bit [31:0] base, int unsigned len, ref bit [31:0] w[$]);
    w.delete();
    for (int unsigned i = 0; i < len; i++) begin
      bit [31:0] x;
      case (kind % 4)
        0: x = $urandom();
        1: x = 32'h8080_8080;                                       // flat at the predictor's start value
        2: for (int b = 0; b < 4; b++) x[8*b +: 8] = 8'(4 * i + b); // ramp
        3: for (int b = 0; b < 4; b++) x[8*b +: 8] = 8'(100 + ((4 * i + b) / 37) % 20 + $urandom_range(2));  // smooth
      endcase
      w.push_back(x);
    end
    mem().load_words(base, w);
  endfunction
endclass

// testlist: video_codec_roundtrip_test 3
class video_codec_roundtrip_test extends video_codec_job_base_test;
  `uvm_component_utils(video_codec_roundtrip_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lws[$] = '{0, 1, 7, 480, 1920};
    bit [31:0] w[$], back[$], c1, c2;
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 16; i++) begin
      int unsigned lw = lws[i % lws.size()];
      int unsigned len = (lw >= 480) ? lw * 2 + $urandom_range(1, lw - 1) :
                         (i < 3) ? ((i == 0) ? 1 : (i == 1) ? 9 : 16) : $urandom_range(1, 700);
      // word offsets inside the page so bursts split at 4 KB boundaries in every way
      bit [31:0] a = 32'h1000_0000 + 4 * $urandom_range(0, 1023), b = 32'h2000_0000 + 4 * $urandom_range(0, 1023),
                 c = 32'h3000_0000 + 4 * $urandom_range(0, 1023);
      backpressure(i);
      frame(i, a, len, w);
      job($sformatf("encode %0d lw=%0d len=%0d", i, lw, len), 0, a, b, len, lw, c1);
      job($sformatf("decode %0d", i), 1, b, c, len, lw, c2);
      mem().get_words(c, len, back);
      check_words(c, w, $sformatf("frame %0d after encode + decode", i));
      check_eq(c2, c1, $sformatf("frame %0d: CHECKSUM of encode and decode", i));
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: video_codec_err_test 2
class video_codec_err_test extends video_codec_job_base_test;
  `uvm_component_utils(video_codec_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$], c;
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0040, 32'h1000_0080, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0140, AXI_DECERR);
    frame(0, 32'h1000_0000, 256, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hC0DE_0000 + i);
    job("encode read error", 0, 32'h1000_0000, 32'h2400_0000, 64, 16, c);
    job("decode write error", 1, 32'h1000_0200, 32'h2000_0000, 128, 0, c);
    job("clean", 0, 32'h1000_0200, 32'h2800_0000, 40, 8, c);
    phase.drop_objection(this);
  endtask
endclass
