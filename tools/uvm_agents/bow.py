# OCP / ODSA Bunch of Wires (BoW) PHY VIP, BoW PHY specification v2.0: a BoW
# RX slice (the DUT model) driven by a TX slice agent over the die-to-die
# wires of one slice (forwarded clock, D[15:0], AUX, FEC).
#
# The agent drives one UI per bench clock: the forwarded clock ck toggles on
# every UI (DDR, one bit per clock edge, sec. 10.2) and the 18 data wires
# carry that UI's bits. A clock that does not toggle is a clock-gated UI
# (sec. 11.2). Logic-interface ratio M = 4 (BoW-64 at 1000 MHz PCLK).
#
# tb/top_tb.sv bow_model is the RX slice with the link-layer checks that the
# spec puts on the RX side:
#   PHYResetB low resets the slice (sec. 6.5.1.1). After it rises the RX
#   self-aligns on the TX training pattern (sec. 14.2 steps 6-10): this
#   model's datasheet pattern is TP = F0CA, 16 UI per wire, MSB first, on
#   every wire. PHYReady rises once at least 32 clock edges have been seen
#   and the last 16 UI on every wire (except lines marked defective) equal
#   TP; the parallel word boundary is then put at the start of the pattern.
#   Deserialisation (sec. 10.1): UI k of a word (k = 0..3) gives
#   P_D[16k + i] = D[i], PAUX[k] = AUX, PFEC[k] = FEC; pv pulses one clock
#   after the 4th UI with the word.
#   Redundancy (sec. 13), when rep_en: bad_a / bad_b name defective lines
#   (0 = AUX, 1..16 = D0..D15, 17 = FEC, others = none). One defective data
#   line: logical lines at or below it shift down by one; two defective lines
#   (any of the 18): lines at or below the lower shift down, lines at or
#   above the higher shift up; a defective AUX or FEC alone moves nothing.
#   With rep_en, PAUX / PFEC are 0 (AUX / FEC are spares).
#   Clock gating (sec. 11.2), checked after PHYReady; err pulses one clock
#   after the cause:
#     err[0] the clock stays gated for more than 512 UI (128 words, sec. 11.2.4)
#     err[1] the word before a gate (postamble) or the first word after it
#            (preamble) is not IDLE: all lanes, AUX and FEC 0 (sec. 11.2.3)
#     err[2] the clock stops in the middle of a word (sec. 11.2.2); the
#            partial word is dropped
#     err[3] the clock is gated high (sec. 11.2.1: CLK must be driven low)
#   PRBS-9 checker (sec. 17.1, x^9 + x^5 + 1) on the 16 logical lanes when
#   prbs_en: it locks after 9 non-IDLE UIs (an IDLE UI restarts the lock),
#   then err[4] pulses for any non-IDLE UI with a lane bit != b[n-9] ^ b[n-5].
# In a SoC bench the model sits on the wires of a BoW TX slice; the agent
# then runs passive and its monitor records every clock.

BOW_DEFS = """
localparam bit [15:0] BOW_TP    = 16'hF0CA;   // RX training pattern (this model's datasheet)
localparam int        BOW_ALIGN = 32;         // clock edges before PHYReady
localparam int        BOW_GMAX  = 512;        // max UI in the clock gated state
// physical line (0 = AUX, 1..16 = D0..D15, 17 = FEC) of logical data lane j
function automatic int bow_phys(int j, bit rep, bit [4:0] a, bit [4:0] b);
  int lo = -1, hi = 99;
  bit va = (a <= 5'd17), vb = (b <= 5'd17) && (b != a);
  if (rep) begin
    if (va && vb) begin lo = (a < b) ? a : b; hi = (a < b) ? b : a; end
    else if (va && a >= 5'd1 && a <= 5'd16) lo = a;
    else if (vb && b >= 5'd1 && b <= 5'd16) lo = b;
  end
  if (j + 1 <= lo) return j;
  if (j + 1 >= hi) return j + 2;
  return j + 1;
endfunction
function automatic bit bow_bad(int i, bit rep, bit [4:0] a, bit [4:0] b);
  return rep && ((a <= 5'd17 && i == a) || (b <= 5'd17 && i == b));
endfunction
"""

SPEC = dict(
    vip="BoW-UVM-VIP", p="bow", P="BoW", dir="bow", family="Interconnect",
    desc="OCP / ODSA Bunch of Wires (BoW) PHY v2.0 VIP: RX slice model with PHYResetB / PHYReady "
         "training-pattern alignment, DDR bit ordering into 4-UI words, AUX / FEC redundancy repair "
         "around two defective lines, clock-gated state rules (IDLE pre/postamble, word-aligned "
         "payload, 512 UI limit, CLK low) and a PRBS-9 checker; TX slice agent.",
    about="""
BoW is the open die-to-die PHY of the OCP Open Domain-Specific Architecture:
each slice forwards a DDR clock with 16 data wires and two optional wires,
AUX and FEC. The DUT model is an RX slice. The agent is the TX slice and its
link layer: it resets the slice and sends the training pattern until
PHYReady, sends payload words with and without the IDLE preamble and
postamble around clock-gated periods, stops the clock mid-word, gates it high
or for too long, configures redundancy around one or two defective lines
(shifting the logical lanes onto AUX and FEC as section 13 requires, with
noise on the defective lines), and sends PRBS-9 test data with and without
a bit error. The scoreboard runs its own copy of the slice on the monitored
wires and predicts PHYReady, every parallel word and every error pulse clock
by clock. Electrical and timing items (sections 9, 10.3, 12) are out of
scope for a logic VIP.""",
    defs=BOW_DEFS,
    timeout=100000,
    cfg="""int unsigned gap = 20;    // static clocks that end an item (any gate inside an item is shorter)""",
    ports=[
        ("in", "logic", "phy_reset_b"), ("in", "logic", "ck"), ("in", "logic [15:0]", "d"),
        ("in", "logic", "aux"), ("in", "logic", "fec"), ("in", "logic", "rep_en"),
        ("in", "logic [4:0]", "bad_a"), ("in", "logic [4:0]", "bad_b"), ("in", "logic", "prbs_en"),
        ("out", "logic", "phy_ready"), ("out", "logic", "pv"), ("out", "logic [63:0]", "pd"),
        ("out", "logic [3:0]", "paux"), ("out", "logic [3:0]", "pfec"), ("out", "logic [4:0]", "err"),
    ],
    fields=[
        # per clock {prbs_en, bad_b, bad_a, rep_en, phy_reset_b, ck, fec, aux, d}
        ("bit [31:0]", "mo", "req", "q"),
        # per clock {phy_ready, pv, err, paux, pfec, pd}
        ("bit [78:0]", "so", "rsp", "q"),
        ("bit [4:0]", "errs", "rsp"),           # OR of err over the item
        ("bit [3:0]", "kind", "info", "rand"),
        ("bit [3:0]", "nw", "info", "rand"),
        ("bit [4:0]", "ba", "info", "rand"),
        ("bit [4:0]", "bb", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_kind { kind dist { 1 := 8, 0 := 2, [2:5] :/ 4, 6 := 4, 7 := 2, 8 := 1, 9 := 3, 10 := 1, [11:15] :/ 2 }; }
constraint c_nw   { nw inside {[1:8]}; }
constraint c_bad  { ba inside {[0:17], 31}; bb inside {[0:17], 31}; }
""",
    tr_functions="""
// kind: 0 reset + training + words, 1 burst with IDLE pre/postamble, 2 no
// preamble, 3 two extra UI (partial word), 4 a gate of 520 UI first, 5 CLK
// gated high (odd UI count), 6 PRBS-9 burst, 7 PRBS-9 with a flipped bit,
// 8 reset + wrong training pattern, 9 reset with redundancy (ba, bb),
// 10 reset with the PRBS checker on, 11-15 bursts as 1
function void set(int k, int n = 4, bit [31:0] s = 32'h1, int a = 31, int b = 31);
  kind = k; nw = n; seed = s; ba = a; bb = b;
endfunction
function int kk(); return (kind >= 11) ? 1 : kind; endfunction
// derived from the monitored wires (for coverage)
function int nwords();
  int n = 0;
  foreach (so[i]) if (so[i][77]) n++;
  return n;
endfunction
function bit rep_seen();
  foreach (mo[i]) if (mo[i][20]) return 1;
  return 0;
endfunction
function bit prbs_seen();
  foreach (mo[i]) if (mo[i][31]) return 1;
  return 0;
endfunction
function bit ready_seen();
  foreach (so[i]) if (so[i][78]) return 1;
  return 0;
endfunction
// redundancy configuration seen: 1 one defective data line, 2 two defective
// lines with at least one data line, 3 only AUX / FEC defective, 0 none
function int rep_kind();
  bit [4:0] a = 31, b = 31;
  int n;
  bit dl;
  foreach (mo[i]) if (mo[i][20]) begin a = mo[i][25:21]; b = mo[i][30:26]; end
  n = (a <= 17) + (b <= 17 && b != a);
  dl = (a >= 1 && a <= 16) || (b >= 1 && b <= 16);
  if (n == 0) return 0;
  if (!dl) return 3;
  return n;
endfunction
""",
    drv_rsp=False,
    drv_members="""bit         ckl = 0;          // forwarded clock level
bit         rb = 1;           // PHYResetB
bit         rep = 0, prb = 0;
bit [4:0]   a = 31, b = 31;
bit [31:0]  nz = 32'h1234_5678;   // noise on defective lines
bit [8:0]   lfsr [16];        // PRBS-9 generator per logical lane
bit         first = 1;
bow_transaction cur;""",
    drv_tasks="""
function bit noise();
  nz ^= nz << 13; nz ^= nz >> 17; nz ^= nz << 5;
  return nz[0];
endfunction
// one bench clock: toggle the forwarded clock or not, 18 physical lines
task automatic clk1(bit tog, bit [17:0] ln);
  if (tog) ckl = !ckl;
  vif.drv_cb.phy_reset_b <= rb;
  vif.drv_cb.ck      <= ckl;
  vif.drv_cb.aux     <= ln[0];
  vif.drv_cb.d       <= ln[16:1];
  vif.drv_cb.fec     <= ln[17];
  vif.drv_cb.rep_en  <= rep;
  vif.drv_cb.bad_a   <= a;
  vif.drv_cb.bad_b   <= b;
  vif.drv_cb.prbs_en <= prb;
  cur.mo.push_back({prb, b, a, rep, rb, ckl, ln[17], ln[0], ln[16:1]});
  @(vif.drv_cb);
endtask
task automatic still(int n); repeat (n) clk1(1'b0, 18'h0); endtask
// one UI of logical data through the TX redundancy mux
task automatic ui(bit [15:0] l, bit la = 0, bit lf = 0);
  bit [17:0] x = 0;
  if (!rep) x = {lf, l, la};
  else begin
    for (int j = 0; j < 16; j++) x[bow_phys(j, rep, a, b)] = l[j];
    for (int i = 0; i < 18; i++) if (bow_bad(i, rep, a, b)) x[i] = noise();
  end
  clk1(1'b1, x);
endtask
task automatic word(bit [63:0] w, bit [3:0] wa = 0, bit [3:0] wf = 0);
  for (int k = 0; k < 4; k++) ui(w[16*k +: 16], (rep ? 1'b0 : wa[k]), (rep ? 1'b0 : wf[k]));
endtask
task automatic idle_word(); word(64'h0); endtask
function bit [63:0] rword(bit [31:0] s, int i);
  bit [63:0] x = {s, s ^ 32'h9E37_79B9} + 64'(i) * 64'hD1B5_4A32_D192_ED03;
  x ^= x >> 29; x *= 64'hBF58_476D_1CE4_E5B9; x ^= x >> 32;
  return (x == 0) ? 64'h1 : x;          // never an IDLE word
endfunction
// training: TP on every line (noise on defective ones), n UI
task automatic train(int n, bit [15:0] tp);
  for (int u = 0; u < n; u++) begin
    bit [17:0] x = {18{tp[15 - u % 16]}};
    for (int i = 0; i < 18; i++) if (bow_bad(i, rep, a, b)) x[i] = noise();
    clk1(1'b1, x);
  end
endtask
task automatic do_reset(bit r, bit p, bit [4:0] na, bit [4:0] nb);
  rb = 0; rep = r; prb = p; a = na; b = nb;
  still(4);
  rb = 1;
endtask
task automatic prbs_ui(int flip);
  bit [15:0] l;
  for (int j = 0; j < 16; j++) begin
    bit nb = lfsr[j][8] ^ lfsr[j][4];
    l[j] = nb;
    lfsr[j] = {lfsr[j][7:0], nb};
  end
  if (flip >= 0) l[flip] = !l[flip];
  ui(l);
endtask
""",
    drv_desc="one item per burst on the slice wires: optional PHYResetB pulse with configuration and training pattern, "
             "payload words with or without the IDLE preamble / postamble, partial words, CLK gated low or high, "
             "a long gate, PRBS-9 data; every item ends with cfg.gap static clocks (the clock gated low)",
    drv_idle="""
vif.drv_cb.phy_reset_b <= 1'b1;
vif.drv_cb.ck <= 1'b0; vif.drv_cb.d <= '0; vif.drv_cb.aux <= 1'b0; vif.drv_cb.fec <= 1'b0;
vif.drv_cb.rep_en <= 1'b0; vif.drv_cb.bad_a <= 5'd31; vif.drv_cb.bad_b <= 5'd31; vif.drv_cb.prbs_en <= 1'b0;
foreach (lfsr[j]) lfsr[j] = 9'(j * 37 + 1);
""",
    drv_item="""
int n = (t.nw == 0) ? 1 : t.nw;
cur = t;
t.mo.delete();
if (t.kk() == 4 && !first) still(520);
first = 0;
case (t.kk())
  0, 8, 9, 10: begin
    do_reset(t.kk() == 9, t.kk() == 10, (t.kk() == 9) ? t.ba : 5'd31, (t.kk() == 9) ? t.bb : 5'd31);
    train(48, (t.kk() == 8) ? (BOW_TP ^ 16'h0100) : BOW_TP);
    if (t.kk() != 8) begin
      for (int i = 0; i < n; i++) word(rword(t.seed, i), t.seed[3:0] ^ 4'(i), t.seed[7:4] ^ 4'(i));
      idle_word();
    end
  end
  6, 7: begin
    idle_word();
    for (int u = 0; u < 4 * n + 12; u++) prbs_ui((t.kk() == 7 && u == 10 + t.seed % 8) ? int'(t.seed[7:4]) : -1);
    idle_word();
  end
  default: begin
    if (t.kk() != 2) idle_word();
    for (int i = 0; i < n; i++) word(rword(t.seed, i), t.seed[3:0], t.seed[11:8]);
    if (t.kk() == 5) begin
      ui(16'h0);           // odd UI count: gated high, mid-word
      still(3);
      repeat (3) ui(16'h0); // back to low (and mid-word again)
    end else begin
      idle_word();
      if (t.kk() == 3) begin ui(16'h0); ui(16'h0); end
    end
  end
endcase
still(cfg.gap);
""",
    mon_desc="every bench clock's wires and outputs; an item starts at a forwarded-clock edge or a PHYResetB change "
             "(with the static clocks before it) and ends after cfg.gap static clocks",
    mon_run="""
bit started = 0;
bit pck = 0, prb = 1;
bit [31:0] pend_mo [$];
bit [78:0] pend_so [$];
wait (vif.rst_n === 1'b1);
forever begin
  bow_transaction t = null;
  int st = 0;
  // static clocks up to the next activity
  forever begin
    bit [31:0] m;
    bit [78:0] o;
    @(vif.mon_cb);
    m = {vif.mon_cb.prbs_en, vif.mon_cb.bad_b, vif.mon_cb.bad_a, vif.mon_cb.rep_en, vif.mon_cb.phy_reset_b,
         vif.mon_cb.ck, vif.mon_cb.fec, vif.mon_cb.aux, vif.mon_cb.d};
    o = {vif.mon_cb.phy_ready, vif.mon_cb.pv, vif.mon_cb.err, vif.mon_cb.paux, vif.mon_cb.pfec, vif.mon_cb.pd};
    if (t == null && (m[18] != pck || m[19] != prb)) begin
      t = bow_transaction::type_id::create("t");
      if (started) begin t.mo = pend_mo; t.so = pend_so; end
      pend_mo.delete(); pend_so.delete();
      started = 1;
    end
    if (t == null) begin
      if (started) begin pend_mo.push_back(m); pend_so.push_back(o); end
    end else begin
      t.mo.push_back(m); t.so.push_back(o);
      if (m[18] != pck || m[19] != prb) st = 0; else st++;
    end
    pck = m[18]; prb = m[19];
    if (t != null && st == cfg.gap) break;
  end
  t.errs = 0;
  foreach (t.so[i]) t.errs |= t.so[i][76:72];
  publish(t);
end
""",
    sb_members="""// the RX slice (scoreboard copy), kept across items
bit        ckq = 0, rdy = 0, gated = 0, need_pre = 0, last_idle = 1, widle = 1;
int        edges = 0, ph = 0, g = 0, pn = 0;
bit [15:0] win [18];
bit [8:0]  hist [16];
bit [47:0] wd = 0;
bit [3:0]  wa = 0, wf = 0;
bit        o_pv = 0;
bit [63:0] o_pd = 0;
bit [3:0]  o_paux = 0, o_pfec = 0;
bit [4:0]  o_err = 0;
""",
    predict="""
t.so.delete();
t.errs = 0;
foreach (t.mo[k]) begin
  bit [31:0] m = t.mo[k];
  bit        prb = m[31], rep = m[20], rb = m[19], c = m[18];
  bit [4:0]  bb = m[30:26], ba = m[25:21];
  bit [17:0] ln = {m[17], m[15:0], m[16]};
  bit [15:0] lg;
  bit        la, lf, ui_idle, match, perr, wi;
  bit        n_pv = 0;
  bit [4:0]  n_err = 0;
  t.so.push_back({rdy, o_pv, o_err, o_paux, o_pfec, o_pd});
  t.errs |= o_err;
  for (int j = 0; j < 16; j++) lg[j] = ln[bow_phys(j, rep, ba, bb)];
  la = rep ? 1'b0 : ln[0];
  lf = rep ? 1'b0 : ln[17];
  ui_idle = (lg == 0) && !la && !lf;
  match = 1;
  for (int i = 0; i < 18; i++) if (!bow_bad(i, rep, ba, bb) && {win[i][14:0], ln[i]} != BOW_TP) match = 0;
  perr = 0;
  for (int j = 0; j < 16; j++) if (!ui_idle && pn >= 9 && lg[j] != (hist[j][8] ^ hist[j][4])) perr = 1;
  if (!rb) begin
    rdy = 0; edges = 0; ph = 0; gated = 0; g = 0; need_pre = 0; last_idle = 1; widle = 1; pn = 0;
    foreach (win[i]) win[i] = 0;
  end else if (!rdy) begin
    if (c != ckq) begin
      foreach (win[i]) win[i] = {win[i][14:0], ln[i]};
      if (edges < 63) edges++;
      if (edges >= BOW_ALIGN && match) begin rdy = 1; ph = 0; pn = 0; last_idle = 1; gated = 0; end
    end
  end else if (c != ckq) begin
    wi = (ph == 0) ? ui_idle : (widle && ui_idle);
    widle = wi;
    if (gated) need_pre = 1;
    gated = 0; g = 0;
    if (ph == 3) begin
      n_pv = 1; o_pd = {lg, wd}; o_paux = {la, wa[2:0]}; o_pfec = {lf, wf[2:0]};
      last_idle = wi;
      if (need_pre) begin need_pre = 0; if (!wi) n_err[1] = 1; end
    end else begin
      wd[16 * ph +: 16] = lg; wa[ph] = la; wf[ph] = lf;
    end
    ph = (ph + 1) % 4;
    if (prb) begin
      if (perr) n_err[4] = 1;
      for (int j = 0; j < 16; j++) hist[j] = {hist[j][7:0], lg[j]};
      if (ui_idle) pn = 0; else if (pn != 9) pn++;
    end else pn = 0;
  end else begin
    if (!gated) begin
      gated = 1; g = 1;
      if (ph != 0) begin n_err[2] = 1; ph = 0; end
      else if (!last_idle) n_err[1] = 1;
      if (c) n_err[3] = 1;
    end else if (g != BOW_GMAX + 1) begin
      if (g == BOW_GMAX) n_err[0] = 1;
      g++;
    end
  end
  ckq = c;
  o_pv = n_pv;
  o_err = n_err;
end
""",
    checks="""
if (t.mo.size() == 0) fail(t, "empty item");
""",
    coverage="""
cp_e0    : coverpoint tr.errs[0] { bins seen = {1}; bins none = {0}; }
cp_e1    : coverpoint tr.errs[1] { bins seen = {1}; bins none = {0}; }
cp_e2    : coverpoint tr.errs[2] { bins seen = {1}; bins none = {0}; }
cp_e3    : coverpoint tr.errs[3] { bins seen = {1}; bins none = {0}; }
cp_e4    : coverpoint tr.errs[4] { bins seen = {1}; bins none = {0}; }
cp_words : coverpoint tr.nwords() { bins none = {0}; bins few = {[1:4]}; bins many = {[5:$]}; }
cp_rep   : coverpoint tr.rep_kind() iff (tr.rep_seen()) { bins one = {1}; bins two = {2}; bins spare_only = {3}; }
cp_prbs  : coverpoint tr.prbs_seen();
cp_ready : coverpoint tr.ready_seen();
""",
    directed="""
// bring-up, words, every clock-gating rule, redundancy cases, PRBS-9, retraining
t = item(); t.set(1, 2); send(t);                     // before any training: no words
t = item(); t.set(0, 3, 32'hA5); send(t);
t = item(); t.set(1, 4, 32'h11); send(t);
t = item(); t.set(1, 8, 32'h22); send(t);
t = item(); t.set(2, 2, 32'h33); send(t);             // no preamble
t = item(); t.set(1, 1, 32'h44); send(t);
t = item(); t.set(3, 2, 32'h55); send(t);             // partial word
t = item(); t.set(1, 2, 32'h66); send(t);
t = item(); t.set(4, 2, 32'h77); send(t);             // 520 UI gate
t = item(); t.set(5, 1, 32'h88); send(t);             // gated high
t = item(); t.set(1, 3, 32'h99); send(t);
t = item(); t.set(9, 2, 32'h1, 5, 7); send(t);        // D4 and D6 defective (sec. 13 example)
t = item(); t.set(1, 3, 32'h2); send(t);
t = item(); t.set(9, 2, 32'h3, 11, 31); send(t);      // D10 alone
t = item(); t.set(1, 2, 32'h4); send(t);
t = item(); t.set(9, 2, 32'h5, 0, 17); send(t);       // AUX and FEC: nothing moves
t = item(); t.set(1, 2, 32'h6); send(t);
t = item(); t.set(9, 2, 32'h7, 0, 4); send(t);        // AUX and D3: D3 and up shift up
t = item(); t.set(1, 2, 32'h8); send(t);
t = item(); t.set(9, 2, 32'h9, 17, 31); send(t);      // FEC alone
t = item(); t.set(1, 2, 32'hA); send(t);
t = item(); t.set(10, 1, 32'hB); send(t);             // PRBS checker on
t = item(); t.set(6, 6, 32'hC); send(t);
t = item(); t.set(7, 6, 32'h1D); send(t);
t = item(); t.set(6, 4, 32'hE); send(t);
t = item(); t.set(8, 1, 32'hF); send(t);              // wrong pattern: not ready
t = item(); t.set(1, 2, 32'h10); send(t);
t = item(); t.set(0, 2, 32'h11); send(t);
t = item(); t.set(1, 5, 32'h12); send(t);
""",
    drain_ns=2000,
    model="""
module bow_model #(
  parameter logic [15:0] TP    = 16'hF0CA,
  parameter int          ALIGN = 32,
  parameter int          GMAX  = 512
) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        phy_reset_b,
  input  logic        ck,
  input  logic [15:0] d,
  input  logic        aux,
  input  logic        fec,
  input  logic        rep_en,
  input  logic [4:0]  bad_a,
  input  logic [4:0]  bad_b,
  input  logic        prbs_en,
  output logic        phy_ready,
  output logic        pv,
  output logic [63:0] pd,
  output logic [3:0]  paux,
  output logic [3:0]  pfec,
  output logic [4:0]  err
);
  // physical line of logical lane j (0 = AUX, 1..16 = D0..D15, 17 = FEC)
  function automatic integer phys_of(input integer j);
    integer lo, hi;
    logic va, vb;
    lo = -1; hi = 99;
    va = (bad_a <= 5'd17);
    vb = (bad_b <= 5'd17) && (bad_b != bad_a);
    if (rep_en) begin
      if (va && vb) begin
        lo = (bad_a < bad_b) ? bad_a : bad_b;
        hi = (bad_a < bad_b) ? bad_b : bad_a;
      end else if (va && bad_a >= 5'd1 && bad_a <= 5'd16) lo = bad_a;
      else if (vb && bad_b >= 5'd1 && bad_b <= 5'd16) lo = bad_b;
    end
    if (j + 1 <= lo) phys_of = j;
    else if (j + 1 >= hi) phys_of = j + 2;
    else phys_of = j + 1;
  endfunction
  function automatic logic bad_line(input integer i);
    bad_line = rep_en && ((bad_a <= 5'd17 && i == bad_a) || (bad_b <= 5'd17 && i == bad_b));
  endfunction

  wire  [17:0] line = {fec, d, aux};
  logic [15:0] lg;
  logic        la, lf, ui_idle, match, perr, wi;
  logic [15:0] win [0:17];
  logic [8:0]  hist [0:15];
  logic        ck_q, gated, need_pre, last_idle, widle;
  logic [5:0]  edges;
  logic [1:0]  ph;
  logic [47:0] wd;
  logic [3:0]  wa, wf;
  logic [9:0]  g;
  logic [3:0]  pn;

  always_comb begin
    for (int j = 0; j < 16; j++) lg[j] = line[phys_of(j)];
    la = rep_en ? 1'b0 : aux;
    lf = rep_en ? 1'b0 : fec;
    ui_idle = (lg == 16'h0) && !la && !lf;
    match = 1'b1;
    for (int i = 0; i < 18; i++)
      if (!bad_line(i) && {win[i][14:0], line[i]} != TP) match = 1'b0;
    perr = 1'b0;
    for (int j = 0; j < 16; j++)
      if (!ui_idle && pn >= 4'd9 && lg[j] != (hist[j][8] ^ hist[j][4])) perr = 1'b1;
    wi = (ph == 2'd0) ? ui_idle : (widle && ui_idle);
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ck_q <= 1'b0; phy_ready <= 1'b0; pv <= 1'b0; pd <= '0; paux <= '0; pfec <= '0; err <= '0;
      edges <= '0; ph <= '0; wd <= '0; wa <= '0; wf <= '0; gated <= 1'b0; g <= '0;
      need_pre <= 1'b0; last_idle <= 1'b1; widle <= 1'b1; pn <= '0;
      for (int i = 0; i < 18; i++) win[i] <= '0;
      for (int j = 0; j < 16; j++) hist[j] <= '0;
    end else begin
      ck_q <= ck;
      pv   <= 1'b0;
      err  <= '0;
      if (!phy_reset_b) begin
        phy_ready <= 1'b0; edges <= '0; ph <= '0; gated <= 1'b0; g <= '0;
        need_pre <= 1'b0; last_idle <= 1'b1; widle <= 1'b1; pn <= '0;
        for (int i = 0; i < 18; i++) win[i] <= '0;
      end else if (!phy_ready) begin
        if (ck != ck_q) begin
          for (int i = 0; i < 18; i++) win[i] <= {win[i][14:0], line[i]};
          if (edges != 6'd63) edges <= edges + 6'd1;
          if (32'(edges) + 1 >= ALIGN && match) begin
            phy_ready <= 1'b1; ph <= '0; pn <= '0; last_idle <= 1'b1; gated <= 1'b0;
          end
        end
      end else if (ck != ck_q) begin
        widle <= wi;
        if (gated) need_pre <= 1'b1;
        gated <= 1'b0; g <= '0;
        if (ph == 2'd3) begin
          pv <= 1'b1; pd <= {lg, wd}; paux <= {la, wa[2:0]}; pfec <= {lf, wf[2:0]};
          last_idle <= wi;
          if (need_pre) begin
            need_pre <= 1'b0;
            if (!wi) err[1] <= 1'b1;
          end
        end else begin
          case (ph)
            2'd0: wd[15:0]  <= lg;
            2'd1: wd[31:16] <= lg;
            default: wd[47:32] <= lg;
          endcase
          wa[ph] <= la; wf[ph] <= lf;
        end
        ph <= ph + 2'd1;
        if (prbs_en) begin
          if (perr) err[4] <= 1'b1;
          for (int j = 0; j < 16; j++) hist[j] <= {hist[j][7:0], lg[j]};
          if (ui_idle) pn <= '0;
          else if (pn != 4'd9) pn <= pn + 4'd1;
        end else pn <= '0;
      end else begin
        if (!gated) begin
          gated <= 1'b1; g <= 10'd1;
          if (ph != 2'd0) begin err[2] <= 1'b1; ph <= '0; end
          else if (!last_idle) err[1] <= 1'b1;
          if (ck) err[3] <= 1'b1;
        end else if (32'(g) != GMAX + 1) begin
          if (32'(g) == GMAX) err[0] <= 1'b1;
          g <= g + 10'd1;
        end
      end
    end
  end
endmodule
""",
    sva="""
// outputs are never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({phy_ready, pv, err}))
  else $error("BoW: X on PHYReady / pv / err");
// a parallel word only comes from a ready slice
assert property (@(posedge clk) disable iff (!rst_n) pv |-> phy_ready)
  else $error("BoW: word without PHYReady");
// PHYResetB low takes PHYReady down on the next clock (sec. 6.5.1.1)
assert property (@(posedge clk) disable iff (!rst_n) !phy_reset_b |=> !phy_ready)
  else $error("BoW: PHYReady while PHYResetB is asserted");
// PHYReady rises only after a forwarded clock edge (self-alignment, sec. 6.5.1.3)
assert property (@(posedge clk) disable iff (!rst_n) $rose(phy_ready) |-> $past(phy_reset_b) && $past(ck) != $past(ck, 2))
  else $error("BoW: PHYReady without a clock edge");
// a gated clock produces no word
assert property (@(posedge clk) disable iff (!rst_n) phy_ready && $stable(ck) && phy_reset_b |=> !pv)
  else $error("BoW: word while the clock is gated");
// with redundancy on, AUX / FEC are spares
assert property (@(posedge clk) disable iff (!rst_n) pv && $past(rep_en) |-> paux == 4'h0 && pfec == 4'h0)
  else $error("BoW: AUX / FEC data with redundancy on");
// the rule checks the tests break on purpose: covers, not assertions
cover property (@(posedge clk) disable iff (!rst_n) err[0]);
cover property (@(posedge clk) disable iff (!rst_n) err[1]);
cover property (@(posedge clk) disable iff (!rst_n) err[2]);
cover property (@(posedge clk) disable iff (!rst_n) err[3]);
cover property (@(posedge clk) disable iff (!rst_n) err[4]);
cover property (@(posedge clk) disable iff (!rst_n) $rose(phy_ready));
cover property (@(posedge clk) disable iff (!rst_n) pv && rep_en);
""",
    smoke=r"""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic phy_reset_b = 1'b1, ck = 1'b0, aux = 1'b0, fec = 1'b0, rep_en = 1'b0, prbs_en = 1'b0;
logic [15:0] d = 16'h0;
logic [4:0]  bad_a = 5'd31, bad_b = 5'd31;
wire  phy_ready, pv;
wire  [63:0] pd;
wire  [3:0]  paux, pfec;
wire  [4:0]  err;

always #5 clk = ~clk;

bow_model u_dut (.clk(clk), .rst_n(rst_n), .phy_reset_b(phy_reset_b), .ck(ck), .d(d), .aux(aux), .fec(fec),
                 .rep_en(rep_en), .bad_a(bad_a), .bad_b(bad_b), .prbs_en(prbs_en), .phy_ready(phy_ready),
                 .pv(pv), .pd(pd), .paux(paux), .pfec(pfec), .err(err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// what the slice reported: the last word, every error bit seen, the clock of each
logic [63:0] w_pd;  logic [3:0] w_aux, w_fec;
integer nw = 0, e_seen [0:4], e_at [0:4], nclk = 0;
always @(posedge clk) begin
  nclk = nclk + 1;
  if (pv) begin nw = nw + 1; w_pd = pd; w_aux = paux; w_fec = pfec; end
  for (int i = 0; i < 5; i++) if (err[i]) begin e_seen[i] = e_seen[i] + 1; e_at[i] = nclk; end
end
task automatic settle(); repeat (2) @(posedge clk); #1; endtask
task automatic clr(); for (int i = 0; i < 5; i++) e_seen[i] = 0; endtask
function automatic bit no_err(); no_err = (e_seen[0] + e_seen[1] + e_seen[2] + e_seen[3] + e_seen[4]) == 0; endfunction

// one bench clock with the 18 physical lines {FEC, D, AUX}; tog toggles the forwarded clock
task automatic phy(input bit tog, input logic [17:0] x);
  @(negedge clk);
  if (tog) ck = !ck;
  aux = x[0]; d = x[16:1]; fec = x[17];
endtask
task automatic still(input integer n); repeat (n) phy(0, 18'h0); endtask
task automatic ui(input logic [15:0] v, input bit a = 0, input bit f = 0); phy(1, {f, v, a}); endtask
task automatic word(input logic [63:0] w, input logic [3:0] a = 0, input logic [3:0] f = 0);
  for (int k = 0; k < 4; k++) ui(w[16*k +: 16], a[k], f[k]);
endtask
task automatic train(input integer n, input logic [15:0] tp);
  for (int u = 0; u < n; u++) phy(1, {18{tp[15 - u % 16]}});
endtask
task automatic preset();
  @(negedge clk); phy_reset_b = 0; still(3); @(negedge clk); phy_reset_b = 1;
endtask
// physical lines for logical lanes l with redundancy around physical lines p, q (p < q, 31 = none)
function automatic logic [17:0] rmap(input logic [15:0] l, input integer p, input integer q);
  logic [17:0] x;
  integer pj;
  x = 18'h0;
  for (int j = 0; j < 16; j++) begin
    pj = (j + 1 <= p) ? j : (j + 1 >= q) ? j + 2 : j + 1;
    x[pj] = l[j];
  end
  rmap = x;
endfunction
integer t0, k;
logic [8:0] s [0:15];
logic [15:0] pl;
logic [15:0] tpat = 16'hF0CA;

initial begin
  clr();
  repeat (3) @(posedge clk);
  chk(phy_ready === 1'b0 && pv === 1'b0 && err === 5'h0, "reset: not ready, nothing out");
  rst_n = 1;
  // no training yet: random wire activity gives no PHYReady
  for (int u = 0; u < 40; u++) phy(1, {18{u[1] ^ u[3]}});
  chk(phy_ready === 1'b0, "no PHYReady without the training pattern");
  // wrong pattern
  preset(); train(64, 16'hF1CA);
  chk(phy_ready === 1'b0, "wrong training pattern: not ready");
  // the right one: ready after 32 edges, word boundary at the pattern start
  preset(); train(31, 16'hF0CA); settle();
  chk(phy_ready === 1'b0, "31 UI of pattern: not yet ready");
  phy(1, {18{1'b0}}); settle();    // UI 31: the pattern's last bit (TP[0] = 0)
  chk(phy_ready === 1'b1, "ready after 32 UI with the last 16 equal to the pattern");
  nw = 0;
  phy(1, {18{1'b1}}); phy(1, {18{1'b1}}); phy(1, {18{1'b1}}); phy(1, {18{1'b1}});  // pattern bits 15..12 = 1111
  settle();
  chk(nw == 1 && w_pd == {64{1'b1}} && w_aux == 4'hF && w_fec == 4'hF, "first word = first 4 UI of the pattern");
  train(12, 16'h0CA0);       // finish the pattern (bits 11..0) without a gate
  // bit ordering: UI k -> P_D[16k +: 16]
  word(64'h4444_3333_2222_1111, 4'b0101, 4'b1010); settle();
  chk(w_pd == 64'h4444_3333_2222_1111 && w_aux == 4'b0101 && w_fec == 4'b1010, "UI k lands in P_D[16k+15:16k], AUX / FEC bit k");
  // a proper gate: IDLE postamble, gate, IDLE preamble
  word(64'h0); still(3); clr(); still(20); word(64'h0); word(64'hDEAD_BEEF_0123_4567); word(64'h0); still(5);
  settle();
  chk(no_err(), "IDLE postamble / preamble around a gate: no error");
  chk(w_pd == 64'h0, "the IDLE postamble is delivered as a word");
  // non-IDLE postamble
  clr(); word(64'h0); word(64'h1); still(5); @(posedge clk);
  chk(e_seen[1] == 1 && e_seen[2] == 0, "gate after a non-IDLE word: postamble error");
  // non-IDLE preamble
  clr(); word(64'h0, 4'b0001); word(64'h0); still(4);
  chk(e_seen[1] == 1, "first word after a gate not IDLE (AUX set): preamble error");
  // partial word
  clr(); word(64'h0); ui(16'h0); ui(16'h0); still(4); @(posedge clk);
  chk(e_seen[2] == 1 && e_seen[1] == 0, "clock stopped after 2 UI of a word: error 2");
  k = nw; word(64'h0); word(64'hAB); word(64'h0); still(3); settle();
  chk(nw == k + 3 && w_pd == 64'h0, "the next words start at a word boundary again");
  // gated high: odd UI count
  clr(); word(64'h0); ui(16'h0); still(4); @(posedge clk);
  chk(e_seen[3] == 1 && e_seen[2] == 1, "clock gated high (mid-word): errors 3 and 2");
  ui(16'h0); ui(16'h0); ui(16'h0); still(3);   // back to low
  // gate length: 512 UI fine, 513 not
  clr(); word(64'h0); still(512); word(64'h0); still(3); @(posedge clk);
  chk(e_seen[0] == 0, "512 UI gated: no error");
  clr(); word(64'h0); t0 = nclk; still(513); settle();
  chk(e_seen[0] == 1 && e_at[0] - t0 == 515, "513th gated UI: error 0, one clock later");
  still(600); @(posedge clk);
  chk(e_seen[0] == 1, "error 0 once per gate");
  word(64'h0); still(3);
  // redundancy: D4 and D6 defective (physical 5 and 7)
  rep_en = 1; bad_a = 5'd7; bad_b = 5'd5;
  preset(); for (int u = 0; u < 48; u++) begin
    logic [17:0] x; x = {18{u % 16 == 0 || u % 16 == 1 || u % 16 == 2 || u % 16 == 3 ||
                        u % 16 == 8 || u % 16 == 9 || u % 16 == 12 || u % 16 == 14}};
    x[5] = u[0]; x[7] = !u[0];    // noise on the defective lines
    phy(1, x);
  end
  chk(phy_ready === 1'b1, "training ignores the defective lines");
  clr();
  for (int kk = 0; kk < 4; kk++) begin logic [17:0] x; x = rmap(16'h8001 << kk | 16'h0010, 5, 7); x[5] = 1; x[7] = 1; phy(1, x); end
  settle();
  chk(w_pd == {16'h0010 | 16'h8001 << 3, 16'h0010 | 16'h8001 << 2, 16'h0010 | 16'h8001 << 1, 16'h8011},
      "D4, D6 defective: logical D[4:0] on {D[3:0], AUX}, D[15:6] on {FEC, D[15:7]}");
  chk(w_aux == 4'h0 && w_fec == 4'h0, "redundancy on: PAUX / PFEC are 0");
  // logical D0 really travels on AUX, D15 on FEC
  phy(1, 18'h00001); phy(1, 18'h20000); phy(1, 18'h00040); phy(1, 18'h00010); settle();
  chk(w_pd == {16'h0010, 16'h0020, 16'h8000, 16'h0001}, "AUX carries logical D0, FEC D15, physical D5 / D3 carry D5 / D4");
  // one defective data line: D10 (physical 11)
  bad_a = 5'd11; bad_b = 5'd31; preset(); train(48, 16'hF0CA);
  phy(1, rmap(16'h0400, 11, 31)); phy(1, rmap(16'h0800, 11, 31)); phy(1, rmap(16'h0001, 11, 31)); phy(1, rmap(16'hFFFF, 11, 31));
  settle();
  chk(w_pd == {16'hFFFF, 16'h0001, 16'h0800, 16'h0400} && rmap(16'h0400, 11, 31) == 18'h00400, "D10 defective: D10 on physical D9, D11 stays");
  // only AUX and FEC defective: nothing moves
  bad_a = 5'd0; bad_b = 5'd17; preset(); train(48, 16'hF0CA);
  word(64'h8000_0001_1234_00FF); settle();
  chk(w_pd == 64'h8000_0001_1234_00FF, "AUX and FEC defective: no shift");
  // AUX and D3 defective: D3 and up shift up
  bad_a = 5'd4; bad_b = 5'd0; preset(); train(48, 16'hF0CA);
  phy(1, rmap(16'h0008, 0, 4)); phy(1, rmap(16'h8000, 0, 4)); phy(1, rmap(16'h0004, 0, 4)); phy(1, rmap(16'h0001, 0, 4));
  settle();
  chk(w_pd == {16'h0001, 16'h0004, 16'h8000, 16'h0008} && rmap(16'h8000, 0, 4) == 18'h20000,
      "AUX and D3 defective: D3 on D4 ... D15 on FEC");
  // FEC alone: no shift
  bad_a = 5'd17; bad_b = 5'd31; preset(); train(48, 16'hF0CA);
  word(64'h0001_8000_0010_0100); settle();
  chk(w_pd == 64'h0001_8000_0010_0100, "FEC alone defective: no shift");
  // AUX alone, named by bad_b: no shift
  bad_a = 5'd31; bad_b = 5'd0; preset(); train(48, 16'hF0CA);
  word(64'h8001_0002_4000_0100); settle();
  chk(w_pd == 64'h8001_0002_4000_0100, "AUX alone defective (second defect field): no shift");
  // a line named in bad_a with noise: trains with redundancy on, not with it off
  for (int r = 1; r >= 0; r--) begin
    rep_en = r[0]; bad_a = 5'd6; bad_b = 5'd31; preset();
    for (int u = 0; u < 48; u++) begin
      logic [17:0] x; x = {18{tpat[15 - u % 16]}}; x[6] = u[1]; phy(1, x);
    end
    settle();
    if (r == 1) chk(phy_ready === 1'b1, "redundancy on: noise on the line in bad_a is ignored in training");
    else        chk(phy_ready === 1'b0, "redundancy off: bad_a is ignored, the noisy line keeps PHYReady low");
  end
  // PRBS-9 checker
  rep_en = 0; bad_a = 5'd31; bad_b = 5'd31; prbs_en = 1; preset(); train(48, 16'hF0CA);
  word(64'h0); still(5); clr();
  for (int j = 0; j < 16; j++) s[j] = 9'(j * 29 + 3);
  word(64'h0);
  for (int u = 0; u < 40; u++) begin
    for (int j = 0; j < 16; j++) begin pl[j] = s[j][8] ^ s[j][4]; s[j] = {s[j][7:0], pl[j]}; end
    ui(pl);
  end
  word(64'h0); still(5);
  chk(e_seen[4] == 0 && e_seen[1] == 0, "PRBS-9 (x^9 + x^5 + 1) on 16 lanes: no error");
  clr(); word(64'h0);
  for (int u = 0; u < 40; u++) begin
    for (int j = 0; j < 16; j++) begin pl[j] = s[j][8] ^ s[j][4]; s[j] = {s[j][7:0], pl[j]}; end
    if (u == 20) pl[7] = !pl[7];
    ui(pl);
  end
  word(64'h0); still(5);
  chk(e_seen[4] >= 1, "one flipped bit: PRBS error");
  clr(); word(64'h0);
  for (int u = 0; u < 8; u++) ui(16'hFFFF);  // 8 UI: still locking, then IDLE
  word(64'h0); still(5);
  chk(e_seen[4] == 0, "no PRBS check before 9 UI of data");
  prbs_en = 0; clr(); word(64'h0); word(64'h1234); word(64'h0); still(5);
  chk(e_seen[4] == 0, "checker off: no PRBS error");
  // PHYResetB drops PHYReady
  @(negedge clk); phy_reset_b = 0; settle();
  chk(phy_ready === 1'b0, "PHYResetB low: PHYReady low on the next clock");
  @(negedge clk); phy_reset_b = 1; k = nw; word(64'h1); word(64'h0); still(3);
  chk(phy_ready === 1'b0 && nw == k, "after reset no words until retrained");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #4000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
