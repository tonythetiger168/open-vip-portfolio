# CAN XL (ISO 11898-1:2024 / CiA 610-1) frame agent, bit level, one bit per
# clock (the arbitration / data bit-rate switch is not modelled).
#
# Frame as built by the agent and decoded by the monitor and the DUT model:
#   arbitration phase, dynamic stuffing (a complement bit after five equal
#   bits): SOF(0) ID[10:0] RRS(0) IDE(0) FDF(1) XLF(1) resXL(0)
#   ADS, reduced to ADH(1) ADL(0)
#   data phase, fixed stuffing (a complement bit before every eleventh bit):
#   SDT[7:0] SEC DLC[10:0] SBC[3:0] PCRC[12:0] VCID[7:0] AF[31:0]
#   DATA (DLC + 1 bytes, MSB first) FCRC[31:0]
#   FCP "1100", ACK slot, ACK delimiter, EOF (7 recessive)
# SBC = 3-bit Gray code of (dynamic stuff bits mod 8) + even parity bit.
# PCRC covers SOF .. SBC including the dynamic stuff bits, FCRC covers SOF ..
# DATA including PCRC (cascaded); fixed stuff bits are in neither.
# The CRC polynomials / initial values and the fixed-stuff interval are
# parameters in can_xl_defs_pkg (CANXL_*). The defaults are the author's
# reading of CiA 610-1 material and have not been checked against the ISO
# text: set them from ISO 11898-1:2024 before using the VIP for compliance.
#
# tb/top_tb.sv can_xl_model: a CAN XL receiver node. It decodes rx, drives
# a dominant ACK on tx for a correct frame, signals the first error it finds
# with a six-bit dominant error flag on tx (then waits for 11 recessive bits),
# counts receive errors (+1 per error, -1 per good frame), and reports a good
# frame whose VCID passes its filter (vcid_flt, 0 = all) on rx_ok with the
# frame's fields and the sum of its data bytes.

CRC = """
// serial CRCs, MSB first: c = (c << 1) ^ poly when (bit ^ c[msb])
localparam bit [12:0] CANXL_PCRC_POLY = 13'h1CC5;
localparam bit [12:0] CANXL_PCRC_INIT = 13'h1FFF;
localparam bit [31:0] CANXL_FCRC_POLY = 32'hF4AC_FB13;
localparam bit [31:0] CANXL_FCRC_INIT = 32'hFFFF_FFFF;
localparam int        CANXL_FSB       = 10;    // data bits between fixed stuff bits

typedef enum bit [2:0] {XL_OK, XL_STUFF_DYN, XL_STUFF_FIX, XL_FORM, XL_SBC, XL_PCRC, XL_FCRC} canxl_err_e;

function automatic bit [12:0] canxl_crc13(bit [12:0] c, bit b);
  bit fb = b ^ c[12];
  c = c << 1;
  return fb ? c ^ CANXL_PCRC_POLY : c;
endfunction

function automatic bit [31:0] canxl_crc32(bit [31:0] c, bit b);
  bit fb = b ^ c[31];
  c = c << 1;
  return fb ? c ^ CANXL_FCRC_POLY : c;
endfunction

function automatic bit [3:0] canxl_sbc(int unsigned nsb);
  bit [2:0] b = nsb % 8;
  bit [2:0] g = b ^ (b >> 1);
  return {g, ^g};
endfunction
"""

SPEC = dict(
    vip="CAN_XL-UVM-VIP", p="can_xl", P="CAN XL", dir="can_xl", family="Automotive",
    desc="CAN XL (ISO 11898-1:2024, CiA 610-1) VIP at bit level: dynamic and fixed bit stuffing, SDT / SEC / "
         "VCID / AF fields, 1 to 2048 data bytes, SBC, cascaded PCRC / FCRC, FCP, ACK and error flags, "
         "with error injection and an independent decoder.",
    about="""
CAN XL is the third CAN generation (up to 2048 data bytes, 10+ Mbit/s data phase)
aimed at zonal vehicle networks next to 10BASE-T1S. The agent builds frames bit
by bit and injects one error per frame (a dynamic or fixed stuff violation, a bad
SBC, PCRC, FCRC or FCP); the monitor decodes the line with its own de-stuffer and
CRCs and reports the first error it sees; the scoreboard predicts the receiver's
ACK, error flag, error code, receive error counter, VCID filtering and reported
fields.

The frame is simplified where the public material was not enough to be exact:
ADS / DAS are reduced to ADH ADL, and the CRC polynomials, initial values and
fixed-stuff interval are parameters (`CANXL_*` in `can_xl_defs.sv`) whose
defaults are not taken from the ISO text. Check them against ISO 11898-1:2024
before using this VIP for compliance work.""",
    defs=CRC,
    timeout=100,
    ports=[
        ("in", "logic", "rx"), ("in", "logic [7:0]", "vcid_flt"),
        ("out", "logic", "tx"), ("out", "logic", "rx_ok"), ("out", "logic", "rx_err"),
        ("out", "logic [2:0]", "err_code"), ("out", "logic [7:0]", "rec"),
        ("out", "logic [10:0]", "out_id"), ("out", "logic [7:0]", "out_sdt"), ("out", "logic [7:0]", "out_vcid"),
        ("out", "logic [31:0]", "out_af"), ("out", "logic [10:0]", "out_dlc"), ("out", "logic [31:0]", "out_sum"),
    ],
    cfg="""int unsigned idle_bits = 11;    // recessive bits before each frame
bit [7:0] vcid_flt = 8'h05;       // receiver VCID filter (0 = accept all)""",
    fields=[
        ("bit [10:0]", "id", "req"),
        ("bit [7:0]", "sdt", "req"),
        ("bit", "sec", "req"),
        ("bit [7:0]", "vcid", "req"),
        ("bit [31:0]", "af", "req"),
        ("bit [10:0]", "dlc", "req"),
        ("bit [7:0]", "data", "req", "q"),
        ("canxl_err_e", "err_kind", "req"),
        ("bit", "acked", "rsp"),
        ("bit", "eflag", "rsp"),
        ("bit", "rx_ok", "rsp"),
        ("bit [2:0]", "err_code", "rsp"),
        ("bit [7:0]", "rec", "rsp"),
        ("bit [10:0]", "out_id", "rsp"),
        ("bit [7:0]", "out_sdt", "rsp"),
        ("bit [7:0]", "out_vcid", "rsp"),
        ("bit [31:0]", "out_af", "rsp"),
        ("bit [10:0]", "out_dlc", "rsp"),
        ("bit [31:0]", "out_sum", "rsp"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit", "bits", "info", "q"),            # line bits SOF .. FCP
        ("int unsigned", "ack_pos", "info"),     # index of the ACK slot in the line bits
    ],
    constraints="""
constraint c_len  { dlc inside {[0:63]}; }
constraint c_vcid { vcid dist { 8'h05 := 3, 8'h00 := 1, [8'h01:8'hFF] :/ 2 }; }
constraint c_err  { err_kind dist { XL_OK := 10, XL_STUFF_DYN := 1, XL_STUFF_FIX := 1, XL_FORM := 1,
                                    XL_SBC := 1, XL_PCRC := 1, XL_FCRC := 1 }; }
""",
    tr_functions="""
function void post_randomize();
  bit [31:0] x = seed | 1;
  data.delete();
  for (int i = 0; i <= dlc; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    data.push_back(x[7:0]);
  end
  build();
endfunction

// line bits for the frame, with err_kind injected
function void build();
  bit a[$], d[$];
  bit last = 1, s;
  int run = 0, nsb = 0, fcnt = 0;
  bit dyn_done = 0, fix_done = 0;
  bit [12:0] pc = CANXL_PCRC_INIT;
  bit [31:0] fc = CANXL_FCRC_INIT;
  bit [12:0] pcrc;
  bit [31:0] fcrc;
  if (err_kind == XL_STUFF_DYN) id[10:7] = 4'h0;     // SOF + four zeros force a stuff bit
  bits.delete();
  // arbitration phase
  a.push_back(1'b0);
  for (int i = 10; i >= 0; i--) a.push_back(id[i]);
  a.push_back(1'b0); a.push_back(1'b0); a.push_back(1'b1); a.push_back(1'b1); a.push_back(1'b0);
  for (int i = 0; i <= a.size(); i++) begin
    if (run == 5) begin                          // dynamic stuff bit
      s = !last;
      if (err_kind == XL_STUFF_DYN && !dyn_done) begin s = last; dyn_done = 1; end
      bits.push_back(s); pc = canxl_crc13(pc, s); fc = canxl_crc32(fc, s);
      nsb++; last = s; run = 1;
    end
    if (i == a.size()) break;
    bits.push_back(a[i]); pc = canxl_crc13(pc, a[i]); fc = canxl_crc32(fc, a[i]);
    if (a[i] == last) run++; else begin last = a[i]; run = 1; end
  end
  // ADS
  bits.push_back(1'b1); pc = canxl_crc13(pc, 1'b1); fc = canxl_crc32(fc, 1'b1);
  bits.push_back(1'b0); pc = canxl_crc13(pc, 1'b0); fc = canxl_crc32(fc, 1'b0);
  // data phase fields
  for (int i = 7; i >= 0; i--) d.push_back(sdt[i]);
  d.push_back(sec);
  for (int i = 10; i >= 0; i--) d.push_back(dlc[i]);
  begin
    bit [3:0] sbc = canxl_sbc(nsb);
    for (int i = 3; i >= 0; i--) d.push_back(sbc[i]);
  end
  foreach (d[i]) begin pc = canxl_crc13(pc, d[i]); fc = canxl_crc32(fc, d[i]); end
  pcrc = pc;
  for (int i = 12; i >= 0; i--) begin d.push_back(pcrc[i]); fc = canxl_crc32(fc, pcrc[i]); end
  begin
    int n0 = d.size();
    for (int i = 7; i >= 0; i--) d.push_back(vcid[i]);
    for (int i = 31; i >= 0; i--) d.push_back(af[i]);
    foreach (data[j]) for (int i = 7; i >= 0; i--) d.push_back(data[j][i]);
    for (int i = n0; i < d.size(); i++) fc = canxl_crc32(fc, d[i]);
  end
  fcrc = fc;
  for (int i = 31; i >= 0; i--) d.push_back(fcrc[i]);
  // line errors after the transmitter
  case (err_kind)
    XL_SBC:  d[23] = !d[23];                          // SBC parity
    XL_PCRC: d[36] = !d[36];                          // PCRC LSB
    XL_FCRC: d[d.size() - 1] = !d[d.size() - 1];      // FCRC LSB
    default: ;
  endcase
  // fixed stuffing: a complement bit before every (CANXL_FSB + 1)th bit
  last = 1'b0;                                        // ADL
  foreach (d[i]) begin
    if (fcnt == CANXL_FSB) begin
      s = !last;
      if (err_kind == XL_STUFF_FIX && !fix_done) begin s = last; fix_done = 1; end
      bits.push_back(s); fcnt = 0;
    end
    bits.push_back(d[i]); last = d[i]; fcnt++;
  end
  // FCP
  bits.push_back(1'b1); bits.push_back(1'b1); bits.push_back(1'b0);
  bits.push_back(err_kind == XL_FORM ? 1'b1 : 1'b0);
  ack_pos = bits.size();
endfunction
""",
    drv_rsp=False,
    drv_desc="idle recessive bits, the frame's line bits one per clock, then ACK slot, delimiter and EOF recessive",
    drv_idle="""
vif.drv_cb.rx <= 1'b1;
vif.drv_cb.vcid_flt <= cfg.vcid_flt;
""",
    drv_item="""
@(vif.drv_cb);
repeat (cfg.idle_bits) begin vif.drv_cb.rx <= 1'b1; @(vif.drv_cb); end
foreach (t.bits[i]) begin vif.drv_cb.rx <= t.bits[i]; @(vif.drv_cb); end
repeat (12) begin vif.drv_cb.rx <= 1'b1; @(vif.drv_cb); end     // ACK slot, delimiter, EOF, IFS
""",
    mon_desc="frames from SOF to 11 recessive bits; independent de-stuffer, field decoder and CRC / SBC / FCP checks; DUT ACK, error flag and outputs",
    mon_run="""
bit rxq[$], txq[$];
int unsigned ones = 0;
bit in_frame = 0, okp = 0, errp = 0;
forever begin
  bit rx;
  @(vif.mon_cb);
  rx = vif.mon_cb.rx;
  if (!in_frame) begin
    if (rx == 1'b0 && ones >= 11) begin
      in_frame = 1; rxq.delete(); txq.delete(); okp = 0; errp = 0;
    end
  end
  if (in_frame) begin
    rxq.push_back(rx); txq.push_back(vif.mon_cb.tx);
    if (vif.mon_cb.rx_ok) okp = 1;
    if (vif.mon_cb.rx_err) errp = 1;
    // 11 recessive bits end the frame once the decoded frame (up to its ACK
    // slot) lies before them; a run inside the data phase does not
    if (ones >= 10 && rx) begin
      can_xl_transaction t = can_xl_transaction::type_id::create("t");
      if (decode(t, rxq) && t.ack_pos + 11 <= rxq.size()) begin
      // the DUT's tx answers rx one clock later: tx sampled with rx bit i
      // is the response to bit i - 1, so the ACK appears at ack_pos
      t.eflag = errp;
      t.acked = !txq[t.ack_pos] && !errp;
      t.rx_ok = okp;
      t.err_code = vif.mon_cb.err_code; t.rec = vif.mon_cb.rec;
      t.out_id = vif.mon_cb.out_id; t.out_sdt = vif.mon_cb.out_sdt; t.out_vcid = vif.mon_cb.out_vcid;
      t.out_af = vif.mon_cb.out_af; t.out_dlc = vif.mon_cb.out_dlc; t.out_sum = vif.mon_cb.out_sum;
      for (int i = 0; i < t.ack_pos; i++) t.bits.push_back(rxq[i]);
      publish(t);
      in_frame = 0;
      end
    end
  end
  ones = rx ? ones + 1 : 0;
end
""",
    mon_tasks="""
// independent decoder: de-stuff, rebuild the fields, report the first error
// returns 0 while the frame is incomplete
function bit decode(can_xl_transaction t, bit lb[$]);
  bit f[$];                       // data-phase field bits (fixed stuff removed)
  bit last = 1;
  int run = 0, nsb = 0, i = 0, fcnt = 0, k;
  bit [12:0] pc = CANXL_PCRC_INIT, rpc;
  bit [31:0] fc = CANXL_FCRC_INIT, rfc;
  bit [3:0] sbc;
  bit a[$];
  canxl_err_e e = XL_OK;
  // arbitration phase: 17 bits after de-stuffing (+ a trailing stuff bit)
  if (lb.size() < 40) return 0;
  while (a.size() <= 17 && i < lb.size()) begin
    if (run == 5) begin
      if (lb[i] == last && e == XL_OK) e = XL_STUFF_DYN;
      pc = canxl_crc13(pc, lb[i]); fc = canxl_crc32(fc, lb[i]);
      nsb++; last = lb[i]; run = 1; i++;
      continue;
    end
    if (a.size() == 17) break;
    a.push_back(lb[i]); pc = canxl_crc13(pc, lb[i]); fc = canxl_crc32(fc, lb[i]);
    if (lb[i] == last) run++; else begin last = lb[i]; run = 1; end
    i++;
  end
  for (int j = 0; j < 11; j++) t.id[10 - j] = a[1 + j];
  if ((a[14] != 1 || a[15] != 1 || a[16] != 0) && e == XL_OK) e = XL_FORM;
  // ADS
  if ((lb[i] != 1 || lb[i + 1] != 0) && e == XL_OK) e = XL_FORM;
  pc = canxl_crc13(pc, lb[i]); fc = canxl_crc32(fc, lb[i]);
  pc = canxl_crc13(pc, lb[i + 1]); fc = canxl_crc32(fc, lb[i + 1]);
  last = lb[i + 1]; i += 2;
  // data phase up to the end of DLC, to know the length
  k = 77 + 8 * 64 + 32;                       // upper bound until DLC is known
  while (f.size() < k && i < lb.size()) begin
    if (fcnt == CANXL_FSB) begin
      if (lb[i] == last && e == XL_OK) e = XL_STUFF_FIX;
      fcnt = 0; i++;
      continue;
    end
    f.push_back(lb[i]); last = lb[i]; fcnt++; i++;
    if (f.size() == 20) begin
      for (int j = 0; j < 11; j++) t.dlc[10 - j] = f[9 + j];
      k = 77 + 8 * (t.dlc + 1) + 32;
    end
  end
  if (f.size() < k || i + 4 > lb.size()) return 0;
  for (int j = 0; j < 8; j++) t.sdt[7 - j] = f[j];
  t.sec = f[8];
  for (int j = 0; j < 24; j++) begin pc = canxl_crc13(pc, f[j]); fc = canxl_crc32(fc, f[j]); end
  for (int j = 0; j < 4; j++) sbc[3 - j] = f[20 + j];
  if (sbc != canxl_sbc(nsb) && e == XL_OK) e = XL_SBC;
  for (int j = 0; j < 13; j++) rpc[12 - j] = f[24 + j];
  if (rpc != pc && e == XL_OK) e = XL_PCRC;
  for (int j = 24; j < k - 32; j++) fc = canxl_crc32(fc, f[j]);
  for (int j = 0; j < 8; j++) t.vcid[7 - j] = f[37 + j];
  for (int j = 0; j < 32; j++) t.af[31 - j] = f[45 + j];
  t.data.delete();
  for (int b = 0; b <= t.dlc; b++) begin
    bit [7:0] v;
    for (int j = 0; j < 8; j++) v[7 - j] = f[77 + 8 * b + j];
    t.data.push_back(v);
  end
  for (int j = 0; j < 32; j++) rfc[31 - j] = f[k - 32 + j];
  if (rfc != fc && e == XL_OK) e = XL_FCRC;
  if ({lb[i], lb[i + 1], lb[i + 2], lb[i + 3]} != 4'b1100 && e == XL_OK) e = XL_FORM;
  t.ack_pos = i + 4;
  t.err_kind = e;
  return 1;
endfunction
""",
    sb_members="""bit [7:0] rec = 0;
bit [2:0] last_err = 0;
bit [10:0] l_id = 0; bit [7:0] l_sdt = 0, l_vcid = 0; bit [31:0] l_af = 0; bit [10:0] l_dlc = 0;
bit [31:0] l_sum = 0;""",
    predict="""
bit err = (t.err_kind != XL_OK);
t.acked = !err;
t.eflag = err;
if (err) begin
  last_err = t.err_kind;
  if (rec != 8'hFF) rec++;
end else if (rec != 0) rec--;
t.err_code = last_err;
t.rec = rec;
t.rx_ok = !err && (cfg.vcid_flt == 0 || t.vcid == cfg.vcid_flt);
if (t.rx_ok) begin
  l_id = t.id; l_sdt = t.sdt; l_vcid = t.vcid; l_af = t.af; l_dlc = t.dlc;
  l_sum = 0;
  foreach (t.data[i]) l_sum += t.data[i];
end
t.out_id = l_id; t.out_sdt = l_sdt; t.out_vcid = l_vcid; t.out_af = l_af; t.out_dlc = l_dlc; t.out_sum = l_sum;
""",
    checks="""
if (t.data.size() != t.dlc + 1) fail(t, "data length does not match DLC + 1");
if (t.acked && t.eflag) fail(t, "frame both ACKed and error-flagged");
""",
    coverage="""
cp_err  : coverpoint tr.err_kind;
cp_len  : coverpoint tr.dlc { bins one = {0}; bins short_ = {[1:15]}; bins mid = {[16:63]}; bins long_ = {[64:2047]}; }
cp_flt  : coverpoint tr.rx_ok;
cp_sec  : coverpoint tr.sec;
x_err_len : cross cp_err, cp_len { ignore_bins big = binsof(cp_len.long_); }
""",
    directed="""
// one good frame of every length class, the longest frame, and every error kind
t = item(); t.id = 11'h123; t.sdt = 8'h03; t.vcid = 8'h05; t.af = 32'hCAFE_0001; t.dlc = 0; t.seed = 1;
t.post_randomize(); send(t);
t = item(); t.id = 11'h7FF; t.sdt = 8'h05; t.sec = 1; t.vcid = 8'h05; t.af = 32'hFFFF_FFFF; t.dlc = 63; t.seed = 2;
t.post_randomize(); send(t);
t = item(); t.id = 11'h000; t.sdt = 8'h00; t.vcid = 8'h00; t.af = 32'h0; t.dlc = 7; t.seed = 3;
t.post_randomize(); send(t);
t = item(); t.id = 11'h2AA; t.sdt = 8'h07; t.vcid = 8'h09; t.af = 32'h1234_5678; t.dlc = 15; t.seed = 4;
t.post_randomize(); send(t);                  // filtered: ACKed, not reported
t = item(); t.id = 11'h055; t.sdt = 8'h01; t.vcid = 8'h05; t.af = 32'hA5A5_5A5A; t.dlc = 2047; t.seed = 5;
t.post_randomize(); send(t);                  // 2048 data bytes
for (int k = 1; k < 7; k++) begin
  t = item(); t.id = 11'h100 + k; t.sdt = k; t.vcid = 8'h05; t.af = k; t.dlc = 3 + k; t.seed = 10 + k;
  t.err_kind = canxl_err_e'(k);
  t.post_randomize(); send(t);
end
// recovery: good frames bring the receive error counter back down
repeat (3) begin
  t = item(); t.id = 11'h321; t.vcid = 8'h05; t.dlc = 1; t.seed = 99; t.post_randomize(); send(t);
end
""",
    drain_ns=1000,
    model="""
module can_xl_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        rx,
  input  logic [7:0]  vcid_flt,
  output logic        tx,
  output logic        rx_ok,
  output logic        rx_err,
  output logic [2:0]  err_code,
  output logic [7:0]  rec,
  output logic [10:0] out_id,
  output logic [7:0]  out_sdt,
  output logic [7:0]  out_vcid,
  output logic [31:0] out_af,
  output logic [10:0] out_dlc,
  output logic [31:0] out_sum
);
  localparam logic [12:0] P_POLY = 13'h1CC5, P_INIT = 13'h1FFF;
  localparam logic [31:0] F_POLY = 32'hF4ACFB13, F_INIT = 32'hFFFFFFFF;
  localparam int FSB = 10;

  typedef enum logic [2:0] {IDLE, ARB, ADS, DATA, FCP, ACK, EOFR, ERRW} st_t;
  st_t st;
  logic        last;
  logic [3:0]  run, fcnt;
  logic [3:0]  ones;            // recessive run (saturates at 11)
  logic [2:0]  nsb;
  logic [4:0]  apos;            // arbitration bits taken
  logic [15:0] k;               // data-phase field bits taken
  logic [1:0]  spos;            // ADS / FCP bit
  logic [12:0] pc, rpc;
  logic [31:0] fc, rfc;
  logic [3:0]  sbc;
  logic [10:0] id, dlc;
  logic [7:0]  sdt, vcid, cur;
  logic [31:0] af, sum;
  logic [2:0]  eflag;           // error-flag bits still to send
  logic [3:0]  eofc;

  function automatic logic [12:0] f_pc(input logic [12:0] c, input logic b);
    f_pc = (b ^ c[12]) ? ((c << 1) ^ P_POLY) : (c << 1);
  endfunction
  function automatic logic [31:0] f_fc(input logic [31:0] c, input logic b);
    f_fc = (b ^ c[31]) ? ((c << 1) ^ F_POLY) : (c << 1);
  endfunction
  function automatic logic [3:0] f_sbc(input logic [2:0] n);
    logic [2:0] g;
    g = n ^ (n >> 1);
    f_sbc = {g, ^g};
  endfunction

  wire [15:0] dend = 16'd77 + (({5'b0, dlc} + 16'd1) << 3);   // first FCRC bit (DLC 2047: 2048 bytes)

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= IDLE; last <= 1'b1; run <= '0; fcnt <= '0; ones <= '0; nsb <= '0; apos <= '0; k <= '0;
      spos <= '0; pc <= P_INIT; fc <= F_INIT; rpc <= '0; rfc <= '0; sbc <= '0; id <= '0; dlc <= '0;
      sdt <= '0; vcid <= '0; cur <= '0; af <= '0; sum <= '0; eflag <= '0; eofc <= '0;
      tx <= 1'b1; rx_ok <= 1'b0; rx_err <= 1'b0; err_code <= '0; rec <= '0;
      out_id <= '0; out_sdt <= '0; out_vcid <= '0; out_af <= '0; out_dlc <= '0; out_sum <= '0;
    end else begin : step
      logic       fe;               // error found on this bit
      logic [2:0] ec;
      fe = 1'b0; ec = 3'd0;
      rx_ok <= 1'b0; rx_err <= 1'b0;
      ones <= rx ? ((ones == 4'd11) ? ones : ones + 4'd1) : 4'd0;
      // error flag: six dominant bits
      if (eflag != 0) begin tx <= 1'b0; eflag <= eflag - 3'd1; end
      else tx <= 1'b1;
      case (st)
        IDLE:
          if (!rx && ones == 4'd11) begin            // SOF
            st <= ARB; last <= 1'b0; run <= 4'd1; nsb <= '0; apos <= 5'd1;
            pc <= f_pc(P_INIT, 1'b0); fc <= f_fc(F_INIT, 1'b0);
          end
        ARB: begin
          pc <= f_pc(pc, rx); fc <= f_fc(fc, rx);
          if (run == 4'd5) begin                     // dynamic stuff bit
            if (rx == last) begin fe = 1'b1; ec = 3'd1; end
            nsb <= nsb + 3'd1; last <= rx; run <= 4'd1;
            if (apos == 5'd17) begin st <= ADS; spos <= '0; end
          end else if (apos == 5'd17) begin          // ADH (no stuff bit pending)
            if (!rx) begin fe = 1'b1; ec = 3'd3; end
            st <= ADS; spos <= 2'd1;
          end else begin
            if (apos >= 5'd1 && apos <= 5'd11) id <= {id[9:0], rx};
            if ((apos == 5'd14 && !rx) || (apos == 5'd15 && !rx) || (apos == 5'd16 && rx)) begin fe = 1'b1; ec = 3'd3; end
            run <= (rx == last) ? run + 4'd1 : 4'd1;
            last <= rx; apos <= apos + 5'd1;
          end
        end
        ADS: begin
          pc <= f_pc(pc, rx); fc <= f_fc(fc, rx);
          if (spos == 2'd0) begin
            if (!rx) begin fe = 1'b1; ec = 3'd3; end
            spos <= 2'd1;
          end else begin
            if (rx) begin fe = 1'b1; ec = 3'd3; end
            st <= DATA; k <= '0; fcnt <= '0; last <= rx; sum <= '0;
          end
        end
        DATA: begin
          if (fcnt == FSB[3:0]) begin                // fixed stuff bit
            if (rx == last) begin fe = 1'b1; ec = 3'd2; end
            fcnt <= '0;
          end else begin
            fcnt <= fcnt + 4'd1; last <= rx; k <= k + 16'd1;
            if (k < 16'd24) pc <= f_pc(pc, rx);
            if (k < dend) fc <= f_fc(fc, rx);
            if (k < 16'd8) sdt <= {sdt[6:0], rx};
            else if (k >= 16'd9 && k < 16'd20) dlc <= {dlc[9:0], rx};
            else if (k >= 16'd20 && k < 16'd24) begin
              sbc <= {sbc[2:0], rx};
              if (k == 16'd23 && {sbc[2:0], rx} != f_sbc(nsb)) begin fe = 1'b1; ec = 3'd4; end
            end else if (k >= 16'd24 && k < 16'd37) begin
              rpc <= {rpc[11:0], rx};
              if (k == 16'd36 && {rpc[11:0], rx} != pc) begin fe = 1'b1; ec = 3'd5; end
            end else if (k >= 16'd37 && k < 16'd45) vcid <= {vcid[6:0], rx};
            else if (k >= 16'd45 && k < 16'd77) af <= {af[30:0], rx};
            else if (k < dend) begin
              cur <= {cur[6:0], rx};
              if (k[2:0] == 3'd4) sum <= sum + {24'h0, cur[6:0], rx};   // (k - 77) % 8 == 7
            end else begin
              rfc <= {rfc[30:0], rx};
              if (k == dend + 16'd31) begin
                if ({rfc[30:0], rx} != fc) begin fe = 1'b1; ec = 3'd6; end
                st <= FCP; spos <= '0;
              end
            end
          end
        end
        FCP: begin
          if (rx != ((spos < 2'd2) ? 1'b1 : 1'b0)) begin fe = 1'b1; ec = 3'd3; end
          spos <= spos + 2'd1;
          if (spos == 2'd3) begin
            st <= ACK;
            if (!fe) tx <= 1'b0;                     // dominant ACK in the slot
          end
        end
        ACK: begin st <= EOFR; eofc <= '0; end      // ACK slot
        EOFR: begin                                  // ACK delimiter + EOF
          eofc <= eofc + 4'd1;
          if (eofc == 4'd7) begin
            st <= IDLE;
            if (rec != 0) rec <= rec - 8'd1;
            if (vcid_flt == 0 || vcid == vcid_flt) begin
              rx_ok <= 1'b1;
              out_id <= id; out_sdt <= sdt; out_vcid <= vcid; out_af <= af; out_dlc <= dlc; out_sum <= sum;
            end
          end
        end
        default: if (ones == 4'd11) st <= IDLE;      // ERRW: wait for bus idle
      endcase
      if (fe) begin
        st <= ERRW; eflag <= 3'd6; err_code <= ec; rx_err <= 1'b1;
        if (rec != 8'hFF) rec <= rec + 8'd1;
      end
    end
  end
endmodule
""",
    sva="""
// outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({tx, rx_ok, rx_err, err_code, rec}))
  else $error("CAN XL: X on outputs");
// recessive in reset
assert property (@(posedge clk) disable iff (1'b0) !rst_n |=> tx)
  else $error("CAN XL: tx not recessive in reset");
// an error flag is six dominant bits after rx_err
assert property (@(posedge clk) disable iff (!rst_n) rx_err |=> !tx [*6] ##1 tx)
  else $error("CAN XL: error flag is not six dominant bits");
// the ACK is a single dominant bit
assert property (@(posedge clk) disable iff (!rst_n) !tx && $past(tx) && !$past(rx_err) |=> tx)
  else $error("CAN XL: ACK longer than one bit");
// a good frame and an error are never reported together
assert property (@(posedge clk) disable iff (!rst_n) !(rx_ok && rx_err))
  else $error("CAN XL: rx_ok and rx_err together");
cover property (@(posedge clk) disable iff (!rst_n) rx_ok);
cover property (@(posedge clk) disable iff (!rst_n) rx_err && err_code == 3'd6);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic rx = 1'b1;
logic [7:0] vcid_flt = 8'h00;
wire tx, rx_ok, rx_err;
wire [2:0] err_code;
wire [7:0] rec, out_sdt, out_vcid;
wire [10:0] out_id, out_dlc;
wire [31:0] out_af, out_sum;

always #5 clk = ~clk;

can_xl_model u_dut (.clk(clk), .rst_n(rst_n), .rx(rx), .vcid_flt(vcid_flt), .tx(tx), .rx_ok(rx_ok),
                    .rx_err(rx_err), .err_code(err_code), .rec(rec), .out_id(out_id), .out_sdt(out_sdt),
                    .out_vcid(out_vcid), .out_af(out_af), .out_dlc(out_dlc), .out_sum(out_sum));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [12:0] f_pc(input logic [12:0] c, input logic b);
  f_pc = (b ^ c[12]) ? ((c << 1) ^ 13'h1CC5) : (c << 1);
endfunction
function automatic logic [31:0] f_fc(input logic [31:0] c, input logic b);
  f_fc = (b ^ c[31]) ? ((c << 1) ^ 32'hF4ACFB13) : (c << 1);
endfunction

// build and send one frame (two data bytes); flip = data-phase field bit to invert (-1 none)
logic lb [0:511];
int nl;
logic saw_ack, saw_ok, saw_err;
int lflip = -1;                 // raw (stuffed) bit index to invert before sending, -1 none
int ntxlow, t_ack, t_ok, cyc;
task automatic send(input logic [10:0] id, input logic [7:0] vc, input logic [7:0] d0, input logic [7:0] d1,
                    input int flip);
  logic a [0:16];
  logic d [0:200];
  int nd, run, nsb, fcnt;
  logic last;
  logic [12:0] pc; logic [31:0] fc;
  logic [2:0] g;
  pc = 13'h1FFF; fc = 32'hFFFFFFFF; nl = 0; run = 0; nsb = 0; last = 1;
  a[0] = 0; for (int i = 0; i < 11; i++) a[1 + i] = id[10 - i];
  a[12] = 0; a[13] = 0; a[14] = 1; a[15] = 1; a[16] = 0;
  for (int i = 0; i <= 17; i++) begin
    if (run == 5) begin lb[nl] = !last; pc = f_pc(pc, !last); fc = f_fc(fc, !last); nl++; nsb++; last = !last; run = 1; end
    if (i == 17) break;
    lb[nl] = a[i]; nl++; pc = f_pc(pc, a[i]); fc = f_fc(fc, a[i]);
    if (a[i] == last) run++; else begin last = a[i]; run = 1; end
  end
  lb[nl] = 1; nl++; pc = f_pc(pc, 1); fc = f_fc(fc, 1);
  lb[nl] = 0; nl++; pc = f_pc(pc, 0); fc = f_fc(fc, 0);
  nd = 0;
  for (int i = 7; i >= 0; i--) begin d[nd] = (8'h03 >> i) & 1; nd++; end       // SDT 0x03
  d[nd] = 0; nd++;                                                            // SEC
  for (int i = 10; i >= 0; i--) begin d[nd] = (11'd1 >> i) & 1; nd++; end      // DLC 1 = 2 bytes
  g = nsb[2:0] ^ (nsb[2:0] >> 1);
  d[nd] = g[2]; d[nd + 1] = g[1]; d[nd + 2] = g[0]; d[nd + 3] = ^g; nd += 4;
  for (int i = 0; i < nd; i++) begin pc = f_pc(pc, d[i]); fc = f_fc(fc, d[i]); end
  for (int i = 12; i >= 0; i--) begin d[nd] = pc[i]; fc = f_fc(fc, pc[i]); nd++; end
  for (int i = 7; i >= 0; i--) begin d[nd] = vc[i]; fc = f_fc(fc, vc[i]); nd++; end
  for (int i = 31; i >= 0; i--) begin d[nd] = (32'h0BAD_F00D >> i) & 1; fc = f_fc(fc, d[nd]); nd++; end
  for (int i = 7; i >= 0; i--) begin d[nd] = d0[i]; fc = f_fc(fc, d0[i]); nd++; end
  for (int i = 7; i >= 0; i--) begin d[nd] = d1[i]; fc = f_fc(fc, d1[i]); nd++; end
  for (int i = 31; i >= 0; i--) begin d[nd] = fc[i]; nd++; end
  if (flip >= 0) d[flip] = !d[flip];
  last = 0; fcnt = 0;
  for (int i = 0; i < nd; i++) begin
    if (fcnt == 10) begin lb[nl] = !last; nl++; fcnt = 0; end
    lb[nl] = d[i]; nl++; last = d[i]; fcnt++;
  end
  lb[nl] = 1; lb[nl + 1] = 1; lb[nl + 2] = 0; lb[nl + 3] = 0; nl += 4;
  if (lflip >= 0) lb[lflip] = !lb[lflip];
  saw_ack = 0; saw_ok = 0; saw_err = 0; ntxlow = 0; t_ack = -1; t_ok = -1; cyc = 0;
  begin
    int bad = 0;
    repeat (12) begin @(negedge clk); rx = 1; if (tx !== 1'b1) bad++; end
    chk(bad == 0, "tx recessive while idle");
  end
  for (int i = 0; i < nl; i++) begin
    @(negedge clk); rx = lb[i]; cyc++;
    if (rx_err) saw_err = 1;
    if (!tx) ntxlow++;
  end
  repeat (14) begin
    @(negedge clk); rx = 1; cyc++;
    if (!tx && !saw_err) begin saw_ack = 1; if (t_ack < 0) t_ack = cyc; end
    if (!tx) ntxlow++;
    if (rx_ok) begin saw_ok = 1; if (t_ok < 0) t_ok = cyc; end
    if (rx_err) saw_err = 1;
  end
endtask

initial begin
  repeat (3) @(posedge clk);
  chk(tx === 1'b1, "tx recessive in reset");
  rst_n = 1;

  send(11'h123, 8'h05, 8'h11, 8'h22, -1);
  chk(saw_ack && saw_ok && !saw_err, "good frame ACKed and reported");
  chk(out_id === 11'h123 && out_vcid === 8'h05 && out_af === 32'h0BAD_F00D && out_dlc === 11'd1, "fields reported");
  chk(out_sum === 32'h33 && out_sdt === 8'h03, "data sum and SDT reported");
  chk(ntxlow == 1, "a good frame drives exactly one dominant bit (ACK)");
  chk(t_ok - t_ack == 9, $sformatf("frame reported after ACK delimiter and 7-bit EOF (%0d)", t_ok - t_ack));
  send(11'h0F0, 8'h07, 8'hAA, 8'h55, 50);       // flip an AF bit: only the FCRC covers it
  chk(!saw_ack && saw_err && err_code === 3'd6, "FCRC error flagged, no ACK");
  chk(ntxlow == 6, $sformatf("six-bit error flag (%0d dominant bits)", ntxlow));
  chk(rec === 8'd1, "receive error counter +1");
  send(11'h0F0, 8'h07, 8'hAA, 8'h55, 30);       // flip a PCRC bit
  chk(saw_err && err_code === 3'd5 && rec === 8'd2, "PCRC error flagged");
  send(11'h123, 8'h06, 8'h01, 8'h02, -1);
  chk(saw_ack && !saw_err && rec === 8'd1, "good frame after errors, counter -1");
  chk(out_vcid === 8'h06, "VCID field boundary (PCRC ends at bit 37)");
  send(11'h123, 8'h06, 8'h01, 8'h02, 21);       // flip the SBC parity bit
  chk(saw_err && err_code === 3'd4, "SBC error flagged");
  // arbitration-phase errors (ID 0x123 has no stuff bits before ADH: raw index = field bit)
  begin : arb
    int r0;
    for (int b = 14; b <= 17; b++) begin
      r0 = rec;
      lflip = b; send(11'h123, 8'h06, 8'h01, 8'h02, -1); lflip = -1;
      chk(saw_err && !saw_ok && err_code === 3'd3 && rec == r0 + 1,
          $sformatf("form error on %s", b == 14 ? "FDF" : b == 15 ? "XLF" : b == 16 ? "resXL" : "ADH"));
    end
    lflip = 5; send(11'h000, 8'h06, 8'h01, 8'h02, -1); lflip = -1;   // the stuff bit after SOF + 4 zeros
    chk(saw_err && err_code === 3'd1, "dynamic stuff error in arbitration");
    repeat (8) begin send(11'h123, 8'h06, 8'h01, 8'h02, -1); end
  end
  vcid_flt = 8'h05;
  send(11'h124, 8'h06, 8'h01, 8'h02, -1);
  chk(saw_ack && !saw_ok, "VCID filtered: ACKed, not reported");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #500000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
