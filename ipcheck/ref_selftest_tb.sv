// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
// ref_selftest_tb.sv -- xchk_ref_pkg against public vectors (FIPS 180-4,
// RFC 4231, CRC catalogue check values, CSI-2 checksum examples, DVI codes).
module ref_selftest_tb;
  import xchk_ref_pkg::*;
  int checks = 0, fails = 0;
  task automatic chk(input bit ok, input string msg);
    checks++;
    if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
  endtask
  function automatic logic [1023:0] str(input string s);
    logic [1023:0] m;
    m = '0;
    for (int i = 0; i < s.len(); i++) m[1023 - 8 * i -: 8] = s[i];
    return m;
  endfunction
  initial begin
    logic [31:0] c32; logic [15:0] c16;
    logic [191:0] ex1, ex2;
    string s9;
    ex1 = 192'hFF000002B9DCF372BBD4B85AC875C27C81F805DFFF000001;
    ex2 = 192'hFF0000001EF01EC74F8278C582E08C70D23C78E9FF000001;
    s9 = "123456789";
    c32 = '1; c16 = '1;
    for (int i = 0; i < 9; i++) begin c32 = crc32_byte(c32, s9[i]); c16 = crc16_byte(c16, s9[i]); end
    chk(~c32 == 32'hCBF43926, "CRC-32 check value");
    chk(c16 == 16'h6F91, "CRC-16/MCRF4XX check value");
    c16 = '1; for (int i = 0; i < 24; i++) c16 = crc16_byte(c16, ex1[191 - 8 * i -: 8]);
    chk(c16 == 16'h00F0, "CSI-2 checksum example 1");
    c16 = '1; for (int i = 0; i < 24; i++) c16 = crc16_byte(c16, ex2[191 - 8 * i -: 8]);
    chk(c16 == 16'hE569, "CSI-2 checksum example 2");
    begin
      bit uniq;
      uniq = 1;
      for (int i = 0; i < 24; i++) for (int j = i + 1; j < 24; j++) if (csi2_col(i) == csi2_col(j)) uniq = 0;
      chk(uniq, "CSI-2 ECC columns distinct (single errors correctable)");
    end
    chk(tmds_dec(10'h100) == 8'h00 && tmds_dec(10'h200) == 8'hFF, "TMDS decode of 0x00 / 0xFF at zero disparity");
    begin
      int cnt, bad;
      logic [17:0] e;
      cnt = 0; bad = 0;
      for (int i = 0; i < 256; i++) begin
        e = tmds_enc(i[7:0], cnt);
        cnt = $signed(e[17:10]);
        if (tmds_dec(e[9:0]) != i[7:0] || cnt > 16 || cnt < -16) bad++;
      end
      chk(bad == 0, "TMDS encode/decode round trip over all bytes, disparity bounded");
      e = tmds_enc(8'h00, 0);
      chk(e[9:0] == 10'h100 && $signed(e[17:10]) == -8, "TMDS encode of 0x00 at zero disparity");
    end
    chk(tmds_ctl(10'b1101010100) == 3'b100 && tmds_ctl(10'b1010101011) == 3'b111, "TMDS control tokens");
    chk(terc4_dec(10'b1010011100) == 5'h10 && terc4_dec(10'b1011000011) == 5'h1F, "TERC4 table ends");
    chk(hdmi_bch(56'h0D0282, 24) == 8'hE4, "BCH(32,24) of the AVI InfoFrame header");
    chk(sha256(str("abc"), 3) == 256'hba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad, "SHA-256 'abc'");
    chk(sha256('0, 0) == 256'he3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855, "SHA-256 ''");
    chk(sha256(str("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"), 56) ==
        256'h248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1, "SHA-256 448-bit message");
    chk(hmac_sha256({{20{8'h0b}}, 352'h0}, str("Hi There") >> 512, 8) ==
        256'hb0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7, "HMAC RFC 4231 TC1");
    chk(hmac_sha256({"Jefe", 480'h0}, str("what do ya want for nothing?") >> 512, 28) ==
        256'h5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843, "HMAC RFC 4231 TC2");
    if (fails == 0) $display("XCHK_PASS checks=%0d", checks);
    else            $display("XCHK_FAIL checks=%0d fails=%0d", checks, fails);
    $finish;
  end
endmodule
