# DMTF NC-SI (Network Controller Sideband Interface, DSP0222 1.x) management
# controller agent: NC-SI control packets over the RMII-based transport
# (RBT). The agent drives TX_EN / TXD[1:0] towards the network controller and
# takes its responses from CRS_DV / RXD[1:0]; two bits a REF_CLK, LSB first,
# each frame behind a 7-byte 0x55 preamble and the SFD 0xD5.
#
# Control packet: Ethernet header (DA FF:FF:FF:FF:FF:FF, SA, EtherType
# 0x88F8), the 16-byte NC-SI header (MC ID, header revision 0x01, reserved,
# instance ID, packet type, channel ID {package[2:0], channel[4:0]},
# payload length[11:0], 8 reserved bytes), the payload padded to 4 bytes, a
# 32-bit checksum (two's complement of the 16-bit sum over header and padded
# payload; 0 means not used), Ethernet padding to 60 bytes and the FCS.
#
# tb/top_tb.sv ncsi_model: one package (ID 0) with channels 0 and 1. It
# drops a frame with a bad FCS, another EtherType, a header revision other
# than 1, another package or channel, or a nonzero checksum that is wrong.
# Otherwise it answers (type = command | 0x80, MC ID, IID and channel ID
# echoed) 16 REF_CLKs after the command with a response code / reason code:
#   0x0003 / 0x7FFF  command type not supported
#   0x0001 / 0x0002  parameter invalid: a package command (Select / Deselect
#                    Package) not sent to channel 0x1F, a channel command sent
#                    to 0x1F, or a payload length wrong for the command
#   0x0001 / 0x0001  interface initialization required: a channel command
#                    other than Clear Initial State while the channel is in
#                    its initial state (after reset and after Reset Channel)
#   0x0000 / 0x0000  completed
# Commands: 0x00 Clear Initial State, 0x01 Select Package (4-byte payload),
# 0x02 Deselect Package, 0x03 Enable Channel, 0x04 Disable Channel (4),
# 0x05 Reset Channel (4; back to the initial state, disabled), 0x0A Get
# Link Status (12 data bytes: link status 0x00000011 while the channel is
# enabled, 0x00000010 while disabled, then 8 zero bytes) and 0x15 Get
# Version ID (40 bytes: NC-SI 1.1 F1 F1 F0 00, firmware name
# "OPENVIP-NCSI", version 1.2.3.4, PCI IDs, manufacturer ID).

NCSI_FUNCS = """
localparam int NCSI_WAIT = 200;    // REF_CLKs the controller waits for a response
function automatic bit [31:0] ncsi_crc32(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction
// payload length the command takes (-1: not supported by the model)
function automatic int ncsi_exp_len(bit [7:0] cmd);
  case (cmd)
    8'h00, 8'h02, 8'h03, 8'h0A, 8'h15: return 0;
    8'h01, 8'h04, 8'h05: return 4;
    default: return -1;
  endcase
endfunction
// Get Version ID response data
function automatic bit [7:0] ncsi_ver_byte(int i);
  string name = "OPENVIP-NCSI";
  case (i)
    0, 1: return 8'hF1;
    2: return 8'hF0;
    20: return 8'h01; 21: return 8'h02; 22: return 8'h03; 23: return 8'h04;
    24: return 8'h12; 25: return 8'h34; 26: return 8'hAB; 27: return 8'hCD;
    28: return 8'h00; 29: return 8'h01; 30: return 8'hAB; 31: return 8'hCD;
    39: return 8'h2A;
    default: return (i >= 8 && i < 20) ? name[i - 8] : 8'h00;
  endcase
endfunction
// two's complement of the 16-bit big-endian sum of b[from +: n]
function automatic bit [31:0] ncsi_csum(bit [7:0] b[$], int from, int n);
  bit [31:0] s = 0;
  for (int i = 0; i < n; i += 2) s += {16'h0, b[from + i], (i + 1 < n) ? b[from + i + 1] : 8'h00};
  return -s;
endfunction
"""

SPEC = dict(
    vip="NC-SI-UVM-VIP", p="ncsi", P="NCSI", dir="ncsi", family="Power / Management",
    desc="DMTF NC-SI management controller VIP over RBT (RMII): control packets with checksum and FCS, package / channel "
         "addressing, initial state, select / enable / reset, link status, version ID, response and reason codes, dropped frames.",
    about="""
NC-SI is the sideband between a BMC and the server's network controller: the
BMC shares the NIC's port and manages it with control packets (EtherType
0x88F8) over an RMII-based link. Every command gets a response with the same
instance ID, or none at all when the controller drops it. The DUT model is a
one-package, two-channel network controller; the scoreboard keeps each
channel's initial state and enable bit and predicts every response (or its
absence), its code, reason and data. Driver and monitor agree on the planted
faults (a wrong checksum, a zero checksum, a bad FCS, a header revision, a
wrong payload length), so a checksum or addressing slip in the controller
shows up.""",
    defs=NCSI_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "tx_en"), ("in", "logic [1:0]", "txd"),
        ("out", "logic", "crs_dv"), ("out", "logic [1:0]", "rxd"),
    ],
    fields=[
        ("bit [7:0]", "mcid", "req"),
        ("bit [7:0]", "iid", "req"),
        ("bit [7:0]", "cmd", "req"),
        ("bit [7:0]", "chan", "req"),
        ("bit [7:0]", "pl", "req", "q"),
        ("bit [2:0]", "fault", "req"),     # 1 checksum, 2 FCS, 3 header revision, 4 length + 4, 5 zero checksum
        ("bit", "got", "rsp"),
        ("bit [7:0]", "rtype", "rsp"),
        ("bit [7:0]", "riid", "rsp"),
        ("bit [7:0]", "rchan", "rsp"),
        ("bit [15:0]", "rcode", "rsp"),
        ("bit [15:0]", "reason", "rsp"),
        ("bit [7:0]", "rdata", "rsp", "q"),
        ("bit", "rok", "rsp"),             # response FCS, checksum, header good
        ("bit [3:0]", "csel", "info", "rand"),
        ("bit [3:0]", "tsel", "info", "rand"),
        ("bit [4:0]", "fsel", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_iid { iid != 0; }
""",
    tr_functions="""
// command, channel and fault from the selectors (no dist inside implications)
function void post_randomize();
  bit [7:0] cmds [16] = '{8'h00, 8'h00, 8'h01, 8'h02, 8'h03, 8'h03, 8'h04, 8'h05,
                          8'h0A, 8'h0A, 8'h15, 8'h15, 8'h50, 8'h0E, 8'h0A, 8'h03};
  cmd = cmds[csel];
  if (cmd == 8'h01 || cmd == 8'h02)
    chan = (tsel < 14) ? 8'h1F : (tsel == 14) ? 8'h00 : 8'h20;
  else
    chan = (tsel < 7) ? 8'h00 : (tsel < 13) ? 8'h01 : (tsel == 13) ? 8'h1F : (tsel == 14) ? 8'h02 : 8'h21;
  case (fsel)
    25: fault = 1;
    26: fault = 2;
    27: fault = 3;
    28: fault = (ncsi_exp_len(cmd) >= 0) ? 4 : 0;
    29, 30: fault = 5;
    default: fault = 0;
  endcase
  mk_pl();
endfunction
function void mk_pl();
  bit [31:0] x = seed | 1;
  int n = (ncsi_exp_len(cmd) >= 0) ? ncsi_exp_len(cmd) : 4;
  pl.delete();
  for (int i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    pl.push_back(x[7:0]);
  end
endfunction
function void set(bit [7:0] c, bit [7:0] ch, bit [2:0] f = 0);
  cmd = c; chan = ch; fault = f;
  mk_pl();
endfunction

// Ethernet frame from DA to FCS (no preamble)
function void cmd_bytes(output bit [7:0] b[$]);
  bit [31:0] c = 32'hFFFF_FFFF, s;
  int len = pl.size() + ((fault == 4) ? 4 : 0);
  b.delete();
  repeat (6) b.push_back(8'hFF);
  b.push_back(8'h02); repeat (4) b.push_back(8'h00); b.push_back(mcid);
  b.push_back(8'h88); b.push_back(8'hF8);
  b.push_back(mcid); b.push_back((fault == 3) ? 8'h02 : 8'h01); b.push_back(8'h00); b.push_back(iid);
  b.push_back(cmd); b.push_back(chan); b.push_back({4'h0, len[11:8]}); b.push_back(len[7:0]);
  repeat (8) b.push_back(8'h00);
  foreach (pl[i]) b.push_back(pl[i]);
  if (fault == 4) repeat (4) b.push_back(8'h00);
  while (b.size() % 4 != 2) b.push_back(8'h00);
  s = ncsi_csum(b, 14, b.size() - 14);
  if (fault == 5) s = 0;
  else if (fault == 1) s ^= 32'h0000_0100;
  for (int i = 3; i >= 0; i--) b.push_back(s[8*i +: 8]);
  while (b.size() < 60) b.push_back(8'h00);
  foreach (b[i]) c = ncsi_crc32(c, b[i]);
  c = ~c ^ {31'h0, fault == 2};
  for (int i = 0; i < 4; i++) b.push_back(c[8*i +: 8]);
endfunction

// command fields and the planted fault from a command frame
function void from_cmd(bit [7:0] b[$]);
  bit [31:0] c = 32'hFFFF_FFFF, s, sum;
  int len, e, p4;
  foreach (b[i]) c = ncsi_crc32(c, b[i]);
  mcid = b[14]; iid = b[17]; cmd = b[18]; chan = b[19];
  len = {b[20][3:0], b[21]};
  e = ncsi_exp_len(cmd);
  p4 = (len + 3) / 4 * 4;
  pl.delete();
  for (int i = 0; i < ((e >= 0 && len != e) ? e : len); i++) pl.push_back(b[30 + i]);
  s = ncsi_csum(b, 14, 16 + p4);
  sum = {b[30 + p4], b[31 + p4], b[32 + p4], b[33 + p4]};
  fault = (c != 32'hDEBB_20E3) ? 2 : (b[15] != 8'h01) ? 3 : (e >= 0 && len != e) ? 4 : (sum == 0) ? 5 : (sum != s) ? 1 : 0;
endfunction

// response fields from a response frame
function void from_rsp(bit [7:0] r[$]);
  bit [31:0] c = 32'hFFFF_FFFF, s;
  int len, p4;
  got = 1; rok = 0; rdata.delete();
  if (r.size() < 64) return;
  foreach (r[i]) c = ncsi_crc32(c, r[i]);
  riid = r[17]; rtype = r[18]; rchan = r[19];
  len = {r[20][3:0], r[21]};
  rcode = {r[30], r[31]}; reason = {r[32], r[33]};
  for (int i = 4; i < len; i++) rdata.push_back(r[30 + i]);
  p4 = (len + 3) / 4 * 4;
  s = ncsi_csum(r, 14, 16 + p4);
  rok = (c == 32'hDEBB_20E3) && ({r[30 + p4], r[31 + p4], r[32 + p4], r[33 + p4]} == s) && r[15] == 8'h01 &&
        r[14] == mcid && {r[12], r[13]} == 16'h88F8 && r.size() == ((34 + p4 < 60) ? 60 : 34 + p4) + 4;
endfunction
""",
    drv_rsp=True,
    drv_desc="one control packet per item: preamble, SFD and frame on TX_EN / TXD two bits a clock, then the response taken from CRS_DV / RXD (or none within the wait)",
    drv_idle="""
vif.drv_cb.tx_en <= 1'b0;
vif.drv_cb.txd   <= 2'b00;
""",
    drv_item="""
bit [7:0] b[$], r[$];
bit [7:0] sh;
int k = 0, d = 0;
bit sync = 0;
t.cmd_bytes(b);
b.push_front(8'hD5);
repeat (7) b.push_front(8'h55);
foreach (b[i]) for (int j = 0; j < 4; j++) begin
  vif.drv_cb.tx_en <= 1'b1; vif.drv_cb.txd <= b[i][2*j +: 2];
  @(vif.drv_cb);
end
vif.drv_cb.tx_en <= 1'b0; vif.drv_cb.txd <= 2'b00;
while (k < NCSI_WAIT && !vif.drv_cb.crs_dv) begin @(vif.drv_cb); k++; end
if (vif.drv_cb.crs_dv) begin
  while (vif.drv_cb.crs_dv) begin
    if (!sync) sync = (vif.drv_cb.rxd == 2'b11);
    else begin
      sh = {vif.drv_cb.rxd, sh[7:2]};
      if (++d == 4) begin r.push_back(sh); d = 0; end
    end
    @(vif.drv_cb);
  end
  t.from_rsp(r);
end
repeat (4) @(vif.drv_cb);
""",
    mon_desc="command frames from TX_EN / TXD and response frames from CRS_DV / RXD, each after its SFD; a command without a response within the wait is published with got = 0",
    mon_run="""
bit [7:0] b[$], r[$];
bit [7:0] tsh, rsh;
int td = 0, rd = 0, cnt = 0;
bit tsync = 0, rsync = 0, tx_p = 0, rx_p = 0, pend = 0;
ncsi_transaction cur;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.tx_en) begin
    if (!tx_p) begin tsync = 0; b.delete(); td = 0; end
    if (!tsync) tsync = (vif.mon_cb.txd == 2'b11);
    else begin
      tsh = {vif.mon_cb.txd, tsh[7:2]};
      if (++td == 4) begin b.push_back(tsh); td = 0; end
    end
  end else if (tx_p) begin
    if (pend) publish(cur);
    if (b.size() < 64) `uvm_error("MON", $sformatf("NC-SI: command frame of %0d bytes", b.size()))
    cur = ncsi_transaction::type_id::create("t");
    cur.from_cmd(b);
    pend = 1; cnt = 0; td = 0;
  end
  if (vif.mon_cb.crs_dv) begin
    if (!rx_p) begin rsync = 0; r.delete(); rd = 0; end
    if (!rsync) rsync = (vif.mon_cb.rxd == 2'b11);
    else begin
      rsh = {vif.mon_cb.rxd, rsh[7:2]};
      if (++rd == 4) begin r.push_back(rsh); rd = 0; end
    end
  end else if (rx_p) begin
    if (!pend) `uvm_error("MON", "NC-SI: response without a command")
    else begin cur.from_rsp(r); publish(cur); pend = 0; end
    rd = 0;
  end
  if (pend && !vif.mon_cb.crs_dv && !vif.mon_cb.tx_en && ++cnt > NCSI_WAIT) begin publish(cur); pend = 0; end
  tx_p = vif.mon_cb.tx_en; rx_p = vif.mon_cb.crs_dv;
end
""",
    sb_members="bit [1:0] init_req = 2'b11, en = 2'b00;",
    predict="""
int e = ncsi_exp_len(t.cmd), ch = t.chan[4:0];
bit pkgc = (t.cmd == 8'h01 || t.cmd == 8'h02);
t.got = 0; t.rtype = 0; t.riid = 0; t.rchan = 0; t.rcode = 0; t.reason = 0; t.rok = 0; t.rdata.delete();
if (!(t.fault inside {1, 2, 3}) && t.chan[7:5] == 0 && (ch <= 1 || ch == 31)) begin
  t.got = 1; t.rok = 1; t.rtype = t.cmd | 8'h80; t.riid = t.iid; t.rchan = t.chan;
  if (e < 0) begin t.rcode = 3; t.reason = 16'h7FFF; end
  else if (pkgc != (ch == 31) || t.fault == 4) begin t.rcode = 1; t.reason = 2; end
  else if (ch != 31 && init_req[ch] && t.cmd != 0) begin t.rcode = 1; t.reason = 1; end
  else
    case (t.cmd)
      8'h00: init_req[ch] = 0;
      8'h03: en[ch] = 1;
      8'h04: en[ch] = 0;
      8'h05: begin init_req[ch] = 1; en[ch] = 0; end
      8'h0A: begin
        repeat (12) t.rdata.push_back(8'h00);
        t.rdata[3] = en[ch] ? 8'h11 : 8'h10;
      end
      8'h15: for (int i = 0; i < 40; i++) t.rdata.push_back(ncsi_ver_byte(i));
      default: ;
    endcase
end
""",
    checks="""
if (t.got && !t.rok) fail(t, "response with a bad FCS, checksum or header");
if (t.got && t.riid != t.iid) fail(t, "response instance ID differs from the command");
""",
    coverage="""
cp_cmd : coverpoint tr.cmd { bins clear = {8'h00}; bins sel = {8'h01}; bins desel = {8'h02}; bins enable = {8'h03};
                             bins disable_ch = {8'h04}; bins reset_ch = {8'h05}; bins link = {8'h0A}; bins version = {8'h15};
                             bins unsupported = {8'h50, 8'h0E}; }
cp_rsp : coverpoint (!tr.got ? 4 : tr.rcode == 0 ? 0 : tr.rcode == 3 ? 3 : tr.reason == 1 ? 1 : 2) {
  bins completed = {0}; bins init_required = {1}; bins param_invalid = {2}; bins unsupported = {3}; bins dropped = {4}; }
cp_fault : coverpoint tr.fault { bins none = {0}; bins checksum = {1}; bins fcs = {2}; bins revision = {3}; bins length = {4}; bins zero_sum = {5}; }
cp_target : coverpoint tr.chan { bins ch0 = {8'h00}; bins ch1 = {8'h01}; bins pkg = {8'h1F}; bins absent = {8'h02, 8'h20, 8'h21}; }
cp_link : coverpoint (tr.rdata.size() == 12 ? tr.rdata[3] : 8'h00) iff (tr.cmd == 8'h0A && tr.rcode == 0 && tr.got) { bins up = {8'h11}; bins down = {8'h10}; }
""",
    directed="""
// initial state, clear, every command per channel, package commands, then the faults
t = item(); t.set(8'h15, 8'h00); send(t);
t = item(); t.set(8'h00, 8'h00); send(t);
t = item(); t.set(8'h15, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h00); send(t);
t = item(); t.set(8'h03, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h00); send(t);
t = item(); t.set(8'h03, 8'h01); send(t);
t = item(); t.set(8'h00, 8'h01); send(t);
t = item(); t.set(8'h03, 8'h01); send(t);
t = item(); t.set(8'h04, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h01); send(t);
t = item(); t.set(8'h01, 8'h1F); send(t);
t = item(); t.set(8'h02, 8'h1F); send(t);
t = item(); t.set(8'h01, 8'h00); send(t);
t = item(); t.set(8'h00, 8'h1F); send(t);
t = item(); t.set(8'h50, 8'h00); send(t);
t = item(); t.set(8'h50, 8'h1F); send(t);
for (int f = 1; f < 6; f++) begin
  t = item(); t.set(8'h03, 8'h00, f); send(t);
end
t = item(); t.set(8'h03, 8'h20); send(t);
t = item(); t.set(8'h03, 8'h02); send(t);
t = item(); t.set(8'h05, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h00); send(t);
t = item(); t.set(8'h00, 8'h00); send(t);
t = item(); t.set(8'h0A, 8'h00); send(t);
""",
    drain_ns=8000,
    model="""
module ncsi_model (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       tx_en,
  input  logic [1:0] txd,
  output logic       crs_dv,
  output logic [1:0] rxd
);
  localparam int GAP = 16;            // REF_CLKs from the command's end to the response

  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    logic [31:0] x;
    x = c ^ {24'h0, b};
    for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
    crc32_byte = x;
  endfunction
  function automatic logic [7:0] ver_byte(input integer i);
    case (i)
      0, 1: ver_byte = 8'hF1;
      2: ver_byte = 8'hF0;
      8: ver_byte = "O"; 9: ver_byte = "P"; 10: ver_byte = "E"; 11: ver_byte = "N";
      12: ver_byte = "V"; 13: ver_byte = "I"; 14: ver_byte = "P"; 15: ver_byte = "-";
      16: ver_byte = "N"; 17: ver_byte = "C"; 18: ver_byte = "S"; 19: ver_byte = "I";
      20: ver_byte = 8'h01; 21: ver_byte = 8'h02; 22: ver_byte = 8'h03; 23: ver_byte = 8'h04;
      24: ver_byte = 8'h12; 25: ver_byte = 8'h34; 26: ver_byte = 8'hAB; 27: ver_byte = 8'hCD;
      28: ver_byte = 8'h00; 29: ver_byte = 8'h01; 30: ver_byte = 8'hAB; 31: ver_byte = 8'hCD;
      39: ver_byte = 8'h2A;
      default: ver_byte = 8'h00;
    endcase
  endfunction

  logic [7:0]  rb [0:127];            // command frame after the SFD
  logic [7:0]  tb [0:127];            // response: preamble, SFD, frame
  logic [7:0]  nrb, sh, tlen;
  logic [1:0]  dib;
  logic        sync, tx_p, pend, busy;
  logic [1:0]  init_req, en;
  logic [4:0]  wcnt;
  logic [9:0]  tdib;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nrb <= '0; sh <= '0; dib <= '0; sync <= 1'b0; tx_p <= 1'b0; pend <= 1'b0; busy <= 1'b0;
      init_req <= 2'b11; en <= 2'b00; wcnt <= '0; tdib <= '0; tlen <= '0;
      crs_dv <= 1'b0; rxd <= 2'b00;
    end else begin
      tx_p <= tx_en;
      // receive: dibits after the SFD's 11, LSB first
      if (tx_en) begin
        if (!tx_p) begin sync <= (txd == 2'b11); nrb <= '0; dib <= '0; end
        else if (!sync) sync <= (txd == 2'b11);
        else begin
          sh <= {txd, sh[7:2]};
          dib <= dib + 2'd1;
          if (dib == 2'd3) begin
            if (nrb < 8'd128) rb[nrb[6:0]] <= {txd, sh[7:2]};
            nrb <= nrb + 8'd1;
          end
        end
      end else if (tx_p && !busy && !pend) begin : decode
        logic [7:0]  f [0:127];
        logic [31:0] c, s, sum;
        logic [11:0] len;
        logic [7:0]  cmd, ch;
        logic [15:0] code, reason;
        integer      n, p4, e, dl, fl;
        logic        ok, pkgc;
        n = nrb;
        ok = (n >= 64 && n <= 128);
        c = 32'hFFFF_FFFF;
        for (int i = 0; i < 128; i++) if (i < n) c = crc32_byte(c, rb[i]);
        if (c != 32'hDEBB_20E3) ok = 1'b0;
        if ({rb[12], rb[13]} != 16'h88F8 || rb[15] != 8'h01) ok = 1'b0;
        cmd = rb[18]; ch = rb[19];
        if (ch[7:5] != 3'd0 || (ch[4:0] > 5'd1 && ch[4:0] != 5'h1F)) ok = 1'b0;
        len = {rb[20][3:0], rb[21]};
        p4 = (len + 3) / 4 * 4;
        if (34 + p4 > n - 4) ok = 1'b0;
        s = 32'h0;
        for (int i = 0; i < 112; i += 2) if (i < 16 + p4) s = s + {16'h0, rb[14 + i], rb[15 + i]};
        s = -s;
        sum = {rb[30 + p4], rb[31 + p4], rb[32 + p4], rb[33 + p4]};
        if (sum != 32'h0 && sum != s) ok = 1'b0;
        case (cmd)
          8'h00, 8'h02, 8'h03, 8'h0A, 8'h15: e = 0;
          8'h01, 8'h04, 8'h05: e = 4;
          default: e = -1;
        endcase
        pkgc = (cmd == 8'h01 || cmd == 8'h02);
        dl = 0;
        for (int i = 0; i < 128; i++) f[i] = 8'h00;
        if (ok) begin
          if (e < 0) begin code = 16'h0003; reason = 16'h7FFF; end
          else if (pkgc != (ch[4:0] == 5'h1F) || len != e) begin code = 16'h0001; reason = 16'h0002; end
          else if (ch[4:0] != 5'h1F && init_req[ch[0]] && cmd != 8'h00) begin code = 16'h0001; reason = 16'h0001; end
          else begin
            code = 16'h0000; reason = 16'h0000;
            case (cmd)
              8'h00: init_req[ch[0]] <= 1'b0;
              8'h03: en[ch[0]] <= 1'b1;
              8'h04: en[ch[0]] <= 1'b0;
              8'h05: begin init_req[ch[0]] <= 1'b1; en[ch[0]] <= 1'b0; end
              8'h0A: begin dl = 12; f[45] = en[ch[0]] ? 8'h11 : 8'h10; end
              8'h15: begin dl = 40; for (int i = 0; i < 40; i++) f[42 + i] = ver_byte(i); end
              default: ;
            endcase
          end
          // response frame at f[8..]: preamble and SFD first
          for (int i = 0; i < 7; i++) f[i] = 8'h55;
          f[7] = 8'hD5;
          for (int i = 0; i < 12; i++) f[8 + i] = 8'hFF;
          f[20] = 8'h88; f[21] = 8'hF8;
          f[22] = rb[14]; f[23] = 8'h01; f[25] = rb[17]; f[26] = cmd | 8'h80; f[27] = ch;
          f[28] = 8'h00; f[29] = 8'(4 + dl);
          f[38] = code[15:8]; f[39] = code[7:0]; f[40] = reason[15:8]; f[41] = reason[7:0];
          s = 32'h0;
          for (int i = 0; i < 60; i += 2) if (i < 20 + dl) s = s + {16'h0, f[22 + i], f[23 + i]};
          s = -s;
          for (int i = 0; i < 4; i++) f[42 + dl + i] = s[31 - 8*i -: 8];
          fl = 38 + dl;                          // frame bytes before the padding
          if (fl < 60) fl = 60;
          c = 32'hFFFF_FFFF;
          for (int i = 0; i < 100; i++) if (i < fl) c = crc32_byte(c, f[8 + i]);
          c = ~c;
          for (int i = 0; i < 4; i++) f[8 + fl + i] = c[8*i +: 8];
          for (int i = 0; i < 128; i++) tb[i] <= f[i];
          tlen <= 8'(8 + fl + 4);
          pend <= 1'b1; wcnt <= '0;
        end
      end
      // transmit after the gap
      if (pend) begin
        wcnt <= wcnt + 5'd1;
        if (wcnt == 5'(GAP - 1)) begin pend <= 1'b0; busy <= 1'b1; tdib <= '0; end
      end
      if (busy) begin
        crs_dv <= 1'b1;
        rxd <= tb[tdib[9:2]][2*tdib[1:0] +: 2];
        tdib <= tdib + 10'd1;
        if (tdib == {tlen, 2'b00} - 10'd1) busy <= 1'b0;
      end else begin
        crs_dv <= 1'b0; rxd <= 2'b00;
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({tx_en, crs_dv}))
  else $error("NC-SI: X on TX_EN / CRS_DV");
assert property (@(posedge clk) disable iff (!rst_n) crs_dv |-> !$isunknown(rxd))
  else $error("NC-SI: X on RXD while CRS_DV");
// the controller never answers over a command
assert property (@(posedge clk) disable iff (!rst_n) !(tx_en && $rose(crs_dv)))
  else $error("NC-SI: response started during a command");
cover property (@(posedge clk) disable iff (!rst_n) $fell(crs_dv));
cover property (@(posedge clk) disable iff (!rst_n) $fell(tx_en) ##1 (!crs_dv)[*200]);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic tx_en = 1'b0;
logic [1:0] txd = 2'b00;
wire crs_dv;
wire [1:0] rxd;

always #10 clk = ~clk;

ncsi_model u_dut (.clk(clk), .rst_n(rst_n), .tx_en(tx_en), .txd(txd), .crs_dv(crs_dv), .rxd(rxd));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [31:0] crc32(input logic [31:0] c, input logic [7:0] b);
  logic [31:0] x;
  x = c ^ {24'h0, b};
  for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
  crc32 = x;
endfunction

// response capture
logic [7:0] rr [0:127];
integer rn = 0, rcount = 0, npre = 0, cyc = 0, tend = 0, rstart = 0, rd = 0;
logic rs = 0, cp = 0, tp = 0;
logic [7:0] rsh = 0;
always @(posedge clk) begin
  cyc = cyc + 1;
  if (crs_dv) begin
    if (!cp) begin rs = 0; rn = 0; npre = 0; rstart = cyc; end
    if (!rs) begin
      if (rxd == 2'b11) begin rs = 1; rd = 0; end
      else if (rxd == 2'b01) npre = npre + 1;
    end else begin
      rsh = {rxd, rsh[7:2]}; rd = rd + 1;
      if (rd == 4) begin rr[rn] = rsh; rn = rn + 1; rd = 0; end
    end
  end else if (cp) rcount = rcount + 1;
  if (!tx_en && tp) tend = cyc;
  cp = crs_dv; tp = tx_en;
end

// command frame
logic [7:0] fb [0:127];
integer fn;
integer iid = 1;
function automatic integer exp_len(input logic [7:0] cmd);
  case (cmd)
    8'h00, 8'h02, 8'h03, 8'h0A, 8'h15: exp_len = 0;
    8'h01, 8'h04, 8'h05: exp_len = 4;
    default: exp_len = 4;
  endcase
endfunction
// fault: 1 checksum + 0x100, 2 FCS, 3 header revision 2, 5 zero checksum, 6 EtherType 0x0800
task automatic build(input logic [7:0] mcid, input logic [7:0] cmd, input logic [7:0] ch, input integer len, input integer fault);
  logic [31:0] c, s;
  for (int i = 0; i < 128; i++) fb[i] = 8'h00;
  for (int i = 0; i < 6; i++) fb[i] = 8'hFF;
  fb[6] = 8'h02; fb[11] = mcid;
  fb[12] = (fault == 6) ? 8'h08 : 8'h88; fb[13] = (fault == 6) ? 8'h00 : 8'hF8;
  fb[14] = mcid; fb[15] = (fault == 3) ? 8'h02 : 8'h01; fb[17] = iid; fb[18] = cmd; fb[19] = ch;
  fb[20] = len >> 8; fb[21] = len;
  for (int i = 0; i < 64; i++) if (i < len) fb[30 + i] = 8'hA0 + i;
  fn = 30 + (len + 3) / 4 * 4;
  s = 0;
  for (int i = 14; i < 128; i += 2) if (i < fn) s = s + {16'h0, fb[i], fb[i + 1]};
  s = -s;
  if (fault == 5) s = 0;
  if (fault == 1) s = s ^ 32'h100;
  fb[fn] = s[31:24]; fb[fn + 1] = s[23:16]; fb[fn + 2] = s[15:8]; fb[fn + 3] = s[7:0];
  fn = fn + 4;
  if (fn < 60) fn = 60;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 128; i++) if (i < fn) c = crc32(c, fb[i]);
  c = ~c;
  if (fault == 2) c = c ^ 32'h1;
  fb[fn] = c[7:0]; fb[fn + 1] = c[15:8]; fb[fn + 2] = c[23:16]; fb[fn + 3] = c[31:24];
  fn = fn + 4;
endtask
task automatic send_byte(input logic [7:0] b);
  for (int j = 0; j < 4; j++) begin
    @(negedge clk); tx_en = 1; txd = b[2*j +: 2];
  end
endtask
logic got;
task automatic send_frame();
  integer r0, k;
  r0 = rcount;
  for (int i = 0; i < 7; i++) send_byte(8'h55);
  send_byte(8'hD5);
  for (int i = 0; i < 128; i++) if (i < fn) send_byte(fb[i]);
  @(negedge clk); tx_en = 0; txd = 0;
  k = 0;
  while (k < 500 && rcount == r0) begin @(negedge clk); k = k + 1; end
  got = (rcount != r0);
  iid = iid + 1;
endtask
task automatic xact(input logic [7:0] cmd, input logic [7:0] ch, input integer len = -1, input integer fault = 0,
                    input logic [7:0] mcid = 8'h00);
  build(mcid, cmd, ch, (len < 0) ? exp_len(cmd) : len, fault);
  send_frame();
endtask

// FCS again after editing fb
task automatic refcs();
  logic [31:0] c;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 128; i++) if (i < fn - 4) c = crc32(c, fb[i]);
  c = ~c;
  fb[fn - 4] = c[7:0]; fb[fn - 3] = c[15:8]; fb[fn - 2] = c[23:16]; fb[fn - 1] = c[31:24];
endtask
localparam integer RSP_GAP = 18;   // GAP clocks plus the two register stages
function automatic logic [7:0] ver_exp(input integer i);
  reg [8*12-1:0] name;
  name = "OPENVIP-NCSI";
  case (i)
    0, 1: ver_exp = 8'hF1;
    2: ver_exp = 8'hF0;
    20: ver_exp = 8'h01; 21: ver_exp = 8'h02; 22: ver_exp = 8'h03; 23: ver_exp = 8'h04;
    24: ver_exp = 8'h12; 25: ver_exp = 8'h34; 26: ver_exp = 8'hAB; 27: ver_exp = 8'hCD;
    28: ver_exp = 8'h00; 29: ver_exp = 8'h01; 30: ver_exp = 8'hAB; 31: ver_exp = 8'hCD;
    39: ver_exp = 8'h2A;
    default: ver_exp = (i >= 8 && i < 20) ? name[8*(19 - i) +: 8] : 8'h00;
  endcase
endfunction
// response fields
function automatic logic [15:0] r_code(input integer x); r_code = {rr[30], rr[31]}; endfunction
function automatic logic [15:0] r_reason(input integer x); r_reason = {rr[32], rr[33]}; endfunction
function automatic logic r_good(input integer dl);
  logic [31:0] c, s;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 128; i++) if (i < rn) c = crc32(c, rr[i]);
  s = 0;
  for (int i = 14; i < 128; i += 2) if (i < 34 + dl) s = s + {16'h0, rr[i], rr[i + 1]};
  s = -s;
  r_good = (c == 32'hDEBB_20E3) && ({rr[34 + dl], rr[35 + dl], rr[36 + dl], rr[37 + dl]} == s) &&
           ({rr[20][3:0], rr[21]} == 4 + dl) && rr[15] == 8'h01 && {rr[12], rr[13]} == 16'h88F8 &&
           rn == ((38 + dl < 60) ? 64 : 38 + dl + 4);
endfunction
function automatic logic rsp(input logic [7:0] cmd, input logic [7:0] ch, input logic [15:0] code, input logic [15:0] reason,
                             input integer dl);
  rsp = got && rr[18] == (cmd | 8'h80) && rr[19] == ch && rr[17] == iid - 1 && r_code(0) == code && r_reason(0) == reason && r_good(dl);
endfunction

initial begin
  logic ok;
  repeat (4) @(posedge clk);
  chk(crs_dv === 1'b0, "CRS_DV low in reset");
  rst_n = 1;
  repeat (4) @(negedge clk);

  // initial state: channel commands other than Clear Initial State are refused
  xact(8'h15, 8'h00, -1, 0, 8'h5A);
  chk(rsp(8'h15, 8'h00, 16'h1, 16'h1, 0) && rr[14] == 8'h5A, "Get Version ID in the initial state: 1 / 1, MC ID echoed");
  chk(npre == 31, $sformatf("response preamble and SFD (%0d dibits 01 before 11)", npre));
  chk(rstart - tend == RSP_GAP, $sformatf("response %0d clocks after the command", rstart - tend));
  xact(8'h00, 8'h00);
  chk(rsp(8'h00, 8'h00, 16'h0, 16'h0, 0), "Clear Initial State ch 0");
  xact(8'h15, 8'h00);
  ok = rsp(8'h15, 8'h00, 16'h0, 16'h0, 40) && rr[34] == 8'hF1 && rr[35] == 8'hF1 && rr[36] == 8'hF0 && rr[37] == 8'h00 &&
       rr[42] == "O" && rr[53] == "I" && rr[54] == 8'h01 && rr[57] == 8'h04 && rr[58] == 8'h12 && rr[73] == 8'h2A;
  chk(ok, "Get Version ID: 40 bytes, version F1 F1 F0 00, name, firmware, IDs");
  ok = 1;
  for (int i = 0; i < 40; i++) if (rr[34 + i] !== ver_exp(i)) ok = 0;
  chk(ok, "Get Version ID: every data byte");
  ok = 1;
  for (int i = 0; i < 12; i++) if (rr[i] !== 8'hFF) ok = 0;
  chk(ok, "response DA and SA FF:FF:FF:FF:FF:FF");
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h0, 16'h0, 12) && {rr[34], rr[35], rr[36], rr[37]} == 32'h10, "Get Link Status ch 0 disabled: 0x10");
  xact(8'h03, 8'h00);
  chk(rsp(8'h03, 8'h00, 16'h0, 16'h0, 0), "Enable Channel ch 0");
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h0, 16'h0, 12) && rr[37] == 8'h11, "Get Link Status ch 0 enabled: 0x11");
  // channel 1 has its own state
  xact(8'h03, 8'h01);
  chk(rsp(8'h03, 8'h01, 16'h1, 16'h1, 0), "Enable Channel ch 1 in its initial state: 1 / 1");
  xact(8'h00, 8'h01);
  chk(rsp(8'h00, 8'h01, 16'h0, 16'h0, 0), "Clear Initial State ch 1");
  xact(8'h0A, 8'h01);
  chk(rsp(8'h0A, 8'h01, 16'h0, 16'h0, 12) && rr[37] == 8'h10, "ch 1 cleared but disabled: 0x10");
  xact(8'h03, 8'h01);
  xact(8'h04, 8'h00);
  chk(rsp(8'h04, 8'h00, 16'h0, 16'h0, 0), "Disable Channel ch 0");
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h0, 16'h0, 12) && rr[37] == 8'h10, "ch 0 disabled again: 0x10");
  xact(8'h0A, 8'h01);
  chk(rsp(8'h0A, 8'h01, 16'h0, 16'h0, 12) && rr[37] == 8'h11, "ch 1 still enabled: 0x11");
  // package commands
  xact(8'h01, 8'h1F, -1, 0, 8'h33);
  chk(rsp(8'h01, 8'h1F, 16'h0, 16'h0, 0) && rr[14] == 8'h33, "Select Package to 0x1F");
  xact(8'h02, 8'h1F);
  chk(rsp(8'h02, 8'h1F, 16'h0, 16'h0, 0), "Deselect Package to 0x1F");
  xact(8'h01, 8'h00);
  chk(rsp(8'h01, 8'h00, 16'h1, 16'h2, 0), "Select Package to a channel: 1 / 2");
  xact(8'h03, 8'h1F);
  chk(rsp(8'h03, 8'h1F, 16'h1, 16'h2, 0), "Enable Channel to 0x1F: 1 / 2");
  // unsupported, wrong length
  xact(8'h50, 8'h00);
  chk(rsp(8'h50, 8'h00, 16'h3, 16'h7FFF, 0), "unsupported command 0x50: 3 / 0x7FFF");
  xact(8'h0E, 8'h1F);
  chk(rsp(8'h0E, 8'h1F, 16'h3, 16'h7FFF, 0), "unsupported command 0x0E to the package: 3 / 0x7FFF");
  xact(8'h03, 8'h00, 4);
  chk(rsp(8'h03, 8'h00, 16'h1, 16'h2, 0), "Enable Channel with 4 payload bytes: 1 / 2");
  xact(8'h04, 8'h01, 0);
  chk(rsp(8'h04, 8'h01, 16'h1, 16'h2, 0), "Disable Channel with no payload: 1 / 2");
  xact(8'h05, 8'h00, 8);
  chk(rsp(8'h05, 8'h00, 16'h1, 16'h2, 0), "Reset Channel with 8 payload bytes: 1 / 2");
  // payload length 28 fills the frame to the checksum (no padding): still parsed
  xact(8'h03, 8'h00, 28);
  chk(fn == 66 && rsp(8'h03, 8'h00, 16'h1, 16'h2, 0), "unpadded 66-byte command with a 28-byte payload: 1 / 2");
  // a length field past the end of the frame (good FCS): dropped
  build(8'h00, 8'h03, 8'h00, 0, 0);
  fb[21] = 8'd60; refcs();
  send_frame();
  chk(!got, "payload length past the frame: no response");
  // a zero checksum is accepted
  xact(8'h03, 8'h00, -1, 5);
  chk(rsp(8'h03, 8'h00, 16'h0, 16'h0, 0), "zero checksum accepted");
  // dropped frames
  xact(8'h0A, 8'h00, -1, 1); chk(!got, "wrong checksum: no response");
  xact(8'h0A, 8'h00, -1, 2); chk(!got, "bad FCS: no response");
  xact(8'h0A, 8'h00, -1, 3); chk(!got, "header revision 2: no response");
  xact(8'h0A, 8'h00, -1, 6); chk(!got, "EtherType 0x0800: no response");
  xact(8'h0A, 8'h20);        chk(!got, "package 1: no response");
  xact(8'h0A, 8'h02);        chk(!got, "channel 2: no response");
  xact(8'h0A, 8'h3F);        chk(!got, "package 1 channel 0x1F: no response");
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h0, 16'h0, 12) && rr[37] == 8'h11, "a clean command after the drops (ch 0 enabled)");
  // reset channel: back to the initial state, disabled
  xact(8'h05, 8'h00);
  chk(rsp(8'h05, 8'h00, 16'h0, 16'h0, 0), "Reset Channel ch 0");
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h1, 16'h1, 0), "after Reset Channel: initialization required");
  xact(8'h00, 8'h00);
  xact(8'h0A, 8'h00);
  chk(rsp(8'h0A, 8'h00, 16'h0, 16'h0, 12) && rr[37] == 8'h10, "Reset Channel left ch 0 disabled");
  xact(8'h0A, 8'h01);
  chk(rsp(8'h0A, 8'h01, 16'h0, 16'h0, 12) && rr[37] == 8'h11, "ch 1 untouched by the reset of ch 0");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #20000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
