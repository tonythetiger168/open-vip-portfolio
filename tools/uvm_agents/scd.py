# ISO/IEC 7816-3 smartcard VIP: a smartcard model (the conditional-access
# card of a set-top box) with an interface-device (reader) agent.
#
# Agent -> DUT (reader): the card clock sc_clk, the card's RST sc_rst_n, the
# reader's open-drain I/O pull io_m_lo. DUT -> agent (card): io_s_lo, the
# card's pull. The I/O line is high (pull-up) unless either side pulls it.
# The card samples on the sc_clk rising edge and changes io_s_lo on the
# falling edge.
#
# tb/top_tb.sv scd_model is the card (T = 0, direct convention):
#   RST low (sampled on sc_clk) resets the card; the memory is kept. ATR_DLY
#   clocks after RST rises the card sends the ATR 3B 02 53 43 (no interface
#   bytes: F = 372, D = 1, T = 0, two historical bytes). Characters: start
#   bit, 8 data bits LSB first, even parity, at one etu = F / D clocks per
#   bit, 12 etu apart. The card samples each bit in its middle; a parity
#   error makes it pull I/O low from 10.5 to 11.5 etu (the reader repeats).
#   It checks for that error signal from the reader at 11 etu of each
#   character it sends and repeats the character at 14 etu, at most 3
#   times, then drops the response. It answers 16 etu after the leading edge
#   of the last character it received.
#   PPS (first exchange after the ATR only): FF PPS0 [PPS1] PCK with T = 0,
#   no PPS2 / PPS3, a good PCK and (Fi, Di) in {1: 372, 9: 512} x {1: 1,
#   2: 2, 3: 4, 4: 8} with F divisible by D: echoed, then etu = F / D. Any
#   other PPS gets no answer.
#   TPDU header CLA INS P1 P2 P3 (Le / Lc = P3, 0 means 256) on a 256-byte
#   file at offset P1P2: READ BINARY (B0): procedure byte B0, the bytes, 90
#   00. UPDATE BINARY (D6): procedure byte D6, the reader's bytes are written,
#   90 00. Offset + length past 256: 6B 00. CLA other than 00: 6E 00. Other
#   INS: 6D 00. File byte i = i ^ 0x5C at power-up; no reset clears the file.
# In a SoC bench the card connects to the smartcard interface's CLK, RST and
# I/O (io_m_lo = the interface pulls I/O, I/O = !(io_m_lo | io_s_lo)); the
# agent runs passive and its monitor records every clock.

SCD_FUNCS = """
function automatic int scd_f(bit [3:0] fi);
  case (fi)
    4'd1: return 372;
    4'd9: return 512;
    default: return 0;
  endcase
endfunction
function automatic int scd_d(bit [3:0] di);
  case (di)
    4'd1: return 1;
    4'd2: return 2;
    4'd3: return 4;
    4'd4: return 8;
    default: return 0;
  endcase
endfunction
// the etu a PPS1 byte gives, 0 when the card does not support it
function automatic int scd_etu(bit [7:0] pps1);
  int f = scd_f(pps1[7:4]), d = scd_d(pps1[3:0]);
  if (f == 0 || d == 0 || f % d != 0) return 0;
  return f / d;
endfunction
"""

SPEC = dict(
    vip="Smartcard_ISO7816-UVM-VIP", p="scd", P="SCD", dir="scd", family="Security",
    desc="ISO/IEC 7816-3 smartcard VIP: card model with ATR, PPS (Fi / Di), T = 0 TPDUs (READ / UPDATE BINARY, "
         "status words), even parity with error signalling and character repetition in both directions; "
         "interface-device agent and I/O monitor.",
    about="""
A set-top box talks to its conditional-access smartcard over the ISO 7816-3
I/O line. The VIP's DUT model is the card, so a SoC bench can hang it on the
smartcard interface's CLK, RST and I/O. The agent is the interface device:
it resets the card and reads the ATR, negotiates the etu with PPS (good,
unsupported and corrupted requests), sends T = 0 TPDUs (READ BINARY,
UPDATE BINARY, wrong class, wrong instruction, offset out of range), sends
characters with bad parity and signals parity errors on the card's
characters, up to the card giving the response up. The scoreboard runs its
own copy of the card on the monitored clock-by-clock RST and I/O and
predicts the card's I/O pull on every sc_clk rising edge: ATR timing, every
character and its parity, the 16 etu turnaround, error signals, repeated
characters, procedure bytes, data and status words.""",
    defs=SCD_FUNCS,
    timeout=4000000,
    cfg="""int unsigned half = 1;     // clocks per sc_clk half period
int unsigned gap  = 16;    // clocks with sc_clk stopped between items""",
    ports=[("in", "logic", "sc_clk"), ("in", "logic", "sc_rst_n"), ("in", "logic", "io_m_lo"),
           ("out", "logic", "io_s_lo")],
    fields=[
        ("bit [1:0]", "mo", "req", "q"),        # {sc_rst_n, io_m_lo} per sc_clk rise
        ("bit", "so", "rsp", "q"),              # io_s_lo per sc_clk rise
        ("bit [3:0]", "kind", "info", "rand"),
        ("bit [3:0]", "blk", "info", "rand"),
        ("bit [2:0]", "cnt", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [7:0]", "sw1", "info"),
        ("bit [7:0]", "sw2", "info"),
    ],
    tr_functions="""
// kind: 0 reset + ATR, 1 PPS (PPS1 from seed), 2 PPS with a bad PCK, 3 READ
// BINARY (cnt + 1 bytes at 16 blk), 4 UPDATE BINARY, 5 READ past the end, 6
// CLA 80, 7 INS CA, 8 READ with a parity error on header byte seed % 5, 9
// READ with the reader signalling an error on card character seed % 3, 10
// UPDATE with a parity error on a data byte, 11 READ of 256 bytes (P3 = 0),
// 12 READ with every try of the first card character refused, 13-15 READ /
// UPDATE mix
function void set(int k, int b = 0, int n = 0, bit [31:0] s = 32'h1); kind = k; blk = b; cnt = n; seed = s; endfunction
function int kk();
  if (kind >= 13) return (kind % 2 == 0) ? 4 : 3;
  return kind;
endfunction
function bit [7:0] pps1();
  bit [7:0] t [6] = '{8'h11, 8'h12, 8'h13, 8'h94, 8'h14, 8'h91};
  return t[seed % 6];
endfunction
function int len();
  return (kk() == 11) ? 256 : int'(cnt) + 1;
endfunction
function bit [7:0] hdr(int i);
  bit [7:0] h [5];
  h[0] = (kk() == 6) ? 8'h80 : 8'h00;
  h[1] = (kk() == 7) ? 8'hCA : (kk() == 4 || kk() == 10) ? 8'hD6 : 8'hB0;
  h[2] = 8'h00;
  h[3] = (kk() == 5) ? 8'hFC : (kk() == 11) ? 8'h00 : {blk, 4'h0};
  h[4] = (kk() == 11) ? 8'h00 : (kk() == 5) ? 8'h08 : 8'(len());
  return h[i];
endfunction
function bit [7:0] wbyte(int i);
  bit [31:0] x = (seed | 1) ^ (32'(i) * 32'h9E37_79B9);
  x ^= x >> 13; x *= 32'h5BD1_E995; x ^= x >> 15;
  return x[7:0];
endfunction
""",
    drv_rsp=False,
    drv_members="""int             etu = 372;
bit             rn = 0;
scd_transaction cur;""",
    drv_tasks="""
// one sc_clk period: outputs at the falling edge, the line at the rising edge
task automatic clk1(bit lo, output bit io);
  vif.drv_cb.sc_clk   <= 1'b0;
  vif.drv_cb.sc_rst_n <= rn;
  vif.drv_cb.io_m_lo  <= lo;
  repeat (cfg.half) @(vif.drv_cb);
  vif.drv_cb.sc_clk <= 1'b1;
  io = !(lo || vif.drv_cb.io_s_lo);
  cur.mo.push_back({rn, lo});
  repeat (cfg.half) @(vif.drv_cb);
endtask
task automatic idle(int n);
  bit io;
  repeat (n) clk1(1'b0, io);
endtask
// send a character; badpar sends it with odd parity. err: the card signalled an error
task automatic tx_char(bit [7:0] b, bit badpar, output bit err);
  bit io;
  bit [9:0] f = {(^b) ^ badpar, b, 1'b0};    // start first, LSB first
  err = 0;
  for (int c = 0; c < 12 * etu; c++) begin
    int k = c / etu;
    clk1(k <= 9 ? !f[k] : 1'b0, io);
    if (c == 11 * etu - etu / 4 && !io) err = 1;
  end
endtask
// send with repetition: a bad parity first when badpar, then until accepted (4 tries)
task automatic tx_rep(bit [7:0] b, bit badpar);
  bit err;
  int n = 0;
  tx_char(b, badpar, err);
  while (err && n < 4) begin idle(2 * etu); tx_char(b, 1'b0, err); n++; end
endtask
// receive a character: wait up to 40 etu for its start bit, sample mid-bit;
// sig_err pulls I/O low at 10.5 .. 11.5 etu. ok = 0 on a timeout or bad parity
task automatic rx_char(bit sig_err, output bit [7:0] b, output bit ok);
  bit io;
  bit [9:0] s = 0;
  int c = 0;
  ok = 0; b = 0;
  do begin clk1(1'b0, io); c++; end while (io && c < 40 * etu);
  if (io) return;
  for (c = 1; c < 10 * etu; c++) begin
    clk1(1'b0, io);
    if (c % etu == etu / 2) s[c / etu] = io;
  end
  b = s[8:1];
  ok = !s[0] && (^s[9:1]) == 1'b0;
  if (sig_err) begin
    for (; c < 21 * etu / 2; c++) clk1(1'b0, io);
    for (; c < 23 * etu / 2; c++) clk1(1'b1, io);
    ok = 0;
  end
endtask
// a character from the card that is repeated after an error: refuse the first `refuse` tries
task automatic rx_rep(int refuse, output bit [7:0] b, output bit ok);
  rx_char(refuse > 0, b, ok);
  for (int n = 1; n <= refuse && n < 4; n++) rx_char(n < refuse, b, ok);
endtask
""",
    drv_desc="one item per exchange with sc_clk running: RST low and the ATR; a PPS request and its echo (the etu follows an accepted PPS); or a TPDU header, the procedure byte, the data in either direction and the status words, with parity errors sent and signalled as the kind asks; then 20 etu idle and sc_clk stopped for cfg.gap clocks",
    drv_idle="""
vif.drv_cb.sc_clk   <= 1'b0;
vif.drv_cb.sc_rst_n <= 1'b0;
vif.drv_cb.io_m_lo  <= 1'b0;
""",
    drv_item="""
bit [7:0] b, pb;
bit ok, e;
cur = t;
t.mo.delete();
t.sw1 = 0; t.sw2 = 0;
@(vif.drv_cb);
if (t.kk() == 0) begin
  rn = 0; idle(200);
  rn = 1; etu = 372;
  for (int i = 0; i < 4; i++) begin rx_char(1'b0, b, ok); if (!ok) break; end
end else if (t.kk() == 1 || t.kk() == 2) begin
  bit [7:0] p [4] = '{8'hFF, 8'h10, t.pps1(), 8'h00};
  bit match = 1;
  p[3] = p[0] ^ p[1] ^ p[2] ^ (t.kk() == 2 ? 8'h01 : 8'h00);
  for (int i = 0; i < 4; i++) tx_rep(p[i], 1'b0);
  for (int i = 0; i < 4; i++) begin rx_char(1'b0, b, ok); if (!ok || b != p[i]) begin match = 0; break; end end
  if (match) etu = scd_etu(p[2]);
end else begin
  int n = t.len();
  for (int i = 0; i < 5; i++) tx_rep(t.hdr(i), t.kk() == 8 && i == t.seed % 5);
  rx_rep(t.kk() == 12 ? 4 : (t.kk() == 9 && t.seed % 3 == 0) ? 1 : 0, pb, ok);
  if (ok && pb == t.hdr(1) && t.hdr(1) == 8'hB0) begin
    for (int i = 0; i < n && ok; i++) rx_rep((t.kk() == 9 && t.seed % 3 == 1 && i == 0) ? 1 : 0, b, ok);
    if (ok) rx_rep((t.kk() == 9 && t.seed % 3 == 2) ? 1 : 0, t.sw1, ok);
    if (ok) rx_char(1'b0, t.sw2, ok);
  end else if (ok && pb == t.hdr(1) && t.hdr(1) == 8'hD6) begin
    idle(16 * etu);
    for (int i = 0; i < n; i++) tx_rep(t.wbyte(i), t.kk() == 10 && i == t.seed % n);
    rx_char(1'b0, t.sw1, ok);
    if (ok) rx_char(1'b0, t.sw2, ok);
  end else if (ok) begin
    t.sw1 = pb;
    rx_char(1'b0, t.sw2, ok);
  end
end
idle(20 * etu);
repeat (cfg.gap) @(vif.drv_cb);
""",
    mon_desc="RST and both I/O pulls at every sc_clk rising edge; sc_clk stopped for more than half of cfg.gap clocks ends the item",
    mon_run="""
forever begin
  scd_transaction t;
  bit pc;
  int q = 0;
  pc = vif.mon_cb.sc_clk;
  @(vif.mon_cb);
  while (!(pc === 1'b0 && vif.mon_cb.sc_clk === 1'b1)) begin pc = vif.mon_cb.sc_clk; @(vif.mon_cb); end
  t = scd_transaction::type_id::create("t");
  forever begin
    if (pc === 1'b0 && vif.mon_cb.sc_clk === 1'b1) begin
      t.mo.push_back({vif.mon_cb.sc_rst_n, vif.mon_cb.io_m_lo});
      t.so.push_back(vif.mon_cb.io_s_lo);
      q = 0;
    end else if (++q > cfg.gap / 2) break;
    pc = vif.mon_cb.sc_clk;
    @(vif.mon_cb);
  end
  publish(t);
end
""",
    sb_members="""// the card (scoreboard copy), kept across items
localparam int ATR_DLY = 400;
bit [7:0]  mem [256];
bit        minit = 0;
int        e = 372, ps = 0, atrc = 0, sinc = 16383;
bit        neg = 0;
bit        ra = 0;
int        rt = 0;
bit [9:0]  rsh = 0;
bit        rbad = 0;
bit [7:0]  h [5];
int        hc = 0;
bit [7:0]  pp [5];
int        pc = 0, newe = 0;
int        dk = 0, nn = 0, off = 0;
bit        ta = 0, txp = 0, terr = 0;
int        ct = 0, tries = 0, seq = 0, ti = 0, tn = 0;
bit [7:0]  tb = 0, sw1 = 0, sw2 = 0;
bit        o_lo = 0;

function bit [7:0] txbyte(int i);
  case (seq)
    0: case (i) 0: return 8'h3B; 1: return 8'h02; 2: return 8'h53; default: return 8'h43; endcase
    1: return (i == tn - 1) ? pp[pc - 1] : pp[i];
    2: return (i == 0) ? sw1 : sw2;
    3: return (i == 0) ? h[1] : (i <= nn) ? mem[(off + i - 1) % 256] : (i == nn + 1) ? 8'h90 : 8'h00;
    default: return h[1];
  endcase
endfunction
function void start_seq(int s, int n);
  seq = s; tn = n; ti = 0; txp = 1; ps = 6;
endfunction
function void sw(bit [7:0] a, bit [7:0] b);
  sw1 = a; sw2 = b; start_seq(2, 2);
endfunction
function void got_char(bit [7:0] d);
  case (ps)
    2: if (neg && d == 8'hFF) begin ps = 4; pp[0] = d; pc = 1; end
       else begin neg = 0; h[0] = d; hc = 1; ps = 3; end
    4: begin
         int tot;
         pp[pc] = d; pc++;
         tot = 3 + pp[1][4] + pp[1][5] + pp[1][6];
         if (pc == tot) begin
           bit [7:0] x = 0;
           int ne = pp[1][4] ? scd_etu(pp[2]) : e;
           for (int i = 0; i < tot; i++) x ^= pp[i];
           if (x == 0 && pp[1][3:0] == 0 && pp[1][6:5] == 0 && ne != 0) begin
             neg = 0; newe = ne; start_seq(1, tot);
           end else ps = 2;
         end
       end
    3: begin
         h[hc] = d; hc++;
         if (hc == 5) begin
           nn = (h[4] == 0) ? 256 : h[4];
           off = {h[2], h[3]};
           if (h[0] != 0) sw(8'h6E, 8'h00);
           else if (h[1] != 8'hB0 && h[1] != 8'hD6) sw(8'h6D, 8'h00);
           else if (off + nn > 256) sw(8'h6B, 8'h00);
           else if (h[1] == 8'hB0) start_seq(3, nn + 3);
           else begin dk = 0; start_seq(4, 1); end
         end
       end
    5: begin
         mem[(off + dk) % 256] = d; dk++;
         if (dk == nn) sw(8'h90, 8'h00);
       end
    default: ;
  endcase
endfunction
""",
    predict="""
if (!minit) begin for (int i = 0; i < 256; i++) mem[i] = 8'(i ^ 8'h5C); minit = 1; end
t.so.delete();
foreach (t.mo[i]) begin
  bit io;
  t.so.push_back(o_lo);
  io = !(t.mo[i][0] || o_lo);
  if (!t.mo[i][1]) begin
    e = 372; ps = 1; atrc = 0; sinc = 16383; neg = 0; ra = 0; rt = 0; ta = 0; txp = 0; o_lo = 0; hc = 0; pc = 0;
    continue;
  end
  if (sinc < 16383) sinc++;
  if (ps == 1) begin
    atrc++;
    if (atrc == ATR_DLY) start_seq(0, 4);
  end
  // receiver
  if (!ta && !txp && ps != 1) begin
    if (!ra) begin if (!io) begin ra = 1; rt = 0; rbad = 0; sinc = 0; end end
    else begin
      rt++;
      if (rt % e == e / 2 && rt / e <= 9) begin
        rsh[rt / e] = io;
        if (rt / e == 0 && io) ra = 0;
      end
      if (ra && rt == 10 * e && (^rsh[9:1]) == 1'b0) begin ra = 0; got_char(rsh[8:1]); end
      else if (ra && rt == 10 * e) rbad = 1;
      if (ra && rbad && rt == 23 * e / 2) ra = 0;
    end
  end
  // transmitter
  if (ta) begin
    ct++;
    if (ct == 11 * e && !io) terr = 1;
    if ((!terr && ct == 12 * e) || (terr && ct == 14 * e)) begin
      if (terr) begin
        tries++;
        if (tries == 4) begin ta = 0; ps = 2; end
        else begin ct = 0; terr = 0; end
      end else begin
        ti++;
        if (ti < tn) begin ct = 0; tb = txbyte(ti); tries = 0; end
        else begin
          ta = 0;
          if (seq == 1) e = newe;
          ps = (seq == 4) ? 5 : 2;
          if (seq == 0) neg = 1;
          sinc = 16383;
        end
      end
    end
  end else if (txp && (sinc >= 16 * e || seq == 0) && !ra) begin
    txp = 0; ta = 1; ct = 0; terr = 0; tries = 0; tb = txbyte(0);
  end
  // the pull for the next period
  if (ta) begin
    int k = ct / e;
    o_lo = (k == 0) ? 1'b1 : (k <= 8) ? !tb[k - 1] : (k == 9) ? !(^tb) : 1'b0;
  end else o_lo = ra && rbad && rt >= 21 * e / 2 && rt < 23 * e / 2;
end
""",
    checks="",
    coverage="""
cp_kind : coverpoint tr.kind { bins k[] = {[0:12]}; bins mix = {[13:15]}; }
cp_sw1  : coverpoint tr.sw1 { bins ok = {8'h90}; bins wrong_p = {8'h6B}; bins wrong_ins = {8'h6D};
                              bins wrong_cla = {8'h6E}; bins none = {8'h00}; }
""",
    directed="""
// ATR, PPS paths, every TPDU outcome, parity errors both ways, repetition limit, reset in the middle
t = item(); t.set(3); send(t);              // before any reset: the card is off
t = item(); t.set(0); send(t);
t = item(); t.set(1, 0, 0, 32'd4); send(t); // PPS 14: 372 / 8, refused
t = item(); t.set(2, 0, 0, 32'd3); send(t); // bad PCK
t = item(); t.set(1, 0, 0, 32'd3); send(t); // PPS 94: 512 / 8 = 64 clocks
t = item(); t.set(1, 0, 0, 32'd1); send(t); // no longer negotiable
t = item(); t.set(3, 2, 3); send(t);
t = item(); t.set(4, 2, 3, 32'h77); send(t);
t = item(); t.set(3, 2, 3); send(t);
t = item(); t.set(5); send(t);
t = item(); t.set(6); send(t);
t = item(); t.set(7); send(t);
for (int i = 0; i < 5; i++) begin t = item(); t.set(8, 1, 1, i); send(t); end
for (int i = 0; i < 3; i++) begin t = item(); t.set(9, 3, 2, i); send(t); end
t = item(); t.set(10, 4, 4, 32'h21); send(t);
t = item(); t.set(3, 4, 4); send(t);
t = item(); t.set(12, 5, 1); send(t);       // the card gives up
t = item(); t.set(3, 5, 1); send(t);
t = item(); t.set(11); send(t);             // 256 bytes
t = item(); t.set(0); send(t);              // reset: back to 372, data kept
t = item(); t.set(1, 0, 0, 32'd2); send(t); // PPS 13: 93 clocks
t = item(); t.set(3, 2, 3); send(t);
t = item(); t.set(0); send(t);
t = item(); t.set(1, 0, 0, 32'd0); send(t); // PPS 11: 372
t = item(); t.set(4, 15, 7, 32'h99); send(t);
t = item(); t.set(3, 15, 7); send(t);
t = item(); t.set(0); send(t);
t = item(); t.set(1, 0, 0, 32'd3); send(t);
""",
    drain_ns=40000,
    model="""
module scd_model #(
  parameter int ATR_DLY = 400
) (
  input  logic clk,
  input  logic rst_n,
  input  logic sc_clk,
  input  logic sc_rst_n,
  input  logic io_m_lo,
  output logic io_s_lo
);
  localparam logic [2:0] P_OFF = 3'd0, P_ATRW = 3'd1, P_IDLE = 3'd2, P_HDR = 3'd3, P_PPS = 3'd4,
                         P_DATA = 3'd5, P_RESP = 3'd6;
  localparam logic [2:0] S_ATR = 3'd0, S_PPS = 3'd1, S_SW = 3'd2, S_RD = 3'd3, S_ACK = 3'd4;
  function automatic logic [9:0] etu_of(input logic [7:0] p);
    logic [9:0] f, q;
    logic [3:0] d;
    f = (p[7:4] == 4'd1) ? 10'd372 : (p[7:4] == 4'd9) ? 10'd512 : 10'd0;
    d = (p[3:0] == 4'd1) ? 4'd1 : (p[3:0] == 4'd2) ? 4'd2 : (p[3:0] == 4'd3) ? 4'd4 : (p[3:0] == 4'd4) ? 4'd8 : 4'd0;
    if (d == 0) etu_of = 10'd0;      // f = 0 gives 0 below
    else begin
      q = f / 10'(d);
      etu_of = (q * 10'(d) == f) ? q : 10'd0;
    end
  endfunction

  logic [7:0]  mem [0:255];
  logic [9:0]  e, newe;
  logic [2:0]  ps, seq;
  logic        neg, ra, rbad, ta, txp, terr;
  logic [15:0] atrc;
  logic [13:0] sinc, rt, ct;
  logic [9:0]  rsh;
  logic [7:0]  h0, h1, h2, h3, h4, p0, p1, p2, p3, sw1, sw2;
  logic [2:0]  hc, pc, tries;
  logic [8:0]  dk, nn, ti, tn;
  logic [15:0] off;
  logic        n_lo;
  wire         io = !(io_m_lo || io_s_lo);
  wire         _unused = &{1'b0, clk};

  // the file is non-volatile: its factory content, kept across every reset
  initial foreach (mem[k]) mem[k] = 8'(k) ^ 8'h5C;

  always_ff @(posedge sc_clk or negedge rst_n) begin
    if (!rst_n) begin
      ps <= P_OFF;      // powered, RST not yet seen: the card ignores I/O; RST low sets the rest
      n_lo <= 1'b0;
    end else begin : step
      logic [9:0]  v_e, v_newe, ne;
      logic [2:0]  v_ps, v_seq, v_hc, v_pc, v_tries;
      logic        v_neg, v_ra, v_rbad, v_ta, v_txp, v_terr, got;
      logic [15:0] v_atrc, v_off;
      logic [13:0] v_sinc, v_rt, v_ct;
      logic [9:0]  v_rsh;
      logic [7:0]  v_h0, v_h1, v_h2, v_h3, v_h4, v_p0, v_p1, v_p2, v_p3, v_sw1, v_sw2, d, x, tb;
      logic [8:0]  v_dk, v_nn, v_ti, v_tn;
      logic [3:0]  k;
      logic [2:0]  tot;
      v_e = e; v_newe = newe; v_ps = ps; v_seq = seq; v_hc = hc; v_pc = pc; v_tries = tries;
      v_neg = neg; v_ra = ra; v_rbad = rbad; v_ta = ta; v_txp = txp; v_terr = terr;
      v_atrc = atrc; v_off = off; v_sinc = sinc; v_rt = rt; v_ct = ct; v_rsh = rsh;
      v_h0 = h0; v_h1 = h1; v_h2 = h2; v_h3 = h3; v_h4 = h4; v_p0 = p0; v_p1 = p1; v_p2 = p2; v_p3 = p3;
      v_sw1 = sw1; v_sw2 = sw2; v_dk = dk; v_nn = nn; v_ti = ti; v_tn = tn;
      got = 1'b0; d = '0; tb = '0;
      if (!sc_rst_n) begin
        v_e = 10'd372; v_ps = P_ATRW; v_atrc = '0; v_sinc = 14'h3FFF; v_neg = 1'b0; v_ra = 1'b0; v_rt = '0;
        v_ta = 1'b0; v_txp = 1'b0; v_hc = '0; v_pc = '0;
        n_lo <= 1'b0;
      end else if (v_ps == P_OFF) n_lo <= 1'b0;
      else begin
        if (v_sinc != 14'h3FFF) v_sinc = v_sinc + 14'd1;
        if (v_ps == P_ATRW) begin
          v_atrc = v_atrc + 16'd1;
          if (v_atrc == 16'(ATR_DLY)) begin v_seq = S_ATR; v_tn = 9'd4; v_ti = '0; v_txp = 1'b1; v_ps = P_RESP; end
        end
        // receiver
        if (!v_ta && !v_txp && v_ps != P_ATRW && v_ps != P_OFF) begin
          if (!v_ra) begin if (!io) begin v_ra = 1'b1; v_rt = '0; v_rbad = 1'b0; v_sinc = '0; end end
          else begin
            v_rt = v_rt + 14'd1;
            if (v_rt % 14'(v_e) == 14'(v_e / 10'd2) && v_rt / 14'(v_e) <= 14'd9) begin
              v_rsh[4'(v_rt / 14'(v_e))] = io;
              if (v_rt / 14'(v_e) == 14'd0 && io) v_ra = 1'b0;
            end
            if (v_ra && v_rt == 14'(v_e) * 14'd10) begin
              if ((^v_rsh[9:1]) == 1'b0) begin v_ra = 1'b0; got = 1'b1; d = v_rsh[8:1]; end
              else v_rbad = 1'b1;
            end
            if (v_ra && v_rbad && v_rt == 14'(v_e) * 14'd23 / 14'd2) v_ra = 1'b0;
          end
        end
        // a character received
        if (got) begin
          case (v_ps)
            P_IDLE:
              if (v_neg && d == 8'hFF) begin v_ps = P_PPS; v_p0 = d; v_pc = 3'd1; end
              else begin v_neg = 1'b0; v_h0 = d; v_hc = 3'd1; v_ps = P_HDR; end
            P_PPS: begin
              case (v_pc) 3'd1: v_p1 = d; 3'd2: v_p2 = d; 3'd3: v_p3 = d; default: ; endcase   // PPS2 / PPS3: refused below
              v_pc = v_pc + 3'd1;
              tot = 3'd3 + 3'(v_p1[4]) + 3'(v_p1[5]) + 3'(v_p1[6]);
              if (v_pc == tot) begin
                x = v_p0 ^ v_p1 ^ v_p2 ^ ((tot == 3'd4) ? v_p3 : 8'h0);
                ne = v_p1[4] ? etu_of(v_p2) : v_e;
                if (x == 8'h0 && v_p1[3:0] == 4'h0 && v_p1[6:5] == 2'b00 && ne != 0) begin
                  v_neg = 1'b0; v_newe = ne; v_seq = S_PPS; v_tn = 9'(tot); v_ti = '0; v_txp = 1'b1; v_ps = P_RESP;
                end else v_ps = P_IDLE;
              end
            end
            P_HDR: begin
              case (v_hc) 3'd1: v_h1 = d; 3'd2: v_h2 = d; 3'd3: v_h3 = d; default: v_h4 = d; endcase
              v_hc = v_hc + 3'd1;
              if (v_hc == 3'd5) begin
                v_nn = (v_h4 == 8'h0) ? 9'd256 : 9'(v_h4);
                v_off = {v_h2, v_h3};
                v_ti = '0; v_txp = 1'b1; v_ps = P_RESP;
                if (v_h0 != 8'h0) begin v_seq = S_SW; v_tn = 9'd2; v_sw1 = 8'h6E; v_sw2 = 8'h00; end
                else if (v_h1 != 8'hB0 && v_h1 != 8'hD6) begin v_seq = S_SW; v_tn = 9'd2; v_sw1 = 8'h6D; v_sw2 = 8'h00; end
                else if (17'(v_off) + 17'(v_nn) > 17'd256) begin v_seq = S_SW; v_tn = 9'd2; v_sw1 = 8'h6B; v_sw2 = 8'h00; end
                else if (v_h1 == 8'hB0) begin v_seq = S_RD; v_tn = v_nn + 9'd3; end
                else begin v_seq = S_ACK; v_tn = 9'd1; v_dk = '0; end
              end
            end
            P_DATA: begin
              mem[8'(v_off + 16'(v_dk))] <= d;
              v_dk = v_dk + 9'd1;
              if (v_dk == v_nn) begin
                v_seq = S_SW; v_tn = 9'd2; v_sw1 = 8'h90; v_sw2 = 8'h00; v_ti = '0; v_txp = 1'b1; v_ps = P_RESP;
              end
            end
            default: ;
          endcase
        end
        // transmitter
        if (v_ta) begin
          v_ct = v_ct + 14'd1;
          if (v_ct == 14'(v_e) * 14'd11 && !io) v_terr = 1'b1;
          if ((!v_terr && v_ct == 14'(v_e) * 14'd12) || (v_terr && v_ct == 14'(v_e) * 14'd14)) begin
            if (v_terr) begin
              v_tries = v_tries + 3'd1;
              if (v_tries == 3'd4) begin v_ta = 1'b0; v_ps = P_IDLE; end
              else begin v_ct = '0; v_terr = 1'b0; end
            end else begin
              v_ti = v_ti + 9'd1;
              if (v_ti < v_tn) begin v_ct = '0; v_tries = '0; end
              else begin
                v_ta = 1'b0;
                if (v_seq == S_PPS) v_e = v_newe;
                v_ps = (v_seq == S_ACK) ? P_DATA : P_IDLE;
                if (v_seq == S_ATR) v_neg = 1'b1;
                v_sinc = 14'h3FFF;
              end
            end
          end
        end else if (v_txp && (v_sinc >= 14'(v_e) * 14'd16 || v_seq == S_ATR) && !v_ra) begin
          v_txp = 1'b0; v_ta = 1'b1; v_ct = '0; v_terr = 1'b0; v_tries = '0;
        end
        // the character being sent
        case (v_seq)
          S_ATR: tb = (v_ti == 0) ? 8'h3B : (v_ti == 1) ? 8'h02 : (v_ti == 2) ? 8'h53 : 8'h43;
          S_PPS: tb = (v_ti == 0) ? v_p0 : (v_ti == 1) ? v_p1 : (v_ti == 2) ? v_p2 : v_p3;   // the echo
          S_SW:  tb = (v_ti == 0) ? v_sw1 : v_sw2;
          S_RD:  tb = (v_ti == 0) ? v_h1 : (v_ti <= v_nn) ? mem[8'(v_off + 16'(v_ti) - 16'd1)] :
                      (v_ti == v_nn + 9'd1) ? 8'h90 : 8'h00;
          default: tb = v_h1;
        endcase
        // the pull for the next period
        if (v_ta) begin
          k = 4'(v_ct / 14'(v_e));
          n_lo <= (k == 0) ? 1'b1 : (k <= 4'd8) ? !tb[k - 4'd1] : (k == 4'd9) ? !(^tb) : 1'b0;
        end else n_lo <= v_ra && v_rbad && v_rt >= 14'(v_e) * 14'd21 / 14'd2 && v_rt < 14'(v_e) * 14'd23 / 14'd2;
      end
      e <= v_e; newe <= v_newe; ps <= v_ps; seq <= v_seq; hc <= v_hc; pc <= v_pc; tries <= v_tries;
      neg <= v_neg; ra <= v_ra; rbad <= v_rbad; ta <= v_ta; txp <= v_txp; terr <= v_terr;
      atrc <= v_atrc; off <= v_off; sinc <= v_sinc; rt <= v_rt; ct <= v_ct; rsh <= v_rsh;
      h0 <= v_h0; h1 <= v_h1; h2 <= v_h2; h3 <= v_h3; h4 <= v_h4; p0 <= v_p0; p1 <= v_p1; p2 <= v_p2; p3 <= v_p3;
      sw1 <= v_sw1; sw2 <= v_sw2; dk <= v_dk; nn <= v_nn; ti <= v_ti; tn <= v_tn;
    end
  end

  // falling sc_clk: the pull changes
  always_ff @(negedge sc_clk or negedge rst_n) begin
    if (!rst_n) io_s_lo <= 1'b0;
    else        io_s_lo <= n_lo;
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({sc_clk, sc_rst_n, io_m_lo, io_s_lo}))
  else $error("SCD: X on CLK, RST or I/O");
assert property (@(posedge clk) disable iff (!rst_n) $changed(io_s_lo) |-> !sc_clk)
  else $error("SCD: card I/O changed while CLK is high");
cover property (@(posedge clk) disable iff (!rst_n) io_m_lo && io_s_lo);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;      // a falling edge: the card has no clock to see a level reset
logic sc_clk = 1'b0, sc_rst_n = 1'b1, io_m_lo = 1'b0;
wire io_s_lo;

always #5 clk = ~clk;

scd_model u_dut (.clk(clk), .rst_n(rst_n), .sc_clk(sc_clk), .sc_rst_n(sc_rst_n), .io_m_lo(io_m_lo), .io_s_lo(io_s_lo));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

integer etu = 372;
logic io;
integer t_now = 0, t_lead = 0;
task automatic clk1(input logic lo);
  @(negedge clk); sc_clk = 0; io_m_lo = lo;
  @(negedge clk);
  sc_clk = 1; io = !(lo || io_s_lo); t_now = t_now + 1;
  @(negedge clk);
endtask
task automatic idle(input integer n); repeat (n) clk1(0); endtask
logic err;
task automatic tx_char(input logic [7:0] b, input logic badpar = 0);
  logic [9:0] f;
  integer k;
  f = {(^b) ^ badpar, b, 1'b0};
  err = 0;
  for (int c = 0; c < 12 * etu; c++) begin
    k = c / etu;
    clk1(k <= 9 ? !f[k] : 1'b0);
    if (c == 11 * etu - etu / 4 && !io) err = 1;
  end
endtask
logic [7:0] rb;
logic rok;
integer rwait;
task automatic rx_char(input logic sig_err = 0, input integer tmo = 40);
  logic [9:0] s;
  integer c;
  rok = 0; rb = 0; s = 0; c = 0;
  do begin clk1(0); c = c + 1; end while (io && c < tmo * etu);
  rwait = c;
  t_lead = t_now;
  if (io) return;
  for (c = 1; c < 10 * etu; c++) begin clk1(0); if (c % etu == etu / 2) s[c / etu] = io; end
  rb = s[8:1];
  rok = !s[0] && (^s[9:1]) == 1'b0;
  if (sig_err) begin
    for (; c < 21 * etu / 2; c++) clk1(0);
    for (; c < 23 * etu / 2; c++) clk1(1);
  end
endtask
logic [7:0] r [0:263];
integer nr;
// receive up to n characters, stop at the first missing one
task automatic rx_n(input integer n);
  nr = 0;
  for (int i = 0; i < n; i++) begin rx_char(); if (!rok) return; r[i] = rb; nr = nr + 1; end
endtask
task automatic header(input logic [7:0] c, input logic [7:0] i, input logic [7:0] p1, input logic [7:0] p2,
                      input logic [7:0] p3);
  tx_char(c); tx_char(i); tx_char(p1); tx_char(p2); tx_char(p3);
endtask
function automatic logic [7:0] ib(input integer i); ib = i ^ 8'h5C; endfunction
logic ok;
integer t0, gapc;

initial begin
  repeat (3) @(posedge clk);
  chk(io_s_lo === 1'b0, "card off I/O in reset");
  rst_n = 1;
  // powered with RST high and never reset: no ATR, no answer to a header
  idle(500);
  header(8'h00, 8'hB0, 8'h00, 8'h00, 8'h01);
  rx_char(0, 30); chk(!rok && rwait >= 30 * etu, "no RST yet: the card stays off");
  sc_rst_n = 0;
  idle(50);
  chk(io_s_lo === 1'b0, "RST low: the card stays silent");
  sc_rst_n = 1; t0 = t_now;
  rx_n(4);
  chk(nr == 4 && r[0] == 8'h3B && r[1] == 8'h02 && r[2] == 8'h53 && r[3] == 8'h43, "ATR 3B 02 53 43");
  // the first ATR character's leading edge: ATR_DLY clocks after RST
  sc_rst_n = 0; idle(10); sc_rst_n = 1; t0 = t_now;
  rx_char(); chk(rok && rb == 8'h3B && t_lead - t0 == 401, "ATR starts 400 clocks after RST");
  rx_char(); t0 = t_lead; rx_char(); chk(rok && t_lead - t0 == 12 * etu, "ATR characters 12 etu apart");
  rx_char(); idle(20 * etu);
  // PPS 14 (372 / 8): not supported, no answer
  tx_char(8'hFF); tx_char(8'h10); tx_char(8'h14); tx_char(8'hFF ^ 8'h10 ^ 8'h14);
  rx_char(0, 30); chk(!rok && rwait >= 30 * etu, "PPS 372 / 8: no answer");
  // bad PCK
  tx_char(8'hFF); tx_char(8'h10); tx_char(8'h94); tx_char(8'h00);
  rx_char(0, 30); chk(!rok, "PPS with a bad PCK: no answer");
  // PPS 94: 512 / 8
  tx_char(8'hFF); t0 = t_now; tx_char(8'h10); tx_char(8'h94); tx_char(8'hFF ^ 8'h10 ^ 8'h94); gapc = t_now;
  rx_n(4);
  chk(nr == 4 && r[0] == 8'hFF && r[1] == 8'h10 && r[2] == 8'h94 && r[3] == (8'hFF ^ 8'h10 ^ 8'h94), "PPS 94 echoed");
  etu = 64; idle(20 * etu);
  // right after an accepted PPS, FF is a class byte
  tx_char(8'hFF); tx_char(8'h10); tx_char(8'h11); tx_char(8'hFE); tx_char(8'h00);
  rx_n(2); chk(nr == 2 && r[0] == 8'h6E && r[1] == 8'h00, "after a PPS no second PPS: 6E 00");
  idle(20 * etu);
  // READ BINARY 4 bytes at 0x20
  header(8'h00, 8'hB0, 8'h00, 8'h20, 8'h04); t0 = t_now;
  rx_n(7);
  chk(nr == 7 && r[0] == 8'hB0 && r[1] == ib(32) && r[2] == ib(33) && r[3] == ib(34) && r[4] == ib(35) &&
      r[5] == 8'h90 && r[6] == 8'h00, "READ BINARY at the new etu: B0, data, 90 00");
  idle(20 * etu);
  // the 16 etu turnaround: leading edge of the last header byte to the procedure byte
  header(8'h00, 8'hB0, 8'h00, 8'h00, 8'h01); t0 = t_now - 12 * etu;
  rx_char(); chk(rok && t_lead - t0 == 16 * etu + 2, "card answers 16 etu after the last leading edge");
  rx_n(3); idle(20 * etu);
  // a second PPS is a header now: CLA FF -> 6E 00
  tx_char(8'hFF); tx_char(8'h10); tx_char(8'h11); tx_char(8'hFE); tx_char(8'h00);
  rx_n(2); chk(nr == 2 && r[0] == 8'h6E && r[1] == 8'h00, "after the first exchange FF is a class byte: 6E 00");
  idle(20 * etu);
  // UPDATE BINARY 3 bytes at 0x40
  header(8'h00, 8'hD6, 8'h00, 8'h40, 8'h03);
  rx_char(); chk(rok && rb == 8'hD6, "UPDATE BINARY: procedure byte D6");
  idle(16 * etu);
  tx_char(8'hA1); tx_char(8'hB2); tx_char(8'hC3);
  rx_n(2); chk(nr == 2 && r[0] == 8'h90 && r[1] == 8'h00, "UPDATE: 90 00");
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h00, 8'h3F, 8'h05); rx_n(8);
  chk(nr == 8 && r[1] == ib(63) && r[2] == 8'hA1 && r[3] == 8'hB2 && r[4] == 8'hC3 && r[5] == ib(67), "read-back");
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h00, 8'hFC, 8'h05); rx_n(2); chk(nr == 2 && r[0] == 8'h6B && r[1] == 8'h00, "past the end: 6B 00");
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h00, 8'hFC, 8'h04); rx_n(7); chk(nr == 7 && r[4] == ib(255), "up to the last byte");
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h01, 8'h00, 8'h01); rx_n(2); chk(nr == 2 && r[0] == 8'h6B, "P1 = 1: 6B 00");
  idle(20 * etu);
  header(8'h80, 8'hB0, 8'h00, 8'h00, 8'h01); rx_n(2); chk(nr == 2 && r[0] == 8'h6E, "CLA 80: 6E 00");
  idle(20 * etu);
  header(8'h00, 8'hCA, 8'h00, 8'h00, 8'h01); rx_n(2); chk(nr == 2 && r[0] == 8'h6D, "INS CA: 6D 00");
  idle(20 * etu);
  // parity error on P2: the card signals it, the reader repeats
  tx_char(8'h00); tx_char(8'hB0); tx_char(8'h00); tx_char(8'h10, 1); ok = err;
  idle(2 * etu); tx_char(8'h10); ok = ok && !err; tx_char(8'h02);
  rx_n(5); chk(ok && nr == 5 && r[1] == ib(16) && r[2] == ib(17), "bad parity: error signal, the repeat is taken");
  idle(20 * etu);
  // the reader signals an error on the card's first data byte: repeated
  header(8'h00, 8'hB0, 8'h00, 8'h08, 8'h02);
  rx_char(); ok = rok && rb == 8'hB0; rx_char(1);
  rx_char(); chk(ok && rok && rb == ib(8), "a refused character is sent again");
  rx_n(3); chk(nr == 3 && r[0] == ib(9) && r[1] == 8'h90, "and the response goes on");
  idle(20 * etu);
  // refuse all four tries: the card drops the response
  header(8'h00, 8'hB0, 8'h00, 8'h00, 8'h01);
  rx_char(1); rx_char(1); rx_char(1); rx_char(1); ok = rb == 8'hB0;
  rx_char(0, 30); chk(ok && !rok, "after 4 refused tries the card gives up");
  header(8'h00, 8'hB0, 8'h00, 8'h41, 8'h01); rx_n(4); chk(nr == 4 && r[1] == 8'hB2, "and takes the next command");
  idle(20 * etu);
  // 256 bytes (P3 = 0)
  header(8'h00, 8'hB0, 8'h00, 8'h00, 8'h00); rx_n(259);
  ok = nr == 259 && r[257] == 8'h90;
  for (int i = 0; i < 256; i++) if (r[1 + i] !== ((i >= 64 && i < 67) ? (i == 64 ? 8'hA1 : i == 65 ? 8'hB2 : 8'hC3) : ib(i))) ok = 0;
  chk(ok, "P3 = 0 reads all 256 bytes");
  // RST: back to F = 372 / D = 1; the file is kept
  sc_rst_n = 0; idle(20); chk(io_s_lo === 1'b0, "RST: off I/O"); sc_rst_n = 1; etu = 372;
  rx_n(4); chk(nr == 4 && r[0] == 8'h3B, "ATR again at 372");
  idle(20 * etu);
  tx_char(8'hFF); tx_char(8'h10); tx_char(8'h13); tx_char(8'hFF ^ 8'h10 ^ 8'h13);
  rx_n(4); chk(nr == 4 && r[2] == 8'h13, "PPS 13: 372 / 4"); etu = 93;
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h00, 8'h40, 8'h01); rx_n(4); chk(nr == 4 && r[1] == 8'hA1, "data kept across RST, etu 93");
  idle(20 * etu);
  // PPS0 = 00 (no PPS1): accepted, etu unchanged
  sc_rst_n = 0; idle(20); sc_rst_n = 1; etu = 372; rx_n(4); idle(20 * etu);
  tx_char(8'hFF); tx_char(8'h00); tx_char(8'hFF);
  rx_n(3); chk(nr == 3 && r[1] == 8'h00 && r[2] == 8'hFF, "PPS without PPS1 echoed");
  idle(20 * etu);
  header(8'h00, 8'hB0, 8'h00, 8'h00, 8'h01); rx_n(4); chk(nr == 4 && r[1] == ib(0), "still 372");
  // a header with a parity error on CLA; repeat with good parity
  idle(20 * etu);
  tx_char(8'h00, 1); ok = err; idle(2 * etu); tx_char(8'h00); tx_char(8'hB0); tx_char(8'h00); tx_char(8'h01); tx_char(8'h01);
  rx_n(4); chk(ok && nr == 4 && r[1] == ib(1), "parity error on the first byte");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
