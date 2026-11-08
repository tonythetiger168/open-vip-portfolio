# HDMI source VIP: drives TMDS characters (one 10-bit character per channel
# per clock; the serialiser and the TMDS clock lane are abstracted) into an
# HDMI receiver, the role of a set-top box, player or console feeding a TV.
#
# Per frame (one item): v_front, v_sync (VSYNC high), v_back and v_active
# lines; each line is h_front, h_sync (HSYNC high) and h_back blanking
# characters, then h_active pixels. Blanking: control tokens, {VSYNC, HSYNC}
# on channel 0 (10'h354 / 0AB / 154 / 2AB = 00 / 01 / 10 / 11), CTL0..3 on
# channels 1 and 2. Before the pixels of each line: the video preamble (8
# characters, CTL0 = 1) and the video guard band (2 characters: 10'h2CC on
# channels 0 and 2, 10'h133 on channel 1). Pixels: DVI 1.0 TMDS encoding
# (channel 0 blue, 1 green, 2 red) with the running disparity reset at the
# start of every video period. In the first v_back line, after HSYNC, an
# optional data island: island preamble (CTL0 = CTL2 = 1), leading guard band,
# one 32-character packet (header bits on channel 0 bit 2, subpackets in
# TERC4 on channels 1 and 2, BCH ECC) and the trailing guard band. The packet
# is an AVI or audio InfoFrame. One control character closes each item.
#
# tb/top_tb.sv hdmisrc_model: an HDMI receiver (HACT x VACT, as
# HDMI_RX_DMA_top in open-ip-portfolio: capture starts at the VSYNC rising
# edge, guard bands are skipped). It drives hpd, outputs every pixel of a
# captured frame (pix_valid, pix_data {R, G, B}, pix_sol, pix_sof), every data
# island packet (pkt_valid, pkt_hdr {ECC, HB2, HB1, HB0}, pkt_sp, pkt_ok = all
# five BCH codes correct), and after VACT active lines a frame report
# (frm_valid; frm_lines, frm_badlen = lines without HACT pixels, frm_nogb =
# lines without a video guard band).

HDMI_FUNCS = """
localparam bit [9:0] HS_GB_V02 = 10'h2CC;   // video guard band, channels 0 and 2
localparam bit [9:0] HS_GB_V1  = 10'h133;   // video guard band channel 1, island guard band channels 1 and 2
// DVI 1.0 figure 3-5 encoder; cnt is the running disparity of the channel
function automatic bit [9:0] hs_enc(bit [7:0] d, ref int cnt);
  bit [8:0] qm;
  int n1d = $countones(d), n1, n0;
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
    cnt = qm[8] ? cnt + (n1 - n0) : cnt + (n0 - n1);
    return {!qm[8], qm[8], qm[8] ? qm[7:0] : ~qm[7:0]};
  end
  if ((cnt > 0 && n1 > n0) || (cnt < 0 && n0 > n1)) begin
    cnt = cnt + 2 * qm[8] + (n0 - n1);
    return {1'b1, qm[8], ~qm[7:0]};
  end
  cnt = cnt - 2 * (!qm[8]) + (n1 - n0);
  return {1'b0, qm[8], qm[7:0]};
endfunction
function automatic bit [7:0] hs_dec(bit [9:0] q);
  bit [7:0] t = q[9] ? ~q[7:0] : q[7:0], d;
  d[0] = t[0];
  for (int i = 1; i < 8; i++) d[i] = q[8] ? (t[i] ^ t[i-1]) : !(t[i] ^ t[i-1]);
  return d;
endfunction
function automatic bit [9:0] hs_tok(bit c1, bit c0);
  case ({c1, c0})
    2'b00: return 10'h354;
    2'b01: return 10'h0AB;
    2'b10: return 10'h154;
    default: return 10'h2AB;
  endcase
endfunction
function automatic bit [2:0] hs_ctl(bit [9:0] q);    // {valid, C1, C0}
  case (q)
    10'h354: return 3'b100;
    10'h0AB: return 3'b101;
    10'h154: return 3'b110;
    10'h2AB: return 3'b111;
    default: return 3'b000;
  endcase
endfunction
function automatic bit [9:0] hs_terc4(bit [3:0] d);
  case (d)
    4'h0: return 10'b1010011100; 4'h1: return 10'b1001100011; 4'h2: return 10'b1011100100; 4'h3: return 10'b1011100010;
    4'h4: return 10'b0101110001; 4'h5: return 10'b0100011110; 4'h6: return 10'b0110001110; 4'h7: return 10'b0100111100;
    4'h8: return 10'b1011001100; 4'h9: return 10'b0100111001; 4'hA: return 10'b0110011100; 4'hB: return 10'b1011000110;
    4'hC: return 10'b1010001110; 4'hD: return 10'b1001110001; 4'hE: return 10'b0101100011; default: return 10'b1011000011;
  endcase
endfunction
function automatic bit [4:0] hs_terc4_dec(bit [9:0] q);  // {valid, d}
  for (int i = 0; i < 16; i++) if (hs_terc4(i) == q) return {1'b1, 4'(i)};
  return 5'h00;
endfunction
// packet ECC: BCH, G(x) = 1 + x^6 + x^7 + x^8, bit 0 first
function automatic bit [7:0] hs_bch(bit [55:0] bits, int n);
  bit [7:0] e = 0;
  for (int i = 0; i < n; i++) begin
    bit fb = e[0] ^ bits[i];
    e = e >> 1;
    if (fb) e ^= 8'h83;
  end
  return e;
endfunction
// CTA-861 timing presets {h_active, h_front, h_sync, h_back, v_active, v_front, v_sync, v_back}:
// 0 bench default 64x16, 1 640x480p60 (VIC 1), 2 1080p60 (VIC 16), 3 2160p60 (VIC 97),
// 4 4320p60 (VIC 199; check against CTA-861 before relying on it)
function automatic bit [15:0] hs_preset(int id, int f);
  bit [15:0] t [8];
  case (id)
    1: t = '{640, 16, 96, 48, 480, 10, 2, 33};
    2: t = '{1920, 88, 44, 148, 1080, 4, 5, 36};
    3: t = '{3840, 176, 88, 296, 2160, 8, 10, 72};
    4: t = '{7680, 552, 176, 2392, 4320, 16, 20, 44};
    default: t = '{64, 8, 8, 32, 16, 1, 1, 2};
  endcase
  return t[f];
endfunction
"""

SPEC = dict(
    vip="HDMI_Source-UVM-VIP", p="hdmisrc", P="HDMI source", dir="hdmisrc", family="Video",
    desc="HDMI source VIP: TMDS character agent (DVI 1.0 encoding with running disparity, HSYNC / VSYNC control tokens, "
         "preambles, video guard bands, data islands with AVI / audio InfoFrames and BCH ECC) driving an HDMI receiver; "
         "receiver model matching the open-ip HDMI RX.",
    about="""
A TV's HDMI input is verified with an HDMI source on the other side of the
cable. This agent is that source at the TMDS character level: it sends whole
frames with configurable timing (`cfg.h_active` .. `cfg.v_back`; `cfg.preset`
loads a CTA-861 timing: 640x480, 1080p, 2160p, 4320p), pixels TMDS-encoded
exactly as DVI 1.0 specifies (running disparity reset per video period),
sync in the channel 0 control tokens, video preambles and guard bands, and
data islands carrying AVI or audio InfoFrames with their BCH codes. It also
plants faults: corrupted header or subpacket ECC, lines one pixel short or
long, lines without a guard band and whole frames in DVI mode (no preamble,
guard band or island). It waits for hpd. The monitor decodes the character
stream on its own (usable passively to check an HDMI transmitter IP) and
collects what the receiver delivered; the scoreboard checks the receiver's
pixels, packets and frame report against the decoded frame. The default
frame is 64x16 active pixels so Verilator runs stay short. Pins match
HDMI_RX_DMA_top in open-ip-portfolio (tmds_ch0/1/2, hpd); set
`cfg.preamble_en` or `cfg.island_en` to 0 for a receiver that expects plain
control periods.""",
    defs=HDMI_FUNCS,
    timeout=20000,
    cfg="""int unsigned preset = 0;           // hs_preset() timing; 0 = bench default 64x16 (receiver model HACT x VACT)
int unsigned h_active = 64, h_front = 8, h_sync = 8, h_back = 32;
int unsigned v_active = 16, v_front = 1, v_sync = 1, v_back = 2;
bit preamble_en = 1;                 // video preamble + guard band before every line
bit island_en   = 1;                 // data islands in kinds that carry an InfoFrame
function void load_preset(int id);
  preset = id;
  h_active = hs_preset(id, 0); h_front = hs_preset(id, 1); h_sync = hs_preset(id, 2); h_back = hs_preset(id, 3);
  v_active = hs_preset(id, 4); v_front = hs_preset(id, 5); v_sync = hs_preset(id, 6); v_back = hs_preset(id, 7);
endfunction""",
    ports=[
        ("in", "logic [9:0]", "tmds_ch0"), ("in", "logic [9:0]", "tmds_ch1"), ("in", "logic [9:0]", "tmds_ch2"),
        ("out", "logic", "hpd"),
        ("out", "logic", "pix_valid"), ("out", "logic [23:0]", "pix_data"), ("out", "logic", "pix_sol"), ("out", "logic", "pix_sof"),
        ("out", "logic", "pkt_valid"), ("out", "logic [31:0]", "pkt_hdr"), ("out", "logic [255:0]", "pkt_sp"), ("out", "logic", "pkt_ok"),
        ("out", "logic", "frm_valid"), ("out", "logic [11:0]", "frm_lines"), ("out", "logic [11:0]", "frm_badlen"),
        ("out", "logic [11:0]", "frm_nogb"),
    ],
    fields=[
        ("bit [23:0]", "pix", "req", "q"),      # active pixels {R, G, B} as decoded from the characters
        ("bit [15:0]", "llen", "req", "q"),     # pixels per active line
        ("bit", "gb", "req", "q"),              # video guard band before the line
        ("bit [31:0]", "hdr", "req", "q"),      # island packet headers {ECC, HB2, HB1, HB0}
        ("bit [63:0]", "sp", "req", "q"),       # subpackets {ECC, PB} (4 per packet)
        ("bit [23:0]", "rpix", "rsp", "q"),
        ("bit [31:0]", "rhdr", "rsp", "q"),
        ("bit [63:0]", "rsp_sp", "rsp", "q"),
        ("bit", "rok", "rsp", "q"),
        ("bit [11:0]", "rlines", "rsp"),
        ("bit [11:0]", "rbadlen", "rsp"),
        ("bit [11:0]", "rnogb", "rsp"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-3 AVI InfoFrame island, 4 header ECC flipped, 5 subpacket ECC flipped,
// 6 one line a pixel short, 7 one line a pixel long, 8 one line without a guard
// band, 9 DVI mode (no preamble, guard band or island), 10 audio InfoFrame,
// 11 colour bars, 12-31 random pixels without an island
function void set(int k, bit [31:0] s = 1); kind = k; seed = s; endfunction
function bit has_island(); return kind inside {[0:5], 10}; endfunction
// InfoFrame packet: header {ECC, HB2, HB1, HB0} and 4 subpackets {ECC, 7 PB}
function void infoframe(output bit [31:0] h, output bit [63:0] s[4]);
  bit [7:0] hb [3], pb [28];
  bit [7:0] sum = 0;
  bit [31:0] x = seed | 1;
  foreach (pb[i]) pb[i] = 0;
  if (kind == 10) begin hb = '{8'h84, 8'h01, 8'h0A}; pb[1] = 8'h01; pb[4] = x[7:0] & 8'h1F; end
  else begin hb = '{8'h82, 8'h02, 8'h0D}; pb[1] = 8'h10 | {x[1:0], 5'h0}; pb[2] = 8'h08; pb[4] = x[15:8] & 8'h7F; end
  for (int i = 0; i < 3; i++) sum += hb[i];
  for (int i = 1; i < 28; i++) sum += pb[i];
  pb[0] = 8'h00 - sum;
  h[23:0] = {hb[2], hb[1], hb[0]};
  h[31:24] = hs_bch({32'h0, h[23:0]}, 24);
  if (kind == 4) h[31 - x[18:16]] ^= 1'b1;
  for (int k = 0; k < 4; k++) begin
    for (int i = 0; i < 7; i++) s[k][8 * i +: 8] = pb[7 * k + i];
    s[k][63:56] = hs_bch(s[k][55:0], 56);
  end
  if (kind == 5) s[x[21:20]][63 - x[24:22]] ^= 1'b1;
endfunction
""",
    drv_rsp=False,
    drv_desc="one frame of TMDS characters per item (blanking with sync tokens, preamble, guard band, TMDS pixels, an optional InfoFrame island), after hpd is high",
    drv_idle="""
vif.drv_cb.tmds_ch0 <= 10'h354;
vif.drv_cb.tmds_ch1 <= 10'h354;
vif.drv_cb.tmds_ch2 <= 10'h354;
""",
    drv_item="""
bit [31:0] x = t.seed | 1;
int nl = cfg.v_front + cfg.v_sync + cfg.v_back + cfg.v_active;
int hb = cfg.h_front + cfg.h_sync + cfg.h_back;
int fl = cfg.v_front + cfg.v_sync + cfg.v_back + (t.seed[11:8] % cfg.v_active);   // the faulty line
bit dvi = (t.kind == 9) || !cfg.preamble_en;
bit [31:0] ih;
bit [63:0] isp [4];
if (vif.drv_cb.hpd !== 1'b1) begin
  int to = 0;
  while (vif.drv_cb.hpd !== 1'b1 && to < cfg.timeout_cycles) begin @(vif.drv_cb); to++; end
  if (vif.drv_cb.hpd !== 1'b1) `uvm_error("DRV", "HDMI: hpd never went high")
end
@(vif.drv_cb);
t.infoframe(ih, isp);
t.pix.delete(); t.llen.delete(); t.gb.delete(); t.hdr.delete(); t.sp.delete();
if (!dvi && cfg.island_en && t.has_island()) begin t.hdr.push_back(ih); foreach (isp[k]) t.sp.push_back(isp[k]); end
for (int l = 0; l < nl; l++) begin
  bit vs = (l >= cfg.v_front && l < cfg.v_front + cfg.v_sync);
  bit act = (l >= nl - cfg.v_active);
  int na = act ? cfg.h_active + ((l == fl && t.kind == 6) ? -1 : (l == fl && t.kind == 7) ? 1 : 0) : 0;
  int nb = cfg.h_front + cfg.h_sync + cfg.h_back + cfg.h_active - na;
  int is0 = (!dvi && cfg.island_en && t.has_island() && l == cfg.v_front + cfg.v_sync) ? cfg.h_front + cfg.h_sync : -1;
  bit pre = act && !dvi && !(t.kind == 8 && l == fl);
  int c0 = 0, c1 = 0, c2 = 0;
  if (act) begin t.llen.push_back(na); t.gb.push_back(pre); end
  for (int c = 0; c < nb; c++) begin
    bit hs = (c >= cfg.h_front && c < cfg.h_front + cfg.h_sync);
    bit [9:0] a = hs_tok(vs, hs), b = 10'h354, d = 10'h354;
    if (is0 >= 0 && c >= is0 && c < is0 + 44) begin
      int k = c - is0;
      if (k < 8) begin b = 10'h0AB; d = 10'h0AB; end                            // island preamble
      else if (k < 10 || k >= 42) begin a = hs_terc4({2'b11, vs, hs}); b = HS_GB_V1; d = HS_GB_V1; end
      else begin
        int i = k - 10;
        a = hs_terc4({i != 0, ih[i], vs, hs});
        b = hs_terc4({isp[3][2 * i], isp[2][2 * i], isp[1][2 * i], isp[0][2 * i]});
        d = hs_terc4({isp[3][2 * i + 1], isp[2][2 * i + 1], isp[1][2 * i + 1], isp[0][2 * i + 1]});
      end
    end else if (pre && c >= nb - 10) begin
      if (c < nb - 2) b = 10'h0AB;                                               // video preamble, CTL0 = 1
      else begin a = HS_GB_V02; b = HS_GB_V1; d = HS_GB_V02; end
    end
    vif.drv_cb.tmds_ch0 <= a; vif.drv_cb.tmds_ch1 <= b; vif.drv_cb.tmds_ch2 <= d;
    @(vif.drv_cb);
  end
  for (int p = 0; p < na; p++) begin
    bit [23:0] px;
    int bar;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    bar = p * 8 / cfg.h_active;
    if (t.kind == 11) px = {bar[2] ? 8'h00 : 8'hFF, bar[1] ? 8'h00 : 8'hFF, bar[0] ? 8'h00 : 8'hFF};
    else px = x[23:0];
    t.pix.push_back(px);
    vif.drv_cb.tmds_ch0 <= hs_enc(px[7:0], c0);
    vif.drv_cb.tmds_ch1 <= hs_enc(px[15:8], c1);
    vif.drv_cb.tmds_ch2 <= hs_enc(px[23:16], c2);
    @(vif.drv_cb);
  end
end
vif.drv_cb.tmds_ch0 <= 10'h354; vif.drv_cb.tmds_ch1 <= 10'h354; vif.drv_cb.tmds_ch2 <= 10'h354;
@(vif.drv_cb);
""",
    mon_desc="decodes the character stream like a sink (sync tokens, guard bands, TMDS pixels, island packets) from a VSYNC rising edge to v_active lines, with the receiver's pixels, packets and frame report",
    mon_run="""
bit vs_q = 0, armed = 0, in_vid = 0, gbs = 0;
int isl = 0, ni = 0, nlines = 0, ll = 0;
bit [31:0] h;
bit [63:0] s [4];
hdmisrc_transaction t = hdmisrc_transaction::type_id::create("t");
bit done = 0;
forever begin
  bit [2:0] ct0;
  @(vif.mon_cb);
  // what the receiver delivered
  if (vif.mon_cb.pix_valid) t.rpix.push_back(vif.mon_cb.pix_data);
  if (vif.mon_cb.pkt_valid) begin
    t.rhdr.push_back(vif.mon_cb.pkt_hdr); t.rok.push_back(vif.mon_cb.pkt_ok);
    for (int k = 0; k < 4; k++) t.rsp_sp.push_back(vif.mon_cb.pkt_sp[64 * k +: 64]);
  end
  if (vif.mon_cb.frm_valid) begin
    t.rlines = vif.mon_cb.frm_lines; t.rbadlen = vif.mon_cb.frm_badlen; t.rnogb = vif.mon_cb.frm_nogb;
    if (!done) `uvm_error("MON", "HDMI: frame report before the frame ended")
    publish(t);
    t = hdmisrc_transaction::type_id::create("t");
    done = 0;
  end
  // the characters
  ct0 = hs_ctl(vif.mon_cb.tmds_ch0);
  if (ct0[2]) begin
    if (in_vid && armed && !done) begin
      t.llen.push_back(ll); t.gb.push_back(gbs);
      nlines++;
      if (nlines == cfg.v_active) begin done = 1; armed = 0; end
    end
    in_vid = 0; gbs = 0; isl = 0;
    if (ct0[1] && !vs_q && !done) begin
      armed = 1; nlines = 0; t.pix.delete(); t.llen.delete(); t.gb.delete(); t.hdr.delete(); t.sp.delete();
    end
    vs_q = ct0[1];
  end else if (!in_vid && vif.mon_cb.tmds_ch1 == HS_GB_V1 && vif.mon_cb.tmds_ch2 == HS_GB_V1) begin
    isl = (isl + 1) % 4;                     // leading guard band (2), packets, trailing guard band (2)
    if (isl == 2) begin ni = 0; h = 0; foreach (s[k]) s[k] = 0; end
  end else if (!in_vid && isl == 2) begin
    bit [4:0] a = hs_terc4_dec(vif.mon_cb.tmds_ch0), b = hs_terc4_dec(vif.mon_cb.tmds_ch1),
              d = hs_terc4_dec(vif.mon_cb.tmds_ch2);
    h[ni] = a[2];
    for (int k = 0; k < 4; k++) begin s[k][2 * ni] = b[k]; s[k][2 * ni + 1] = d[k]; end
    ni++;
    if (ni == 32) begin
      t.hdr.push_back(h); foreach (s[k]) t.sp.push_back(s[k]);
      ni = 0; h = 0; foreach (s[k]) s[k] = 0;
    end
  end else if (!in_vid && vif.mon_cb.tmds_ch0 == HS_GB_V02 && vif.mon_cb.tmds_ch1 == HS_GB_V1 && vif.mon_cb.tmds_ch2 == HS_GB_V02) begin
    gbs = 1;
  end else if (armed && !done) begin
    if (!in_vid) ll = 0;
    in_vid = 1; ll++;
    t.pix.push_back({hs_dec(vif.mon_cb.tmds_ch2), hs_dec(vif.mon_cb.tmds_ch1), hs_dec(vif.mon_cb.tmds_ch0)});
  end
end
""",
    predict="""
t.rpix = t.pix;
t.rhdr = t.hdr;
t.rsp_sp = t.sp;
t.rok.delete();
foreach (t.hdr[i]) begin
  bit ok = (hs_bch({32'h0, t.hdr[i][23:0]}, 24) == t.hdr[i][31:24]);
  for (int k = 0; k < 4; k++) if (hs_bch(t.sp[4 * i + k][55:0], 56) != t.sp[4 * i + k][63:56]) ok = 0;
  t.rok.push_back(ok);
end
t.rlines = t.llen.size();
t.rbadlen = 0; t.rnogb = 0;
foreach (t.llen[i]) begin
  if (t.llen[i] != cfg.h_active) t.rbadlen++;
  if (!t.gb[i]) t.rnogb++;
end
""",
    checks="""
if (t.rlines != cfg.v_active) fail(t, "frame without v_active lines");
foreach (t.hdr[i]) if (t.rok[i]) begin
  // a packet with good ECC must be an InfoFrame with a correct checksum
  bit [7:0] sum = t.hdr[i][7:0] + t.hdr[i][15:8] + t.hdr[i][23:16];
  for (int k = 0; k < 4; k++) for (int b = 0; b < 7; b++) sum += t.sp[4 * i + k][8 * b +: 8];
  if (!(t.hdr[i][7:0] inside {8'h82, 8'h84})) fail(t, "packet is not an AVI / audio InfoFrame");
  if (sum != 0) fail(t, "InfoFrame checksum");
end
""",
    coverage="""
cp_pkt    : coverpoint tr.hdr.size() { bins none = {0}; bins one = {1}; }
cp_ok     : coverpoint (tr.rok.size() ? tr.rok[0] : 1'b1) iff (tr.hdr.size()) { bins good = {1}; bins bad_ecc = {0}; }
cp_type   : coverpoint (tr.hdr.size() ? tr.hdr[0][7:0] : 8'h00) iff (tr.hdr.size()) { bins avi = {8'h82}; bins audio = {8'h84}; }
cp_badlen : coverpoint tr.rbadlen { bins none = {0}; bins some = {[1:$]}; }
cp_nogb   : coverpoint tr.rnogb { bins none = {0}; bins one = {1}; bins dvi = {[2:$]}; }
""",
    directed="""
// AVI and audio InfoFrames, ECC faults, short / long lines, missing guard band, DVI mode, colour bars
t = item(); t.set(0, 32'h1); send(t);
t = item(); t.set(10, 32'h2); send(t);
t = item(); t.set(11, 32'h3); send(t);
for (int s = 0; s < 3; s++) begin
  t = item(); t.set(4, 32'h1000 * (s + 1) + 7); send(t);
  t = item(); t.set(5, 32'h2000 * (s + 1) + 3); send(t);
  t = item(); t.set(6, 32'h300 * (s + 1)); send(t);
  t = item(); t.set(7, 32'h500 * (s + 1)); send(t);
  t = item(); t.set(8, 32'h700 * (s + 1)); send(t);
end
t = item(); t.set(9, 32'h9); send(t);
t = item(); t.set(1, 32'hA5A5); send(t);
""",
    drain_ns=20000,
    model="""
module hdmisrc_model #(parameter int HACT = 64, parameter int VACT = 16) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic [9:0]   tmds_ch0,
  input  logic [9:0]   tmds_ch1,
  input  logic [9:0]   tmds_ch2,
  output logic         hpd,
  output logic         pix_valid,
  output logic [23:0]  pix_data,
  output logic         pix_sol,
  output logic         pix_sof,
  output logic         pkt_valid,
  output logic [31:0]  pkt_hdr,
  output logic [255:0] pkt_sp,
  output logic         pkt_ok,
  output logic         frm_valid,
  output logic [11:0]  frm_lines,
  output logic [11:0]  frm_badlen,
  output logic [11:0]  frm_nogb
);
  function automatic logic [7:0] dec(input logic [9:0] q);
    logic [7:0] t, d;
    t = q[9] ? ~q[7:0] : q[7:0];
    d[0] = t[0];
    for (int i = 1; i < 8; i++) d[i] = q[8] ? (t[i] ^ t[i-1]) : !(t[i] ^ t[i-1]);
    dec = d;
  endfunction
  function automatic logic [4:0] terc4(input logic [9:0] q);
    case (q)
      10'b1010011100: terc4 = 5'h10; 10'b1001100011: terc4 = 5'h11; 10'b1011100100: terc4 = 5'h12;
      10'b1011100010: terc4 = 5'h13; 10'b0101110001: terc4 = 5'h14; 10'b0100011110: terc4 = 5'h15;
      10'b0110001110: terc4 = 5'h16; 10'b0100111100: terc4 = 5'h17; 10'b1011001100: terc4 = 5'h18;
      10'b0100111001: terc4 = 5'h19; 10'b0110011100: terc4 = 5'h1A; 10'b1011000110: terc4 = 5'h1B;
      10'b1010001110: terc4 = 5'h1C; 10'b1001110001: terc4 = 5'h1D; 10'b0101100011: terc4 = 5'h1E;
      10'b1011000011: terc4 = 5'h1F;
      default:        terc4 = 5'h00;
    endcase
  endfunction
  function automatic logic [7:0] bch(input logic [55:0] bits, input integer n);
    logic [7:0] e;
    logic fb;
    e = 8'h00;
    for (int i = 0; i < 56; i++) if (i < n) begin
      fb = e[0] ^ bits[i];
      e = e >> 1;
      if (fb) e = e ^ 8'h83;
    end
    bch = e;
  endfunction

  logic [3:0]   hcnt;
  logic         vs_q, armed, in_vid, gbs, first;
  logic [1:0]   isl;
  logic [5:0]   ni;
  logic [31:0]  h;
  logic [255:0] s;
  logic [11:0]  nlines, ll, badlen, nogb;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      hpd <= 1'b0; hcnt <= '0;
      vs_q <= 1'b0; armed <= 1'b0; in_vid <= 1'b0; gbs <= 1'b0; first <= 1'b0; isl <= '0; ni <= '0;
      h <= '0; s <= '0; nlines <= '0; ll <= '0; badlen <= '0; nogb <= '0;
      pix_valid <= 1'b0; pix_data <= '0; pix_sol <= 1'b0; pix_sof <= 1'b0;
      pkt_valid <= 1'b0; pkt_hdr <= '0; pkt_sp <= '0; pkt_ok <= 1'b0;
      frm_valid <= 1'b0; frm_lines <= '0; frm_badlen <= '0; frm_nogb <= '0;
    end else begin : step
      logic        c_ok, c_vs;
      logic [4:0]  a, b, d;
      logic [31:0] hn;
      logic [255:0] sn;
      logic        ok;
      pix_valid <= 1'b0; pix_sol <= 1'b0; pix_sof <= 1'b0; pkt_valid <= 1'b0; frm_valid <= 1'b0;
      if (hcnt != 4'hF) hcnt <= hcnt + 4'd1; else hpd <= 1'b1;
      c_ok = (tmds_ch0 == 10'h354) || (tmds_ch0 == 10'h0AB) || (tmds_ch0 == 10'h154) || (tmds_ch0 == 10'h2AB);
      c_vs = (tmds_ch0 == 10'h154) || (tmds_ch0 == 10'h2AB);
      if (c_ok) begin
        if (in_vid && armed) begin
          if (ll != HACT) badlen <= badlen + 12'd1;
          if (!gbs) nogb <= nogb + 12'd1;
          nlines <= nlines + 12'd1;
          if (nlines == VACT - 1) begin
            frm_valid <= 1'b1; frm_lines <= nlines + 12'd1;
            frm_badlen <= badlen + ((ll != HACT) ? 12'd1 : 12'd0);
            frm_nogb <= nogb + (gbs ? 12'd0 : 12'd1);
            armed <= 1'b0;
          end
        end
        in_vid <= 1'b0; gbs <= 1'b0; isl <= '0;
        if (c_vs && !vs_q) begin armed <= 1'b1; first <= 1'b1; nlines <= '0; badlen <= '0; nogb <= '0; end
        vs_q <= c_vs;
      end else if (!in_vid && tmds_ch1 == 10'h133 && tmds_ch2 == 10'h133) begin
        isl <= isl + 2'd1;
        if (isl == 2'd1) begin ni <= '0; h <= '0; s <= '0; end
      end else if (!in_vid && isl == 2'd2) begin
        a = terc4(tmds_ch0); b = terc4(tmds_ch1); d = terc4(tmds_ch2);
        hn = h; sn = s;
        hn[ni[4:0]] = a[2];
        for (int k = 0; k < 4; k++) begin
          sn[64 * k + 2 * ni[4:0]] = b[k];
          sn[64 * k + 2 * ni[4:0] + 1] = d[k];
        end
        if (ni == 6'd31) begin
          ok = (bch({32'h0, hn[23:0]}, 24) == hn[31:24]);
          for (int k = 0; k < 4; k++) if (bch(sn[64 * k +: 56], 56) != sn[64 * k + 56 +: 8]) ok = 1'b0;
          pkt_valid <= 1'b1; pkt_hdr <= hn; pkt_sp <= sn; pkt_ok <= ok;
          ni <= '0; h <= '0; s <= '0;
        end else begin
          ni <= ni + 6'd1; h <= hn; s <= sn;
        end
      end else if (!in_vid && tmds_ch0 == 10'h2CC && tmds_ch1 == 10'h133 && tmds_ch2 == 10'h2CC) begin
        gbs <= 1'b1;
      end else if (armed) begin
        pix_valid <= 1'b1;
        pix_data <= {dec(tmds_ch2), dec(tmds_ch1), dec(tmds_ch0)};
        pix_sol <= !in_vid;
        pix_sof <= !in_vid && first;
        if (!in_vid) begin ll <= 12'd1; first <= 1'b0; end else ll <= ll + 12'd1;
        in_vid <= 1'b1;
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({hpd, pix_valid, pkt_valid, frm_valid}))
  else $error("HDMI: X on hpd / valids");
assert property (@(posedge clk) disable iff (!rst_n) pix_valid |-> !$isunknown(pix_data))
  else $error("HDMI: X in a pixel");
assert property (@(posedge clk) disable iff (!rst_n) pix_sof |-> pix_sol && pix_valid)
  else $error("HDMI: frame start without line start");
assert property (@(posedge clk) disable iff (!rst_n) hpd |-> !$isunknown({tmds_ch0, tmds_ch1, tmds_ch2}))
  else $error("HDMI: X on TMDS with hpd high");
assert property (@(posedge clk) disable iff (!rst_n) $fell(hpd) |-> 0)
  else $error("HDMI: hpd dropped");
cover property (@(posedge clk) disable iff (!rst_n) pkt_valid && pkt_ok);
cover property (@(posedge clk) disable iff (!rst_n) pkt_valid && !pkt_ok);
cover property (@(posedge clk) disable iff (!rst_n) frm_valid && frm_nogb != 0);
""",
    smoke="""
int checks = 0;
int fails  = 0;
localparam integer HA = 64, VA = 16;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic [9:0] tmds_ch0 = 10'h354, tmds_ch1 = 10'h354, tmds_ch2 = 10'h354;
wire hpd, pix_valid, pix_sol, pix_sof, pkt_valid, pkt_ok, frm_valid;
wire [23:0] pix_data;
wire [31:0] pkt_hdr;
wire [255:0] pkt_sp;
wire [11:0] frm_lines, frm_badlen, frm_nogb;

always #5 clk = ~clk;

hdmisrc_model u_dut (.clk(clk), .rst_n(rst_n), .tmds_ch0(tmds_ch0), .tmds_ch1(tmds_ch1), .tmds_ch2(tmds_ch2),
                     .hpd(hpd), .pix_valid(pix_valid), .pix_data(pix_data), .pix_sol(pix_sol), .pix_sof(pix_sof),
                     .pkt_valid(pkt_valid), .pkt_hdr(pkt_hdr), .pkt_sp(pkt_sp), .pkt_ok(pkt_ok),
                     .frm_valid(frm_valid), .frm_lines(frm_lines), .frm_badlen(frm_badlen), .frm_nogb(frm_nogb));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// DVI 1.0 encoder (written from figure 3-5; the receiver only decodes)
function automatic logic [17:0] enc(input logic [7:0] d, input integer cnt);
  logic [8:0] qm;
  logic [9:0] q;
  integer n1d, n1, n0;
  n1d = 0; for (int i = 0; i < 8; i++) n1d = n1d + d[i];
  qm[0] = d[0];
  if (n1d > 4 || (n1d == 4 && d[0] == 1'b0)) begin
    for (int i = 1; i < 8; i++) qm[i] = !(qm[i-1] ^ d[i]); qm[8] = 1'b0;
  end else begin
    for (int i = 1; i < 8; i++) qm[i] = qm[i-1] ^ d[i]; qm[8] = 1'b1;
  end
  n1 = 0; for (int i = 0; i < 8; i++) n1 = n1 + qm[i];
  n0 = 8 - n1;
  if (cnt == 0 || n1 == n0) begin
    q = {!qm[8], qm[8], qm[8] ? qm[7:0] : ~qm[7:0]};
    cnt = qm[8] ? cnt + (n1 - n0) : cnt + (n0 - n1);
  end else if ((cnt > 0 && n1 > n0) || (cnt < 0 && n0 > n1)) begin
    q = {1'b1, qm[8], ~qm[7:0]}; cnt = cnt + 2 * qm[8] + (n0 - n1);
  end else begin
    q = {1'b0, qm[8], qm[7:0]}; cnt = cnt - 2 * (!qm[8]) + (n1 - n0);
  end
  enc = {cnt[7:0], q};
endfunction
function automatic logic [9:0] tok(input logic vs, input logic hs);
  tok = ({vs, hs} == 2'b00) ? 10'h354 : ({vs, hs} == 2'b01) ? 10'h0AB : ({vs, hs} == 2'b10) ? 10'h154 : 10'h2AB;
endfunction
function automatic logic [9:0] t4(input logic [3:0] d);
  case (d)
    4'h0: t4 = 10'b1010011100; 4'h1: t4 = 10'b1001100011; 4'h2: t4 = 10'b1011100100; 4'h3: t4 = 10'b1011100010;
    4'h4: t4 = 10'b0101110001; 4'h5: t4 = 10'b0100011110; 4'h6: t4 = 10'b0110001110; 4'h7: t4 = 10'b0100111100;
    4'h8: t4 = 10'b1011001100; 4'h9: t4 = 10'b0100111001; 4'hA: t4 = 10'b0110011100; 4'hB: t4 = 10'b1011000110;
    4'hC: t4 = 10'b1010001110; 4'hD: t4 = 10'b1001110001; 4'hE: t4 = 10'b0101100011; default: t4 = 10'b1011000011;
  endcase
endfunction
function automatic logic [7:0] bch(input logic [55:0] bits, input integer n);
  logic [7:0] e;
  logic fb;
  e = 8'h00;
  for (int i = 0; i < 56; i++) if (i < n) begin fb = e[0] ^ bits[i]; e = e >> 1; if (fb) e = e ^ 8'h83; end
  bch = e;
endfunction

task automatic ch(input logic [9:0] a, input logic [9:0] b, input logic [9:0] c);
  @(negedge clk); tmds_ch0 = a; tmds_ch1 = b; tmds_ch2 = c;
endtask
integer np = 0, nsol = 0, nsof = 0, npk = 0, nfr = 0, nstray = 0;
logic [23:0] pxlog [0:2047];
logic [31:0] r_hdr; logic [255:0] r_sp; logic r_ok;
logic [11:0] r_lines, r_bad, r_nogb;
always @(posedge clk) begin
  if (rst_n && (pix_sol || pix_sof) && !pix_valid) nstray = nstray + 1;
  if (pix_valid) begin pxlog[np[10:0]] = pix_data; np = np + 1; if (pix_sol) nsol = nsol + 1; if (pix_sof) nsof = nsof + 1; end
  if (pkt_valid) begin npk = npk + 1; r_hdr = pkt_hdr; r_sp = pkt_sp; r_ok = pkt_ok; end
  if (frm_valid) begin nfr = nfr + 1; r_lines = frm_lines; r_bad = frm_badlen; r_nogb = frm_nogb; end
end
// pixel value of line l, pixel p
function automatic logic [23:0] pv(input integer l, input integer p);
  pv = {l[7:0] ^ 8'h5A, p[7:0], l[3:0], p[3:0]} * 24'd2654435;
endfunction
logic [31:0] ph; logic [255:0] psp;
// packet: AVI InfoFrame, optional bit flips (header bit fh, subpacket bit fs)
task automatic mkpkt(input integer fh = -1, input integer fs = -1);
  logic [7:0] pb [0:27];
  logic [7:0] sum;
  for (int i = 0; i < 28; i++) pb[i] = 8'h00;
  pb[1] = 8'h50; pb[2] = 8'h08; pb[4] = 8'h10;
  sum = 8'h82 + 8'h02 + 8'h0D;
  for (int i = 1; i < 28; i++) sum = sum + pb[i];
  pb[0] = 8'h00 - sum;
  ph = {8'h00, 8'h0D, 8'h02, 8'h82};
  ph[31:24] = bch({32'h0, ph[23:0]}, 24);
  for (int k = 0; k < 4; k++) begin
    for (int i = 0; i < 7; i++) psp[64 * k + 8 * i +: 8] = pb[7 * k + i];
    psp[64 * k + 56 +: 8] = bch(psp[64 * k +: 56], 56);
  end
  if (fh >= 0) ph[fh] = ~ph[fh];
  if (fs >= 0) psp[fs] = ~psp[fs];
endtask
// frame: 1 front porch, 1 VSYNC, 2 back porch, VA active lines of 48 + 64 characters;
// short = active line with HA - 1 pixels; nogb = active line without guard band; isl: island in line 2
task automatic frame(input integer short_l = -1, input integer nogb_l = -1, input logic isl = 0,
                     input logic dvi = 0);
  integer c0, c1, c2, na, nb;
  logic [17:0] e;
  for (int l = 0; l < 4 + VA; l++) begin
    na = (l >= 4) ? ((l - 4 == short_l) ? HA - 1 : HA) : 0;
    nb = 112 - na;
    c0 = 0; c1 = 0; c2 = 0;
    for (int c = 0; c < 112; c++) if (c < nb) begin
      if (isl && l == 2 && c >= 16 && c < 60) begin
        if (c < 24) ch(tok(0, 0), 10'h0AB, 10'h0AB);
        else if (c < 26 || c >= 58) ch(t4({2'b11, 1'b0, 1'b0}), 10'h133, 10'h133);
        else ch(t4({c != 26, ph[c - 26], 1'b0, 1'b0}),
                t4({psp[192 + 2 * (c - 26)], psp[128 + 2 * (c - 26)], psp[64 + 2 * (c - 26)], psp[2 * (c - 26)]}),
                t4({psp[193 + 2 * (c - 26)], psp[129 + 2 * (c - 26)], psp[65 + 2 * (c - 26)], psp[1 + 2 * (c - 26)]}));
      end else if (l >= 4 && !dvi && l - 4 != nogb_l && c >= nb - 10) begin
        if (c < nb - 2) ch(tok(0, 0), 10'h0AB, 10'h354); else ch(10'h2CC, 10'h133, 10'h2CC);
      end else ch(tok(l == 1, c >= 8 && c < 16), 10'h354, 10'h354);
    end
    for (int p = 0; p < 64; p++) if (p < na) begin
      logic [9:0] a, b, d;
      logic [23:0] v;
      v = pv(l, p);
      e = enc(v[7:0], c0); a = e[9:0]; c0 = $signed(e[17:10]);
      e = enc(v[15:8], c1); b = e[9:0]; c1 = $signed(e[17:10]);
      e = enc(v[23:16], c2); d = e[9:0]; c2 = $signed(e[17:10]);
      ch(a, b, d);
    end
  end
  ch(tok(0, 0), 10'h354, 10'h354);
  repeat (4) @(negedge clk);
endtask
function automatic logic px_ok();
  logic ok;
  ok = (np == HA * VA);
  for (int l = 0; l < VA; l++) for (int p = 0; p < HA; p++) if (pxlog[l * HA + p] !== pv(l + 4, p)) ok = 0;
  px_ok = ok;
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(hpd === 1'b0 && pix_valid === 1'b0 && pix_sol === 1'b0 && pix_sof === 1'b0 && pkt_valid === 1'b0 &&
      frm_valid === 1'b0, "hpd low and no output in reset");
  rst_n = 1;
  repeat (20) @(negedge clk);
  chk(hpd === 1'b1, "hpd high after reset");
  // pixels before the first VSYNC are not captured
  for (int p = 0; p < 8; p++) ch(10'h1F0, 10'h1F0, 10'h1F0);
  ch(tok(0, 0), 10'h354, 10'h354); repeat (2) @(negedge clk);
  chk(np == 0, "no capture before a VSYNC rising edge");
  np = 0; nsol = 0; nsof = 0; npk = 0; nfr = 0;
  mkpkt(); frame(-1, -1, 1);
  chk(nfr == 1 && r_lines == VA && r_bad == 0 && r_nogb == 0, "frame report: 16 lines, no errors");
  chk(px_ok() && nsol == VA && nsof == 1, "every pixel decoded, one frame start, a line start per line");
  chk(npk == 1 && r_ok && r_hdr == ph && r_sp == psp, "AVI InfoFrame: header, subpackets, ECC ok");
  np = 0; nsol = 0; npk = 0; nfr = 0;
  mkpkt(27); frame(-1, -1, 1); chk(npk == 1 && !r_ok && r_hdr == ph, "header ECC bit flipped");
  np = 0; npk = 0; nfr = 0;
  mkpkt(-1, 130); frame(-1, -1, 1); chk(npk == 1 && !r_ok && r_sp == psp, "subpacket 2 data bit flipped");
  np = 0; nfr = 0;
  mkpkt(); frame(5, 9); chk(nfr == 1 && r_bad == 1 && r_nogb == 1 && np == HA * VA - 1, "short line and a line without guard band");
  np = 0; nfr = 0; npk = 0;
  frame(-1, -1, 0, 1); chk(nfr == 1 && r_bad == 0 && r_nogb == VA && px_ok() && npk == 0, "DVI mode: no guard bands");
  // inside a video period only a control token ends it: characters that look like guard bands are pixels
  np = 0;
  ch(tok(1, 0), 10'h354, 10'h354); ch(tok(0, 0), 10'h354, 10'h354);
  ch(10'h2CC, 10'h133, 10'h2CC); ch(10'h2CC, 10'h133, 10'h2CC);
  ch(10'h1F0, 10'h1F0, 10'h1F0); ch(10'h1F0, 10'h133, 10'h2CC); ch(10'h2CC, 10'h1F0, 10'h2CC); ch(10'h1F0, 10'h133, 10'h133);
  ch(tok(0, 0), 10'h354, 10'h354); repeat (3) @(negedge clk);
  chk(np == 4, $sformatf("guard-band-like characters in a video period are pixels (%0d)", np));
  chk(nstray == 0, "line / frame start only with a pixel");
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
