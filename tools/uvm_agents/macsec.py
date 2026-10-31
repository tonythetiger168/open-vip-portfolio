# IEEE 802.1AE MACsec agent (GCM-AES-128): the agent is the peer's transmit
# SecY and sends protected frames; the DUT is the receive SecY.
#
# Wires: in_valid, in_data[7:0], in_last (one frame byte per clock, no
# preamble or FCS) towards the DUT; out_valid, out_data[7:0], out_last (the
# frame delivered to the controlled port: DA, SA, user data) and rep_valid,
# rep_status[2:0] (one per received frame; on the last output byte when
# there is output) back.
#
# Frame: DA, SA, SecTAG (EtherType 0x88E5, TCI/AN {V, ES, SC, SCB, E, C,
# AN[1:0]}, SL (short length), PN[31:0], SCI[63:0] when SC = 1), secure
# data, ICV (16 bytes). With E = C = 1 the user data is encrypted (AAD = DA,
# SA, SecTAG); with E = C = 0 it is only authenticated (AAD = the whole frame
# before the ICV). IV = SCI || PN; without SC the SCI is SA || 0x0001.
#
# tb/top_tb.sv macsec_model: one receive SC (SCI 00:12:34:56:78:9A / port 1)
# with SAs on AN 0 and AN 1 (fixed SAKs), validateFrames Strict,
# replayProtect with window 0 (each SA keeps its lowest acceptable PN, 1
# after reset, PN + 1 after a frame passes). rep_status:
#   0 passed: DA, SA and the (decrypted) user data delivered
#   1 untagged (EtherType not 0x88E5)
#   2 bad tag: V set, ES with SC, SC with SCB, E differing from C, PN 0, SL
#     not below 48, SL not the data length (under 48) or not 0 (48 and
#     more), or a frame too short for the SecTAG and ICV
#   3 no SA: another SCI, or AN 2 / 3
#   4 late: PN below the SA's lowest acceptable PN
#   5 ICV check failed (the PN is not consumed)

MACSEC_FUNCS = """
localparam bit [63:0]  MCS_PEER_SCI = 64'h0012_3456_789A_0001;
localparam bit [47:0]  MCS_PEER_SA  = 48'h0012_3456_789A;
localparam bit [47:0]  MCS_DA       = 48'h02AA_BBCC_DDEE;
function automatic bit [127:0] mcs_key(bit [1:0] an);
  case (an)
    2'd0: return 128'hFEFF_E992_8665_731C_6D6A_8F94_6730_8308;
    2'd1: return 128'hAD7A_2BD0_3EAC_835A_6F62_0FDC_B506_B345;
    default: return 128'h0;
  endcase
endfunction
function automatic bit [7:0] mcs_xt(bit [7:0] a); return {a[6:0], 1'b0} ^ (a[7] ? 8'h1B : 8'h00); endfunction
function automatic bit [7:0] mcs_gm(bit [7:0] a, bit [7:0] b);
  bit [7:0] p = 0;
  for (int i = 0; i < 8; i++) begin
    if (b[i]) p ^= a;
    a = mcs_xt(a);
  end
  return p;
endfunction
// AES S-box: inverse in GF(2^8) (a^254), then the affine map
function automatic bit [7:0] mcs_sbox(bit [7:0] a);
  bit [7:0] r = 8'h01;
  for (int i = 7; i >= 0; i--) begin
    r = mcs_gm(r, r);
    if (i != 0) r = mcs_gm(r, a);
  end
  return r ^ {r[6:0], r[7]} ^ {r[5:0], r[7:6]} ^ {r[4:0], r[7:5]} ^ {r[3:0], r[7:4]} ^ 8'h63;
endfunction
// AES-128 encryption, byte 0 in bits 127:120
function automatic bit [127:0] mcs_aes(bit [127:0] key, bit [127:0] blk);
  bit [127:0] s = blk ^ key, k = key, t;
  bit [7:0] rc = 8'h01, a0, a1, a2, a3;
  bit [31:0] w;
  for (int r = 1; r <= 10; r++) begin
    for (int c = 0; c < 4; c++)
      for (int j = 0; j < 4; j++)
        t[127 - 8*(4*c + j) -: 8] = mcs_sbox(s[127 - 8*(4*((c + j) % 4) + j) -: 8]);
    if (r != 10)
      for (int c = 0; c < 4; c++) begin
        a0 = t[127 - 32*c -: 8]; a1 = t[119 - 32*c -: 8]; a2 = t[111 - 32*c -: 8]; a3 = t[103 - 32*c -: 8];
        t[127 - 32*c -: 8] = mcs_xt(a0) ^ mcs_xt(a1) ^ a1 ^ a2 ^ a3;
        t[119 - 32*c -: 8] = a0 ^ mcs_xt(a1) ^ mcs_xt(a2) ^ a2 ^ a3;
        t[111 - 32*c -: 8] = a0 ^ a1 ^ mcs_xt(a2) ^ mcs_xt(a3) ^ a3;
        t[103 - 32*c -: 8] = mcs_xt(a0) ^ a0 ^ a1 ^ a2 ^ mcs_xt(a3);
      end
    w = k[31:0];
    w = {mcs_sbox(w[23:16]) ^ rc, mcs_sbox(w[15:8]), mcs_sbox(w[7:0]), mcs_sbox(w[31:24])};
    k[127:96] ^= w; k[95:64] ^= k[127:96]; k[63:32] ^= k[95:64]; k[31:0] ^= k[63:32];
    rc = mcs_xt(rc);
    s = t ^ k;
  end
  return s;
endfunction
// GHASH multiply in GF(2^128) (GCM bit order)
function automatic bit [127:0] mcs_gmul(bit [127:0] x, bit [127:0] y);
  bit [127:0] z = 0, v = y;
  for (int i = 0; i < 128; i++) begin
    if (x[127 - i]) z ^= v;
    v = v[0] ? ((v >> 1) ^ {8'hE1, 120'h0}) : (v >> 1);
  end
  return z;
endfunction
function automatic bit [127:0] mcs_ghash(bit [127:0] h, bit [127:0] x, bit [7:0] q[$]);
  for (int i = 0; i < q.size(); i += 16) begin
    bit [127:0] b = 0;
    for (int j = 0; j < 16; j++) if (i + j < q.size()) b[127 - 8*j -: 8] = q[i + j];
    x = mcs_gmul(x ^ b, h);
  end
  return x;
endfunction
// GCM with a 96-bit IV: out = text XOR keystream; returns the tag over aad and
// the ciphertext (out when enc, text otherwise)
function automatic bit [127:0] mcs_gcm(bit [127:0] key, bit [95:0] iv, bit [7:0] aad[$], bit [7:0] txt[$], bit enc,
                                       output bit [7:0] out[$]);
  bit [127:0] h = mcs_aes(key, 128'h0), x, ks;
  bit [63:0] la = 64'(aad.size()) * 8, lc = 64'(txt.size()) * 8;
  out.delete();
  for (int i = 0; i < txt.size(); i += 16) begin
    ks = mcs_aes(key, {iv, 32'(2 + i / 16)});
    for (int j = 0; j < 16; j++) if (i + j < txt.size()) out.push_back(txt[i + j] ^ ks[127 - 8*j -: 8]);
  end
  x = mcs_ghash(h, 128'h0, aad);
  if (enc) x = mcs_ghash(h, x, out);
  else     x = mcs_ghash(h, x, txt);
  x = mcs_gmul(x ^ {la, lc}, h);
  return x ^ mcs_aes(key, {iv, 32'h1});
endfunction
"""

SPEC = dict(
    vip="MACsec-UVM-VIP", p="macsec", P="MACsec", dir="macsec", family="Security",
    desc="IEEE 802.1AE MACsec VIP (GCM-AES-128): protected frames with SecTAG, SCI, PN and ICV, confidentiality and "
         "integrity-only modes, receive SecY model with tag checks, SA lookup, replay protection and ICV validation.",
    about="""
MACsec secures Ethernet hop by hop: every frame carries a SecTAG (association
number, packet number, optional SCI) and a 16-byte ICV, and its user data is
encrypted with GCM-AES. The agent is the peer's transmit SecY with its own
AES-128 and GHASH; the DUT model is a receive SecY with two installed SAs,
validateFrames Strict and replay protection. The scoreboard keeps each SA's
lowest acceptable PN, opens every frame itself and predicts the status and
the delivered frame. Planted faults (tag bits, SL, PN 0, a foreign SCI or
AN, a replayed PN, a flipped ICV or ciphertext bit, an untagged frame) make
each receive check visible. The smoke test checks its own AES and GCM
against FIPS-197 and the GCM specification's test cases first.""",
    defs=MACSEC_FUNCS,
    timeout=2000,
    ports=[
        ("in", "logic", "in_valid"), ("in", "logic [7:0]", "in_data"), ("in", "logic", "in_last"),
        ("out", "logic", "out_valid"), ("out", "logic [7:0]", "out_data"), ("out", "logic", "out_last"),
        ("out", "logic", "rep_valid"), ("out", "logic [2:0]", "rep_status"),
    ],
    fields=[
        ("bit", "untag", "req"),
        ("bit [47:0]", "sa", "req"),
        ("bit [5:0]", "tci", "req"),        # V ES SC SCB E C
        ("bit [1:0]", "an", "req"),
        ("bit [5:0]", "sl", "req"),
        ("bit [31:0]", "pn", "req"),
        ("bit [63:0]", "sci", "req"),       # 0 unless SC
        ("bit [7:0]", "body", "req", "q"),  # secure data and ICV as sent (user data when untagged)
        ("bit [2:0]", "status", "rsp"),
        ("bit [7:0]", "odata", "rsp", "q"),
        ("bit [7:0]", "pt", "info", "q"),   # user data before protection
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit", "e_r", "info", "rand"),
        ("bit", "sc_r", "info", "rand"),
        ("bit", "es_r", "info", "rand"),
        ("bit", "an_r", "info", "rand"),
        ("bit [6:0]", "n_r", "info", "rand"),
        ("bit [2:0]", "psel", "info", "rand"),  # 6 replay the last PN, 7 jump ahead
        ("bit [1:0]", "icv", "info"),           # 1 ICV bit flipped, 2 secure-data bit flipped
        ("bit", "zero_pn", "info"),
        ("bit", "short_b", "info"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_n { n_r >= 2; n_r <= 80; }
""",
    tr_functions="""
// kind: 0-19 good, 20 untagged, 21 V, 22 ES+SC, 23 SC+SCB, 24 C without E, 25 E without C,
// 26 PN 0, 27 SL wrong, 28 body too short, 29 foreign SCI, 30 AN 2/3, 31 ICV / data corrupted
function void post_randomize(); mk(kind, e_r, sc_r, es_r, an_r, n_r); endfunction
function void mk(int k, bit e_, bit sc_, bit es_, bit [1:0] an_, int n_);
  bit [31:0] x = seed | 1;
  untag = (k == 20); icv = 0; zero_pn = 0; short_b = 0;
  sa = MCS_PEER_SA; sci = MCS_PEER_SCI; an = an_; pn = 0;
  tci = {1'b0, sc_ ? 1'b0 : es_, sc_, 1'b0, e_, e_};
  pt.delete();
  for (int i = 0; i < n_; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    pt.push_back(x[7:0]);
  end
  sl = (n_ < 48) ? 6'(n_) : 6'd0;
  case (k)
    21: tci[5] = 1'b1;
    22: tci[4:3] = 2'b11;
    23: tci[3:2] = 2'b11;
    24: tci[1:0] = 2'b01;
    25: tci[1:0] = 2'b10;
    26: zero_pn = 1;
    27: sl = (n_ < 48) ? 6'((n_ + 1) % 48) : 6'd5;
    28: short_b = 1;
    29: if (tci[3]) sci ^= 64'h100; else sa ^= 48'h1;
    30: an = {1'b1, an_[0]};
    31: icv = x[9] ? 2'd1 : 2'd2;
    default: ;
  endcase
  if (untag) begin
    tci = 0; an = 0; sl = 0; sci = 0;
    pt[0] = 8'h08; pt[1] = 8'h00;
  end
  if (!tci[3]) sci = 0;
endfunction

// DA, SA, SecTAG
function void hdr(output bit [7:0] b[$]);
  b.delete();
  for (int i = 5; i >= 0; i--) b.push_back(MCS_DA[8*i +: 8]);
  for (int i = 5; i >= 0; i--) b.push_back(sa[8*i +: 8]);
  if (untag) return;
  b.push_back(8'h88); b.push_back(8'hE5);
  b.push_back({tci, an}); b.push_back({2'b00, sl});
  for (int i = 3; i >= 0; i--) b.push_back(pn[8*i +: 8]);
  if (tci[3]) for (int i = 7; i >= 0; i--) b.push_back(sci[8*i +: 8]);
endfunction
function bit [63:0] iv_sci(); return tci[3] ? sci : {sa, 16'h0001}; endfunction

// body from pt (pn already set)
function void seal();
  bit [7:0] h[$], a[$], o[$], none[$];
  bit [127:0] tag;
  body.delete();
  if (untag) begin body = pt; return; end
  hdr(h);
  if (tci[1]) tag = mcs_gcm(mcs_key(an), {iv_sci(), pn}, h, pt, 1'b1, o);
  else begin
    a = h;
    foreach (pt[i]) a.push_back(pt[i]);
    tag = mcs_gcm(mcs_key(an), {iv_sci(), pn}, a, none, 1'b1, o);
    o = pt;
  end
  if (icv == 1) tag[0] = ~tag[0];
  if (icv == 2) o[0][3] = ~o[0][3];
  body = o;
  for (int i = 15; i >= 0; i--) body.push_back(tag[8*i +: 8]);
  if (short_b) while (body.size() > 10) void'(body.pop_back());
endfunction
function void frame(output bit [7:0] b[$]);
  hdr(b);
  foreach (body[i]) b.push_back(body[i]);
endfunction
// request fields from a received frame
function void from_frame(bit [7:0] b[$]);
  int h;
  sa = {b[6], b[7], b[8], b[9], b[10], b[11]};
  untag = ({b[12], b[13]} != 16'h88E5);
  tci = 0; an = 0; sl = 0; pn = 0; sci = 0; body.delete();
  if (untag) begin
    for (int i = 12; i < b.size(); i++) body.push_back(b[i]);
    return;
  end
  {tci, an} = b[14]; sl = b[15][5:0];
  pn = {b[16], b[17], b[18], b[19]};
  h = 20;
  if (tci[3]) begin sci = {b[20], b[21], b[22], b[23], b[24], b[25], b[26], b[27]}; h = 28; end
  for (int i = h; i < b.size(); i++) body.push_back(b[i]);
endfunction
function bit tag_bad();
  int n = body.size() - 16;
  return body.size() < 16 || tci[5] || (tci[4] && tci[3]) || (tci[3] && tci[2]) || (tci[1] != tci[0]) || pn == 0 ||
         sl >= 48 || (sl != 0 && sl != n) || (sl == 0 && n < 48);
endfunction
""",
    drv_rsp=True,
    drv_desc="one protected frame per item: PN from the driver's per-AN counter (or replayed / zero), sealed with GCM-AES-128, sent a byte a clock; then the delivered frame and status",
    drv_members="bit [31:0] last_pn [4] = '{0, 0, 0, 0};",
    drv_idle="""
vif.drv_cb.in_valid <= 1'b0;
vif.drv_cb.in_data  <= 8'h00;
vif.drv_cb.in_last  <= 1'b0;
""",
    drv_item="""
bit [7:0] b[$];
int k = 0;
if (!t.untag) begin
  case (t.psel)
    3'd6: t.pn = last_pn[t.an];
    3'd7: t.pn = last_pn[t.an] + 100;
    default: t.pn = last_pn[t.an] + 1;
  endcase
  if (t.zero_pn) t.pn = 0;
  else if (t.pn > last_pn[t.an]) last_pn[t.an] = t.pn;
end
t.seal();
t.frame(b);
foreach (b[i]) begin
  vif.drv_cb.in_valid <= 1'b1; vif.drv_cb.in_data <= b[i]; vif.drv_cb.in_last <= (i == b.size() - 1);
  @(vif.drv_cb);
end
vif.drv_cb.in_valid <= 1'b0; vif.drv_cb.in_last <= 1'b0;
t.odata.delete();
do begin
  @(vif.drv_cb);
  if (vif.drv_cb.out_valid) t.odata.push_back(vif.drv_cb.out_data);
  k++;
end while (!vif.drv_cb.rep_valid && k < cfg.timeout_cycles);
if (!vif.drv_cb.rep_valid) `uvm_error("DRV", "MACsec: no status for a frame")
t.status = vif.drv_cb.rep_status;
repeat (2) @(vif.drv_cb);
""",
    mon_desc="frames into the SecY, then the delivered bytes and the status that close each one",
    mon_run="""
bit [7:0] b[$], o[$];
bit [7:0] frames[$][$];
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.in_valid) begin
    b.push_back(vif.mon_cb.in_data);
    if (vif.mon_cb.in_last) begin frames.push_back(b); b.delete(); end
  end
  if (vif.mon_cb.out_valid) o.push_back(vif.mon_cb.out_data);
  if (vif.mon_cb.rep_valid) begin
    if (frames.size() == 0) `uvm_error("MON", "MACsec: status without a frame")
    else begin
      macsec_transaction t = macsec_transaction::type_id::create("t");
      t.from_frame(frames.pop_front());
      t.odata = o;
      t.status = vif.mon_cb.rep_status;
      publish(t);
    end
    o.delete();
  end
end
""",
    sb_members="""bit [31:0] next_pn [2] = '{1, 1};
bit kat_done = 0;""",
    predict="""
bit [7:0] h[$], a[$], c[$], p[$], none[$];
bit [127:0] tag, icv;
int n;
if (!kat_done) begin
  // FIPS-197 C.1 and GCM test case 2 on the scoreboard's own AES / GHASH
  kat_done = 1;
  if (mcs_aes(128'h0001_0203_0405_0607_0809_0A0B_0C0D_0E0F, 128'h0011_2233_4455_6677_8899_AABB_CCDD_EEFF) !=
      128'h69C4_E0D8_6A7B_0430_D8CD_B780_70B4_C55A) `uvm_error("SB", "MACsec: AES-128 known answer wrong")
  if ((mcs_gmul(mcs_gmul(128'h0388_DACE_60B6_A392_F328_C2B9_71B2_FE78, mcs_aes(0, 0)) ^ 128'd128, mcs_aes(0, 0)) ^ mcs_aes(0, 1)) !=
      128'hAB6E_47D4_2CEC_13BD_F53A_67B2_1257_BDDF) `uvm_error("SB", "MACsec: GCM known answer wrong")
end
t.odata.delete();
if (t.untag) t.status = 1;
else if (t.tag_bad()) t.status = 2;
else if (t.iv_sci() != MCS_PEER_SCI || t.an > 1) t.status = 3;
else if (t.pn < next_pn[t.an[0]]) t.status = 4;
else begin
  n = t.body.size() - 16;
  t.hdr(h);
  for (int i = 0; i < n; i++) c.push_back(t.body[i]);
  for (int i = 0; i < 16; i++) icv[127 - 8*i -: 8] = t.body[n + i];
  if (t.tci[1]) tag = mcs_gcm(mcs_key(t.an), {t.iv_sci(), t.pn}, h, c, 1'b0, p);
  else begin
    a = h;
    foreach (c[i]) a.push_back(c[i]);
    tag = mcs_gcm(mcs_key(t.an), {t.iv_sci(), t.pn}, a, none, 1'b0, p);
    p = c;
  end
  if (tag != icv) t.status = 5;
  else begin
    t.status = 0;
    next_pn[t.an[0]] = t.pn + 1;
    for (int i = 0; i < 12; i++) t.odata.push_back(h[i]);
    foreach (p[i]) t.odata.push_back(p[i]);
  end
end
""",
    checks="""
if (t.status != 0 && t.odata.size() != 0) fail(t, "frame delivered although it was not validated");
""",
    coverage="""
cp_status : coverpoint tr.status { bins passed = {0}; bins untagged = {1}; bins bad_tag = {2}; bins no_sa = {3};
                                   bins late = {4}; bins icv_fail = {5}; }
cp_mode : coverpoint tr.tci[1] iff (tr.status == 0) { bins integrity = {0}; bins confidential = {1}; }
cp_sci : coverpoint tr.tci[4:3] iff (tr.status == 0) { bins implicit = {2'b00}; bins es = {2'b10}; bins explicit = {2'b01}; }
cp_an : coverpoint tr.an iff (tr.status == 0) { bins an0 = {0}; bins an1 = {1}; }
cp_sl : coverpoint (tr.sl != 0) iff (tr.status == 0) { bins long_frame = {0}; bins short_frame = {1}; }
x_mode_sl : cross cp_mode, cp_sl;
""",
    directed="""
// both modes, every SCI form, both SAs, short and long data; then each fault
for (int e = 0; e < 2; e++) begin
  t = item(); t.mk(0, e, 1, 0, 0, 30); t.psel = 0; send(t);
  t = item(); t.mk(0, e, 1, 0, 1, 60); t.psel = 0; send(t);
  t = item(); t.mk(0, e, 0, 0, 0, 47); t.psel = 0; send(t);
  t = item(); t.mk(0, e, 0, 1, 1, 48); t.psel = 0; send(t);
end
for (int k = 20; k < 32; k++) begin
  t = item(); t.mk(k, 1, 1, 0, 0, 40); t.psel = 0; send(t);
end
// replay: the last PN again (passed before), then a resend of a PN whose frame failed its ICV
t = item(); t.mk(0, 1, 1, 0, 0, 20); t.psel = 0; send(t);
t = item(); t.mk(0, 1, 1, 0, 0, 20); t.psel = 6; send(t);
t = item(); t.mk(31, 1, 1, 0, 1, 20); t.psel = 0; send(t);
t = item(); t.mk(0, 1, 1, 0, 1, 20); t.psel = 6; send(t);
t = item(); t.mk(0, 0, 1, 0, 1, 50); t.psel = 7; send(t);
""",
    drain_ns=4000,
    model="""
module macsec_model (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       in_valid,
  input  logic [7:0] in_data,
  input  logic       in_last,
  output logic       out_valid,
  output logic [7:0] out_data,
  output logic       out_last,
  output logic       rep_valid,
  output logic [2:0] rep_status
);
  localparam logic [127:0] K0   = 128'hFEFF_E992_8665_731C_6D6A_8F94_6730_8308;
  localparam logic [127:0] K1   = 128'hAD7A_2BD0_3EAC_835A_6F62_0FDC_B506_B345;
  localparam logic [63:0]  PEER = 64'h0012_3456_789A_0001;

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
  function automatic logic [127:0] aes(input logic [127:0] key, input logic [127:0] blk);
    logic [127:0] s, k, t;
    logic [7:0]   rc, a0, a1, a2, a3;
    logic [31:0]  w;
    s = blk ^ key; k = key; rc = 8'h01;
    for (int r = 1; r <= 10; r++) begin
      for (int c = 0; c < 4; c++)
        for (int j = 0; j < 4; j++)
          t[127 - 8*(4*c + j) -: 8] = sbox(s[127 - 8*(4*((c + j) % 4) + j) -: 8]);
      if (r != 10)
        for (int c = 0; c < 4; c++) begin
          a0 = t[127 - 32*c -: 8]; a1 = t[119 - 32*c -: 8]; a2 = t[111 - 32*c -: 8]; a3 = t[103 - 32*c -: 8];
          t[127 - 32*c -: 8] = xt(a0) ^ xt(a1) ^ a1 ^ a2 ^ a3;
          t[119 - 32*c -: 8] = a0 ^ xt(a1) ^ xt(a2) ^ a2 ^ a3;
          t[111 - 32*c -: 8] = a0 ^ a1 ^ xt(a2) ^ xt(a3) ^ a3;
          t[103 - 32*c -: 8] = xt(a0) ^ a0 ^ a1 ^ a2 ^ xt(a3);
        end
      w = k[31:0];
      w = {sbox(w[23:16]) ^ rc, sbox(w[15:8]), sbox(w[7:0]), sbox(w[31:24])};
      k[127:96] = k[127:96] ^ w;
      k[95:64]  = k[95:64] ^ k[127:96];
      k[63:32]  = k[63:32] ^ k[95:64];
      k[31:0]   = k[31:0] ^ k[63:32];
      rc = xt(rc);
      s = t ^ k;
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

  logic [7:0]  rb [0:127];      // received frame
  logic [7:0]  ob [0:127];      // frame delivered
  logic [7:0]  nrb, olen, opos;
  logic        go, busy;
  logic [31:0] npn0, npn1;      // lowest acceptable PN of AN 0 / AN 1

  // 16 frame bytes from 'from' (zero at and after 'lim')
  function automatic logic [127:0] blk(input integer from, input integer lim);
    logic [127:0] v;
    for (int j = 0; j < 16; j++) v[127 - 8*j -: 8] = (from + j < lim) ? rb[from + j] : 8'h00;
    blk = v;
  endfunction
  function automatic logic [127:0] ghash(input logic [127:0] h, input logic [127:0] x0, input integer from,
                                         input integer lim);
    logic [127:0] x;
    x = x0;
    for (int b = 0; b < 8; b++) if (from + 16*b < lim) x = gmul(x ^ blk(from + 16*b, lim), h);
    ghash = x;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nrb <= '0; olen <= '0; opos <= '0; go <= 1'b0; busy <= 1'b0; npn0 <= 32'd1; npn1 <= 32'd1;
      out_valid <= 1'b0; out_data <= '0; out_last <= 1'b0; rep_valid <= 1'b0; rep_status <= '0;
    end else begin
      rep_valid <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
      go <= in_valid && in_last;
      if (in_valid) begin
        if (nrb < 8'd128) rb[nrb[6:0]] <= in_data;
        nrb <= nrb + 8'd1;
      end
      if (go) begin : receive
        logic [5:0]   tci;
        logic [1:0]   an;
        logic [31:0]  pn;
        logic [63:0]  sci;
        logic [127:0] key, hk, x, tag, ks, cb;
        logic [63:0]  la, lc;
        logic [2:0]   st;
        integer       n, h, dn, alen;
        n = nrb; st = 3'd0;
        nrb <= '0;
        if (n < 14 || {rb[12], rb[13]} != 16'h88E5) st = 3'd1;
        else begin
          tci = rb[14][7:2]; an = rb[14][1:0];
          pn = {rb[16], rb[17], rb[18], rb[19]};
          h = tci[3] ? 28 : 20;
          dn = n - h - 16;
          if (n < h + 16 || tci[5] || (tci[4] && tci[3]) || (tci[3] && tci[2]) || (tci[1] != tci[0]) || pn == 32'd0 ||
              rb[15] >= 8'd48 || (rb[15] != 8'd0 && rb[15] != dn) || (rb[15] == 8'd0 && dn < 48)) st = 3'd2;
          else begin
            sci = tci[3] ? {rb[20], rb[21], rb[22], rb[23], rb[24], rb[25], rb[26], rb[27]}
                         : {rb[6], rb[7], rb[8], rb[9], rb[10], rb[11], 16'h0001};
            if (sci != PEER || an[1]) st = 3'd3;
            else if (pn < (an[0] ? npn1 : npn0)) st = 3'd4;
            else begin
              key = an[0] ? K1 : K0;
              hk = aes(key, 128'h0);
              alen = tci[1] ? h : h + dn;
              x = ghash(hk, 128'h0, 0, alen);
              if (tci[1]) x = ghash(hk, x, h, h + dn);
              la = alen * 8;
              lc = tci[1] ? dn * 8 : 0;
              x = gmul(x ^ {la, lc}, hk);
              tag = x ^ aes(key, {sci, pn, 32'h1});
              if (tag != blk(n - 16, n)) st = 3'd5;
              else begin
                if (an[0]) npn1 <= pn + 32'd1; else npn0 <= pn + 32'd1;
                for (int i = 0; i < 12; i++) ob[i] <= rb[i];
                for (int b = 0; b < 6; b++)
                  if (16*b < dn) begin
                    ks = tci[1] ? aes(key, {sci, pn, 32'd2 + b}) : 128'h0;
                    cb = blk(h + 16*b, h + dn);
                    for (int j = 0; j < 16; j++)
                      if (16*b + j < dn) ob[12 + 16*b + j] <= cb[127 - 8*j -: 8] ^ ks[127 - 8*j -: 8];
                  end
                olen <= 8'(12 + dn);
                opos <= '0;
                busy <= 1'b1;
              end
            end
          end
        end
        if (st != 3'd0) begin rep_valid <= 1'b1; rep_status <= st; end
      end
      if (busy) begin
        out_valid <= 1'b1;
        out_data <= ob[opos[6:0]];
        opos <= opos + 8'd1;
        if (opos == olen - 8'd1) begin
          out_last <= 1'b1; busy <= 1'b0;
          rep_valid <= 1'b1; rep_status <= 3'd0;
        end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({in_valid, out_valid, rep_valid}))
  else $error("MACsec: X on a valid");
assert property (@(posedge clk) disable iff (!rst_n) out_valid |-> !$isunknown(out_data))
  else $error("MACsec: X on delivered data");
// the last delivered byte comes with the status 0
assert property (@(posedge clk) disable iff (!rst_n) out_last |-> rep_valid && rep_status == 3'd0)
  else $error("MACsec: last delivered byte without a pass status");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd5);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd4);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic in_valid = 1'b0, in_last = 1'b0;
logic [7:0] in_data = 8'h00;
wire out_valid, out_last, rep_valid;
wire [7:0] out_data;
wire [2:0] rep_status;

always #5 clk = ~clk;

macsec_model u_dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data), .in_last(in_last),
                    .out_valid(out_valid), .out_data(out_data), .out_last(out_last),
                    .rep_valid(rep_valid), .rep_status(rep_status));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// reference AES-128 / GHASH (checked against FIPS-197 and the GCM test cases below)
function automatic logic [7:0] r_xt(input logic [7:0] a); r_xt = {a[6:0], 1'b0} ^ (a[7] ? 8'h1B : 8'h00); endfunction
function automatic logic [7:0] r_inv(input logic [7:0] a);
  // brute-force inverse: the b with a * b = 1
  logic [7:0] p, x, y;
  r_inv = 8'h00;
  for (int b = 1; b < 256; b++) begin
    p = 8'h00; x = a; y = b;
    for (int i = 0; i < 8; i++) begin
      if (y[i]) p = p ^ x;
      x = r_xt(x);
    end
    if (p == 8'h01) r_inv = b;
  end
endfunction
logic [7:0] sb [0:255];
initial for (int i = 0; i < 256; i++) begin : mk_sbox
  logic [7:0] r;
  r = r_inv(i);
  sb[i] = r ^ {r[6:0], r[7]} ^ {r[5:0], r[7:6]} ^ {r[4:0], r[7:5]} ^ {r[3:0], r[7:4]} ^ 8'h63;
end
function automatic logic [31:0] r_mixcol(input logic [31:0] c);
  logic [7:0] a0, a1, a2, a3;
  {a0, a1, a2, a3} = c;
  r_mixcol = {r_xt(a0) ^ r_xt(a1) ^ a1 ^ a2 ^ a3, a0 ^ r_xt(a1) ^ r_xt(a2) ^ a2 ^ a3,
              a0 ^ a1 ^ r_xt(a2) ^ r_xt(a3) ^ a3, r_xt(a0) ^ a0 ^ a1 ^ a2 ^ r_xt(a3)};
endfunction
function automatic logic [127:0] r_aes(input logic [127:0] key, input logic [127:0] pt);
  logic [127:0] s, k, t;
  logic [31:0] w;
  logic [7:0] rc;
  s = pt ^ key; k = key; rc = 8'h01;
  for (int r = 0; r < 10; r++) begin
    // SubBytes + ShiftRows: row j of column c comes from column c + j
    for (int c = 0; c < 4; c++)
      for (int j = 0; j < 4; j++)
        t[8*(15 - 4*c - j) +: 8] = sb[s[8*(15 - 4*((c + j) & 3) - j) +: 8]];
    if (r < 9) for (int c = 0; c < 4; c++) t[32*(3 - c) +: 32] = r_mixcol(t[32*(3 - c) +: 32]);
    w = {sb[k[23:16]], sb[k[15:8]], sb[k[7:0]], sb[k[31:24]]} ^ {rc, 24'h0};
    k = {k[127:96] ^ w, k[95:64] ^ k[127:96] ^ w, k[63:32] ^ k[95:64] ^ k[127:96] ^ w,
         k[31:0] ^ k[63:32] ^ k[95:64] ^ k[127:96] ^ w};
    rc = r_xt(rc);
    s = t ^ k;
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

// frame under construction: DA, SA, SecTAG, data, ICV
logic [7:0] fb [0:127];
logic [7:0] pt [0:127];
integer fn, fh, fdn;
logic [47:0] DA = 48'h02AA_BBCC_DDEE;
logic [47:0] PSA = 48'h0012_3456_789A;
logic [127:0] K0 = 128'hFEFF_E992_8665_731C_6D6A_8F94_6730_8308;
logic [127:0] K1 = 128'hAD7A_2BD0_3EAC_835A_6F62_0FDC_B506_B345;
function automatic logic [127:0] fblk(input integer from, input integer lim);
  logic [127:0] v;
  for (int j = 0; j < 16; j++) v[8*(15 - j) +: 8] = (from + j < lim) ? fb[from + j] : 8'h00;
  fblk = v;
endfunction
// tci {V ES SC SCB E C}; sci used only with SC; ivsci / key: what the sender uses
task automatic build(input logic [5:0] tci, input logic [1:0] an, input integer sl, input logic [31:0] pn,
                     input logic [47:0] sa, input logic [63:0] sci, input integer n, input logic [7:0] v0);
  logic [63:0] ivs;
  logic [127:0] key, hk, x, ks, tag;
  logic [63:0] la, lc;
  integer alen;
  for (int i = 0; i < 128; i++) fb[i] = 8'h00;
  for (int i = 0; i < n; i++) pt[i] = v0 + 8'd37 * i;
  for (int i = 0; i < 6; i++) begin fb[i] = DA[8*(5 - i) +: 8]; fb[6 + i] = sa[8*(5 - i) +: 8]; end
  fb[12] = 8'h88; fb[13] = 8'hE5; fb[14] = {tci, an}; fb[15] = sl;
  fb[16] = pn[31:24]; fb[17] = pn[23:16]; fb[18] = pn[15:8]; fb[19] = pn[7:0];
  fh = 20;
  if (tci[3]) begin
    for (int i = 0; i < 8; i++) fb[20 + i] = sci[8*(7 - i) +: 8];
    fh = 28;
  end
  ivs = tci[3] ? sci : {sa, 16'h0001};
  key = an[0] ? K1 : K0;
  hk = r_aes(key, 0);
  fdn = n;
  for (int b = 0; b < 6; b++) begin
    ks = tci[1] ? r_aes(key, {ivs, pn, 32'd2 + b}) : 0;
    for (int j = 0; j < 16; j++) if (16*b + j < n) fb[fh + 16*b + j] = pt[16*b + j] ^ ks[8*(15 - j) +: 8];
  end
  alen = tci[1] ? fh : fh + n;
  x = 0;
  for (int b = 0; b < 8; b++) if (16*b < alen) x = r_gmul(x ^ fblk(16*b, alen), hk);
  if (tci[1]) for (int b = 0; b < 6; b++) if (16*b < n) x = r_gmul(x ^ fblk(fh + 16*b, fh + n), hk);
  la = alen * 8; lc = tci[1] ? n * 8 : 0;
  x = r_gmul(x ^ {la, lc}, hk);
  tag = x ^ r_aes(key, {ivs, pn, 32'h1});
  for (int j = 0; j < 16; j++) fb[fh + n + j] = tag[8*(15 - j) +: 8];
  fn = fh + n + 16;
endtask

// delivery capture
logic [7:0] ob [0:255];
integer on = 0, nrep = 0, nlast = 0;
logic [2:0] st;
always @(posedge clk) begin
  if (out_valid) begin ob[on] = out_data; on = on + 1; if (out_last) nlast = nlast + 1; end
  if (rep_valid) begin nrep = nrep + 1; st = rep_status; end
end
task automatic send();
  integer r0, k;
  r0 = nrep; on = 0;
  for (int i = 0; i < 128; i++)
    if (i < fn) begin @(negedge clk); in_valid = 1; in_data = fb[i]; in_last = (i == fn - 1); end
  @(negedge clk); in_valid = 0; in_last = 0;
  k = 0;
  while (k < 200 && nrep == r0) begin @(negedge clk); k = k + 1; end
  @(negedge clk);
endtask
// delivered frame = DA, SA, plaintext
function automatic logic delivered(input integer n);
  logic ok;
  ok = (on == 12 + n);
  for (int i = 0; i < 12; i++) if (ob[i] !== fb[i]) ok = 0;
  for (int i = 0; i < 128; i++) if (i < n && ob[12 + i] !== pt[i]) ok = 0;
  delivered = ok;
endfunction
task automatic want(input integer s, input integer n, input string msg);
  if (s == 0) chk(st == 3'd0 && delivered(n), msg);
  else chk(st == s && on == 0, msg);
endtask

logic [31:0] pa, pb;
initial begin
  logic [127:0] h0, c2;
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && out_valid === 1'b0, "nothing out in reset");
  rst_n = 1;
  // the reference itself
  chk(r_aes(128'h0001_0203_0405_0607_0809_0A0B_0C0D_0E0F, 128'h0011_2233_4455_6677_8899_AABB_CCDD_EEFF) ==
      128'h69C4_E0D8_6A7B_0430_D8CD_B780_70B4_C55A, "reference AES-128: FIPS-197 C.1");
  h0 = r_aes(0, 0);
  chk(h0 == 128'h66E9_4BD4_EF8A_2C3B_884C_FA59_CA34_2B2E, "reference H for the zero key (GCM test case 1)");
  chk(r_aes(0, 1) == 128'h58E2_FCCE_FA7E_3061_367F_1D57_A4E7_455A, "GCM test case 1 tag");
  c2 = r_aes(0, 2);
  chk(c2 == 128'h0388_DACE_60B6_A392_F328_C2B9_71B2_FE78, "GCM test case 2 ciphertext");
  chk((r_gmul(r_gmul(c2, h0) ^ 128'd128, h0) ^ r_aes(0, 1)) == 128'hAB6E_47D4_2CEC_13BD_F53A_67B2_1257_BDDF,
      "GCM test case 2 tag");
  repeat (4) @(negedge clk);
  chk(nrep == 0 && on == 0, "no status or output after reset without a frame");

  // confidentiality, explicit SCI, AN 0 / 1, short and long data
  build(6'b001011, 0, 30, 32'd1, PSA, 64'h0012_3456_789A_0001, 30, 8'h11); send();
  want(0, 30, "E/C, explicit SCI, AN 0, 30 bytes (SL 30)");
  build(6'b001011, 1, 0, 32'd5, PSA, 64'h0012_3456_789A_0001, 64, 8'h22); send();
  want(0, 64, "E/C, AN 1, 64 bytes (SL 0)");
  build(6'b001011, 0, 0, 32'd2, PSA, 64'h0012_3456_789A_0001, 48, 8'h33); send();
  want(0, 48, "48 bytes with SL 0");
  build(6'b001011, 0, 47, 32'd3, PSA, 64'h0012_3456_789A_0001, 47, 8'h34); send();
  want(0, 47, "47 bytes with SL 47");
  // implicit SCI (SC 0), ES; integrity only
  build(6'b000011, 0, 20, 32'd4, PSA, 0, 20, 8'h44); send();
  want(0, 20, "SC 0: SCI from SA || 0x0001");
  build(6'b010011, 1, 0, 32'd6, PSA, 0, 70, 8'h55); send();
  want(0, 70, "ES 1, SC 0");
  build(6'b001000, 0, 10, 32'd7, PSA, 64'h0012_3456_789A_0001, 10, 8'h66); send();
  chk(st == 0 && delivered(10) && fb[28] === 8'h66, "integrity only: data sent in clear and delivered");
  build(6'b000000, 1, 0, 32'd8, PSA, 0, 80, 8'h67); send();
  want(0, 80, "integrity only, SC 0, 80 bytes");
  build(6'b001011, 0, 17, 32'd10, PSA, 64'h0012_3456_789A_0001, 17, 8'h35); send();
  want(0, 17, "17 bytes: a single byte in the second block");
  build(6'b001011, 0, 0, 32'd11, PSA, 64'h0012_3456_789A_0001, 66, 8'h36); send();
  want(0, 66, "66 bytes: two bytes in the fifth block");

  // untagged and bad tags
  build(6'b001011, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h70);
  fb[12] = 8'h08; fb[13] = 8'h00; send();
  want(1, 0, "EtherType 0x0800: untagged");
  fn = 14; fb[12] = 8'h88; fb[13] = 8'hE5; send(); want(2, 0, "14 bytes up to EtherType 0x88E5: bad tag");
  fn = 13; send(); want(1, 0, "13 bytes: untagged");
  build(6'b101011, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h71); send(); want(2, 0, "V set: bad tag");
  build(6'b011011, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h72); send(); want(2, 0, "ES with SC: bad tag");
  build(6'b001111, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h73); send(); want(2, 0, "SC with SCB: bad tag");
  build(6'b001001, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h74); send(); want(2, 0, "C without E: bad tag");
  build(6'b001010, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h75); send(); want(2, 0, "E without C: bad tag");
  build(6'b001011, 0, 30, 32'd0, PSA, 64'h0012_3456_789A_0001, 30, 8'h76); send(); want(2, 0, "PN 0: bad tag");
  build(6'b001011, 0, 31, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h77); send(); want(2, 0, "SL 31 for 30 bytes: bad tag");
  build(6'b001011, 0, 0, 32'd9, PSA, 64'h0012_3456_789A_0001, 47, 8'h78); send(); want(2, 0, "SL 0 for 47 bytes: bad tag");
  build(6'b001011, 0, 48, 32'd9, PSA, 64'h0012_3456_789A_0001, 48, 8'h79); send(); want(2, 0, "SL 48: bad tag");
  build(6'b001011, 0, 0, 32'd9, PSA, 64'h0012_3456_789A_0001, 0, 8'h7B);
  fn = 28 + 15; send(); want(2, 0, "SecTAG and 15 bytes: too short");
  // no SA
  build(6'b001011, 0, 30, 32'd9, PSA, 64'h0012_3456_789A_0002, 30, 8'h80); send(); want(3, 0, "SCI port 2: no SA");
  build(6'b000011, 0, 30, 32'd9, 48'h0012_3456_789B, 0, 30, 8'h81); send(); want(3, 0, "SC 0 from another SA: no SA");
  build(6'b001011, 2, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h82); send(); want(3, 0, "AN 2: no SA");
  build(6'b001011, 3, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h83); send(); want(3, 0, "AN 3: no SA");

  // replay protection (AN 0 accepted up to PN 11, AN 1 up to PN 8)
  build(6'b001011, 0, 30, 32'd7, PSA, 64'h0012_3456_789A_0001, 30, 8'h90); send(); want(4, 0, "AN 0 PN 7 again: late");
  build(6'b001011, 0, 30, 32'd3, PSA, 64'h0012_3456_789A_0001, 30, 8'h91); send(); want(4, 0, "AN 0 PN 3: late");
  build(6'b001011, 0, 30, 32'd12, PSA, 64'h0012_3456_789A_0001, 30, 8'h92); send(); want(0, 30, "AN 0 PN 12: next");
  build(6'b001011, 1, 30, 32'd8, PSA, 64'h0012_3456_789A_0001, 30, 8'h93); send(); want(4, 0, "AN 1 keeps its own PN (8 late)");
  build(6'b001011, 1, 30, 32'd9, PSA, 64'h0012_3456_789A_0001, 30, 8'h94); send(); want(0, 30, "AN 1 PN 9");
  build(6'b001011, 0, 30, 32'h7FFF_0000, PSA, 64'h0012_3456_789A_0001, 30, 8'h95); send(); want(0, 30, "AN 0 jumps ahead");
  build(6'b001011, 0, 30, 32'd6, PSA, 64'h0012_3456_789A_0001, 30, 8'h96); send(); want(4, 0, "AN 0 below the jump: late");

  // ICV failures: the PN is not consumed
  build(6'b001011, 1, 30, 32'd10, PSA, 64'h0012_3456_789A_0001, 30, 8'hA0);
  fb[fn - 1] = fb[fn - 1] ^ 8'h01; send(); want(5, 0, "ICV bit flipped");
  build(6'b001011, 1, 30, 32'd10, PSA, 64'h0012_3456_789A_0001, 30, 8'hA1);
  fb[30] = fb[30] ^ 8'h80; send(); want(5, 0, "ciphertext bit flipped");
  build(6'b001011, 1, 30, 32'd10, PSA, 64'h0012_3456_789A_0001, 30, 8'hA2);
  fb[0] = fb[0] ^ 8'h02; send(); want(5, 0, "DA bit flipped (AAD)");
  build(6'b001011, 1, 30, 32'd10, PSA, 64'h0012_3456_789A_0001, 30, 8'hA3);
  send(); want(0, 30, "after the failures PN 10 still passes");
  build(6'b000000, 1, 0, 32'd11, PSA, 0, 60, 8'hA4);
  fb[60] = fb[60] ^ 8'h10; send(); want(5, 0, "integrity only: data bit flipped");
  build(6'b001011, 1, 30, 32'd11, PSA, 64'h0012_3456_789A_0001, 30, 8'hA5);
  for (int i = 0; i < 16; i++) fb[fn - 16 + i] = fb[fn - 16 + i] ^ 8'hFF; send(); want(5, 0, "ICV inverted");
  // AN changed after sealing (other SA key, other AAD)
  build(6'b001011, 1, 30, 32'h7FFF_0001, PSA, 64'h0012_3456_789A_0001, 30, 8'hA6);
  fb[14] = {6'b001011, 2'd0}; send(); want(5, 0, "AN 0 frame sealed with the AN 1 key");
  build(6'b001011, 0, 30, 32'h7FFF_0001, PSA, 64'h0012_3456_789A_0001, 30, 8'hA7); send(); want(0, 30, "AN 0 PN 0x7FFF0001");
  chk(nlast == 15, $sformatf("one last-byte strobe per delivered frame (%0d)", nlast));

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
