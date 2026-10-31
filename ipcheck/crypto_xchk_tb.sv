// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// crypto_xchk_tb.sv -- Crypto___Security_Engine_top (open-ip-portfolio)
// against SHA-256 / HMAC-SHA-256 digests from Python hashlib and the FIPS
// 180-4 / RFC 4231 vectors (vec.hex from tools/run_ip_crosscheck.py), with
// xchk_ref_pkg computing the same digests as a second reference.
// Record: mode, len, msg[64], key[64], digest[32].
`ifndef NVEC
`define NVEC 1
`endif
module crypto_xchk_tb;
  import xchk_ref_pkg::*;
  localparam int REC = 162;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask

  logic clk = 0, rst_n = 0;
  logic msg_we = 0, key_we = 0, start = 0, mode = 0;
  logic [1:0] msg_widx = 0, key_widx = 0;
  logic [127:0] msg = 0, key = 0;
  logic [6:0] msg_len = 0;
  wire busy, done, irq;
  wire [255:0] digest;
  always #5 clk = ~clk;

  Crypto___Security_Engine_top dut (.clk, .rst_n, .msg_we, .msg_widx, .msg, .key_we, .key_widx, .key,
                                    .msg_len, .start, .mode, .busy, .done, .digest, .irq);

  logic [7:0] v [0:`NVEC * REC - 1];
  int nirq = 0;
  always @(posedge clk) if (irq) nirq++;

  task automatic run(input logic md, input int ln, input logic [511:0] m, input logic [511:0] k,
                     output logic [255:0] dg, output int cyc);
    @(negedge clk);
    for (int w = 0; w < 4; w++) begin
      msg_we = 1; msg_widx = w; msg = m[511 - 128 * w -: 128];
      key_we = 1; key_widx = w; key = k[511 - 128 * w -: 128];
      @(negedge clk);
    end
    msg_we = 0; key_we = 0;
    msg_len = ln; mode = md; start = 1;
    @(negedge clk); start = 0;
    cyc = 0;
    while (!done && cyc < 2000) begin @(negedge clk); cyc++; end
    dg = digest;
  endtask

  initial begin
    logic [511:0] m, k;
    logic [255:0] exp_, dg;
    int base, ln, cyc, n0;
    logic md;
    $readmemh("vec.hex", v);
    repeat (3) @(negedge clk);
    rst_n = 1;
    for (int r = 0; r < `NVEC; r++) begin
      base = r * REC;
      md = v[base][0]; ln = v[base + 1];
      for (int i = 0; i < 64; i++) begin
        m[511 - 8 * i -: 8] = v[base + 2 + i];
        k[511 - 8 * i -: 8] = v[base + 66 + i];
      end
      for (int i = 0; i < 32; i++) exp_[255 - 8 * i -: 8] = v[base + 130 + i];
      chk((md ? hmac_sha256(k, m, ln) : sha256({m, 512'h0}, ln)) === exp_,
          $sformatf("vector %0d: xchk_ref_pkg agrees with hashlib", r));
      run(md, ln, m, k, dg, cyc);
      chk(cyc < 2000, $sformatf("vector %0d: done", r));
      chk(dg === exp_, $sformatf("vector %0d (%s, %0d bytes): digest %h, expected %h", r,
                                 md ? "HMAC" : "SHA-256", ln, dg, exp_));
    end
    // rejected start (msg_len > 64) and writes while busy raise irq
    n0 = nirq;
    @(negedge clk); msg_len = 7'd65; mode = 0; start = 1;
    @(negedge clk); start = 0;
    repeat (3) @(negedge clk);
    chk(nirq == n0 + 1 && !busy, "start with msg_len > 64 rejected with irq");
    n0 = nirq;
    @(negedge clk); msg_len = 7'd3; start = 1;
    @(negedge clk); start = 0; msg_we = 1;
    @(negedge clk); msg_we = 0;
    while (!done) @(negedge clk);
    chk(nirq == n0 + 1, "message write while busy raises irq");
    if (fails == 0) $display("XCHK_PASS checks=%0d", checks);
    else            $display("XCHK_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
endmodule
