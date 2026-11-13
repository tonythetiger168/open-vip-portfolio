// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_mem.svh -- sparse byte-addressed memory shared by the AXI subordinate
// (front door, what the IP sees) and the tests / scoreboards (back door:
// preload input buffers, read back what the IP wrote). Bytes never written
// read as `fill`. Every written byte is remembered in `written`, so a
// scoreboard can tell which bytes the IP touched.

class ssv_mem extends uvm_object;
  `uvm_object_utils(ssv_mem)

  bit [7:0]  mem[bit [31:0]];
  bit        written[bit [31:0]];   // bytes written through the AXI front door
  bit [7:0]  fill = 8'h00;

  function new(string name = "ssv_mem");
    super.new(name);
  endfunction

  function bit [7:0] rd8(bit [31:0] a);
    return mem.exists(a) ? mem[a] : fill;
  endfunction

  function void wr8(bit [31:0] a, bit [7:0] d);
    mem[a] = d;
  endfunction

  // little-endian 32-bit word at a (a need not be aligned)
  function bit [31:0] rd32(bit [31:0] a);
    return {rd8(a + 3), rd8(a + 2), rd8(a + 1), rd8(a)};
  endfunction

  function void wr32(bit [31:0] a, bit [31:0] d, bit [3:0] strb = 4'hF);
    for (int i = 0; i < 4; i++)
      if (strb[i]) wr8(a + i, d[8*i +: 8]);
  endfunction

  // front-door write by the subordinate: also marks the bytes as written
  function void bus_wr32(bit [31:0] a, bit [31:0] d, bit [3:0] strb);
    for (int i = 0; i < 4; i++)
      if (strb[i]) begin
        wr8(a + i, d[8*i +: 8]);
        written[a + i] = 1'b1;
      end
  endfunction

  function void load_words(bit [31:0] base, const ref bit [31:0] w[$]);
    foreach (w[i]) wr32(base + 4 * i, w[i]);
  endfunction

  function void get_words(bit [31:0] base, int unsigned n, ref bit [31:0] w[$]);
    w.delete();
    for (int unsigned i = 0; i < n; i++) w.push_back(rd32(base + 4 * i));
  endfunction

  // number of bytes the IP wrote outside [lo, hi)
  function int unsigned written_outside(bit [31:0] lo, bit [31:0] hi);
    int unsigned n = 0;
    foreach (written[a]) if (a < lo || a >= hi) n++;
    return n;
  endfunction

  function void clear_written();
    written.delete();
  endfunction

  function void reset();
    mem.delete();
    written.delete();
  endfunction
endclass
