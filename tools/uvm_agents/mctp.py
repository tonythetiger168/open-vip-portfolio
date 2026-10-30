# DMTF MCTP over SMBus agent (DSP0236 MCTP base 1.3, DSP0237 SMBus/I2C
# transport binding 1.2). The agent is an MCTP endpoint sending messages as
# SMBus block writes: slave address, command code 0x0F, byte count, source
# slave address, MCTP header (version 1, destination EID, source EID,
# SOM / EOM / packet sequence / TO / message tag), the packet's part of the
# message, PEC (CRC-8). A message longer than the packet payload (cfg.mtu) is
# split into packets with SOM on the first, EOM on the last and the sequence
# number counting up modulo 4.
# tb/top_tb.sv mctp_model: an SMBus target at 7-bit address 0x1D with EID
# 0x1D that ACKs every byte addressed to it, checks each packet and reassembles
# messages. It reports one clock after STOP, once per message: the message
# type, the payload length and CRC-32 (payload after the type byte), the tag /
# TO / source EID, and an error code: 1 = PEC, 2 = packet sequence, 4 = format
# (command code, byte count, header version, source address), 8 = not addressed
# to this endpoint (destination EID not 0x1D, 0x00 or 0xFF). After an error the
# rest of that message is dropped without another report.

MCTP_FUNCS = """
// SMBus PEC: CRC-8, x^8 + x^2 + x + 1, init 0, MSB first
function automatic bit [7:0] crc8(bit [7:0] c, bit [7:0] b);
  c ^= b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction
// IEEE CRC-32 step (reflected), for the payload fingerprint
function automatic bit [31:0] crc32_byte(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction
localparam bit [6:0] MCTP_DEV_ADDR = 7'h1D;
localparam bit [7:0] MCTP_DEV_EID  = 8'h1D;
localparam bit [6:0] MCTP_SRC_ADDR = 7'h10;
localparam bit [7:0] MCTP_SRC_EID  = 8'h08;
"""

SPEC = dict(
    vip="MCTP-UVM-VIP", p="mctp", P="MCTP over SMBus", dir="mctp", family="Power / Management",
    desc="DMTF MCTP over SMBus endpoint VIP (DSP0236 / DSP0237): SMBus block-write packets with PEC, MCTP "
         "transport header, SOM / EOM fragmentation, packet sequence numbers, message tags, EID addressing.",
    about="""
MCTP is the management transport between a BMC and the devices of a server
(NICs, SSDs, GPUs, power supplies); PLDM, SPDM and NVMe-MI messages travel over
it. Over SMBus every MCTP packet is one block write carrying the transport
header, and a message larger than the packet payload is split into packets
marked SOM / EOM with a 2-bit sequence number. The DUT model is an endpoint
that checks every packet (PEC, command code, byte count, header version,
sequence) and reassembles the messages; the scoreboard predicts its report from
the message the agent sent, including the packet a planted PEC or sequence
fault lands in. The monitor rebuilds messages from the SCL/SDA wires alone.""",
    defs=MCTP_FUNCS,
    timeout=400,
    interface="""
// Open-drain bus: each side pulls low (0) or releases (1).
interface mctp_if (input logic clk);
  logic rst_n;

  logic scl_m, sda_m;     // agent side
  logic scl_o, sda_o;     // endpoint (DUT) side
  logic rep_valid;
  logic [7:0] rep_type, rep_len, rep_seid;
  logic [31:0] rep_crc;
  logic [2:0] rep_tag;
  logic rep_to;
  logic [3:0] rep_err;
  wire  scl = scl_m & scl_o;
  wire  sda = sda_m & sda_o;

  clocking drv_cb @(posedge clk);
    input rst_n, scl, sda;
    inout scl_m, sda_m;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, scl, sda, rep_valid, rep_type, rep_len, rep_seid, rep_crc, rep_tag, rep_to, rep_err;
  endclocking
endinterface
""",
    ports=[("in", "logic", "scl"), ("in", "logic", "sda"),
           ("out", "logic", "scl_o"), ("out", "logic", "sda_o"),
           ("out", "logic", "rep_valid"), ("out", "logic [7:0]", "rep_type"), ("out", "logic [7:0]", "rep_len"),
           ("out", "logic [7:0]", "rep_seid"), ("out", "logic [31:0]", "rep_crc"), ("out", "logic [2:0]", "rep_tag"),
           ("out", "logic", "rep_to"), ("out", "logic [3:0]", "rep_err")],
    cfg="int unsigned half = 4;    // system clocks per SCL half period\n"
        "int unsigned mtu  = 16;   // message bytes per packet (DSP0237 baseline is 64)",
    fields=[
        ("bit [7:0]", "deid", "req"),               # destination EID
        ("bit [7:0]", "mtype", "req"),              # message type byte (IC = 0)
        ("bit [2:0]", "mtag", "req"),
        ("bit", "to", "req"),
        ("bit [7:0]", "payload", "req", "q"),
        ("bit [3:0]", "bad_pkt", "req"),            # packet sent with a wrong PEC, 15 = none
        ("bit [3:0]", "skip_pkt", "req"),           # packet whose sequence number skips one, 15 = none
        ("bit [1:0]", "seq0", "req"),
        ("bit [7:0]", "rlen", "rsp"),
        ("bit [31:0]", "rcrc", "rsp"),
        ("bit [7:0]", "rtype", "rsp"),
        ("bit [7:0]", "rseid", "rsp"),
        ("bit [2:0]", "rtag", "rsp"),
        ("bit", "rto", "rsp"),
        ("bit [3:0]", "err", "rsp"),
        ("bit [5:0]", "nbytes", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [1:0]", "fault", "info", "rand"),
    ],
    constraints="""
constraint c_eid  { deid dist { 8'h1D := 12, 8'hFF := 2, 8'h00 := 2, 8'h42 := 1 }; }
constraint c_type { mtype dist { 8'h00 := 3, 8'h01 := 2, 8'h02 := 1, 8'h04 := 2, 8'h05 := 2, 8'h7E := 1, 8'h7F := 1 }; }
constraint c_len  { nbytes inside {[0:47]}; fault dist { 0 := 6, 1 := 1, 2 := 1 }; }
""",
    tr_functions="""
function int unsigned npkt(int unsigned mtu = 16);
  return (payload.size() + 1 + mtu - 1) / mtu;     // the type byte is message byte 0
endfunction

function void post_randomize();
  bit [31:0] x = seed | 32'h1;
  payload.delete();
  for (int unsigned i = 0; i < nbytes; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    payload.push_back(x[7:0]);
  end
  bad_pkt = 15; skip_pkt = 15;
  if (fault == 1) bad_pkt = x[11:8] % npkt();
  if (fault == 2 && npkt() > 1) skip_pkt = 1 + x[15:12] % (npkt() - 1);
endfunction
""",
    drv_rsp=False,
    drv_desc="splits each message into SMBus block-write packets (SOM / EOM, sequence numbers, PEC) and drives them bit by bit on the open-drain bus",
    drv_idle="""
vif.drv_cb.scl_m <= 1'b1;
vif.drv_cb.sda_m <= 1'b1;
""",
    drv_tasks="""
task wait_clk(int unsigned n); repeat (n) @(vif.drv_cb); endtask
task scl_high();
  int unsigned to = 0;
  vif.drv_cb.scl_m <= 1'b1;
  @(vif.drv_cb);
  while (vif.drv_cb.scl !== 1'b1 && to < cfg.timeout_cycles) begin @(vif.drv_cb); to++; end
  if (vif.drv_cb.scl !== 1'b1) `uvm_error("TIMEOUT", "MCTP/SMBus: SCL held low")
endtask
task bit_xfer(bit out, output bit in);
  vif.drv_cb.sda_m <= out; wait_clk(cfg.half / 2);
  scl_high(); wait_clk(cfg.half / 2);
  in = vif.drv_cb.sda;
  wait_clk(cfg.half / 2);
  vif.drv_cb.scl_m <= 1'b0; wait_clk(cfg.half / 2);
endtask
task wr_byte(bit [7:0] b, output bit ack);
  bit in;
  for (int i = 7; i >= 0; i--) bit_xfer(b[i], in);
  bit_xfer(1'b1, in);
  ack = !in;
endtask
""",
    drv_item="""
bit [7:0] msg[$];
int unsigned np, off = 0;
bit [1:0] seq = t.seq0;
msg.push_back(t.mtype);
foreach (t.payload[i]) msg.push_back(t.payload[i]);
np = (msg.size() + cfg.mtu - 1) / cfg.mtu;
for (int unsigned p = 0; p < np; p++) begin
  bit [7:0] pk[$];
  bit [7:0] crc = 0;
  int unsigned n = (msg.size() - off < cfg.mtu) ? msg.size() - off : cfg.mtu;
  bit ack;
  if (p == t.skip_pkt) seq++;
  pk.push_back({MCTP_DEV_ADDR, 1'b0});
  pk.push_back(8'h0F);                                   // MCTP command code
  pk.push_back(8'(n + 5));                               // byte count
  pk.push_back({MCTP_SRC_ADDR, 1'b1});                   // source slave address
  pk.push_back(8'h01);                                   // header version 1
  pk.push_back(t.deid);
  pk.push_back(MCTP_SRC_EID);
  pk.push_back({p == 0, p == np - 1, seq, t.to, t.mtag});
  for (int unsigned i = 0; i < n; i++) pk.push_back(msg[off + i]);
  foreach (pk[i]) crc = crc8(crc, pk[i]);
  pk.push_back(crc ^ {7'h0, p == t.bad_pkt});
  off += n; seq++;
  // START, bytes, STOP
  @(vif.drv_cb);
  vif.drv_cb.sda_m <= 1'b0; wait_clk(cfg.half);
  vif.drv_cb.scl_m <= 1'b0; wait_clk(cfg.half / 2);
  foreach (pk[i]) begin
    wr_byte(pk[i], ack);
    if (!ack) `uvm_error("DRV", $sformatf("MCTP/SMBus: byte %0d of packet %0d NACKed", i, p))
  end
  vif.drv_cb.sda_m <= 1'b0; wait_clk(cfg.half / 2);
  scl_high(); wait_clk(cfg.half);
  vif.drv_cb.sda_m <= 1'b1; wait_clk(3 * cfg.half);
end
""",
    mon_desc="SMBus packets decoded from the SCL/SDA wires, joined into MCTP messages by SOM / EOM; completed by the endpoint's report",
    mon_members="mctp_transaction cur, msg_q[$], rep_q[$]; bit [7:0] pk[$]; int unsigned npk; bit [1:0] seq_exp;",
    mon_run="""
bit scl_p = 1, sda_p = 1, in_xfer = 0;
int unsigned nbit = 0;
bit [7:0] sh = 0;
forever begin
  bit scl, sda;
  @(vif.mon_cb);
  scl = vif.mon_cb.scl; sda = vif.mon_cb.sda;
  if (vif.mon_cb.rep_valid) begin
    mctp_transaction r = mctp_transaction::type_id::create("r");
    r.rtype = vif.mon_cb.rep_type; r.rlen = vif.mon_cb.rep_len; r.rcrc = vif.mon_cb.rep_crc;
    r.rseid = vif.mon_cb.rep_seid; r.rtag = vif.mon_cb.rep_tag; r.rto = vif.mon_cb.rep_to;
    r.err = vif.mon_cb.rep_err;
    rep_q.push_back(r);
  end
  if (scl && scl_p && sda_p && !sda) begin in_xfer = 1; nbit = 0; pk.delete(); end
  else if (scl && scl_p && !sda_p && sda) begin
    if (in_xfer) packet();
    in_xfer = 0;
  end else if (in_xfer && scl && !scl_p) begin
    if (nbit < 8) sh = {sh[6:0], sda}; else pk.push_back(sh);
    nbit = (nbit == 8) ? 0 : nbit + 1;
  end
  scl_p = scl; sda_p = sda;
  while (msg_q.size() != 0 && rep_q.size() != 0) begin
    mctp_transaction t = msg_q.pop_front(), r = rep_q.pop_front();
    t.rtype = r.rtype; t.rlen = r.rlen; t.rcrc = r.rcrc; t.rseid = r.rseid; t.rtag = r.rtag; t.rto = r.rto;
    t.err = r.err;
    publish(t);
  end
end
""",
    mon_tasks="""
// one SMBus packet: header fields, the PEC, the sequence number
function void packet();
  bit [7:0] crc = 0;
  bit som, eom;
  bit [1:0] seq;
  if (pk.size() < 9) begin
    `uvm_error("MON", $sformatf("MCTP: packet of %0d bytes", pk.size()))
    return;
  end
  for (int i = 0; i + 1 < pk.size(); i++) crc = crc8(crc, pk[i]);
  som = pk[7][7]; eom = pk[7][6]; seq = pk[7][5:4];
  if (som) begin
    cur = mctp_transaction::type_id::create("t");
    cur.deid = pk[5]; cur.mtag = pk[7][2:0]; cur.to = pk[7][3]; cur.seq0 = seq;
    cur.mtype = pk[8]; cur.bad_pkt = 15; cur.skip_pkt = 15;
    npk = 0; seq_exp = seq;
  end
  if (cur == null) begin
    `uvm_error("MON", "MCTP: packet without SOM before it")
    return;
  end
  if (seq != seq_exp && cur.skip_pkt == 15) cur.skip_pkt = npk;
  if (pk[pk.size() - 1] != crc && cur.bad_pkt == 15) cur.bad_pkt = npk;
  for (int i = som ? 9 : 8; i + 1 < pk.size(); i++) cur.payload.push_back(pk[i]);
  if (pk[1] != 8'h0F || pk[2] != pk.size() - 4 || pk[4] != 8'h01 || pk[0] != {MCTP_DEV_ADDR, 1'b0})
    `uvm_error("MON", "MCTP: packet format (command code, byte count, version or address)")
  seq_exp = seq + 1; npk++;
  if (eom) begin msg_q.push_back(cur); cur = null; end
endfunction
""",
    predict="""
bit [31:0] c = 32'hFFFF_FFFF;
int unsigned np = t.npkt();
t.err = 0;
if (!(t.deid inside {8'h1D, 8'h00, 8'hFF})) t.err = 8;
else if (t.bad_pkt < np && (t.skip_pkt >= np || t.bad_pkt <= t.skip_pkt)) t.err = 1;
else if (t.skip_pkt < np) t.err = 2;
// the endpoint reports the header fields of the message it saw; the length
// and CRC only for a complete message
t.rtype = t.mtype; t.rseid = MCTP_SRC_EID; t.rtag = t.mtag; t.rto = t.to;
t.rlen = 0; t.rcrc = 0;
if (t.err == 0) begin
  foreach (t.payload[i]) c = crc32_byte(c, t.payload[i]);
  t.rlen = t.payload.size(); t.rcrc = ~c;
end
""",
    checks="""
if (t.err == 4) fail(t, "endpoint rejected the packet format");
""",
    coverage="""
cp_npkt : coverpoint tr.npkt() { bins one = {1}; bins two = {2}; bins more = {[3:4]}; }
cp_type : coverpoint tr.mtype { bins control = {0}; bins pldm = {1}; bins ncsi = {2}; bins nvme = {4}; bins spdm = {5}; bins vdm = {[8'h7E:8'h7F]}; bins other = default; }
cp_eid  : coverpoint tr.deid { bins mine = {8'h1D}; bins null_ = {0}; bins bcast = {8'hFF}; bins other = default; }
cp_err  : coverpoint tr.err { bins ok = {0}; bins pec = {1}; bins seq = {2}; bins eid = {8}; }
cp_seq0 : coverpoint tr.seq0;
x_err_n : cross cp_err, cp_npkt { ignore_bins one_seq = binsof(cp_err.seq) && binsof(cp_npkt.one); ignore_bins eid_n = binsof(cp_err.eid) && !binsof(cp_npkt.one); }
""",
    directed="""
// the CRC-32 check string in one packet, every sequence start, a message of
// exactly one packet payload, then two / three packets, broadcast and null
// EIDs, a message for another endpoint, and planted PEC / sequence faults
begin
  string cv = "123456789";
  t = item(); t.deid = 8'h1D; t.mtype = 8'h7E; t.bad_pkt = 15; t.skip_pkt = 15;
  foreach (cv[i]) t.payload.push_back(cv[i]);
  send(t);
end
for (int s = 0; s < 4; s++) begin
  t = item(); t.deid = 8'h1D; t.mtype = 8'h01; t.seq0 = s; t.mtag = s; t.to = s[0]; t.bad_pkt = 15; t.skip_pkt = 15;
  repeat (15 + 16 * s[0]) t.payload.push_back(8'(s * 7));
  send(t);
end
t = item(); t.deid = 8'hFF; t.mtype = 8'h00; t.payload = '{8'h80, 8'h02}; t.bad_pkt = 15; t.skip_pkt = 15; send(t);
t = item(); t.deid = 8'h00; t.mtype = 8'h00; t.payload = '{8'h80, 8'h01, 8'h00, 8'h1D}; t.bad_pkt = 15; t.skip_pkt = 15; send(t);
t = item(); t.deid = 8'h33; t.mtype = 8'h05; repeat (20) t.payload.push_back(8'h5A); t.bad_pkt = 15; t.skip_pkt = 15; send(t);
t = item(); t.deid = 8'h1D; t.mtype = 8'h05; repeat (40) t.payload.push_back(8'hA5); t.bad_pkt = 0; t.skip_pkt = 15; send(t);
t = item(); t.deid = 8'h1D; t.mtype = 8'h05; repeat (40) t.payload.push_back(8'hA5); t.bad_pkt = 2; t.skip_pkt = 15; send(t);
t = item(); t.deid = 8'h1D; t.mtype = 8'h04; repeat (40) t.payload.push_back(8'h3C); t.bad_pkt = 15; t.skip_pkt = 1; send(t);
t = item(); t.deid = 8'h1D; t.mtype = 8'h04; repeat (40) t.payload.push_back(8'h3C); t.bad_pkt = 15; t.skip_pkt = 2; send(t);
t = item(); t.deid = 8'h1D; t.mtype = 8'h00; t.bad_pkt = 15; t.skip_pkt = 15; send(t);   // type byte only
""",
    drain_ns=20000,
    model="""
module mctp_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        scl,
  input  logic        sda,
  output logic        scl_o,
  output logic        sda_o,
  output logic        rep_valid,
  output logic [7:0]  rep_type,
  output logic [7:0]  rep_len,
  output logic [7:0]  rep_seid,
  output logic [31:0] rep_crc,
  output logic [2:0]  rep_tag,
  output logic        rep_to,
  output logic [3:0]  rep_err
);
  localparam logic [6:0] ADDR = 7'h1D;
  localparam logic [7:0] EID  = 8'h1D;
  logic scl_d, sda_d, active, mine;
  logic [3:0] nbit;
  logic [7:0] sh, nb, cnt, pec;
  // packet fields
  logic [7:0] f_cmd, f_src, f_ver, f_deid, f_seid, f_flags, f_last, f_type;
  // message assembly
  logic        asm_on, dropping;
  logic [1:0]  seq_exp;
  logic [7:0]  m_len, m_type, m_seid;
  logic [2:0]  m_tag;
  logic        m_to;
  logic [31:0] m_crc, p_crc;
  logic [7:0]  p_len;

  function automatic logic [7:0] crc8(input logic [7:0] c, input logic [7:0] b);
    c = c ^ b;
    for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
    return c;
  endfunction
  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    c = c ^ {24'h0, b};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
    return c;
  endfunction

  assign scl_o = 1'b1;

  wire start_c = scl && scl_d && sda_d && !sda;
  wire stop_c  = scl && scl_d && !sda_d && sda;
  wire scl_r   = scl && !scl_d;
  wire scl_f   = !scl && scl_d;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      scl_d <= 1'b1; sda_d <= 1'b1; active <= 1'b0; mine <= 1'b0; nbit <= '0; sh <= '0; nb <= '0;
      cnt <= '0; pec <= '0; sda_o <= 1'b1;
      f_cmd <= '0; f_src <= '0; f_ver <= '0; f_deid <= '0; f_seid <= '0; f_flags <= '0; f_last <= '0; f_type <= '0;
      asm_on <= 1'b0; dropping <= 1'b0; seq_exp <= '0; m_len <= '0; m_type <= '0; m_seid <= '0;
      m_tag <= '0; m_to <= 1'b0; m_crc <= '1; p_crc <= '1; p_len <= '0;
      rep_valid <= 1'b0; rep_type <= '0; rep_len <= '0; rep_seid <= '0; rep_crc <= '0; rep_tag <= '0;
      rep_to <= 1'b0; rep_err <= '0;
    end else begin
      scl_d <= scl; sda_d <= sda;
      rep_valid <= 1'b0;
      if (start_c) begin
        active <= 1'b1; mine <= 1'b0; nbit <= '0; nb <= '0; pec <= '0; p_len <= '0; sda_o <= 1'b1;
      end else if (stop_c) begin
        active <= 1'b0; sda_o <= 1'b1;
        if (mine) begin : pkt_end
          logic som, eom;
          logic [3:0] e;
          som = f_flags[7]; eom = f_flags[6];
          e = 4'd0;
          if (f_cmd != 8'h0F || cnt != nb - 8'd4 || f_ver != 8'h01 || !f_src[0]) e = 4'd4;
          else if (pec != 8'h00) e = 4'd1;                 // PEC folded in: residue 0
          if (som) begin
            if (!(f_deid == EID || f_deid == 8'h00 || f_deid == 8'hFF) && e == 0) e = 4'd8;
            m_type <= f_type; m_seid <= f_seid; m_tag <= f_flags[2:0]; m_to <= f_flags[3];
          end else if (!asm_on) e = 4'd0;                  // the rest of a dropped message
          else if (f_flags[5:4] != seq_exp && e == 0) e = 4'd2;
          if (som || asm_on) begin
            if (e != 0) begin
              asm_on <= 1'b0;
              rep_valid <= 1'b1; rep_err <= e; rep_len <= '0; rep_crc <= '0;
              rep_type <= som ? f_type : m_type; rep_seid <= som ? f_seid : m_seid;
              rep_tag <= som ? f_flags[2:0] : m_tag; rep_to <= som ? f_flags[3] : m_to;
            end else begin
              logic [31:0] c;
              logic [7:0] l;
              c = p_crc;
              l = p_len;
              seq_exp <= f_flags[5:4] + 2'd1;
              if (eom) begin
                asm_on <= 1'b0;
                rep_valid <= 1'b1; rep_err <= 4'd0; rep_len <= l; rep_crc <= ~c;
                rep_type <= som ? f_type : m_type; rep_seid <= som ? f_seid : m_seid;
                rep_tag <= som ? f_flags[2:0] : m_tag; rep_to <= som ? f_flags[3] : m_to;
              end else begin
                asm_on <= 1'b1; m_crc <= c; m_len <= l;
              end
            end
          end
        end
      end else if (active) begin
        if (scl_r) begin
          if (nbit < 4'd8) sh <= {sh[6:0], sda};
          nbit <= nbit + 4'd1;
        end else if (scl_f && nbit == 4'd8) begin : byte_done
          // a whole byte (sh): ACK it if the packet is for this address
          logic ack;
          ack = (nb == 0) ? (sh == {ADDR, 1'b0}) : mine;
          if (nb == 0) mine <= ack;
          sda_o <= !ack;
          pec <= crc8(pec, sh);
          case (nb)
            8'd1: f_cmd <= sh;
            8'd2: cnt <= sh;
            8'd3: f_src <= sh;
            8'd4: f_ver <= sh;
            8'd5: f_deid <= sh;
            8'd6: f_seid <= sh;
            8'd7: begin
                    f_flags <= sh;
                    p_crc <= sh[7] ? 32'hFFFF_FFFF : m_crc;
                    p_len <= sh[7] ? 8'd0 : m_len;
                  end
            default: ;
          endcase
          if (nb == 8'd8 && f_flags[7]) f_type <= sh;
          // bytes from 8 on: the previous one was message payload (the last
          // byte of the packet is the PEC, never folded in), except the
          // type byte of a SOM packet
          if (nb >= 8'd9 && !(nb == 8'd9 && f_flags[7])) begin
            p_crc <= crc32_byte(p_crc, f_last);
            p_len <= p_len + 8'd1;
          end
          if (nb >= 8'd8) f_last <= sh;
          nb <= nb + 8'd1;
        end else if (scl_f && nbit == 4'd9) begin   // ACK clock done: release SDA
          sda_o <= 1'b1; nbit <= '0;
        end
      end
    end
  end
endmodule
""",
    sva="""
logic scl_d, sda_d;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin scl_d <= 1'b1; sda_d <= 1'b1; end else begin scl_d <= scl; sda_d <= sda; end
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({scl, sda, rep_valid}))
  else $error("MCTP/SMBus: X on SCL / SDA / report");
// the endpoint never pulls SCL low (no stretching) and only drives SDA low while SCL is low or for an ACK
assert property (@(posedge clk) disable iff (!rst_n) scl_o)
  else $error("MCTP/SMBus: endpoint holds SCL");
// SDA from the endpoint does not change while SCL is high
assert property (@(posedge clk) disable iff (!rst_n) scl && scl_d |-> $stable(sda_o))
  else $error("MCTP/SMBus: endpoint changed SDA while SCL high");
// a report only follows a STOP
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> $past(scl && sda && !sda_d))
  else $error("MCTP: report without a STOP");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 0 && rep_len > 15);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 1);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 2);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic scl_m = 1, sda_m = 1;
wire scl_o, sda_o, rep_valid, rep_to;
wire scl = scl_m & scl_o;
wire sda = sda_m & sda_o;
wire [7:0] rep_type, rep_len, rep_seid;
wire [31:0] rep_crc;
wire [2:0] rep_tag;
wire [3:0] rep_err;

always #5 clk = ~clk;

mctp_model u_dut (.clk(clk), .rst_n(rst_n), .scl(scl), .sda(sda), .scl_o(scl_o), .sda_o(sda_o),
                  .rep_valid(rep_valid), .rep_type(rep_type), .rep_len(rep_len), .rep_seid(rep_seid),
                  .rep_crc(rep_crc), .rep_tag(rep_tag), .rep_to(rep_to), .rep_err(rep_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

int nrep = 0;
logic [7:0] r_type, r_len, r_seid; logic [31:0] r_crc; logic [2:0] r_tag; logic r_to; logic [3:0] r_err;
always @(posedge clk) if (rep_valid) begin
  nrep++; r_type = rep_type; r_len = rep_len; r_seid = rep_seid; r_crc = rep_crc; r_tag = rep_tag;
  r_to = rep_to; r_err = rep_err;
end

function automatic bit [7:0] crc8(bit [7:0] c, bit [7:0] b);
  c ^= b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction

// the endpoint changes SDA only while SCL is low
logic scl_q = 1'b1, sdao_q = 1'b1;
int sda_glitch = 0;
always @(posedge clk) begin
  if (rst_n && scl && scl_q && sda_o !== sdao_q) sda_glitch++;
  scl_q <= scl; sdao_q <= sda_o;
end

// SMBus master, 8 clocks per SCL period
int nack = 0;
task automatic w(input int n); repeat (n) @(posedge clk); #1; endtask
task automatic tx_byte(input bit [7:0] b);
  for (int i = 7; i >= 0; i--) begin
    sda_m = b[i]; w(2); scl_m = 1; w(4); scl_m = 0; w(2);
  end
  sda_m = 1; w(2); scl_m = 1; w(2);
  if (sda !== 1'b0) nack++;
  w(2); scl_m = 0; w(2);
endtask
bit [7:0] pk[$];
task automatic packet(input bit [7:0] addr8, input bit [7:0] cmd, input bit [7:0] deid, input bit som,
                      input bit eom, input bit [1:0] seq, input bit [2:0] tag, input bit to, input string data,
                      input bit bad_pec = 0, input int cnt_adj = 0, input bit [7:0] ver = 8'h01,
                      input int ctl = -1);   // ctl >= 0: a type byte (may be 0x00) before data
  bit [7:0] c = 0;
  pk.delete();
  pk.push_back(addr8); pk.push_back(cmd); pk.push_back(8'(data.len() + (ctl >= 0) + 5 + cnt_adj)); pk.push_back(8'h21);
  pk.push_back(ver); pk.push_back(deid); pk.push_back(8'h08); pk.push_back({som, eom, seq, to, tag});
  if (ctl >= 0) pk.push_back(8'(ctl));
  for (int i = 0; i < data.len(); i++) pk.push_back(data[i]);
  foreach (pk[i]) c = crc8(c, pk[i]);
  pk.push_back(c ^ {7'h0, bad_pec});
  sda_m = 0; w(4); scl_m = 0; w(2);
  foreach (pk[i]) tx_byte(pk[i]);
  sda_m = 0; w(2); scl_m = 1; w(4); sda_m = 1; w(10);
endtask
task automatic wait_rep(input int prev);
  int n = 0;
  while (nrep == prev && n < 5) begin @(posedge clk); n++; end
  #1;
endtask

initial begin
  int b;
  bit [7:0] c = 0;
  string s9 = "123456789";
  for (int i = 0; i < s9.len(); i++) c = crc8(c, s9[i]);
  chk(c == 8'hF4, $sformatf("CRC-8/SMBUS check value of 123456789 = 0xF4 (%h)", c));
  repeat (3) @(posedge clk);
  chk(sda === 1'b1 && scl === 1'b1, "bus released during reset");
  rst_n = 1;
  w(5);
  chk(rep_valid === 1'b0 && nrep == 0 && sda === 1'b1 && scl === 1'b1, "idle bus, no report");
  // no message open after reset: a packet without SOM is dropped
  packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd0, 3'd0, 0, "zz"); w(5);
  chk(nrep == 0, "packet without SOM right after reset: dropped");

  // one-packet message: type 0x7E, payload "123456789"
  b = nrep; nack = 0;
  packet(8'h3A, 8'h0F, 8'h1D, 1, 1, 2'd1, 3'd5, 1, {"~", s9});
  wait_rep(b);
  chk(nack == 0, "every byte ACKed");
  chk(nrep == b + 1 && r_err == 0 && r_type == 8'h7E && r_len == 9 && r_crc == 32'hCBF4_3926,
      $sformatf("single packet: type 7E, 9 bytes, CRC-32 0xCBF43926 (%0d %h %0d %h)", r_err, r_type, r_len, r_crc));
  chk(r_tag == 3'd5 && r_to === 1'b1 && r_seid == 8'h08, "tag, TO and source EID reported");
  // the EOM closed the message: a following packet without SOM is dropped
  b = nrep; packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd2, 3'd5, 1, "zz"); w(5);
  chk(nrep == b, "packet without SOM after an EOM: dropped");

  // three packets: 1234 | 5678 | 9
  b = nrep;
  packet(8'h3A, 8'h0F, 8'h1D, 1, 0, 2'd3, 3'd2, 0, "~1234");
  chk(nrep == b, "no report before EOM");
  packet(8'h3A, 8'h0F, 8'h1D, 0, 0, 2'd0, 3'd2, 0, "5678");
  packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd1, 3'd2, 0, "9");
  wait_rep(b);
  chk(nrep == b + 1 && r_err == 0 && r_len == 9 && r_crc == 32'hCBF4_3926, "three packets reassembled, sequence 3, 0, 1");

  // PEC error in the middle packet: reported there, the EOM packet dropped
  b = nrep;
  packet(8'h3A, 8'h0F, 8'h1D, 1, 0, 2'd0, 3'd1, 0, "~1234");
  packet(8'h3A, 8'h0F, 8'h1D, 0, 0, 2'd1, 3'd1, 0, "5678", 1);
  wait_rep(b);
  chk(nrep == b + 1 && r_err == 1, "PEC error reported");
  packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd2, 3'd1, 0, "9");
  w(5);
  chk(nrep == b + 1, "the rest of the message dropped without a report");

  // sequence skip
  b = nrep;
  packet(8'h3A, 8'h0F, 8'h1D, 1, 0, 2'd2, 3'd0, 0, "~1234");
  packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd0, 3'd0, 0, "5678");
  wait_rep(b);
  chk(r_err == 2, "packet sequence 2 then 0: sequence error");

  // not addressed: other EID; broadcast and null accepted
  b = nrep; packet(8'h3A, 8'h0F, 8'h42, 1, 1, 2'd0, 3'd0, 0, "~x"); wait_rep(b);
  chk(r_err == 8, "destination EID 0x42: not for this endpoint");
  b = nrep; packet(8'h3A, 8'h0F, 8'hFF, 1, 1, 2'd0, 3'd0, 0, {8'h80, 8'h02}, 0, 0, 8'h01, 0); wait_rep(b);
  chk(r_err == 0 && r_type == 8'h00 && r_len == 2, "broadcast EID: control message accepted");
  b = nrep; packet(8'h3A, 8'h0F, 8'h00, 1, 1, 2'd0, 3'd0, 0, "", 0, 0, 8'h01, 0); wait_rep(b);
  chk(r_err == 0 && r_len == 0 && r_crc == 32'h0, "null EID, type byte only: empty payload");

  // format errors: command code, byte count, version
  b = nrep; packet(8'h3A, 8'h0E, 8'h1D, 1, 1, 2'd0, 3'd0, 0, "~x"); wait_rep(b);
  chk(r_err == 4, "command code 0x0E: format error");
  b = nrep; packet(8'h3A, 8'h0F, 8'h1D, 1, 1, 2'd0, 3'd0, 0, "~x", 0, 1); wait_rep(b);
  chk(r_err == 4, "byte count one too large: format error");
  b = nrep; packet(8'h3A, 8'h0F, 8'h1D, 1, 1, 2'd0, 3'd0, 0, "~x", 0, 0, 8'h02); wait_rep(b);
  chk(r_err == 4, "header version 2: format error");

  // another slave address: NACKed, no report
  b = nrep; nack = 0;
  packet(8'h40, 8'h0F, 8'h1D, 1, 1, 2'd0, 3'd0, 0, "~x");
  w(5);
  chk(nack > 0 && nrep == b, "another slave address: NACK, no report");
  // a packet without SOM and no message open: dropped
  b = nrep; packet(8'h3A, 8'h0F, 8'h1D, 0, 1, 2'd0, 3'd0, 0, "zz"); w(5);
  chk(nrep == b, "middle packet without a message: dropped");
  // after all that, a clean message still works
  b = nrep; packet(8'h3A, 8'h0F, 8'h1D, 1, 1, 2'd0, 3'd7, 0, {8'h05, "123456789"}); wait_rep(b);
  chk(r_err == 0 && r_type == 8'h05 && r_crc == 32'hCBF4_3926 && r_tag == 3'd7, "clean SPDM-type message afterwards");

  chk(sda_glitch == 0, $sformatf("endpoint SDA stable while SCL high (%0d changes)", sda_glitch));
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
