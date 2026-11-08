// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// npu_tests.svh -- NPU-UVM-VIP functional tests (included by npu_pkg.sv).
// Reference model (open-ip-portfolio specs/NPU.json features):
//   four signed int8 samples per word, byte 0 first: sample n = byte n mod 4
//   of word n / 4, for input and output;
//   acc[n] = BIAS + W0*x[n] + W1*x[n-1] + W2*x[n-2] + W3*x[n-3], x[<0] = 0
//   (every job starts with zero history);
//   y[n] = sat8((RELU ? max(acc[n], 0) : acc[n]) >>> SHIFT);
//   SATURATIONS = results that were clipped (saturating).
/* TEST PLAN
- `npu_conv_test`: 36 jobs: identity (W0 = 1), moving sum, a high-pass
  [1, -2, 1, 0], all four taps at +127 / -128, random weights; BIAS 0,
  +-32767 / -32768 and random; SHIFT 0..15; RELU on and off; lengths 1, 2,
  16, 17 and random up to 600 words; four back-pressure settings. Every
  output word, SATURATIONS, STATUS, DONE / ERR, read / write counts, windows,
  AXI ID 2; history is reset between jobs (the same input twice gives the
  same output).
- `npu_err_test`: SLVERR in the source (those samples are 0 and the
  convolution runs across them), DECERR in the destination (untouched):
  DONE + ERR, STATUS.err; a clean job clears it.
*/

class npu_job_base_test extends npu_base_test;
  `uvm_component_utils(npu_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  static function void conv(bit [31:0] in[$], bit [7:0] w[4], bit [15:0] bias, int unsigned shift, bit relu,
                            ref bit [31:0] out[$], output int unsigned sats);
    int x[4];   // x[n], x[n-1], x[n-2], x[n-3]
    out.delete(); sats = 0; x = '{0, 0, 0, 0};
    foreach (in[i]) begin
      bit [31:0] o;
      for (int b = 0; b < 4; b++) begin
        longint acc;
        int y;
        x[3] = x[2]; x[2] = x[1]; x[1] = x[0]; x[0] = $signed(in[i][8*b +: 8]);
        acc = longint'($signed(bias));
        for (int k = 0; k < 4; k++) acc += longint'($signed(w[k])) * x[k];
        if (relu && acc < 0) acc = 0;
        acc = (acc >= 0) ? (acc >> shift) : -((-acc + (64'd1 << shift) - 1) >> shift);   // >>> : floor
        if (acc > 127) begin y = 127; sats++; end
        else if (acc < -128) begin y = -128; sats++; end
        else y = int'(acc);
        o[8*b +: 8] = 8'(y);
      end
      out.push_back(o);
    end
    if (sats > 32'hFFFF) sats = 32'hFFFF;
  endfunction

  task job(string tag, bit [31:0] src, bit [31:0] dst, int unsigned len, bit [7:0] w[4], bit [15:0] bias,
           int unsigned shift, bit relu);
    bit [31:0] in[$], out[$], v; bit rerr; int unsigned sats;
    job_input(src, len, in, rerr);
    conv(in, w, bias, shift, relu, out, sats);
    wr_fields("WEIGHTS", '{"w0", "w1", "w2", "w3"}, '{w[0], w[1], w[2], w[3]});
    wr_fields("CTRL", '{"bias", "shift", "relu"}, '{bias, shift, relu});
    run_job(tag, src, dst, len, out, rerr);
    rd("SATURATIONS", v);
    check_eq(v, sats, {tag, " SATURATIONS"});
  endtask
endclass

// testlist: npu_conv_test 3
class npu_conv_test extends npu_job_base_test;
  `uvm_component_utils(npu_conv_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [7:0] wset[6][4] = '{'{8'd1, 0, 0, 0}, '{8'd1, 8'd1, 8'd1, 8'd1}, '{8'd1, 8'hFE, 8'd1, 0},
                             '{8'd127, 8'd127, 8'd127, 8'd127}, '{8'h80, 8'h80, 8'h80, 8'h80}, '{8'h80, 8'd127, 8'h80, 8'd127}};
    bit [15:0] biases[4] = '{16'd0, 16'h7FFF, 16'h8000, 16'hFFFF};
    int unsigned lens[$] = '{1, 2, 16, 17};
    bit [31:0] w[$];
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 36; i++) begin
      bit [7:0] wt[4];
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 600);
      bit [15:0] bias = (i < 8) ? biases[i % 4] : $urandom();
      int unsigned shift = (i < 16) ? i : $urandom_range(15);
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0001_0000, len);
      bit [31:0] dst = rand_addr(32'h2000_0000, 32'h0001_0000, len);
      if (i < 12) wt = wset[i % 6];
      else foreach (wt[k]) wt[k] = $urandom();
      backpressure(i);
      fill_random(src, len, w);
      job($sformatf("job %0d len=%0d bias=%04h shift=%0d", i, len, bias, shift), src, dst, len, wt, bias, shift, i % 3 == 0);
      if (i == 20)   // history resets: the same job again gives the same output
        job("repeat of job 20", src, dst + 32'h0000_8000 - 4 * len, len, wt, bias, shift, i % 3 == 0);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: npu_err_test 2
class npu_err_test extends npu_job_base_test;
  `uvm_component_utils(npu_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$];
    bit [7:0] wt[4] = '{8'd3, 8'hFD, 8'd2, 8'd1};
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0040, 32'h1000_0080, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0140, AXI_DECERR);
    fill_random(32'h1000_0000, 512, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'h5EED_0000 + i);
    job("read error", 32'h1000_0000, 32'h2400_0000, 64, wt, 16'd5, 2, 0);
    job("write error", 32'h1000_0400, 32'h2000_0000, 128, wt, 16'hFF00, 1, 1);
    job("clean", 32'h1000_0400, 32'h2800_0000, 40, wt, 16'd0, 0, 0);
    phase.drop_objection(this);
  endtask
endclass
