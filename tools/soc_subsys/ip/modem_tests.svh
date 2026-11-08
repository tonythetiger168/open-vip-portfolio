// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// modem_tests.svh -- Modem-UVM-VIP functional tests (included by modem_pkg.sv).
// Reference model (open-ip-portfolio specs/Modem.json features):
//   out word = in word ^ key (key = 0 when CTRL.bypass = 1), LEN words SRC -> DST;
//   key: 32-bit Galois LFSR loaded with SEED at start (0 becomes 1); for bit
//   i = 0..31: key[i] = s[0]; s = s[0] ? (s >> 1) ^ 0x80200003 : s >> 1; the
//   state carries on to the next word;
//   CRC = CRC-32 (IEEE 802.3, reflected 0xEDB88320, init / final XOR
//   0xFFFFFFFF, bytes little-endian) of the input words (CTRL.crc_sel 0) or
//   of the output words (crc_sel 1).
/* TEST PLAN
- `modem_scramble_test`: 36 jobs: SEED 0 (becomes 1), 1, 0xFFFFFFFF and
  random; lengths 0, 1, 16, 17 and random up to 700 words; crc_sel 0 and 1;
  four back-pressure settings; addresses near 4 KB boundaries. Checks every
  output word, CRC, STATUS, DONE / ERR, the read and write word counts and
  windows, AXI ID 6.
- `modem_roundtrip_test`: scramble a block, descramble the output with the
  same seed: the result equals the original block and both CRCs (input of
  the first job, output of the second) match the CRC of the original.
- `modem_bypass_test`: CTRL.bypass = 1: output = input and CRC = CRC of the
  input; known answer: CRC-32 of the bytes "1234" (one little-endian word
  0x34333231) = 0x9BE3E0A3.
- `modem_err_test`: SLVERR in the source (output words = key there, since the
  input reads as 0), DECERR in the destination (words untouched): DONE + ERR,
  STATUS.err; the next clean job clears it.
*/

class modem_job_base_test extends modem_base_test;
  `uvm_component_utils(modem_job_base_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    job_fcov_bins();
    fcov_bins("crc_sel", '{"input", "output"});
    fcov_bins("bypass", '{"scramble", "bypass"});
  endfunction

  static function bit [31:0] crc32_words(bit [31:0] w[$]);
    bit [31:0] c = 32'hFFFF_FFFF;
    foreach (w[i])
      for (int b = 0; b < 4; b++) begin
        c ^= {24'h0, w[i][8*b +: 8]};
        for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
      end
    return ~c;
  endfunction

  static function void scramble(bit [31:0] seed, bit bypass, bit [31:0] in[$], ref bit [31:0] out[$]);
    bit [31:0] s = (seed == 0) ? 32'h1 : seed;
    out.delete();
    foreach (in[i]) begin
      bit [31:0] key;
      for (int b = 0; b < 32; b++) begin
        key[b] = s[0];
        s = s[0] ? ((s >> 1) ^ 32'h8020_0003) : (s >> 1);
      end
      out.push_back(bypass ? in[i] : (in[i] ^ key));
    end
  endfunction

  task job(string tag, bit [31:0] src, bit [31:0] dst, int unsigned len, bit [31:0] seed,
           bit crc_sel, bit bypass, output bit [31:0] crc_got);
    bit [31:0] in[$], out[$]; bit rerr;
    job_input(src, len, in, rerr);
    scramble(seed, bypass, in, out);
    wr("SEED", seed);
    wr("CTRL", {30'h0, bypass, crc_sel});
    fcov("crc_sel", crc_sel ? "output" : "input");
    fcov("bypass", bypass ? "bypass" : "scramble");
    run_job(tag, src, dst, len, out, rerr);
    rd("CRC", crc_got);
    if (crc_sel) check_eq(crc_got, crc32_words(out), {tag, " CRC of the output"});
    else         check_eq(crc_got, crc32_words(in),  {tag, " CRC of the input"});
  endtask
endclass

// testlist: modem_scramble_test 3
class modem_scramble_test extends modem_job_base_test;
  `uvm_component_utils(modem_scramble_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    int unsigned lens[$] = '{0, 1, 16, 17};
    bit [31:0] seeds[$] = '{0, 1, 32'hFFFF_FFFF, 32'h1234_5678};
    bit [31:0] w[$], c;
    phase.raise_objection(this);
    wait_reset();
    for (int unsigned i = 0; i < 36; i++) begin
      int unsigned len = (i < lens.size()) ? lens[i] : $urandom_range(1, 700);
      bit [31:0] seed = (i < seeds.size()) ? seeds[i] : $urandom();
      bit [31:0] src = rand_addr(32'h1000_0000, 32'h0001_0000, len);
      bit [31:0] dst = rand_addr(32'h2000_0000, 32'h0001_0000, len);
      backpressure(i);
      fill_random(src, len, w);
      job($sformatf("job %0d len=%0d seed=%08h", i, len, seed), src, dst, len, seed, i % 2, 0, c);
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: modem_roundtrip_test 2
class modem_roundtrip_test extends modem_job_base_test;
  `uvm_component_utils(modem_roundtrip_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] orig[$], back[$], c1, c2;
    phase.raise_objection(this);
    wait_reset();
    for (int r = 0; r < 4; r++) begin
      int unsigned len = $urandom_range(1, 500);
      bit [31:0] seed = $urandom();
      backpressure(r);
      fill_random(32'h1000_0000, len, orig);
      job("scramble", 32'h1000_0000, 32'h2000_0000, len, seed, 0, 0, c1);
      job("descramble", 32'h2000_0000, 32'h3000_0000, len, seed, 1, 0, c2);
      mem().get_words(32'h3000_0000, len, back);
      foreach (orig[i]) check_eq(back[i], orig[i], $sformatf("round trip word %0d", i));
      check_eq(c1, crc32_words(orig), "CRC of the scrambler input");
      check_eq(c2, c1, "CRC of the descrambler output = CRC of the original");
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: modem_bypass_test 1
class modem_bypass_test extends modem_job_base_test;
  `uvm_component_utils(modem_bypass_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$], c;
    phase.raise_objection(this);
    wait_reset();
    // known answer: CRC-32 of the bytes "1234" (one little-endian word)
    mem().wr32(32'h1000_0000, 32'h3433_3231);
    job("known answer", 32'h1000_0000, 32'h2000_0000, 1, 0, 0, 1, c);
    check_eq(c, 32'h9BE3_E0A3, "CRC-32(\"1234\")");
    for (int i = 0; i < 6; i++) begin
      int unsigned len = $urandom_range(1, 300);
      fill_random(32'h1000_1000, len, w);
      backpressure(i);
      job($sformatf("bypass %0d", i), 32'h1000_1000, 32'h2000_4000, len, $urandom(), i % 2, 1, c);
      check_eq(c, crc32_words(w), "bypass: CRC = CRC of the input");
    end
    phase.drop_objection(this);
  endtask
endclass

// testlist: modem_err_test 2
class modem_err_test extends modem_job_base_test;
  `uvm_component_utils(modem_err_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    bit [31:0] w[$], c;
    phase.raise_objection(this);
    wait_reset();
    env.axi_cfg.add_err_region(32'h1000_0080, 32'h1000_00C0, AXI_SLVERR);
    env.axi_cfg.add_err_region(32'h2000_0100, 32'h2000_0120, AXI_DECERR);
    fill_random(32'h1000_0000, 256, w);
    for (int i = 0; i < 128; i++) mem().wr32(32'h2000_0000 + 4 * i, 32'hBEEF_0000 + i);
    job("read error", 32'h1000_0000, 32'h2400_0000, 96, 32'hACE1, 1, 0, c);
    job("write error", 32'h1000_0200, 32'h2000_0000, 128, 32'hACE1, 0, 0, c);
    job("clean", 32'h1000_0200, 32'h2800_0000, 40, 32'h5, 0, 0, c);
    phase.drop_objection(this);
  endtask
endclass
