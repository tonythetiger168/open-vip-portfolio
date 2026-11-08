# MIPI CSI-2 camera sensor transmitter VIP (packet layer over one serial HS
# lane, the camera side of an IP camera / phone ISP input).
#
# Agent -> DUT, one bit per clock while rx_valid is high (one HS burst, SoT to
# EoT, LSB first per byte): HS-zero lead-in bits, the 0xB8 sync byte, the
# packet header {DI = {VC, DT}, WC[7:0], WC[15:8]} and its ECC byte (CSI-2
# Hamming code, 6 parity bits, bits 7:6 zero), for long packets (DT >= 0x10)
# WC payload bytes and the CRC-16 (poly 0x1021 reflected, init 0xFFFF, low
# byte first); further packets in the same burst start with 0xB8 on the same
# byte alignment, and the burst ends with trailer bits (the inverse of the
# last bit). Short packets: FS 0x00 / FE 0x01 (data field = frame number),
# LS 0x02 / LE 0x03.
# DUT -> agent: every payload byte as received (out_valid, out_data) and one
# report per packet: rep_flags [0] CRC error [1] ECC uncorrectable (header
# dropped, dt / wc 0) [2] burst ended inside the packet [3] ECC corrected,
# with rep_dt / rep_wc (corrected header), rep_frame (FS count) and rep_line
# (good long packets since FS).
#
# tb/top_tb.sv csis_model is the packet layer of CSI_2_top in open-ip-portfolio
# (same sync hunt, ECC, CRC, frame / line counting); the agent's pins are the
# IP's rx_bit / rx_valid, so in a SoC bench the driver and monitor connect to
# CSI_2_top directly and the report pins are left open.

CSIS_FUNCS = """
function automatic bit [5:0] csis_ecc(bit [23:0] d);
  bit [5:0] e;
  e[0] = d[0]^d[1]^d[2]^d[4]^d[5]^d[7]^d[10]^d[11]^d[13]^d[16]^d[20]^d[21]^d[22]^d[23];
  e[1] = d[0]^d[1]^d[3]^d[4]^d[6]^d[8]^d[10]^d[12]^d[14]^d[17]^d[20]^d[21]^d[22]^d[23];
  e[2] = d[0]^d[2]^d[3]^d[5]^d[6]^d[9]^d[11]^d[12]^d[15]^d[18]^d[20]^d[21]^d[22];
  e[3] = d[1]^d[2]^d[3]^d[7]^d[8]^d[9]^d[13]^d[14]^d[15]^d[19]^d[20]^d[21]^d[23];
  e[4] = d[4]^d[5]^d[6]^d[7]^d[8]^d[9]^d[16]^d[17]^d[18]^d[19]^d[20]^d[22]^d[23];
  e[5] = d[10]^d[11]^d[12]^d[13]^d[14]^d[15]^d[16]^d[17]^d[18]^d[19]^d[21]^d[22]^d[23];
  return e;
endfunction
function automatic bit [23:0] csis_fix(bit [5:0] syn);   // data bit a syndrome points at, 0 if none
  for (int i = 0; i < 24; i++) if (syn == csis_ecc(24'h1 << i)) return 24'h1 << i;
  return 24'h0;
endfunction
function automatic bit [15:0] csis_crc(bit [15:0] c, bit [7:0] d);
  bit [15:0] v = c ^ {8'h00, d};
  for (int k = 0; k < 8; k++) v = v[0] ? (v >> 1) ^ 16'h8408 : (v >> 1);
  return v;
endfunction
// report word: {4'h0, flags, dt, wc, frame, line}
function automatic bit [63:0] csis_rep(bit [3:0] f, bit [23:0] h, bit [15:0] fr, bit [15:0] ln);
  return {4'h0, f, h[7:0], h[23:8], fr, ln};
endfunction
"""

SPEC = dict(
    vip="CSI2_Sensor-UVM-VIP", p="csis", P="CSIS", dir="csis", family="Video",
    desc="MIPI CSI-2 camera sensor transmitter VIP: serial HS bursts with SoT sync, packet headers with ECC, "
         "FS / FE / LS / LE short packets, RAW / YUV / RGB long packets with CRC-16, several packets per burst; "
         "receiver model with ECC correction, CRC check and frame / line counting (CSI_2_top pins).",
    about="""
The camera sensor of an IP camera or phone sends frames to the SoC's CSI-2
receiver as HS bursts of packets. The agent is that sensor: it sends Frame
Start / Frame End with the frame number, Line Start / Line End, image lines
in RAW8, RAW10, YUV422 and RGB888 data types on any virtual channel, empty
long packets and long lines, several packets in one burst, and faults:
single-bit header errors in every position (corrected), ECC byte errors,
two-bit header errors (dropped), payload and CRC errors, bursts cut inside
the header, payload or CRC, a junk byte between packets, random HS-zero
lead-in and trailer lengths. The DUT model is the receiver's packet layer;
the scoreboard runs its own bit-level receiver on the monitored bits and
predicts every report, the payload stream and the frame / line counters
across bursts. The pins are CSI_2_top's rx_bit / rx_valid in
open-ip-portfolio, so the same agent drives the IP in a SoC bench.""",
    defs=CSIS_FUNCS,
    timeout=2000,
    cfg="""int unsigned gap = 8;      // clocks with rx_valid low between bursts (LP state), at least 4""",
    ports=[
        ("in", "logic", "rx_valid"), ("in", "logic", "rx_bit"),
        ("out", "logic", "rep_valid"), ("out", "logic [3:0]", "rep_flags"), ("out", "logic [7:0]", "rep_dt"),
        ("out", "logic [15:0]", "rep_wc"), ("out", "logic [15:0]", "rep_frame"), ("out", "logic [15:0]", "rep_line"),
        ("out", "logic", "out_valid"), ("out", "logic [7:0]", "out_data"),
    ],
    fields=[
        ("bit", "bits", "req", "q"),
        ("bit [63:0]", "rep", "rsp", "q"),
        ("bit [7:0]", "pay", "rsp", "q"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "dsel", "info", "rand"),
        ("bit [1:0]", "vc", "info", "rand"),
        ("bit [7:0]", "wc", "info", "rand"),
        ("bit [3:0]", "lead", "info", "rand"),
        ("bit [3:0]", "trail", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-9 one image line, 10 FS, 11 FE, 12 LS / LE, 13 FS + line in one
// burst, 14 two lines + FE in one burst, 15 long packet with WC 0, 16 header
// data bit error, 17 ECC bit error, 18 ECC bits 7:6 set, 19 two-bit header
// error, 20 payload bit error, 21 CRC bit error, 22 burst cut in the header,
// 23 cut in the payload, 24 cut in the CRC, 25 uncorrectable packet then a
// good one, 26 junk byte between two packets, 27 line of 100-355 bytes,
// 28 line with a header bit error, 29-31 image line.
function void set(int k, int w = 8, bit [31:0] s = 32'h1); kind = k; wc = w; seed = s; endfunction
function bit [5:0] dt_of();
  case (dsel)
    0: return 6'h2A;      // RAW8
    1: return 6'h2B;      // RAW10
    2: return 6'h1E;      // YUV422 8-bit
    default: return 6'h24; // RGB888
  endcase
endfunction
// one packet; hf: 1 data bit, 2 ECC bit, 3 ECC bits 7:6, 4 two data bits;
// pf: 1 payload bit, 2 CRC bit
function void pkt(ref bit [7:0] b[$], input bit [7:0] di, input bit [15:0] w, input int hf, input int pf,
                  ref bit [31:0] x);
  bit [23:0] h = {w, di};
  bit [7:0] e = {2'b00, csis_ecc(h)};
  bit [15:0] c = 16'hFFFF;
  bit [7:0] p [$];
  int j;
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  case (hf)
    1: h[x[15:8] % 24] ^= 1'b1;
    2: e[x[15:8] % 6] ^= 1'b1;
    3: e[7:6] = x[9:8] | 2'b01;
    4: begin j = x[15:8] % 24; h[j] ^= 1'b1; h[(j + 1 + x[23:16] % 23) % 24] ^= 1'b1; end
    default: ;
  endcase
  b.push_back(8'hB8); b.push_back(h[7:0]); b.push_back(h[15:8]); b.push_back(h[23:16]); b.push_back(e);
  if (di[5:0] >= 6'h10) begin
    for (int i = 0; i < w; i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      p.push_back(x[7:0]); c = csis_crc(c, x[7:0]);
    end
    if (pf == 1 && w != 0) begin j = x[7:0] % w; p[j][x[10:8]] ^= 1'b1; end
    if (pf == 2) c[x[11:8]] ^= 1'b1;
    foreach (p[i]) b.push_back(p[i]);
    b.push_back(c[7:0]); b.push_back(c[15:8]);
  end
endfunction
function void build();
  bit [31:0] x = seed | 1;
  bit [7:0] b [$];
  bit [7:0] di = {vc, dt_of()};
  bit [15:0] w = 1 + wc % 48;
  int cut = -1;
  case (kind)
    10: pkt(b, {vc, 6'h00}, seed[15:0], 0, 0, x);
    11: pkt(b, {vc, 6'h01}, seed[15:0], 0, 0, x);
    12: pkt(b, {vc, 5'h01, seed[0]}, seed[15:0], 0, 0, x);
    13: begin pkt(b, {vc, 6'h00}, seed[15:0], 0, 0, x); pkt(b, di, w, 0, 0, x); end
    14: begin pkt(b, di, w, 0, 0, x); pkt(b, di, w, 0, 0, x); pkt(b, {vc, 6'h01}, seed[15:0], 0, 0, x); end
    15: pkt(b, di, 16'h0, 0, 0, x);
    16: pkt(b, di, w, 1, 0, x);
    17: pkt(b, di, w, 2, 0, x);
    18: pkt(b, di, w, 3, 0, x);
    19: pkt(b, di, w, 4, 0, x);
    20: pkt(b, di, w, 0, 1, x);
    21: pkt(b, di, w, 0, 2, x);
    22: begin pkt(b, di, w, 0, 0, x); cut = 1 + x[1:0]; end
    23: begin pkt(b, di, w, 0, 0, x); cut = 5 + x[15:8] % w; end
    24: begin pkt(b, di, w, 0, 0, x); cut = 5 + w + x[0]; end
    25: begin pkt(b, di, w, 4, 0, x); pkt(b, di, w, 0, 0, x); end
    26: begin pkt(b, di, w, 0, 0, x); b.push_back(8'h00); pkt(b, di, w, 0, 0, x); end
    27: pkt(b, di, 16'd100 + wc, 0, 0, x);
    28: pkt(b, di, w, 1, 0, x);
    default: pkt(b, di, w, 0, 0, x);
  endcase
  bits.delete();
  for (int i = 0; i < lead; i++) bits.push_back(1'b0);
  foreach (b[i]) for (int k = 0; k < 8; k++) bits.push_back(b[i][k]);
  if (cut >= 0) begin
    int n = lead + 8 * cut + x[18:16];
    while (bits.size() > n) void'(bits.pop_back());
  end else begin
    bit l = bits[bits.size() - 1];
    for (int i = 0; i < trail; i++) bits.push_back(!l);
  end
endfunction
""",
    drv_rsp=False,
    drv_desc="one HS burst per item: rx_valid high for the lead-in, packet and trailer bits (one per clock), then cfg.gap clocks low",
    drv_idle="""
vif.drv_cb.rx_valid <= 1'b0;
vif.drv_cb.rx_bit   <= 1'b0;
""",
    drv_item="""
t.build();
@(vif.drv_cb);
foreach (t.bits[i]) begin
  vif.drv_cb.rx_valid <= 1'b1;
  vif.drv_cb.rx_bit   <= t.bits[i];
  @(vif.drv_cb);
end
vif.drv_cb.rx_valid <= 1'b0;
vif.drv_cb.rx_bit   <= 1'b0;
repeat ((cfg.gap < 4) ? 4 : cfg.gap) @(vif.drv_cb);
""",
    mon_desc="the bits of each HS burst (rx_valid high) with the payload bytes and reports up to three clocks after it",
    mon_run="""
csis_transaction t;
int idle = 0;
forever begin
  @(vif.mon_cb);
  if (t == null && vif.mon_cb.rx_valid === 1'b1) begin t = csis_transaction::type_id::create("t"); idle = 0; end
  if (t != null) begin
    if (vif.mon_cb.rep_valid === 1'b1)
      t.rep.push_back(csis_rep(vif.mon_cb.rep_flags, {vif.mon_cb.rep_wc, vif.mon_cb.rep_dt},
                               vif.mon_cb.rep_frame, vif.mon_cb.rep_line));
    if (vif.mon_cb.out_valid === 1'b1) t.pay.push_back(vif.mon_cb.out_data);
    if (vif.mon_cb.rx_valid === 1'b1) begin t.bits.push_back(vif.mon_cb.rx_bit); idle = 0; end
    else if (++idle == 3) begin publish(t); t = null; end
  end
end
""",
    sb_members="""bit [15:0] frm = 0;
bit [15:0] lin = 0;""",
    predict="""
// bit-level receiver: sync hunt, header + ECC, payload + CRC, next sync or EoT
int st = 0;                 // 0 hunt 1-3 header 4 ECC 5 payload 6-7 CRC 8 next 9 EoT
int bc = 0;
bit [6:0] sh = 0;
bit [23:0] hdr = 0, hc = 0;
bit [15:0] w = 0, pc = 0, crc = 0;
bit [7:0] clo = 0;
bit corr = 0;
t.rep.delete(); t.pay.delete();
foreach (t.bits[i]) begin
  bit [7:0] rb = {t.bits[i], sh};
  bit rdy = (bc == 7);
  sh = rb[7:1];
  bc = (bc + 1) % 8;
  if (st == 0) begin
    if (rb == 8'hB8) begin st = 1; bc = 0; end
  end else if (rdy) begin
    case (st)
      8: st = (rb == 8'hB8) ? 1 : 9;
      1: begin hdr[7:0] = rb; st = 2; end
      2: begin hdr[15:8] = rb; st = 3; end
      3: begin hdr[23:16] = rb; st = 4; end
      4: begin
           bit [5:0] syn = rb[5:0] ^ csis_ecc(hdr);
           bit [23:0] fx = csis_fix(syn);
           bit oh = syn != 0 && (syn & (syn - 6'd1)) == 0;
           if (!(syn == 0 || fx != 0 || oh)) begin st = 8; t.rep.push_back(csis_rep(4'b0010, 24'h0, frm, lin)); end
           else begin
             hc = hdr ^ fx; corr = (syn != 0);
             if (hc[5:0] < 6'h10) begin
               st = 8;
               if (hc[5:0] == 6'h00) begin frm++; lin = 0; end
               t.rep.push_back(csis_rep({corr, 3'b000}, hc, frm, lin));
             end else begin
               w = hc[23:8]; pc = 0; crc = 16'hFFFF;
               st = (w == 0) ? 6 : 5;
             end
           end
         end
      5: begin crc = csis_crc(crc, rb); t.pay.push_back(rb); pc++; if (pc == w) st = 6; end
      6: begin clo = rb; st = 7; end
      7: begin
           st = 8;
           if ({rb, clo} == crc) lin++;
           t.rep.push_back(csis_rep({corr, 2'b00, {rb, clo} != crc}, hc, frm, lin));
         end
      default: ;
    endcase
  end
end
if (st >= 1 && st <= 7) t.rep.push_back(csis_rep({corr && st >= 5, 3'b100}, (st >= 5) ? hc : 24'h0, frm, lin));
""",
    checks="""
foreach (t.rep[i]) begin
  if (t.rep[i][57] && t.rep[i][55:32] != 0) fail(t, "dropped header reported with a data type / word count");
  if (t.rep[i][57] && t.rep[i][59:56] != 4'b0010) fail(t, "uncorrectable header with other flags");
  if (t.rep[i][56] && t.rep[i][53:48] < 6'h10) fail(t, "CRC error on a short packet");
end
if (t.rep.size() == 0) fail(t, "burst without a packet report");
""",
    coverage="""
cp_flags : coverpoint (tr.rep.size() ? tr.rep[0][59:56] : 4'h0) { bins clean = {0}; bins crc = {1}; bins unc = {2};
                                                                   bins cut = {4}; bins corr = {8}; bins corr_cut = {12}; }
cp_dt    : coverpoint (tr.rep.size() ? tr.rep[0][53:48] : 6'h3F) { bins fs = {6'h00}; bins fe = {6'h01}; bins ls_le = {6'h02, 6'h03};
                                                                   bins raw8 = {6'h2A}; bins raw10 = {6'h2B}; bins yuv = {6'h1E};
                                                                   bins rgb = {6'h24}; }
cp_vc    : coverpoint (tr.rep.size() ? tr.rep[0][55:54] : 2'd0);
cp_npk   : coverpoint tr.rep.size() { bins one = {1}; bins multi = {[2:3]}; }
""",
    directed="""
// a frame of RAW8 lines with line start / end, every data type, every fault, multi-packet bursts
t = item(); t.set(10, 0, 32'h1); send(t);
for (int i = 0; i < 6; i++) begin t = item(); t.set(0, 8 + i, 32'h100 + i); t.dsel = i % 4; send(t); end
t = item(); t.set(12, 0, 32'h2); send(t);
t = item(); t.set(12, 0, 32'h3); send(t);
t = item(); t.set(11, 0, 32'h1); send(t);
for (int k = 13; k < 32; k++)
  for (int s = 0; s < 3; s++) begin t = item(); t.set(k, 5 + 11 * s, 32'h1000 * k + 7 * s + 1); send(t); end
for (int i = 0; i < 24; i++) begin t = item(); t.set(16, 3 + i, 32'h5000 + i); send(t); end
t = item(); t.set(10, 0, 32'hFFFF); send(t);
""",
    drain_ns=4000,
    model="""
module csis_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        rx_valid,
  input  logic        rx_bit,
  output logic        rep_valid,
  output logic [3:0]  rep_flags,
  output logic [7:0]  rep_dt,
  output logic [15:0] rep_wc,
  output logic [15:0] rep_frame,
  output logic [15:0] rep_line,
  output logic        out_valid,
  output logic [7:0]  out_data
);
  localparam logic [3:0] S_HUNT = 4'd0, S_HDR0 = 4'd1, S_HDR1 = 4'd2, S_HDR2 = 4'd3, S_ECC = 4'd4,
                         S_PAY = 4'd5, S_CRC0 = 4'd6, S_CRC1 = 4'd7, S_NEXT = 4'd8, S_EOT = 4'd9;

  function automatic logic [5:0] ecc24(input logic [23:0] d);
    ecc24[0] = d[0]^d[1]^d[2]^d[4]^d[5]^d[7]^d[10]^d[11]^d[13]^d[16]^d[20]^d[21]^d[22]^d[23];
    ecc24[1] = d[0]^d[1]^d[3]^d[4]^d[6]^d[8]^d[10]^d[12]^d[14]^d[17]^d[20]^d[21]^d[22]^d[23];
    ecc24[2] = d[0]^d[2]^d[3]^d[5]^d[6]^d[9]^d[11]^d[12]^d[15]^d[18]^d[20]^d[21]^d[22];
    ecc24[3] = d[1]^d[2]^d[3]^d[7]^d[8]^d[9]^d[13]^d[14]^d[15]^d[19]^d[20]^d[21]^d[23];
    ecc24[4] = d[4]^d[5]^d[6]^d[7]^d[8]^d[9]^d[16]^d[17]^d[18]^d[19]^d[20]^d[22]^d[23];
    ecc24[5] = d[10]^d[11]^d[12]^d[13]^d[14]^d[15]^d[16]^d[17]^d[18]^d[19]^d[21]^d[22]^d[23];
  endfunction
  function automatic logic [23:0] ecc_fix(input logic [5:0] syn);
    ecc_fix = '0;
    for (int i = 0; i < 24; i++) if (syn == ecc24(24'h1 << i)) ecc_fix = 24'h1 << i;
  endfunction
  function automatic logic [15:0] crc16_byte(input logic [15:0] c, input logic [7:0] d);
    logic [15:0] v;
    v = c ^ {8'h00, d};
    for (int k = 0; k < 8; k++) v = v[0] ? (v >> 1) ^ 16'h8408 : (v >> 1);
    crc16_byte = v;
  endfunction

  logic [3:0]  state;
  logic [6:0]  shreg;
  logic [2:0]  bit_cnt;
  logic [23:0] hdr, hc_r;
  logic [15:0] wc, pay_cnt, crc, frame_cnt, line_cnt;
  logic [7:0]  crc_lo;
  logic        corr;

  wire [7:0]  rx_byte  = {rx_bit, shreg};
  wire        byte_rdy = rx_valid && bit_cnt == 3'd7;
  wire [5:0]  syn      = rx_byte[5:0] ^ ecc24(hdr);
  wire [23:0] fix      = ecc_fix(syn);
  wire        ecc_bit  = syn != 6'h00 && (syn & (syn - 6'd1)) == 6'h00;
  wire        ecc_ok   = syn == 6'h00 || fix != '0 || ecc_bit;
  wire [23:0] hc       = hdr ^ fix;
  wire        in_pkt   = state != S_HUNT && state != S_NEXT && state != S_EOT;
  wire        hdr_done = state == S_PAY || state == S_CRC0 || state == S_CRC1;

  assign rep_frame = frame_cnt;
  assign rep_line  = line_cnt;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= S_HUNT; shreg <= '0; bit_cnt <= '0; hdr <= '0; hc_r <= '0; wc <= '0;
      pay_cnt <= '0; crc <= 16'hFFFF; crc_lo <= '0; corr <= 1'b0; frame_cnt <= '0; line_cnt <= '0;
      rep_valid <= 1'b0; rep_flags <= '0; rep_dt <= '0; rep_wc <= '0; out_valid <= 1'b0; out_data <= '0;
    end else begin
      rep_valid <= 1'b0;
      out_valid <= 1'b0;
      if (!rx_valid) begin
        bit_cnt <= '0;
        state   <= S_HUNT;
        if (in_pkt) begin
          rep_valid <= 1'b1;
          rep_flags <= {corr && hdr_done, 3'b100};
          rep_dt    <= hdr_done ? hc_r[7:0] : 8'h00;
          rep_wc    <= hdr_done ? hc_r[23:8] : 16'h0000;
        end
      end else begin
        shreg   <= rx_byte[7:1];
        bit_cnt <= bit_cnt + 3'd1;
        if (state == S_HUNT) begin
          if (rx_byte == 8'hB8) begin state <= S_HDR0; bit_cnt <= '0; end
        end else if (byte_rdy) begin
          case (state)
            S_NEXT: state <= (rx_byte == 8'hB8) ? S_HDR0 : S_EOT;
            S_HDR0: begin hdr[7:0]   <= rx_byte; state <= S_HDR1; end
            S_HDR1: begin hdr[15:8]  <= rx_byte; state <= S_HDR2; end
            S_HDR2: begin hdr[23:16] <= rx_byte; state <= S_ECC;  end
            S_ECC: begin
              if (!ecc_ok) begin
                state <= S_NEXT;
                rep_valid <= 1'b1; rep_flags <= 4'b0010; rep_dt <= 8'h00; rep_wc <= 16'h0000;
              end else begin
                hc_r <= hc;
                corr <= syn != 6'h00;
                if (hc[5:0] < 6'h10) begin
                  state <= S_NEXT;
                  rep_valid <= 1'b1; rep_flags <= {syn != 6'h00, 3'b000}; rep_dt <= hc[7:0]; rep_wc <= hc[23:8];
                  if (hc[5:0] == 6'h00) begin frame_cnt <= frame_cnt + 16'd1; line_cnt <= '0; end
                end else begin
                  wc <= hc[23:8]; pay_cnt <= '0; crc <= 16'hFFFF;
                  state <= (hc[23:8] == 16'h0) ? S_CRC0 : S_PAY;
                end
              end
            end
            S_PAY: begin
              crc <= crc16_byte(crc, rx_byte);
              out_valid <= 1'b1; out_data <= rx_byte;
              pay_cnt <= pay_cnt + 16'd1;
              if (pay_cnt == wc - 16'd1) state <= S_CRC0;
            end
            S_CRC0: begin crc_lo <= rx_byte; state <= S_CRC1; end
            S_CRC1: begin
              state <= S_NEXT;
              rep_valid <= 1'b1;
              rep_flags <= {corr, 2'b00, {rx_byte, crc_lo} != crc};
              rep_dt <= hc_r[7:0]; rep_wc <= hc_r[23:8];
              if ({rx_byte, crc_lo} == crc) line_cnt <= line_cnt + 16'd1;
            end
            default: ;
          endcase
        end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({rx_valid, rep_valid, out_valid}))
  else $error("CSIS: X on a valid");
assert property (@(posedge clk) disable iff (!rst_n) rx_valid |-> !$isunknown(rx_bit))
  else $error("CSIS: X on rx_bit inside a burst");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_flags[1] |-> rep_flags == 4'b0010 && rep_dt == 8'h00 && rep_wc == 16'h0)
  else $error("CSIS: dropped header reported with fields");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_flags[0] |-> rep_dt[5:0] >= 6'h10)
  else $error("CSIS: CRC error on a short packet");
assert property (@(posedge clk) disable iff (!rst_n) out_valid |-> !rep_valid)
  else $error("CSIS: payload byte and report in the same clock");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_flags == 4'b1000);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_flags[2]);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic rx_valid = 1'b0, rx_bit = 1'b0;
wire rep_valid, out_valid;
wire [3:0] rep_flags;
wire [7:0] rep_dt, out_data;
wire [15:0] rep_wc, rep_frame, rep_line;

always #5 clk = ~clk;

csis_model u_dut (.clk(clk), .rst_n(rst_n), .rx_valid(rx_valid), .rx_bit(rx_bit), .rep_valid(rep_valid),
                  .rep_flags(rep_flags), .rep_dt(rep_dt), .rep_wc(rep_wc), .rep_frame(rep_frame),
                  .rep_line(rep_line), .out_valid(out_valid), .out_data(out_data));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [5:0] ecc24(input logic [23:0] d);
  ecc24[0] = d[0]^d[1]^d[2]^d[4]^d[5]^d[7]^d[10]^d[11]^d[13]^d[16]^d[20]^d[21]^d[22]^d[23];
  ecc24[1] = d[0]^d[1]^d[3]^d[4]^d[6]^d[8]^d[10]^d[12]^d[14]^d[17]^d[20]^d[21]^d[22]^d[23];
  ecc24[2] = d[0]^d[2]^d[3]^d[5]^d[6]^d[9]^d[11]^d[12]^d[15]^d[18]^d[20]^d[21]^d[22];
  ecc24[3] = d[1]^d[2]^d[3]^d[7]^d[8]^d[9]^d[13]^d[14]^d[15]^d[19]^d[20]^d[21]^d[23];
  ecc24[4] = d[4]^d[5]^d[6]^d[7]^d[8]^d[9]^d[16]^d[17]^d[18]^d[19]^d[20]^d[22]^d[23];
  ecc24[5] = d[10]^d[11]^d[12]^d[13]^d[14]^d[15]^d[16]^d[17]^d[18]^d[19]^d[21]^d[22]^d[23];
endfunction
function automatic logic [15:0] crc16(input logic [15:0] c, input logic [7:0] d);
  logic [15:0] v;
  v = c ^ {8'h00, d};
  for (int k = 0; k < 8; k++) v = v[0] ? (v >> 1) ^ 16'h8408 : (v >> 1);
  crc16 = v;
endfunction

logic [7:0] pb [0:1023];
integer pn = 0, p0 = 0, pw = 0;
// packet at pb[pn]: hf 1 data bit hb, 2 ECC bit hb, 3 ECC bits 7:6, 4 data bits hb and hb+5;
// pf 1 last payload byte bit 3, 2 CRC bit 9
task automatic addpkt(input logic [7:0] di, input logic [15:0] w, input integer hf = 0, input integer hb = 0,
                      input integer pf = 0);
  logic [23:0] h;
  logic [7:0] e;
  logic [15:0] c;
  h = {w, di}; e = {2'b00, ecc24(h)}; c = 16'hFFFF;
  if (hf == 1) h[hb] = ~h[hb];
  if (hf == 2) e[hb] = ~e[hb];
  if (hf == 3) e[7:6] = 2'b11;
  if (hf == 4) begin h[hb] = ~h[hb]; h[(hb + 5) % 24] = ~h[(hb + 5) % 24]; end
  pb[pn] = 8'hB8; pb[pn + 1] = h[7:0]; pb[pn + 2] = h[15:8]; pb[pn + 3] = h[23:16]; pb[pn + 4] = e;
  pn = pn + 5; p0 = pn; pw = 0;
  if (di[5:0] >= 6'h10) begin
    for (int i = 0; i < w; i++) begin pb[pn] = (8'h30 + i * 13) ^ di; c = crc16(c, pb[pn]); pn = pn + 1; end
    pw = w;
    if (pf == 1) pb[pn - 1][3] = ~pb[pn - 1][3];
    if (pf == 2) c[9] = ~c[9];
    pb[pn] = c[7:0]; pb[pn + 1] = c[15:8]; pn = pn + 2;
  end
endtask

logic [7:0] ob [0:1023];
integer on = 0, nrep = 0, r0 = 0, both = 0;
logic [3:0]  r_f  [0:255];
logic [7:0]  r_dt [0:255];
logic [15:0] r_wc [0:255], r_fr [0:255], r_ln [0:255];
always @(posedge clk) begin
  if (out_valid) begin ob[on] = out_data; on = on + 1; end
  if (out_valid && rep_valid) both = both + 1;
  if (rep_valid) begin
    r_f[nrep] = rep_flags; r_dt[nrep] = rep_dt; r_wc[nrep] = rep_wc; r_fr[nrep] = rep_frame; r_ln[nrep] = rep_line;
    nrep = nrep + 1;
  end
end
// one burst: lead zeros, the first nb bits of pb (all when -1), trail bits of value tv, gap clocks low
task automatic send(input integer lead = 3, input integer nb = -1, input integer trail = 4, input logic tv = 1'b1,
                    input integer gap = 6);
  integer n;
  r0 = nrep; on = 0;
  n = (nb < 0) ? 8 * pn : nb;
  for (int i = 0; i < lead; i++) begin @(negedge clk); rx_valid = 1; rx_bit = 0; end
  for (int i = 0; i < n; i++) begin @(negedge clk); rx_valid = 1; rx_bit = pb[i / 8][i % 8]; end
  for (int i = 0; i < trail; i++) begin @(negedge clk); rx_valid = 1; rx_bit = tv; end
  @(negedge clk); rx_valid = 0; rx_bit = 0;
  repeat (gap) @(negedge clk);
  pn = 0;
endtask
function automatic logic rep(input integer i, input logic [3:0] f, input logic [7:0] dt, input logic [15:0] wc,
                             input logic [15:0] fr, input logic [15:0] ln);
  rep = r_f[r0 + i] == f && r_dt[r0 + i] == dt && r_wc[r0 + i] == wc && r_fr[r0 + i] == fr && r_ln[r0 + i] == ln;
endfunction
function automatic logic delivered();
  logic ok;
  ok = (on == pw);
  for (int i = 0; i < 1024; i++) if (i < pw && ob[i] !== pb[p0 + i]) ok = 0;
  delivered = ok;
endfunction
logic [7:0] keep [0:1023];
integer allok;

initial begin
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && out_valid === 1'b0, "nothing out in reset");
  rst_n = 1;
  repeat (5) @(negedge clk);
  pb[0] = 8'h00; pn = 1; send(5, 8, 0);
  chk(nrep == 0 && on == 0, "a burst of HS-zeros only: no report");
  addpkt(8'h00, 16'd7); send();
  chk(nrep == r0 + 1 && rep(0, 4'h0, 8'h00, 16'd7, 16'd1, 16'd0), "FS with frame number 7");
  addpkt(8'h2A, 16'd16); send(13);
  chk(nrep == r0 + 1 && rep(0, 4'h0, 8'h2A, 16'd16, 16'd1, 16'd1) && delivered(), "RAW8 line of 16 after 13 lead-in zeros");
  addpkt(8'h9E, 16'd9); send(0, -1, 0);
  chk(rep(0, 4'h0, 8'h9E, 16'd9, 16'd1, 16'd2) && delivered(), "YUV422 on VC 2, no lead-in or trailer");
  addpkt(8'h2B, 16'd0); send();
  chk(rep(0, 4'h0, 8'h2B, 16'd0, 16'd1, 16'd3) && on == 0, "long packet with WC 0");
  allok = 1;
  for (int b = 0; b < 24; b++) begin
    addpkt(8'h24, 16'd5, 1, b); send();
    if (!(nrep == r0 + 1 && rep(0, 4'h8, 8'h24, 16'd5, 16'd1, 16'd4 + b) && delivered())) allok = 0;
  end
  chk(allok, "header bit error in each of the 24 positions: corrected, line counted");
  allok = 1;
  for (int b = 0; b < 6; b++) begin
    addpkt(8'h02, 16'd3, 2, b); send();
    if (!rep(0, 4'h8, 8'h02, 16'd3, 16'd1, 16'd27)) allok = 0;
  end
  chk(allok, "ECC bit errors: corrected");
  addpkt(8'h03, 16'd4, 3); send();
  chk(rep(0, 4'h0, 8'h03, 16'd4, 16'd1, 16'd27), "ECC bits 7:6 are ignored");
  addpkt(8'h2A, 16'd8, 4, 2); send();
  chk(nrep == r0 + 1 && rep(0, 4'h2, 8'h00, 16'd0, 16'd1, 16'd27) && on == 0, "two-bit header error: dropped");
  addpkt(8'h2A, 16'd8, 0, 0, 1); send();
  chk(rep(0, 4'h1, 8'h2A, 16'd8, 16'd1, 16'd27) && on == 8, "payload bit error: CRC error, line not counted");
  addpkt(8'h2A, 16'd8, 0, 0, 2); send();
  chk(rep(0, 4'h1, 8'h2A, 16'd8, 16'd1, 16'd27), "CRC bit error");
  addpkt(8'h2A, 16'd8); send(3, 8 * 2 + 3, 0);
  chk(nrep == r0 + 1 && rep(0, 4'h4, 8'h00, 16'd0, 16'd1, 16'd27), "burst cut in the header");
  addpkt(8'h2A, 16'd8); send(3, 8 * 5, 0);
  chk(rep(0, 4'h4, 8'h2A, 16'd8, 16'd1, 16'd27) && on == 0, "burst cut right after the ECC byte");
  addpkt(8'h2A, 16'd8, 1, 20); send(3, 8 * 9 + 5, 0);
  chk(rep(0, 4'hC, 8'h2A, 16'd8, 16'd1, 16'd27) && on == 4, "corrected header, burst cut in the payload");
  addpkt(8'h2A, 16'd8); send(3, 8 * 13 + 2, 0);
  chk(rep(0, 4'h4, 8'h2A, 16'd8, 16'd1, 16'd27), "burst cut in the CRC");
  addpkt(8'h2A, 16'd8); send(3, 8 * 14, 0);
  chk(rep(0, 4'h4, 8'h2A, 16'd8, 16'd1, 16'd27), "burst cut after the CRC low byte");
  addpkt(8'h02, 16'd0); addpkt(8'h2A, 16'd6); addpkt(8'h03, 16'd0); send();
  chk(nrep == r0 + 3 && rep(0, 4'h0, 8'h02, 16'd0, 16'd1, 16'd27) && rep(1, 4'h0, 8'h2A, 16'd6, 16'd1, 16'd28)
      && rep(2, 4'h0, 8'h03, 16'd0, 16'd1, 16'd28), "LS + line + LE in one burst");
  addpkt(8'h2A, 16'd6); pb[pn] = 8'h00; pn = pn + 1; addpkt(8'h2A, 16'd6); send();
  chk(nrep == r0 + 1 && rep(0, 4'h0, 8'h2A, 16'd6, 16'd1, 16'd29), "junk byte after a packet: rest of the burst ignored");
  addpkt(8'h2A, 16'd6); send(3, -1, 7, 1'b0);
  chk(nrep == r0 + 1, "trailer of zeros: no further report");
  addpkt(8'h2A, 16'd300); send();
  chk(rep(0, 4'h0, 8'h2A, 16'd300, 16'd1, 16'd31) && delivered(), "line of 300 bytes");
  addpkt(8'h01, 16'd7); send(3, -1, 4, 1'b1, 1);
  chk(rep(0, 4'h0, 8'h01, 16'd7, 16'd1, 16'd31), "FE");
  addpkt(8'h40, 16'd8); send(3, -1, 4, 1'b1, 1);
  chk(rep(0, 4'h0, 8'h40, 16'd8, 16'd2, 16'd0), "FS on VC 1 after a one-clock gap: frame 2, line count cleared");
  addpkt(8'h2A, 16'd8, 4, 2); addpkt(8'h2A, 16'd8); send();
  chk(nrep == r0 + 1 && r_f[r0] == 4'h2, "packet after a dropped header in the same burst is not taken");
  chk(both == 0, "no payload byte in the clock of a report");
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
