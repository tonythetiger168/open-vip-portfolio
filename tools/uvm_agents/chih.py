# AMBA CHI Issue H link-level VIP: a Subordinate Node (SN-F, memory) with
# Issue H flit formats on the REQ / RSP / DAT channels and link-layer
# L-credit flow control, driven by a Home Node (HN-F) agent.
#
# Configuration (AMBA CHI Architecture Specification, Issue H, B13.9):
#   NodeID_Width = 7, Req_Addr_Width = 44, Data_Width = 128, and no optional
#   fields (MPAM, PBHA, MECID / StreamID, SecSID1, RSVDC, DataCheck, Poison).
#   Flit widths: REQ 137 (93 + RAW), RSP 71, DAT 240 bits.
# Bit layouts, low bit first, as in Tables B13.6, B13.7 and B13.9:
#   REQ  QoS[3:0] TgtID[10:4] SrcID[17:11] TxnID[29:18] ReturnNID[36:30]
#        StashNIDValid / Endian / Deep / PrefetchTgtHint[37]
#        ReturnTxnID[49:38] Opcode[56:50] MultiReq[57] NumReq / {3'b0, Size}[63:58]
#        Addr[107:64] PAS[110:108] LikelyShared[111] AllowRetry[112] Order[114:113]
#        PCrdType[118:115] MemAttr[122:119] SnpAttr / DoDWT[123]
#        PGroupID / StashGroupID / TagGroupID / {3'b0, LPID}[131:124]
#        Excl / SnoopMe / CAH[132] ExpCompAck[133] TagOp[135:134] TraceTag[136]
#   RSP  QoS[3:0] TgtID[10:4] SrcID[17:11] TxnID[29:18] Opcode[34:30]
#        RespErr[36:35] Resp[39:37] FwdState / DataPull[42:40] CBusy[45:43]
#        DBID / PGroupID / StashGroupID / TagGroupID[57:46] PCrdType[61:58]
#        TagOp[63:62] TraceTag[64] CacheLineID[70:65]
#   DAT  QoS[3:0] TgtID[10:4] SrcID[17:11] TxnID[29:18] HomeNID[36:30]
#        Opcode[40:37] RespErr[42:41] Resp[45:43] DataSource / FwdState[53:46]
#        DataPull[54] CBusy[57:55] {4'b0, DBID}[73:58] CCID[75:74] DataID[77:76]
#        CacheLineID[83:78] TagOp[85:84] Tag[89:86] TU[90] TraceTag[91] CAH[92]
#        NumDat[94:93] Replicate[95] BE[111:96] Data[239:112]
#
# tb/top_tb.sv chih_model is the SN-F (NodeID 0x20) with 1 KB of memory:
#   L-credits (B13.2): it grants 4 REQ and 4 DAT L-credits after reset and
#   returns one for every flit it consumes, at most one per channel per clock;
#   it holds the credits the HN grants on TXRSPLCRDV / TXDATLCRDV (at most 15,
#   B13.2.1) and sends a RSP / DAT flit only while it holds one. Requests queue
#   in arrival order and are served one at a time.
#   ReadNoSnp (0x04, Size 0..6): CompData_UC packets (B2.9.4: one 16-byte
#   packet for Size <= 4, else 2^Size / 16, DataID = address bits [5:4] of the
#   packet, data at natural byte positions) to ReturnNID with ReturnTxnID,
#   HomeNID = SrcID and DBID = TxnID (DMT, B5.1.8); with Order = 0b01 a
#   ReadReceipt first (B2.7.5.1).
#   WriteNoSnpFull (0x1D, Size 6) / WriteNoSnpPtl (0x1C, Size 0..6):
#   CompDBIDResp with the next 12-bit DBID, then NonCopyBackWriteData (0x3) or
#   WriteDataCancel (0x7) packets with TxnID = DBID; bytes with BE set are
#   written (B2.9.3).
#   An address at or above 1 KB completes with RespErr = NDERR (0b11): read
#   data zero, write data dropped.
# err (one-clock pulses, the cause is dropped unless noted):
#   [0] REQ / DAT flit without an L-credit
#   [1] REQ TgtID is not this node (credit returned)
#   [2] field value not permitted here: MultiReq, NumReq / Size MBZ bits,
#       Size > 6, Order 0b10 / 0b11 (reserved HN-F to SN-F, Table B13.22),
#       WriteNoSnpFull with Size != 6 (credit returned)
#   [3] opcode not supported by this SN (credit returned)
#   [4] write data breaks a B2.9.3 rule: BE outside the data window, data
#       non-zero where BE = 0, WriteNoSnpFull without all BE in the window,
#       WriteDataCancel with BE set, WriteNoSnpPtl to Device memory with BE
#       below Addr (the packet counts, nothing is written)
#   [5] DAT flit nobody waits for: no write waiting, TgtID / TxnID / DataID
#       not the expected ones, or an opcode other than 0x3 / 0x7
#   [6] L-credit granted to the SN while it already holds 15

CHIH_DEFS = """
localparam bit [6:0] CHIH_SN  = 7'h20;   // the SN-F model's NodeID
localparam bit [6:0] CHIH_HN  = 7'h05;   // the agent's NodeID
localparam bit [6:0] CHIH_RN  = 7'h11;   // a requester for DMT (ReturnNID)
localparam bit [6:0] CHIH_READ_NOSNP  = 7'h04;
localparam bit [6:0] CHIH_WRITE_PTL   = 7'h1C;
localparam bit [6:0] CHIH_WRITE_FULL  = 7'h1D;
localparam bit [4:0] CHIH_RSP_COMPDBID = 5'h05;
localparam bit [4:0] CHIH_RSP_RRECEIPT = 5'h08;
localparam bit [3:0] CHIH_DAT_NCBWR    = 4'h3;
localparam bit [3:0] CHIH_DAT_COMPDATA = 4'h4;
localparam bit [3:0] CHIH_DAT_CANCEL   = 4'h7;
typedef struct packed {
  bit [6:0] tgt; bit [6:0] src; bit [11:0] txn; bit [6:0] rnid; bit [11:0] rtxn; bit [6:0] op;
  bit mreq; bit [5:0] nreq; bit [43:0] addr; bit [1:0] order; bit [3:0] memattr;
} chih_req_t;
function automatic bit [136:0] chih_req(chih_req_t r);
  bit [136:0] f = '0;
  f[10:4] = r.tgt; f[17:11] = r.src; f[29:18] = r.txn; f[36:30] = r.rnid; f[49:38] = r.rtxn;
  f[56:50] = r.op; f[57] = r.mreq; f[63:58] = r.nreq; f[107:64] = r.addr; f[114:113] = r.order;
  f[122:119] = r.memattr;
  return f;
endfunction
// RSP / DAT flits as the SN builds them
function automatic bit [70:0] chih_rsp(bit [6:0] tgt, bit [11:0] txn, bit [4:0] op, bit [1:0] re, bit [11:0] dbid);
  bit [70:0] f = '0;
  f[10:4] = tgt; f[17:11] = CHIH_SN; f[29:18] = txn; f[34:30] = op; f[36:35] = re; f[57:46] = dbid;
  return f;
endfunction
function automatic bit [239:0] chih_dat(bit [6:0] tgt, bit [6:0] src, bit [11:0] txn, bit [6:0] home, bit [3:0] op,
                                        bit [1:0] re, bit [2:0] resp, bit [11:0] dbid, bit [1:0] ccid, bit [1:0] did,
                                        bit [15:0] be, bit [127:0] d);
  bit [239:0] f = '0;
  f[10:4] = tgt; f[17:11] = src; f[29:18] = txn; f[36:30] = home; f[40:37] = op; f[42:41] = re; f[45:43] = resp;
  f[73:58] = {4'b0, dbid}; f[75:74] = ccid; f[77:76] = did; f[111:96] = be; f[239:112] = d;
  return f;
endfunction
// data window of a request (B2.9.3): byte offset b of packet DataID d is inside
function automatic bit chih_in_win(bit [5:0] a, bit [2:0] size, int d, int b);
  int base = a & ~((1 << size) - 1);
  int o = d * 16 + b;
  return o >= base && o < base + (1 << size);
endfunction
function automatic int chih_npk(bit [2:0] size); return (size <= 4) ? 1 : (1 << (size - 4)); endfunction
function automatic int chih_did0(bit [5:0] a, bit [2:0] size); return (size >= 6) ? 0 : ((a & ~((1 << size) - 1)) >> 4); endfunction
"""

SPEC = dict(
    vip="CHI_H-UVM-VIP", p="chih", P="CHIH", dir="chih", family="AMBA",
    desc="AMBA CHI Issue H link-level VIP: Subordinate Node (SN-F) model with the Issue H REQ / RSP / DAT "
         "flit formats (12-bit TxnID / DBID, 7-bit opcodes, MultiReq / NumReq, PAS), L-credit flow control, "
         "ReadNoSnp with DMT and ReadReceipt, WriteNoSnpFull / Ptl with CompDBIDResp, NonCopyBackWriteData and "
         "WriteDataCancel, data packetization and the byte-enable rules; Home Node agent.",
    about="""
CHI Issue H widened TxnID and DBID to 12 bits, made the REQ opcode 7 bits wide
and added multi-request fields, a 3-bit PAS and several overlaid fields. This
VIP works at flit level against those formats: the DUT model is a memory
Subordinate Node (SN-F) and the agent is the Home Node that talks to it over
the REQ, RSP and DAT channels with link-layer L-credits. The agent sends
ReadNoSnp of every size with and without DMT (ReturnNID / ReturnTxnID to
another requester) and with Order = 0b01 (ReadReceipt), WriteNoSnpFull and
WriteNoSnpPtl with random byte enables, Device-memory writes and
WriteDataCancel, out-of-range addresses (NDERR), and protocol errors: flits
without credits, a credit overflow, a wrong target, unsupported opcodes,
reserved field values and write data that breaks the byte-enable rules. The
scoreboard runs its own copy of the SN on the monitored flits and predicts
every flit and credit, clock by clock. Snoops, link activation, retry and
the optional fields (MPAM, PBHA, MECID, RSVDC, DataCheck, Poison) are out of
this model's scope.""",
    defs=CHIH_DEFS,
    timeout=200000,
    cfg="""int unsigned gap = 20;    // quiet clocks (no flit, no credit) that end an item""",
    ports=[
        ("in", "logic", "rxreqflitv"), ("in", "logic [136:0]", "rxreqflit"), ("out", "logic", "rxreqlcrdv"),
        ("in", "logic", "rxdatflitv"), ("in", "logic [239:0]", "rxdatflit"), ("out", "logic", "rxdatlcrdv"),
        ("out", "logic", "txrspflitv"), ("out", "logic [70:0]", "txrspflit"), ("in", "logic", "txrsplcrdv"),
        ("out", "logic", "txdatflitv"), ("out", "logic [239:0]", "txdatflit"), ("in", "logic", "txdatlcrdv"),
        ("out", "logic [6:0]", "err"),
    ],
    fields=[
        # per clock {txdatlcrdv, txrsplcrdv, rxdatflitv, rxdatflit, rxreqflitv, rxreqflit}
        ("bit [380:0]", "mo", "req", "q"),
        # per clock {err, rxdatlcrdv, rxreqlcrdv, txdatflitv, txdatflit, txrspflitv, txrspflit}
        ("bit [321:0]", "so", "rsp", "q"),
        ("bit [3:0]", "kind", "info", "rand"),
        ("bit [2:0]", "size", "info", "rand"),
        ("bit [9:0]", "addr", "info", "rand"),
        ("bit [11:0]", "txn", "info", "rand"),
        ("bit", "dmt", "info", "rand"),
        ("bit", "ord", "info", "rand"),
        ("bit [2:0]", "sub", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_kind { kind dist { 0 := 6, 1 := 4, 2 := 5, 3 := 1, 4 := 1, 5 := 1, 6 := 2, 7 := 1, 8 := 1,
                                9 := 1, 10 := 1, 11 := 2, 12 := 1, [13:15] :/ 6 }; }
""",
    tr_functions="""
// kind: 0 ReadNoSnp, 1 WriteNoSnpFull, 2 WriteNoSnpPtl (sub[0]: Device memory),
// 3 WriteNoSnpPtl cancelled, 4 read at or above 1 KB, 5 write at or above 1 KB,
// 6 four reads back to back, 7 six 64-byte reads ignoring L-credits,
// 8 REQ to another node, 9 unsupported opcode (sub), 10 reserved field value
// (sub), 11 write data breaking a rule (sub), 12 L-credit overflow,
// 13 full write, partial write, read back, 14 / 15 as 0 / 2
function void set(int k, int sz = 6, int a = 0, int tx = 1, bit d = 0, bit o = 0, int sb = 0, bit [31:0] s = 1);
  kind = k; size = sz; addr = a; txn = tx; dmt = d; ord = o; sub = sb; seed = s;
endfunction
function int kk(); return (kind == 14) ? 0 : (kind == 15) ? 2 : kind; endfunction
// derived from the monitored flits (for coverage)
function int n_rsp(bit [4:0] op);
  int n = 0;
  foreach (so[i]) if (so[i][71] && so[i][34:30] == op) n++;
  return n;
endfunction
function int n_dat(bit [3:0] op);
  int n = 0;
  foreach (so[i]) if (so[i][312] && so[i][112:109] == op) n++;
  return n;
endfunction
function bit nderr_seen();
  foreach (so[i]) if ((so[i][71] && so[i][36:35] == 2'b11) || (so[i][312] && so[i][114:113] == 2'b11)) return 1;
  return 0;
endfunction
function bit [6:0] errs();
  bit [6:0] e = 0;
  foreach (so[i]) e |= so[i][321:315];
  return e;
endfunction
function bit cancel_seen();
  foreach (mo[i]) if (mo[i][378] && mo[i][178:175] == 4'h7) return 1;
  return 0;
endfunction
function bit dmt_seen();
  foreach (so[i]) if (so[i][312] && so[i][112:109] == 4'h4 && so[i][82:76] != 7'h05) return 1;
  return 0;
endfunction
// request sizes seen: bit s set for a ReadNoSnp / WriteNoSnp* of Size s
function bit [7:0] sizes();
  bit [7:0] m = 0;
  foreach (mo[i]) if (mo[i][137] && !mo[i][57] && mo[i][63:61] == 0) m[mo[i][60:58]] = 1;
  return m;
endfunction
""",
    drv_rsp=False,
    drv_members="""int        rq_cr = 4, dt_cr = 4;       // L-credits the SN granted us (all 4 by the first item)
int        sn_rs = 0, sn_dt = 0;       // L-credits we granted the SN
int        ovf = 0;                    // extra RSP credits to grant (overflow test)
bit [136:0] req_q [$];
bit        req_force [$];              // send even without an L-credit
bit [239:0] dat_q [$];
bit [239:0] wq_pk [$];                 // write packets waiting for CompDBIDResp
bit        wq_bad [$];                 // that packet goes out with a wrong TxnID
int        wq_n [$];                   // packets per write, in request order
bit [31:0] rs = 32'h1;
bit        first = 1;
chih_transaction cur;""",
    drv_tasks="""
function bit [31:0] rnd();
  rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5;
  return rs;
endfunction
function bit [127:0] rnd128(); return {rnd(), rnd(), rnd(), rnd()}; endfunction
// one clock: drive the HN side, then look at what the SN sent
task automatic clk1(output bit act);
  bit rv = 0, dv = 0, rc = 0, dc = 0;
  bit [136:0] rf = '0;
  bit [239:0] df = '0;
  if (req_q.size() && (rq_cr > 0 || req_force[0])) begin
    rf = req_q.pop_front(); void'(req_force.pop_front()); rv = 1; rq_cr--;
  end
  if (dat_q.size() && dt_cr > 0) begin df = dat_q.pop_front(); dv = 1; dt_cr--; end
  if (ovf > 0) begin rc = 1; ovf--; if (sn_rs < 15) sn_rs++; end
  else if (sn_rs < 2) begin rc = 1; sn_rs++; end
  if (sn_dt < 2) begin dc = 1; sn_dt++; end
  vif.drv_cb.rxreqflitv <= rv; vif.drv_cb.rxreqflit <= rf;
  vif.drv_cb.rxdatflitv <= dv; vif.drv_cb.rxdatflit <= df;
  vif.drv_cb.txrsplcrdv <= rc; vif.drv_cb.txdatlcrdv <= dc;
  cur.mo.push_back({dc, rc, dv, df, rv, rf});
  @(vif.drv_cb);
  act = rv | dv | rc | dc;
  if (vif.drv_cb.rxreqlcrdv === 1'b1) begin rq_cr++; act = 1; end
  if (vif.drv_cb.rxdatlcrdv === 1'b1) begin dt_cr++; act = 1; end
  if (vif.drv_cb.txdatflitv === 1'b1) begin sn_dt--; act = 1; end
  if (vif.drv_cb.txrspflitv === 1'b1) begin
    bit [70:0] f = vif.drv_cb.txrspflit;
    sn_rs--; act = 1;
    if (f[34:30] == CHIH_RSP_COMPDBID && wq_n.size()) begin
      int n = wq_n.pop_front();
      repeat (n) begin
        bit [239:0] p = wq_pk.pop_front();
        bit b = wq_bad.pop_front();
        p[10:4] = f[17:11];
        p[29:18] = b ? (f[57:46] ^ 12'h001) : f[57:46];
        dat_q.push_back(p);
        if (b) begin p[29:18] = f[57:46]; dat_q.push_back(p); end   // then the right one
      end
    end
  end
endtask
task automatic quiet();
  int q = 0;
  bit a;
  while (q < cfg.gap) begin clk1(a); q = a ? 0 : q + 1; end
endtask
function void mkreq(bit [6:0] op, bit [43:0] a, bit [2:0] sz, bit [11:0] tx, bit d = 0, bit [1:0] o = 0,
                  bit [6:0] tgt = CHIH_SN, bit [3:0] ma = 4'b0101, bit mr = 0, bit [2:0] hi = 0, bit force_ = 0);
  chih_req_t r;
  r.tgt = tgt; r.src = CHIH_HN; r.txn = tx; r.rnid = d ? CHIH_RN : CHIH_HN; r.rtxn = d ? (tx ^ 12'hA5A) : tx;
  r.op = op; r.mreq = mr; r.nreq = {hi, sz}; r.addr = a; r.order = o; r.memattr = ma;
  req_q.push_back(chih_req(r));
  req_force.push_back(force_);
endfunction
// write data packets for Addr / Size; mode 0 random BE (Ptl), 1 all BE (Full),
// 2 cancel, 3 BE only at or above Addr (Device), 4.. broken (see drv_item)
function void wdata(bit [43:0] a, bit [2:0] sz, int mode, int bad = -1);
  int n = chih_npk(sz), d0 = chih_did0(a[5:0], sz);
  for (int k = 0; k < n; k++) begin
    int d = d0 + k;
    bit [15:0] be = 0;
    bit [127:0] dt = rnd128();
    bit [239:0] p = '0;
    for (int b = 0; b < 16; b++) begin
      bit w = chih_in_win(a[5:0], sz, d, b);
      case (mode)
        0: be[b] = w && rnd()[0];
        1: be[b] = w;
        3: be[b] = w && (d * 16 + b >= a[5:0]) && rnd()[0];
        default: be[b] = 0;
      endcase
      if (!be[b]) dt[8*b +: 8] = 8'h00;
    end
    if (k == 0) case (bad)
      0: be[15 - (a[3:0] == 4'hF)] = 1;                          // probably outside the window
      1: dt[8 * (be[0] ? 1 : 0) +: 8] = 8'h5A;                   // data under BE = 0 (if that BE is 0)
      2: be[d * 16 >= (a[5:0] & ~((1 << sz) - 1)) ? 0 : 15] = 0; // Full without every BE
      3: be[0] = 1;                                              // cancel with a BE
      default: ;
    endcase
    p[17:11] = CHIH_HN;
    p[40:37] = (mode == 2) ? CHIH_DAT_CANCEL : CHIH_DAT_NCBWR;
    p[75:74] = a[5:4]; p[77:76] = d; p[111:96] = be; p[239:112] = dt;
    wq_pk.push_back(p);
    wq_bad.push_back(bad == 4 && k == 0);
  end
  wq_n.push_back(n);
endfunction
""",
    drv_desc="one item per scenario: REQ flits (ReadNoSnp / WriteNoSnp* or a broken request) under L-credits, the write data "
             "after each CompDBIDResp, L-credits granted back to the SN for its RSP / DAT flits, then cfg.gap quiet clocks",
    drv_idle="""
vif.drv_cb.rxreqflitv <= 1'b0; vif.drv_cb.rxreqflit <= '0;
vif.drv_cb.rxdatflitv <= 1'b0; vif.drv_cb.rxdatflit <= '0;
vif.drv_cb.txrsplcrdv <= 1'b0; vif.drv_cb.txdatlcrdv <= 1'b0;
""",
    drv_item="""
bit a;
bit [43:0] ad = {34'h0, t.addr};
bit [2:0] sz = (t.size > 6) ? 3'd6 : t.size;
cur = t;
t.mo.delete();
// the 4 idle clocks after reset (run_phase) open the first item, as the monitor sees them
if (first) begin repeat (4) t.mo.push_back('0); first = 0; end
rs = t.seed ^ 32'h9E37_79B9;
if (rs == 0) rs = 1;
case (t.kk())
  0: mkreq(CHIH_READ_NOSNP, ad, sz, t.txn, t.dmt, t.ord ? 2'b01 : 2'b00);
  1: begin mkreq(CHIH_WRITE_FULL, ad, 3'd6, t.txn); wdata(ad, 3'd6, 1); end
  2: begin
    mkreq(CHIH_WRITE_PTL, ad, sz, t.txn, 0, 0, CHIH_SN, t.sub[0] ? 4'b0010 : 4'b0101);
    wdata(ad, sz, t.sub[0] ? 3 : 0);
  end
  3: begin mkreq(CHIH_WRITE_PTL, ad, sz, t.txn); wdata(ad, sz, 2); end
  4: mkreq(CHIH_READ_NOSNP, ad | 44'h400 << t.sub, sz, t.txn, t.dmt);
  5: begin mkreq(CHIH_WRITE_FULL, ad | 44'h800_0000_0000 >> t.sub, 3'd6, t.txn); wdata(ad, 3'd6, 1); end
  6: for (int i = 0; i < 4; i++) mkreq(CHIH_READ_NOSNP, ad ^ (i << 6), 3'(4 + i % 3), t.txn + i, i[0], i[1] ? 2'b01 : 2'b00);
  7: for (int i = 0; i < 6; i++) mkreq(CHIH_READ_NOSNP, ad ^ (i << 6), 3'd6, t.txn + i, 0, 0, CHIH_SN, 4'b0101, 0, 0, 1);
  8: mkreq(CHIH_READ_NOSNP, ad, sz, t.txn, 0, 0, CHIH_SN ^ 7'(1 + t.sub));
  9: mkreq((t.sub[1:0] == 0) ? 7'h01 : (t.sub[1:0] == 1) ? 7'h19 : (t.sub[1:0] == 2) ? 7'h44 : 7'h3A, ad, sz, t.txn);
  10: case (t.sub % 5)
    0: mkreq(CHIH_READ_NOSNP, ad, sz, t.txn, 0, 0, CHIH_SN, 4'b0101, 1);           // MultiReq
    1: mkreq(CHIH_READ_NOSNP, ad, sz, t.txn, 0, 0, CHIH_SN, 4'b0101, 0, 3'b100);   // NumReq bits of {3'b0, Size}
    2: mkreq(CHIH_READ_NOSNP, ad, 3'd7, t.txn);                                    // Size 128 bytes
    3: mkreq(CHIH_READ_NOSNP, ad, sz, t.txn, 0, t.sub[0] ? 2'b10 : 2'b11);         // reserved Order
    default: mkreq(CHIH_WRITE_FULL, ad, (sz == 6) ? 3'd5 : sz, t.txn);             // Full, Size != 6
  endcase
  11: begin
    int b = t.sub % 5;
    bit full = (b == 2);
    mkreq(full ? CHIH_WRITE_FULL : CHIH_WRITE_PTL, ad, full ? 3'd6 : sz, t.txn);
    wdata(ad, full ? 3'd6 : sz, (b == 2) ? 1 : (b == 3) ? 2 : 0, b);
  end
  12: ovf = 17;
  13: begin
    mkreq(CHIH_WRITE_FULL, ad, 3'd6, t.txn); wdata(ad, 3'd6, 1);
    mkreq(CHIH_WRITE_PTL, ad | 44'h10, 3'd4, t.txn + 1); wdata(ad | 44'h10, 3'd4, 0);
    mkreq(CHIH_READ_NOSNP, ad, 3'd6, t.txn + 2);
  end
  default: ;
endcase
while (req_q.size() || dat_q.size() || wq_n.size() || ovf > 0) begin
  int w = 0;
  clk1(a);
  if (++w > 400 && wq_n.size()) begin wq_n.delete(); wq_pk.delete(); wq_bad.delete(); end
end
quiet();
// at a quiet point every L-credit is back where it started
rq_cr = 4; dt_cr = 4;
""",
    mon_desc="every clock's flits and L-credits; an item starts at the first flit or credit and ends after cfg.gap "
             "quiet clocks",
    mon_run="""
// the SN acts on its own from the first clock after reset (it grants L-credits),
// so every clock from there on belongs to some item
bit started = 1;
bit [380:0] pend_mo [$];
bit [321:0] pend_so [$];
wait (vif.rst_n === 1'b1);
forever begin
  chih_transaction t = null;
  int q = 0;
  forever begin
    bit [380:0] m;
    bit [321:0] o;
    bit act;
    @(vif.mon_cb);
    m = {vif.mon_cb.txdatlcrdv, vif.mon_cb.txrsplcrdv, vif.mon_cb.rxdatflitv, vif.mon_cb.rxdatflit,
         vif.mon_cb.rxreqflitv, vif.mon_cb.rxreqflit};
    o = {vif.mon_cb.err, vif.mon_cb.rxdatlcrdv, vif.mon_cb.rxreqlcrdv, vif.mon_cb.txdatflitv, vif.mon_cb.txdatflit,
         vif.mon_cb.txrspflitv, vif.mon_cb.txrspflit};
    act = m[380] | m[379] | m[378] | m[137] | o[314] | o[313] | o[312] | o[71];
    if (t == null && act) begin
      t = chih_transaction::type_id::create("t");
      if (started) begin t.mo = pend_mo; t.so = pend_so; end
      pend_mo.delete(); pend_so.delete();
      started = 1;
    end
    if (t == null) begin
      if (started) begin pend_mo.push_back(m); pend_so.push_back(o); end
    end else begin
      t.mo.push_back(m); t.so.push_back(o);
      q = act ? 0 : q + 1;
    end
    if (t != null && q == cfg.gap) break;
  end
  publish(t);
end
""",
    sb_members="""// the SN-F (scoreboard copy), kept across items
bit [7:0]   mem [1024];
int         rq_out = 0, rq_give = 4, dt_out = 0, dt_give = 4, rs_cr = 0, dd_cr = 0;
bit [136:0] fifo [$];
int         st = 0, k = 0, n = 0, d0 = 0;      // 0 idle, 1 ReadReceipt, 2 CompData, 3 CompDBIDResp, 4 write data
bit [136:0] c;
bit [11:0]  dbid = 12'hFF0;
bit [3:0]   got = 0, need = 0;
bit         o_rq = 0, o_dt = 0, o_rv = 0, o_dv = 0;
bit [70:0]  o_rf = 0;
bit [239:0] o_df = 0;
bit [6:0]   o_err = 0;
function void step(bit [380:0] m);
  bit [136:0] rf = m[136:0];
  bit [239:0] df = m[377:138];
  bit rv = m[137], dv = m[378], rc = m[379], dc = m[380];
  bit n_rq = 0, n_dt = 0, n_rv = 0, n_dv = 0;
  bit [70:0] n_rf = 0;
  bit [239:0] n_df = 0;
  bit [6:0] e = 0;
  bit oob = c[107:74] != 0;
  if (rc) begin if (rs_cr == 15) e[6] = 1; else rs_cr++; end
  if (dc) begin if (dd_cr == 15) e[6] = 1; else dd_cr++; end
  if (rv) begin if (rq_out == 0) e[0] = 1; else begin rq_out--; fifo.push_back(rf); end end
  if (dv) begin
    if (dt_out == 0) e[0] = 1;
    else begin
      int d = df[77:76];
      bit [2:0] sz = c[60:58];
      dt_out--; dt_give++;
      if (st != 4 || df[10:4] != CHIH_SN || df[29:18] != dbid || !(df[40:37] inside {CHIH_DAT_NCBWR, CHIH_DAT_CANCEL})
          || !need[d] || got[d]) e[5] = 1;
      else begin
        bit bad = 0;
        bit [15:0] be = df[111:96];
        for (int b = 0; b < 16; b++) begin
          bit w = chih_in_win(c[69:64], sz, d, b);
          if (be[b] && !w) bad = 1;
          if (!be[b] && df[112 + 8 * b +: 8] != 0) bad = 1;
          if (c[56:50] == CHIH_WRITE_FULL && df[40:37] == CHIH_DAT_NCBWR && w && !be[b]) bad = 1;
          if (df[40:37] == CHIH_DAT_CANCEL && be[b]) bad = 1;
          if (c[56:50] == CHIH_WRITE_PTL && c[120] && be[b] && d * 16 + b < c[69:64]) bad = 1;
        end
        if (bad) e[4] = 1;
        else if (!oob && df[40:37] == CHIH_DAT_NCBWR)
          for (int b = 0; b < 16; b++) if (be[b]) mem[{c[73:70], 6'(d * 16 + b)}] = df[112 + 8 * b +: 8];
        got[d] = 1;
        if (got == need) begin st = 0; dbid++; end
      end
    end
  end
  case (st)
    0: if (fifo.size()) begin
      c = fifo.pop_front();
      rq_give++;
      oob = c[107:74] != 0;
      if (c[10:4] != CHIH_SN) e[1] = 1;
      else if (!(c[56:50] inside {CHIH_READ_NOSNP, CHIH_WRITE_PTL, CHIH_WRITE_FULL})) e[3] = 1;
      else if (c[57] || c[63:61] != 0 || c[60:58] == 7 || c[114] || (c[56:50] == CHIH_WRITE_FULL && c[60:58] != 6)) e[2] = 1;
      else begin
        n = chih_npk(c[60:58]); d0 = chih_did0(c[69:64], c[60:58]); k = 0;
        need = 0; got = 0;
        for (int i = 0; i < n; i++) need[d0 + i] = 1;
        if (c[56:50] == CHIH_READ_NOSNP) st = (c[114:113] == 2'b01) ? 1 : 2;
        else st = 3;
      end
    end
    1: if (rs_cr > 0) begin
      rs_cr--; n_rv = 1; n_rf = chih_rsp(c[17:11], c[29:18], CHIH_RSP_RRECEIPT, 2'b00, 12'h0); st = 2;
    end
    2: if (dd_cr > 0) begin
      bit [15:0] be = 0;
      bit [127:0] d = 0;
      int di = d0 + k;
      for (int b = 0; b < 16; b++) begin
        be[b] = chih_in_win(c[69:64], c[60:58], di, b);
        if (!oob) d[8 * b +: 8] = mem[{c[73:70], 6'(di * 16 + b)}];
      end
      dd_cr--; n_dv = 1;
      n_df = chih_dat(c[36:30], CHIH_SN, c[49:38], c[17:11], CHIH_DAT_COMPDATA, oob ? 2'b11 : 2'b00, 3'b010,
                      c[29:18], c[69:68], 2'(di), be, d);
      k++;
      if (k == n) st = 0;
    end
    3: if (rs_cr > 0) begin
      rs_cr--; n_rv = 1; n_rf = chih_rsp(c[17:11], c[29:18], CHIH_RSP_COMPDBID, oob ? 2'b11 : 2'b00, dbid); st = 4;
    end
    default: ;
  endcase
  if (rq_give > 0) begin n_rq = 1; rq_give--; rq_out++; end
  if (dt_give > 0) begin n_dt = 1; dt_give--; dt_out++; end
  o_rq = n_rq; o_dt = n_dt; o_rv = n_rv; o_rf = n_rf; o_dv = n_dv; o_df = n_df; o_err = e;
endfunction
""",
    predict="""
t.so.delete();
foreach (t.mo[i]) begin
  t.so.push_back({o_err, o_dt, o_rq, o_dv, o_df, o_rv, o_rf});
  step(t.mo[i]);
end
""",
    checks="""
if (t.mo.size() == 0) fail(t, "empty item");
""",
    coverage="""
cp_e0    : coverpoint tr.errs()[0];
cp_e1    : coverpoint tr.errs()[1];
cp_e2    : coverpoint tr.errs()[2];
cp_e3    : coverpoint tr.errs()[3];
cp_e4    : coverpoint tr.errs()[4];
cp_e5    : coverpoint tr.errs()[5];
cp_e6    : coverpoint tr.errs()[6];
cp_rr    : coverpoint tr.n_rsp(5'h08) { bins none = {0}; bins some = {[1:$]}; }
cp_dbid  : coverpoint tr.n_rsp(5'h05) { bins none = {0}; bins one = {1}; bins more = {[2:$]}; }
cp_cdata : coverpoint tr.n_dat(4'h4) { bins none = {0}; bins one = {1}; bins two = {2}; bins four = {[4:$]}; }
cp_nderr : coverpoint tr.nderr_seen();
cp_cncl  : coverpoint tr.cancel_seen();
cp_dmt   : coverpoint tr.dmt_seen();
cp_s0    : coverpoint tr.sizes()[0] { bins seen = {1}; }
cp_s3    : coverpoint tr.sizes()[3] { bins seen = {1}; }
cp_s4    : coverpoint tr.sizes()[4] { bins seen = {1}; }
cp_s5    : coverpoint tr.sizes()[5] { bins seen = {1}; }
cp_s6    : coverpoint tr.sizes()[6] { bins seen = {1}; }
""",
    directed="""
// every request type and size, DMT, ReadReceipt, write data rules, every error
t = item(); t.set(1, 6, 10'h040, 12'hABC, 0, 0, 0, 32'h11); send(t);       // WriteNoSnpFull, 12-bit TxnID
t = item(); t.set(0, 6, 10'h040, 12'hF01, 0, 0); send(t);                   // read it back
t = item(); t.set(0, 6, 10'h040, 12'h123, 1, 1); send(t);                   // DMT + ReadReceipt
for (int s = 0; s <= 6; s++) begin
  t = item(); t.set(2, s, 10'h080 + 10'(s * 9), 12'h200 + s, 0, 0, 0, 32'h20 + s); send(t);   // Ptl, every size
  t = item(); t.set(0, s, 10'h080 + 10'(s * 9), 12'h300 + s, s % 2, (s % 3) == 0); send(t);
end
t = item(); t.set(2, 6, 10'h0D3, 12'h400, 0, 0, 1, 32'h31); send(t);       // Device: BE at or above Addr
t = item(); t.set(3, 5, 10'h120, 12'h401, 0, 0, 0, 32'h32); send(t);       // cancelled
t = item(); t.set(0, 5, 10'h120, 12'h402); send(t);
t = item(); t.set(4, 6, 10'h000, 12'h403, 1, 0, 2); send(t);               // NDERR read
t = item(); t.set(5, 6, 10'h1C0, 12'h404, 0, 0, 3, 32'h33); send(t);       // NDERR write
t = item(); t.set(6, 6, 10'h200, 12'h410); send(t);                         // four reads
t = item(); t.set(7, 6, 10'h240, 12'h420); send(t);                         // without L-credits
t = item(); t.set(0, 6, 10'h240, 12'h430); send(t);
for (int s = 0; s < 4; s++) begin t = item(); t.set(8, 4, 10'h010, 12'h440 + s, 0, 0, s); send(t); end
for (int s = 0; s < 4; s++) begin t = item(); t.set(9, 4, 10'h010, 12'h450 + s, 0, 0, s); send(t); end
for (int s = 0; s < 6; s++) begin t = item(); t.set(10, 6, 10'h010, 12'h460 + s, 0, 0, s); send(t); end
for (int s = 0; s < 5; s++) begin
  t = item(); t.set(11, (s == 1) ? 4 : 5, (s == 0) ? 10'h305 : 10'h300, 12'h470 + s, 0, 0, s, 32'h40 + s); send(t);
end
t = item(); t.set(12); send(t);                                            // credit overflow
t = item(); t.set(13, 6, 10'h3C0, 12'hFFE, 0, 0, 0, 32'h55); send(t);      // write + read, DBID wraps
t = item(); t.set(0, 3, 10'h3C8, 12'h7FF); send(t);
""",
    drain_ns=2000,
    model="""
module chih_model #(
  parameter logic [6:0] NID = 7'h20
) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         rxreqflitv,
  input  logic [136:0] rxreqflit,
  output logic         rxreqlcrdv,
  input  logic         rxdatflitv,
  input  logic [239:0] rxdatflit,
  output logic         rxdatlcrdv,
  output logic         txrspflitv,
  output logic [70:0]  txrspflit,
  input  logic         txrsplcrdv,
  output logic         txdatflitv,
  output logic [239:0] txdatflit,
  input  logic         txdatlcrdv,
  output logic [6:0]   err
);
  // REQ fields used (Table B13.6, NodeID_Width 7, Req_Addr_Width 44)
  `define RQ_TGT(f)   f[10:4]
  `define RQ_SRC(f)   f[17:11]
  `define RQ_TXN(f)   f[29:18]
  `define RQ_RNID(f)  f[36:30]
  `define RQ_RTXN(f)  f[49:38]
  `define RQ_OP(f)    f[56:50]
  `define RQ_MREQ(f)  f[57]
  `define RQ_SIZE(f)  f[60:58]
  `define RQ_NRQHI(f) f[63:61]
  `define RQ_ADDR(f)  f[107:64]
  `define RQ_ORDER(f) f[114:113]
  `define RQ_DEV(f)   f[120]

  logic [7:0]   mem [0:1023];
  logic [136:0] fq [0:3];
  integer       fr, fc;                      // FIFO read index, count
  integer       rq_out, rq_give, dt_out, dt_give, rs_cr, dd_cr;
  integer       st, k, n, d0, di, o, b, bs;
  logic [136:0] c;
  logic [11:0]  dbid;
  logic [3:0]   got, need;
  logic         oob, bad, w;
  logic [6:0]   e;
  logic [15:0]  be;
  logic [127:0] dd;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 1024; i++) mem[i] = 8'h00;
      fr = 0; fc = 0; rq_out = 0; rq_give = 4; dt_out = 0; dt_give = 4; rs_cr = 0; dd_cr = 0;
      st = 0; k = 0; n = 0; d0 = 0; c = '0; dbid = 12'hFF0; got = '0; need = '0;
      rxreqlcrdv <= 1'b0; rxdatlcrdv <= 1'b0; txrspflitv <= 1'b0; txrspflit <= '0;
      txdatflitv <= 1'b0; txdatflit <= '0; err <= '0;
    end else begin
      e = '0;
      txrspflitv <= 1'b0; txrspflit <= '0; txdatflitv <= 1'b0; txdatflit <= '0;
      // L-credits from the HN
      if (txrsplcrdv) begin if (rs_cr == 15) e[6] = 1'b1; else rs_cr = rs_cr + 1; end
      if (txdatlcrdv) begin if (dd_cr == 15) e[6] = 1'b1; else dd_cr = dd_cr + 1; end
      // REQ flit in
      if (rxreqflitv) begin
        if (rq_out == 0) e[0] = 1'b1;
        else begin rq_out = rq_out - 1; fq[(fr + fc) % 4] = rxreqflit; fc = fc + 1; end
      end
      // DAT flit in
      oob = (`RQ_ADDR(c) >= 44'd1024);
      if (rxdatflitv) begin
        if (dt_out == 0) e[0] = 1'b1;
        else begin
          dt_out = dt_out - 1; dt_give = dt_give + 1;
          di = rxdatflit[77:76];
          if (st != 4 || rxdatflit[10:4] != NID || rxdatflit[29:18] != dbid ||
              (rxdatflit[40:37] != 4'h3 && rxdatflit[40:37] != 4'h7) || !need[di] || got[di]) e[5] = 1'b1;
          else begin
            bad = 1'b0;
            be = rxdatflit[111:96];
            bs = `RQ_ADDR(c) & ~((1 << `RQ_SIZE(c)) - 1);
            bs = bs % 64;
            for (b = 0; b < 16; b = b + 1) begin
              o = di * 16 + b;
              w = (o >= bs) && (o < bs + (1 << `RQ_SIZE(c)));
              if (be[b] && !w) bad = 1'b1;
              if (!be[b] && rxdatflit[112 + 8 * b +: 8] != 8'h00) bad = 1'b1;
              if (`RQ_OP(c) == 7'h1D && rxdatflit[40:37] == 4'h3 && w && !be[b]) bad = 1'b1;
              if (rxdatflit[40:37] == 4'h7 && be[b]) bad = 1'b1;
              if (`RQ_OP(c) == 7'h1C && `RQ_DEV(c) && be[b] && o < `RQ_ADDR(c) % 64) bad = 1'b1;
            end
            if (bad) e[4] = 1'b1;
            else if (!oob && rxdatflit[40:37] == 4'h3)
              for (b = 0; b < 16; b = b + 1)
                if (be[b]) mem[`RQ_ADDR(c) / 64 % 16 * 64 + di * 16 + b] = rxdatflit[112 + 8 * b +: 8];
            got[di] = 1'b1;
            if (got == need) begin st = 0; dbid = dbid + 12'd1; end
          end
        end
      end
      // the request engine
      case (st)
        0: if (fc > 0) begin
          c = fq[fr]; fr = (fr + 1) % 4; fc = fc - 1;
          rq_give = rq_give + 1;
          if (`RQ_TGT(c) != NID) e[1] = 1'b1;
          else if (`RQ_OP(c) != 7'h04 && `RQ_OP(c) != 7'h1C && `RQ_OP(c) != 7'h1D) e[3] = 1'b1;
          else if (`RQ_MREQ(c) || `RQ_NRQHI(c) != 3'd0 || `RQ_SIZE(c) == 3'd7 || `RQ_ORDER(c) >= 2'b10 ||
                   (`RQ_OP(c) == 7'h1D && `RQ_SIZE(c) != 3'd6)) e[2] = 1'b1;
          else begin
            n = (`RQ_SIZE(c) <= 4) ? 1 : (1 << (`RQ_SIZE(c) - 4));
            d0 = (`RQ_SIZE(c) == 6) ? 0 : ((`RQ_ADDR(c) % 64) & ~((1 << `RQ_SIZE(c)) - 1)) / 16;
            k = 0; got = '0; need = '0;
            for (int i = 0; i < 4; i++) if (i >= d0 && i < d0 + n) need[i] = 1'b1;
            if (`RQ_OP(c) == 7'h04) st = (`RQ_ORDER(c) == 2'b01) ? 1 : 2;
            else st = 3;
          end
        end
        1: if (rs_cr > 0) begin       // ReadReceipt
          rs_cr = rs_cr - 1;
          txrspflitv <= 1'b1;
          txrspflit <= {7'h0, 4'h0, 2'b00, 12'h000, 3'b000, 3'b000, 3'b000, 2'b00, 5'h08, `RQ_TXN(c), NID, `RQ_SRC(c), 4'h0};
          st = 2;
        end
        2: if (dd_cr > 0) begin       // CompData_UC to ReturnNID / ReturnTxnID
          oob = (`RQ_ADDR(c) >= 44'd1024);
          di = d0 + k;
          bs = (`RQ_ADDR(c) % 64) & ~((1 << `RQ_SIZE(c)) - 1);
          for (b = 0; b < 16; b = b + 1) begin
            o = di * 16 + b;
            be[b] = (o >= bs) && (o < bs + (1 << `RQ_SIZE(c)));
            dd[8 * b +: 8] = oob ? 8'h00 : mem[`RQ_ADDR(c) / 64 % 16 * 64 + o];
          end
          dd_cr = dd_cr - 1;
          txdatflitv <= 1'b1;
          txdatflit <= {dd, be, 1'b0, 2'b00, 1'b0, 1'b0, 1'b0, 4'h0, 2'b00, 6'h00, di[1:0], c[69:68],
                        4'h0, `RQ_TXN(c), 3'b000, 1'b0, 8'h00, 3'b010, (oob ? 2'b11 : 2'b00), 4'h4,
                        `RQ_SRC(c), `RQ_RTXN(c), NID, `RQ_RNID(c), 4'h0};
          k = k + 1;
          if (k == n) st = 0;
        end
        3: if (rs_cr > 0) begin       // CompDBIDResp
          oob = (`RQ_ADDR(c) >= 44'd1024);
          rs_cr = rs_cr - 1;
          txrspflitv <= 1'b1;
          txrspflit <= {7'h0, 4'h0, 2'b00, dbid, 3'b000, 3'b000, 3'b000, (oob ? 2'b11 : 2'b00), 5'h05, `RQ_TXN(c),
                        NID, `RQ_SRC(c), 4'h0};
          st = 4;
        end
        default: ;
      endcase
      // L-credits back to the HN
      rxreqlcrdv <= 1'b0; rxdatlcrdv <= 1'b0;
      if (rq_give > 0) begin rxreqlcrdv <= 1'b1; rq_give = rq_give - 1; rq_out = rq_out + 1; end
      if (dt_give > 0) begin rxdatlcrdv <= 1'b1; dt_give = dt_give - 1; dt_out = dt_out + 1; end
      err <= e;
    end
  end
  `undef RQ_TGT
  `undef RQ_SRC
  `undef RQ_TXN
  `undef RQ_RNID
  `undef RQ_RTXN
  `undef RQ_OP
  `undef RQ_MREQ
  `undef RQ_SIZE
  `undef RQ_NRQHI
  `undef RQ_ADDR
  `undef RQ_ORDER
  `undef RQ_DEV
endmodule
""",
    sva="""
// outputs are never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({rxreqlcrdv, rxdatlcrdv, txrspflitv, txdatflitv, err}))
  else $error("CHI-H: X on a valid / credit / err output");
// a protocol flit has a non-zero opcode (B13.10)
assert property (@(posedge clk) disable iff (!rst_n) txrspflitv |-> txrspflit[34:30] != 5'h00)
  else $error("CHI-H: RSP flit with opcode 0");
assert property (@(posedge clk) disable iff (!rst_n) txdatflitv |-> txdatflit[40:37] != 4'h0)
  else $error("CHI-H: DAT flit with opcode 0");
// the SN's flits come from the SN, and DBID's upper 4 bits in DAT are MBZ (Table B13.9)
assert property (@(posedge clk) disable iff (!rst_n) txrspflitv |-> txrspflit[17:11] == 7'h20)
  else $error("CHI-H: RSP SrcID is not the SN");
assert property (@(posedge clk) disable iff (!rst_n) txdatflitv |-> txdatflit[17:11] == 7'h20 && txdatflit[73:70] == 4'h0)
  else $error("CHI-H: DAT SrcID / DBID MBZ bits");
// CompData is UC (Table B4.38) and its CCID names the critical chunk (B2.9.7)
assert property (@(posedge clk) disable iff (!rst_n) txdatflitv |-> txdatflit[40:37] == 4'h4 && txdatflit[45:43] == 3'b010)
  else $error("CHI-H: SN data that is not CompData_UC");
// the errors the tests cause on purpose: covers
cover property (@(posedge clk) disable iff (!rst_n) err[0]);
cover property (@(posedge clk) disable iff (!rst_n) err[1]);
cover property (@(posedge clk) disable iff (!rst_n) err[2]);
cover property (@(posedge clk) disable iff (!rst_n) err[3]);
cover property (@(posedge clk) disable iff (!rst_n) err[4]);
cover property (@(posedge clk) disable iff (!rst_n) err[5]);
cover property (@(posedge clk) disable iff (!rst_n) err[6]);
cover property (@(posedge clk) disable iff (!rst_n) txrspflitv && txrspflit[34:30] == 5'h08);
cover property (@(posedge clk) disable iff (!rst_n) txdatflitv && txdatflit[42:41] == 2'b11);
""",
    smoke=r"""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic         rxreqflitv = 1'b0, rxdatflitv = 1'b0, rsp_cr = 1'b0, dat_cr = 1'b0, rsp_extra = 1'b0, dat_extra = 1'b0;
logic [136:0] rxreqflit = '0;
logic [239:0] rxdatflit = '0;
wire          rxreqlcrdv, rxdatlcrdv, txrspflitv, txdatflitv;
wire  [70:0]  txrspflit;
wire  [239:0] txdatflit;
wire  [6:0]   err;
wire          txrsplcrdv = rsp_cr | rsp_extra;
wire          txdatlcrdv = dat_cr | dat_extra;

always #5 clk = ~clk;

chih_model u_dut (.clk(clk), .rst_n(rst_n), .rxreqflitv(rxreqflitv), .rxreqflit(rxreqflit), .rxreqlcrdv(rxreqlcrdv),
                  .rxdatflitv(rxdatflitv), .rxdatflit(rxdatflit), .rxdatlcrdv(rxdatlcrdv), .txrspflitv(txrspflitv),
                  .txrspflit(txrspflit), .txrsplcrdv(txrsplcrdv), .txdatflitv(txdatflitv), .txdatflit(txdatflit),
                  .txdatlcrdv(txdatlcrdv), .err(err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// the HN side of the link: credits it holds, credits it gives back, what it received
// the SN gets one RSP and one DAT credit and one back per flit: it never holds more than 1
integer req_cr = 0, dat_cr_n = 0, give_rsp = 1, give_dat = 1;
logic [70:0]  rsp_log [0:63];
logic [239:0] dat_log [0:63];
integer nrsp = 0, ndat = 0;
integer e_seen [0:6];
always @(posedge clk) begin
  if (rxreqlcrdv) req_cr = req_cr + 1;
  if (rxdatlcrdv) dat_cr_n = dat_cr_n + 1;
  if (txrspflitv) begin rsp_log[nrsp % 64] = txrspflit; nrsp = nrsp + 1; give_rsp = give_rsp + 1; end
  if (txdatflitv) begin dat_log[ndat % 64] = txdatflit; ndat = ndat + 1; give_dat = give_dat + 1; end
  for (int i = 0; i < 7; i++) if (err[i]) e_seen[i] = e_seen[i] + 1;
end
// return the SN's TX credits one per clock
always @(negedge clk) begin
  rsp_cr = 1'b0; dat_cr = 1'b0;
  if (rst_n && give_rsp > 0) begin rsp_cr = 1'b1; give_rsp = give_rsp - 1; end
  if (rst_n && give_dat > 0) begin dat_cr = 1'b1; give_dat = give_dat - 1; end
end
task automatic clr(); for (int i = 0; i < 7; i++) e_seen[i] = 0; nrsp = 0; ndat = 0; endtask
function automatic bit no_err(); no_err = (e_seen[0] + e_seen[1] + e_seen[2] + e_seen[3] + e_seen[4] + e_seen[5] + e_seen[6]) == 0; endfunction
task automatic idle(input integer n); repeat (n) @(posedge clk); #1; endtask

// a REQ flit, bit positions from Table B13.6
function automatic logic [136:0] mkreq(input logic [6:0] op, input logic [43:0] a, input logic [2:0] size,
                                       input logic [11:0] txn, input logic [6:0] rnid = 7'h05, input logic [11:0] rtxn = 12'hFFF,
                                       input logic [1:0] order = 2'b00, input logic [6:0] tgt = 7'h20,
                                       input logic [3:0] memattr = 4'b0101);
  logic [136:0] f;
  f = '0;
  f[3:0] = 4'hA;            // QoS: not interpreted
  f[10:4] = tgt; f[17:11] = 7'h05; f[29:18] = txn; f[36:30] = rnid; f[49:38] = (rtxn == 12'hFFF) ? txn : rtxn;
  f[56:50] = op; f[63:58] = {3'b000, size}; f[107:64] = a; f[110:108] = 3'b001; f[114:113] = order;
  f[122:119] = memattr; f[136] = 1'b1;   // TraceTag: not interpreted
  mkreq = f;
endfunction
task automatic send_req(input logic [136:0] f, input bit nocredit = 0);
  @(negedge clk);
  while (!nocredit && req_cr == 0) @(negedge clk);
  if (req_cr > 0) req_cr = req_cr - 1;
  rxreqflitv = 1'b1; rxreqflit = f;
  @(negedge clk);
  rxreqflitv = 1'b0;
endtask
// a write data flit (Table B13.9)
task automatic send_dat(input logic [3:0] op, input logic [11:0] txn, input logic [1:0] did, input logic [15:0] be,
                        input logic [127:0] d, input logic [6:0] tgt = 7'h20, input bit nocredit = 0);
  logic [239:0] f;
  f = '0;
  f[10:4] = tgt; f[17:11] = 7'h05; f[29:18] = txn; f[40:37] = op; f[77:76] = did; f[111:96] = be; f[239:112] = d;
  @(negedge clk);
  while (!nocredit && dat_cr_n == 0) @(negedge clk);
  if (dat_cr_n > 0) dat_cr_n = dat_cr_n - 1;
  rxdatflitv = 1'b1; rxdatflit = f;
  @(negedge clk);
  rxdatflitv = 1'b0;
endtask
function automatic logic [127:0] pat(input integer s);
  pat = {32'(s * 32'h0101_0101 + 32'h1357_9BDF), 32'(s ^ 32'hDEAD_BEEF), 32'(s * 7 + 32'h0BAD_F00D), 32'(~s)};
endfunction
logic [11:0] dbid;
logic [127:0] d;
integer i, n;

initial begin
  clr();
  repeat (3) @(posedge clk);
  #1 chk(rxreqlcrdv === 1'b0 && txrspflitv === 1'b0 && err === 7'h0, "reset: no credits, no flits");
  // a flit in the first clock after reset, before any L-credit: dropped
  @(negedge clk); rst_n = 1;
  rxreqflitv = 1'b1; rxreqflit = mkreq(7'h04, 44'h0, 3'd6, 12'h001);
  rxdatflitv = 1'b1; rxdatflit = '0;
  @(negedge clk); rxreqflitv = 1'b0; rxdatflitv = 1'b0;
  idle(8);
  chk(e_seen[0] == 1 && ndat == 0, "REQ and DAT flits before the first L-credit: dropped (err 0)");
  chk(req_cr == 4 && dat_cr_n == 4, "4 REQ and 4 DAT L-credits granted after reset");

  // WriteNoSnpFull with a 12-bit TxnID: CompDBIDResp, then 4 packets
  clr();
  send_req(mkreq(7'h1D, 44'h040, 3'd6, 12'hABC));
  idle(4);
  chk(nrsp == 1 && rsp_log[0][34:30] == 5'h05 && rsp_log[0][29:18] == 12'hABC && rsp_log[0][10:4] == 7'h05 &&
      rsp_log[0][17:11] == 7'h20 && rsp_log[0][36:35] == 2'b00, "WriteNoSnpFull: CompDBIDResp to SrcID with the 12-bit TxnID");
  dbid = rsp_log[0][57:46];
  chk(dbid == 12'hFF0, "first DBID is the model's start value 0xFF0 (12 bits)");
  for (i = 0; i < 4; i++) send_dat(4'h3, dbid, i, 16'hFFFF, pat(i));
  idle(4);
  chk(no_err(), "full write data accepted");
  chk(dat_cr_n == 4, "one DAT L-credit back per write data flit");
  // read it back: CompData_UC, DataID 0..3, DMT fields
  clr();
  send_req(mkreq(7'h04, 44'h040, 3'd6, 12'h7E1));
  idle(10);
  chk(ndat == 4 && nrsp == 0, "ReadNoSnp of 64 bytes: 4 CompData packets, no RSP");
  for (i = 0; i < 4; i++)
    chk(dat_log[i][40:37] == 4'h4 && dat_log[i][45:43] == 3'b010 && dat_log[i][77:76] == i && dat_log[i][239:112] == pat(i),
        $sformatf("CompData_UC packet %0d: DataID %0d and the written data", i, i));
  chk(dat_log[0][10:4] == 7'h05 && dat_log[0][29:18] == 12'h7E1 && dat_log[0][36:30] == 7'h05 && dat_log[0][73:58] == 16'h07E1,
      "no DMT: TgtID = ReturnNID = SrcID, TxnID = ReturnTxnID, HomeNID = SrcID, DBID = TxnID");
  chk(dat_log[1][3:0] == 4'h0 && dat_log[1][57:46] == 12'h0 && dat_log[1][73:70] == 4'h0 && dat_log[1][95:78] == 18'h0,
      "CompData: QoS, DataSource, DataPull, CBusy, DBID MBZ, CacheLineID, TagOp, Tag, TU, TraceTag, CAH, NumDat, Replicate all 0");
  // DMT with Order = 0b01: ReadReceipt to the HN, data to the requester
  clr();
  send_req(mkreq(7'h04, 44'h050, 3'd4, 12'h123, 7'h11, 12'h9A9, 2'b01));
  idle(6);
  chk(nrsp == 1 && rsp_log[0][34:30] == 5'h08 && rsp_log[0][10:4] == 7'h05 && rsp_log[0][29:18] == 12'h123,
      "Order 0b01: ReadReceipt to SrcID with TxnID");
  chk(ndat == 1 && dat_log[0][10:4] == 7'h11 && dat_log[0][29:18] == 12'h9A9 && dat_log[0][36:30] == 7'h05 &&
      dat_log[0][73:58] == 16'h0123, "DMT: CompData to ReturnNID with ReturnTxnID, HomeNID = SrcID, DBID = TxnID");
  chk(dat_log[0][77:76] == 2'd1 && dat_log[0][75:74] == 2'd1 && dat_log[0][239:112] == pat(1),
      "16-byte read at 0x50: one packet, DataID = CCID = Addr[5:4] = 1");
  chk(dat_log[0][111:96] == 16'hFFFF, "read BE marks the 16-byte data window");
  // packet counts per Size (B2.9.4)
  for (i = 0; i <= 6; i++) begin
    clr();
    send_req(mkreq(7'h04, 44'h06C, i, 12'h200 + i));
    idle(10);
    n = (i <= 4) ? 1 : (1 << (i - 4));
    chk(ndat == n && dat_log[0][77:76] == ((i == 6) ? 0 : (i == 5) ? 2 : 2'd2),
        $sformatf("Size %0d at 0x6C: %0d packet(s) from DataID %0d", i, n, (i == 6) ? 0 : 2));
  end
  clr();
  send_req(mkreq(7'h04, 44'h06C, 3'd2, 12'h210)); idle(8);
  chk(dat_log[0][111:96] == 16'hF000, "Size 2 at 0x6C: BE bytes 12..15 of the packet");
  // WriteNoSnpPtl, 32 bytes at 0x0A0, some BE
  clr();
  send_req(mkreq(7'h1C, 44'h0A0, 3'd5, 12'h301));
  idle(4); dbid = rsp_log[0][57:46];
  chk(dbid == 12'hFF1, "next DBID");
  send_dat(4'h3, dbid, 2, 16'h00FF, {64'h0, 64'h1122_3344_5566_7788});
  send_dat(4'h3, dbid, 3, 16'h8001, {8'hEE, 112'h0, 8'h99});
  idle(3);
  chk(no_err(), "partial write: random BE accepted");
  clr(); send_req(mkreq(7'h04, 44'h080, 3'd6, 12'h302)); idle(10);
  chk(dat_log[2][239:112] == {64'h0, 64'h1122_3344_5566_7788} && dat_log[3][239:112] == {8'hEE, 112'h0, 8'h99},
      "only bytes with BE are written");
  // WriteDataCancel: nothing written, BE must be 0
  clr();
  send_req(mkreq(7'h1C, 44'h080, 3'd4, 12'h303)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h7, dbid, 0, 16'h0000, 128'h0); idle(3);
  chk(no_err(), "WriteDataCancel accepted");
  clr(); send_req(mkreq(7'h04, 44'h080, 3'd4, 12'h304)); idle(8);
  chk(dat_log[0][239:112] == 128'h0 && ndat == 1, "cancelled write left memory alone");
  // Device memory WriteNoSnpPtl: BE below Addr is an error
  clr();
  send_req(mkreq(7'h1C, 44'h0C4, 3'd4, 12'h305, 7'h05, 12'hFFF, 2'b00, 7'h20, 4'b0010)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid, 0, 16'h0008, {96'h0, 8'h77, 24'h0}); idle(3);
  chk(e_seen[4] == 1, "Device WriteNoSnpPtl: BE below Addr breaks B2.9.3");
  clr();
  send_req(mkreq(7'h1C, 44'h0C4, 3'd4, 12'h306, 7'h05, 12'hFFF, 2'b00, 7'h20, 4'b0010)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid, 0, 16'h0030, {80'h0, 16'hABCD, 32'h0}); idle(3);
  chk(no_err(), "Device WriteNoSnpPtl: BE at and above Addr is fine");
  // write data rule breaks
  clr();
  send_req(mkreq(7'h1D, 44'h100, 3'd6, 12'h307)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid, 0, 16'hFFFE, pat(9) & ~128'hFF); for (i = 1; i < 4; i++) send_dat(4'h3, dbid, i, 16'hFFFF, pat(i));
  idle(3);
  chk(e_seen[4] == 1, "WriteNoSnpFull with a byte not enabled: error");
  clr(); send_req(mkreq(7'h04, 44'h100, 3'd4, 12'h308)); idle(8);
  chk(dat_log[0][239:112] == 128'h0, "the broken packet was not written");
  clr();
  send_req(mkreq(7'h1C, 44'h140, 3'd4, 12'h309)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid, 0, 16'h0001, {120'h0, 8'h00} | {8'h01, 120'h0}); idle(3);
  chk(e_seen[4] == 1, "data under BE = 0 must be zero");
  clr();
  send_req(mkreq(7'h1C, 44'h140, 3'd2, 12'h30A)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid, 0, 16'h0010, 128'h0); idle(3);
  chk(e_seen[4] == 1, "BE outside the 4-byte data window");
  clr();
  send_req(mkreq(7'h1C, 44'h140, 3'd4, 12'h30B)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h7, dbid, 0, 16'h0001, 128'h0); idle(3);
  chk(e_seen[4] == 1, "WriteDataCancel with a BE set");
  // unexpected write data
  clr();
  send_dat(4'h3, 12'h123, 0, 16'hFFFF, 128'h0); idle(3);
  chk(e_seen[5] == 1, "write data with no write waiting");
  clr();
  send_req(mkreq(7'h1C, 44'h180, 3'd4, 12'h30C)); idle(4); dbid = rsp_log[0][57:46];
  send_dat(4'h3, dbid ^ 12'h100, 0, 16'h0001, 128'h1); idle(2);
  chk(e_seen[5] == 1, "write data with a TxnID that is not the DBID");
  clr();
  send_dat(4'h3, dbid, 1, 16'h0000, 128'h0); idle(2);
  chk(e_seen[5] == 1, "write data with a DataID outside the transfer");
  clr();
  send_dat(4'h1, dbid, 0, 16'h0000, 128'h0); idle(2);
  chk(e_seen[5] == 1, "SnpRespData is not write data");
  clr();
  send_dat(4'h3, dbid, 0, 16'h0001, 128'h2, 7'h21); idle(2);
  chk(e_seen[5] == 1, "write data to another node");
  clr();
  send_dat(4'h3, dbid, 0, 16'h0001, 128'h3); idle(2);
  send_dat(4'h3, dbid, 0, 16'h0001, 128'h4); idle(2);
  chk(e_seen[5] == 1, "a repeated DataID");
  // out of range: NDERR
  clr();
  send_req(mkreq(7'h04, 44'h400, 3'd6, 12'h401)); idle(10);
  chk(ndat == 4 && dat_log[0][42:41] == 2'b11 && dat_log[3][239:112] == 128'h0, "read at 1 KB: CompData with NDERR, data 0");
  clr();
  send_req(mkreq(7'h1D, 44'h800_0000_0040, 3'd6, 12'h402)); idle(4); dbid = rsp_log[0][57:46];
  chk(rsp_log[0][36:35] == 2'b11, "write above 1 KB: CompDBIDResp with NDERR");
  for (i = 0; i < 4; i++) send_dat(4'h3, dbid, i, 16'hFFFF, 128'h5);
  idle(3);
  clr(); send_req(mkreq(7'h04, 44'h040, 3'd4, 12'h403)); idle(8);
  chk(no_err() && dat_log[0][239:112] == pat(0), "the NDERR write did not touch line 1");
  // request errors
  clr(); send_req(mkreq(7'h04, 44'h0, 3'd6, 12'h404, 7'h05, 12'hFFF, 2'b00, 7'h21)); idle(6);
  chk(e_seen[1] == 1 && ndat == 0, "REQ to another node: dropped");
  clr(); send_req(mkreq(7'h19, 44'h0, 3'd6, 12'h405)); idle(6);
  chk(e_seen[3] == 1 && nrsp == 0, "WriteUniqueFull is not an SN-F request");
  clr(); send_req(mkreq(7'h44, 44'h0, 3'd6, 12'h406)); idle(6);
  chk(e_seen[3] == 1 && ndat == 0, "WriteNoSnpZero (7-bit opcode 0x44) not supported here");
  clr(); begin logic [136:0] f; f = mkreq(7'h04, 44'h0, 3'd6, 12'h407); f[57] = 1'b1; send_req(f); end idle(6);
  chk(e_seen[2] == 1 && ndat == 0, "MultiReq request: not supported");
  clr(); begin logic [136:0] f; f = mkreq(7'h04, 44'h0, 3'd6, 12'h408); f[63] = 1'b1; send_req(f); end idle(6);
  chk(e_seen[2] == 1, "NumReq / {3'b0, Size}: MBZ bit set");
  clr(); send_req(mkreq(7'h04, 44'h0, 3'd7, 12'h409)); idle(6);
  chk(e_seen[2] == 1, "Size 128 bytes is reserved");
  clr(); send_req(mkreq(7'h04, 44'h0, 3'd6, 12'h40A, 7'h05, 12'hFFF, 2'b10)); idle(6);
  chk(e_seen[2] == 1, "Order 0b10 is reserved from HN-F to SN-F");
  clr(); send_req(mkreq(7'h04, 44'h0, 3'd6, 12'h40B, 7'h05, 12'hFFF, 2'b11)); idle(6);
  chk(e_seen[2] == 1, "Order 0b11 is reserved from HN-F to SN-F");
  clr(); send_req(mkreq(7'h1D, 44'h0, 3'd5, 12'h40C)); idle(6);
  chk(e_seen[2] == 1 && nrsp == 0, "WriteNoSnpFull of 32 bytes");
  idle(4);
  chk(req_cr == 4, "dropped requests still return their L-credit");
  // L-credit violations
  clr();
  for (i = 0; i < 4; i++) send_req(mkreq(7'h04, 44'h0, 3'd6, 12'h500 + i));
  send_req(mkreq(7'h04, 44'h0, 3'd6, 12'h504), 1);
  idle(60);
  chk(e_seen[0] == 0 && ndat == 20, "5th REQ after a credit came back: accepted, 20 packets");
  // six 64-byte reads on consecutive clocks: the first is taken at once and its
  // credit comes back, four more fill the credits, the sixth has none
  clr();
  @(negedge clk); req_cr = 0;
  for (i = 0; i < 6; i++) begin rxreqflitv = 1'b1; rxreqflit = mkreq(7'h04, 44'h0, 3'd6, 12'h510 + i); @(negedge clk); end
  rxreqflitv = 1'b0;
  idle(70);
  chk(e_seen[0] == 1 && ndat == 20, "6 back-to-back REQ flits on 4 L-credits: one dropped (err 0), 5 served");
  idle(10); req_cr = 4;
  clr(); give_rsp = 14; give_dat = 14; idle(20);
  chk(no_err(), "15 RSP and 15 DAT L-credits held: fine");
  @(negedge clk); rsp_extra = 1'b1; @(negedge clk); rsp_extra = 1'b0; idle(2);
  chk(e_seen[6] == 1, "a 16th RSP L-credit: overflow");
  clr();
  @(negedge clk); dat_extra = 1'b1; @(negedge clk); dat_extra = 1'b0; idle(2);
  chk(e_seen[6] == 1, "a 16th DAT L-credit: overflow");
  // the SN keeps 15: a burst of reads still flows
  clr(); give_rsp = 0;
  send_req(mkreq(7'h04, 44'h040, 3'd6, 12'hFFF)); idle(10);
  chk(ndat == 4 && no_err() && dat_log[1][239:112] == pat(1), "after the overflow the link still works");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
