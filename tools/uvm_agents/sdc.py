# SD memory card device VIP: an SD card model (the recording card of an IP
# camera) with a host agent, 4-bit bus, the block length of SD_top.
#
# Agent -> DUT (host): sd_clk, the host's CMD drive cmd_m with cmd_m_oe, its
# DAT drive dat_m[3:0] with dat_m_oe. DUT -> agent (card): cmd_s / cmd_s_oe,
# dat_s[3:0] / dat_s_oe[3:0]. Undriven lines read 1 (pull-ups). Both sides
# change their outputs on the sd_clk falling edge and sample on the rising
# edge.
#
# tb/top_tb.sv sdc_model is the card, made to pair with SD_top in
# open-ip-portfolio (32-byte blocks, 4-bit data from the start):
#   CMD0 -> idle (no response). CMD8 in idle: R7 echoing VHS + check pattern
#   when VHS = 1, else no response. CMD55: R1 with APP_CMD; ACMD41 in idle /
#   ready: R3 with the OCR (0xFF8000 window), busy for POLLS calls, then
#   ready, CCS = HC & HCS -> ready. CMD2 in ready: R2 with the CID (its own
#   CRC7, CID[0] = 1) -> ident. CMD3 in ident / stby: R6 with RCA -> stby.
#   CMD7 with the RCA in stby / tran: R1 -> tran; another RCA deselects (tran
#   -> stby) without a response. CMD13 with the RCA: R1. CMD17 / CMD24 in
#   tran: R1, then a read block NAC clocks after the response (start 0000,
#   64 nibbles, a CRC16 per line, end 1111), or a write block from the host,
#   then the CRC status token on DAT0 two clocks after its end bit (010
#   accepted, 101 CRC / end bit error) and BUSY clocks of busy. A command
#   with a bad CRC7 / end / transmission bit gets no response and sets
#   COM_CRC_ERROR; a command not legal in the state gets none and sets
#   ILLEGAL_COMMAND; both show in the next R1 / R6 and are then cleared. R1
#   status: CURRENT_STATE when the command arrived in [12:9], READY_FOR_DATA,
#   APP_CMD. Responses start NCR clocks after the command's end bit. Blocks
#   are addressed by number (CCS = 1) or by byte address / 32; 16 blocks,
#   block b byte i = (16 b + i) ^ 0x3C after reset.
# In a SoC bench the card connects to SD_top's pins (cmd_m <= cmd, cmd_m_oe
# <= 1, dat_m <= dat, dat_m_oe <= 1, and cmd / dat driven by the card where
# its enables are set); the agent runs passive and its monitor records every
# command, response and block.

SDC_FUNCS = """
function automatic bit [6:0] sdc_crc7(bit [119:0] d, int n);   // over d[n-1:0], MSB first
  bit [6:0] c = 0;
  for (int i = n - 1; i >= 0; i--) begin
    bit fb = d[i] ^ c[6];
    c = {c[5:0], 1'b0};
    if (fb) c ^= 7'h09;
  end
  return c;
endfunction
function automatic bit [15:0] sdc_crc16(bit [15:0] c, bit b);
  bit fb = b ^ c[15];
  return {c[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
endfunction
function automatic bit [47:0] sdc_frame(bit [5:0] i, bit [31:0] a, bit tx = 1'b1);
  bit [39:0] b = {1'b0, tx, i, a};
  return {b, sdc_crc7({80'h0, b}, 40), 1'b1};
endfunction
function automatic bit [255:0] sdc_init_blk(int b);
  bit [255:0] v;
  for (int i = 0; i < 32; i++) v[255 - 8 * i -: 8] = 8'((16 * b + i) ^ 8'h3C);
  return v;
endfunction
localparam bit [119:0] SDC_CID_BODY = 120'h1D4F565344433110123456780016A0;
"""

# the card, step by step: shared by the scoreboard (class code, blocking)
SPEC = dict(
    vip="SD_Card-UVM-VIP", p="sdc", P="SDC", dir="sdc", family="Memory",
    desc="SD memory card device VIP: card model with CMD0 / 8 / 55 / ACMD41 / 2 / 3 / 7 / 13 / 17 / 24, R1 / R2 / "
         "R3 / R6 / R7 responses with CRC7, 4-bit data blocks with per-line CRC16, CRC status token and busy, "
         "COM_CRC_ERROR / ILLEGAL_COMMAND reporting; SD host agent and bus monitor (SD_top pins).",
    about="""
An IP camera records to an SD card through the SoC's SD host. The VIP's DUT
model is that card, made to pair with SD_top in open-ip-portfolio (the same
32-byte blocks and 4-bit bus), so a SoC bench can hang it on the host's
pins. The agent is a host that walks the card through identification
(CMD0, CMD8 with good and bad voltage, CMD55 / ACMD41 polls with and
without HCS, CMD2, CMD3, CMD7) and data transfer (CMD24 with good and
corrupted block CRCs, CMD17 read-back, CMD13), and sends commands with a
bad CRC7, commands that are illegal in the state, CMD7 to another RCA and
to RCA 0, and CMD0 in the middle of everything. The scoreboard runs its own
copy of the card on the monitored host bits and predicts the card's CMD and
DAT drive at every sd_clk rising edge: response timing (NCR, NAC), every
response bit and CRC7, the CID, the RCA, read data and CRC16s, the CRC
status token and the busy time.""",
    defs=SDC_FUNCS,
    timeout=40000,
    cfg="""int unsigned half = 2;     // clocks per sd_clk half period
int unsigned gap  = 16;    // clocks with sd_clk stopped between items""",
    ports=[
        ("in", "logic", "sd_clk"), ("in", "logic", "cmd_m"), ("in", "logic", "cmd_m_oe"),
        ("in", "logic [3:0]", "dat_m"), ("in", "logic", "dat_m_oe"),
        ("out", "logic", "cmd_s"), ("out", "logic", "cmd_s_oe"),
        ("out", "logic [3:0]", "dat_s"), ("out", "logic [3:0]", "dat_s_oe"),
    ],
    fields=[
        ("bit [6:0]", "mo", "req", "q"),        # {cmd_m_oe, cmd_m, dat_m_oe, dat_m} per sd_clk rise (masked)
        ("bit [9:0]", "so", "rsp", "q"),        # {cmd_s_oe, cmd_s, dat_s_oe, dat_s} per sd_clk rise (masked)
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [3:0]", "blk", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [5:0]", "idx", "info"),
        ("bit [31:0]", "arg", "info"),
        ("bit", "got", "info"),
    ],
    tr_functions="""
// kind: 0 CMD0, 1 CMD8 (VHS 1), 2 CMD8 (VHS 2), 3 CMD55, 4 ACMD41 with HCS,
// 5 ACMD41 without HCS, 6 CMD2, 7 CMD3, 8 CMD7 (RCA), 9 CMD7 (other RCA),
// 10 CMD13, 11 CMD24, 12 CMD24 with a bad CRC16, 13 CMD17, 14 CMD13 with a
// bad CRC7, 15 CMD6 (illegal), 16 CMD7 (RCA 0), 17 CMD13 (other RCA),
// 18-31 CMD24 / CMD17 / CMD13 / CMD55 mix
function void set(int k, int b = 0, bit [31:0] s = 32'h1); kind = k; blk = b; seed = s; endfunction
function bit [47:0] cmd(bit [15:0] rca, bit hc);
  bit [31:0] ba = hc ? {28'h0, blk} : {23'h0, blk, 5'h0};
  int k = kind;
  if (k >= 18) k = (k % 4 == 0) ? 11 : (k % 4 == 1) ? 13 : (k % 4 == 2) ? 10 : 3;
  case (k)
    0: begin idx = 0; arg = 0; end
    1: begin idx = 8; arg = 32'h0000_01AA; end
    2: begin idx = 8; arg = 32'h0000_02AA; end
    3: begin idx = 55; arg = {rca, 16'h0}; end
    4: begin idx = 41; arg = 32'h40FF_8000; end
    5: begin idx = 41; arg = 32'h00FF_8000; end
    6: begin idx = 2; arg = 0; end
    7: begin idx = 3; arg = 0; end
    8: begin idx = 7; arg = {rca, 16'h0}; end
    9: begin idx = 7; arg = {rca ^ 16'h0101, 16'h0}; end
    10, 14: begin idx = 13; arg = {rca, 16'h0}; end
    11, 12: begin idx = 24; arg = ba; end
    13: begin idx = 17; arg = ba; end
    15: begin idx = 6; arg = 0; end
    16: begin idx = 7; arg = 0; end
    default: begin idx = 13; arg = {rca ^ 16'h8000, 16'h0}; end
  endcase
  if (k == 14) return sdc_frame(idx, arg) ^ 48'h4;
  return sdc_frame(idx, arg);
endfunction
function bit [255:0] wdata();
  bit [31:0] x = seed | 1;
  bit [255:0] v;
  for (int i = 0; i < 8; i++) begin x ^= x << 13; x ^= x >> 17; x ^= x << 5; v[32 * i +: 32] = x; end
  return v;
endfunction
function bit bad_crc(); return kind == 12; endfunction
""",
    drv_rsp=False,
    drv_members="""bit [15:0]      rca = 0;
bit             hc = 0;
sdc_transaction cur;""",
    drv_tasks="""
// one sd_clk period: outputs at the falling edge, the lines at the rising edge
task automatic clk1(bit co, bit c, bit doe, bit [3:0] d, output bit cl, output bit [3:0] dl);
  vif.drv_cb.sd_clk   <= 1'b0;
  vif.drv_cb.cmd_m_oe <= co; vif.drv_cb.cmd_m <= c;
  vif.drv_cb.dat_m_oe <= doe; vif.drv_cb.dat_m <= d;
  repeat (cfg.half) @(vif.drv_cb);
  vif.drv_cb.sd_clk <= 1'b1;
  cl = co ? c : (vif.drv_cb.cmd_s_oe ? vif.drv_cb.cmd_s : 1'b1);
  for (int i = 0; i < 4; i++) dl[i] = doe ? d[i] : (vif.drv_cb.dat_s_oe[i] ? vif.drv_cb.dat_s[i] : 1'b1);
  cur.mo.push_back({co, c & co, doe, d & {4{doe}}});
  repeat (cfg.half) @(vif.drv_cb);
endtask
task automatic idle1(output bit cl, output bit [3:0] dl);
  clk1(1'b0, 1'b0, 1'b0, 4'h0, cl, dl);
endtask
""",
    drv_desc="one command per item with sd_clk running: 4 idle clocks, the 48-bit command, a response hunt of up to 64 clocks and the response; for CMD24 the block (start, 64 nibbles, CRC16s, end), the CRC status token and the busy wait; for CMD17 the block hunt and the block; then 8 idle clocks and sd_clk stopped for cfg.gap clocks",
    drv_idle="""
vif.drv_cb.sd_clk   <= 1'b1;
vif.drv_cb.cmd_m    <= 1'b0;
vif.drv_cb.cmd_m_oe <= 1'b0;
vif.drv_cb.dat_m    <= 4'h0;
vif.drv_cb.dat_m_oe <= 1'b0;
""",
    drv_item="""
bit cl;
bit [3:0] dl;
bit [47:0] f;
bit [135:0] r = 0;
int k;
cur = t;
t.mo.delete();
f = t.cmd(rca, hc);
t.got = 0;
@(vif.drv_cb);
repeat (4) idle1(cl, dl);
for (int i = 47; i >= 0; i--) clk1(1'b1, f[i], 1'b0, 4'h0, cl, dl);
k = 0;
while (k < 64 && !t.got) begin idle1(cl, dl); if (!cl) t.got = 1; k++; end
if (t.got) begin
  int len = (t.idx == 2) ? 136 : 48;
  for (int i = 1; i < len; i++) begin idle1(cl, dl); r = {r[134:0], cl}; end
  if (t.idx == 3) rca = r[39:24];
  if (t.idx == 41) hc = r[38];
  if (t.idx == 0) begin rca = 0; hc = 0; end
end
if (t.idx == 0) begin rca = 0; hc = 0; end
if (t.got && t.idx == 24) begin
  bit [255:0] w = t.wdata();
  bit [15:0] c [4] = '{0, 0, 0, 0};
  idle1(cl, dl); idle1(cl, dl);
  clk1(1'b0, 1'b0, 1'b1, 4'hF, cl, dl);
  clk1(1'b0, 1'b0, 1'b1, 4'h0, cl, dl);
  for (int n = 0; n < 64; n++) begin
    bit [3:0] v = w[255 - 4 * n -: 4];
    for (int l = 0; l < 4; l++) c[l] = sdc_crc16(c[l], v[l]);
    clk1(1'b0, 1'b0, 1'b1, v, cl, dl);
  end
  if (t.bad_crc()) c[t.seed[1:0]][t.seed[5:2]] ^= 1'b1;
  for (int n = 15; n >= 0; n--) clk1(1'b0, 1'b0, 1'b1, {c[3][n], c[2][n], c[1][n], c[0][n]}, cl, dl);
  clk1(1'b0, 1'b0, 1'b1, 4'hF, cl, dl);
  k = 0;
  do begin idle1(cl, dl); k++; end while (dl[0] && k < 64);
  if (!dl[0]) begin
    repeat (4) idle1(cl, dl);
    k = 0;
    do begin idle1(cl, dl); k++; end while (!dl[0] && k < 256);
  end
end
if (t.got && t.idx == 17) begin
  k = 0;
  do begin idle1(cl, dl); k++; end while (dl != 4'h0 && k < 64);
  if (dl == 4'h0) repeat (64 + 16 + 1) idle1(cl, dl);
end
repeat (8) idle1(cl, dl);
repeat (cfg.gap) @(vif.drv_cb);
""",
    mon_desc="host and card drive (masked by their enables) at every sd_clk rising edge; sd_clk stopped for more than half of cfg.gap clocks ends the item",
    mon_run="""
forever begin
  sdc_transaction t;
  bit pc;
  int q = 0;
  pc = vif.mon_cb.sd_clk;
  @(vif.mon_cb);
  while (!(pc === 1'b0 && vif.mon_cb.sd_clk === 1'b1)) begin pc = vif.mon_cb.sd_clk; @(vif.mon_cb); end
  t = sdc_transaction::type_id::create("t");
  forever begin
    if (pc === 1'b0 && vif.mon_cb.sd_clk === 1'b1) begin
      t.mo.push_back({vif.mon_cb.cmd_m_oe, vif.mon_cb.cmd_m & vif.mon_cb.cmd_m_oe, vif.mon_cb.dat_m_oe,
                      vif.mon_cb.dat_m & {4{vif.mon_cb.dat_m_oe}}});
      t.so.push_back({vif.mon_cb.cmd_s_oe, vif.mon_cb.cmd_s & vif.mon_cb.cmd_s_oe, vif.mon_cb.dat_s_oe,
                      vif.mon_cb.dat_s & vif.mon_cb.dat_s_oe});
      q = 0;
    end else if (++q > cfg.gap / 2) break;
    pc = vif.mon_cb.sd_clk;
    @(vif.mon_cb);
  end
  publish(t);
end
""",
    sb_members="""// the card (scoreboard copy), kept across items
bit [255:0] mem [16];
bit         minit = 0;
int         cst = 0, polls = 0, dm = 0, rdd = 0, tokd = 0, tokn = 0, busyn = 0, dcnt = 0;
bit         app = 0, crc_e = 0, ill = 0, ccs = 0;
bit [15:0]  rca = 0;
int         rxc = 0, txd = 0, txn = 0;
bit [47:0]  rxs = 0;
bit [135:0] txs = 0;
bit [3:0]   blk = 0;
bit [255:0] buff = 0;
bit [15:0]  c [4], rc [4];
bit [4:0]   tok = 0;
bit         o_cmd = 0, o_cmd_oe = 0;
bit [3:0]   o_dat = 0, o_dat_oe = 0;
localparam int NCR = 2, NAC = 2, BUSY = 4, POLLS = 1;
localparam bit HC = 1;
localparam bit [15:0] RCA = 16'h1234;

function void send(bit [135:0] fr, int n);
  txs = fr; txn = n; txd = NCR - 1;
endfunction
function bit [31:0] r1st(int st, bit appc);
  return {8'h00, crc_e, ill, 9'h000, 4'(st), 1'b1, 2'b00, appc, 5'h00};
endfunction
function void frame(bit [47:0] f);
  bit [5:0] i = f[45:40];
  bit [31:0] a = f[39:8];
  int st = cst;
  bit wa = app;
  if (sdc_crc7({80'h0, f[47:8]}, 40) != f[7:1] || !f[0] || !f[46]) begin crc_e = 1; return; end
  app = 0;
  if (i == 0) begin cst = 0; polls = 0; ccs = 0; rca = 0; dm = 0; end
  else if (i == 8 && cst == 0) begin
    if (a[11:8] == 4'h1) send({sdc_frame(6'd8, {20'h0, a[11:0]}, 1'b0), 88'h0}, 48);
  end else if (i == 55 && cst != 2) begin
    app = 1; send({sdc_frame(6'd55, r1st(st, 1'b1), 1'b0), 88'h0}, 48); crc_e = 0; ill = 0;
  end else if (i == 41 && wa && (cst == 0 || cst == 1)) begin
    bit rdy = polls >= POLLS;
    if (polls != 15) polls++;
    if (rdy) begin cst = 1; ccs = HC && a[30]; end
    send({2'b00, 6'h3F, rdy, rdy && HC && a[30], 6'h00, 24'hFF8000, 8'hFF, 88'h0}, 48);
  end else if (i == 2 && cst == 1) begin
    bit [127:0] cid = {SDC_CID_BODY, sdc_crc7(SDC_CID_BODY, 120), 1'b1};
    cst = 2; send({2'b00, 6'h3F, cid[127:1], 1'b1}, 136);
  end else if (i == 3 && (cst == 2 || cst == 3)) begin
    cst = 3; rca = RCA;
    send({sdc_frame(6'd3, {RCA, crc_e, ill, 1'b0, 4'(st), 1'b1, 2'b00, 1'b0, 5'h00}, 1'b0), 88'h0}, 48);
    crc_e = 0; ill = 0;
  end else if (i == 7 && (cst == 3 || cst == 4)) begin
    if (a[31:16] == rca && rca != 0) begin
      cst = 4; send({sdc_frame(6'd7, r1st(st, 1'b0), 1'b0), 88'h0}, 48); crc_e = 0; ill = 0;
    end else if (cst == 4) cst = 3;
  end else if (i == 13 && (cst == 3 || cst == 4)) begin
    if (a[31:16] == rca) begin send({sdc_frame(6'd13, r1st(st, 1'b0), 1'b0), 88'h0}, 48); crc_e = 0; ill = 0; end
  end else if ((i == 17 || i == 24) && cst == 4) begin
    send({sdc_frame(i, r1st(st, 1'b0), 1'b0), 88'h0}, 48); crc_e = 0; ill = 0;
    blk = ccs ? a[3:0] : a[8:5];
    if (i == 17) begin dm = 7; buff = mem[blk]; end
    else dm = 1;
  end else ill = 1;
endfunction
""",
    predict="""
if (!minit) begin for (int b = 0; b < 16; b++) mem[b] = sdc_init_blk(b); minit = 1; end
t.so.delete();
foreach (t.mo[i]) begin
  bit cl;
  bit [3:0] dl;
  t.so.push_back({o_cmd_oe, o_cmd & o_cmd_oe, o_dat_oe, o_dat & o_dat_oe});
  cl = t.mo[i][6] ? t.mo[i][5] : (o_cmd_oe ? o_cmd : 1'b1);
  for (int l = 0; l < 4; l++) dl[l] = t.mo[i][4] ? t.mo[i][l] : (o_dat_oe[l] ? o_dat[l] : 1'b1);
  // command receiver (not while a response goes out)
  if (txd == 0 && txn == 0) begin
    if (rxc == 0) begin if (!cl) begin rxc = 1; rxs = 0; end end
    else begin
      rxs = {rxs[46:0], cl}; rxc++;
      if (rxc == 48) begin rxc = 0; frame(rxs); end
    end
  end
  // write block receiver
  case (dm)
    1: if (dl == 4'h0) begin dm = 2; dcnt = 0; c = '{0, 0, 0, 0}; end
    2: begin
         buff = {buff[251:0], dl};
         for (int l = 0; l < 4; l++) c[l] = sdc_crc16(c[l], dl[l]);
         if (++dcnt == 64) begin dm = 3; dcnt = 0; rc = '{0, 0, 0, 0}; end
       end
    3: begin
         for (int l = 0; l < 4; l++) rc[l] = {rc[l][14:0], dl[l]};
         if (++dcnt == 16) dm = 4;
       end
    4: begin
         bit good = dl == 4'hF && rc[0] == c[0] && rc[1] == c[1] && rc[2] == c[2] && rc[3] == c[3];
         if (good) mem[blk] = buff;
         tok = good ? 5'b0_010_1 : 5'b0_101_1;
         dm = 5; tokd = 1; tokn = 5; busyn = good ? BUSY : 0;
       end
    default: ;
  endcase
  // outputs for the next period
  if (txd > 0) begin txd--; o_cmd_oe = 0; end
  else if (txn > 0) begin
    o_cmd_oe = 1; o_cmd = txs[135]; txs = txs << 1; txn--;
    if (txn == 0 && dm == 7) begin dm = 8; rdd = NAC; end
  end else o_cmd_oe = 0;
  case (dm)
    5: if (tokd > 0) begin tokd--; o_dat_oe = 0; end
       else if (tokn > 0) begin o_dat_oe = 4'b0001; o_dat[0] = tok[4]; tok = tok << 1; tokn--; end
       else if (busyn > 0) begin o_dat_oe = 4'b0001; o_dat[0] = 1'b0; busyn--; end
       else begin o_dat_oe = 0; dm = 0; end
    8: if (rdd > 0) begin rdd--; o_dat_oe = 0; end
       else begin o_dat_oe = 4'hF; o_dat = 4'h0; dm = 9; dcnt = 0; c = '{0, 0, 0, 0}; end
    9: begin
         bit [3:0] v = buff[255 - 4 * dcnt -: 4];
         o_dat_oe = 4'hF; o_dat = v;
         for (int l = 0; l < 4; l++) c[l] = sdc_crc16(c[l], v[l]);
         if (++dcnt == 64) begin dm = 10; dcnt = 0; end
       end
    10: begin
          o_dat_oe = 4'hF; o_dat = {c[3][15], c[2][15], c[1][15], c[0][15]};
          for (int l = 0; l < 4; l++) c[l] = c[l] << 1;
          if (++dcnt == 16) dm = 11;
        end
    11: begin o_dat_oe = 4'hF; o_dat = 4'hF; dm = 12; end
    12: begin o_dat_oe = 0; dm = 0; end
    default: o_dat_oe = 0;
  endcase
end
""",
    checks="""
foreach (t.so[i]) begin
  if (t.so[i][9] && t.mo[i][6]) fail(t, "host and card drive CMD together");
  if (t.so[i][7:4] != 0 && t.mo[i][4]) fail(t, "host and card drive DAT together");
end
""",
    coverage="""
cp_idx  : coverpoint tr.idx { bins c0 = {0}; bins c2 = {2}; bins c3 = {3}; bins c7 = {7}; bins c8 = {8}; bins c13 = {13};
                              bins c17 = {17}; bins c24 = {24}; bins c41 = {41}; bins c55 = {55}; bins other = {6}; }
cp_got  : coverpoint tr.got;
cp_len  : coverpoint tr.mo.size() { bins cmd = {[100:200]}; bins r2 = {[201:260]}; bins blk = {[261:500]}; }
""",
    directed="""
// identification, both addressing modes, transfers, every error path, reset in transfer state
t = item(); t.set(13); send(t);            // illegal in idle
t = item(); t.set(0); send(t);
t = item(); t.set(2); send(t);             // VHS 2: no response
t = item(); t.set(1); send(t);
t = item(); t.set(4); send(t);             // ACMD41 without CMD55: illegal
t = item(); t.set(3); send(t);             // reports ILLEGAL_COMMAND
t = item(); t.set(4); send(t);             // busy
t = item(); t.set(3); send(t);
t = item(); t.set(4); send(t);             // ready, CCS 1
t = item(); t.set(6); send(t);
t = item(); t.set(7); send(t);
t = item(); t.set(14); send(t);            // bad CRC7
t = item(); t.set(10); send(t);            // reports COM_CRC_ERROR
t = item(); t.set(8); send(t);
for (int b = 0; b < 4; b++) begin
  t = item(); t.set(13, b); send(t);
  t = item(); t.set(11, b, 32'h1000 + b); send(t);
  t = item(); t.set(13, b); send(t);
end
t = item(); t.set(12, 5, 32'h77); send(t);
t = item(); t.set(13, 5); send(t);
t = item(); t.set(15); send(t);
t = item(); t.set(10); send(t);
t = item(); t.set(17); send(t);
t = item(); t.set(9); send(t);             // deselect
t = item(); t.set(13); send(t);            // illegal in stby
t = item(); t.set(8); send(t);
t = item(); t.set(16); send(t);
t = item(); t.set(8); send(t);
t = item(); t.set(0); send(t);             // reset from transfer state
t = item(); t.set(1); send(t);
t = item(); t.set(3); send(t);
t = item(); t.set(5); send(t);             // no HCS: byte addressing
t = item(); t.set(3); send(t);
t = item(); t.set(5); send(t);
t = item(); t.set(6); send(t);
t = item(); t.set(7); send(t);
t = item(); t.set(7); send(t);             // CMD3 again in stby
t = item(); t.set(8); send(t);
t = item(); t.set(11, 9, 32'h55); send(t);
t = item(); t.set(13, 9); send(t);
t = item(); t.set(13, 1); send(t);
""",
    drain_ns=4000,
    model="""
module sdc_model #(
  parameter int          NCR   = 2,
  parameter int          NAC   = 2,
  parameter int          BUSY  = 4,
  parameter int          POLLS = 1,
  parameter bit          HC    = 1'b1,
  parameter logic [15:0] RCA   = 16'h1234
) (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       sd_clk,
  input  logic       cmd_m,
  input  logic       cmd_m_oe,
  input  logic [3:0] dat_m,
  input  logic       dat_m_oe,
  output logic       cmd_s,
  output logic       cmd_s_oe,
  output logic [3:0] dat_s,
  output logic [3:0] dat_s_oe
);
  localparam logic [119:0] CID_BODY = 120'h1D4F565344433110123456780016A0;
  localparam logic [3:0] D_NONE = 4'd0, D_WWAIT = 4'd1, D_WDATA = 4'd2, D_WCRC = 4'd3, D_WEND = 4'd4,
                         D_TOK = 4'd5, D_RPEND = 4'd7, D_RWAIT = 4'd8, D_RDATA = 4'd9, D_RCRC = 4'd10,
                         D_REND = 4'd11, D_RREL = 4'd12;
  function automatic logic [6:0] crc7(input logic [119:0] d, input integer n);
    logic [6:0] c;
    logic fb;
    c = 7'h00;
    for (int i = 119; i >= 0; i--) if (i < n) begin
      fb = d[i] ^ c[6];
      c = {c[5:0], 1'b0};
      if (fb) c = c ^ 7'h09;
    end
    crc7 = c;
  endfunction
  function automatic logic [15:0] crc16(input logic [15:0] c, input logic b);
    crc16 = {c[14:0], 1'b0} ^ ((b ^ c[15]) ? 16'h1021 : 16'h0000);
  endfunction
  function automatic logic [47:0] rframe(input logic [5:0] i, input logic [31:0] a);
    logic [39:0] b;
    b = {2'b00, i, a};
    rframe = {b, crc7({80'h0, b}, 40), 1'b1};
  endfunction

  logic [255:0] mem [0:15];
  logic [2:0]   cst;
  logic [3:0]   polls, dm, blk;
  logic         app, crc_e, ill, ccs;
  logic [15:0]  rca;
  logic [5:0]   rxc;
  logic [47:0]  rxs;
  logic [7:0]   txn;
  logic [6:0]   txd;
  logic [135:0] txs;
  logic [255:0] buff;
  logic [15:0]  c0, c1, c2, c3, r0, r1, r2, r3;
  logic [6:0]   dcnt;
  logic [6:0]   rdd, tokd;
  logic [2:0]   tokn;
  logic [4:0]   tok;
  logic [7:0]   busyn;
  logic         n_cmd, n_cmd_oe;
  logic [3:0]   n_dat, n_dat_oe;
  wire          cl = cmd_m_oe ? cmd_m : (cmd_s_oe ? cmd_s : 1'b1);
  wire  [3:0]   dl = dat_m_oe ? dat_m : ((dat_s_oe & dat_s) | ~dat_s_oe);
  wire          _unused = &{1'b0, clk};

  // rising sd_clk: receive, run the card, decide the next outputs
  always_ff @(posedge sd_clk or negedge rst_n) begin
    if (!rst_n) begin
      cst <= '0; polls <= '0; dm <= D_NONE; blk <= '0; app <= 1'b0; crc_e <= 1'b0; ill <= 1'b0; ccs <= 1'b0;
      rca <= '0; rxc <= '0; rxs <= '0; txn <= '0; txd <= '0; txs <= '0; buff <= '0;
      c0 <= '0; c1 <= '0; c2 <= '0; c3 <= '0; r0 <= '0; r1 <= '0; r2 <= '0; r3 <= '0;
      dcnt <= '0; rdd <= '0; tokd <= '0; tokn <= '0; tok <= '0; busyn <= '0;
      n_cmd <= 1'b0; n_cmd_oe <= 1'b0; n_dat <= 4'h0; n_dat_oe <= 4'h0;
      for (int b = 0; b < 16; b++)
        for (int i = 0; i < 32; i++) mem[b][255 - 8 * i -: 8] <= 8'((16 * b + i) ^ 8'h3C);
    end else begin : step
      logic [2:0]   v_cst;
      logic [3:0]   v_polls, v_dm, v_blk;
      logic         v_app, v_crc_e, v_ill, v_ccs;
      logic [15:0]  v_rca;
      logic [5:0]   v_rxc;
      logic [47:0]  v_rxs, f;
      logic [7:0]   v_txn;
      logic [6:0]   v_txd;
      logic [135:0] v_txs;
      logic [255:0] v_buff;
      logic [15:0]  v0, v1, v2, v3;
      logic [6:0]   v_dcnt, v_rdd, v_tokd;
      logic [2:0]   v_tokn;
      logic [4:0]   v_tok;
      logic [7:0]   v_busyn;
      logic [3:0]   nib;
      logic         go, good, wa, rdy;
      logic [2:0]   st;
      logic [5:0]   i;
      logic [31:0]  a;
      logic [127:0] cid;
      v_cst = cst; v_polls = polls; v_dm = dm; v_blk = blk; v_app = app; v_crc_e = crc_e; v_ill = ill;
      v_ccs = ccs; v_rca = rca; v_rxc = rxc; v_rxs = rxs; v_txn = txn; v_txd = txd; v_txs = txs;
      v_buff = buff; v0 = c0; v1 = c1; v2 = c2; v3 = c3; v_dcnt = dcnt; v_rdd = rdd; v_tokd = tokd;
      v_tokn = tokn; v_tok = tok; v_busyn = busyn;
      go = 1'b0; f = '0;
      // command receiver
      if (v_txd == 0 && v_txn == 0) begin
        if (v_rxc == 0) begin if (!cl) begin v_rxc = 6'd1; v_rxs = '0; end end
        else begin
          v_rxs = {v_rxs[46:0], cl};
          v_rxc = v_rxc + 6'd1;
          if (v_rxc == 6'd48) begin v_rxc = '0; go = 1'b1; f = v_rxs; end
        end
      end
      if (go) begin
        i = f[45:40]; a = f[39:8]; st = v_cst; wa = v_app;
        if (crc7({80'h0, f[47:8]}, 40) != f[7:1] || !f[0] || !f[46]) v_crc_e = 1'b1;
        else begin
          v_app = 1'b0;
          if (i == 6'd0) begin v_cst = 3'd0; v_polls = '0; v_ccs = 1'b0; v_rca = '0; v_dm = D_NONE; end
          else if (i == 6'd8 && v_cst == 3'd0) begin
            if (a[11:8] == 4'h1) begin v_txs = {rframe(6'd8, {20'h0, a[11:0]}), 88'h0}; v_txn = 8'd48; v_txd = 7'(NCR - 1); end
          end else if (i == 6'd55 && v_cst != 3'd2) begin
            v_app = 1'b1;
            v_txs = {rframe(6'd55, {8'h00, v_crc_e, v_ill, 9'h000, 1'b0, st, 1'b1, 2'b00, 1'b1, 5'h00}), 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
          end else if (i == 6'd41 && wa && (v_cst == 3'd0 || v_cst == 3'd1)) begin
            rdy = v_polls >= 4'(POLLS);
            if (v_polls != 4'd15) v_polls = v_polls + 4'd1;
            if (rdy) begin v_cst = 3'd1; v_ccs = HC && a[30]; end
            v_txs = {2'b00, 6'h3F, rdy, rdy && HC && a[30], 6'h00, 24'hFF8000, 8'hFF, 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1);
          end else if (i == 6'd2 && v_cst == 3'd1) begin
            cid = {CID_BODY, crc7(CID_BODY, 120), 1'b1};
            v_cst = 3'd2; v_txs = {2'b00, 6'h3F, cid[127:1], 1'b1}; v_txn = 8'd136; v_txd = 7'(NCR - 1);
          end else if (i == 6'd3 && (v_cst == 3'd2 || v_cst == 3'd3)) begin
            v_cst = 3'd3; v_rca = RCA;
            v_txs = {rframe(6'd3, {RCA, v_crc_e, v_ill, 1'b0, 1'b0, st, 1'b1, 2'b00, 1'b0, 5'h00}), 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
          end else if (i == 6'd7 && (v_cst == 3'd3 || v_cst == 3'd4)) begin
            if (a[31:16] == v_rca && v_rca != 16'h0) begin
              v_cst = 3'd4;
              v_txs = {rframe(6'd7, {8'h00, v_crc_e, v_ill, 9'h000, 1'b0, st, 1'b1, 2'b00, 1'b0, 5'h00}), 88'h0};
              v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
            end else if (v_cst == 3'd4) v_cst = 3'd3;
          end else if (i == 6'd13 && (v_cst == 3'd3 || v_cst == 3'd4)) begin
            if (a[31:16] == v_rca) begin
              v_txs = {rframe(6'd13, {8'h00, v_crc_e, v_ill, 9'h000, 1'b0, st, 1'b1, 2'b00, 1'b0, 5'h00}), 88'h0};
              v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
            end
          end else if ((i == 6'd17 || i == 6'd24) && v_cst == 3'd4) begin
            v_txs = {rframe(i, {8'h00, v_crc_e, v_ill, 9'h000, 1'b0, st, 1'b1, 2'b00, 1'b0, 5'h00}), 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
            v_blk = v_ccs ? a[3:0] : a[8:5];
            if (i == 6'd17) begin v_dm = D_RPEND; v_buff = mem[v_blk]; end
            else v_dm = D_WWAIT;
          end else v_ill = 1'b1;
        end
      end
      // write block receiver
      case (v_dm)
        D_WWAIT: if (dl == 4'h0) begin v_dm = D_WDATA; v_dcnt = '0; v0 = '0; v1 = '0; v2 = '0; v3 = '0; end
        D_WDATA: begin
          v_buff = {v_buff[251:0], dl};
          v0 = crc16(v0, dl[0]); v1 = crc16(v1, dl[1]); v2 = crc16(v2, dl[2]); v3 = crc16(v3, dl[3]);
          v_dcnt = v_dcnt + 7'd1;
          if (v_dcnt == 7'd64) begin v_dm = D_WCRC; v_dcnt = '0; r0 <= '0; r1 <= '0; r2 <= '0; r3 <= '0; end
        end
        D_WCRC: begin
          r0 <= {r0[14:0], dl[0]}; r1 <= {r1[14:0], dl[1]}; r2 <= {r2[14:0], dl[2]}; r3 <= {r3[14:0], dl[3]};
          v_dcnt = v_dcnt + 7'd1;
          if (v_dcnt == 7'd16) v_dm = D_WEND;
        end
        D_WEND: begin
          good = dl == 4'hF && r0 == v0 && r1 == v1 && r2 == v2 && r3 == v3;
          if (good) mem[v_blk] <= v_buff;
          v_tok = good ? 5'b0_010_1 : 5'b0_101_1;
          v_dm = D_TOK; v_tokd = 7'd1; v_tokn = 3'd5; v_busyn = good ? 8'(BUSY) : 8'd0;
        end
        default: ;
      endcase
      // outputs for the next period
      if (v_txd != 0) begin v_txd = v_txd - 7'd1; n_cmd_oe <= 1'b0; end
      else if (v_txn != 0) begin
        n_cmd_oe <= 1'b1; n_cmd <= v_txs[135]; v_txs = v_txs << 1; v_txn = v_txn - 8'd1;
        if (v_txn == 0 && v_dm == D_RPEND) begin v_dm = D_RWAIT; v_rdd = 7'(NAC); end
      end else n_cmd_oe <= 1'b0;
      case (v_dm)
        D_TOK:
          if (v_tokd != 0) begin v_tokd = v_tokd - 7'd1; n_dat_oe <= 4'h0; end
          else if (v_tokn != 0) begin n_dat_oe <= 4'b0001; n_dat <= {3'b000, v_tok[4]}; v_tok = v_tok << 1; v_tokn = v_tokn - 3'd1; end
          else if (v_busyn != 0) begin n_dat_oe <= 4'b0001; n_dat <= 4'h0; v_busyn = v_busyn - 8'd1; end
          else begin n_dat_oe <= 4'h0; v_dm = D_NONE; end
        D_RWAIT:
          if (v_rdd != 0) begin v_rdd = v_rdd - 7'd1; n_dat_oe <= 4'h0; end
          else begin n_dat_oe <= 4'hF; n_dat <= 4'h0; v_dm = D_RDATA; v_dcnt = '0; v0 = '0; v1 = '0; v2 = '0; v3 = '0; end
        D_RDATA: begin
          nib = v_buff[255 - 4 * v_dcnt -: 4];
          n_dat_oe <= 4'hF; n_dat <= nib;
          v0 = crc16(v0, nib[0]); v1 = crc16(v1, nib[1]); v2 = crc16(v2, nib[2]); v3 = crc16(v3, nib[3]);
          v_dcnt = v_dcnt + 7'd1;
          if (v_dcnt == 7'd64) begin v_dm = D_RCRC; v_dcnt = '0; end
        end
        D_RCRC: begin
          n_dat_oe <= 4'hF; n_dat <= {v3[15], v2[15], v1[15], v0[15]};
          v0 = v0 << 1; v1 = v1 << 1; v2 = v2 << 1; v3 = v3 << 1;
          v_dcnt = v_dcnt + 7'd1;
          if (v_dcnt == 7'd16) v_dm = D_REND;
        end
        D_REND: begin n_dat_oe <= 4'hF; n_dat <= 4'hF; v_dm = D_RREL; end
        D_RREL: begin n_dat_oe <= 4'h0; v_dm = D_NONE; end
        default: n_dat_oe <= 4'h0;
      endcase
      cst <= v_cst; polls <= v_polls; dm <= v_dm; blk <= v_blk; app <= v_app; crc_e <= v_crc_e; ill <= v_ill;
      ccs <= v_ccs; rca <= v_rca; rxc <= v_rxc; rxs <= v_rxs; txn <= v_txn; txd <= v_txd; txs <= v_txs;
      buff <= v_buff; c0 <= v0; c1 <= v1; c2 <= v2; c3 <= v3; dcnt <= v_dcnt; rdd <= v_rdd; tokd <= v_tokd;
      tokn <= v_tokn; tok <= v_tok; busyn <= v_busyn;
    end
  end

  // falling sd_clk: the outputs change
  always_ff @(negedge sd_clk or negedge rst_n) begin
    if (!rst_n) begin
      cmd_s <= 1'b0; cmd_s_oe <= 1'b0; dat_s <= 4'h0; dat_s_oe <= 4'h0;
    end else begin
      cmd_s <= n_cmd; cmd_s_oe <= n_cmd_oe; dat_s <= n_dat; dat_s_oe <= n_dat_oe;
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({sd_clk, cmd_m_oe, dat_m_oe, cmd_s_oe, dat_s_oe}))
  else $error("SDC: X on sd_clk or an enable");
assert property (@(posedge clk) disable iff (!rst_n) !(cmd_m_oe && cmd_s_oe))
  else $error("SDC: host and card drive CMD together");
assert property (@(posedge clk) disable iff (!rst_n) !(dat_m_oe && dat_s_oe != 4'h0))
  else $error("SDC: host and card drive DAT together");
assert property (@(posedge clk) disable iff (!rst_n) $changed({cmd_s_oe, cmd_s, dat_s_oe, dat_s}) |-> !sd_clk)
  else $error("SDC: card output changed while sd_clk is high");
cover property (@(posedge clk) disable iff (!rst_n) dat_s_oe == 4'b0001 && !dat_s[0]);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;      // a falling edge: the card has no clock to see a level reset
logic sd_clk = 1'b1, cmd_m = 1'b0, cmd_m_oe = 1'b0, dat_m_oe = 1'b0;
logic [3:0] dat_m = 4'h0;
wire cmd_s, cmd_s_oe;
wire [3:0] dat_s, dat_s_oe;

always #5 clk = ~clk;

sdc_model u_dut (.clk(clk), .rst_n(rst_n), .sd_clk(sd_clk), .cmd_m(cmd_m), .cmd_m_oe(cmd_m_oe), .dat_m(dat_m),
                 .dat_m_oe(dat_m_oe), .cmd_s(cmd_s), .cmd_s_oe(cmd_s_oe), .dat_s(dat_s), .dat_s_oe(dat_s_oe));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [6:0] crc7(input logic [119:0] d, input integer n);
  logic [6:0] c;
  logic fb;
  c = 7'h00;
  for (int i = 119; i >= 0; i--) if (i < n) begin fb = d[i] ^ c[6]; c = {c[5:0], 1'b0}; if (fb) c = c ^ 7'h09; end
  crc7 = c;
endfunction
function automatic logic [15:0] crc16(input logic [15:0] c, input logic b);
  crc16 = {c[14:0], 1'b0} ^ ((b ^ c[15]) ? 16'h1021 : 16'h0000);
endfunction

logic cl;
logic [3:0] dl;
integer conflict = 0;
task automatic clk1(input logic co, input logic c, input logic doe, input logic [3:0] d);
  @(negedge clk); sd_clk = 0; cmd_m_oe = co; cmd_m = c; dat_m_oe = doe; dat_m = d;
  @(negedge clk);
  sd_clk = 1;
  cl = co ? c : (cmd_s_oe ? cmd_s : 1'b1);
  for (int i = 0; i < 4; i++) dl[i] = doe ? d[i] : (dat_s_oe[i] ? dat_s[i] : 1'b1);
  if ((co && cmd_s_oe) || (doe && dat_s_oe != 0)) conflict = conflict + 1;
  @(negedge clk);
endtask
task automatic idle1(); clk1(0, 0, 0, 4'h0); endtask
logic [135:0] r;
integer ncr, rlen_got;
logic got;
// command; response hunted for 64 clocks, len bits
task automatic cmd(input logic [5:0] i, input logic [31:0] a, input integer len = 48, input logic badcrc = 0,
                   input integer trail = 4);
  logic [39:0] b;
  logic [47:0] f;
  integer k;
  b = {2'b01, i, a}; f = {b, crc7({80'h0, b}, 40), 1'b1};
  if (badcrc) f[3] = ~f[3];
  repeat (2) idle1();
  for (int j = 47; j >= 0; j--) clk1(1, f[j], 0, 4'h0);
  got = 0; k = 0; r = 0;
  while (k < 64 && !got) begin idle1(); k = k + 1; if (!cl) got = 1; end
  ncr = k;
  if (got) for (int j = 1; j < len; j++) begin idle1(); r = {r[134:0], cl}; end
  repeat (trail) idle1();
endtask
function automatic logic r48_ok(input logic [5:0] i);
  r48_ok = r[46] == 1'b0 && r[45:40] == i && r[0] == 1'b1 && crc7({80'h0, 1'b0, r[46:8]}, 40) == r[7:1];
endfunction
logic [255:0] wb, rb;
logic [3:0] tok;
integer busy, tokk;
localparam int TOKK = 2;
task automatic wr_blk(input logic bad = 0);
  logic [15:0] c [0:3];
  logic [3:0] v;
  integer k;
  for (int l = 0; l < 4; l++) c[l] = 16'h0;
  clk1(0, 0, 1, 4'hF); clk1(0, 0, 1, 4'h0);
  for (int n = 0; n < 64; n++) begin
    v = wb[255 - 4 * n -: 4];
    for (int l = 0; l < 4; l++) c[l] = crc16(c[l], v[l]);
    clk1(0, 0, 1, v);
  end
  if (bad) c[2][7] = ~c[2][7];
  for (int n = 15; n >= 0; n--) clk1(0, 0, 1, {c[3][n], c[2][n], c[1][n], c[0][n]});
  clk1(0, 0, 1, 4'hF);
  k = 0;
  do begin idle1(); k = k + 1; end while (dl[0] && k < 64);
  tokk = k;
  tok = {dl[0], 3'b000};
  for (int j = 2; j >= 0; j--) begin idle1(); tok[j] = dl[0]; end
  idle1();
  busy = 0;
  if (dl[0]) begin idle1(); while (!dl[0] && busy < 64) begin busy = busy + 1; idle1(); end end
  repeat (4) idle1();
endtask
logic rd_ok;
task automatic rd_blk();
  logic [15:0] c [0:3], x [0:3];
  integer k;
  for (int l = 0; l < 4; l++) begin c[l] = 16'h0; x[l] = 16'h0; end
  k = 0;
  do begin idle1(); k = k + 1; end while (dl != 4'h0 && k < 64);
  for (int n = 0; n < 64; n++) begin
    idle1(); rb[255 - 4 * n -: 4] = dl;
    for (int l = 0; l < 4; l++) c[l] = crc16(c[l], dl[l]);
  end
  for (int n = 0; n < 16; n++) begin idle1(); for (int l = 0; l < 4; l++) x[l] = {x[l][14:0], dl[l]}; end
  idle1();
  rd_ok = k == 2 && dl == 4'hF && c[0] == x[0] && c[1] == x[1] && c[2] == x[2] && c[3] == x[3];
  repeat (4) idle1();
endtask
function automatic logic [255:0] init_blk(input integer b);
  for (int i = 0; i < 32; i++) init_blk[255 - 8 * i -: 8] = (16 * b + i) ^ 8'h3C;
endfunction
logic [15:0] rca;

initial begin
  repeat (3) @(posedge clk);
  chk(cmd_s_oe === 1'b0 && dat_s_oe === 4'h0, "card off the bus in reset");
  rst_n = 1;
  repeat (4) idle1();
  cmd(6'd0, 32'h0); chk(!got, "CMD0: no response");
  cmd(6'd8, 32'h0000_02AA); chk(!got, "CMD8 with VHS 2: no response");
  cmd(6'd8, 32'h0000_01AA); chk(got && ncr == 2 && r48_ok(6'd8) && r[19:8] == 12'h1AA, "CMD8: R7 echo after NCR = 2");
  cmd(6'd41, 32'h40FF_8000); chk(!got, "CMD41 without CMD55: illegal, no response");
  cmd(6'd55, 32'h0); chk(got && r48_ok(6'd55) && r[39:8] == 32'h0040_0120, "CMD55: ILLEGAL_COMMAND, idle, APP_CMD");
  cmd(6'd41, 32'h40FF_8000);
  chk(got && r[45:40] == 6'h3F && r[7:0] == 8'hFF && r[39:8] == 32'h00FF_8000, "ACMD41: R3, busy");
  cmd(6'd55, 32'h0); chk(r[39:8] == 32'h0000_0120, "flags cleared after a report");
  cmd(6'd41, 32'h40FF_8000); chk(got && r[39:8] == 32'hC0FF_8000, "ACMD41: ready, CCS 1");
  cmd(6'd3, 32'h0); chk(!got, "CMD3 in ready: illegal, no response");
  cmd(6'd2, 32'h0, 136);
  chk(got && r[133:128] == 6'h3F && r[0] && crc7(r[127:8], 120) == r[7:1] && r[127:8] == 120'h1D4F565344433110123456780016A0,
      "CMD2: R2 with the CID and its CRC7");
  cmd(6'd3, 32'h0); rca = r[39:24];
  chk(got && r48_ok(6'd3) && rca == 16'h1234 && r[23:8] == 16'h4500, "CMD3: R6 with the RCA, ILLEGAL_COMMAND, ident state");
  cmd(6'd55, 32'h0); chk(got && r48_ok(6'd55), "CMD55 in stby");
  cmd(6'd41, 32'h40FF_8000); chk(!got, "ACMD41 in stby: illegal, no response");
  cmd(6'd13, {rca, 16'h0}, 48, 1); chk(!got, "bad CRC7: no response");
  cmd(6'd13, {rca, 16'h0}); chk(got && ncr == 2 && r48_ok(6'd13) && r[39:8] == 32'h00C0_0700, "CMD13: COM_CRC_ERROR and ILLEGAL_COMMAND, stby, NCR = 2");
  cmd(6'd7, {rca, 16'h0}); chk(got && r48_ok(6'd7) && r[20:17] == 4'd3, "CMD7: selected");
  wb = 256'hDEADBEEF_01234567_89ABCDEF_FEDCBA98_76543210_A5A5A5A5_5A5A5A5A_00FF00FF;
  cmd(6'd24, 32'd2, 48, 0, 0); chk(got && ncr == 2 && r48_ok(6'd24) && r[39:8] == 32'h0000_0900, "CMD24: R1 after NCR = 2, tran state, flags clear");
  wr_blk(); chk(tok == 4'b0010 && busy == 4 && tokk == TOKK, "block accepted: token 010 after 2 clocks, 4 clocks busy");
  cmd(6'd17, 32'd2, 48, 0, 0); rd_blk(); chk(rd_ok && rb == wb, "CMD17 reads the block back, NAC = 2, CRC16s good");
  cmd(6'd17, 32'd3, 48, 0, 0); rd_blk(); chk(rd_ok && rb == init_blk(3), "an untouched block");
  cmd(6'd24, 32'd3, 48, 0, 0); wr_blk(1); chk(tok == 4'b0101 && busy == 0, "bad CRC16: token 101, no busy");
  cmd(6'd17, 32'd3, 48, 0, 0); rd_blk(); chk(rb == init_blk(3), "and nothing written");
  cmd(6'd6, 32'h0); chk(!got, "CMD6: illegal");
  cmd(6'd7, {rca ^ 16'h1, 16'h0}); chk(!got, "CMD7 to another RCA: deselected, no response");
  cmd(6'd17, 32'd2); chk(!got, "CMD17 in stby: illegal");
  cmd(6'd13, {rca, 16'h0}); chk(got && r[39:8] == 32'h0040_0700, "CMD13: ILLEGAL_COMMAND, stby");
  cmd(6'd13, {rca ^ 16'h8000, 16'h0}); chk(!got, "CMD13 to another RCA: no response");
  cmd(6'd0, 32'h0);
  cmd(6'd8, 32'h0000_01AA);
  cmd(6'd55, 32'h0); cmd(6'd41, 32'h00FF_8000); chk(got && r[39:8] == 32'h00FF_8000, "after CMD0: busy again");
  cmd(6'd55, 32'h0); cmd(6'd41, 32'h00FF_8000); chk(r[39:8] == 32'h80FF_8000, "no HCS: ready with CCS 0");
  cmd(6'd2, 32'h0, 136); cmd(6'd3, 32'h0); cmd(6'd7, {rca, 16'h0});
  cmd(6'd17, {23'h0, 4'd2, 5'h0}, 48, 0, 0); rd_blk(); chk(rd_ok && rb == wb, "byte addressing: address 64 is block 2");
  chk(conflict == 0, "no bus contention");
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
