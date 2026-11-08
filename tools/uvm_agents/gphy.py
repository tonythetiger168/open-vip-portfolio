# GMII PHY link partner VIP for a gigabit Ethernet MAC (the PHY side of the
# MAC's GMII byte interface, the far end of an IP camera's RTSP / ONVIF port).
#
# Agent -> DUT (receive side of the MAC): one byte per byte time (cfg.bt
# clocks) on grxd with grx_dv, grx_er flags a symbol error: any number of
# preamble bytes 0x55, the SFD 0xD5, DA, SA, length / type, payload and the
# FCS (CRC-32, least significant byte first).
# DUT -> agent: the MAC's transmit side on gtxd / gtx_en / gtx_er (preamble,
# SFD, frame padded to 60 bytes, FCS, at least 12 idle byte times), its
# receive host stream (rx_valid, rx_data, rx_last with rx_stat = {pause,
# phy_err, len_err, crc_err}, rx_frag) and tx_paused.
#
# tb/top_tb.sv gphy_model is the MAC of Ethernet_top in open-ip-portfolio
# (cfg_div = DIV = 1, so a byte time is 2 clocks; cfg_mac = 02:00:5E:10:00:01,
# no promiscuous mode, PAUSE honoured) with a loopback client on its host
# side: every frame received without an error flag that is not a PAUSE frame
# is sent back with DA = the received SA and SA = the MAC address; with a
# length field (< 0x0600) only that many data bytes are sent back, so the
# MAC pads short frames to 60 bytes. PAUSE frames hold the transmitter for
# quanta x 64 byte times. In a SoC bench the agent's pins connect to
# Ethernet_top's GMII and tx_paused pins and the host-stream pins are left
# to the SoC's DMA.

GPHY_FUNCS = """
function automatic bit [31:0] gphy_crc(bit [31:0] c, bit [7:0] d);
  for (int i = 0; i < 8; i++) c = (c[0] ^ d[i]) ? (c >> 1) ^ 32'hEDB88320 : c >> 1;
  return c;
endfunction
"""

SPEC = dict(
    vip="GMII_PHY-UVM-VIP", p="gphy", P="GPHY", dir="gphy", family="Networking",
    desc="GMII PHY link partner VIP for a gigabit Ethernet MAC: preamble / SFD, unicast, broadcast and filtered "
         "frames, CRC, symbol, runt and oversize errors, VLAN tags, PAUSE frames, fragments; checks the MAC's "
         "transmitted frames (preamble, padding, FCS); Ethernet_top MAC model with a loopback client.",
    about="""
An IP camera streams video over its gigabit Ethernet MAC to a GMII PHY. The
agent is that PHY's link partner side: it sends frames to the MAC's address,
broadcast, other unicast and multicast addresses (filtered), frames with a
bad FCS, a grx_er symbol error, runts and oversize frames, VLAN-tagged
maximum frames, PAUSE frames (with and without the PAUSE opcode), bad and
missing preambles, frames cut inside the address and preamble-only bursts,
and takes every frame the MAC transmits. The DUT model is the MAC with a
loopback client that sends good frames back, so the same item checks both
directions: the scoreboard runs its own receive filter, CRC residue and
length rules, predicts the host stream, the status and fragment pulses, and
predicts the exact transmitted frame (preamble, SFD, swapped addresses,
length-field truncation, zero padding to 60 bytes, FCS). The pins are
Ethernet_top's GMII pins in open-ip-portfolio; `cfg.bt` is cfg_div + 1.""",
    defs=GPHY_FUNCS,
    timeout=20000,
    cfg="""int unsigned bt  = 2;                        // clocks per byte time (MAC cfg_div + 1)
bit [47:0]   mac = 48'h02_00_5E_10_00_01;     // the MAC's address (cfg_mac)
int unsigned ifg = 4;                        // extra idle byte times before the next frame""",
    ports=[
        ("in", "logic [7:0]", "grxd"), ("in", "logic", "grx_dv"), ("in", "logic", "grx_er"),
        ("out", "logic [7:0]", "gtxd"), ("out", "logic", "gtx_en"), ("out", "logic", "gtx_er"),
        ("out", "logic", "tx_paused"),
        ("out", "logic", "rx_valid"), ("out", "logic [7:0]", "rx_data"), ("out", "logic", "rx_last"),
        ("out", "logic [3:0]", "rx_stat"), ("out", "logic", "rx_frag"),
    ],
    fields=[
        ("bit [8:0]", "rxb", "req", "q"),       # {grx_er, grxd} per byte time while grx_dv
        ("bit [7:0]", "rxo", "rsp", "q"),       # host stream bytes
        ("bit [3:0]", "rst", "rsp", "q"),       # rx_stat of each rx_last
        ("bit [3:0]", "nfrag", "rsp"),
        ("bit [8:0]", "txo", "rsp", "q"),       # {gtx_er, gtxd} per byte time while gtx_en
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [10:0]", "len", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-4 frame to the MAC (type 0x0800), 5-9 the same with a length field,
// 10 broadcast, 11 other unicast, 12 multicast, 13 FCS error, 14 grx_er,
// 15 runt (38 bytes), 16 1519 bytes, 17 VLAN 1522 bytes, 18 PAUSE, 19 MAC
// control opcode 2, 20 bad preamble byte, 21 no preamble (SFD only),
// 22 cut after 1-5 bytes, 23 preamble only, 24 15-byte preamble, 25 64
// bytes, 26 1518 bytes, 27-28 short length field, 29-31 frame to the MAC
function void set(int k, int l = 60, bit [31:0] s = 32'h1); kind = k; len = l; seed = s; endfunction
function int stat_of(); return rst.size() ? rst[0] : 16; endfunction
function void build(bit [47:0] mac);
  bit [31:0] x = seed | 1;
  bit [7:0] f [$];
  bit [31:0] c = 32'hFFFF_FFFF;
  bit [47:0] da = mac, sa = 48'h02_11_22_33_44_55 ^ {16'h0, seed};
  bit [15:0] et = 16'h0800;
  int n = 46 + len % 200, np = 7, cut = -1;
  if (kind inside {[5:9]}) et = len % 120;
  case (kind)
    10: da = 48'hFFFF_FFFF_FFFF;
    11: da = mac ^ 48'h1;
    12: da = 48'h01_00_5E_00_00_FB;
    15: n = 20;
    16: n = 1501;
    17: begin et = 16'h8100; n = 1504; end
    18, 19: begin da = 48'h01_80_C2_00_00_01; et = 16'h8808; n = 46; end
    21: np = 0;
    22: cut = 1 + x[15:8] % 5;
    24: np = 15;
    25: n = 46;
    26: n = 1500;
    27, 28: et = len % 46;
    default: ;
  endcase
  for (int i = 5; i >= 0; i--) f.push_back(da[8 * i +: 8]);
  for (int i = 5; i >= 0; i--) f.push_back(sa[8 * i +: 8]);
  f.push_back(et[15:8]); f.push_back(et[7:0]);
  for (int i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    f.push_back(x[7:0]);
  end
  if (kind == 18 || kind == 19) begin
    f[14] = 8'h00; f[15] = (kind == 18) ? 8'h01 : 8'h02; f[16] = 8'h00; f[17] = 1 + seed[1:0] % 3;
  end
  foreach (f[i]) c = gphy_crc(c, f[i]);
  for (int i = 0; i < 4; i++) f.push_back(~c[8 * i +: 8]);
  if (kind == 13) f[f.size() - 1 - x[1:0]][x[4:2]] ^= 1'b1;
  rxb.delete();
  for (int i = 0; i < np; i++) rxb.push_back({1'b0, (kind == 20 && i == 3) ? 8'h54 : 8'h55});
  if (kind == 23) return;
  rxb.push_back({1'b0, 8'hD5});
  foreach (f[i]) begin
    if (cut >= 0 && i == cut) break;
    rxb.push_back({kind == 14 && i == 20 + x[5:0], f[i]});
  end
endfunction
""",
    drv_rsp=False,
    drv_desc="one burst per item: the preamble, SFD and frame bytes on grxd with grx_dv, each held cfg.bt clocks; then the line idles until the MAC has been quiet (no gtx_en, no tx_paused) for 12 byte times, plus cfg.ifg byte times",
    drv_idle="""
vif.drv_cb.grxd   <= 8'h00;
vif.drv_cb.grx_dv <= 1'b0;
vif.drv_cb.grx_er <= 1'b0;
""",
    drv_item="""
int q = 0;
t.build(cfg.mac);
@(vif.drv_cb);
foreach (t.rxb[i]) begin
  vif.drv_cb.grx_dv <= 1'b1;
  vif.drv_cb.grxd   <= t.rxb[i][7:0];
  vif.drv_cb.grx_er <= t.rxb[i][8];
  repeat (cfg.bt) @(vif.drv_cb);
end
vif.drv_cb.grx_dv <= 1'b0;
vif.drv_cb.grxd   <= 8'h00;
vif.drv_cb.grx_er <= 1'b0;
while (q < 12 * cfg.bt) begin
  @(vif.drv_cb);
  if (vif.drv_cb.gtx_en || vif.drv_cb.tx_paused) q = 0; else q++;
end
repeat (cfg.ifg * cfg.bt) @(vif.drv_cb);
""",
    mon_desc="from grx_dv rising: the received bytes (one per byte time), the host stream, status and fragment pulses, and the next frame on gtxd, until the MAC has been quiet for 12 byte times",
    mon_run="""
forever begin
  gphy_transaction t;
  int k = 0, tk = -1, q = 0;
  bit in_rx = 1;
  while (vif.mon_cb.grx_dv !== 1'b1) @(vif.mon_cb);
  t = gphy_transaction::type_id::create("t");
  t.nfrag = 0;
  forever begin
    if (vif.mon_cb.rx_valid === 1'b1) begin
      t.rxo.push_back(vif.mon_cb.rx_data);
      if (vif.mon_cb.rx_last === 1'b1) t.rst.push_back(vif.mon_cb.rx_stat);
    end
    if (vif.mon_cb.rx_frag === 1'b1) t.nfrag++;
    if (in_rx) begin
      if (k % cfg.bt == 0) begin
        if (vif.mon_cb.grx_dv !== 1'b1) in_rx = 0;
        else t.rxb.push_back({vif.mon_cb.grx_er, vif.mon_cb.grxd});
      end
      k++;
    end
    if (tk < 0 && vif.mon_cb.gtx_en === 1'b1) tk = 0;
    if (tk >= 0) begin
      if (tk % cfg.bt == 0) begin
        if (vif.mon_cb.gtx_en !== 1'b1) tk = -2;
        else t.txo.push_back({vif.mon_cb.gtx_er, vif.mon_cb.gtxd});
      end
      if (tk >= 0) tk++;
    end
    if (!in_rx) begin
      if (vif.mon_cb.gtx_en === 1'b1 || vif.mon_cb.tx_paused === 1'b1) q = 0; else q++;
      if (q == 12 * cfg.bt) break;
    end
    @(vif.mon_cb);
  end
  publish(t);
end
""",
    predict="""
// the MAC receiver on the burst, then its end (grx_dv low)
int st = 0, rn = 0;          // 0 idle 1 preamble 2 data 3 drop
bit [31:0] rc = 0;
bit perr = 0, acc = 0;
bit [7:0] d [$];
bit [47:0] da = 0;
bit [15:0] ty = 0, op = 0;
t.rxo.delete(); t.rst.delete(); t.nfrag = 0; t.txo.delete();
foreach (t.rxb[i]) begin
  bit [7:0] b = t.rxb[i][7:0];
  case (st)
    0, 1: if (b == 8'hD5) begin st = 2; rn = 0; rc = 32'hFFFF_FFFF; perr = 0; acc = 0; d.delete(); end
          else if (b == 8'h55) st = 1;
          else begin st = 3; t.nfrag++; end
    2: begin
         rc = gphy_crc(rc, b); d.push_back(b);
         if (t.rxb[i][8]) perr = 1;
         if (rn < 6) da = {da[39:0], b};
         if (rn == 5) acc = da == cfg.mac || da == 48'hFFFF_FFFF_FFFF || da == 48'h01_80_C2_00_00_01;
         if (rn == 12 || rn == 13) ty = {ty[7:0], b};
         if (rn == 14 || rn == 15) op = {op[7:0], b};
         rn++;
       end
    default: ;
  endcase
end
if (st == 1) t.nfrag++;
if (st == 2 && rn < 6) t.nfrag++;
else if (st == 2 && acc) begin
  bit ce = rc != 32'hDEBB20E3;
  bit le = rn < 64 || rn > ((ty == 16'h8100) ? 1522 : 1518);
  bit pz = ty == 16'h8808 && op == 16'h0001 && rn >= 18;
  for (int i = 0; i < rn - 4; i++) t.rxo.push_back(d[i]);
  t.rst.push_back({pz, perr, le, ce});
  if (!(pz || perr || le || ce)) begin
    bit [7:0] e [$];
    bit [31:0] c = 32'hFFFF_FFFF;
    int m = rn - 18;
    bit [15:0] et = {d[12], d[13]};
    for (int i = 6; i < 12; i++) e.push_back(d[i]);
    for (int j = 5; j >= 0; j--) e.push_back(cfg.mac[8 * j +: 8]);
    e.push_back(d[12]); e.push_back(d[13]);
    if (et < 16'h0600 && et < m) m = et;
    for (int i = 0; i < m; i++) e.push_back(d[14 + i]);
    while (e.size() < 60) e.push_back(8'h00);
    foreach (e[i]) c = gphy_crc(c, e[i]);
    repeat (7) t.txo.push_back({1'b0, 8'h55});
    t.txo.push_back({1'b0, 8'hD5});
    foreach (e[i]) t.txo.push_back({1'b0, e[i]});
    for (int k = 0; k < 4; k++) t.txo.push_back({1'b0, ~c[8 * k +: 8]});
  end
end
""",
    checks="""
if (t.txo.size() != 0 && t.txo.size() < 72) fail(t, "transmitted frame shorter than 64 bytes");
if (t.txo.size() != 0 && t.rst.size() == 0) fail(t, "frame transmitted without one received");
if (t.rst.size() > 1) fail(t, "two rx_last for one burst");
foreach (t.txo[i]) if (t.txo[i][8]) fail(t, "gtx_er without an underrun");
""",
    coverage="""
cp_stat : coverpoint tr.stat_of() { bins ok = {0}; bins crc = {1}; bins len = {2}; bins phy = {4}; bins pause = {8};
                                    bins none = {16}; }
cp_echo : coverpoint tr.txo.size() { bins none = {0}; bins min = {72}; bins mid = {[73:600]}; bins max = {[1500:1530]}; }
cp_frag : coverpoint tr.nfrag { bins no = {0}; bins yes = {1}; }
""",
    directed="""
// each filter decision, each error, PAUSE, preamble cases, size limits, length-field padding
t = item(); t.set(0, 54, 32'h11); send(t);
t = item(); t.set(5, 30, 32'h12); send(t);
for (int k = 10; k < 32; k++) begin t = item(); t.set(k, 7 * k, 32'h100 + k); send(t); end
t = item(); t.set(18, 0, 32'h2); send(t);
t = item(); t.set(0, 199, 32'h3); send(t);
for (int i = 0; i < 6; i++) begin t = item(); t.set(27, 5 + 9 * i, 32'h200 + i); send(t); end
""",
    drain_ns=20000,
    model="""
module gphy_model #(
  parameter logic [4:0]  DIV      = 5'd1,
  parameter logic [47:0] MAC      = 48'h02_00_5E_10_00_01,
  parameter bit          PAUSE_EN = 1'b1
) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic [7:0]  grxd,
  input  logic        grx_dv,
  input  logic        grx_er,
  output logic [7:0]  gtxd,
  output logic        gtx_en,
  output logic        gtx_er,
  output logic        tx_paused,
  output logic        rx_valid,
  output logic [7:0]  rx_data,
  output logic        rx_last,
  output logic [3:0]  rx_stat,
  output logic        rx_frag
);
  localparam logic [47:0] PAUSE_DA = 48'h0180C2000001;
  localparam logic [31:0] RESIDUE = 32'hDEBB20E3;
  localparam logic [2:0] T_IDLE = 3'd0, T_PRE = 3'd1, T_DATA = 3'd2, T_PAD = 3'd3, T_FCS = 3'd4, T_IFG = 3'd5;
  localparam logic [2:0] R_IDLE = 3'd0, R_PRE = 3'd1, R_DATA = 3'd2, R_DROP = 3'd3, R_FL1 = 3'd4, R_FL2 = 3'd5;
  function automatic logic [31:0] crc8(input logic [31:0] c, input logic [7:0] d);
    logic [31:0] r;
    r = c;
    for (int i = 0; i < 8; i++) r = (r[0] ^ d[i]) ? (r >> 1) ^ 32'hEDB88320 : r >> 1;
    crc8 = r;
  endfunction

  logic [4:0]  dc;
  wire         ls = dc == DIV;
  logic [2:0]  ts, rs;
  logic [3:0]  tk;
  logic [5:0]  tn;
  logic [31:0] tcrc, rcrc;
  logic [21:0] pause;
  logic [10:0] rn;
  logic [7:0]  p0, p1, p2, p3, p4, p5;
  logic [39:0] da;
  logic [15:0] rtype, ropc, rq;
  logic        acc, perr;
  // loopback client: received bytes, then the frame to send back
  logic [7:0]  rbuf [0:2047];
  logic [10:0] ridx, eidx, elen;
  logic        echo;
  wire  [7:0]  ebyte = (eidx < 11'd6) ? rbuf[eidx + 11'd6] : (eidx < 11'd12) ? MAC[8 * (11 - eidx) +: 8] : rbuf[eidx];
  wire  [15:0] et = {rbuf[12], rbuf[13]};

  assign tx_paused = pause != 22'd0;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      dc <= '0; ts <= T_IDLE; tk <= '0; tn <= '0; tcrc <= '0; pause <= '0;
      gtxd <= '0; gtx_en <= 1'b0; gtx_er <= 1'b0;
      rs <= R_IDLE; rn <= '0; rcrc <= '0; {p0, p1, p2, p3, p4, p5} <= '0; da <= '0;
      rtype <= '0; ropc <= '0; rq <= '0; acc <= 1'b0; perr <= 1'b0;
      rx_valid <= 1'b0; rx_data <= '0; rx_last <= 1'b0; rx_stat <= '0; rx_frag <= 1'b0;
      ridx <= '0; eidx <= '0; elen <= '0; echo <= 1'b0;
    end else begin
      rx_valid <= 1'b0; rx_frag <= 1'b0;
      dc <= ls ? 5'd0 : dc + 5'd1;
      if (ls) begin
        if (pause != 22'd0) pause <= pause - 22'd1;
        // ---- transmit (host stream from the loopback client, never late)
        case (ts)
          T_IDLE: if (echo && pause == 22'd0) begin
            ts <= T_PRE; tk <= 4'd1; gtx_en <= 1'b1; gtxd <= 8'h55;
          end
          T_PRE: begin
            tk <= tk + 4'd1;
            gtxd <= tk == 4'd7 ? 8'hD5 : 8'h55;
            if (tk == 4'd7) begin ts <= T_DATA; tn <= '0; tcrc <= '1; end
          end
          T_DATA: begin
            gtxd <= ebyte; tcrc <= crc8(tcrc, ebyte);
            if (tn != 6'd60) tn <= tn + 6'd1;
            eidx <= eidx + 11'd1;
            if (eidx == elen - 11'd1) begin
              echo <= 1'b0;
              if (tn >= 6'd59) ts <= T_FCS; else ts <= T_PAD;
              tk <= '0;
            end
          end
          T_PAD: begin
            gtxd <= 8'h00; tcrc <= crc8(tcrc, 8'h00); tn <= tn + 6'd1;
            if (tn == 6'd59) ts <= T_FCS;
          end
          T_FCS: begin
            gtxd <= ~tcrc[8 * tk[1:0] +: 8];
            tk <= tk + 4'd1;
            if (tk == 4'd3) begin ts <= T_IFG; tk <= '0; end
          end
          T_IFG: begin
            gtx_en <= 1'b0; gtx_er <= 1'b0; gtxd <= 8'h00;
            tk <= tk + 4'd1;
            if (tk == 4'd11) ts <= T_IDLE;
          end
          default: ts <= T_IDLE;
        endcase
        // ---- receive
        case (rs)
          R_IDLE, R_PRE: if (!grx_dv) begin
            if (rs == R_PRE) rx_frag <= 1'b1;
            rs <= R_IDLE;
          end else if (grxd == 8'hD5) begin
            rs <= R_DATA; rn <= '0; rcrc <= '1; perr <= 1'b0; acc <= 1'b0; ridx <= '0;
          end else if (grxd == 8'h55) rs <= R_PRE;
          else begin rs <= R_DROP; rx_frag <= 1'b1; end
          R_DATA: if (grx_dv) begin : b_byte
            logic [47:0] d2;
            rcrc <= crc8(rcrc, grxd);
            if (rn != 11'h7FF) rn <= rn + 11'd1;
            if (grx_er) perr <= 1'b1;
            {p5, p4, p3, p2, p1, p0} <= {p4, p3, p2, p1, p0, grxd};
            d2 = {da, grxd};
            if (rn < 11'd6) da <= d2[39:0];
            if (rn == 11'd5) acc <= d2 == MAC || d2 == 48'hFFFF_FFFF_FFFF || d2 == PAUSE_DA;
            if (rn == 11'd12 || rn == 11'd13) rtype <= {rtype[7:0], grxd};
            if (rn == 11'd14 || rn == 11'd15) ropc <= {ropc[7:0], grxd};
            if (rn == 11'd16 || rn == 11'd17) rq <= {rq[7:0], grxd};
            if (rn >= 11'd6 && acc) begin
              rx_valid <= 1'b1; rx_data <= p5; rx_last <= 1'b0;
              rbuf[ridx] <= p5; ridx <= ridx + 11'd1;
            end
          end else if (rn < 11'd6) begin rs <= R_IDLE; rx_frag <= 1'b1; end
          else if (acc) rs <= R_FL1; else rs <= R_IDLE;
          R_DROP: if (!grx_dv) rs <= R_IDLE;
          R_FL1: begin
            rx_valid <= 1'b1; rx_data <= p5; rx_last <= 1'b0; rs <= R_FL2;
            rbuf[ridx] <= p5; ridx <= ridx + 11'd1;
          end
          R_FL2: begin : b_end
            logic crc_e, len_e, pz;
            logic [10:0] m;
            crc_e = rcrc != RESIDUE;
            len_e = rn < 11'd64 || rn > (rtype == 16'h8100 ? 11'd1522 : 11'd1518);
            pz = rtype == 16'h8808 && ropc == 16'h0001 && rn >= 11'd18;
            rx_valid <= 1'b1; rx_data <= p4; rx_last <= 1'b1;
            rx_stat <= {pz, perr, len_e, crc_e};
            rbuf[ridx] <= p4;
            if (pz && PAUSE_EN && !crc_e && !len_e && !perr) pause <= {rq, 6'd0};
            if (!pz && !crc_e && !len_e && !perr) begin
              m = rn - 11'd18;
              if (et < 16'h0600 && et < {5'd0, m}) m = et[10:0];
              elen <= 11'd14 + m; eidx <= '0; echo <= 1'b1;
            end
            rs <= R_IDLE;
          end
          default: rs <= R_IDLE;
        endcase
      end
    end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({grx_dv, gtx_en, rx_valid, rx_frag, tx_paused}))
  else $error("GPHY: X on a control");
assert property (@(posedge clk) disable iff (!rst_n) grx_dv |-> !$isunknown({grxd, grx_er}))
  else $error("GPHY: X on grxd inside a frame");
assert property (@(posedge clk) disable iff (!rst_n) gtx_en |-> !$isunknown({gtxd, gtx_er}))
  else $error("GPHY: X on gtxd inside a frame");
assert property (@(posedge clk) disable iff (!rst_n) rx_frag |-> !rx_valid)
  else $error("GPHY: fragment pulse with a host byte");
assert property (@(posedge clk) disable iff (!rst_n) gtx_er |-> gtx_en)
  else $error("GPHY: gtx_er outside a frame");
cover property (@(posedge clk) disable iff (!rst_n) $rose(tx_paused));
cover property (@(posedge clk) disable iff (!rst_n) rx_valid && rx_last && rx_stat == 4'h0);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic [7:0] grxd = 8'h00;
logic grx_dv = 1'b0, grx_er = 1'b0;
wire [7:0] gtxd, rx_data;
wire gtx_en, gtx_er, tx_paused, rx_valid, rx_last, rx_frag;
wire [3:0] rx_stat;
localparam logic [47:0] MAC = 48'h02_00_5E_10_00_01;

always #5 clk = ~clk;

gphy_model u_dut (.clk(clk), .rst_n(rst_n), .grxd(grxd), .grx_dv(grx_dv), .grx_er(grx_er), .gtxd(gtxd),
                  .gtx_en(gtx_en), .gtx_er(gtx_er), .tx_paused(tx_paused), .rx_valid(rx_valid),
                  .rx_data(rx_data), .rx_last(rx_last), .rx_stat(rx_stat), .rx_frag(rx_frag));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [31:0] crc8(input logic [31:0] c, input logic [7:0] d);
  logic [31:0] r;
  r = c;
  for (int i = 0; i < 8; i++) r = (r[0] ^ d[i]) ? (r >> 1) ^ 32'hEDB88320 : r >> 1;
  crc8 = r;
endfunction

logic [7:0] fb [0:2047];
integer fn = 0;
// frame without FCS: da, sa 02:11:22:33:44:55, type / length, n payload bytes
task automatic mk(input logic [47:0] da, input logic [15:0] et, input integer n);
  logic [47:0] sa;
  sa = 48'h02_11_22_33_44_55;
  for (int i = 0; i < 6; i++) begin fb[i] = da[8 * (5 - i) +: 8]; fb[6 + i] = sa[8 * (5 - i) +: 8]; end
  fb[12] = et[15:8]; fb[13] = et[7:0];
  for (int i = 0; i < n; i++) fb[14 + i] = 8'h21 + i * 7;
  fn = 14 + n;
endtask
task automatic fcs();
  logic [31:0] c;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 2048; i++) if (i < fn) c = crc8(c, fb[i]);
  for (int i = 0; i < 4; i++) fb[fn + i] = ~c[8 * i +: 8];
  fn = fn + 4;
endtask

logic [7:0] ob [0:2047], tb [0:2047];
integer on = 0, nlast = 0, nfr = 0, tn = 0, tph = 0, ntx = 0;
logic [3:0] lst;
always @(posedge clk) begin
  if (rx_valid) begin ob[on] = rx_data; on = on + 1; end
  if (rx_valid && rx_last) begin nlast = nlast + 1; lst = rx_stat; end
  if (rx_frag) nfr = nfr + 1;
  if (gtx_en) begin
    if (tph == 0) begin tb[tn] = gtxd; tn = tn + 1; if (gtx_er) ntx = ntx + 1; end
    tph = (tph + 1) % 2;
  end else tph = 0;
end
// one burst: np preamble bytes (byte 3 = bad if >= 0), SFD unless nosfd, the first cut bytes of fb
// (all when -1), grx_er on byte erb; then wait until the MAC is quiet unless nowait
task automatic send(input integer np = 7, input integer cut = -1, input integer erb = -1, input integer bad = -1,
                    input logic nosfd = 0, input logic nowait = 0);
  integer n, q;
  on = 0; nlast = 0; nfr = 0; tn = 0;
  n = (cut < 0) ? fn : cut;
  for (int i = 0; i < np; i++) begin @(negedge clk); grx_dv = 1; grxd = (i == bad) ? 8'h54 : 8'h55; @(negedge clk); end
  if (!nosfd) begin @(negedge clk); grx_dv = 1; grxd = 8'hD5; @(negedge clk); end
  if (!nosfd) for (int i = 0; i < n; i++) begin
    @(negedge clk); grx_dv = 1; grxd = fb[i]; grx_er = (i == erb); @(negedge clk);
  end
  @(negedge clk); grx_dv = 0; grxd = 0; grx_er = 0;
  q = 0;
  if (!nowait) while (q < 30) begin @(negedge clk); if (gtx_en || tx_paused) q = 0; else q = q + 1; end
  else repeat (8) @(negedge clk);
endtask
function automatic logic got_rx(input logic [3:0] st);
  logic ok;
  ok = nlast == 1 && lst == st && on == fn - 4 && nfr == 0;
  for (int i = 0; i < 2048; i++) if (i < fn - 4 && ob[i] !== fb[i]) ok = 0;
  got_rx = ok;
endfunction
function automatic logic nothing();
  nothing = on == 0 && nlast == 0 && tn == 0;
endfunction
// expected loopback frame: m data bytes
function automatic logic got_tx(input integer m);
  logic [7:0] e [0:2047];
  logic [31:0] c;
  integer en;
  logic ok;
  for (int i = 0; i < 6; i++) begin e[i] = fb[6 + i]; e[6 + i] = MAC[8 * (5 - i) +: 8]; end
  e[12] = fb[12]; e[13] = fb[13];
  for (int i = 0; i < 2048; i++) if (i >= 14) e[i] = (i < 14 + m) ? fb[i] : 8'h00;
  en = (14 + m < 60) ? 60 : 14 + m;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 2048; i++) if (i < en) c = crc8(c, e[i]);
  ok = tn == 8 + en + 4 && ntx == 0;
  for (int i = 0; i < 7; i++) if (tb[i] !== 8'h55) ok = 0;
  if (tb[7] !== 8'hD5) ok = 0;
  for (int i = 0; i < 2048; i++) if (i < en && tb[8 + i] !== e[i]) ok = 0;
  for (int i = 0; i < 4; i++) if (tb[8 + en + i] !== ~c[8 * i +: 8]) ok = 0;
  got_tx = ok;
endfunction
time tp, te;

initial begin
  repeat (3) @(posedge clk);
  chk(rx_valid === 1'b0 && gtx_en === 1'b0 && rx_frag === 1'b0, "nothing out in reset");
  rst_n = 1;
  repeat (40) @(negedge clk);
  chk(on == 0 && nfr == 0 && tn == 0 && tx_paused == 0, "quiet after reset");
  mk(MAC, 16'h0800, 100); fcs(); send();
  chk(got_rx(4'h0) && got_tx(100), "frame to the MAC: delivered without FCS, sent back with swapped addresses");
  mk(48'hFFFF_FFFF_FFFF, 16'h0800, 46); fcs(); send();
  chk(got_rx(4'h0) && got_tx(46), "broadcast, 64 bytes: sent back without padding");
  mk(MAC ^ 48'h1, 16'h0800, 60); fcs(); send();
  chk(nothing() && nfr == 0, "other unicast: dropped silently");
  mk(48'h01_00_5E_00_00_FB, 16'h0800, 60); fcs(); send();
  chk(nothing(), "multicast: dropped");
  mk(MAC, 16'h0800, 60); fcs(); fb[fn - 2] = fb[fn - 2] ^ 8'h10; send();
  chk(got_rx(4'h1) && tn == 0, "FCS error: crc_err, not sent back");
  mk(MAC, 16'h0800, 60); fcs(); send(7, -1, 33);
  chk(got_rx(4'h4) && tn == 0, "grx_er: phy_err");
  mk(MAC, 16'h0800, 20); fcs(); send();
  chk(got_rx(4'h2) && tn == 0, "38-byte runt: len_err");
  mk(MAC, 16'h0800, 1501); fcs(); send();
  chk(got_rx(4'h2) && tn == 0, "1519 bytes: len_err");
  mk(MAC, 16'h0800, 1500); fcs(); send();
  chk(got_rx(4'h0) && got_tx(1500), "1518 bytes: good");
  mk(MAC, 16'h8100, 1504); fcs(); send();
  chk(got_rx(4'h0) && got_tx(1504), "VLAN-tagged 1522 bytes: good");
  mk(MAC, 16'd20, 46); fcs(); send();
  chk(got_rx(4'h0) && got_tx(20), "length field 20: 20 data bytes sent back, padded to 60");
  mk(MAC, 16'd100, 60); fcs(); send();
  chk(got_rx(4'h0) && got_tx(60), "length field longer than the frame: all of it");
  mk(MAC, 16'h0600, 50); fcs(); send();
  chk(got_rx(4'h0) && got_tx(50), "type 0x0600 is not a length");
  mk(48'h01_80_C2_00_00_01, 16'h8808, 46); fb[14] = 0; fb[15] = 1; fb[16] = 0; fb[17] = 2; fcs(); send(7, -1, -1, -1, 0, 1);
  chk(nlast == 1 && lst == 4'h8 && tn == 0 && tx_paused == 1, "PAUSE quanta 2: pause status, transmitter held");
  tp = $time;
  mk(MAC, 16'h0800, 46); fcs(); send();
  te = $time;
  chk(got_rx(4'h0) && got_tx(46), "frame during the pause is sent back after it");
  chk(te - tp >= 2 * 64 * 20, "pause lasted at least 128 byte times");
  mk(48'h01_80_C2_00_00_01, 16'h8808, 46); fb[14] = 0; fb[15] = 2; fb[16] = 0; fb[17] = 2; fcs(); send();
  chk(got_rx(4'h0) && got_tx(46) && tx_paused == 0, "MAC control opcode 2: not a PAUSE");
  mk(48'h01_80_C2_00_00_01, 16'h8808, 46); fb[14] = 0; fb[15] = 1; fb[16] = 0; fb[17] = 2; fcs();
  fb[fn - 1] = ~fb[fn - 1]; send();
  chk(got_rx(4'h9) && tx_paused == 0, "PAUSE with an FCS error is not honoured");
  mk(MAC, 16'h0800, 60); fcs(); send(7, -1, -1, 3);
  chk(nothing() && nfr == 1, "bad preamble byte: fragment");
  mk(MAC, 16'h0800, 60); fcs(); send(0);
  chk(got_rx(4'h0) && got_tx(60), "SFD without preamble");
  mk(MAC, 16'h0800, 60); fcs(); send(15);
  chk(got_rx(4'h0) && got_tx(60), "15-byte preamble");
  mk(MAC, 16'h0800, 60); fcs(); send(7, 3);
  chk(nothing() && nfr == 1, "frame cut after 3 bytes: fragment");
  mk(MAC, 16'h0800, 60); fcs(); send(7, 6);
  chk(nlast == 1 && lst == 4'h3 && on == 2 && nfr == 0, "6-byte frame: delivered with crc and len errors");
  mk(MAC, 16'h0800, 60); fcs(); send(7, -1, -1, -1, 1);
  chk(nothing() && nfr == 1, "preamble only: fragment");
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
