# CAN FD (ISO 11898-1:2015) receiver agent at bit level, with the two bit
# rates of CAN FD: nominal bits last cfg.nbt clocks and, when BRS is set, the
# bits after BRS up to the last CRC bit last cfg.dbt clocks.
#
# Frames, as built by the agent and decoded by the monitor and the DUT model:
#   base:     SOF ID[10:0] RTR/RRS IDE(0) FDF
#   extended: SOF ID[28:18] SRR(1) IDE(1) ID[17:0] RTR/RRS FDF [r0 if classical]
#   FD:       ... FDF(1) res(0) BRS ESI DLC[3:0] DATA(0..64 bytes)
#             FSB SC[3:0] FSB CRC ... (a fixed stuff bit before every 4 bits)
#   classical: ... FDF(0) DLC[3:0] DATA(0..8 bytes, none for RTR) CRC15
#   then CRC delimiter (1), ACK slot, ACK delimiter (1), EOF (7 recessive).
# Dynamic stuffing (a complement bit after five equal bits) runs from SOF to
# the end of the data field in FD frames and to the end of CRC15 in classical
# frames. In FD frames the first fixed stuff bit takes the place of a dynamic
# stuff bit due after the last data bit.
# SC = 3-bit Gray code of (dynamic stuff bits mod 8) + even parity bit.
# CRC17 (frames up to 16 data bytes) and CRC21 (longer frames) cover SOF ..
# DATA including the dynamic stuff bits, then the SC bits; fixed stuff bits
# are not covered. CRC15 covers the de-stuffed SOF .. DATA of classical frames.
# The polynomials and initial values are in can_fd_defs_pkg (CANFD_*); they
# are the values published for ISO 11898-1:2015 and should be checked against
# the ISO text before the VIP is used for compliance work.
#
# Simplifications: the bit rate switches at the bit boundary after BRS and
# before the CRC delimiter (ISO switches at the sample points of those bits);
# the receiver hard-synchronises on SOF and does not resynchronise, so the
# driver must keep an exact bit time.
#
# tb/top_tb.sv can_fd_model: a CAN FD receiver node. It ACKs a correct frame,
# signals the first error with a six-bit dominant error flag (a CRC or stuff
# count error after the ACK delimiter, other errors on the next bit) and then
# waits for 11 recessive bits before it accepts a new SOF, counts
# receive errors (+1 per error; -1 per good frame, or back to 127 when error
# passive), enters protocol exception on a recessive res bit when pex_en is
# set, and reports a good frame whose ID passes the acceptance filter on rx_ok
# with its fields and the sum of its data bytes.

CRC = """
// serial CRCs, MSB first: c = (c << 1) ^ poly when (bit ^ c[msb])
localparam bit [14:0] CANFD_CRC15_POLY = 15'h4599;
localparam bit [16:0] CANFD_CRC17_POLY = 17'h1685B;
localparam bit [16:0] CANFD_CRC17_INIT = 17'h10000;
localparam bit [20:0] CANFD_CRC21_POLY = 21'h102899;
localparam bit [20:0] CANFD_CRC21_INIT = 21'h100000;

// injected error (FD_SC / FD_FSB / FD_PEX need an FD frame)
typedef enum bit [2:0] {FD_OK, FD_STUFF, FD_FORM, FD_CRC, FD_SC, FD_FSB, FD_PEX} canfd_err_e;

function automatic bit [14:0] canfd_crc15(bit [14:0] c, bit b);
  bit fb = b ^ c[14];
  c = c << 1;
  return fb ? c ^ CANFD_CRC15_POLY : c;
endfunction

function automatic bit [16:0] canfd_crc17(bit [16:0] c, bit b);
  bit fb = b ^ c[16];
  c = c << 1;
  return fb ? c ^ CANFD_CRC17_POLY : c;
endfunction

function automatic bit [20:0] canfd_crc21(bit [20:0] c, bit b);
  bit fb = b ^ c[20];
  c = c << 1;
  return fb ? c ^ CANFD_CRC21_POLY : c;
endfunction

// stuff count field: Gray code of the dynamic stuff bits mod 8, parity
function automatic bit [3:0] canfd_sc(int unsigned nsb);
  bit [2:0] b = nsb % 8;
  bit [2:0] g = b ^ (b >> 1);
  return {g, ^g};
endfunction

// data bytes for a DLC
function automatic int unsigned canfd_len(bit [3:0] dlc, bit fdf, bit rtr);
  if (!fdf) return rtr ? 0 : ((dlc > 8) ? 8 : dlc);
  case (dlc)
    4'd9:  return 12;
    4'd10: return 16;
    4'd11: return 20;
    4'd12: return 24;
    4'd13: return 32;
    4'd14: return 48;
    4'd15: return 64;
    default: return dlc;
  endcase
endfunction

// error code reported by the receiver for an injected error
function automatic bit [2:0] canfd_code(canfd_err_e e, bit pex_en);
  case (e)
    FD_STUFF:      return 3'd1;
    FD_FORM:       return 3'd2;
    FD_CRC, FD_SC: return 3'd3;
    FD_FSB:        return 3'd4;
    FD_PEX:        return pex_en ? 3'd0 : 3'd2;
    default:       return 3'd0;
  endcase
endfunction
"""

SPEC = dict(
    vip="CAN_FD-UVM-VIP", p="can_fd", P="CAN-FD", dir="can_fd", family="Automotive",
    desc="CAN FD (ISO 11898-1:2015) VIP at bit level: classical and FD frames in base and extended format, "
         "RTR / FDF / BRS / ESI, DLC up to 64 bytes, dynamic and fixed bit stuffing, stuff count, CRC15 / "
         "CRC17 / CRC21, nominal and data bit rates, ACK, error flags, protocol exception, acceptance filter "
         "and error-passive state, with error injection and an independent decoder.",
    about="""
CAN FD adds a second, faster bit rate and up to 64 data bytes to classical CAN.
The agent builds classical and FD frames bit by bit, drives the arbitration
phase at the nominal bit time and the data phase at the data bit time when BRS
is set, and injects one error per frame (a dynamic stuff violation, a dominant
CRC delimiter, a bad CRC, a bad stuff count, a bad fixed stuff bit, or a
recessive res bit). The monitor samples the line with its own bit timing,
de-stuffs it and checks the CRCs independently of the DUT model; the scoreboard
predicts the receiver's ACK, error flag, error code, receive error counter,
error-passive flag, protocol exception and acceptance filter.

The bit-rate switch happens at bit boundaries instead of sample points and the
receiver does not resynchronise; the CRC polynomials and initial values are
parameters (`CANFD_*` in `can_fd_defs.sv`) to check against ISO 11898-1:2015
before compliance work.""",
    defs=CRC,
    timeout=100,
    ports=[
        ("in", "logic", "rx"), ("in", "logic [3:0]", "nbt"), ("in", "logic [3:0]", "dbt"),
        ("in", "logic", "pex_en"), ("in", "logic [28:0]", "acc_id"), ("in", "logic [28:0]", "acc_msk"),
        ("out", "logic", "tx"), ("out", "logic", "rx_ok"), ("out", "logic", "rx_err"), ("out", "logic", "pex"),
        ("out", "logic [2:0]", "err_code"), ("out", "logic [7:0]", "rec"), ("out", "logic", "err_pas"),
        ("out", "logic [28:0]", "out_id"), ("out", "logic", "out_ide"), ("out", "logic", "out_fdf"),
        ("out", "logic", "out_brs"), ("out", "logic", "out_esi"), ("out", "logic", "out_rtr"),
        ("out", "logic [3:0]", "out_dlc"), ("out", "logic [6:0]", "out_len"), ("out", "logic [15:0]", "out_sum"),
    ],
    cfg="""int unsigned idle_bits = 11;    // recessive bits before each frame
bit [3:0] nbt = 4'd4;             // clocks per nominal bit
bit [3:0] dbt = 4'd1;             // clocks per data-phase bit (<= nbt)
bit       pex_en = 1'b1;          // receiver protocol exception enabled
bit [28:0] acc_id  = 29'h0;       // acceptance filter: (id ^ acc_id) & acc_msk == 0
bit [28:0] acc_msk = 29'h1000_0000;""",
    fields=[
        ("bit", "ide", "req"),
        ("bit [28:0]", "id", "req"),
        ("bit", "rtr", "req"),
        ("bit", "fdf", "req"),
        ("bit", "brs", "req"),
        ("bit", "esi", "req"),
        ("bit [3:0]", "dlc", "req"),
        ("bit [7:0]", "data", "req", "q"),
        ("canfd_err_e", "err_kind", "req"),
        ("bit", "acked", "rsp"),
        ("bit", "eflag", "rsp"),
        ("bit", "rx_ok", "rsp"),
        ("bit", "pex", "rsp"),
        ("bit [2:0]", "err_code", "rsp"),
        ("bit [7:0]", "rec", "rsp"),
        ("bit", "err_pas", "rsp"),
        ("bit [28:0]", "out_id", "rsp"),
        ("bit", "out_ide", "rsp"),
        ("bit", "out_fdf", "rsp"),
        ("bit", "out_brs", "rsp"),
        ("bit", "out_esi", "rsp"),
        ("bit", "out_rtr", "rsp"),
        ("bit [3:0]", "out_dlc", "rsp"),
        ("bit [6:0]", "out_len", "rsp"),
        ("bit [15:0]", "out_sum", "rsp"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit", "bits", "info", "q"),            # line bits SOF .. CRC delimiter
        ("bit", "fast", "info", "q"),            # 1: data-phase bit (cfg.dbt clocks)
        ("int unsigned", "ack_clk", "info"),     # monitor: clock index of the ACK slot sample
    ],
    constraints="""
constraint c_fmt { fdf dist { 1 := 3, 0 := 1 };
                   !ide -> id[28:11] == 0;
                   fdf -> rtr == 0;
                   !fdf -> (brs == 0 && esi == 0);
                   brs dist { 1 := 3, 0 := 1 }; }
constraint c_err { err_kind dist { FD_OK := 12, FD_STUFF := 1, FD_FORM := 1, FD_CRC := 1,
                                   FD_SC := 1, FD_FSB := 1, FD_PEX := 1 };
                   (err_kind inside {FD_SC, FD_FSB, FD_PEX}) -> fdf; }
""",
    tr_functions="""
function void post_randomize();
  bit [31:0] x = seed | 1;
  data.delete();
  for (int i = 0; i < canfd_len(dlc, fdf, rtr); i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    data.push_back(x[7:0]);
  end
  build();
endfunction

function void push(bit b, bit f);
  bits.push_back(b);
  fast.push_back(f);
endfunction

// line bits for the frame, with err_kind injected
function void build();
  bit a[$], f[$];
  bit last = 1, s, fst = 0, dyn_done = 0;
  int run = 0, nsb = 0, brs_i = -1, ncrc;
  bit [14:0] c15 = 0;
  bit [16:0] c17 = CANFD_CRC17_INIT;
  bit [20:0] c21 = CANFD_CRC21_INIT, crc;
  bit [3:0] sc;
  if (err_kind == FD_STUFF) begin                   // SOF + four zeros force a stuff bit
    if (ide) id[28:25] = 4'h0; else id[10:7] = 4'h0;
  end
  bits.delete(); fast.delete();
  a.push_back(1'b0);
  if (ide) begin
    for (int i = 28; i >= 18; i--) a.push_back(id[i]);
    a.push_back(1'b1); a.push_back(1'b1);           // SRR, IDE
    for (int i = 17; i >= 0; i--) a.push_back(id[i]);
    a.push_back(fdf ? 1'b0 : rtr);                  // RTR / RRS
    a.push_back(fdf);
    if (!fdf) a.push_back(1'b0);                    // r0
  end else begin
    for (int i = 10; i >= 0; i--) a.push_back(id[i]);
    a.push_back(fdf ? 1'b0 : rtr); a.push_back(1'b0); a.push_back(fdf);
  end
  if (fdf) begin
    a.push_back(err_kind == FD_PEX);                // res
    a.push_back(brs); brs_i = a.size() - 1;
    a.push_back(esi);
  end
  for (int i = 3; i >= 0; i--) a.push_back(dlc[i]);
  foreach (data[j]) for (int i = 7; i >= 0; i--) a.push_back(data[j][i]);
  if (!fdf) begin                                   // CRC15 over the de-stuffed bits
    foreach (a[i]) c15 = canfd_crc15(c15, a[i]);
    if (err_kind == FD_CRC) c15[0] = !c15[0];
    for (int i = 14; i >= 0; i--) a.push_back(c15[i]);
  end
  // dynamic stuffing (FD: no stuff bit after the last data bit, the FSB follows)
  for (int i = 0; i <= a.size(); i++) begin
    if (run == 5 && (i < a.size() || !fdf)) begin
      s = !last;
      if (err_kind == FD_STUFF && !dyn_done) begin s = last; dyn_done = 1; end
      push(s, fst); c17 = canfd_crc17(c17, s); c21 = canfd_crc21(c21, s);
      nsb++; last = s; run = 1;
    end
    if (i == a.size()) break;
    push(a[i], fst); c17 = canfd_crc17(c17, a[i]); c21 = canfd_crc21(c21, a[i]);
    if (a[i] == last) run++; else begin last = a[i]; run = 1; end
    if (i == brs_i && brs) fst = 1;
  end
  if (fdf) begin
    sc = canfd_sc(nsb);
    for (int i = 3; i >= 0; i--) begin f.push_back(sc[i]); c17 = canfd_crc17(c17, sc[i]); c21 = canfd_crc21(c21, sc[i]); end
    ncrc = (data.size() <= 16) ? 17 : 21;
    crc = (ncrc == 17) ? {4'h0, c17} : c21;
    for (int i = ncrc - 1; i >= 0; i--) f.push_back(crc[i]);
    if (err_kind == FD_SC)  f[3] = !f[3];                       // SC parity
    if (err_kind == FD_CRC) f[f.size() - 1] = !f[f.size() - 1];   // CRC LSB
    foreach (f[i]) begin
      if (i % 4 == 0) begin                         // fixed stuff bit
        s = (err_kind == FD_FSB && i == 0) ? last : !last;
        push(s, fst); last = s;
      end
      push(f[i], fst); last = f[i];
    end
  end
  push(err_kind == FD_FORM ? 1'b0 : 1'b1, 1'b0);   // CRC delimiter
endfunction
""",
    drv_rsp=False,
    drv_desc="idle recessive bits, the frame's line bits at the nominal or data bit time, then ACK slot, delimiter and EOF recessive",
    drv_idle="""
vif.drv_cb.rx <= 1'b1;
vif.drv_cb.nbt <= cfg.nbt;
vif.drv_cb.dbt <= cfg.dbt;
vif.drv_cb.pex_en <= cfg.pex_en;
vif.drv_cb.acc_id <= cfg.acc_id;
vif.drv_cb.acc_msk <= cfg.acc_msk;
""",
    drv_item="""
@(vif.drv_cb);
repeat (cfg.idle_bits * cfg.nbt) begin vif.drv_cb.rx <= 1'b1; @(vif.drv_cb); end
foreach (t.bits[i])
  repeat (t.fast[i] ? cfg.dbt : cfg.nbt) begin vif.drv_cb.rx <= t.bits[i]; @(vif.drv_cb); end
repeat (9 * cfg.nbt) begin vif.drv_cb.rx <= 1'b1; @(vif.drv_cb); end   // ACK slot, delimiter, EOF
""",
    mon_desc="frames from SOF to the end of EOF; own bit timing (nominal / data rate), de-stuffer, field decoder and CRC / SC / FSB checks; DUT ACK, error flag and outputs",
    mon_run="""
bit rxq[$], txq[$];
int unsigned ones = 0;
bit in_frame = 0, okp = 0, errp = 0, pexp = 0;
forever begin
  bit rx;
  @(vif.mon_cb);
  rx = vif.mon_cb.rx;
  if (!in_frame && rx == 1'b0 && ones >= 10 * cfg.nbt) begin
    in_frame = 1; rxq.delete(); txq.delete(); okp = 0; errp = 0; pexp = 0;
  end
  if (in_frame) begin
    rxq.push_back(rx); txq.push_back(vif.mon_cb.tx);
    if (vif.mon_cb.rx_ok) okp = 1;
    if (vif.mon_cb.rx_err) errp = 1;
    if (vif.mon_cb.pex) pexp = 1;
    // a frame never holds 8 recessive nominal bits before its ACK slot
    if (rx && ones >= 8 * cfg.nbt) begin
      can_fd_transaction t = can_fd_transaction::type_id::create("t");
      dq = rxq;
      if (decode(t) && t.ack_clk + 8 * cfg.nbt < rxq.size()) begin
        // tx sampled with the ACK slot is the DUT's ACK (or its error flag)
        t.eflag = errp;
        t.acked = !txq[t.ack_clk] && !errp;
        t.rx_ok = okp;
        t.pex = pexp;
        t.err_code = vif.mon_cb.err_code; t.rec = vif.mon_cb.rec; t.err_pas = vif.mon_cb.err_pas;
        t.out_id = vif.mon_cb.out_id; t.out_ide = vif.mon_cb.out_ide; t.out_fdf = vif.mon_cb.out_fdf;
        t.out_brs = vif.mon_cb.out_brs; t.out_esi = vif.mon_cb.out_esi; t.out_rtr = vif.mon_cb.out_rtr;
        t.out_dlc = vif.mon_cb.out_dlc; t.out_len = vif.mon_cb.out_len; t.out_sum = vif.mon_cb.out_sum;
        publish(t);
        in_frame = 0;
      end else if (ones >= 20 * cfg.nbt) begin
        `uvm_error("MON", "CAN FD frame could not be decoded")
        in_frame = 0;
      end
    end
  end
  ones = rx ? ones + 1 : 0;
end
""",
    mon_members="""// independent decoder state over the clock samples of one frame (from SOF)
bit dq[$];
int unsigned dp, dsmp;
bit dfast, dshort, dlast;
int unsigned drun, dnsb;
bit [14:0] d15;
bit [16:0] d17;
bit [20:0] d21;
canfd_err_e de;
""",
    mon_tasks="""

// next line bit, sampled in the middle of its bit time
function bit rb();
  int unsigned L = dfast ? cfg.dbt : cfg.nbt;
  if (dp + L > dq.size()) begin dshort = 1; return 1'b1; end
  dsmp = dp + L / 2;
  dp += L;
  return dq[dsmp];
endfunction

// next de-stuffed bit; crc15 = 0 for the CRC15 field itself
function bit db(bit crc15 = 1);
  bit b;
  if (drun == 5) begin
    b = rb();
    if (b == dlast && de == FD_OK) de = FD_STUFF;
    d17 = canfd_crc17(d17, b); d21 = canfd_crc21(d21, b);
    dnsb++; dlast = b; drun = 1;
  end
  b = rb();
  if (crc15) begin d15 = canfd_crc15(d15, b); d17 = canfd_crc17(d17, b); d21 = canfd_crc21(d21, b); end
  drun = (b == dlast) ? drun + 1 : 1;
  dlast = b;
  return b;
endfunction

// returns 0 while the frame is incomplete
function bit decode(can_fd_transaction t);
  bit b, crc_bad = 0;
  bit [3:0] sc;
  bit [20:0] rc = 0;
  int unsigned n;
  dp = 0; dfast = 0; dshort = 0; dlast = 1; drun = 0; dnsb = 0; de = FD_OK;
  d15 = 0; d17 = CANFD_CRC17_INIT; d21 = CANFD_CRC21_INIT;
  t.id = 0; t.dlc = 0;
  void'(db());                                     // SOF
  for (int i = 0; i < 11; i++) t.id = {t.id[27:0], db()};
  b = db();                                        // RTR (base) / SRR (extended)
  t.ide = db();
  if (t.ide) begin
    for (int i = 0; i < 18; i++) t.id = {t.id[27:0], db()};
    t.rtr = db();
  end else t.rtr = b;
  t.fdf = db();
  t.brs = 0; t.esi = 0;
  if (t.fdf) begin
    t.rtr = 0;                                     // RRS
    if (db() && de == FD_OK) de = FD_PEX;
    t.brs = db();
    if (t.brs) dfast = 1;
    t.esi = db();
  end else if (t.ide) void'(db());                 // r0
  for (int i = 0; i < 4; i++) t.dlc = {t.dlc[2:0], db()};
  n = canfd_len(t.dlc, t.fdf, t.rtr);
  t.data.delete();
  for (int j = 0; j < n; j++) begin
    bit [7:0] v;
    for (int i = 0; i < 8; i++) v = {v[6:0], db()};
    t.data.push_back(v);
  end
  if (dshort) return 0;
  if (t.fdf) begin
    int unsigned ncrc = (n <= 16) ? 17 : 21;
    for (int i = 0; i < 4 + ncrc; i++) begin
      if (i % 4 == 0) begin                        // fixed stuff bit
        b = rb();
        if (b == dlast && de == FD_OK) de = FD_FSB;
        dlast = b;
      end
      b = rb(); dlast = b;
      if (i < 4) begin sc = {sc[2:0], b}; d17 = canfd_crc17(d17, b); d21 = canfd_crc21(d21, b); end
      else rc = {rc[19:0], b};
    end
    if (sc != canfd_sc(dnsb)) crc_bad = 1;
    if (ncrc == 17 ? (rc[16:0] != d17) : (rc != d21)) crc_bad = 1;
    if (crc_bad && de == FD_OK) de = (sc != canfd_sc(dnsb)) ? FD_SC : FD_CRC;
  end else begin
    bit [14:0] c = d15;
    for (int i = 0; i < 15; i++) rc = {rc[19:0], db(0)};
    if (drun == 5) begin                           // stuff bit after the last CRC bit
      b = rb();
      if (b == dlast && de == FD_OK) de = FD_STUFF;
    end
    if (rc[14:0] != c && de == FD_OK) de = FD_CRC;
  end
  dfast = 0;
  b = rb();                                        // CRC delimiter
  if (!b && (de == FD_OK || de == FD_CRC || de == FD_SC)) de = FD_FORM;
  t.ack_clk = dp + cfg.nbt / 2;
  if (dshort) return 0;
  t.err_kind = de;
  return 1;
endfunction
""",
    sb_members="""bit [7:0] rec = 0;
bit [2:0] last_err = 0;
bit [28:0] l_id = 0; bit l_ide = 0, l_fdf = 0, l_brs = 0, l_esi = 0, l_rtr = 0;
bit [3:0] l_dlc = 0; bit [6:0] l_len = 0; bit [15:0] l_sum = 0;""",
    predict="""
bit [2:0] code = canfd_code(t.err_kind, cfg.pex_en);
t.acked = (t.err_kind == FD_OK);
t.eflag = (code != 0);
t.pex = (t.err_kind == FD_PEX) && cfg.pex_en;
if (code != 0) begin
  last_err = code;
  if (rec != 8'hFF) rec++;
end else if (t.err_kind == FD_OK) begin
  if (rec > 127) rec = 127;
  else if (rec != 0) rec--;
end
t.err_code = last_err;
t.rec = rec;
t.err_pas = rec[7];
t.rx_ok = (t.err_kind == FD_OK) && (((t.id ^ cfg.acc_id) & cfg.acc_msk) == 0);
if (t.rx_ok) begin
  l_id = t.id; l_ide = t.ide; l_fdf = t.fdf; l_brs = t.brs; l_esi = t.esi; l_rtr = t.rtr;
  l_dlc = t.dlc; l_len = t.data.size();
  l_sum = 0;
  foreach (t.data[i]) l_sum += t.data[i];
end
t.out_id = l_id; t.out_ide = l_ide; t.out_fdf = l_fdf; t.out_brs = l_brs; t.out_esi = l_esi; t.out_rtr = l_rtr;
t.out_dlc = l_dlc; t.out_len = l_len; t.out_sum = l_sum;
""",
    checks="""
if (t.data.size() != canfd_len(t.dlc, t.fdf, t.rtr)) fail(t, "data length does not match the DLC");
if (t.acked && t.eflag) fail(t, "frame both ACKed and error-flagged");
if (t.pex && t.eflag) fail(t, "protocol exception with an error flag");
if (!t.fdf && (t.brs || t.esi)) fail(t, "BRS / ESI in a classical frame");
""",
    coverage="""
cp_err : coverpoint tr.err_kind;
cp_fdf : coverpoint tr.fdf;
cp_ide : coverpoint tr.ide;
cp_dlc : coverpoint tr.dlc;
cp_brs : coverpoint tr.brs iff (tr.fdf);
cp_esi : coverpoint tr.esi iff (tr.fdf);
cp_rtr : coverpoint tr.rtr iff (!tr.fdf);
cp_ok  : coverpoint tr.rx_ok;
cp_pas : coverpoint tr.err_pas;
x_fmt_dlc : cross cp_fdf, cp_ide, cp_dlc;
cp_err_fd  : coverpoint tr.err_kind iff (tr.fdf);
cp_err_cls : coverpoint tr.err_kind iff (!tr.fdf) { bins k[] = {FD_OK, FD_STUFF, FD_FORM, FD_CRC}; }
""",
    directed="""
// every DLC in classical / FD x base / extended format (BRS and ESI vary in FD)
for (int f = 0; f < 4; f++)
  for (int d = 0; d < 16; d++) begin
    t = item(); t.fdf = f[1]; t.ide = f[0];
    t.id = f[0] ? (29'h0ABC_DE00 + d) : (29'h120 + d);
    t.brs = f[1] & d[0]; t.esi = f[1] & d[1]; t.dlc = d; t.seed = 16 * f + d + 1;
    t.post_randomize(); send(t);
  end
// classical remote frames
t = item(); t.id = 29'h7FF; t.rtr = 1; t.dlc = 8; t.post_randomize(); send(t);
t = item(); t.ide = 1; t.id = 29'h1FFF_FFFF; t.rtr = 1; t.dlc = 3; t.post_randomize(); send(t);
// every error kind in an FD frame, then the classical ones
for (int k = 1; k < 7; k++) begin
  t = item(); t.fdf = 1; t.brs = 1; t.ide = k[0]; t.id = 29'h0123_4567 & (k[0] ? 29'h0FFF_FFFF : 29'h7FF);
  t.dlc = 8 + k; t.seed = 40 + k; t.err_kind = canfd_err_e'(k);
  t.post_randomize(); send(t);
end
for (int k = 1; k < 4; k++) begin
  t = item(); t.id = 29'h3A5; t.dlc = k; t.seed = 50 + k; t.err_kind = canfd_err_e'(k);
  t.post_randomize(); send(t);
end
// acceptance filter miss (ACKed, not reported)
t = item(); t.fdf = 1; t.ide = 1; t.id = 29'h1000_0001; t.dlc = 2; t.seed = 60; t.post_randomize(); send(t);
// error passive: 130 errors, then good frames bring the counter back
for (int k = 0; k < 130; k++) begin
  t = item(); t.id = 29'h055; t.err_kind = FD_STUFF; t.seed = k; t.post_randomize(); send(t);
end
repeat (3) begin
  t = item(); t.fdf = 1; t.brs = 1; t.id = 29'h321; t.dlc = 1; t.seed = 99; t.post_randomize(); send(t);
end
""",
    drain_ns=2000,
    model="""
module can_fd_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        rx,
  input  logic [3:0]  nbt,
  input  logic [3:0]  dbt,
  input  logic        pex_en,
  input  logic [28:0] acc_id,
  input  logic [28:0] acc_msk,
  output logic        tx,
  output logic        rx_ok,
  output logic        rx_err,
  output logic        pex,
  output logic [2:0]  err_code,
  output logic [7:0]  rec,
  output logic        err_pas,
  output logic [28:0] out_id,
  output logic        out_ide,
  output logic        out_fdf,
  output logic        out_brs,
  output logic        out_esi,
  output logic        out_rtr,
  output logic [3:0]  out_dlc,
  output logic [6:0]  out_len,
  output logic [15:0] out_sum
);
  localparam logic [14:0] P15 = 15'h4599;
  localparam logic [16:0] P17 = 17'h1685B, I17 = 17'h10000;
  localparam logic [20:0] P21 = 21'h102899, I21 = 21'h100000;

  // ERRW: after an error or a protocol exception, wait for 11 recessive bits
  typedef enum logic [3:0] {IDLE, SOFS, DYN, FIX, CDEL, ACKS, ADEL, EOFS, ERRW} st_t;
  typedef enum logic [3:0] {F_ID, F_B12, F_IDE, F_IDX, F_RTR, F_FDF, F_R0, F_RES, F_BRS, F_ESI,
                            F_DLC, F_DATA, F_CRC} fld_t;
  st_t         st;
  fld_t        fld;
  logic [3:0]  cnt, len_q;      // clock in bit, clocks in this bit
  logic        fast;            // the next bit is a data-phase bit
  logic        rxp;             // rx one clock ago
  logic        integ;           // 11 recessive bits seen (bus integration)
  logic        tx_nx;           // tx for the next bit
  logic [3:0]  ones;            // recessive bits in a row (saturates at 11)
  logic        last;
  logic [2:0]  run, nsb;
  logic [9:0]  fc;              // field bit counter
  logic [4:0]  xc;              // SC + CRC bits taken (FD)
  logic        fsbd;            // fixed stuff bit taken for this group of four
  logic [14:0] c15;
  logic [16:0] c17;
  logic [20:0] c21, rcrc;
  logic [3:0]  scv;
  logic        crc_bad;
  logic [28:0] id;
  logic        b12, ide, rtr, fdf, brs, esi;
  logic [3:0]  dlc;
  logic [6:0]  len;
  logic [7:0]  cur;
  logic [15:0] sum;
  logic [2:0]  eflag;           // error-flag bits still to send after the first
  logic [2:0]  eofc;

  function automatic logic [14:0] f15(input logic [14:0] c, input logic b);
    f15 = (b ^ c[14]) ? ((c << 1) ^ P15) : (c << 1);
  endfunction
  function automatic logic [16:0] f17(input logic [16:0] c, input logic b);
    f17 = (b ^ c[16]) ? ((c << 1) ^ P17) : (c << 1);
  endfunction
  function automatic logic [20:0] f21(input logic [20:0] c, input logic b);
    f21 = (b ^ c[20]) ? ((c << 1) ^ P21) : (c << 1);
  endfunction
  function automatic logic [3:0] f_sc(input logic [2:0] n);
    logic [2:0] g;
    g = n ^ (n >> 1);
    f_sc = {g, ^g};
  endfunction
  function automatic logic [6:0] f_len(input logic [3:0] d, input logic fd, input logic r);
    if (!fd) f_len = r ? 7'd0 : ((d > 4'd8) ? 7'd8 : {3'b0, d});
    else case (d)
      4'd9:  f_len = 7'd12;
      4'd10: f_len = 7'd16;
      4'd11: f_len = 7'd20;
      4'd12: f_len = 7'd24;
      4'd13: f_len = 7'd32;
      4'd14: f_len = 7'd48;
      4'd15: f_len = 7'd64;
      default: f_len = {3'b0, d};
    endcase
  endfunction

  wire [3:0] nb = (nbt == 4'd0) ? 4'd1 : nbt;
  wire [3:0] db = (dbt == 4'd0) ? 4'd1 : dbt;
  assign err_pas = rec[7];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= IDLE; fld <= F_ID; cnt <= '0; len_q <= 4'd1; fast <= 1'b0; rxp <= 1'b1; integ <= 1'b0;
      tx_nx <= 1'b1; ones <= '0; last <= 1'b1; run <= '0; nsb <= '0; fc <= '0; xc <= '0; fsbd <= 1'b0;
      c15 <= '0; c17 <= I17; c21 <= I21; rcrc <= '0; scv <= '0; crc_bad <= 1'b0;
      id <= '0; b12 <= 1'b0; ide <= 1'b0; rtr <= 1'b0; fdf <= 1'b0; brs <= 1'b0; esi <= 1'b0;
      dlc <= '0; len <= '0; cur <= '0; sum <= '0; eflag <= '0; eofc <= '0;
      tx <= 1'b1; rx_ok <= 1'b0; rx_err <= 1'b0; pex <= 1'b0; err_code <= '0; rec <= '0;
      out_id <= '0; out_ide <= 1'b0; out_fdf <= 1'b0; out_brs <= 1'b0; out_esi <= 1'b0; out_rtr <= 1'b0;
      out_dlc <= '0; out_len <= '0; out_sum <= '0;
    end else begin : step
      logic       sync, smp, wrap, nx, fst, b, fe, dend;
      logic [2:0] ec;
      logic [3:0] c, lc;
      st_t        stc;
      fe = 1'b0; ec = 3'd0; dend = 1'b0;
      rx_ok <= 1'b0; rx_err <= 1'b0; pex <= 1'b0;
      rxp <= rx;
      // bit timing: hard synchronisation on the SOF edge, sample in mid-bit
      sync = (st == IDLE) && integ && rxp && !rx;
      c    = sync ? 4'd0 : cnt;
      lc   = sync ? nb : len_q;
      smp  = (c == (lc >> 1));
      wrap = (c >= lc - 4'd1);
      cnt  <= wrap ? 4'd0 : c + 4'd1;
      if (sync) stc = SOFS; else stc = st;
      if (sync) st <= SOFS;
      nx = tx_nx; fst = fast; b = rx;
      if (smp) begin
        ones <= b ? ((ones == 4'd11) ? ones : ones + 4'd1) : 4'd0;
        if (eflag != 3'd0) begin nx = 1'b0; eflag <= eflag - 3'd1; end
        else nx = 1'b1;
        case (stc)
          IDLE:
            if (b && ones >= 4'd10) integ <= 1'b1;
          SOFS:
            if (b) st <= IDLE;
            else begin
              st <= DYN; fld <= F_ID; fc <= '0; last <= 1'b0; run <= 3'd1; nsb <= '0;
              c15 <= f15(15'h0, 1'b0); c17 <= f17(I17, 1'b0); c21 <= f21(I21, 1'b0);
              id <= '0; brs <= 1'b0; esi <= 1'b0; sum <= '0;   // the other fields are always written
            end
          DYN:
            if (run == 3'd5) begin                 // dynamic stuff bit
              if (b == last) begin fe = 1'b1; ec = 3'd1; end
              nsb <= nsb + 3'd1; last <= b; run <= 3'd1;
              c17 <= f17(c17, b); c21 <= f21(c21, b);
            end else begin
              run <= (b == last) ? run + 3'd1 : 3'd1;
              last <= b;
              if (fld != F_CRC) begin c15 <= f15(c15, b); c17 <= f17(c17, b); c21 <= f21(c21, b); end
              fc <= fc + 10'd1;
              case (fld)
                F_ID:  begin id <= {id[27:0], b}; if (fc == 10'd10) fld <= F_B12; end
                F_B12: begin b12 <= b; fld <= F_IDE; end
                F_IDE: begin
                  ide <= b; fc <= '0;
                  if (b) fld <= F_IDX;
                  else begin rtr <= b12; fld <= F_FDF; end
                end
                F_IDX: begin id <= {id[27:0], b}; if (fc == 10'd17) fld <= F_RTR; end
                F_RTR: begin rtr <= b; fld <= F_FDF; end
                F_FDF: begin
                  fdf <= b; fc <= '0;
                  if (b) begin rtr <= 1'b0; fld <= F_RES; end
                  else if (ide) fld <= F_R0;
                  else fld <= F_DLC;
                end
                F_R0:  begin fc <= '0; fld <= F_DLC; end
                F_RES: begin
                  if (b) begin
                    if (pex_en) begin st <= ERRW; pex <= 1'b1; ones <= '0; end
                    else begin fe = 1'b1; ec = 3'd2; end
                  end
                  fld <= F_BRS;
                end
                F_BRS: begin brs <= b; if (b) fst = 1'b1; fld <= F_ESI; end
                F_ESI: begin esi <= b; fc <= '0; fld <= F_DLC; end
                F_DLC: begin
                  dlc <= {dlc[2:0], b};
                  if (fc == 10'd3) begin
                    len <= f_len({dlc[2:0], b}, fdf, rtr);
                    fc <= '0; fld <= F_DATA;
                    if (f_len({dlc[2:0], b}, fdf, rtr) == 7'd0) dend = 1'b1;
                  end
                end
                F_DATA: begin
                  cur <= {cur[6:0], b};
                  if (fc[2:0] == 3'd7) sum <= sum + {8'h0, cur[6:0], b};
                  if (fc == ({3'b0, len} << 3) - 10'd1) dend = 1'b1;
                end
                default: begin                       // F_CRC: classical CRC15
                  rcrc <= {rcrc[19:0], b};
                  if (fc == 10'd14) begin crc_bad <= ({rcrc[13:0], b} != c15); st <= CDEL; end
                end
              endcase
              if (dend) begin
                fc <= '0;
                if (fdf) begin st <= FIX; xc <= '0; fsbd <= 1'b0; run <= 3'd0; end
                else fld <= F_CRC;
              end
            end
          FIX:
            if (xc[1:0] == 2'd0 && !fsbd) begin   // fixed stuff bit
              if (b == last) begin fe = 1'b1; ec = 3'd4; end
              fsbd <= 1'b1; last <= b;
            end else begin
              fsbd <= 1'b0; last <= b; xc <= xc + 5'd1;
              if (xc < 5'd4) begin scv <= {scv[2:0], b}; c17 <= f17(c17, b); c21 <= f21(c21, b); end
              else rcrc <= {rcrc[19:0], b};
              if (xc == ((len > 7'd16) ? 5'd24 : 5'd20)) begin
                st <= CDEL; fst = 1'b0;              // nominal rate from the CRC delimiter
                if (len > 7'd16) crc_bad <= (scv != f_sc(nsb)) || ({rcrc[19:0], b} != c21);
                else             crc_bad <= (scv != f_sc(nsb)) || ({rcrc[15:0], b} != c17);
              end
            end
          CDEL:
            if (!fdf && run == 3'd5) begin         // stuff bit after the last CRC15 bit
              if (b == last) begin fe = 1'b1; ec = 3'd1; end
              run <= 3'd0;
            end else begin
              if (!b) begin fe = 1'b1; ec = 3'd2; end
              else if (!crc_bad) nx = 1'b0;          // dominant ACK in the slot
              st <= ACKS;
            end
          ACKS: st <= ADEL;
          ADEL:
            if (!b) begin fe = 1'b1; ec = 3'd2; end
            else if (crc_bad) begin fe = 1'b1; ec = 3'd3; end
            else begin st <= EOFS; eofc <= '0; end
          EOFS: begin                               // a dominant last EOF bit is not an error
            eofc <= eofc + 3'd1;
            if (eofc < 3'd6 && !b) begin fe = 1'b1; ec = 3'd2; end
            else if (eofc == 3'd5) begin             // frame valid for a receiver
              if (rec > 8'd127) rec <= 8'd127;
              else if (rec != 8'd0) rec <= rec - 8'd1;
              if (((id ^ acc_id) & acc_msk) == 29'h0) begin
                rx_ok <= 1'b1;
                out_id <= id; out_ide <= ide; out_fdf <= fdf; out_brs <= brs; out_esi <= esi;
                out_rtr <= rtr; out_dlc <= dlc; out_len <= len; out_sum <= sum;
              end
            end
            if (eofc == 3'd6) st <= IDLE;
          end
          default:                                 // ERRW: 11 recessive bits after the error
            if (b && ones >= 4'd10) st <= IDLE;
        endcase
        if (fe) begin
          st <= ERRW; eflag <= 3'd5; nx = 1'b0; fst = 1'b0; ones <= '0;
          err_code <= ec; rx_err <= 1'b1;
          if (rec != 8'hFF) rec <= rec + 8'd1;
        end
        tx_nx <= nx; fast <= fst;
      end
      if (wrap) begin tx <= nx; len_q <= fst ? db : nb; end
    end
  end
endmodule
""",
)

SPEC["smoke"] = """
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic rx = 1'b1;
logic [3:0] nbt = 4'd1, dbt = 4'd1;      // DUT bit-time inputs
int tn = 1, td = 1;                      // bit times the testbench drives
logic pex_en = 1'b1;
logic [28:0] acc_id = 29'h0, acc_msk = 29'h0;
wire tx, rx_ok, rx_err, pex, err_pas, out_ide, out_fdf, out_brs, out_esi, out_rtr;
wire [2:0] err_code;
wire [7:0] rec;
wire [28:0] out_id;
wire [3:0] out_dlc;
wire [6:0] out_len;
wire [15:0] out_sum;

always #5 clk = ~clk;

can_fd_model u_dut (.clk(clk), .rst_n(rst_n), .rx(rx), .nbt(nbt), .dbt(dbt), .pex_en(pex_en), .acc_id(acc_id),
                    .acc_msk(acc_msk), .tx(tx), .rx_ok(rx_ok), .rx_err(rx_err), .pex(pex), .err_code(err_code),
                    .rec(rec), .err_pas(err_pas), .out_id(out_id), .out_ide(out_ide), .out_fdf(out_fdf),
                    .out_brs(out_brs), .out_esi(out_esi), .out_rtr(out_rtr), .out_dlc(out_dlc), .out_len(out_len),
                    .out_sum(out_sum));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [14:0] f15(input logic [14:0] c, input logic b);
  f15 = (b ^ c[14]) ? ((c << 1) ^ 15'h4599) : (c << 1);
endfunction
function automatic logic [16:0] f17(input logic [16:0] c, input logic b);
  f17 = (b ^ c[16]) ? ((c << 1) ^ 17'h1685B) : (c << 1);
endfunction
function automatic logic [20:0] f21(input logic [20:0] c, input logic b);
  f21 = (b ^ c[20]) ? ((c << 1) ^ 21'h102899) : (c << 1);
endfunction
function automatic int flen(input logic [3:0] d, input logic fd, input logic r);
  if (!fd) flen = r ? 0 : ((d > 8) ? 8 : d);
  else case (d)
    9: flen = 12;  10: flen = 16;  11: flen = 20;  12: flen = 24;
    13: flen = 32; 14: flen = 48;  15: flen = 64;
    default: flen = d;
  endcase
endfunction

logic lb [0:1023];               // line bits SOF .. CRC delimiter
logic lf [0:1023];               // 1: data-phase bit
int nl;
int tsb;                         // index of a stuff bit after the last CRC15 bit (-1 none)
logic [7:0] dat [0:63];
logic [15:0] esum;               // sum of the frame's data bytes
logic saw_ack, saw_ok, saw_err, saw_pex;
int ntxlow, t_ok, t_err, cyc, ack_c;
int adel_dom = 0, eof_dom = -1;  // trailer faults: dominant ACK delimiter / EOF bit

task automatic fill(input int seed);
  for (int j = 0; j < 64; j++) dat[j] = (seed * 37 + j * 11 + (j >> 2)) ^ (j[0] ? 8'h5A : 8'hC3);
endtask

// err: 0 none, 1 stuff, 2 dominant CRC delimiter, 3 CRC, 4 stuff count, 5 fixed stuff bit, 6 res recessive
task automatic build(input logic ide, input logic [28:0] id0, input logic rtr, input logic fdf, input logic brs,
                     input logic esi, input logic [3:0] dlc, input int err);
  logic a [0:700];
  logic f [0:31];
  logic [28:0] id;
  int na, n, run, nsb, nf, ncrc, brs_i, i, j;
  logic last, s, fst, dd;
  logic [14:0] c15;
  logic [16:0] c17;
  logic [20:0] c21, crc;
  logic [2:0] g;
  id = id0;
  if (err == 1) begin if (ide) id[28:25] = 4'h0; else id[10:7] = 4'h0; end
  na = 0; nl = 0; tsb = -1;
  a[na] = 0; na++;
  if (ide) begin
    for (i = 28; i >= 18; i--) begin a[na] = id[i]; na++; end
    a[na] = 1; a[na + 1] = 1; na += 2;
    for (i = 17; i >= 0; i--) begin a[na] = id[i]; na++; end
    a[na] = fdf ? 1'b0 : rtr; a[na + 1] = fdf; na += 2;
    if (!fdf) begin a[na] = 0; na++; end
  end else begin
    for (i = 10; i >= 0; i--) begin a[na] = id[i]; na++; end
    a[na] = fdf ? 1'b0 : rtr; a[na + 1] = 0; a[na + 2] = fdf; na += 3;
  end
  brs_i = -1;
  if (fdf) begin a[na] = (err == 6); a[na + 1] = brs; a[na + 2] = esi; brs_i = na + 1; na += 3; end
  for (i = 3; i >= 0; i--) begin a[na] = dlc[i]; na++; end
  n = flen(dlc, fdf, rtr);
  esum = 0;
  for (j = 0; j < n; j++) begin
    esum = esum + dat[j];
    for (i = 7; i >= 0; i--) begin a[na] = dat[j][i]; na++; end
  end
  if (!fdf) begin
    c15 = 0;
    for (i = 0; i < na; i++) c15 = f15(c15, a[i]);
    if (err == 3) c15[0] = !c15[0];
    for (i = 14; i >= 0; i--) begin a[na] = c15[i]; na++; end
  end
  last = 1; run = 0; nsb = 0; fst = 0; dd = 0;
  c17 = 17'h10000; c21 = 21'h100000;
  for (i = 0; i <= na; i++) begin
    if (run == 5 && (i < na || !fdf)) begin
      s = !last;
      if (err == 1 && !dd) begin s = last; dd = 1; end
      if (i == na) tsb = nl;
      lb[nl] = s; lf[nl] = fst; nl++;
      c17 = f17(c17, s); c21 = f21(c21, s); nsb++; last = s; run = 1;
    end
    if (i == na) break;
    lb[nl] = a[i]; lf[nl] = fst; nl++;
    c17 = f17(c17, a[i]); c21 = f21(c21, a[i]);
    if (a[i] == last) run++; else begin last = a[i]; run = 1; end
    if (i == brs_i && brs) fst = 1;
  end
  if (fdf) begin
    g = nsb[2:0] ^ (nsb[2:0] >> 1);
    f[0] = g[2]; f[1] = g[1]; f[2] = g[0]; f[3] = ^g; nf = 4;
    for (i = 0; i < 4; i++) begin c17 = f17(c17, f[i]); c21 = f21(c21, f[i]); end
    ncrc = (n <= 16) ? 17 : 21;
    crc = (ncrc == 17) ? {4'h0, c17} : c21;
    for (i = ncrc - 1; i >= 0; i--) begin f[nf] = crc[i]; nf++; end
    if (err == 4) f[3] = !f[3];
    if (err == 3) f[nf - 1] = !f[nf - 1];
    for (i = 0; i < nf; i++) begin
      if (i % 4 == 0) begin
        s = (err == 5 && i == 0) ? last : !last;
        lb[nl] = s; lf[nl] = fst; nl++; last = s;
      end
      lb[nl] = f[i]; lf[nl] = fst; nl++; last = f[i];
    end
  end
  lb[nl] = (err == 2) ? 1'b0 : 1'b1; lf[nl] = 0; nl++;
endtask

task automatic sample();
  if (!tx) ntxlow++;
  if (rx_ok) begin saw_ok = 1; if (t_ok < 0) t_ok = cyc; end
  if (rx_err) begin saw_err = 1; if (t_err < 0) t_err = cyc; end
  if (pex) saw_pex = 1;
endtask

// idle bits, the frame at its bit times, then ACK slot, ACK delimiter, EOF
task automatic send(input int idle);
  int k, b, L;
  saw_ack = 0; saw_ok = 0; saw_err = 0; saw_pex = 0; ntxlow = 0; t_ok = -1; t_err = -1; cyc = 0;
  repeat (idle * tn) begin @(negedge clk); rx = 1; end
  for (k = 0; k < nl; k++) begin
    L = lf[k] ? td : tn;
    repeat (L) begin @(negedge clk); rx = lb[k]; cyc++; sample(); end
  end
  ack_c = cyc + 1;
  for (k = 0; k < 9 * tn; k++) begin
    b = k / tn;                     // 0 ACK slot, 1 ACK delimiter, 2..8 EOF
    @(negedge clk);
    rx = !((b == 1 && adel_dom) || (eof_dom >= 0 && b == 2 + eof_dom));
    cyc++; sample();
    if (b == 0 && !tx && !saw_err) saw_ack = 1;
  end
endtask

int r0, nok;

initial begin
  repeat (3) @(posedge clk);
  chk(tx === 1'b1, "tx recessive in reset");
  chk(rx_ok === 1'b0 && rx_err === 1'b0 && pex === 1'b0 && rec === 8'd0 && err_code === 3'd0, "no reports in reset");
  chk(out_id === 29'h0 && {out_ide, out_fdf, out_brs, out_esi, out_rtr} === 5'b0 && out_dlc === 4'd0 &&
      out_len === 7'd0 && out_sum === 16'h0, "frame outputs clear in reset");
  rst_n = 1;

  // no bus integration yet: a frame straight after reset is ignored
  fill(1); build(0, 29'h123, 0, 0, 0, 0, 4'd2, 0); send(0);
  chk(!saw_ack && !saw_ok && !saw_err && ntxlow == 0, "frame before bus integration ignored");

  // classical base data frame
  fill(2); build(0, 29'h123, 0, 0, 0, 0, 4'd2, 0); send(11);
  chk(saw_ack && saw_ok && !saw_err, "classical base frame ACKed and reported");
  chk(out_id === 29'h123 && !out_ide && !out_fdf && !out_rtr && !out_brs && out_dlc === 4'd2 && out_len === 7'd2,
      "classical base fields");
  chk(out_sum === esum, "data byte sum");
  chk(ntxlow == 1, $sformatf("one dominant bit (ACK) for a good frame (%0d)", ntxlow));
  chk(t_ok - ack_c == 8, $sformatf("rx_ok after the sixth EOF bit (%0d)", t_ok - ack_c));
  // classical extended remote frame
  build(1, 29'h1ABC_1234, 1, 0, 0, 0, 4'd3, 0); send(11);
  chk(saw_ack && saw_ok && out_id === 29'h1ABC_1234 && out_ide && out_rtr && out_dlc === 4'd3 && out_len === 7'd0,
      "classical extended remote frame");
  // classical DLC above 8 carries 8 bytes
  fill(3); build(0, 29'h050, 0, 0, 0, 0, 4'd12, 0); send(11);
  chk(saw_ok && out_len === 7'd8 && out_dlc === 4'd12 && out_sum === esum, "classical DLC 12 = 8 bytes");
  // FD base frame, no rate switch, CRC17
  fill(4); build(0, 29'h2A5, 0, 1, 0, 0, 4'd9, 0); send(11);
  chk(saw_ack && saw_ok && out_fdf && !out_brs && !out_esi && !out_rtr && out_len === 7'd12 && out_sum === esum,
      "FD frame, 12 bytes, CRC17");

  // dual bit rate: nominal 4 clocks, data 1 clock, 64 bytes, CRC21
  nbt = 4; dbt = 1; tn = 4; td = 1;
  fill(5); build(1, 29'h0F0F_0F0F, 0, 1, 1, 1, 4'd15, 0); send(11);
  chk(saw_ack && saw_ok && !saw_err, "FD extended frame with BRS ACKed");
  chk(out_id === 29'h0F0F_0F0F && out_brs && out_esi && out_ide && out_len === 7'd64 && out_sum === esum,
      "BRS / ESI / 64 bytes reported");
  chk(ntxlow == 4, $sformatf("ACK lasts one nominal bit (%0d clocks)", ntxlow));
  chk(t_ok - ack_c == 31, $sformatf("rx_ok at the nominal bit time (%0d)", t_ok - ack_c));
  // nominal 3, data 2: CRC17 / CRC21 boundary
  nbt = 3; dbt = 2; tn = 3; td = 2;
  fill(6); build(0, 29'h3C3, 0, 1, 1, 0, 4'd10, 0); send(11);
  chk(saw_ack && saw_ok && out_len === 7'd16 && out_sum === esum, "16 bytes at 3/2 clocks (CRC17)");
  fill(7); build(0, 29'h3C4, 0, 1, 1, 0, 4'd11, 0); send(11);
  chk(saw_ack && saw_ok && out_len === 7'd20 && out_sum === esum, "20 bytes at 3/2 clocks (CRC21)");
  // every FD DLC at 2/1 clocks, and classical frames with many stuff patterns
  nbt = 2; dbt = 1; tn = 2; td = 1;
  nok = 0;
  for (int d = 0; d < 16; d++) begin
    fill(10 + d); build(d[0], 29'h0155_5000 + d * 29'h31, 0, 1, 1, d[1], d[3:0], 0); send(11);
    if (saw_ack && saw_ok && !saw_err && out_len == flen(d[3:0], 1, 0) && out_sum === esum) nok++;
  end
  chk(nok == 16, $sformatf("all 16 FD DLCs received (%0d)", nok));
  nbt = 1; dbt = 1; tn = 1; td = 1;
  nok = 0;
  for (int d = 0; d < 40; d++) begin
    fill(40 + d); build(d[0], d[0] ? 29'h0 + d : 29'h7C0 + d, 0, 0, 0, 0, d % 9, 0); send(11);
    if (saw_ack && saw_ok && !saw_err && out_sum === esum) nok++;
  end
  chk(nok == 40, $sformatf("40 classical frames received (%0d)", nok));
  // nbt / dbt of 0 count as one clock
  nbt = 0; dbt = 0;
  fill(8); build(0, 29'h111, 0, 1, 1, 0, 4'd4, 0); send(11);
  chk(saw_ack && saw_ok && out_sum === esum, "bit time 0 treated as one clock");
  nbt = 1; dbt = 1;

  // errors
  r0 = rec;
  fill(9); build(0, 29'h4F0, 0, 0, 0, 0, 4'd1, 1); send(11);
  chk(saw_err && !saw_ack && !saw_ok && err_code === 3'd1, "stuff error flagged, no ACK");
  chk(ntxlow == 6, $sformatf("six-bit error flag (%0d)", ntxlow));
  chk(rec == r0 + 1 && !err_pas, "receive error counter +1");
  build(0, 29'h0F0, 0, 1, 1, 0, 4'd8, 3); send(11);
  chk(saw_err && !saw_ack && err_code === 3'd3 && rec == r0 + 2, "FD CRC error flagged, no ACK");
  chk(t_err - ack_c == 2, $sformatf("CRC error flag after the ACK delimiter (%0d)", t_err - ack_c));
  chk(ntxlow == 6, "CRC error flag six bits");
  // after the error (at the ACK delimiter) the node needs 11 recessive bits:
  // 7 EOF bits + 3 idle bits are too few, 7 + 4 are enough
  fill(13); build(0, 29'h0E1, 0, 1, 0, 0, 4'd1, 0); send(3);
  chk(!saw_ack && !saw_ok && !saw_err, "SOF ignored 10 recessive bits after an error");
  build(0, 29'h0E2, 0, 1, 0, 0, 4'd1, 3); send(11);
  build(0, 29'h0E3, 0, 1, 0, 0, 4'd1, 0); send(4);
  chk(saw_ack && saw_ok, "SOF accepted 11 recessive bits after an error");
  build(1, 29'h0ABC_DEF0, 0, 1, 1, 0, 4'd13, 3); send(11);
  chk(saw_err && err_code === 3'd3, "FD CRC21 error flagged");
  build(0, 29'h0F1, 0, 1, 0, 0, 4'd3, 4); send(11);
  chk(saw_err && !saw_ack && err_code === 3'd3, "stuff count error flagged as CRC error");
  build(0, 29'h0F2, 0, 1, 1, 0, 4'd5, 5); send(11);
  chk(saw_err && !saw_ack && err_code === 3'd4, "fixed stuff bit error");
  build(0, 29'h0F3, 0, 0, 0, 0, 4'd2, 2); send(11);
  chk(saw_err && !saw_ack && !saw_ok && err_code === 3'd2, "dominant CRC delimiter: form error");
  build(0, 29'h0F4, 0, 0, 0, 0, 4'd2, 3); send(11);
  chk(saw_err && !saw_ack && err_code === 3'd3, "classical CRC15 error");
  // a stuff bit after the last CRC15 bit is checked too
  begin : trail
    int sd;
    sd = 0;
    do begin fill(100 + sd); build(0, 29'h200 + sd, 0, 0, 0, 0, 4'd1 + sd % 8, 0); sd++; end
    while (tsb < 0 && sd < 400);
    chk(tsb >= 0, "found a classical frame ending in a stuff bit");
    send(11);
    chk(saw_ok && !saw_err, "trailing CRC15 stuff bit accepted");
    lb[tsb] = !lb[tsb]; send(11);
    chk(saw_err && !saw_ack && err_code === 3'd1, "bad trailing CRC15 stuff bit: stuff error");
  end
  // a dominant glitch shorter than the sample point is not a SOF
  nbt = 4; tn = 4;
  repeat (12 * 4) @(negedge clk);
  rx = 0; @(negedge clk); rx = 1;
  repeat (20) @(negedge clk);
  chk(!rx_err && !rx_ok && tx === 1'b1, "one-clock glitch ignored");
  fill(15); build(0, 29'h0E4, 0, 0, 0, 0, 4'd1, 0); send(11);
  chk(saw_ack && saw_ok, "frame after a glitch received");
  nbt = 1; tn = 1;
  adel_dom = 1; build(0, 29'h0F5, 0, 1, 0, 0, 4'd1, 0); send(11); adel_dom = 0;
  chk(saw_ack && saw_err && !saw_ok && err_code === 3'd2, "dominant ACK delimiter: form error after the ACK");
  eof_dom = 5; build(0, 29'h0F6, 0, 0, 0, 0, 4'd1, 0); send(11); eof_dom = -1;
  chk(saw_err && !saw_ok && err_code === 3'd2, "dominant sixth EOF bit: form error");
  r0 = rec;
  eof_dom = 6; build(0, 29'h0F7, 0, 0, 0, 0, 4'd1, 0); send(11); eof_dom = -1;
  chk(saw_ok && !saw_err && rec == r0 - 1, "dominant last EOF bit ignored, counter -1");
  // protocol exception
  r0 = rec;
  build(0, 29'h0F8, 0, 1, 1, 0, 4'd6, 6); send(11);
  chk(saw_pex && !saw_err && !saw_ack && !saw_ok && rec == r0, "res recessive: protocol exception, no flag");
  build(0, 29'h0F8, 0, 1, 1, 0, 4'd6, 0); send(11);
  chk(saw_ok && !saw_pex, "frame after a protocol exception received");
  pex_en = 0;
  build(0, 29'h0F9, 0, 1, 1, 0, 4'd6, 6); send(11);
  chk(saw_err && !saw_pex && err_code === 3'd2, "res recessive without protocol exception: form error");
  pex_en = 1;

  // acceptance filter
  acc_id = 29'h124; acc_msk = 29'h7FF;
  fill(11); build(0, 29'h123, 0, 1, 1, 0, 4'd2, 0); send(11);
  chk(saw_ack && !saw_ok && out_id !== 29'h123, "filtered frame ACKed, not reported");
  build(0, 29'h124, 0, 1, 1, 0, 4'd2, 0); send(11);
  chk(saw_ok && out_id === 29'h124, "matching frame reported");
  acc_msk = 29'h0;

  // error passive and back
  while (rec < 8'd130) begin build(0, 29'h055, 0, 0, 0, 0, 4'd0, 1); send(11); end
  chk(err_pas && rec == 8'd130, "error passive at 128 and above");
  fill(12); build(0, 29'h056, 0, 1, 0, 0, 4'd1, 0); send(11);
  chk(saw_ok && rec == 8'd127 && !err_pas, "good frame sets an error-passive counter to 127");
  while (rec < 8'd255) begin build(0, 29'h055, 0, 0, 0, 0, 4'd0, 1); send(11); end
  build(0, 29'h055, 0, 0, 0, 0, 4'd0, 1); send(11);
  chk(saw_err && rec == 8'd255, "counter saturates at 255");

  // bus integration after reset: 11 recessive bits before the first SOF
  @(negedge clk); rst_n = 0; @(negedge clk); rst_n = 1;
  chk(rec === 8'd0 && !err_pas, "reset clears the error counter");
  fill(14); build(0, 29'h0D1, 0, 0, 0, 0, 4'd1, 0); send(9);
  chk(!saw_ack && !saw_ok && !saw_err, "SOF after 10 recessive bits from reset ignored");
  @(negedge clk); rst_n = 0; @(negedge clk); rst_n = 1;
  build(0, 29'h0D1, 0, 0, 0, 0, 4'd1, 0); send(10);
  chk(saw_ack && saw_ok, "SOF after 11 recessive bits from reset received");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #5000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
"""

SPEC["sva"] = """
// outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({tx, rx_ok, rx_err, pex, err_code, rec, err_pas}))
  else $error("CAN FD: X on outputs");
// recessive in reset
assert property (@(posedge clk) disable iff (1'b0) !rst_n |=> tx)
  else $error("CAN FD: tx not recessive in reset");
// a good frame, an error and a protocol exception are never reported together
assert property (@(posedge clk) disable iff (!rst_n) !(rx_ok && rx_err) && !(pex && rx_err) && !(pex && rx_ok))
  else $error("CAN FD: rx_ok / rx_err / pex together");
// error passive from a receive error count of 128
assert property (@(posedge clk) disable iff (!rst_n) err_pas == rec[7])
  else $error("CAN FD: err_pas does not follow rec");
// an error moves the counter up by one (saturating)
assert property (@(posedge clk) disable iff (!rst_n) rx_err |-> rec == $past(rec) + 8'd1 || $past(rec) == 8'hFF)
  else $error("CAN FD: receive error counter not incremented");
// tx is dominant for at most six nominal bits in a row (the error flag)
int unsigned low_clk;
always @(posedge clk or negedge rst_n)
  if (!rst_n) low_clk <= 0;
  else low_clk <= tx ? 0 : low_clk + 1;
assert property (@(posedge clk) disable iff (!rst_n) low_clk <= 6 * ((nbt == 4'd0) ? 1 : nbt))
  else $error("CAN FD: tx dominant for more than six nominal bits");
cover property (@(posedge clk) disable iff (!rst_n) rx_ok && out_fdf && out_brs);
cover property (@(posedge clk) disable iff (!rst_n) rx_err && err_code == 3'd4);
cover property (@(posedge clk) disable iff (!rst_n) pex);
"""
