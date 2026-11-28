# IEEE 1588-2019 (PTPv2) ordinary clock, slave side, over Ethernet (Annex F:
# EtherType 0x88F7, destination 01-1B-19-00-00-00). The agent plays the
# master: it sends Announce, Sync (one-step or two-step), Follow_Up and
# Delay_Resp frames and answers the DUT's Delay_Req. Frames are byte streams
# (rx_valid / rx_data / rx_last, one byte per clock, no FCS); the DUT sends
# its Delay_Req on tx_valid / tx_data / tx_last.
#
# Message layout (offsets in the PTP message, after the 14-byte Ethernet
# header): 0 majorSdoId|messageType, 1 versionPTP (2), 2-3 messageLength,
# 4 domainNumber, 6-7 flagField (octet 0 bit 1: twoStepFlag), 8-15
# correctionField (ns x 2^16), 20-29 sourcePortIdentity (clockIdentity +
# portNumber), 30-31 sequenceId, 34-43 timestamp (48-bit seconds, 32-bit ns),
# Delay_Resp 44-53 requestingPortIdentity, Announce 47 grandmasterPriority1,
# 48-51 grandmasterClockQuality, 52 grandmasterPriority2, 53-60
# grandmasterIdentity.
#
# tb/top_tb.sv ptp_model: a slave-only ordinary clock with a free-running
# 8 ns/clock local time. It selects its master from Announce messages (the
# dataset comparison on priority1, clockQuality, priority2, grandmaster
# identity), accepts Sync / Follow_Up / Delay_Resp only from that master,
# timestamps Sync ingress (t2) and its own Delay_Req egress (t3), computes
#   meanPathDelay = ((t2 - t1) + (t4 - t3)) / 2,  offset = (t2 - t1) - delay
# with t1 = originTimestamp + correction (Sync, + Follow_Up for two-step) and
# t4 = receiveTimestamp - correction (Delay_Resp), and steps its clock by
# -offset. Every received frame ends with rx_done and a drop code: 0 used,
# 1 not a PTP frame, 2 version, 3 domain, 4 length / timestamp format,
# 5 not from the selected master, 6 out of sequence, 7 unsupported type.

DEFS = """
localparam longint     PTP_NS_PER_S = 64'd1_000_000_000;
localparam bit [63:0]  PTP_OWN_ID   = 64'h0011_22FF_FE33_4455;   // the DUT's clockIdentity
localparam bit [15:0]  PTP_OWN_PORT = 16'd1;
localparam bit [47:0]  PTP_DA       = 48'h011B_1900_0000;       // Annex F multicast address
localparam bit [63:0]  PTP_MASTER_A = 64'hA0A0_A0FF_FEA0_0001;   // the agent's master clocks
localparam bit [63:0]  PTP_MASTER_B = 64'hB0B0_B0FF_FEB0_0002;

typedef enum bit [3:0] {PTP_NONE, PTP_BAD_ETH, PTP_BAD_VER, PTP_BAD_DOM, PTP_BAD_LEN, PTP_BAD_NS,
                        PTP_NOT_MASTER, PTP_BAD_SEQ, PTP_BAD_PORT} ptp_inj_e;

// minimum messageLength per messageType
function automatic int unsigned ptp_minlen(bit [3:0] mt);
  case (mt)
    4'h0, 4'h1, 4'h8: return 44;
    4'h9:             return 54;
    4'hB:             return 64;
    default:          return 34;
  endcase
endfunction

function automatic bit ptp_has_ts(bit [3:0] mt);
  return mt inside {4'h0, 4'h1, 4'h8, 4'h9, 4'hB};
endfunction
"""

SPEC = dict(
    vip="PTP-VIP", p="ptp", P="PTP", dir="ptp", family="Networking",
    desc="IEEE 1588-2019 PTPv2 VIP over Ethernet: Announce / Sync (one- and two-step) / Follow_Up / "
         "Delay_Req / Delay_Resp messages with header, correctionField and timestamps, best-master "
         "selection, the delay request-response exchange and clock correction, with error injection.",
    about="""
The agent is a PTP master on an Ethernet link (Annex F mapping). It sends
Announce messages for two master clocks, Sync in one-step or two-step mode
with Follow_Up, and answers the DUT's Delay_Req with Delay_Resp, stamping
t1 / t4 from its own time base (8 ns per clock plus an offset and a link
delay). Any message can be broken on purpose: a wrong EtherType, PTP version,
domain or messageLength, a nanoseconds field above 10^9, a sender that is
not the selected master, a wrong sequenceId or requestingPortIdentity. The
monitor parses both directions; the scoreboard's reference model runs the
same best-master selection and delay request-response state machine and
predicts every drop code, the DUT's Delay_Req contents, the offset and mean
path delay and the clock step.

The model is a slave-only ordinary clock with a stepping servo (no
frequency adjustment) and no Announce timeout; peer delay, management and
signaling messages are not modelled.""",
    defs=DEFS,
    timeout=400,
    ports=[
        ("in", "logic", "rx_valid"), ("in", "logic [7:0]", "rx_data"), ("in", "logic", "rx_last"),
        ("in", "logic [7:0]", "domain"),
        ("out", "logic [31:0]", "clock_sec"), ("out", "logic [31:0]", "clock_ns"),
        ("out", "logic", "rx_done"), ("out", "logic [2:0]", "rx_drop"), ("out", "logic [3:0]", "rx_type"),
        ("out", "logic", "sync_ok"), ("out", "logic [63:0]", "offset"), ("out", "logic [63:0]", "delay"),
        ("out", "logic [63:0]", "master_id"),
        ("out", "logic", "tx_valid"), ("out", "logic [7:0]", "tx_data"), ("out", "logic", "tx_last"),
    ],
    cfg="""bit [7:0] domain = 8'd0;                 // DUT domainNumber
longint   master_offset_ns = 64'd1_999_999_000;   // master time - 8 ns x clock count
longint   link_delay_ns = 64'd48;""",
    fields=[
        ("bit", "dir", "req", "norand"),            # 0: agent -> DUT, 1: DUT Delay_Req
        ("bit [3:0]", "mtype", "req"),
        ("bit", "eth_ok", "req", "norand"),         # destination and EtherType of PTP
        ("bit [3:0]", "version", "req", "norand"),
        ("bit [15:0]", "mlen", "req", "norand"),    # messageLength field
        ("bit [7:0]", "nbytes", "req", "norand"),   # frame bytes
        ("bit [7:0]", "dom", "req", "norand"),
        ("bit", "two_step", "req"),
        ("bit [63:0]", "corr", "req"),              # correctionField (ns x 2^16)
        ("bit [63:0]", "src_clock", "req"),
        ("bit [15:0]", "src_port", "req", "norand"),
        ("bit [15:0]", "seq", "req", "norand"),
        ("bit [47:0]", "ts_sec", "req", "norand"),
        ("bit [31:0]", "ts_ns", "req", "norand"),
        ("bit [63:0]", "req_clock", "req", "norand"),
        ("bit [15:0]", "req_port", "req", "norand"),
        ("bit [7:0]", "prio1", "req"),
        ("bit [31:0]", "quality", "req"),
        ("bit [7:0]", "prio2", "req"),
        ("bit [2:0]", "drop", "rsp"),
        ("bit", "ok", "rsp"),                        # offset computed (Delay_Resp used)
        ("bit [63:0]", "offset", "rsp"),
        ("bit [63:0]", "delay", "rsp"),
        ("bit [63:0]", "adj", "rsp"),                # clock step seen with rx_done
        ("bit [63:0]", "master", "rsp"),             # selected master clockIdentity after the frame
        ("ptp_inj_e", "inj", "info", "rand"),
        ("bit signed [15:0]", "jump", "info", "rand"),  # master time step before a Sync (ns)
        ("bit [3:0]", "gap", "info", "rand"),
        ("bit [31:0]", "t_sec", "info"),             # DUT clock at the first byte
        ("bit [31:0]", "t_ns", "info"),
    ],
    constraints="""
constraint c_type { mtype dist { 4'h0 := 4, 4'h8 := 4, 4'h9 := 4, 4'hB := 1, 4'hC := 1 }; }
constraint c_src  { src_clock dist { PTP_MASTER_A := 8, PTP_MASTER_B := 1 }; }
constraint c_ann  { prio1 inside {8'd64, 8'd128, 8'd200}; prio2 inside {8'd128, 8'd255};
                    quality inside {32'hF8FE_FFFF, 32'h06FE_FFFF}; }
constraint c_corr { corr dist { 0 := 6, [64'h1_0000 : 64'hFF_0000] :/ 2 }; corr[15:0] == 0; }
constraint c_inj  { inj dist { PTP_NONE := 16, [PTP_BAD_ETH : PTP_BAD_PORT] :/ 4 };
                    inj == PTP_BAD_PORT -> mtype == 4'h9;
                    inj == PTP_BAD_SEQ -> mtype inside {4'h8, 4'h9};
                    inj == PTP_BAD_NS -> mtype != 4'hC; }
constraint c_misc { jump dist { 0 := 3, [-4000:-8] :/ 1, [8:4000] :/ 1 }; jump[2:0] == 0; gap inside {[0:6]}; }
""",
    tr_functions="""
// total nanoseconds of the timestamp field
function longint ts_total();
  return longint'(ts_sec) * PTP_NS_PER_S + ts_ns;
endfunction

function void set_ts(longint tot);
  ts_sec = tot / PTP_NS_PER_S;
  ts_ns = tot % PTP_NS_PER_S;
endfunction
""",
    drv_rsp=False,
    drv_desc="one PTP frame per item, with the timestamps of the agent's master time base; Delay_Resp answers the DUT's last Delay_Req",
    drv_members="""realtime     t0 = 0, per = 0;         // master time base: clock edges counted from t0
longint      m_off;                   // master time = 8 ns x cycle + m_off
bit [79:0]   last_src = 0;            // last Delay_Req answered
bit [15:0]   last_seq = 0;
longint      last_mt = 0;
bit [15:0]   sync_seq = 0;
bit [15:0]   last_sync_seq = 0;
longint      last_t1 = 0, last_corr = 0;
// Delay_Req frames seen on tx: sequenceId, sender, master time
bit [15:0]   dq_seq[$];
bit [79:0]   dq_src[$];
longint      dq_mt[$];         // master time of the first byte""",
    drv_bg="""
begin   // one process: fork would run each statement in parallel
bit [7:0] b[$];
int unsigned c0;
m_off = cfg.master_offset_ns;
@(vif.drv_cb); t0 = $realtime;
@(vif.drv_cb); per = $realtime - t0;
forever begin
  @(vif.drv_cb);
  if (vif.drv_cb.tx_valid === 1'b1) begin
    c0 = cyc_now();
    b.delete();
    b.push_back(vif.drv_cb.tx_data);
    while (vif.drv_cb.tx_last !== 1'b1) begin
      @(vif.drv_cb);
      if (vif.drv_cb.tx_valid === 1'b1) b.push_back(vif.drv_cb.tx_data);
    end
    if (b.size() >= 46) begin
      dq_seq.push_back({b[44], b[45]});
      dq_src.push_back({b[34], b[35], b[36], b[37], b[38], b[39], b[40], b[41], b[42], b[43]});
      dq_mt.push_back(longint'(c0 - 1) * 8 + m_off);   // the DUT drove the first byte one edge earlier
    end
  end
end
end""",
    drv_idle="""
vif.drv_cb.rx_valid <= 1'b0; vif.drv_cb.rx_data <= '0; vif.drv_cb.rx_last <= 1'b0;
vif.drv_cb.domain <= cfg.domain;
""",
    drv_item="""
bit [7:0] f[$];
longint c, now;
// never overlap a Delay_Req the DUT is about to send or is sending
repeat (12) @(vif.drv_cb);
while (vif.drv_cb.tx_valid === 1'b1) @(vif.drv_cb);
repeat (t.gap) @(vif.drv_cb);
c = longint'($signed(t.corr)) >>> 16;
t.dir = 0; t.eth_ok = (t.inj != PTP_BAD_ETH); t.version = (t.inj == PTP_BAD_VER) ? 4'd1 : 4'd2;
t.dom = cfg.domain + (t.inj == PTP_BAD_DOM);
t.src_port = (t.inj == PTP_NOT_MASTER) ? 16'd9 : 16'd1;
t.req_clock = 0; t.req_port = 0;
if (t.mtype != 4'hB) begin t.prio1 = 0; t.quality = 0; t.prio2 = 0; end
if (t.mtype != 4'h0) t.two_step = 0;
if (t.mtype == 4'h0) m_off += t.jump;
now = longint'(cyc_now()) * 8 + m_off;         // master time at the edge driving the first byte
case (t.mtype)
  4'h0: begin                                  // Sync: t1 = time on the wire - link delay
    sync_seq++; t.seq = sync_seq; last_sync_seq = sync_seq;
    last_t1 = now - cfg.link_delay_ns; last_corr = c;
    t.set_ts(t.two_step ? 0 : last_t1 - c);
  end
  4'h8: begin                                  // Follow_Up: preciseOriginTimestamp
    t.seq = last_sync_seq + (t.inj == PTP_BAD_SEQ);
    t.set_ts(last_t1 - last_corr - c);
  end
  4'h9: begin                                  // Delay_Resp for the oldest Delay_Req
    int unsigned w = 0;
    while (dq_seq.size() == 0 && w < 4) begin @(vif.drv_cb); w++; end
    if (dq_seq.size() != 0) begin
      last_src = dq_src.pop_front(); last_seq = dq_seq.pop_front(); last_mt = dq_mt.pop_front();
    end
    // no new Delay_Req: answer the last one again
    t.seq = last_seq + (t.inj == PTP_BAD_SEQ);
    t.req_clock = last_src[79:16]; t.req_port = last_src[15:0] + (t.inj == PTP_BAD_PORT);
    t.set_ts(last_mt + cfg.link_delay_ns + c);
  end
  4'hB: begin t.seq = sync_seq; t.set_ts(now); end
  default: begin t.seq = 0; t.set_ts(0); end
endcase
if (t.inj == PTP_BAD_NS) t.ts_ns = 32'd1_000_000_000 + t.ts_ns[7:0];
t.mlen = ptp_minlen(t.mtype) - 2 * (t.inj == PTP_BAD_LEN);
t.nbytes = 14 + ptp_minlen(t.mtype);
// Ethernet header
for (int i = 5; i >= 0; i--) f.push_back(PTP_DA[8*i +: 8]);
for (int i = 0; i < 6; i++) f.push_back(8'hA0 + i);
f.push_back(t.eth_ok ? 8'h88 : 8'h08); f.push_back(t.eth_ok ? 8'hF7 : 8'h00);
// PTP header
f.push_back({4'h0, t.mtype}); f.push_back({4'h0, t.version});
f.push_back(t.mlen[15:8]); f.push_back(t.mlen[7:0]); f.push_back(t.dom); f.push_back(8'h00);
f.push_back({6'b0, t.two_step, 1'b0}); f.push_back(8'h00);
for (int i = 7; i >= 0; i--) f.push_back(t.corr[8*i +: 8]);
repeat (4) f.push_back(8'h00);
for (int i = 7; i >= 0; i--) f.push_back(t.src_clock[8*i +: 8]);
f.push_back(t.src_port[15:8]); f.push_back(t.src_port[7:0]);
f.push_back(t.seq[15:8]); f.push_back(t.seq[7:0]);
f.push_back(8'h00); f.push_back(8'h00);
// body: timestamp, then the type's fields
if (ptp_has_ts(t.mtype)) begin
  for (int i = 5; i >= 0; i--) f.push_back(t.ts_sec[8*i +: 8]);
  for (int i = 3; i >= 0; i--) f.push_back(t.ts_ns[8*i +: 8]);
end
if (t.mtype == 4'h9) begin
  for (int i = 7; i >= 0; i--) f.push_back(t.req_clock[8*i +: 8]);
  f.push_back(t.req_port[15:8]); f.push_back(t.req_port[7:0]);
end
if (t.mtype == 4'hB) begin
  f.push_back(8'h00); f.push_back(8'h25); f.push_back(8'h00); f.push_back(t.prio1);
  for (int i = 3; i >= 0; i--) f.push_back(t.quality[8*i +: 8]);
  f.push_back(t.prio2);
  for (int i = 7; i >= 0; i--) f.push_back(t.src_clock[8*i +: 8]);   // grandmasterIdentity
  f.push_back(8'h00); f.push_back(8'h00); f.push_back(8'hA0);
end
while (f.size() < t.nbytes) f.push_back(8'h00);
foreach (f[i]) begin
  vif.drv_cb.rx_valid <= 1'b1; vif.drv_cb.rx_data <= f[i]; vif.drv_cb.rx_last <= (i == f.size() - 1);
  @(vif.drv_cb);
end
vif.drv_cb.rx_valid <= 1'b0; vif.drv_cb.rx_last <= 1'b0;
""",
    drv_tasks="""
// clock edges since t0 (no race with a counting thread)
function int unsigned cyc_now();
  return (per == 0) ? 0 : int'(($realtime - t0) / per);   // rounds to the nearest edge
endfunction
""",
    mon_desc="frames in both directions parsed into items; DUT rx_done / drop code / offset / delay and the clock step; clock continuity checked",
    mon_run="""
bit [7:0] rb[$], tb[$];
bit [31:0] rs, rn, ts_, tn;
ptp_transaction pend[$];
longint prev = -1;
forever begin
  longint now;
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin prev = -1; continue; end
  now = longint'(vif.mon_cb.clock_sec) * PTP_NS_PER_S + vif.mon_cb.clock_ns;
  // rx_done of the oldest received frame (the clock step shows with it)
  if (vif.mon_cb.rx_done) begin
    if (pend.size() == 0) `uvm_error("MON", "PTP rx_done without a frame")
    else begin
      ptp_transaction t = pend.pop_front();
      t.drop = vif.mon_cb.rx_drop;
      t.ok = vif.mon_cb.sync_ok;
      if (t.ok) begin t.offset = vif.mon_cb.offset; t.delay = vif.mon_cb.delay; end
      t.adj = (prev < 0) ? 0 : now - prev - 8;
      t.master = vif.mon_cb.master_id;
      if (vif.mon_cb.rx_type != t.mtype) `uvm_error("MON", "PTP rx_type differs from the frame's messageType")
      publish(t);
    end
  end else if (prev >= 0 && now != prev + 8)
    `uvm_error("MON", $sformatf("PTP clock stepped from %0d to %0d without a correction", prev, now))
  prev = now;
  if (vif.mon_cb.rx_valid) begin
    if (rb.size() == 0) begin rs = vif.mon_cb.clock_sec; rn = vif.mon_cb.clock_ns; end
    rb.push_back(vif.mon_cb.rx_data);
    if (vif.mon_cb.rx_last) begin
      ptp_transaction t = ptp_transaction::type_id::create("rx");
      parse(t, rb); t.dir = 0; t.t_sec = rs; t.t_ns = rn;
      pend.push_back(t);
      rb.delete();
    end
  end
  if (vif.mon_cb.tx_valid) begin
    if (tb.size() == 0) begin ts_ = vif.mon_cb.clock_sec; tn = vif.mon_cb.clock_ns; end
    tb.push_back(vif.mon_cb.tx_data);
    if (vif.mon_cb.tx_last) begin
      ptp_transaction t = ptp_transaction::type_id::create("tx");
      parse(t, tb); t.dir = 1; t.t_sec = ts_; t.t_ns = tn; t.master = vif.mon_cb.master_id;
      publish(t);
      tb.delete();
    end
  end
end
""",
    mon_tasks="""
// fields of a PTP frame (bytes from the destination address on)
function void parse(ptp_transaction t, bit [7:0] b[$]);
  t.nbytes = b.size();
  while (b.size() < 78) b.push_back(8'h00);
  t.eth_ok = ({b[0], b[1], b[2], b[3], b[4], b[5]} == 48'h011B_1900_0000) && ({b[12], b[13]} == 16'h88F7);
  t.mtype = b[14][3:0]; t.version = b[15][3:0]; t.mlen = {b[16], b[17]}; t.dom = b[18];
  t.two_step = b[20][1];
  for (int i = 0; i < 8; i++) t.corr = {t.corr[55:0], b[22 + i]};
  for (int i = 0; i < 8; i++) t.src_clock = {t.src_clock[55:0], b[34 + i]};
  t.src_port = {b[42], b[43]}; t.seq = {b[44], b[45]};
  for (int i = 0; i < 6; i++) t.ts_sec = {t.ts_sec[39:0], b[48 + i]};
  for (int i = 0; i < 4; i++) t.ts_ns = {t.ts_ns[23:0], b[54 + i]};
  if (t.mtype == 4'h9) begin
    for (int i = 0; i < 8; i++) t.req_clock = {t.req_clock[55:0], b[58 + i]};
    t.req_port = {b[66], b[67]};
  end
  if (t.mtype == 4'hB) begin
    t.prio1 = b[61]; t.quality = {b[62], b[63], b[64], b[65]}; t.prio2 = b[66];
  end
endfunction
""",
    sb_members="""bit        mvalid = 0;
bit [79:0] mport = 0;
bit [7:0]  mp1 = 0, mp2 = 0;
bit [31:0] mq = 0;
bit [63:0] mgm = 0;
int        xs = 0;                        // 0 idle, 1 wait Follow_Up, 2 ready, 3 wait Delay_Resp
bit [15:0] seq_s = 0, dseq = 0, dsent = 0;
longint    t1 = 0, t2 = 0, t3 = 0, corr_s = 0;""",
    predict="""
longint tr = longint'(t.t_sec) * PTP_NS_PER_S + t.t_ns;
longint c = longint'($signed(t.corr)) >>> 16;
t.ok = 0; t.offset = 0; t.delay = 0; t.adj = 0;
if (t.dir) begin
  // the DUT's Delay_Req
  if (xs != 2) t.drop = 7;                 // not expected: shows as a mismatch
  t.mtype = 4'h1; t.eth_ok = 1; t.version = 2; t.mlen = 44; t.nbytes = 58; t.dom = cfg.domain;
  t.two_step = 0; t.corr = 0; t.src_clock = PTP_OWN_ID; t.src_port = PTP_OWN_PORT; t.seq = dseq;
  t.set_ts(tr); t.req_clock = 0; t.req_port = 0; t.prio1 = 0; t.quality = 0; t.prio2 = 0;
  dsent = dseq; dseq++; t3 = tr; xs = 3;
end else begin
  bit [79:0] src = {t.src_clock, t.src_port};
  t.drop = 0;
  if (!t.eth_ok) t.drop = 1;
  else if (t.version != 2) t.drop = 2;
  else if (t.dom != cfg.domain) t.drop = 3;
  else if (t.mlen != t.nbytes - 14 || t.mlen < ptp_minlen(t.mtype) || (ptp_has_ts(t.mtype) && t.ts_ns >= PTP_NS_PER_S))
    t.drop = 4;
  else case (t.mtype)
    4'hB:
      if (!mvalid || src == mport || {t.prio1, t.quality, t.prio2, t.src_clock} < {mp1, mq, mp2, mgm}) begin
        mvalid = 1; mport = src; mp1 = t.prio1; mq = t.quality; mp2 = t.prio2; mgm = t.src_clock;
      end
    4'h0:
      if (!mvalid || src != mport) t.drop = 5;
      else begin
        t2 = tr; seq_s = t.seq; corr_s = c;
        if (t.two_step) xs = 1;
        else begin t1 = t.ts_total() + c; xs = 2; end
      end
    4'h8:
      if (!mvalid || src != mport) t.drop = 5;
      else if (xs != 1 || t.seq != seq_s) t.drop = 6;
      else begin t1 = t.ts_total() + corr_s + c; xs = 2; end
    4'h9:
      if (!mvalid || src != mport) t.drop = 5;
      else if (xs != 3 || t.seq != dsent || t.req_clock != PTP_OWN_ID || t.req_port != PTP_OWN_PORT) t.drop = 6;
      else begin
        longint t4 = t.ts_total() - c;
        longint d = ((t2 - t1) + (t4 - t3)) >>> 1;
        longint o = (t2 - t1) - d;
        t.ok = 1; t.delay = d; t.offset = o; t.adj = -o;
        xs = 0;
      end
    default: t.drop = 7;
  endcase
end
t.master = mvalid ? mport[79:16] : 64'h0;
""",
    pair_skip="t.dir",
    checks="""
if (t.dir && t.mtype != 4'h1) fail(t, "the DUT sent something other than Delay_Req");
if (t.ok && $signed(t.delay) < 0) fail(t, "negative mean path delay");
if (t.ts_ns >= 32'd1_000_000_000 && t.drop != 4 && !t.dir) fail(t, "nanoseconds field >= 10^9 accepted");
""",
    coverage="""
cp_type  : coverpoint tr.mtype iff (!tr.dir) { bins sync = {4'h0}; bins fu = {4'h8}; bins dresp = {4'h9};
                                               bins ann = {4'hB}; bins other = {4'hC}; }
cp_two   : coverpoint tr.two_step iff (!tr.dir && tr.mtype == 4'h0);
cp_drop  : coverpoint tr.drop iff (!tr.dir);
cp_corr  : coverpoint (tr.corr != 0) iff (!tr.dir);
cp_ok    : coverpoint tr.ok iff (!tr.dir && tr.mtype == 4'h9);
cp_off   : coverpoint tr.offset iff (tr.ok) { bins zero = {0}; bins pos = {[1:64'h7FFF_FFFF_FFFF_FFFF]};
                                              bins neg = {[64'h8000_0000_0000_0000:$]}; }
cp_dreq  : coverpoint tr.dir;
cp_master: coverpoint tr.master { bins none = {0}; bins a = {PTP_MASTER_A}; bins b = {PTP_MASTER_B}; }
// drop codes reachable for each message type (iff per type: Verilator counts ignore_bins of a cross)
cp_drop_sync : coverpoint tr.drop iff (!tr.dir && tr.mtype == 4'h0) { bins d[] = {[0:5]}; }
cp_drop_fu   : coverpoint tr.drop iff (!tr.dir && tr.mtype == 4'h8) { bins d[] = {[0:6]}; }
cp_drop_dr   : coverpoint tr.drop iff (!tr.dir && tr.mtype == 4'h9) { bins d[] = {[0:6]}; }
cp_drop_ann  : coverpoint tr.drop iff (!tr.dir && tr.mtype == 4'hB) { bins d[] = {[0:4]}; }
cp_drop_oth  : coverpoint tr.drop iff (!tr.dir && tr.mtype == 4'hC) { bins d[] = {[1:4], 7}; }
""",
    directed="""
// no master yet: Sync dropped; Announce from A selects it
t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_A; send(t);
t = item(); t.mtype = 4'hB; t.src_clock = PTP_MASTER_A; t.prio1 = 128; t.quality = 32'hF8FE_FFFF; t.prio2 = 128; send(t);
// one-step and two-step exchanges, with and without corrections and master time steps
for (int k = 0; k < 6; k++) begin
  t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_A; t.two_step = k[0]; t.corr = k[1] ? 64'h40_0000 : 0;
  t.jump = (k == 2) ? 16'd800 : (k == 4) ? 16'd8 : 0; send(t);
  if (k[0]) begin t = item(); t.mtype = 4'h8; t.src_clock = PTP_MASTER_A; t.corr = k[2] ? 64'h18_0000 : 0; send(t); end
  t = item(); t.mtype = 4'h9; t.src_clock = PTP_MASTER_A; t.corr = (k == 3) ? 64'h20_0000 : 0; send(t);
end
// every injected error on every message type it applies to
for (int i = 1; i <= 8; i++) begin
  t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_A; t.two_step = 1;
  t.inj = (i inside {7, 8}) ? PTP_NONE : ptp_inj_e'(i); send(t);
  t = item(); t.mtype = 4'h8; t.src_clock = PTP_MASTER_A; t.inj = (i == 8) ? PTP_NONE : ptp_inj_e'(i); send(t);
  t = item(); t.mtype = 4'h9; t.src_clock = PTP_MASTER_A; t.inj = ptp_inj_e'(i); send(t);
end
// header errors on Announce and Signaling
for (int i = 1; i <= 5; i++) begin
  t = item(); t.mtype = 4'hB; t.src_clock = PTP_MASTER_B; t.prio1 = 255; t.inj = ptp_inj_e'(i); send(t);
  if (i != 5) begin t = item(); t.mtype = 4'hC; t.src_clock = PTP_MASTER_A; t.inj = ptp_inj_e'(i); send(t); end
end
t = item(); t.mtype = 4'hC; t.src_clock = PTP_MASTER_A; send(t);                 // signaling: unsupported
t = item(); t.mtype = 4'h8; t.src_clock = PTP_MASTER_A; send(t);                 // Follow_Up without a Sync
// a worse Announce from B changes nothing, a better one takes over
t = item(); t.mtype = 4'hB; t.src_clock = PTP_MASTER_B; t.prio1 = 200; t.quality = 32'hF8FE_FFFF; t.prio2 = 128; send(t);
t = item(); t.mtype = 4'hB; t.src_clock = PTP_MASTER_B; t.prio1 = 64; t.quality = 32'h06FE_FFFF; t.prio2 = 128; send(t);
t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_A; send(t);                 // A is no longer the master
t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_B; t.jump = 16'd4000; send(t);
t = item(); t.mtype = 4'h9; t.src_clock = PTP_MASTER_B; send(t);
// a new Sync restarts an exchange waiting for its Delay_Resp
t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_B; send(t);
t = item(); t.mtype = 4'h0; t.src_clock = PTP_MASTER_B; send(t);
t = item(); t.mtype = 4'h9; t.src_clock = PTP_MASTER_B; send(t);                 // answers the first Delay_Req: dropped
t = item(); t.mtype = 4'h9; t.src_clock = PTP_MASTER_B; send(t);
// back to A for the random traffic
t = item(); t.mtype = 4'hB; t.src_clock = PTP_MASTER_A; t.prio1 = 1; t.quality = 32'h06FE_FFFF; t.prio2 = 1; send(t);
""",
    drain_ns=3000,
)

SPEC["model"] = """
module ptp_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        rx_valid,
  input  logic [7:0]  rx_data,
  input  logic        rx_last,
  input  logic [7:0]  domain,
  output logic [31:0] clock_sec,
  output logic [31:0] clock_ns,
  output logic        rx_done,
  output logic [2:0]  rx_drop,
  output logic [3:0]  rx_type,
  output logic        sync_ok,
  output logic [63:0] offset,
  output logic [63:0] delay,
  output logic [63:0] master_id,
  output logic        tx_valid,
  output logic [7:0]  tx_data,
  output logic        tx_last
);
  localparam logic [63:0] NS_PER_S = 64'd1000000000;
  localparam logic [63:0] OWN_ID   = 64'h0011_22FF_FE33_4455;
  localparam logic [15:0] OWN_PORT = 16'd1;
  localparam int          TXDLY = 4, DRLEN = 58, RBMAX = 96;
  localparam logic [2:0]  S_IDLE = 3'd0, S_WFU = 3'd1, S_RDY = 3'd2, S_TX = 3'd3, S_WDR = 3'd4;

  logic [63:0]  tns, t2_sof, t1, t2, t3, corr_s;
  logic [7:0]   rb [0:RBMAX-1];
  logic [7:0]   rcnt, nb;
  logic         proc, cap3, mvalid;
  logic [2:0]   st;
  logic [3:0]   wcnt;
  logic [6:0]   tidx;
  logic [15:0]  seq_s, dseq, dsent;
  logic [79:0]  mport;
  logic [111:0] mds;                 // {priority1, clockQuality, priority2, grandmasterIdentity}
  logic [63:0]  qs, rs;

  assign qs = tns / NS_PER_S;
  assign rs = tns % NS_PER_S;
  assign clock_sec = qs[31:0];
  assign clock_ns  = rs[31:0];
  assign master_id = mvalid ? mport[79:16] : 64'h0;

  function automatic logic [15:0] minlen(input logic [3:0] mt);
    case (mt)
      4'h0, 4'h1, 4'h8: minlen = 16'd44;
      4'h9:             minlen = 16'd54;
      4'hB:             minlen = 16'd64;
      default:          minlen = 16'd34;
    endcase
  endfunction

  function automatic logic has_ts(input logic [3:0] mt);
    has_ts = (mt == 4'h0) || (mt == 4'h1) || (mt == 4'h8) || (mt == 4'h9) || (mt == 4'hB);
  endfunction

  // byte i of the DUT's Delay_Req (originTimestamp = t3)
  function automatic logic [7:0] txb(input logic [6:0] i, input logic [15:0] sq, input logic [63:0] ts,
                                     input logic [7:0] dom);
    logic [63:0] sec, ns;
    sec = ts / NS_PER_S;
    ns  = ts % NS_PER_S;
    txb = 8'h00;
    case (i)
      7'd0:  txb = 8'h01;
      7'd1:  txb = 8'h1B;
      7'd2:  txb = 8'h19;
      7'd7:  txb = 8'h11;
      7'd8:  txb = 8'h22;
      7'd9:  txb = 8'h33;
      7'd10: txb = 8'h44;
      7'd11: txb = 8'h55;
      7'd12: txb = 8'h88;
      7'd13: txb = 8'hF7;
      7'd14: txb = 8'h01;
      7'd15: txb = 8'h02;
      7'd17: txb = 8'd44;
      7'd18: txb = dom;
      7'd44: txb = sq[15:8];
      7'd45: txb = sq[7:0];
      7'd46: txb = 8'h01;
      7'd47: txb = 8'h7F;
      default: begin
        if (i >= 7'd34 && i <= 7'd41) txb = OWN_ID[8 * (41 - i) +: 8];
        if (i == 7'd43) txb = OWN_PORT[7:0];
        if (i >= 7'd48 && i <= 7'd53) txb = sec[8 * (53 - i) +: 8];
        if (i >= 7'd54 && i <= 7'd57) txb = ns[8 * (57 - i) +: 8];
      end
    endcase
  endfunction

  // frame fields of the received message
  logic [3:0]         f_mt;
  logic [15:0]        f_len, f_sq, f_port;
  logic [63:0]        f_corr, f_rq, f_ts, f_sec, f_ns, step;
  logic [79:0]        f_src;
  logic [111:0]       f_ds;
  logic               f_eth;
  logic [2:0]         d;
  logic signed [63:0] c, t4, ms, sm, dl, o;

  always_comb begin
    f_mt   = rb[14][3:0];
    f_len  = {rb[16], rb[17]};
    f_corr = {rb[22], rb[23], rb[24], rb[25], rb[26], rb[27], rb[28], rb[29]};
    f_src  = {rb[34], rb[35], rb[36], rb[37], rb[38], rb[39], rb[40], rb[41], rb[42], rb[43]};
    f_sq   = {rb[44], rb[45]};
    f_sec  = {16'h0, rb[48], rb[49], rb[50], rb[51], rb[52], rb[53]};
    f_ns   = {32'h0, rb[54], rb[55], rb[56], rb[57]};
    f_rq   = {rb[58], rb[59], rb[60], rb[61], rb[62], rb[63], rb[64], rb[65]};
    f_port = {rb[66], rb[67]};
    f_ds   = {rb[61], rb[62], rb[63], rb[64], rb[65], rb[66], rb[67], rb[68], rb[69], rb[70], rb[71], rb[72],
              rb[73], rb[74]};
    f_eth  = ({rb[0], rb[1], rb[2], rb[3], rb[4], rb[5]} == 48'h011B_1900_0000) && ({rb[12], rb[13]} == 16'h88F7);
    f_ts   = f_sec * NS_PER_S + f_ns;
    c      = $signed(f_corr) >>> 16;
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tns <= 64'h0; t2_sof <= 64'h0; t1 <= 64'h0; t2 <= 64'h0; t3 <= 64'h0; corr_s <= 64'h0;
      rcnt <= 8'h0; nb <= 8'h0; proc <= 1'b0; cap3 <= 1'b0; mvalid <= 1'b0; st <= S_IDLE; wcnt <= 4'h0;
      tidx <= 7'h0; seq_s <= 16'h0; dseq <= 16'h0; dsent <= 16'h0; mport <= 80'h0; mds <= 112'h0;
      rx_done <= 1'b0; rx_drop <= 3'h0; rx_type <= 4'h0; sync_ok <= 1'b0; offset <= 64'h0; delay <= 64'h0;
      tx_valid <= 1'b0; tx_data <= 8'h0; tx_last <= 1'b0; for (int j = 0; j < RBMAX; j++) rb[j] <= 8'h0;
    end else begin
      step = 64'd8;
      rx_done <= 1'b0;
      sync_ok <= 1'b0;

      // Delay_Req transmission, TXDLY clocks after t1 is known
      case (st)
        S_RDY:
          if (wcnt == TXDLY - 1) begin
            st <= S_TX; tidx <= 7'd1; cap3 <= 1'b1; dsent <= dseq;
            tx_valid <= 1'b1; tx_data <= txb(7'd0, dseq, tns, domain); tx_last <= 1'b0;
          end else wcnt <= wcnt + 4'd1;
        S_TX: begin
          cap3 <= 1'b0;
          if (cap3) t3 <= tns;                 // the clock while the first byte is on the wire
          if (tidx == DRLEN) begin
            tx_valid <= 1'b0; tx_data <= 8'h0; tx_last <= 1'b0; st <= S_WDR; dseq <= dseq + 16'd1;
          end else begin
            tx_data <= txb(tidx, dsent, cap3 ? tns : t3, domain);
            tx_last <= (tidx == DRLEN - 1);
            tidx <= tidx + 7'd1;
          end
        end
        default: ;
      endcase

      // receive: t2 is the clock when the first byte is sampled
      if (rx_valid) begin
        if (rcnt == 8'h0) t2_sof <= tns;
        if (rcnt < RBMAX) rb[rcnt] <= rx_data;
        rcnt <= rcnt + 8'h1;
        if (rx_last) begin nb <= rcnt + 8'h1; rcnt <= 8'h0; proc <= 1'b1; end
      end

      if (proc) begin
        proc <= 1'b0;
        d = 3'd0;
        if (!f_eth) d = 3'd1;
        else if (rb[15][3:0] != 4'd2) d = 3'd2;
        else if (rb[18] != domain) d = 3'd3;
        else if (f_len != nb - 14 || f_len < minlen(f_mt) || (has_ts(f_mt) && f_ns >= NS_PER_S)) d = 3'd4;
        else case (f_mt)
          4'hB:   // Announce: keep the best master (dataset comparison, lowest wins)
            if (!mvalid || f_src == mport || f_ds < mds) begin mvalid <= 1'b1; mport <= f_src; mds <= f_ds; end
          4'h0:   // Sync
            if (!mvalid || f_src != mport) d = 3'd5;
            else begin
              t2 <= t2_sof; seq_s <= f_sq; corr_s <= c;
              if (rb[20][1]) st <= S_WFU;
              else begin t1 <= f_ts + c; st <= S_RDY; wcnt <= 4'h0; end
            end
          4'h8:   // Follow_Up
            if (!mvalid || f_src != mport) d = 3'd5;
            else if (st != S_WFU || f_sq != seq_s) d = 3'd6;
            else begin t1 <= f_ts + corr_s + c; st <= S_RDY; wcnt <= 4'h0; end
          4'h9:   // Delay_Resp
            if (!mvalid || f_src != mport) d = 3'd5;
            else if (st != S_WDR || f_sq != dsent || f_rq != OWN_ID || f_port != OWN_PORT) d = 3'd6;
            else begin
              t4 = f_ts - c;
              ms = t2 - t1;
              sm = t4 - t3;
              dl = (ms + sm) >>> 1;
              o  = ms - dl;
              offset <= o; delay <= dl; sync_ok <= 1'b1;
              step = 64'd8 - o;
              st <= S_IDLE;
            end
          default: d = 3'd7;
        endcase
        rx_done <= 1'b1; rx_drop <= d; rx_type <= f_mt;
      end
      tns <= tns + step;
    end
  end
endmodule
"""

SPEC["sva"] = """
logic [63:0] tot;
assign tot = clock_sec * 64'd1000000000 + clock_ns;
// outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n)
                 !$isunknown({rx_done, rx_drop, sync_ok, tx_valid, tx_last, clock_sec, clock_ns}))
  else $error("PTP: X on outputs");
assert property (@(posedge clk) disable iff (!rst_n) clock_ns < 32'd1000000000)
  else $error("PTP: clock nanoseconds >= 10^9");
// every received frame gets one rx_done, the clock after its last byte has been processed
assert property (@(posedge clk) disable iff (!rst_n) rx_valid && rx_last |=> ##1 rx_done)
  else $error("PTP: no rx_done after a frame");
assert property (@(posedge clk) disable iff (!rst_n) rx_done |-> $past(rx_valid && rx_last, 2))
  else $error("PTP: rx_done without a frame");
// an offset is produced only by a Delay_Resp that was used
assert property (@(posedge clk) disable iff (!rst_n) sync_ok |-> rx_done && rx_drop == 3'd0 && rx_type == 4'h9)
  else $error("PTP: sync_ok without an accepted Delay_Resp");
// the clock advances 8 ns per clock unless it is corrected
assert property (@(posedge clk) disable iff (!rst_n) ##1 !sync_ok |-> tot == $past(tot) + 64'd8)
  else $error("PTP: clock stepped without a correction");
// Delay_Req: contiguous bytes, starting with the PTP multicast address
assert property (@(posedge clk) disable iff (!rst_n) tx_last |-> tx_valid)
  else $error("PTP: tx_last without tx_valid");
assert property (@(posedge clk) disable iff (!rst_n) tx_valid && !tx_last |=> tx_valid)
  else $error("PTP: gap in the Delay_Req");
assert property (@(posedge clk) disable iff (!rst_n) $rose(tx_valid) |-> tx_data == 8'h01)
  else $error("PTP: Delay_Req does not start with 01-1B-19");
cover property (@(posedge clk) disable iff (!rst_n) sync_ok);
cover property (@(posedge clk) disable iff (!rst_n) rx_done && rx_drop == 3'd5);
cover property (@(posedge clk) disable iff (!rst_n) tx_last);
"""

SPEC["smoke"] = """
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic rx_valid = 1'b0, rx_last = 1'b0;
logic [7:0] rx_data = '0, domain = '0;
wire [31:0] clock_sec, clock_ns;
wire rx_done, sync_ok, tx_valid, tx_last;
wire [2:0] rx_drop;
wire [3:0] rx_type;
wire [63:0] offset, delay, master_id;
wire [7:0] tx_data;

always #5 clk = ~clk;

ptp_model u_dut (.clk(clk), .rst_n(rst_n), .rx_valid(rx_valid), .rx_data(rx_data), .rx_last(rx_last),
                 .domain(domain), .clock_sec(clock_sec), .clock_ns(clock_ns), .rx_done(rx_done),
                 .rx_drop(rx_drop), .rx_type(rx_type), .sync_ok(sync_ok), .offset(offset), .delay(delay),
                 .master_id(master_id), .tx_valid(tx_valid), .tx_data(tx_data), .tx_last(tx_last));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

localparam longint NS = 64'd1000000000;
localparam logic [63:0] A = 64'hA0A0_A0FF_FEA0_0001, B = 64'hB0B0_B0FF_FEB0_0002, C = 64'hC0C0_C0FF_FEC0_0003;
localparam logic [63:0] OWN = 64'h0011_22FF_FE33_4455;

function automatic longint tot_now();
  return longint'(clock_sec) * NS + clock_ns;
endfunction

// monitors, all at the falling edge: clock steps, rx results, the DUT's Delay_Req
int tcyc = 0;
always @(posedge clk) tcyc++;
longint ptot = 0, lstep = 0, t3_obs = 0;
bit pv = 0;
int nlast = 0, nstep = 0, ndone = 0, nok = 0, ndreq = 0, txn = 0, txlen = 0, t_done = 0, t_tx = 0;
logic [2:0] ldrop = 0;
logic [3:0] ltype = 0;
logic [63:0] loff = 0, ldly = 0;
logic [7:0] txf [0:79];
always @(negedge clk) begin
  if (!rst_n) pv = 0;
  else begin
    if (pv && tot_now() != ptot + 8) begin nstep++; lstep = tot_now() - ptot - 8; end
    ptot = tot_now(); pv = 1;
    if (rx_done) begin ndone++; ldrop = rx_drop; ltype = rx_type; t_done = tcyc; end
    if (sync_ok) begin nok++; loff = offset; ldly = delay; end
    if (tx_last && !tx_valid) nlast++;
    if (tx_valid) begin
      if (txn == 0) begin t3_obs = tot_now(); t_tx = tcyc; end
      if (txn < 80) txf[txn] = tx_data;
      txn++;
      if (tx_last) begin ndreq++; txlen = txn; txn = 0; end
    end
  end
end

task automatic idle(input int n);
  repeat (n) @(negedge clk);
  #1;
endtask

// frame under construction
logic [7:0] fb [0:99];
int fn;
logic [7:0] dom = 0;
task automatic put(input int at, input int n, input logic [79:0] v);
  for (int i = 0; i < n; i++) fb[at + i] = v[8 * (n - 1 - i) +: 8];
endtask
function automatic int minlen(input logic [3:0] mt);
  case (mt)
    4'h0, 4'h1, 4'h8: return 44;
    4'h9:             return 54;
    4'hB:             return 64;
    default:          return 34;
  endcase
endfunction
task automatic set_ts(input longint t);
  put(48, 6, t / NS);
  put(54, 4, t % NS);
endtask
task automatic build(input logic [3:0] mt, input logic [63:0] src, input logic [15:0] port, input logic [15:0] sq,
                     input logic [63:0] corr, input bit two);
  for (int i = 0; i < 100; i++) fb[i] = 8'h00;
  fn = 14 + minlen(mt);
  put(0, 6, 48'h011B_1900_0000); put(6, 6, 48'hA0A1_A2A3_A4A5); put(12, 2, 16'h88F7);
  fb[14] = {4'h0, mt}; fb[15] = 8'h02; put(16, 2, minlen(mt)); fb[18] = dom; fb[20] = {6'b0, two, 1'b0};
  put(22, 8, corr); put(34, 8, src); put(42, 2, port); put(44, 2, sq);
endtask
task automatic ann(input logic [63:0] src, input logic [15:0] port, input logic [7:0] p1, input logic [31:0] q,
                   input logic [7:0] p2, input logic [63:0] gm);
  build(4'hB, src, port, 16'h0, 64'h0, 1'b0);
  fb[61] = p1; put(62, 4, q); fb[66] = p2; put(67, 8, gm);
endtask

// send fb[0:fn-1]; with patch the timestamp becomes (clock at the first byte) + pdelta
bit patch = 0;
longint pdelta = 0, t2_obs = 0;
task automatic send();
  for (int i = 0; i < fn; i++) begin
    @(negedge clk);
    rx_valid = 1; rx_data = fb[i]; rx_last = (i == fn - 1);
    if (i == 0) begin
      t2_obs = tot_now();
      if (patch) begin set_ts(t2_obs + pdelta); patch = 0; end
    end
  end
  @(negedge clk); rx_valid = 0; rx_last = 0; rx_data = 0;
  @(negedge clk); #1;
endtask

int n0, nq0;
task automatic rx(input logic [2:0] dexp, input string msg);
  n0 = ndone; nq0 = ndreq;
  send();
  chk(ndone == n0 + 1 && ldrop == dexp && ltype == fb[14][3:0],
      $sformatf("%s: drop %0d (got %0d, %0d done)", msg, dexp, ldrop, ndone - n0));
endtask

// wait for the DUT's Delay_Req after the last frame sent
task automatic wait_dreq();
  for (int i = 0; i < 100 && ndreq == nq0; i++) @(negedge clk);
  #1;
endtask

// one-step Sync whose t2 - t1 is o + dly; Delay_Resp whose t4 - t3 is dly - o
task automatic sync1(input logic [63:0] src, input logic [15:0] sq, input longint o, input longint dly,
                     input logic [63:0] corr);
  build(4'h0, src, 16'd1, sq, corr, 1'b0);
  patch = 1; pdelta = -(o + dly) - ($signed(corr) >>> 16);
endtask
task automatic dresp(input logic [63:0] src, input logic [15:0] sq, input longint o, input longint dly,
                     input logic [63:0] corr);
  build(4'h9, src, 16'd1, sq, corr, 1'b0);
  set_ts(t3_obs - o + dly + ($signed(corr) >>> 16));
  put(58, 8, OWN); put(66, 2, 16'd1);
endtask

int ns0;
longint t2_a;
initial begin
  idle(3);
  chk(clock_sec == 0 && clock_ns == 0 && !rx_done && !tx_valid && !sync_ok && master_id == 0, "reset values");
  rst_n = 1;
  idle(5);
  chk(nstep == 0 && tot_now() == 40, $sformatf("free-running clock 8 ns per cycle (%0d)", tot_now()));
  chk(ndone == 0 && ndreq == 0, "no frame reported or sent after reset");

  // no master selected: everything from A is dropped as not from the master
  sync1(A, 16'd1, 0, 0, 0); rx(5, "Sync before any Announce");
  build(4'h8, A, 16'd1, 16'd1, 0, 0); rx(5, "Follow_Up before any Announce");
  dresp(A, 16'd0, 0, 0, 0); rx(5, "Delay_Resp before any Announce");
  chk(master_id == 0 && ndreq == 0 && nstep == 0, "nothing selected, nothing sent");

  // best master selection
  ann(A, 16'd1, 8'd128, 32'hF8FE_FFFF, 8'd128, A); rx(0, "Announce A");
  chk(master_id == A, "A selected");
  ann(B, 16'd1, 8'd129, 32'h06FE_FFFF, 8'd1, B); rx(0, "Announce B, priority1 129");
  chk(master_id == A, "worse priority1: A kept");
  ann(B, 16'd1, 8'd128, 32'hF8FE_FFFE, 8'd255, B); rx(0, "Announce B, better clockQuality");
  chk(master_id == B, "better clockQuality: B selected");
  ann(A, 16'd1, 8'd128, 32'hF8FE_FFFE, 8'd254, A); rx(0, "Announce A, better priority2");
  chk(master_id == A, "better priority2: A selected");
  ann(C, 16'd1, 8'd128, 32'hF8FE_FFFE, 8'd254, 64'h0); rx(0, "Announce C, lower grandmasterIdentity");
  chk(master_id == C, "identity tie-break: C selected");
  ann(C, 16'd1, 8'd200, 32'hF8FE_FFFF, 8'd255, C); rx(0, "Announce C again, worse dataset");
  chk(master_id == C, "the master's own Announce updates its dataset");
  ann(A, 16'd1, 8'd199, 32'hF8FE_FFFF, 8'd255, C); rx(0, "Announce A, now better than C");
  chk(master_id == A, "A selected over C's new dataset");
  ann(A, 16'd2, 8'd199, 32'hF8FE_FFFF, 8'd255, C); rx(0, "Announce from A port 2, equal dataset");
  sync1(A, 16'd7, 0, 0, 0); fb[43] = 8'd2; rx(5, "Sync from A port 2");
  chk(nstep == 0 && ndreq == 0, "equal dataset from another port: master port kept");

  // one-step Sync, Delay_Req, Delay_Resp: slave 1 ms behind, 48 ns link
  nq0 = ndreq;
  sync1(A, 16'd7, -50000000, 48, 0); rx(0, "one-step Sync");
  t2_a = t2_obs;
  idle(2);
  chk(ndreq == nq0, "no Delay_Req before the delay");
  wait_dreq();
  chk(ndreq == nq0 + 1 && t_tx - t_done == 4, $sformatf("Delay_Req 4 clocks after the Sync (%0d)", t_tx - t_done));
  chk(txlen == 58, $sformatf("Delay_Req is 58 bytes (%0d)", txlen));
  chk({txf[0], txf[1], txf[2], txf[3], txf[4], txf[5]} == 48'h011B_1900_0000 &&
      {txf[6], txf[7], txf[8], txf[9], txf[10], txf[11]} == 48'h0011_2233_4455 && {txf[12], txf[13]} == 16'h88F7,
      "Delay_Req Ethernet header");
  chk(txf[14] == 8'h01 && txf[15] == 8'h02 && {txf[16], txf[17]} == 16'd44 && txf[18] == 8'h00 &&
      txf[20] == 0 && txf[46] == 8'h01 && txf[47] == 8'h7F, "Delay_Req message header");
  chk({txf[22], txf[23], txf[24], txf[25], txf[26], txf[27], txf[28], txf[29]} == 0, "Delay_Req correction 0");
  chk({txf[34], txf[35], txf[36], txf[37], txf[38], txf[39], txf[40], txf[41], txf[42], txf[43]} == {OWN, 16'd1},
      "Delay_Req sourcePortIdentity");
  chk({txf[44], txf[45]} == 16'd0, "first Delay_Req sequenceId 0");
  chk({txf[48], txf[49], txf[50], txf[51], txf[52], txf[53]} == t3_obs / NS &&
      {txf[54], txf[55], txf[56], txf[57]} == t3_obs % NS, $sformatf("originTimestamp = t3 (%0d)", t3_obs));
  chk(txf[19] == 0 && txf[21] == 0 && {txf[30], txf[31], txf[32], txf[33]} == 0, "reserved bytes zero");
  ns0 = nstep;
  dresp(A, 16'd0, -50000000, 48, 0); rx(0, "Delay_Resp");
  chk(nok == 1 && $signed(loff) == -50000000 && ldly == 48, $sformatf("offset -50 ms, delay 48 (%0d, %0d)",
      $signed(loff), ldly));
  chk(nstep == ns0 + 1 && lstep == 50000000, $sformatf("clock stepped +50 ms (%0d)", lstep));
  dresp(A, 16'd0, 0, 48, 0); rx(6, "second Delay_Resp for the same request");

  // two-step Sync, corrections everywhere, slave 5 us ahead, 100 ns link
  nq0 = ndreq;
  build(4'h0, A, 16'd1, 16'd8, 64'h0003_0000, 1'b1); set_ts(0); rx(0, "two-step Sync");
  t2_a = t2_obs;
  idle(10);
  chk(ndreq == nq0, "two-step: no Delay_Req before the Follow_Up");
  build(4'h8, A, 16'd1, 16'd9, 64'h0, 1'b0); set_ts(t2_a); rx(6, "Follow_Up, wrong sequenceId");
  build(4'h8, B, 16'd1, 16'd8, 64'h0, 1'b0); set_ts(t2_a); rx(5, "Follow_Up from another clock");
  build(4'h8, A, 16'd1, 16'd8, 64'h0002_0000, 1'b0); set_ts(t2_a - 5000 - 100 - 3 - 2); rx(0, "Follow_Up");
  wait_dreq();
  chk(ndreq == nq0 + 1 && {txf[44], txf[45]} == 16'd1, "second Delay_Req sequenceId 1");
  chk({txf[48], txf[49], txf[50], txf[51], txf[52], txf[53]} == t3_obs / NS &&
      {txf[54], txf[55], txf[56], txf[57]} == t3_obs % NS && txf[54] != 0,
      $sformatf("originTimestamp = t3 after the step (%0d)", t3_obs));
  build(4'h8, A, 16'd1, 16'd8, 64'h0, 1'b0); set_ts(t2_a); rx(6, "Follow_Up after the Delay_Req");
  dresp(A, 16'd0, 5000, 100, 64'h0007_0000); rx(6, "Delay_Resp, old sequenceId");
  dresp(A, 16'd1, 5000, 100, 64'h0007_0000); put(58, 8, OWN ^ 1); rx(6, "Delay_Resp, other requesting clock");
  dresp(A, 16'd1, 5000, 100, 64'h0007_0000); put(66, 2, 16'd2); rx(6, "Delay_Resp, other requesting port");
  dresp(A, 16'd1, 5000, 100, 64'h0007_0000); put(42, 2, 16'd3); rx(5, "Delay_Resp from another port");
  ns0 = nstep;
  dresp(A, 16'd1, 5000, 100, 64'h0007_0000); rx(0, "Delay_Resp, two-step");
  chk(nok == 2 && $signed(loff) == 5000 && ldly == 100, $sformatf("offset +5 us, delay 100 (%0d, %0d)",
      $signed(loff), ldly));
  chk(nstep == ns0 + 1 && lstep == -5000, $sformatf("clock stepped -5 us (%0d)", lstep));

  // asymmetric path: t2 - t1 = 300, t4 - t3 = 100
  nq0 = ndreq;
  sync1(A, 16'd9, 100, 200, 64'h0001_0000); rx(0, "one-step Sync with correction");
  wait_dreq();
  chk({txf[44], txf[45]} == 16'd2, "third Delay_Req sequenceId 2");
  dresp(A, 16'd2, 100, 200, 0); rx(0, "Delay_Resp");
  chk($signed(loff) == 100 && ldly == 200, $sformatf("offset 100, delay 200 (%0d, %0d)", $signed(loff), ldly));
  // odd sum: the mean path delay rounds down
  nq0 = ndreq;
  sync1(A, 16'd10, 0, 7, 0); rx(0, "Sync");
  wait_dreq();
  dresp(A, 16'd3, 0, 8, 0); rx(0, "Delay_Resp");
  chk(ldly == 7 && $signed(loff) == 0, $sformatf("delay (7 + 8) / 2 = 7, offset 0 (%0d, %0d)", ldly, $signed(loff)));

  // a new Sync while waiting for the Delay_Resp restarts the exchange
  nq0 = ndreq;
  sync1(A, 16'd11, 0, 10, 0); rx(0, "Sync");
  wait_dreq();
  sync1(A, 16'd12, 0, 20, 0); rx(0, "Sync again");
  nq0 = ndreq; wait_dreq();
  dresp(A, 16'd4, 0, 20, 0); rx(6, "Delay_Resp for the first Delay_Req");
  dresp(A, 16'd5, 0, 20, 0); rx(0, "Delay_Resp for the second");
  chk(ldly == 20, $sformatf("delay of the second exchange (%0d)", ldly));

  // header checks, in priority order
  sync1(A, 16'd13, 0, 0, 0); fb[0] = 8'h03; rx(1, "multicast address byte 0");
  sync1(A, 16'd13, 0, 0, 0); fb[1] = 8'h80; rx(1, "multicast address byte 1");
  sync1(A, 16'd13, 0, 0, 0); fb[2] = 8'h18; rx(1, "multicast address byte 2");
  sync1(A, 16'd13, 0, 0, 0); fb[5] = 8'h0E; rx(1, "multicast address byte 5");
  sync1(A, 16'd13, 0, 0, 0); fb[12] = 8'h08; rx(1, "EtherType high byte");
  sync1(A, 16'd13, 0, 0, 0); fb[13] = 8'hF6; rx(1, "EtherType low byte");
  sync1(A, 16'd13, 0, 0, 0); fb[12] = 8'h08; fb[15] = 8'h01; rx(1, "bad EtherType before the version");
  sync1(A, 16'd13, 0, 0, 0); fb[15] = 8'h01; rx(2, "PTP version 1");
  sync1(A, 16'd13, 0, 0, 0); fb[15] = 8'h03; rx(2, "PTP version 3");
  sync1(A, 16'd13, 0, 0, 0); fb[15] = 8'h12; rx(0, "minorVersionPTP 1 accepted");
  wait_dreq();
  sync1(A, 16'd13, 0, 0, 0); fb[15] = 8'h01; fb[18] = 8'h01; rx(2, "version before the domain");
  sync1(A, 16'd13, 0, 0, 0); fb[18] = 8'h01; rx(3, "domain 1 on a domain-0 clock");
  sync1(A, 16'd13, 0, 0, 0); fb[18] = 8'h01; put(16, 2, 16'd40); rx(3, "domain before the length");
  sync1(A, 16'd13, 0, 0, 0); put(16, 2, 16'd45); rx(4, "messageLength above the frame");
  sync1(A, 16'd13, 0, 0, 0); put(16, 2, 16'd43); rx(4, "messageLength below the frame");
  sync1(A, 16'd13, 0, 0, 0); put(16, 2, 16'd42); fn = 56; rx(4, "Sync shorter than 44");
  sync1(A, 16'd13, 0, 0, 0); put(16, 2, 16'd45); fn = 59; rx(0, "Sync with a trailing byte");
  wait_dreq();
  sync1(A, 16'd13, 0, 0, 0); put(16, 2, 16'd86); fn = 100; for (int i = 58; i < 100; i++) fb[i] = 8'hEE;
  rx(0, "100-byte Sync: bytes past the buffer ignored");
  wait_dreq();
  dresp(A, 16'd0, 0, 0, 0); put(16, 2, 16'd52); fn = 66; rx(4, "Delay_Resp shorter than 54");
  ann(A, 16'd1, 8'd1, 32'h0, 8'd1, A); put(16, 2, 16'd62); fn = 76; rx(4, "Announce shorter than 64");
  build(4'h0, A, 16'd1, 16'd13, 0, 0); put(48, 6, 48'd5); put(54, 4, 32'd1000000000); rx(4, "nanoseconds 10^9");
  build(4'h0, A, 16'd1, 16'd13, 0, 0); put(48, 6, 48'd5); put(54, 4, 32'd999999999); rx(0, "nanoseconds 10^9 - 1");
  wait_dreq();
  build(4'h8, A, 16'd1, 16'd13, 0, 0); put(54, 4, 32'hFFFF_FFFF); rx(4, "Follow_Up nanoseconds overflow");
  build(4'h9, A, 16'd1, 16'd13, 0, 0); put(54, 4, 32'hFFFF_FFFF); rx(4, "Delay_Resp nanoseconds overflow");
  ann(A, 16'd1, 8'd1, 32'h0, 8'd1, A); put(54, 4, 32'hFFFF_FFFF); rx(4, "Announce nanoseconds overflow");
  build(4'h1, A, 16'd1, 16'd13, 0, 0); put(54, 4, 32'hFFFF_FFFF); rx(4, "Delay_Req nanoseconds overflow");
  build(4'hC, A, 16'd1, 16'd13, 0, 0); put(16, 2, 16'd34); fn = 48; rx(7, "Signaling: unsupported");
  build(4'hC, A, 16'd1, 16'd13, 0, 0); put(16, 2, 16'd33); fn = 47; rx(4, "Signaling shorter than 34");
  build(4'h2, A, 16'd1, 16'd13, 0, 0); put(16, 2, 16'd44); fn = 58; put(54, 4, 32'hFFFF_FFFF);
  rx(7, "Pdelay_Req: unsupported, no timestamp check");
  build(4'h1, A, 16'd1, 16'd13, 0, 0); rx(7, "Delay_Req received: unsupported");
  build(4'h0, A, 16'd1, 16'd13, 0, 0); fb[14] = 8'h10; rx(0, "majorSdoId ignored");
  wait_dreq();

  // domain input
  dom = 8'd5; domain = 8'd5; idle(1);
  sync1(A, 16'd14, 0, 0, 0); fb[18] = 8'd0; rx(3, "domain-0 Sync on a domain-5 clock");
  ann(A, 16'd1, 8'd1, 32'h0, 8'd1, A); fb[18] = 8'd0; rx(3, "domain-0 Announce on a domain-5 clock");
  sync1(A, 16'd14, 0, 0, 0); fb[18] = 8'd5; rx(0, "domain 5 Sync accepted");
  wait_dreq();
  chk(txf[18] == 8'd5, "Delay_Req carries domainNumber 5");
  dom = 8'd0; domain = 8'd0; idle(1);

  // reset clears the master, the exchange and the clock
  rst_n = 0; idle(2);
  chk(master_id == 0 && clock_sec == 0 && clock_ns == 0 && !tx_valid, "reset clears the clock and the master");
  rst_n = 1; idle(2);
  sync1(A, 16'd1, 0, 0, 0); rx(5, "after reset no master is selected");
  ann(A, 16'd1, 8'd128, 32'h0, 8'd128, A); rx(0, "Announce A");
  nq0 = ndreq;
  sync1(A, 16'd1, 0, 0, 0); rx(0, "Sync");
  wait_dreq();
  chk({txf[44], txf[45]} == 16'd0, "Delay_Req sequenceId restarts at 0");
  dresp(A, 16'd0, 0, 0, 0); rx(0, "Delay_Resp with no delay");
  chk(ldly == 0 && loff == 0, "zero offset, zero delay");
  // seconds field: the slave is 3 s behind, so the step makes the next originTimestamp carry seconds 3
  sync1(A, 16'd2, -64'sd3000000000, 0, 0); rx(0, "Sync, slave 3 s behind");
  wait_dreq();
  dresp(A, 16'd1, -64'sd3000000000, 0, 0); rx(0, "Delay_Resp");
  chk(lstep == 64'sd3000000000, $sformatf("clock stepped +3 s (%0d)", lstep));
  nq0 = ndreq;
  sync1(A, 16'd3, 0, 0, 0); rx(0, "Sync after the step");
  wait_dreq();
  chk(t3_obs / NS == 3 && {txf[48], txf[49], txf[50], txf[51], txf[52], txf[53]} == 3 &&
      {txf[54], txf[55], txf[56], txf[57]} == t3_obs % NS, $sformatf("originTimestamp seconds 3 (%0d)", t3_obs));

  chk(nlast == 0, $sformatf("tx_last only with tx_valid (%0d)", nlast));
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
"""
