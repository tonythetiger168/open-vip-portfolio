// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// xchk_ref_pkg.sv -- protocol reference functions written from the public
// specifications, for checking IP that is not allowed to check itself:
//   * CRC-32 (IEEE 802.3 FCS) and CRC-16 (CSI-2 payload checksum)
//   * CSI-2 packet header ECC (6 parity bits, SEC-DED)
//   * TMDS (DVI 1.0 3.2) data decode, control tokens, HDMI TERC4 decode,
//     guard bands and the BCH(32,24)/BCH(64,56) packet ECC
//   * SHA-256 (FIPS 180-4) and HMAC-SHA-256 (RFC 2104) for messages up to
//     128 bytes
// Every function is checked against public vectors by
// ipcheck/ref_selftest_tb.sv (tools/run_ip_crosscheck.py runs it first).
package xchk_ref_pkg;

  // ---------------------------------------------------------------- CRC
  // CRC-32, reflected polynomial 0xEDB88320; start with '1, invert at the end
  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    for (int i = 0; i < 8; i++) c = (c[0] ^ b[i]) ? (c >> 1) ^ 32'hEDB88320 : (c >> 1);
    return c;
  endfunction
  // CRC-16/MCRF4XX (x^16+x^12+x^5+1 reflected, init 0xFFFF, no final xor)
  function automatic logic [15:0] crc16_byte(input logic [15:0] c, input logic [7:0] b);
    for (int i = 0; i < 8; i++) c = (c[0] ^ b[i]) ? (c >> 1) ^ 16'h8408 : (c >> 1);
    return c;
  endfunction

  // ---------------------------------------------------------------- CSI-2 ECC
  // syndrome column of each header bit D0..D23 (bit p = parity Pp covers it)
  function automatic logic [5:0] csi2_col(input int i);
    case (i)
      0: return 6'h07;  1: return 6'h0B;  2: return 6'h0D;  3: return 6'h0E;
      4: return 6'h13;  5: return 6'h15;  6: return 6'h16;  7: return 6'h19;
      8: return 6'h1A;  9: return 6'h1C; 10: return 6'h23; 11: return 6'h25;
      12: return 6'h26; 13: return 6'h29; 14: return 6'h2A; 15: return 6'h2C;
      16: return 6'h31; 17: return 6'h32; 18: return 6'h34; 19: return 6'h38;
      20: return 6'h1F; 21: return 6'h2F; 22: return 6'h37; default: return 6'h3B;
    endcase
  endfunction
  function automatic logic [5:0] csi2_ecc(input logic [23:0] d);
    logic [5:0] e;
    e = 0;
    for (int i = 0; i < 24; i++) if (d[i]) e ^= csi2_col(i);
    return e;
  endfunction

  // ---------------------------------------------------------------- TMDS / HDMI
  // DVI 1.0 decode of a video data code (q[0] is the first bit on the wire)
  function automatic logic [7:0] tmds_dec(input logic [9:0] q);
    logic [7:0] t, d;
    t = q[9] ? ~q[7:0] : q[7:0];
    d[0] = t[0];
    for (int i = 1; i < 8; i++) d[i] = q[8] ? (t[i] ^ t[i-1]) : !(t[i] ^ t[i-1]);
    return d;
  endfunction
  // DVI 1.0 figure 3-5 encoder: code for d with running disparity cnt (0 at
  // the start of every video period); returns {cnt', code}, cnt' signed 8 bits
  function automatic logic [17:0] tmds_enc(input logic [7:0] d, input int cnt);
    logic [8:0] qm;
    logic [9:0] q;
    int n1d, n1, n0;
    n1d = $countones(d);
    qm[0] = d[0];
    if (n1d > 4 || (n1d == 4 && d[0] == 1'b0)) begin
      for (int i = 1; i < 8; i++) qm[i] = !(qm[i-1] ^ d[i]);
      qm[8] = 1'b0;
    end else begin
      for (int i = 1; i < 8; i++) qm[i] = qm[i-1] ^ d[i];
      qm[8] = 1'b1;
    end
    n1 = $countones(qm[7:0]); n0 = 8 - n1;
    if (cnt == 0 || n1 == n0) begin
      q = {!qm[8], qm[8], qm[8] ? qm[7:0] : ~qm[7:0]};
      cnt = qm[8] ? cnt + (n1 - n0) : cnt + (n0 - n1);
    end else if ((cnt > 0 && n1 > n0) || (cnt < 0 && n0 > n1)) begin
      q = {1'b1, qm[8], ~qm[7:0]};
      cnt = cnt + 2 * qm[8] + (n0 - n1);
    end else begin
      q = {1'b0, qm[8], qm[7:0]};
      cnt = cnt - 2 * (!qm[8]) + (n1 - n0);
    end
    return {cnt[7:0], q};
  endfunction
  // control token -> {valid, C1, C0}
  function automatic logic [2:0] tmds_ctl(input logic [9:0] q);
    case (q)
      10'b1101010100: return 3'b100;
      10'b0010101011: return 3'b101;
      10'b0101010100: return 3'b110;
      10'b1010101011: return 3'b111;
      default:        return 3'b000;
    endcase
  endfunction
  // HDMI TERC4 -> {valid, d[3:0]}
  function automatic logic [4:0] terc4_dec(input logic [9:0] q);
    case (q)
      10'b1010011100: return 5'h10; 10'b1001100011: return 5'h11;
      10'b1011100100: return 5'h12; 10'b1011100010: return 5'h13;
      10'b0101110001: return 5'h14; 10'b0100011110: return 5'h15;
      10'b0110001110: return 5'h16; 10'b0100111100: return 5'h17;
      10'b1011001100: return 5'h18; 10'b0100111001: return 5'h19;
      10'b0110011100: return 5'h1A; 10'b1011000110: return 5'h1B;
      10'b1010001110: return 5'h1C; 10'b1001110001: return 5'h1D;
      10'b0101100011: return 5'h1E; 10'b1011000011: return 5'h1F;
      default:        return 5'h00;
    endcase
  endfunction
  localparam logic [9:0] GB_VID_02 = 10'b1011001100;   // video guard band, channels 0 and 2
  localparam logic [9:0] GB_VID_1  = 10'b0100110011;   // video guard band, channel 1
  localparam logic [9:0] GB_ISL_12 = 10'b0100110011;   // data island guard band, channels 1 and 2
  // packet ECC, BCH with G(x) = 1 + x^6 + x^7 + x^8 over n bits, bit 0 first
  function automatic logic [7:0] hdmi_bch(input logic [55:0] bits, input int n);
    logic [7:0] e;
    logic fb;
    e = 0;
    for (int i = 0; i < n; i++) begin
      fb = e[0] ^ bits[i];
      e = e >> 1;
      if (fb) e ^= 8'h83;
    end
    return e;
  endfunction

  // ---------------------------------------------------------------- SHA-256
  function automatic logic [31:0] k256(input int t);
    localparam logic [2047:0] K = {
      32'h428a2f98, 32'h71374491, 32'hb5c0fbcf, 32'he9b5dba5, 32'h3956c25b, 32'h59f111f1, 32'h923f82a4, 32'hab1c5ed5,
      32'hd807aa98, 32'h12835b01, 32'h243185be, 32'h550c7dc3, 32'h72be5d74, 32'h80deb1fe, 32'h9bdc06a7, 32'hc19bf174,
      32'he49b69c1, 32'hefbe4786, 32'h0fc19dc6, 32'h240ca1cc, 32'h2de92c6f, 32'h4a7484aa, 32'h5cb0a9dc, 32'h76f988da,
      32'h983e5152, 32'ha831c66d, 32'hb00327c8, 32'hbf597fc7, 32'hc6e00bf3, 32'hd5a79147, 32'h06ca6351, 32'h14292967,
      32'h27b70a85, 32'h2e1b2138, 32'h4d2c6dfc, 32'h53380d13, 32'h650a7354, 32'h766a0abb, 32'h81c2c92e, 32'h92722c85,
      32'ha2bfe8a1, 32'ha81a664b, 32'hc24b8b70, 32'hc76c51a3, 32'hd192e819, 32'hd6990624, 32'hf40e3585, 32'h106aa070,
      32'h19a4c116, 32'h1e376c08, 32'h2748774c, 32'h34b0bcb5, 32'h391c0cb3, 32'h4ed8aa4a, 32'h5b9cca4f, 32'h682e6ff3,
      32'h748f82ee, 32'h78a5636f, 32'h84c87814, 32'h8cc70208, 32'h90befffa, 32'ha4506ceb, 32'hbef9a3f7, 32'hc67178f2};
    return K[2047 - 32 * t -: 32];
  endfunction
  function automatic logic [31:0] rotr(input logic [31:0] x, input int n);
    return (x >> n) | (x << (32 - n));
  endfunction
  // compress one 512-bit block (word 0 in the most significant bits)
  function automatic logic [255:0] sha256_block(input logic [255:0] hin, input logic [511:0] blk);
    logic [31:0] w [0:63];
    logic [31:0] a, b, c, d, e, f, g, h, t1, t2, s0, s1;
    for (int t = 0; t < 16; t++) w[t] = blk[511 - 32 * t -: 32];
    for (int t = 16; t < 64; t++) begin
      s0 = rotr(w[t-15], 7) ^ rotr(w[t-15], 18) ^ (w[t-15] >> 3);
      s1 = rotr(w[t-2], 17) ^ rotr(w[t-2], 19) ^ (w[t-2] >> 10);
      w[t] = w[t-16] + s0 + w[t-7] + s1;
    end
    {a, b, c, d, e, f, g, h} = hin;
    for (int t = 0; t < 64; t++) begin
      t1 = h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k256(t) + w[t];
      t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
      h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    end
    return {hin[255:224] + a, hin[223:192] + b, hin[191:160] + c, hin[159:128] + d,
            hin[127:96] + e, hin[95:64] + f, hin[63:32] + g, hin[31:0] + h};
  endfunction
  // SHA-256 of the first len bytes of m (byte 0 in m[1023:1016]), len <= 128
  function automatic logic [255:0] sha256(input logic [1023:0] m, input int len);
    logic [1535:0] buf_;
    logic [255:0] hs;
    int nb;
    buf_ = '0;
    for (int i = 0; i < len; i++) buf_[1535 - 8 * i -: 8] = m[1023 - 8 * i -: 8];
    buf_[1535 - 8 * len -: 8] = 8'h80;
    nb = (len + 9 + 63) / 64;
    buf_[1535 - 512 * nb + 64 -: 64] = 64'(len) * 64'd8;
    hs = {32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
          32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19};
    for (int b = 0; b < nb; b++) hs = sha256_block(hs, buf_[1535 - 512 * b -: 512]);
    return hs;
  endfunction
  // HMAC-SHA-256 with a key block of 64 bytes (shorter keys zero-padded) and len <= 64
  function automatic logic [255:0] hmac_sha256(input logic [511:0] key, input logic [511:0] msg, input int len);
    logic [1023:0] in_;
    logic [255:0] ih;
    in_ = {key ^ {64{8'h36}}, msg};
    ih = sha256(in_, 64 + len);
    in_ = {key ^ {64{8'h5c}}, ih, 256'h0};
    return sha256(in_, 96);
  endfunction
endpackage
