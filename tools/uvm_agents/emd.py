# eMMC device VIP: an eMMC device model (the boot / storage flash of an IP
# camera) with a host agent, 1-bit bus, the block length of eMMC_top.
#
# Agent -> DUT (host): emmc_clk, the device's RST_n emmc_rst_n, the host's
# CMD drive cmd_m with cmd_m_oe, its DAT0 drive dat0_m with dat0_m_oe.
# DUT -> agent (device): cmd_s / cmd_s_oe, dat0_s / dat0_s_oe. Undriven
# lines read 1 (pull-ups). Both sides change their outputs on the emmc_clk
# falling edge and sample on the rising edge.
#
# tb/top_tb.sv emd_model is the device, made to pair with eMMC_top in
# open-ip-portfolio (32-byte blocks, 1-bit bus, RCA set by the host):
#   CMD0 -> idle (no response). CMD1 in idle: R3 with the OCR (access mode
#   sector, 0xFF8080 window), busy for POLLS calls, then ready -> ready.
#   CMD2 in ready: R2 with the CID (its own CRC7, CID[0] = 1) -> ident. CMD3
#   in ident with a non-zero RCA in the argument: R1, the RCA is taken ->
#   stby. CMD7 with the RCA in stby / tran: R1b (R1, then DAT0 low SELBUSY
#   clocks from two clocks after the end bit) -> tran; another RCA
#   deselects (tran -> stby) without a response. CMD13 with the RCA: R1.
#   CMD17 / CMD24 in tran: R1, then a read block NAC clocks after the
#   response (start 0, 256 bits, CRC16, end 1), or a write block from the
#   host, then the CRC status token two clocks after its end bit (010
#   accepted, 101 CRC / end bit error) and BUSY clocks of busy. A command
#   with a bad CRC7 / end / transmission bit gets no response and sets
#   COM_CRC_ERROR; a command not legal in the state gets none and sets
#   ILLEGAL_COMMAND; both show in the next R1 and are then cleared. R1
#   status: CURRENT_STATE when the command arrived in [12:9] and
#   READY_FOR_DATA. Responses start NCR clocks after the command's end bit.
#   Blocks are addressed by number (sector mode), 16 blocks, block b byte i =
#   (16 b + i) ^ 0xC3 after the system reset. RST_n low resets the device
#   (state, RCA, flags, any transfer) but keeps the blocks.
# In a SoC bench the device connects to eMMC_top's pins (emmc_clk,
# emmc_rst_n, cmd_m <= cmd, cmd_m_oe <= 1, dat0_m <= dat[0], dat0_m_oe <= 1,
# and cmd / dat[0] driven by the device where its enables are set); the
# agent runs passive and its monitor records every command, response and
# block.

EMD_FUNCS = """
function automatic bit [6:0] emd_crc7(bit [119:0] d, int n);   // over d[n-1:0], MSB first
  bit [6:0] c = 0;
  for (int i = n - 1; i >= 0; i--) begin
    bit fb = d[i] ^ c[6];
    c = {c[5:0], 1'b0};
    if (fb) c ^= 7'h09;
  end
  return c;
endfunction
function automatic bit [15:0] emd_crc16(bit [15:0] c, bit b);
  bit fb = b ^ c[15];
  return {c[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
endfunction
function automatic bit [47:0] emd_frame(bit [5:0] i, bit [31:0] a, bit tx = 1'b1);
  bit [39:0] b = {1'b0, tx, i, a};
  return {b, emd_crc7({80'h0, b}, 40), 1'b1};
endfunction
function automatic bit [255:0] emd_init_blk(int b);
  bit [255:0] v;
  for (int i = 0; i < 32; i++) v[255 - 8 * i -: 8] = 8'((16 * b + i) ^ 8'hC3);
  return v;
endfunction
localparam bit [119:0] EMD_CID_BODY = 120'h150100454D4D43313600123456789A;
"""

SPEC = dict(
    vip="eMMC_Device-UVM-VIP", p="emd", P="EMD", dir="emd", family="Memory",
    desc="eMMC device VIP: device model with CMD0 / 1 / 2 / 3 / 7 / 13 / 17 / 24, R1 / R1b / R2 / R3 responses "
         "with CRC7, 1-bit data blocks with CRC16, CRC status token and busy, RST_n hardware reset, "
         "COM_CRC_ERROR / ILLEGAL_COMMAND reporting; eMMC host agent and bus monitor (eMMC_top pins).",
    about="""
An IP camera boots from and logs to an eMMC device on the SoC's eMMC host.
The VIP's DUT model is that device, made to pair with eMMC_top in
open-ip-portfolio (the same 32-byte blocks, 1-bit bus and host-assigned
RCA), so a SoC bench can hang it on the host's pins. The agent is a host
that walks the device through identification (CMD0, CMD1 polls, CMD2,
CMD3, CMD7 with its R1b busy) and data transfer (CMD24 with good and
corrupted block CRCs, CMD17 read-back, CMD13), and sends commands with a
bad CRC7, commands that are illegal in the state, CMD3 with RCA 0, CMD7 to
another RCA and to RCA 0, CMD0 and RST_n pulses in the middle of
everything. The scoreboard runs its own copy of the device on the
monitored host bits and predicts the device's CMD and DAT0 drive at every
emmc_clk rising edge: response timing (NCR, NAC), every response bit and
CRC7, the CID, read data and CRC16, the CRC status token, the write and
select busy times, and that the blocks survive RST_n.""",
    defs=EMD_FUNCS,
    timeout=40000,
    cfg="""int unsigned half = 2;     // clocks per emmc_clk half period
int unsigned gap  = 16;    // clocks with emmc_clk stopped between items""",
    ports=[
        ("in", "logic", "emmc_clk"), ("in", "logic", "emmc_rst_n"), ("in", "logic", "cmd_m"),
        ("in", "logic", "cmd_m_oe"), ("in", "logic", "dat0_m"), ("in", "logic", "dat0_m_oe"),
        ("out", "logic", "cmd_s"), ("out", "logic", "cmd_s_oe"),
        ("out", "logic", "dat0_s"), ("out", "logic", "dat0_s_oe"),
    ],
    fields=[
        ("bit [4:0]", "mo", "req", "q"),        # {emmc_rst_n, cmd_m_oe, cmd_m, dat0_m_oe, dat0_m} per emmc_clk rise (masked)
        ("bit [3:0]", "so", "rsp", "q"),        # {cmd_s_oe, cmd_s, dat0_s_oe, dat0_s} per emmc_clk rise (masked)
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [3:0]", "blk", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [5:0]", "idx", "info"),
        ("bit [31:0]", "arg", "info"),
        ("bit", "got", "info"),
    ],
    tr_functions="""
// kind: 0 CMD0, 1 CMD1, 2 CMD2, 3 CMD3 (RCA 1 + blk), 4 CMD7 (RCA), 5 CMD7
// (other RCA), 6 CMD7 (RCA 0), 7 CMD13, 8 CMD13 (other RCA), 9 CMD24, 10
// CMD24 with a bad CRC16, 11 CMD17, 12 CMD13 with a bad CRC7, 13 CMD8 (not
// modelled: illegal), 14 RST_n pulse (idx 63, no command), 15 CMD3 with RCA
// 0, 16-31 CMD24 / CMD17 / CMD13 / CMD1 mix
function void set(int k, int b = 0, bit [31:0] s = 32'h1); kind = k; blk = b; seed = s; endfunction
function int kk();
  if (kind >= 16) return (kind % 4 == 0) ? 9 : (kind % 4 == 1) ? 11 : (kind % 4 == 2) ? 7 : 1;
  return kind;
endfunction
function bit [47:0] cmd(bit [15:0] rca);
  case (kk())
    0: begin idx = 0; arg = 0; end
    1: begin idx = 1; arg = 32'h40FF_8080; end
    2: begin idx = 2; arg = 0; end
    3: begin idx = 3; arg = {16'h1 + 16'(blk), 16'h0}; end
    4: begin idx = 7; arg = {rca, 16'h0}; end
    5: begin idx = 7; arg = {rca ^ 16'h0101, 16'h0}; end
    6: begin idx = 7; arg = 0; end
    7, 12: begin idx = 13; arg = {rca, 16'h0}; end
    8: begin idx = 13; arg = {rca ^ 16'h8000, 16'h0}; end
    9, 10: begin idx = 24; arg = {28'h0, blk}; end
    11: begin idx = 17; arg = {28'h0, blk}; end
    13: begin idx = 8; arg = 0; end
    14: begin idx = 63; arg = 0; end
    default: begin idx = 3; arg = 0; end
  endcase
  if (kk() == 12) return emd_frame(idx, arg) ^ 48'h4;
  return emd_frame(idx, arg);
endfunction
function bit [255:0] wdata();
  bit [31:0] x = seed | 1;
  bit [255:0] v;
  for (int i = 0; i < 8; i++) begin x ^= x << 13; x ^= x >> 17; x ^= x << 5; v[32 * i +: 32] = x; end
  return v;
endfunction
function bit bad_crc(); return kk() == 10; endfunction
""",
    drv_rsp=False,
    drv_members="""bit [15:0]      rca = 0;
bit             rn = 1;
emd_transaction cur;""",
    drv_tasks="""
// one emmc_clk period: outputs at the falling edge, the lines at the rising edge
task automatic clk1(bit co, bit c, bit doe, bit d, output bit cl, output bit dl);
  vif.drv_cb.emmc_clk   <= 1'b0;
  vif.drv_cb.emmc_rst_n <= rn;
  vif.drv_cb.cmd_m_oe   <= co; vif.drv_cb.cmd_m  <= c;
  vif.drv_cb.dat0_m_oe  <= doe; vif.drv_cb.dat0_m <= d;
  repeat (cfg.half) @(vif.drv_cb);
  vif.drv_cb.emmc_clk <= 1'b1;
  cl = co ? c : (vif.drv_cb.cmd_s_oe ? vif.drv_cb.cmd_s : 1'b1);
  dl = doe ? d : (vif.drv_cb.dat0_s_oe ? vif.drv_cb.dat0_s : 1'b1);
  cur.mo.push_back({rn, co, c & co, doe, d & doe});
  repeat (cfg.half) @(vif.drv_cb);
endtask
task automatic idle1(output bit cl, output bit dl);
  clk1(1'b0, 1'b0, 1'b0, 1'b0, cl, dl);
endtask
""",
    drv_desc="one command per item with emmc_clk running: 4 idle clocks, the 48-bit command, a response hunt of up to 64 clocks and the response; for CMD7 the R1b busy wait; for CMD24 the block (start, 256 bits, CRC16, end), the CRC status token and the busy wait; for CMD17 the block hunt and the block; an RST_n pulse item holds emmc_rst_n low 4 clocks; then 8 idle clocks and emmc_clk stopped for cfg.gap clocks",
    drv_idle="""
vif.drv_cb.emmc_clk   <= 1'b1;
vif.drv_cb.emmc_rst_n <= 1'b1;
vif.drv_cb.cmd_m      <= 1'b0;
vif.drv_cb.cmd_m_oe   <= 1'b0;
vif.drv_cb.dat0_m     <= 1'b0;
vif.drv_cb.dat0_m_oe  <= 1'b0;
""",
    drv_item="""
bit cl, dl;
bit [47:0] f;
bit [135:0] r = 0;
int k;
cur = t;
t.mo.delete();
f = t.cmd(rca);
t.got = 0;
@(vif.drv_cb);
repeat (4) idle1(cl, dl);
if (t.idx == 63) begin
  rn = 0; repeat (4) idle1(cl, dl);
  rn = 1; rca = 0;
end else begin
  for (int i = 47; i >= 0; i--) clk1(1'b1, f[i], 1'b0, 1'b0, cl, dl);
  k = 0;
  while (k < 64 && !t.got) begin idle1(cl, dl); if (!cl) t.got = 1; k++; end
  if (t.got) begin
    int len = (t.idx == 2) ? 136 : 48;
    for (int i = 1; i < len; i++) begin idle1(cl, dl); r = {r[134:0], cl}; end
    if (t.idx == 3) rca = t.arg[31:16];
  end
  if (t.idx == 0) rca = 0;
  if (t.got && t.idx == 7) begin
    k = 0;
    do begin idle1(cl, dl); k++; end while (dl && k < 8);
    k = 0;
    while (!dl && k < 256) begin idle1(cl, dl); k++; end
  end
  if (t.got && t.idx == 24) begin
    bit [255:0] w = t.wdata();
    bit [15:0] c = 0;
    idle1(cl, dl); idle1(cl, dl);
    clk1(1'b0, 1'b0, 1'b1, 1'b1, cl, dl);
    clk1(1'b0, 1'b0, 1'b1, 1'b0, cl, dl);
    for (int n = 255; n >= 0; n--) begin c = emd_crc16(c, w[n]); clk1(1'b0, 1'b0, 1'b1, w[n], cl, dl); end
    if (t.bad_crc()) c[t.seed[3:0]] ^= 1'b1;
    for (int n = 15; n >= 0; n--) clk1(1'b0, 1'b0, 1'b1, c[n], cl, dl);
    clk1(1'b0, 1'b0, 1'b1, 1'b1, cl, dl);
    k = 0;
    do begin idle1(cl, dl); k++; end while (dl && k < 64);
    if (!dl) begin
      repeat (4) idle1(cl, dl);
      k = 0;
      do begin idle1(cl, dl); k++; end while (!dl && k < 256);
    end
  end
  if (t.got && t.idx == 17) begin
    k = 0;
    do begin idle1(cl, dl); k++; end while (dl && k < 64);
    if (!dl) repeat (256 + 16 + 1) idle1(cl, dl);
  end
end
repeat (8) idle1(cl, dl);
repeat (cfg.gap) @(vif.drv_cb);
""",
    mon_desc="host and device drive (masked by their enables) and RST_n at every emmc_clk rising edge; emmc_clk stopped for more than half of cfg.gap clocks ends the item",
    mon_run="""
forever begin
  emd_transaction t;
  bit pc;
  int q = 0;
  pc = vif.mon_cb.emmc_clk;
  @(vif.mon_cb);
  while (!(pc === 1'b0 && vif.mon_cb.emmc_clk === 1'b1)) begin pc = vif.mon_cb.emmc_clk; @(vif.mon_cb); end
  t = emd_transaction::type_id::create("t");
  forever begin
    if (pc === 1'b0 && vif.mon_cb.emmc_clk === 1'b1) begin
      t.mo.push_back({vif.mon_cb.emmc_rst_n, vif.mon_cb.cmd_m_oe, vif.mon_cb.cmd_m & vif.mon_cb.cmd_m_oe,
                      vif.mon_cb.dat0_m_oe, vif.mon_cb.dat0_m & vif.mon_cb.dat0_m_oe});
      t.so.push_back({vif.mon_cb.cmd_s_oe, vif.mon_cb.cmd_s & vif.mon_cb.cmd_s_oe, vif.mon_cb.dat0_s_oe,
                      vif.mon_cb.dat0_s & vif.mon_cb.dat0_s_oe});
      q = 0;
    end else if (++q > cfg.gap / 2) break;
    pc = vif.mon_cb.emmc_clk;
    @(vif.mon_cb);
  end
  publish(t);
end
""",
    sb_members="""// the device (scoreboard copy), kept across items
bit [255:0] mem [16];
bit         minit = 0;
int         cst = 0, polls = 0, dm = 0, rdd = 0, tokd = 0, tokn = 0, busyn = 0, dcnt = 0;
bit         crc_e = 0, ill = 0;
bit [15:0]  rca = 0;
int         rxc = 0, txd = 0, txn = 0;
bit [47:0]  rxs = 0;
bit [135:0] txs = 0;
bit [3:0]   blk = 0;
bit [255:0] buff = 0;
bit [15:0]  c = 0, rc = 0;
bit [4:0]   tok = 0;
bit         o_cmd = 0, o_cmd_oe = 0, o_dat = 0, o_dat_oe = 0;
localparam int NCR = 2, NAC = 2, BUSY = 4, SELBUSY = 3, POLLS = 1;

function void reset_dev();
  cst = 0; polls = 0; dm = 0; rdd = 0; tokd = 0; tokn = 0; busyn = 0; dcnt = 0; crc_e = 0; ill = 0; rca = 0;
  rxc = 0; txd = 0; txn = 0; rxs = 0; txs = 0; blk = 0; buff = 0; c = 0; rc = 0; tok = 0;
  o_cmd = 0; o_cmd_oe = 0; o_dat = 0; o_dat_oe = 0;
endfunction
function void send(bit [135:0] fr, int n);
  txs = fr; txn = n; txd = NCR - 1;
endfunction
function void r1(bit [5:0] i, int st);
  send({emd_frame(i, {8'h00, crc_e, ill, 9'h000, 4'(st), 1'b1, 8'h00}, 1'b0), 88'h0}, 48);
  crc_e = 0; ill = 0;
endfunction
function void frame(bit [47:0] f);
  bit [5:0] i = f[45:40];
  bit [31:0] a = f[39:8];
  int st = cst;
  if (emd_crc7({80'h0, f[47:8]}, 40) != f[7:1] || !f[0] || !f[46]) begin crc_e = 1; return; end
  if (i == 0) begin cst = 0; polls = 0; rca = 0; dm = 0; end
  else if (i == 1 && cst == 0) begin
    bit rdy = polls >= POLLS;
    if (polls != 15) polls++;
    if (rdy) cst = 1;
    send({2'b00, 6'h3F, rdy, 2'b10, 29'h00FF_8080, 8'hFF, 88'h0}, 48);
  end else if (i == 2 && cst == 1) begin
    bit [127:0] cid = {EMD_CID_BODY, emd_crc7(EMD_CID_BODY, 120), 1'b1};
    cst = 2; send({2'b00, 6'h3F, cid[127:1], 1'b1}, 136);
  end else if (i == 3 && cst == 2 && a[31:16] != 0) begin
    cst = 3; rca = a[31:16]; r1(i, st);
  end else if (i == 7 && (cst == 3 || cst == 4)) begin
    if (a[31:16] == rca) begin cst = 4; r1(i, st); dm = 6; end
    else if (cst == 4) cst = 3;
  end else if (i == 13 && (cst == 3 || cst == 4)) begin
    if (a[31:16] == rca) r1(i, st);
  end else if ((i == 17 || i == 24) && cst == 4) begin
    r1(i, st);
    blk = a[3:0];
    if (i == 17) begin dm = 7; buff = mem[blk]; end
    else dm = 1;
  end else ill = 1;
endfunction
""",
    predict="""
if (!minit) begin for (int b = 0; b < 16; b++) mem[b] = emd_init_blk(b); minit = 1; end
t.so.delete();
foreach (t.mo[i]) begin
  bit cl, dl;
  if (!t.mo[i][4]) begin reset_dev(); t.so.push_back(4'h0); continue; end
  t.so.push_back({o_cmd_oe, o_cmd & o_cmd_oe, o_dat_oe, o_dat & o_dat_oe});
  cl = t.mo[i][3] ? t.mo[i][2] : (o_cmd_oe ? o_cmd : 1'b1);
  dl = t.mo[i][1] ? t.mo[i][0] : (o_dat_oe ? o_dat : 1'b1);
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
    1: if (!dl) begin dm = 2; dcnt = 0; c = 0; end
    2: begin
         buff = {buff[254:0], dl};
         c = emd_crc16(c, dl);
         if (++dcnt == 256) begin dm = 3; dcnt = 0; rc = 0; end
       end
    3: begin
         rc = {rc[14:0], dl};
         if (++dcnt == 16) dm = 4;
       end
    4: begin
         bit good = dl && rc == c;
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
    if (txn == 0 && dm == 6) begin dm = 5; tokd = 2; tokn = 0; busyn = SELBUSY; end
  end else o_cmd_oe = 0;
  case (dm)
    5: if (tokd > 0) begin tokd--; o_dat_oe = 0; end
       else if (tokn > 0) begin o_dat_oe = 1; o_dat = tok[4]; tok = tok << 1; tokn--; end
       else if (busyn > 0) begin o_dat_oe = 1; o_dat = 1'b0; busyn--; end
       else begin o_dat_oe = 0; dm = 0; end
    8: if (rdd > 0) begin rdd--; o_dat_oe = 0; end
       else begin o_dat_oe = 1; o_dat = 1'b0; dm = 9; dcnt = 0; c = 0; end
    9: begin
         o_dat_oe = 1; o_dat = buff[255 - dcnt];
         c = emd_crc16(c, o_dat);
         if (++dcnt == 256) begin dm = 10; dcnt = 0; end
       end
    10: begin
          o_dat_oe = 1; o_dat = c[15]; c = c << 1;
          if (++dcnt == 16) dm = 11;
        end
    11: begin o_dat_oe = 1; o_dat = 1'b1; dm = 12; end
    12: begin o_dat_oe = 0; dm = 0; end
    default: o_dat_oe = 0;
  endcase
end
""",
    checks="""
foreach (t.so[i]) begin
  if (t.so[i][3] && t.mo[i][3]) fail(t, "host and device drive CMD together");
  if (t.so[i][1] && t.mo[i][1]) fail(t, "host and device drive DAT0 together");
end
""",
    coverage="""
cp_idx  : coverpoint tr.idx { bins c0 = {0}; bins c1 = {1}; bins c2 = {2}; bins c3 = {3}; bins c7 = {7}; bins c13 = {13};
                              bins c17 = {17}; bins c24 = {24}; bins c8 = {8}; bins rst = {63}; }
cp_got  : coverpoint tr.got;
cp_len  : coverpoint tr.mo.size() { bins rst = {[1:40]}; bins cmd = {[100:200]}; bins r2 = {[201:260]}; bins blk = {[261:700]}; }
""",
    directed="""
// identification, transfers, every error path, CMD0 and RST_n in transfer state
t = item(); t.set(7); send(t);             // illegal in idle
t = item(); t.set(0); send(t);
t = item(); t.set(1); send(t);             // busy
t = item(); t.set(2); send(t);             // illegal in idle
t = item(); t.set(1); send(t);             // ready
t = item(); t.set(1); send(t);             // illegal in ready
t = item(); t.set(2); send(t);
t = item(); t.set(15); send(t);            // RCA 0: illegal
t = item(); t.set(3); send(t);             // reports ILLEGAL_COMMAND
t = item(); t.set(12); send(t);            // bad CRC7
t = item(); t.set(7); send(t);             // reports COM_CRC_ERROR
t = item(); t.set(8); send(t);
t = item(); t.set(4); send(t);
for (int b = 0; b < 4; b++) begin
  t = item(); t.set(11, b); send(t);
  t = item(); t.set(9, b, 32'h1000 + b); send(t);
  t = item(); t.set(11, b); send(t);
end
t = item(); t.set(10, 5, 32'h77); send(t);
t = item(); t.set(11, 5); send(t);
t = item(); t.set(13); send(t);
t = item(); t.set(7); send(t);
t = item(); t.set(4); send(t);             // CMD7 again in tran
t = item(); t.set(14); send(t);            // RST_n in tran
t = item(); t.set(7); send(t);             // idle again
t = item(); t.set(0); send(t);
t = item(); t.set(1); send(t);
t = item(); t.set(1); send(t);
t = item(); t.set(2); send(t);
t = item(); t.set(3, 6); send(t);
t = item(); t.set(4); send(t);
t = item(); t.set(11, 2); send(t);         // the block survives RST_n
t = item(); t.set(5); send(t);             // deselect
t = item(); t.set(7); send(t);
t = item(); t.set(9, 1); send(t);          // illegal in stby
t = item(); t.set(6); send(t);
t = item(); t.set(4); send(t);
t = item(); t.set(9, 9, 32'h55); send(t);
t = item(); t.set(11, 9); send(t);
t = item(); t.set(0); send(t);             // CMD0 from transfer state
t = item(); t.set(11, 1); send(t);
""",
    drain_ns=4000,
    model="""
module emd_model #(
  parameter int NCR     = 2,
  parameter int NAC     = 2,
  parameter int BUSY    = 4,
  parameter int SELBUSY = 3,
  parameter int POLLS   = 1
) (
  input  logic clk,
  input  logic rst_n,
  input  logic emmc_clk,
  input  logic emmc_rst_n,
  input  logic cmd_m,
  input  logic cmd_m_oe,
  input  logic dat0_m,
  input  logic dat0_m_oe,
  output logic cmd_s,
  output logic cmd_s_oe,
  output logic dat0_s,
  output logic dat0_s_oe
);
  localparam logic [119:0] CID_BODY = 120'h150100454D4D43313600123456789A;
  localparam logic [3:0] D_NONE = 4'd0, D_WWAIT = 4'd1, D_WDATA = 4'd2, D_WCRC = 4'd3, D_WEND = 4'd4,
                         D_TOK = 4'd5, D_BPEND = 4'd6, D_RPEND = 4'd7, D_RWAIT = 4'd8, D_RDATA = 4'd9,
                         D_RCRC = 4'd10, D_REND = 4'd11, D_RREL = 4'd12;
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
  function automatic logic [47:0] r1(input logic [5:0] i, input logic [2:0] st, input logic ce,
                                     input logic il);
    logic [39:0] b;
    b = {2'b00, i, 8'h00, ce, il, 9'h000, 1'b0, st, 1'b1, 8'h00};
    r1 = {b, crc7({80'h0, b}, 40), 1'b1};
  endfunction

  logic [255:0] mem [0:15];
  logic [2:0]   cst;
  logic [3:0]   polls, dm, blk;
  logic         crc_e, ill;
  logic [15:0]  rca;
  logic [5:0]   rxc;
  logic [47:0]  rxs;
  logic [7:0]   txn;
  logic [6:0]   txd;
  logic [135:0] txs;
  logic [255:0] buff;
  logic [15:0]  crc, rcrc;
  logic [8:0]   dcnt;
  logic [6:0]   rdd, tokd;
  logic [2:0]   tokn;
  logic [4:0]   tok;
  logic [7:0]   busyn;
  logic         n_cmd, n_cmd_oe, n_dat, n_dat_oe;
  wire          cl = cmd_m_oe ? cmd_m : (cmd_s_oe ? cmd_s : 1'b1);
  wire          dl = dat0_m_oe ? dat0_m : (dat0_s_oe ? dat0_s : 1'b1);
  wire          arst_n = rst_n & emmc_rst_n;
  wire          _unused = &{1'b0, clk};

  // rising emmc_clk: receive, run the device, decide the next outputs
  always_ff @(posedge emmc_clk or negedge arst_n) begin
    if (!arst_n) begin
      cst <= '0; polls <= '0; dm <= D_NONE; blk <= '0; crc_e <= 1'b0; ill <= 1'b0;
      rca <= '0; rxc <= '0; rxs <= '0; txn <= '0; txd <= '0; txs <= '0; buff <= '0;
      crc <= '0; rcrc <= '0; dcnt <= '0; rdd <= '0; tokd <= '0; tokn <= '0; tok <= '0; busyn <= '0;
      n_cmd <= 1'b0; n_cmd_oe <= 1'b0; n_dat <= 1'b0; n_dat_oe <= 1'b0;
      if (!rst_n)            // RST_n alone keeps the blocks
        for (int b = 0; b < 16; b++)
          for (int i = 0; i < 32; i++) mem[b][255 - 8 * i -: 8] <= 8'((16 * b + i) ^ 8'hC3);
    end else begin : step
      logic [2:0]   v_cst;
      logic [3:0]   v_polls, v_dm, v_blk;
      logic         v_crc_e, v_ill;
      logic [15:0]  v_rca;
      logic [5:0]   v_rxc;
      logic [47:0]  v_rxs, f;
      logic [7:0]   v_txn;
      logic [6:0]   v_txd;
      logic [135:0] v_txs;
      logic [255:0] v_buff;
      logic [15:0]  v_crc, v_rcrc;
      logic [8:0]   v_dcnt;
      logic [6:0]   v_rdd, v_tokd;
      logic [2:0]   v_tokn;
      logic [4:0]   v_tok;
      logic [7:0]   v_busyn;
      logic         b, go, good, rdy, cmdok;
      logic [2:0]   st;
      logic [5:0]   i;
      logic [31:0]  a;
      logic [126:0] cid;
      v_cst = cst; v_polls = polls; v_dm = dm; v_blk = blk; v_crc_e = crc_e; v_ill = ill;
      v_rca = rca; v_rxc = rxc; v_rxs = rxs; v_txn = txn; v_txd = txd; v_txs = txs;
      v_buff = buff; v_crc = crc; v_rcrc = rcrc; v_dcnt = dcnt; v_rdd = rdd; v_tokd = tokd;
      v_tokn = tokn; v_tok = tok; v_busyn = busyn;
      go = 1'b0; f = '0; cmdok = 1'b0;
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
        i = f[45:40]; a = f[39:8]; st = v_cst;
        if (crc7({80'h0, f[47:8]}, 40) != f[7:1] || !f[0] || !f[46]) v_crc_e = 1'b1;
        else if (i == 6'd0) begin v_cst = 3'd0; v_polls = '0; v_rca = '0; v_dm = D_NONE; end
        else if (i == 6'd1 && v_cst == 3'd0) begin
          rdy = v_polls >= 4'(POLLS);
          if (v_polls != 4'd15) v_polls = v_polls + 4'd1;
          if (rdy) v_cst = 3'd1;
          v_txs = {2'b00, 6'h3F, rdy, 2'b10, 29'h00FF_8080, 8'hFF, 88'h0};
          v_txn = 8'd48; v_txd = 7'(NCR - 1);
        end else if (i == 6'd2 && v_cst == 3'd1) begin
          cid = {CID_BODY, crc7(CID_BODY, 120)};
          v_cst = 3'd2; v_txs = {2'b00, 6'h3F, cid, 1'b1}; v_txn = 8'd136; v_txd = 7'(NCR - 1);
        end else if (i == 6'd3 && v_cst == 3'd2 && a[31:16] != 16'h0) begin
          v_cst = 3'd3; v_rca = a[31:16]; cmdok = 1'b1;
        end else if (i == 6'd7 && (v_cst == 3'd3 || v_cst == 3'd4)) begin
          if (a[31:16] == v_rca) begin v_cst = 3'd4; cmdok = 1'b1; v_dm = D_BPEND; end
          else if (v_cst == 3'd4) v_cst = 3'd3;
        end else if (i == 6'd13 && (v_cst == 3'd3 || v_cst == 3'd4)) begin
          if (a[31:16] == v_rca) cmdok = 1'b1;
        end else if ((i == 6'd17 || i == 6'd24) && v_cst == 3'd4) begin
          cmdok = 1'b1; v_blk = a[3:0];
          if (i == 6'd17) begin v_dm = D_RPEND; v_buff = mem[v_blk]; end
          else v_dm = D_WWAIT;
        end else v_ill = 1'b1;
        if (cmdok) begin
          v_txs = {r1(i, st, v_crc_e, v_ill), 88'h0};
          v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
        end
      end
      // write block receiver
      case (v_dm)
        D_WWAIT: if (!dl) begin v_dm = D_WDATA; v_dcnt = '0; v_crc = '0; end
        D_WDATA: begin
          v_buff = {v_buff[254:0], dl};
          v_crc = crc16(v_crc, dl);
          v_dcnt = v_dcnt + 9'd1;
          if (v_dcnt == 9'd256) begin v_dm = D_WCRC; v_dcnt = '0; v_rcrc = '0; end
        end
        D_WCRC: begin
          v_rcrc = {v_rcrc[14:0], dl};
          v_dcnt = v_dcnt + 9'd1;
          if (v_dcnt == 9'd16) v_dm = D_WEND;
        end
        D_WEND: begin
          good = dl && v_rcrc == v_crc;
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
        if (v_txn == 0 && v_dm == D_BPEND) begin v_dm = D_TOK; v_tokd = 7'd2; v_tokn = 3'd0; v_busyn = 8'(SELBUSY); end
      end else n_cmd_oe <= 1'b0;
      case (v_dm)
        D_TOK:
          if (v_tokd != 0) begin v_tokd = v_tokd - 7'd1; n_dat_oe <= 1'b0; end
          else if (v_tokn != 0) begin n_dat_oe <= 1'b1; n_dat <= v_tok[4]; v_tok = v_tok << 1; v_tokn = v_tokn - 3'd1; end
          else if (v_busyn != 0) begin n_dat_oe <= 1'b1; n_dat <= 1'b0; v_busyn = v_busyn - 8'd1; end
          else begin n_dat_oe <= 1'b0; v_dm = D_NONE; end
        D_RWAIT:
          if (v_rdd != 0) begin v_rdd = v_rdd - 7'd1; n_dat_oe <= 1'b0; end
          else begin n_dat_oe <= 1'b1; n_dat <= 1'b0; v_dm = D_RDATA; v_dcnt = '0; v_crc = '0; end
        D_RDATA: begin
          b = v_buff[8'(9'd255 - v_dcnt)];
          n_dat_oe <= 1'b1; n_dat <= b;
          v_crc = crc16(v_crc, b);
          v_dcnt = v_dcnt + 9'd1;
          if (v_dcnt == 9'd256) begin v_dm = D_RCRC; v_dcnt = '0; end
        end
        D_RCRC: begin
          n_dat_oe <= 1'b1; n_dat <= v_crc[15];
          v_crc = v_crc << 1;
          v_dcnt = v_dcnt + 9'd1;
          if (v_dcnt == 9'd16) v_dm = D_REND;
        end
        D_REND: begin n_dat_oe <= 1'b1; n_dat <= 1'b1; v_dm = D_RREL; end
        D_RREL: begin n_dat_oe <= 1'b0; v_dm = D_NONE; end
        default: n_dat_oe <= 1'b0;
      endcase
      cst <= v_cst; polls <= v_polls; dm <= v_dm; blk <= v_blk; crc_e <= v_crc_e; ill <= v_ill;
      rca <= v_rca; rxc <= v_rxc; rxs <= v_rxs; txn <= v_txn; txd <= v_txd; txs <= v_txs;
      buff <= v_buff; crc <= v_crc; rcrc <= v_rcrc; dcnt <= v_dcnt; rdd <= v_rdd; tokd <= v_tokd;
      tokn <= v_tokn; tok <= v_tok; busyn <= v_busyn;
    end
  end

  // falling emmc_clk: the outputs change
  always_ff @(negedge emmc_clk or negedge arst_n) begin
    if (!arst_n) begin
      cmd_s <= 1'b0; cmd_s_oe <= 1'b0; dat0_s <= 1'b0; dat0_s_oe <= 1'b0;
    end else begin
      cmd_s <= n_cmd; cmd_s_oe <= n_cmd_oe; dat0_s <= n_dat; dat0_s_oe <= n_dat_oe;
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({emmc_clk, emmc_rst_n, cmd_m_oe, dat0_m_oe, cmd_s_oe, dat0_s_oe}))
  else $error("EMD: X on emmc_clk, RST_n or an enable");
assert property (@(posedge clk) disable iff (!rst_n) !(cmd_m_oe && cmd_s_oe))
  else $error("EMD: host and device drive CMD together");
assert property (@(posedge clk) disable iff (!rst_n) !(dat0_m_oe && dat0_s_oe))
  else $error("EMD: host and device drive DAT0 together");
assert property (@(posedge clk) disable iff (!rst_n) !emmc_rst_n |-> !cmd_s_oe && !dat0_s_oe)
  else $error("EMD: device drives the bus in RST_n");
assert property (@(posedge clk) disable iff (!rst_n) $changed({cmd_s_oe, cmd_s, dat0_s_oe, dat0_s}) |-> !emmc_clk || !emmc_rst_n)
  else $error("EMD: device output changed while emmc_clk is high");
cover property (@(posedge clk) disable iff (!rst_n) dat0_s_oe && !dat0_s);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;      // a falling edge: the device has no clock to see a level reset
logic emmc_clk = 1'b1, emmc_rst_n = 1'b1, cmd_m = 1'b0, cmd_m_oe = 1'b0, dat0_m = 1'b0, dat0_m_oe = 1'b0;
wire cmd_s, cmd_s_oe, dat0_s, dat0_s_oe;

always #5 clk = ~clk;

emd_model u_dut (.clk(clk), .rst_n(rst_n), .emmc_clk(emmc_clk), .emmc_rst_n(emmc_rst_n), .cmd_m(cmd_m),
                 .cmd_m_oe(cmd_m_oe), .dat0_m(dat0_m), .dat0_m_oe(dat0_m_oe), .cmd_s(cmd_s), .cmd_s_oe(cmd_s_oe),
                 .dat0_s(dat0_s), .dat0_s_oe(dat0_s_oe));

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

logic cl, dl;
logic rn = 1'b1;
integer conflict = 0;
task automatic clk1(input logic co, input logic c, input logic doe, input logic d);
  @(negedge clk); emmc_clk = 0; emmc_rst_n = rn; cmd_m_oe = co; cmd_m = c; dat0_m_oe = doe; dat0_m = d;
  @(negedge clk);
  emmc_clk = 1;
  cl = co ? c : (cmd_s_oe ? cmd_s : 1'b1);
  dl = doe ? d : (dat0_s_oe ? dat0_s : 1'b1);
  if ((co && cmd_s_oe) || (doe && dat0_s_oe)) conflict = conflict + 1;
  @(negedge clk);
endtask
task automatic idle1(); clk1(0, 0, 0, 0); endtask
logic [135:0] r;
integer ncr;
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
  for (int j = 47; j >= 0; j--) clk1(1, f[j], 0, 0);
  got = 0; k = 0; r = 0;
  while (k < 64 && !got) begin idle1(); k = k + 1; if (!cl) got = 1; end
  ncr = k;
  if (got) for (int j = 1; j < len; j++) begin idle1(); r = {r[134:0], cl}; end
  repeat (trail) idle1();
endtask
function automatic logic r48_ok(input logic [5:0] i);
  r48_ok = r[46] == 1'b0 && r[45:40] == i && r[0] == 1'b1 && crc7({80'h0, 1'b0, r[46:8]}, 40) == r[7:1];
endfunction
integer busy, bk, tokk;
task automatic sel_busy();
  bk = 0;
  do begin idle1(); bk = bk + 1; end while (dl && bk < 16);
  busy = 0;
  while (!dl && busy < 64) begin busy = busy + 1; idle1(); end
  repeat (4) idle1();
endtask
logic [255:0] wb, rb;
logic [3:0] tok;
task automatic wr_blk(input logic bad = 0);
  logic [15:0] c;
  integer k;
  c = 16'h0;
  clk1(0, 0, 1, 1); clk1(0, 0, 1, 0);
  for (int n = 255; n >= 0; n--) begin c = crc16(c, wb[n]); clk1(0, 0, 1, wb[n]); end
  if (bad) c[7] = ~c[7];
  for (int n = 15; n >= 0; n--) clk1(0, 0, 1, c[n]);
  clk1(0, 0, 1, 1);
  k = 0;
  do begin idle1(); k = k + 1; end while (dl && k < 64);
  tokk = k;
  tok = {dl, 3'b000};
  for (int j = 2; j >= 0; j--) begin idle1(); tok[j] = dl; end
  idle1();
  busy = 0;
  if (dl) begin idle1(); while (!dl && busy < 64) begin busy = busy + 1; idle1(); end end
  repeat (4) idle1();
endtask
logic rd_ok;
task automatic rd_blk();
  logic [15:0] c, x;
  integer k;
  c = 16'h0; x = 16'h0;
  k = 0;
  do begin idle1(); k = k + 1; end while (dl && k < 64);
  for (int n = 255; n >= 0; n--) begin idle1(); rb[n] = dl; c = crc16(c, dl); end
  for (int n = 0; n < 16; n++) begin idle1(); x = {x[14:0], dl}; end
  idle1();
  rd_ok = k == 2 && dl && c == x;
  repeat (4) idle1();
endtask
function automatic logic [255:0] init_blk(input integer b);
  for (int i = 0; i < 32; i++) init_blk[255 - 8 * i -: 8] = (16 * b + i) ^ 8'hC3;
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(cmd_s_oe === 1'b0 && dat0_s_oe === 1'b0, "device off the bus in reset");
  rst_n = 1;
  repeat (4) idle1();
  cmd(6'd13, 32'h0001_0000); chk(!got, "CMD13 in idle: illegal, no response");
  cmd(6'd0, 32'h0); chk(!got, "CMD0: no response");
  cmd(6'd1, 32'h40FF_8080);
  chk(got && ncr == 2 && r[46] == 1'b0 && r[45:40] == 6'h3F && r[7:0] == 8'hFF && r[39:8] == 32'h40FF_8080,
      "CMD1: R3 after NCR = 2, busy, sector mode");
  cmd(6'd2, 32'h0, 136); chk(!got, "CMD2 in idle: illegal");
  cmd(6'd1, 32'h40FF_8080); chk(got && r[39:8] == 32'hC0FF_8080, "CMD1: ready");
  cmd(6'd1, 32'h40FF_8080); chk(!got, "CMD1 in ready: illegal");
  cmd(6'd2, 32'h0, 136);
  chk(got && ncr == 2 && r[133:128] == 6'h3F && r[0] && crc7(r[127:8], 120) == r[7:1] &&
      r[127:8] == 120'h150100454D4D43313600123456789A, "CMD2: R2 with the CID and its CRC7");
  cmd(6'd3, 32'h0); chk(!got, "CMD3 with RCA 0: illegal");
  cmd(6'd3, 32'h0001_0000);
  chk(got && ncr == 2 && r48_ok(6'd3) && r[39:8] == 32'h0040_0500, "CMD3: R1, ILLEGAL_COMMAND reported, ident");
  cmd(6'd3, 32'h0001_0000); chk(!got, "CMD3 in stby: illegal");
  cmd(6'd13, 32'h0001_0000, 48, 1); chk(!got, "bad CRC7: no response");
  cmd(6'd13, 32'h0001_0000);
  chk(got && ncr == 2 && r48_ok(6'd13) && r[39:8] == 32'h00C0_0700, "CMD13: COM_CRC_ERROR and ILLEGAL_COMMAND, stby");
  cmd(6'd13, 32'h0002_0000); chk(!got, "CMD13 to another RCA: no response");
  cmd(6'd7, 32'h0001_0000, 48, 0, 0);
  chk(got && ncr == 2 && r48_ok(6'd7) && r[39:8] == 32'h0000_0700, "CMD7: R1 from stby");
  sel_busy(); chk(bk == 2 && busy == 3, "CMD7: R1b busy, 3 clocks from 2 clocks after the end bit");
  cmd(6'd17, 32'd0, 48, 0, 0); rd_blk(); chk(rd_ok && rb == init_blk(0), "block 0 after reset");
  wb = 256'hDEADBEEF_01234567_89ABCDEF_FEDCBA98_76543210_A5A5A5A5_5A5A5A5A_00FF00FF;
  cmd(6'd24, 32'd2, 48, 0, 0); chk(got && ncr == 2 && r48_ok(6'd24) && r[39:8] == 32'h0000_0900, "CMD24: R1, tran state");
  wr_blk(); chk(tok == 4'b0010 && busy == 4 && tokk == 2, "block accepted: token 010 after 2 clocks, 4 clocks busy");
  cmd(6'd17, 32'd2, 48, 0, 0); rd_blk(); chk(rd_ok && rb == wb, "CMD17 reads the block back, NAC = 2, CRC16 good");
  cmd(6'd17, 32'd3, 48, 0, 0); rd_blk(); chk(rd_ok && rb == init_blk(3), "an untouched block");
  cmd(6'd24, 32'd3, 48, 0, 0); wr_blk(1); chk(tok == 4'b0101 && busy == 0, "bad CRC16: token 101, no busy");
  cmd(6'd17, 32'd3, 48, 0, 0); rd_blk(); chk(rb == init_blk(3), "and nothing written");
  cmd(6'd8, 32'h0); chk(!got, "CMD8: illegal");
  cmd(6'd13, 32'h0001_0000); chk(got && r[39:8] == 32'h0040_0900, "CMD13: ILLEGAL_COMMAND, tran");
  cmd(6'd7, 32'h0001_0000, 48, 0, 0); sel_busy(); chk(got && r[39:8] == 32'h0000_0900 && busy == 3, "CMD7 again in tran");
  rn = 0; repeat (2) idle1(); chk(cmd_s_oe === 1'b0 && dat0_s_oe === 1'b0, "RST_n: off the bus");
  repeat (2) idle1(); rn = 1; repeat (4) idle1();
  cmd(6'd13, 32'h0001_0000); chk(!got, "after RST_n: idle, CMD13 illegal");
  cmd(6'd0, 32'h0);
  cmd(6'd1, 32'h40FF_8080); chk(got && r[39:8] == 32'h40FF_8080, "after RST_n: busy again");
  cmd(6'd1, 32'h40FF_8080);
  cmd(6'd2, 32'h0, 136);
  cmd(6'd3, 32'h0006_0000); chk(got && r[39:8] == 32'h0040_0500, "flags cleared by RST_n, new ILLEGAL_COMMAND");
  cmd(6'd7, 32'h0006_0000, 48, 0, 0); sel_busy();
  cmd(6'd17, 32'd2, 48, 0, 0); rd_blk(); chk(rd_ok && rb == wb, "the block survives RST_n");
  cmd(6'd7, 32'h0007_0000); chk(!got, "CMD7 to another RCA: deselected, no response");
  cmd(6'd13, 32'h0006_0000); chk(got && r[39:8] == 32'h0000_0700, "CMD13: stby");
  cmd(6'd17, 32'd2); chk(!got, "CMD17 in stby: illegal");
  cmd(6'd0, 32'h0);
  cmd(6'd2, 32'h0, 136); chk(!got, "CMD0 resets: CMD2 illegal in idle");
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
