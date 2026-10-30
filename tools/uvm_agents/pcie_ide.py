# PCIe IDE (Integrity and Data Encryption, PCIe 6.x selective IDE stream,
# non-flit TLPs) agent: the agent is the transmitting port of IDE stream 3
# and sends TLPs a DW per clock (in_valid, in_dw[31:0], in_last; byte 0 of
# a DW in bits 31:24); the DUT is the receiving port's IDE block.
#
# IDE TLP: IDE prefix DW, the 3-DW header (MWr 0x40, MRd 0x00, CplD 0x4A in
# byte 0, length in DW in bytes 2-3), the payload encrypted with
# AES-256-GCM, then a 96-bit MAC (the upper 96 bits of the GCM tag). AAD =
# prefix and header. The prefix used here (the model's layout): byte 0 0x92,
# byte 1 {M, K, T, P, sub-stream[2:0], 0}, byte 2 stream ID, byte 3 0.
# Sub-streams: 0 posted (MWr), 1 non-posted (MRd), 2 completions (CplD).
# Key of sub-stream s, key set k: IDE_KBASE ^ {s, 1'b0, k}. The invocation
# counter is not sent: each side keeps one per sub-stream and key set,
# starting at 1, and IV = {16'h0, 5'h0, sub-stream, stream ID, counter[63:0]},
# so a lost or replayed TLP fails its MAC.
#
# tb/top_tb.sv ide_model: stream 3, both key sets programmed. Output: the
# header and decrypted payload (out_valid, out_dw, out_last) and rep_valid /
# rep_status:
#   0 IDE TLP passed (counter of its sub-stream / key set + 1)
#   1 TLP without an IDE prefix: delivered as it came
#   2 a TLP over 48 DW (the model's buffer), or a bad IDE TLP, dropped
#     without counting: another stream, a sub-stream
#     that does not match the TLP type, M = 0, P = 1, an unknown TLP type, a
#     payload over 8 DW (the model's limit) or a length that does not match
#     the payload and MAC
#   3 MAC check failed: dropped, the stream becomes insecure
#   4 IDE TLP while the stream is insecure: dropped
#   5 K_SET_GO for stream 3 (a non-IDE MsgD with a 3-DW header, message code
#     0x7F, payload byte 0 0x05, byte 2 the stream ID): every counter back to
#     1, stream secure

IDE_FUNCS = """
localparam bit [255:0] IDE_KBASE = 256'h0001_0203_0405_0607_0809_0A0B_0C0D_0E0F_1011_1213_1415_1617_1819_1A1B_1C1D_1E1F;
localparam bit [7:0]   IDE_SID   = 8'd3;
function automatic bit [255:0] ide_key(bit [2:0] ss, bit ks); return IDE_KBASE ^ {251'h0, ss, 1'b0, ks}; endfunction
function automatic bit [7:0] ide_xt(bit [7:0] a); return {a[6:0], 1'b0} ^ (a[7] ? 8'h1B : 8'h00); endfunction
function automatic bit [7:0] ide_gm(bit [7:0] a, bit [7:0] b);
  bit [7:0] p = 0;
  for (int i = 0; i < 8; i++) begin
    if (b[i]) p ^= a;
    a = ide_xt(a);
  end
  return p;
endfunction
function automatic bit [7:0] ide_sbox(bit [7:0] a);
  bit [7:0] r = 8'h01;
  for (int i = 7; i >= 0; i--) begin
    r = ide_gm(r, r);
    if (i != 0) r = ide_gm(r, a);
  end
  return r ^ {r[6:0], r[7]} ^ {r[5:0], r[7:6]} ^ {r[4:0], r[7:5]} ^ {r[3:0], r[7:4]} ^ 8'h63;
endfunction
function automatic bit [31:0] ide_subw(bit [31:0] w);
  return {ide_sbox(w[31:24]), ide_sbox(w[23:16]), ide_sbox(w[15:8]), ide_sbox(w[7:0])};
endfunction
function automatic bit [127:0] ide_next(bit [127:0] k, bit [31:0] w);
  bit [127:0] n;
  n[127:96] = k[127:96] ^ w; n[95:64] = k[95:64] ^ n[127:96]; n[63:32] = k[63:32] ^ n[95:64]; n[31:0] = k[31:0] ^ n[63:32];
  return n;
endfunction
// AES-256 encryption (14 rounds, round keys made on the fly)
function automatic bit [127:0] ide_aes(bit [255:0] key, bit [127:0] blk);
  bit [127:0] ka = key[255:128], kb = key[127:0], s = blk ^ key[255:128], t, rk;
  bit [7:0] rc = 8'h01, a0, a1, a2, a3;
  for (int r = 1; r <= 14; r++) begin
    for (int c = 0; c < 4; c++)
      for (int j = 0; j < 4; j++)
        t[127 - 8*(4*c + j) -: 8] = ide_sbox(s[127 - 8*(4*((c + j) % 4) + j) -: 8]);
    if (r != 14)
      for (int c = 0; c < 4; c++) begin
        a0 = t[127 - 32*c -: 8]; a1 = t[119 - 32*c -: 8]; a2 = t[111 - 32*c -: 8]; a3 = t[103 - 32*c -: 8];
        t[127 - 32*c -: 8] = ide_xt(a0) ^ ide_xt(a1) ^ a1 ^ a2 ^ a3;
        t[119 - 32*c -: 8] = a0 ^ ide_xt(a1) ^ ide_xt(a2) ^ a2 ^ a3;
        t[111 - 32*c -: 8] = a0 ^ a1 ^ ide_xt(a2) ^ ide_xt(a3) ^ a3;
        t[103 - 32*c -: 8] = ide_xt(a0) ^ a0 ^ a1 ^ a2 ^ ide_xt(a3);
      end
    if (r == 1) rk = kb;
    else if (r % 2 == 0) begin
      ka = ide_next(ka, ide_subw({kb[23:0], kb[31:24]}) ^ {rc, 24'h0});
      rc = ide_xt(rc);
      rk = ka;
    end else begin
      kb = ide_next(kb, ide_subw(ka[31:0]));
      rk = kb;
    end
    s = t ^ rk;
  end
  return s;
endfunction
function automatic bit [127:0] ide_gmul(bit [127:0] x, bit [127:0] y);
  bit [127:0] z = 0, v = y;
  for (int i = 0; i < 128; i++) begin
    if (x[127 - i]) z ^= v;
    v = v[0] ? ((v >> 1) ^ {8'hE1, 120'h0}) : (v >> 1);
  end
  return z;
endfunction
function automatic bit [127:0] ide_ghash(bit [127:0] h, bit [127:0] x, bit [7:0] q[$]);
  for (int i = 0; i < q.size(); i += 16) begin
    bit [127:0] b = 0;
    for (int j = 0; j < 16; j++) if (i + j < q.size()) b[127 - 8*j -: 8] = q[i + j];
    x = ide_gmul(x ^ b, h);
  end
  return x;
endfunction
// AES-256-GCM: out = text XOR keystream; returns the tag over aad and the ciphertext
function automatic bit [127:0] ide_gcm(bit [255:0] key, bit [95:0] iv, bit [7:0] aad[$], bit [7:0] txt[$], bit enc,
                                       output bit [7:0] out[$]);
  bit [127:0] h = ide_aes(key, 128'h0), x, ks;
  bit [63:0] la = 64'(aad.size()) * 8, lc = 64'(txt.size()) * 8;
  out.delete();
  for (int i = 0; i < txt.size(); i += 16) begin
    ks = ide_aes(key, {iv, 32'(2 + i / 16)});
    for (int j = 0; j < 16; j++) if (i + j < txt.size()) out.push_back(txt[i + j] ^ ks[127 - 8*j -: 8]);
  end
  x = ide_ghash(h, 128'h0, aad);
  if (enc) x = ide_ghash(h, x, out);
  else     x = ide_ghash(h, x, txt);
  x = ide_gmul(x ^ {la, lc}, h);
  return x ^ ide_aes(key, {iv, 32'h1});
endfunction
function automatic bit [95:0] ide_iv(bit [2:0] ss, bit [7:0] sid, bit [63:0] ctr); return {16'h0, 5'h0, ss, sid, ctr}; endfunction
"""

SPEC = dict(
    vip="PCIe_IDE-UVM-VIP", p="ide", P="IDE", dir="pcie_ide", family="Security",
    desc="PCIe IDE VIP (selective IDE stream, AES-256-GCM): IDE prefix, sub-streams and key sets, implicit invocation "
         "counters, 96-bit MAC, K_SET_GO; receiver model with stream / sub-stream checks, MAC failure and insecure state.",
    about="""
PCIe IDE encrypts and authenticates TLPs between two ports (or end to end
through switches) with AES-256-GCM. Each TLP carries an IDE prefix naming the
stream, the sub-stream (posted, non-posted, completions) and the key set,
and ends in a 96-bit MAC; the invocation counter that makes up the IV is
kept by both sides and never sent, so a lost, reordered or replayed TLP
fails its MAC and turns the stream insecure until it is re-keyed. The agent
is the transmitting port with its own AES-256 and GHASH; the DUT model is
the receiving IDE block. The scoreboard keeps the receiver's counters and
secure state and opens every TLP itself. The smoke test checks its own
AES-256 and GCM against FIPS-197 and the GCM specification first.""",
    defs=IDE_FUNCS,
    timeout=2000,
    ports=[
        ("in", "logic", "in_valid"), ("in", "logic [31:0]", "in_dw"), ("in", "logic", "in_last"),
        ("out", "logic", "out_valid"), ("out", "logic [31:0]", "out_dw"), ("out", "logic", "out_last"),
        ("out", "logic", "rep_valid"), ("out", "logic [2:0]", "rep_status"),
    ],
    fields=[
        ("bit [7:0]", "tlp", "req", "q"),     # the TLP as sent, bytes
        ("bit [2:0]", "status", "rsp"),
        ("bit [7:0]", "odata", "rsp", "q"),
        ("bit [7:0]", "pt", "info", "q"),     # payload before encryption
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "tsel", "info", "rand"),
        ("bit", "ks", "info", "rand"),
        ("bit [2:0]", "len_r", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [63:0]", "ctr", "info"),        # invocation counter the driver used
    ],
    tr_functions="""
// kind: 0-15 IDE TLP, 16-17 plain TLP, 18-19 K_SET_GO, 20 other stream, 21 sub-stream mismatch,
// 22 M = 0, 23 P = 1, 24 MAC bit, 25 payload bit, 26 header bit, 27 replayed counter, 28 MAC DW missing,
// 29-31 IDE TLP
function bit is_ide(); return !(kind inside {16, 17, 18, 19}); endfunction
function bit [2:0] ss_of(); return (tsel == 1) ? 3'd1 : (tsel == 2) ? 3'd2 : 3'd0; endfunction
// header (3 DW) and payload; the driver seals with the counter it chooses
function void hdr(output bit [7:0] h[$]);
  bit [31:0] x = seed | 1;
  bit [9:0] len = len_r + 1;
  h.delete();
  if (kind inside {18, 19}) begin
    h = '{8'h72, 8'h00, 8'h00, 8'h01, 8'h00, 8'h00, 8'h00, 8'h7F, 8'h00, 8'h00, 8'h00, 8'h00};
    return;
  end
  h.push_back((tsel == 1) ? 8'h00 : (tsel == 2) ? 8'h4A : 8'h40);
  h.push_back(8'h00); h.push_back({6'h0, len[9:8]}); h.push_back(len[7:0]);
  for (int i = 0; i < 8; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    h.push_back(x[7:0]);
  end
  if (tsel != 2) h[11][1:0] = 2'b00;
endfunction
function void mk_pt();
  bit [31:0] x = seed ^ 32'h5A5A_0F0F;
  pt.delete();
  if (kind inside {18, 19}) begin pt = '{8'h05, 8'h00, IDE_SID, 8'h00}; return; end
  if (tsel == 1) return;
  for (int i = 0; i < 4 * (len_r + 1); i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    pt.push_back(x[7:0]);
  end
endfunction
function void post_randomize(); if (tsel == 3) tsel = 0; mk_pt(); endfunction
function void set(int k, bit [1:0] ts, bit kset, int n);
  kind = k; tsel = ts; ks = kset; len_r = n - 1;
  mk_pt();
endfunction
// the TLP on the wire, sealed with counter c
function void seal(bit [63:0] c);
  bit [7:0] h[$], a[$], o[$];
  bit [127:0] tag;
  bit [2:0] ss = ss_of();
  ctr = c;
  hdr(h);
  tlp.delete();
  if (!is_ide()) begin
    tlp = h;
    foreach (pt[i]) tlp.push_back(pt[i]);
    return;
  end
  if (kind == 21) ss = (ss == 0) ? 3'd1 : 3'd0;
  a = '{8'h92, {kind != 22, ks, 1'b1, kind == 23, ss, 1'b0}, (kind == 20) ? 8'd5 : IDE_SID, 8'h00};
  foreach (h[i]) a.push_back(h[i]);
  tag = ide_gcm(ide_key(ss, ks), ide_iv(ss, (kind == 20) ? 8'd5 : IDE_SID, c), a, pt, 1'b1, o);
  if (kind == 24) tag[100] = ~tag[100];
  if (kind == 25 && o.size() != 0) o[0][2] = ~o[0][2];
  if (kind == 26 || (kind == 25 && o.size() == 0)) a[12][5] = ~a[12][5];
  tlp = a;
  foreach (o[i]) tlp.push_back(o[i]);
  if (kind != 28) for (int i = 15; i >= 4; i--) tlp.push_back(tag[8*i +: 8]);
endfunction
""",
    drv_rsp=True,
    drv_desc="one TLP per item: the driver keeps the transmit invocation counters (and follows the receiver's insecure state) and seals IDE TLPs with them; DW per clock; then the delivered DWs and the status",
    drv_members="""bit [63:0] tx_ctr [3][2] = '{'{1, 1}, '{1, 1}, '{1, 1}};
bit insecure = 0;""",
    drv_idle="""
vif.drv_cb.in_valid <= 1'b0;
vif.drv_cb.in_dw    <= 32'h0;
vif.drv_cb.in_last  <= 1'b0;
""",
    drv_item="""
bit [2:0] ss = t.ss_of();
bit [63:0] c = tx_ctr[ss][t.ks];
int k = 0;
if (t.kind == 27) c = c - 1;
t.seal(c);
if (t.is_ide() && !insecure) begin
  if (t.kind inside {24, 25, 26, 27}) insecure = 1;
  else if (!(t.kind inside {20, 21, 22, 23, 28})) tx_ctr[ss][t.ks] = c + 1;
end
if (t.kind inside {18, 19}) begin
  foreach (tx_ctr[i, j]) tx_ctr[i][j] = 1;
  insecure = 0;
end
for (int i = 0; i < t.tlp.size(); i += 4) begin
  vif.drv_cb.in_valid <= 1'b1;
  vif.drv_cb.in_dw <= {t.tlp[i], t.tlp[i + 1], t.tlp[i + 2], t.tlp[i + 3]};
  vif.drv_cb.in_last <= (i + 4 >= t.tlp.size());
  @(vif.drv_cb);
end
vif.drv_cb.in_valid <= 1'b0; vif.drv_cb.in_last <= 1'b0;
t.odata.delete();
do begin
  @(vif.drv_cb);
  if (vif.drv_cb.out_valid) for (int i = 3; i >= 0; i--) t.odata.push_back(vif.drv_cb.out_dw[8*i +: 8]);
  k++;
end while (!vif.drv_cb.rep_valid && k < cfg.timeout_cycles);
if (!vif.drv_cb.rep_valid) `uvm_error("DRV", "IDE: no status for a TLP")
t.status = vif.drv_cb.rep_status;
repeat (2) @(vif.drv_cb);
""",
    mon_desc="TLPs into the IDE block, then the delivered DWs and the status that close each one",
    mon_run="""
bit [7:0] b[$], o[$];
bit [7:0] tlps[$][$];
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.in_valid) begin
    for (int i = 3; i >= 0; i--) b.push_back(vif.mon_cb.in_dw[8*i +: 8]);
    if (vif.mon_cb.in_last) begin tlps.push_back(b); b.delete(); end
  end
  if (vif.mon_cb.out_valid) for (int i = 3; i >= 0; i--) o.push_back(vif.mon_cb.out_dw[8*i +: 8]);
  if (vif.mon_cb.rep_valid) begin
    if (tlps.size() == 0) `uvm_error("MON", "IDE: status without a TLP")
    else begin
      ide_transaction t = ide_transaction::type_id::create("t");
      t.tlp = tlps.pop_front();
      t.odata = o;
      t.status = vif.mon_cb.rep_status;
      publish(t);
    end
    o.delete();
  end
end
""",
    sb_members="""bit [63:0] rx_ctr [3][2] = '{'{1, 1}, '{1, 1}, '{1, 1}};
bit insecure = 0;
bit kat_done = 0;""",
    predict="""
bit [7:0] q[$], aad[$], c[$], p[$];
bit [127:0] tag;
bit [2:0] ss, want;
bit [9:0] len;
int n = t.tlp.size(), plen;
bit m, pb, ks, data;
if (!kat_done) begin
  // FIPS-197 C.3 and GCM test case 13 on the scoreboard's own AES-256 / GHASH
  kat_done = 1;
  if (ide_aes(IDE_KBASE, 128'h0011_2233_4455_6677_8899_AABB_CCDD_EEFF) != 128'h8EA2_B7CA_5167_45BF_EAFC_4990_4B49_6089)
    `uvm_error("SB", "IDE: AES-256 known answer wrong")
  if (ide_aes(256'h0, 128'h1) != 128'h530F_8AFB_C745_36B9_A963_B4F1_C4CB_738B)
    `uvm_error("SB", "IDE: GCM test case 13 tag wrong")
end
t.odata.delete();
if (n > 192) t.status = 2;
else if (n < 4 || t.tlp[0] != 8'h92) begin
  // no IDE prefix: K_SET_GO for this stream, or delivered as it came
  if (n == 16 && t.tlp[0] == 8'h72 && t.tlp[7] == 8'h7F && t.tlp[12] == 8'h05 && t.tlp[14] == IDE_SID) begin
    t.status = 5;
    foreach (rx_ctr[i, j]) rx_ctr[i][j] = 1;
    insecure = 0;
  end else begin
    t.status = 1;
    t.odata = t.tlp;
  end
end else begin
  {m, ks, pb} = {t.tlp[1][7], t.tlp[1][6], t.tlp[1][4]};
  ss = t.tlp[1][3:1];
  want = (t.tlp[4] == 8'h40) ? 3'd0 : (t.tlp[4] == 8'h00) ? 3'd1 : (t.tlp[4] == 8'h4A) ? 3'd2 : 3'd7;
  len = {t.tlp[6][1:0], t.tlp[7]};
  data = (want != 3'd1);
  plen = data ? 4 * ((len == 0) ? 1024 : len) : 0;
  if (t.tlp[2] != IDE_SID || want == 3'd7 || ss != want || !m || pb || plen > 32 || n != 16 + plen + 12) t.status = 2;
  else if (insecure) t.status = 4;
  else begin
    for (int i = 0; i < 16; i++) aad.push_back(t.tlp[i]);
    for (int i = 0; i < plen; i++) c.push_back(t.tlp[16 + i]);
    tag = ide_gcm(ide_key(ss, ks), ide_iv(ss, IDE_SID, rx_ctr[ss][ks]), aad, c, 1'b0, p);
    for (int i = 0; i < 12; i++) q.push_back(tag[127 - 8*i -: 8]);
    for (int i = 0; i < 12; i++) if (q[i] != t.tlp[16 + plen + i]) insecure = 1;
    if (insecure) t.status = 3;
    else begin
      t.status = 0;
      rx_ctr[ss][ks]++;
      for (int i = 4; i < 16; i++) t.odata.push_back(t.tlp[i]);
      foreach (p[i]) t.odata.push_back(p[i]);
    end
  end
end
""",
    checks="""
if (!(t.status inside {0, 1}) && t.odata.size() != 0) fail(t, "TLP delivered although it was dropped");
""",
    coverage="""
cp_status : coverpoint tr.status { bins passed = {0}; bins plain = {1}; bins bad = {2}; bins mac_fail = {3}; bins insecure = {4};
                                   bins set_go = {5}; }
cp_ss : coverpoint tr.tlp[1][3:1] iff (tr.status == 0) { bins posted = {0}; bins non_posted = {1}; bins cpl = {2}; }
cp_ks : coverpoint tr.tlp[1][6] iff (tr.status == 0);
cp_len : coverpoint tr.odata.size() iff (tr.status == 0) { bins nodata = {12}; bins one = {16}; bins more = {[20:44]}; }
x_ss_ks : cross cp_ss, cp_ks;
""",
    directed="""
// each sub-stream on both key sets, a plain TLP, every fault (each followed by K_SET_GO), replay
for (int s = 0; s < 3; s++)
  for (int k = 0; k < 2; k++) begin t = item(); t.set(0, s, k, 1 + 3 * s + k); send(t); end
t = item(); t.set(16, 0, 0, 2); send(t);
for (int f = 20; f < 29; f++) begin
  t = item(); t.set(f, 0, 0, 2); send(t);
  t = item(); t.set(0, 2, 1, 3); send(t);
  t = item(); t.set(18, 0, 0, 1); send(t);
end
t = item(); t.set(0, 1, 1, 1); send(t);
t = item(); t.set(0, 0, 1, 8); send(t);
""",
    drain_ns=4000,
    model="""
module ide_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        in_valid,
  input  logic [31:0] in_dw,
  input  logic        in_last,
  output logic        out_valid,
  output logic [31:0] out_dw,
  output logic        out_last,
  output logic        rep_valid,
  output logic [2:0]  rep_status
);
  localparam logic [255:0] KBASE = 256'h0001_0203_0405_0607_0809_0A0B_0C0D_0E0F_1011_1213_1415_1617_1819_1A1B_1C1D_1E1F;
  localparam logic [7:0]   SID   = 8'd3;

  function automatic logic [7:0] xt(input logic [7:0] a);
    xt = {a[6:0], 1'b0} ^ (a[7] ? 8'h1B : 8'h00);
  endfunction
  function automatic logic [7:0] gm(input logic [7:0] a, input logic [7:0] b);
    logic [7:0] p, x;
    p = 8'h00; x = a;
    for (int i = 0; i < 8; i++) begin
      if (b[i]) p = p ^ x;
      x = xt(x);
    end
    gm = p;
  endfunction
  function automatic logic [7:0] sbox(input logic [7:0] a);
    logic [7:0] r;
    r = 8'h01;
    for (int i = 7; i >= 0; i--) begin
      r = gm(r, r);
      if (i != 0) r = gm(r, a);
    end
    sbox = r ^ {r[6:0], r[7]} ^ {r[5:0], r[7:6]} ^ {r[4:0], r[7:5]} ^ {r[3:0], r[7:4]} ^ 8'h63;
  endfunction
  function automatic logic [31:0] subw(input logic [31:0] w);
    subw = {sbox(w[31:24]), sbox(w[23:16]), sbox(w[15:8]), sbox(w[7:0])};
  endfunction
  function automatic logic [127:0] kexp(input logic [127:0] k, input logic [31:0] w);
    logic [127:0] n;
    n[127:96] = k[127:96] ^ w;
    n[95:64]  = k[95:64] ^ n[127:96];
    n[63:32]  = k[63:32] ^ n[95:64];
    n[31:0]   = k[31:0] ^ n[63:32];
    kexp = n;
  endfunction
  function automatic logic [127:0] aes(input logic [255:0] key, input logic [127:0] blk);
    logic [127:0] ka, kb, s, t, rk;
    logic [7:0]   rc, a0, a1, a2, a3;
    ka = key[255:128]; kb = key[127:0]; s = blk ^ key[255:128]; rc = 8'h01;
    for (int r = 1; r <= 14; r++) begin
      for (int c = 0; c < 4; c++)
        for (int j = 0; j < 4; j++)
          t[127 - 8*(4*c + j) -: 8] = sbox(s[127 - 8*(4*((c + j) % 4) + j) -: 8]);
      if (r != 14)
        for (int c = 0; c < 4; c++) begin
          a0 = t[127 - 32*c -: 8]; a1 = t[119 - 32*c -: 8]; a2 = t[111 - 32*c -: 8]; a3 = t[103 - 32*c -: 8];
          t[127 - 32*c -: 8] = xt(a0) ^ xt(a1) ^ a1 ^ a2 ^ a3;
          t[119 - 32*c -: 8] = a0 ^ xt(a1) ^ xt(a2) ^ a2 ^ a3;
          t[111 - 32*c -: 8] = a0 ^ a1 ^ xt(a2) ^ xt(a3) ^ a3;
          t[103 - 32*c -: 8] = xt(a0) ^ a0 ^ a1 ^ a2 ^ xt(a3);
        end
      if (r == 1) rk = kb;
      else if (r % 2 == 0) begin
        ka = kexp(ka, subw({kb[23:0], kb[31:24]}) ^ {rc, 24'h0});
        rc = xt(rc);
        rk = ka;
      end else begin
        kb = kexp(kb, subw(ka[31:0]));
        rk = kb;
      end
      s = t ^ rk;
    end
    aes = s;
  endfunction
  function automatic logic [127:0] gmul(input logic [127:0] x, input logic [127:0] y);
    logic [127:0] z, v;
    z = 128'h0; v = y;
    for (int i = 0; i < 128; i++) begin
      if (x[127 - i]) z = z ^ v;
      v = v[0] ? ((v >> 1) ^ {8'hE1, 120'h0}) : (v >> 1);
    end
    gmul = z;
  endfunction

  logic [7:0]  rb [0:191];      // TLP bytes
  logic [31:0] ob [0:47];       // delivered DWs
  logic [7:0]  nrb;             // DWs received
  logic [5:0]  olen, opos;
  logic        go, busy, insecure;
  logic [63:0] ctr [0:5];       // receive counters, index 2 * sub-stream + key set

  function automatic logic [127:0] blk(input integer from, input integer lim);
    logic [127:0] v;
    for (int j = 0; j < 16; j++) v[127 - 8*j -: 8] = (from + j < lim) ? rb[from + j] : 8'h00;
    blk = v;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nrb <= '0; olen <= '0; opos <= '0; go <= 1'b0; busy <= 1'b0; insecure <= 1'b0;
      for (int i = 0; i < 6; i++) ctr[i] <= 64'd1;
      out_valid <= 1'b0; out_dw <= '0; out_last <= 1'b0; rep_valid <= 1'b0; rep_status <= '0;
    end else begin
      rep_valid <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
      go <= in_valid && in_last;
      if (in_valid) begin
        if (nrb < 8'd48) begin
          rb[4*nrb] <= in_dw[31:24]; rb[4*nrb + 1] <= in_dw[23:16]; rb[4*nrb + 2] <= in_dw[15:8]; rb[4*nrb + 3] <= in_dw[7:0];
        end
        if (nrb != 8'hFF) nrb <= nrb + 8'd1;
      end
      // output first: a TLP that completes now restarts it
      if (busy) begin
        out_valid <= 1'b1;
        out_dw <= ob[opos];
        opos <= opos + 6'd1;
        if (opos == olen - 6'd1) begin out_last <= 1'b1; busy <= 1'b0; rep_valid <= 1'b1; end
      end
      if (go) begin : receive
        logic [2:0]   st, ss, want;
        logic [9:0]   len;
        logic [255:0] key;
        logic [127:0] hk, x, tag, ks, cb, mac;
        logic [95:0]  iv;
        logic [63:0]  la, lc, c;
        integer       n, plen, nd;
        n = 4 * nrb;
        nrb <= '0;
        st = 3'd0; nd = 0;
        if (n > 192) st = 3'd2;
        else if (n < 4 || rb[0] != 8'h92) begin
          if (n == 16 && rb[0] == 8'h72 && rb[7] == 8'h7F && rb[12] == 8'h05 && rb[14] == SID) begin
            st = 3'd5;
            for (int i = 0; i < 6; i++) ctr[i] <= 64'd1;
            insecure <= 1'b0;
          end else begin
            st = 3'd1;
            for (int i = 0; i < 48; i++) if (4*i < n) ob[i] <= {rb[4*i], rb[4*i + 1], rb[4*i + 2], rb[4*i + 3]};
            nd = n / 4;
          end
        end else begin
          ss = rb[1][3:1];
          want = (rb[4] == 8'h40) ? 3'd0 : (rb[4] == 8'h00) ? 3'd1 : (rb[4] == 8'h4A) ? 3'd2 : 3'd7;
          len = {rb[6][1:0], rb[7]};
          plen = (want == 3'd1) ? 0 : 4 * ((len == 10'd0) ? 1024 : len);
          if (rb[2] != SID || want == 3'd7 || ss != want || !rb[1][7] || rb[1][4] || plen > 32 || n != 16 + plen + 12) st = 3'd2;
          else if (insecure) st = 3'd4;
          else begin
            key = KBASE ^ {251'h0, ss, 1'b0, rb[1][6]};
            c = ctr[2*ss + rb[1][6]];
            iv = {16'h0, 5'h0, ss, SID, c};
            hk = aes(key, 128'h0);
            x = gmul(blk(0, 16), hk);
            for (int b = 0; b < 2; b++) if (16*b < plen) x = gmul(x ^ blk(16 + 16*b, 16 + plen), hk);
            la = 64'd128; lc = plen * 8;
            x = gmul(x ^ {la, lc}, hk);
            tag = x ^ aes(key, {iv, 32'h1});
            mac = blk(16 + plen, 16 + plen + 12);
            if (tag[127:32] != mac[127:32]) begin
              st = 3'd3; insecure <= 1'b1;
            end else begin
              ctr[2*ss + rb[1][6]] <= c + 64'd1;
              for (int i = 0; i < 3; i++) ob[i] <= {rb[4 + 4*i], rb[5 + 4*i], rb[6 + 4*i], rb[7 + 4*i]};
              for (int b = 0; b < 2; b++)
                if (16*b < plen) begin
                  ks = aes(key, {iv, 32'd2 + b});
                  cb = blk(16 + 16*b, 16 + plen) ^ ks;
                  for (int j = 0; j < 4; j++) if (16*b + 4*j < plen) ob[3 + 4*b + j] <= cb[127 - 32*j -: 32];
                end
              nd = 3 + plen / 4;
            end
          end
        end
        if (nd != 0) begin olen <= 6'(nd); opos <= '0; busy <= 1'b1; end
        else begin rep_valid <= 1'b1; rep_status <= st; end
        rep_status <= st;
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({in_valid, out_valid, rep_valid}))
  else $error("IDE: X on a valid");
assert property (@(posedge clk) disable iff (!rst_n) out_valid |-> !$isunknown(out_dw))
  else $error("IDE: X on delivered data");
assert property (@(posedge clk) disable iff (!rst_n) out_last |-> rep_valid && rep_status <= 3'd1)
  else $error("IDE: last delivered DW without a pass / plain status");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd3);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd5);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic in_valid = 1'b0, in_last = 1'b0;
logic [31:0] in_dw = 32'h0;
wire out_valid, out_last, rep_valid;
wire [31:0] out_dw;
wire [2:0] rep_status;

always #5 clk = ~clk;

ide_model u_dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_dw(in_dw), .in_last(in_last),
                 .out_valid(out_valid), .out_dw(out_dw), .out_last(out_last), .rep_valid(rep_valid), .rep_status(rep_status));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// reference AES-256 / GHASH (table S-box from brute-force inverses)
function automatic logic [7:0] r_xt(input logic [7:0] a); r_xt = {a[6:0], 1'b0} ^ (a[7] ? 8'h1B : 8'h00); endfunction
logic [7:0] sb [0:255];
initial for (int i = 0; i < 256; i++) begin : mk_sbox
  logic [7:0] r, p, x, y;
  r = 8'h00;
  for (int b = 1; b < 256; b++) begin
    p = 8'h00; x = i; y = b;
    for (int k = 0; k < 8; k++) begin
      if (y[k]) p = p ^ x;
      x = r_xt(x);
    end
    if (p == 8'h01) r = b;
  end
  sb[i] = r ^ {r[6:0], r[7]} ^ {r[5:0], r[7:6]} ^ {r[4:0], r[7:5]} ^ {r[3:0], r[7:4]} ^ 8'h63;
end
function automatic logic [31:0] r_mix(input logic [31:0] c);
  logic [7:0] a0, a1, a2, a3;
  {a0, a1, a2, a3} = c;
  r_mix = {r_xt(a0) ^ r_xt(a1) ^ a1 ^ a2 ^ a3, a0 ^ r_xt(a1) ^ r_xt(a2) ^ a2 ^ a3,
           a0 ^ a1 ^ r_xt(a2) ^ r_xt(a3) ^ a3, r_xt(a0) ^ a0 ^ a1 ^ a2 ^ r_xt(a3)};
endfunction
function automatic logic [31:0] r_sw(input logic [31:0] w); r_sw = {sb[w[31:24]], sb[w[23:16]], sb[w[15:8]], sb[w[7:0]]}; endfunction
// full key schedule: 60 words
function automatic logic [127:0] r_aes(input logic [255:0] key, input logic [127:0] pt);
  logic [31:0] w [0:59];
  logic [31:0] tmp;
  logic [127:0] s, t;
  logic [7:0] rc;
  for (int i = 0; i < 8; i++) w[i] = key[255 - 32*i -: 32];
  rc = 8'h01;
  for (int i = 8; i < 60; i++) begin
    tmp = w[i - 1];
    if (i % 8 == 0) begin tmp = r_sw({tmp[23:0], tmp[31:24]}) ^ {rc, 24'h0}; rc = r_xt(rc); end
    else if (i % 8 == 4) tmp = r_sw(tmp);
    w[i] = w[i - 8] ^ tmp;
  end
  s = pt ^ {w[0], w[1], w[2], w[3]};
  for (int r = 1; r <= 14; r++) begin
    for (int c = 0; c < 4; c++)
      for (int j = 0; j < 4; j++)
        t[8*(15 - 4*c - j) +: 8] = sb[s[8*(15 - 4*((c + j) & 3) - j) +: 8]];
    if (r < 14) for (int c = 0; c < 4; c++) t[32*(3 - c) +: 32] = r_mix(t[32*(3 - c) +: 32]);
    s = t ^ {w[4*r], w[4*r + 1], w[4*r + 2], w[4*r + 3]};
  end
  r_aes = s;
endfunction
function automatic logic [127:0] r_gmul(input logic [127:0] x, input logic [127:0] y);
  logic [127:0] z, v;
  z = 0; v = x;
  for (int i = 127; i >= 0; i--) begin
    if (y[i]) z = z ^ v;
    v = v[0] ? ((v >> 1) ^ {8'hE1, 120'h0}) : (v >> 1);
  end
  r_gmul = z;
endfunction

logic [255:0] KB = 256'h0001_0203_0405_0607_0809_0A0B_0C0D_0E0F_1011_1213_1415_1617_1819_1A1B_1C1D_1E1F;
logic [7:0] tb_ [0:255];
logic [7:0] pt [0:63];
integer tn, plen;
logic [63:0] txc [0:5];
function automatic logic [127:0] tblk(input integer from, input integer lim);
  logic [127:0] v;
  for (int j = 0; j < 16; j++) v[8*(15 - j) +: 8] = (from + j < lim) ? tb_[from + j] : 8'h00;
  tblk = v;
endfunction
// IDE TLP: type 0 MWr / 1 MRd / 2 CplD, ndw payload DWs, sub-stream ss, key set ks, stream sid, counter c
task automatic ide(input integer typ, input integer ndw, input integer ss, input integer ks, input integer sid,
                   input logic [63:0] c, input logic m = 1, input logic p = 0);
  logic [255:0] key;
  logic [127:0] hk, x, k2, tag;
  logic [95:0] iv;
  logic [63:0] la, lc;
  for (int i = 0; i < 256; i++) tb_[i] = 8'h00;
  tb_[0] = 8'h92; tb_[1] = {m, ks[0], 1'b1, p, ss[2:0], 1'b0}; tb_[2] = sid; tb_[3] = 8'h00;
  tb_[4] = (typ == 1) ? 8'h00 : (typ == 2) ? 8'h4A : 8'h40; tb_[6] = 8'h00; tb_[7] = ndw;
  for (int i = 8; i < 16; i++) tb_[i] = 8'hC0 + i + ndw;
  plen = (typ == 1) ? 0 : 4 * ndw;
  for (int i = 0; i < 64; i++) pt[i] = 8'h31 * i + ndw + 8'h0B * ss;
  key = KB ^ {251'h0, ss[2:0], 1'b0, ks[0]};
  iv = {16'h0, 5'h0, ss[2:0], sid[7:0], c};
  hk = r_aes(key, 0);
  for (int b = 0; b < 2; b++) begin
    k2 = r_aes(key, {iv, 32'd2 + b});
    for (int j = 0; j < 16; j++) if (16*b + j < plen) tb_[16 + 16*b + j] = pt[16*b + j] ^ k2[8*(15 - j) +: 8];
  end
  x = r_gmul(tblk(0, 16), hk);
  for (int b = 0; b < 2; b++) if (16*b < plen) x = r_gmul(x ^ tblk(16 + 16*b, 16 + plen), hk);
  la = 128; lc = plen * 8;
  x = r_gmul(x ^ {la, lc}, hk);
  tag = x ^ r_aes(key, {iv, 32'h1});
  for (int j = 0; j < 12; j++) tb_[16 + plen + j] = tag[8*(15 - j) +: 8];
  tn = 16 + plen + 12;
endtask

logic [31:0] ob [0:63];
integer on = 0, nrep = 0, nlast = 0, ndel = 0;
logic [2:0] st;
always @(posedge clk) begin
  if (out_valid) begin ob[on] = out_dw; on = on + 1; if (out_last) nlast = nlast + 1; end
  if (rep_valid && rep_status <= 3'd1 && out_last) ndel = ndel + 1;
  if (rep_valid) begin nrep = nrep + 1; st = rep_status; end
end
task automatic send();
  integer r0, k;
  r0 = nrep; on = 0;
  for (int i = 0; i < 256; i += 4)
    if (i < tn) begin
      @(negedge clk); in_valid = 1; in_dw = {tb_[i], tb_[i + 1], tb_[i + 2], tb_[i + 3]}; in_last = (i + 4 >= tn);
    end
  @(negedge clk); in_valid = 0; in_last = 0;
  k = 0;
  while (k < 200 && nrep == r0) begin @(negedge clk); k = k + 1; end
  @(negedge clk);
endtask
// delivered: header DWs and the plaintext
function automatic logic delivered(input integer ndw);
  logic ok;
  ok = (on == 3 + ndw);
  for (int i = 0; i < 3; i++) if (ob[i] !== {tb_[4 + 4*i], tb_[5 + 4*i], tb_[6 + 4*i], tb_[7 + 4*i]}) ok = 0;
  for (int i = 0; i < 16; i++) if (i < ndw && ob[3 + i] !== {pt[4*i], pt[4*i + 1], pt[4*i + 2], pt[4*i + 3]}) ok = 0;
  delivered = ok;
endfunction
task automatic want(input integer s, input integer ndw, input string msg);
  if (s == 0) chk(st == 3'd0 && delivered(ndw), msg);
  else chk(st == s && on == 0, msg);
endtask
task automatic set_go(input integer sid);
  for (int i = 0; i < 256; i++) tb_[i] = 8'h00;
  tb_[0] = 8'h72; tb_[3] = 8'h01; tb_[7] = 8'h7F; tb_[12] = 8'h05; tb_[14] = sid;
  tn = 16;
  send();
endtask

initial begin
  logic [127:0] h0;
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && out_valid === 1'b0 && out_last === 1'b0, "nothing out in reset");
  rst_n = 1;
  chk(r_aes(KB, 128'h0011_2233_4455_6677_8899_AABB_CCDD_EEFF) == 128'h8EA2_B7CA_5167_45BF_EAFC_4990_4B49_6089,
      "reference AES-256: FIPS-197 C.3");
  h0 = r_aes(0, 0);
  chk(h0 == 128'hDC95_C078_A240_8989_AD48_A214_9284_2087, "reference H for the zero 256-bit key (GCM test case 13)");
  chk(r_aes(0, 1) == 128'h530F_8AFB_C745_36B9_A963_B4F1_C4CB_738B, "GCM test case 13 tag");
  chk(r_aes(0, 2) == 128'hCEA7_403D_4D60_6B6E_074E_C5D3_BAF3_9D18, "GCM test case 14 ciphertext");
  chk((r_gmul(r_gmul(128'hCEA7_403D_4D60_6B6E_074E_C5D3_BAF3_9D18, h0) ^ 128'd128, h0) ^ r_aes(0, 1)) ==
      128'hD0D1_C8A7_9999_6BF0_265B_98B5_D48A_B919, "GCM test case 14 tag");
  repeat (4) @(negedge clk);
  chk(nrep == 0 && on == 0, "no status or output without a TLP");

  // every sub-stream and key set; counters count per sub-stream / key set
  ide(0, 1, 0, 0, 3, 1); send(); want(0, 1, "MWr 1 DW, posted, key set 0, counter 1");
  ide(0, 8, 0, 0, 3, 2); send(); want(0, 8, "MWr 8 DW, counter 2");
  ide(0, 5, 0, 1, 3, 1); send(); want(0, 5, "MWr on key set 1 starts at counter 1");
  ide(1, 4, 1, 0, 3, 1); send(); want(0, 0, "MRd (no payload), non-posted");
  ide(2, 3, 2, 0, 3, 1); send(); want(0, 3, "CplD, completions");
  ide(2, 4, 2, 1, 3, 1); send(); want(0, 4, "CplD on key set 1");
  ide(2, 2, 2, 0, 3, 2); send(); want(0, 2, "CplD key set 0 counter 2");
  ide(0, 3, 0, 0, 3, 3); send(); want(0, 3, "MWr key set 0 counter 3");
  // plain TLP
  ide(0, 2, 0, 0, 3, 9); for (int i = 0; i < 16 + 8; i++) tb_[i] = tb_[i + 4]; tb_[0] = 8'h40; tn = 12 + 8;
  for (int i = 0; i < 8; i++) tb_[12 + i] = pt[i];
  send();
  chk(st == 3'd1 && on == 5 && ob[0] == {tb_[0], tb_[1], tb_[2], tb_[3]} && ob[1] == {tb_[4], tb_[5], tb_[6], tb_[7]} &&
      ob[3] == {pt[0], pt[1], pt[2], pt[3]} && ob[4] == {pt[4], pt[5], pt[6], pt[7]}, "TLP without a prefix: delivered as it came");
  for (int i = 0; i < 256; i++) tb_[i] = 8'h00;
  tb_[0] = 8'h92; tb_[2] = 8'd3; tn = 4; send(); want(2, 0, "a lone IDE prefix DW: dropped");
  tb_[0] = 8'h40; tn = 192; send(); chk(st == 3'd1 && on == 48, "48-DW plain TLP: delivered");
  tn = 196; send(); want(2, 0, "49-DW TLP (over the model's buffer): dropped");
  ide(0, 9, 0, 0, 3, 4); tn = 16 + 36 + 12; send(); want(2, 0, "9-DW payload (over the model's 8): dropped");
  // bad IDE TLPs: dropped, not counted
  ide(0, 2, 0, 0, 5, 4); send(); want(2, 0, "stream 5: dropped");
  ide(0, 2, 1, 0, 3, 4); send(); want(2, 0, "MWr on the non-posted sub-stream: dropped");
  ide(1, 2, 0, 0, 3, 4); send(); want(2, 0, "MRd on the posted sub-stream: dropped");
  ide(0, 2, 0, 0, 3, 4, 0); send(); want(2, 0, "M = 0: dropped");
  ide(0, 2, 0, 0, 3, 4, 1, 1); send(); want(2, 0, "P = 1: dropped");
  ide(0, 2, 0, 0, 3, 4); tn = tn - 4; send(); want(2, 0, "MAC DW missing: dropped");
  ide(0, 2, 0, 0, 3, 4); tb_[4] = 8'h60; send(); want(2, 0, "unknown TLP type 0x60: dropped");
  ide(0, 2, 0, 0, 3, 4); send(); want(0, 2, "posted key set 0 still at counter 4");
  // MAC failure: the stream goes insecure
  ide(0, 2, 0, 0, 3, 5); tb_[16] = tb_[16] ^ 8'h01; send(); want(3, 0, "payload bit flipped: MAC fails");
  ide(0, 2, 0, 0, 3, 5); send(); want(4, 0, "next IDE TLP: insecure");
  ide(2, 1, 2, 1, 3, 2); send(); want(4, 0, "other sub-streams too");
  ide(0, 2, 0, 0, 3, 9); for (int i = 0; i < 24; i++) tb_[i] = tb_[i + 4]; tb_[0] = 8'h40; tn = 20;
  send(); chk(st == 3'd1, "plain TLPs still pass while insecure");
  set_go(4); chk(st == 3'd1 && on == 4, "K_SET_GO for stream 4: just a message");
  set_go(3); chk(st == 3'd5 && on == 0, "K_SET_GO for stream 3: consumed");
  ide(0, 2, 0, 0, 3, 1); send(); want(0, 2, "after K_SET_GO: counter 1 again");
  ide(2, 1, 2, 1, 3, 1); send(); want(0, 1, "every counter reset");
  // replay and loss, header and MAC faults (re-key after each)
  ide(0, 2, 0, 0, 3, 1); send(); want(3, 0, "counter 1 replayed: MAC fails");
  set_go(3);
  ide(0, 2, 0, 0, 3, 2); send(); want(3, 0, "counter 2 where 1 is due (a TLP lost): MAC fails");
  set_go(3);
  ide(0, 2, 0, 0, 3, 1); tb_[9] = tb_[9] ^ 8'h40; send(); want(3, 0, "header bit flipped (AAD): MAC fails");
  set_go(3);
  ide(1, 1, 1, 0, 3, 1); tb_[16] = tb_[16] ^ 8'h80; send(); want(3, 0, "MRd MAC bit flipped");
  set_go(3);
  ide(0, 3, 0, 0, 3, 1, 1, 0); tb_[1][6] = 1'b1; send(); want(3, 0, "key set bit changed: other key, MAC fails");
  set_go(3);
  ide(0, 2, 0, 1, 3, 1); tb_[1][5] = 1'b0; send(); want(3, 0, "T bit is in the AAD");
  set_go(3);
  ide(0, 3, 0, 1, 3, 1); send(); want(0, 3, "key set 1 after the faults");
  chk(nlast == 16 && ndel == 16, $sformatf("one last-DW strobe per delivered TLP (%0d / %0d)", nlast, ndel));

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #50000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
