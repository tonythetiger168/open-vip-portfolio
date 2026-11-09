# SD / eMMC card VIP for a full SD / eMMC host (SDMMC_ADMA_top in
# open-ip-portfolio): 512-byte blocks (CMD16), 1 / 4 / 8-bit bus,
# single- and multiple-block transfers with CMD12, EXT_CSD, R1b busy. The
# emmc pin picks the personality (SD memory card or eMMC device).
#
# Agent -> DUT (host): sd_clk, emmc, the host's CMD drive cmd_m with
# cmd_m_oe, its DAT drive dat_m[7:0] with dat_m_oe. DUT -> agent (card):
# cmd_s / cmd_s_oe, dat_s[7:0] / dat_s_oe[7:0]. Undriven lines read 1
# (pull-ups). Both sides change their outputs on the sd_clk falling edge and
# sample on the rising edge.
#
# tb/top_tb.sv sdm_model is the card:
#   SD (emmc = 0): CMD0 -> idle. CMD8 in idle: R7 echo when VHS = 1. CMD55:
#   R1 with APP_CMD. ACMD41 in idle / ready: R3, busy for POLLS calls, then
#   ready with CCS = 1. CMD2 in ready: R2 CID -> ident. CMD3 in ident /
#   stby: R6 with RCA SD_RCA -> stby. ACMD6 in tran: bus width 1 / 4 (arg
#   0 / 2), R1.
#   eMMC (emmc = 1): CMD0 -> idle. CMD1 in idle: R3 (sector mode), busy for
#   POLLS calls, then ready. CMD2 in ready: R2 CID -> ident. CMD3 in ident
#   with a non-zero RCA: R1, RCA taken -> stby. CMD6 SWITCH in tran of
#   EXT_CSD[183] BUS_WIDTH to 0 / 1 / 2 (1 / 4 / 8 bits): R1b. CMD8 in tran:
#   R1, then EXT_CSD as one 512-byte read block.
#   Both: CMD7 with the RCA in stby / tran: R1b -> tran; another RCA
#   deselects (tran -> stby) silently. CMD13 with the RCA in stby or later:
#   R1. CMD16 in tran: block length 1..512. CMD17 / CMD18 / CMD24 / CMD25
#   in tran: R1; the block at argument A starts at byte A * blklen; reads
#   start NAC clocks after the response and after each block (start bit on
#   every line in use, data MSB first: DAT7..0 = a byte, DAT3..0 = a nibble,
#   DAT0 = a bit, a CRC16 per line, end bits); each write block gets the CRC
#   status token on DAT0 two clocks after its end bits (010, or 101 for a
#   CRC / end bit error, not written) and BUSY clocks of busy. CMD18 /
#   CMD25 run until CMD12 (R1b, the read stops at once). R1b busy is RBUSY
#   clocks from two clocks after the response. Bad CRC7 / end / transmission
#   bit: no response, COM_CRC_ERROR; a command not legal in the state: no
#   response, ILLEGAL_COMMAND; both show in the next R1 / R6. R1 status:
#   CURRENT_STATE when the command arrived (idle 0 .. tran 4, data 5, rcv 6),
#   READY_FOR_DATA, APP_CMD. Memory: NBLK * 512 bytes shared by both
#   personalities, byte i = i ^ (i >> 8) ^ 0xA5 after reset, addresses wrap.
# In a SoC bench the card connects to SDMMC_ADMA_top's cmd / dat (cmd_m <=
# cmd, cmd_m_oe <= 1, dat_m <= dat, dat_m_oe <= 1, and each line driven by
# the card where its enable is set; pull-ups); the agent runs passive and
# its monitor records every command, response and block.

SDM_FUNCS = """
function automatic bit [6:0] sdm_crc7(bit [119:0] d, int n);   // over d[n-1:0], MSB first
  bit [6:0] c = 0;
  for (int i = n - 1; i >= 0; i--) begin
    bit fb = d[i] ^ c[6];
    c = {c[5:0], 1'b0};
    if (fb) c ^= 7'h09;
  end
  return c;
endfunction
function automatic bit [15:0] sdm_crc16(bit [15:0] c, bit b);
  bit fb = b ^ c[15];
  return {c[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
endfunction
function automatic bit [47:0] sdm_frame(bit [5:0] i, bit [31:0] a, bit tx = 1'b1);
  bit [39:0] b = {1'b0, tx, i, a};
  return {b, sdm_crc7({80'h0, b}, 40), 1'b1};
endfunction
function automatic bit [7:0] sdm_init_byte(int i);
  return 8'(i ^ (i >> 8) ^ 8'hA5);
endfunction
// lines in use and clocks per byte for a bus-width code (0: 1, 1: 4, 2: 8 bits)
function automatic bit [7:0] sdm_mask(bit [1:0] w);
  return (w == 2) ? 8'hFF : (w == 1) ? 8'h0F : 8'h01;
endfunction
function automatic int sdm_cpb(bit [1:0] w);
  return (w == 2) ? 1 : (w == 1) ? 2 : 8;
endfunction
// the lines' values for clock s (0 .. cpb - 1) of byte b
function automatic bit [7:0] sdm_lines(bit [1:0] w, bit [7:0] b, int s);
  if (w == 2) return b;
  if (w == 1) return {4'hF, (s == 0) ? b[7:4] : b[3:0]};
  return {7'h7F, b[7 - s]};
endfunction
localparam bit [119:0] SDM_CID_SD   = 120'h1D4F5653444D43311012345678016A;
localparam bit [119:0] SDM_CID_EMMC = 120'h150100454D4D4344361087654321A8;
"""

SPEC = dict(
    vip="SDMMC_Card-UVM-VIP", p="sdm", P="SDM", dir="sdm", family="Storage",
    desc="SD / eMMC card VIP for a full SD/eMMC host: SD and eMMC personalities, 512-byte blocks with CMD16, 1 / 4 / "
         "8-bit bus (ACMD6, CMD6 SWITCH), single and multiple block reads and writes with CMD12, EXT_CSD, R1 / R1b / "
         "R2 / R3 / R6 / R7, CRC7, CRC16 per line, CRC status token and busy; host agent and bus monitor "
         "(SDMMC_ADMA_top pins).",
    about="""
An IP camera records to an SD card or an eMMC device through the SoC's
SD/eMMC host with its ADMA2 engine. The VIP's DUT model is that card, in
either personality, made to pair with SDMMC_ADMA_top in open-ip-portfolio
(512-byte blocks, CMD16, 1 / 4 / 8-bit data, multiple-block transfers), so
a SoC bench can hang it on the host's pins. The agent is a host that walks
both personalities through identification (CMD0, CMD8, CMD55 / ACMD41 or
CMD1 polls, CMD2, CMD3, CMD7 with its R1b busy), bus-width changes (ACMD6,
CMD6 SWITCH, EXT_CSD read-back), block-length changes (CMD16) and data
transfers (CMD17 / CMD18 / CMD24 / CMD25 with CMD12, good and corrupted
block CRCs, a read stopped in the middle of a block), and sends commands
with a bad CRC7 and commands illegal in the state. The scoreboard runs its
own copy of the card on the monitored host bits and predicts the card's CMD
and DAT drive at every sd_clk rising edge: response timing, every response
bit and CRC7, the CIDs, read data and per-line CRC16s in every width, the
CRC status token and the busy times.""",
    defs=SDM_FUNCS,
    timeout=200000,
    cfg="""int unsigned half = 1;     // clocks per sd_clk half period
int unsigned gap  = 16;    // clocks with sd_clk stopped between items""",
    ports=[
        ("in", "logic", "sd_clk"), ("in", "logic", "emmc"), ("in", "logic", "cmd_m"), ("in", "logic", "cmd_m_oe"),
        ("in", "logic [7:0]", "dat_m"), ("in", "logic", "dat_m_oe"),
        ("out", "logic", "cmd_s"), ("out", "logic", "cmd_s_oe"),
        ("out", "logic [7:0]", "dat_s"), ("out", "logic [7:0]", "dat_s_oe"),
    ],
    fields=[
        ("bit [11:0]", "mo", "req", "q"),       # {emmc, cmd_m_oe, cmd_m, dat_m_oe, dat_m} per sd_clk rise (masked)
        ("bit [17:0]", "so", "rsp", "q"),       # {cmd_s_oe, cmd_s, dat_s_oe, dat_s} per sd_clk rise (masked)
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [3:0]", "blk", "info", "rand"),
        ("bit [1:0]", "cnt", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [5:0]", "idx", "info"),
        ("bit [31:0]", "arg", "info"),
        ("bit", "got", "info"),
    ],
    tr_functions="""
// kind: 0 CMD0, 1 CMD8 (SD: VHS 1, eMMC: SEND_EXT_CSD), 2 CMD55, 3 ACMD41
// (HCS), 4 CMD1, 5 CMD2, 6 CMD3 (eMMC: RCA 1 + blk), 7 CMD7 (RCA), 8 CMD7
// (other RCA), 9 CMD13, 10 ACMD6 (seed[0]: 4-bit), 11 CMD6 SWITCH bus width
// seed % 3, 12 CMD16 (64 << seed[1:0] bytes, seed[2]: 512), 13 CMD17, 14
// CMD18 + CMD12 (cnt + 1 blocks), 15 CMD24, 16 CMD25 + CMD12, 17 CMD24 with
// a bad CRC16, 18 CMD13 with a bad CRC7, 19 CMD12 alone, 20 CMD18 stopped
// in its first block, 21 personality switch (no command), 22-31 CMD17 /
// CMD24 / CMD13 / CMD18 mix
function void set(int k, int b = 0, int n = 0, bit [31:0] s = 32'h1); kind = k; blk = b; cnt = n; seed = s; endfunction
function int kk();
  if (kind >= 22) return (kind % 4 == 0) ? 13 : (kind % 4 == 1) ? 15 : (kind % 4 == 2) ? 9 : 14;
  return kind;
endfunction
function int nblocks();
  return int'(cnt) + 1;
endfunction
function bit [47:0] cmd(bit [15:0] rca, bit em);
  case (kk())
    0: begin idx = 0; arg = 0; end
    1: begin idx = 8; arg = em ? 32'h0 : 32'h0000_01AA; end
    2: begin idx = 55; arg = {rca, 16'h0}; end
    3: begin idx = 41; arg = 32'h40FF_8000; end
    4: begin idx = 1; arg = 32'h40FF_8080; end
    5: begin idx = 2; arg = 0; end
    6: begin idx = 3; arg = em ? {16'h1 + 16'(blk), 16'h0} : 32'h0; end
    7: begin idx = 7; arg = {rca, 16'h0}; end
    8: begin idx = 7; arg = {rca ^ 16'h0101, 16'h0}; end
    9, 18: begin idx = 13; arg = {rca, 16'h0}; end
    10: begin idx = 6; arg = seed[0] ? 32'h2 : 32'h0; end
    11: begin idx = 6; arg = {6'h0, 2'b11, 8'd183, 8'(seed % 3), 8'h0}; end
    12: begin idx = 16; arg = seed[2] ? 32'd512 : (32'd64 << seed[1:0]); end
    13: begin idx = 17; arg = {28'h0, blk}; end
    14, 20: begin idx = 18; arg = {28'h0, blk}; end
    15, 17: begin idx = 24; arg = {28'h0, blk}; end
    16: begin idx = 25; arg = {28'h0, blk}; end
    19: begin idx = 12; arg = 0; end
    default: begin idx = 63; arg = 0; end
  endcase
  if (kk() == 18) return sdm_frame(idx, arg) ^ 48'h4;
  return sdm_frame(idx, arg);
endfunction
function bit [7:0] wbyte(int blkno, int i);
  bit [31:0] x = (seed | 1) ^ (32'(blkno) * 32'h9E37_79B9) ^ (32'(i) * 32'h85EB_CA6B);
  x ^= x >> 15; x *= 32'h2C1B_3C6D; x ^= x >> 12;
  return x[7:0];
endfunction
function bit bad_crc(); return kk() == 17; endfunction
""",
    drv_rsp=False,
    drv_members="""bit [15:0]      rca = 0;
bit             em = 0;
bit [1:0]       w = 0;
int             blklen = 512;
sdm_transaction cur;""",
    drv_tasks="""
// one sd_clk period: outputs at the falling edge, the lines at the rising edge
task automatic clk1(bit co, bit c, bit doe, bit [7:0] d, output bit cl, output bit [7:0] dl);
  vif.drv_cb.sd_clk   <= 1'b0;
  vif.drv_cb.emmc     <= em;
  vif.drv_cb.cmd_m_oe <= co; vif.drv_cb.cmd_m <= c;
  vif.drv_cb.dat_m_oe <= doe; vif.drv_cb.dat_m <= d;
  repeat (cfg.half) @(vif.drv_cb);
  vif.drv_cb.sd_clk <= 1'b1;
  cl = co ? c : (vif.drv_cb.cmd_s_oe ? vif.drv_cb.cmd_s : 1'b1);
  for (int i = 0; i < 8; i++) dl[i] = doe ? d[i] : (vif.drv_cb.dat_s_oe[i] ? vif.drv_cb.dat_s[i] : 1'b1);
  cur.mo.push_back({em, co, c & co, doe, d & {8{doe}}});
  repeat (cfg.half) @(vif.drv_cb);
endtask
task automatic idle1(output bit cl, output bit [7:0] dl);
  clk1(1'b0, 1'b0, 1'b0, 8'h0, cl, dl);
endtask
// a command and its response (hunted for 64 clocks); got / r
task automatic command(bit [47:0] f, int len, output bit got, output bit [135:0] r);
  bit cl;
  bit [7:0] dl;
  int k = 0;
  got = 0; r = 0;
  repeat (2) idle1(cl, dl);
  for (int i = 47; i >= 0; i--) clk1(1'b1, f[i], 1'b0, 8'h0, cl, dl);
  while (k < 64 && !got) begin idle1(cl, dl); if (!cl) got = 1; k++; end
  if (got) for (int i = 1; i < len; i++) begin idle1(cl, dl); r = {r[134:0], cl}; end
endtask
// wait out DAT0 busy: up to 8 clocks for it to start, 512 for it to end
task automatic busy_wait();
  bit cl;
  bit [7:0] dl;
  int k = 0;
  do begin idle1(cl, dl); k++; end while (dl[0] && k < 8);
  k = 0;
  while (!dl[0] && k < 512) begin idle1(cl, dl); k++; end
endtask
task automatic read_blk(int n);
  bit cl;
  bit [7:0] dl;
  int k = 0;
  do begin idle1(cl, dl); k++; end while (dl[0] && k < 64);
  if (!dl[0]) repeat (n * sdm_cpb(w) + 16 + 1) idle1(cl, dl);
endtask
task automatic write_blk(sdm_transaction t, int b);
  bit cl;
  bit [7:0] dl, m = sdm_mask(w), v;
  bit [15:0] c [8] = '{0, 0, 0, 0, 0, 0, 0, 0};
  int k;
  idle1(cl, dl); idle1(cl, dl);
  clk1(1'b0, 1'b0, 1'b1, 8'hFF, cl, dl);
  clk1(1'b0, 1'b0, 1'b1, ~m, cl, dl);
  for (int i = 0; i < blklen; i++)
    for (int s = 0; s < sdm_cpb(w); s++) begin
      v = sdm_lines(w, t.wbyte(b, i), s);
      for (int l = 0; l < 8; l++) if (m[l]) c[l] = sdm_crc16(c[l], v[l]);
      clk1(1'b0, 1'b0, 1'b1, v, cl, dl);
    end
  if (t.bad_crc()) c[0][t.seed[3:0]] ^= 1'b1;
  for (int n = 15; n >= 0; n--) begin
    for (int l = 0; l < 8; l++) v[l] = m[l] ? c[l][n] : 1'b1;
    clk1(1'b0, 1'b0, 1'b1, v, cl, dl);
  end
  clk1(1'b0, 1'b0, 1'b1, 8'hFF, cl, dl);
  k = 0;
  do begin idle1(cl, dl); k++; end while (dl[0] && k < 64);
  if (!dl[0]) begin
    repeat (4) idle1(cl, dl);
    k = 0;
    do begin idle1(cl, dl); k++; end while (!dl[0] && k < 512);
  end
endtask
""",
    drv_desc="one item per command with sd_clk running: the 48-bit command, a response hunt of up to 64 clocks and the response; R1b busy waits; CMD17 / CMD8 EXT_CSD read blocks, CMD24 write blocks with token and busy, and for CMD18 / CMD25 cnt + 1 blocks followed by CMD12 and its busy (kind 20 sends CMD12 in the middle of the first block); a personality item flips emmc; then 8 idle clocks and sd_clk stopped for cfg.gap clocks",
    drv_idle="""
vif.drv_cb.sd_clk   <= 1'b1;
vif.drv_cb.emmc     <= 1'b0;
vif.drv_cb.cmd_m    <= 1'b0;
vif.drv_cb.cmd_m_oe <= 1'b0;
vif.drv_cb.dat_m    <= 8'h0;
vif.drv_cb.dat_m_oe <= 1'b0;
""",
    drv_item="""
bit cl, g12;
bit [7:0] dl;
bit [47:0] f;
bit [135:0] r, r12;
cur = t;
t.mo.delete();
f = t.cmd(rca, em);
t.got = 0;
@(vif.drv_cb);
repeat (4) idle1(cl, dl);
if (t.idx == 63) begin
  em = ~em;
  repeat (4) idle1(cl, dl);
end else begin
  command(f, (t.idx == 2) ? 136 : 48, t.got, r);
  if (t.idx == 0) begin rca = 0; w = 0; blklen = 512; end
  if (t.got) begin
    if (t.idx == 3) rca = em ? t.arg[31:16] : r[39:24];
    if (t.idx == 6 && !em) w = t.arg[1] ? 2'd1 : 2'd0;
    if (t.idx == 6 && em) w = t.arg[9:8];
    if (t.idx == 16) blklen = int'(t.arg);
    if (t.idx == 7 || t.idx == 12 || (t.idx == 6 && em)) busy_wait();
    if (t.idx == 8 && em) read_blk(512);
    if (t.idx == 17) read_blk(blklen);
    if (t.idx == 24) write_blk(t, 0);
    if (t.idx == 18 && t.kk() == 20) begin
      int k = 0;
      do begin idle1(cl, dl); k++; end while (dl[0] && k < 64);
      repeat (8) idle1(cl, dl);
      command(sdm_frame(6'd12, 32'h0), 48, g12, r12);
      if (g12) busy_wait();
    end else if (t.idx == 18) begin
      for (int b = 0; b < t.nblocks(); b++) read_blk(blklen);
      command(sdm_frame(6'd12, 32'h0), 48, g12, r12);
      if (g12) busy_wait();
    end
    if (t.idx == 25) begin
      for (int b = 0; b < t.nblocks(); b++) write_blk(t, b);
      command(sdm_frame(6'd12, 32'h0), 48, g12, r12);
      if (g12) busy_wait();
    end
  end
end
repeat (8) idle1(cl, dl);
repeat (cfg.gap) @(vif.drv_cb);
""",
    mon_desc="host and card drive (masked by their enables) and the emmc pin at every sd_clk rising edge; sd_clk stopped for more than half of cfg.gap clocks ends the item",
    mon_run="""
forever begin
  sdm_transaction t;
  bit pc;
  int q = 0;
  pc = vif.mon_cb.sd_clk;
  @(vif.mon_cb);
  while (!(pc === 1'b0 && vif.mon_cb.sd_clk === 1'b1)) begin pc = vif.mon_cb.sd_clk; @(vif.mon_cb); end
  t = sdm_transaction::type_id::create("t");
  forever begin
    if (pc === 1'b0 && vif.mon_cb.sd_clk === 1'b1) begin
      t.mo.push_back({vif.mon_cb.emmc, vif.mon_cb.cmd_m_oe, vif.mon_cb.cmd_m & vif.mon_cb.cmd_m_oe,
                      vif.mon_cb.dat_m_oe, vif.mon_cb.dat_m & {8{vif.mon_cb.dat_m_oe}}});
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
localparam int NBLK = 8, MEMB = NBLK * 512, NCR = 2, NAC = 2, BUSY = 4, RBUSY = 3, POLLS = 2;
localparam bit [15:0] SD_RCA = 16'hB37A;
bit [7:0]   mem [MEMB];
bit [7:0]   wbuf [512];
bit         minit = 0;
int         cst = 0, polls = 0, dm = 0, rdd = 0, tokd = 0, tokn = 0, busyn = 0, dcnt = 0, blklen = 512, baddr = 0;
bit         app = 0, crc_e = 0, ill = 0, multi = 0, xcsd = 0;
bit [1:0]   w = 0;
bit [15:0]  rca = 0;
int         rxc = 0, txd = 0, txn = 0;
bit [47:0]  rxs = 0;
bit [135:0] txs = 0;
bit [15:0]  c [8], rc [8];
bit [7:0]   acc = 0;
bit [4:0]   tok = 0;
bit         o_cmd = 0, o_cmd_oe = 0;
bit [7:0]   o_dat = 0, o_dat_oe = 0;

function bit [7:0] ext(int i);
  case (i)
    183: return {6'h0, w};
    192: return 8'h08;
    196: return 8'h07;
    212: return 8'(NBLK);
    default: return 8'h00;
  endcase
endfunction
function bit [7:0] rbyte(int i);
  return xcsd ? ext(i) : mem[(baddr + i) % MEMB];
endfunction
function int nclk();
  return (xcsd ? 512 : blklen) * sdm_cpb(w);
endfunction
function void send(bit [135:0] fr, int n);
  txs = fr; txn = n; txd = NCR - 1;
endfunction
function void r1(bit [5:0] i, int st, bit ap);
  send({sdm_frame(i, {8'h00, crc_e, ill, 9'h000, 4'(st), 1'b1, 2'b00, ap, 5'h00}, 1'b0), 88'h0}, 48);
  crc_e = 0; ill = 0;
endfunction
function void frame(bit [47:0] f, bit em);
  bit [5:0] i = f[45:40];
  bit [31:0] a = f[39:8];
  int st = cst;
  bit wa = app;
  if (sdm_crc7({80'h0, f[47:8]}, 40) != f[7:1] || !f[0] || !f[46]) begin crc_e = 1; return; end
  app = 0;
  if (i == 0) begin cst = 0; polls = 0; rca = 0; w = 0; blklen = 512; dm = 0; multi = 0; end
  else if (!em && i == 8 && cst == 0) begin
    if (a[11:8] == 4'h1) send({sdm_frame(6'd8, {20'h0, a[11:0]}, 1'b0), 88'h0}, 48);
  end else if (em && i == 8 && cst == 4) begin
    r1(i, st, 1'b0); xcsd = 1; multi = 0; baddr = 0; dm = 7; cst = 5;
  end else if (!em && i == 55 && cst != 2 && cst <= 4) begin
    app = 1; r1(i, st, 1'b1);
  end else if (!em && i == 41 && wa && cst <= 1) begin
    bit rdy = polls >= POLLS;
    if (polls != 15) polls++;
    if (rdy) cst = 1;
    send({2'b00, 6'h3F, rdy, rdy, 6'h00, 24'hFF8000, 8'hFF, 88'h0}, 48);
  end else if (em && i == 1 && cst == 0) begin
    bit rdy = polls >= POLLS;
    if (polls != 15) polls++;
    if (rdy) cst = 1;
    send({2'b00, 6'h3F, rdy, 2'b10, 29'h00FF_8080, 8'hFF, 88'h0}, 48);
  end else if (i == 2 && cst == 1) begin
    bit [119:0] body = em ? SDM_CID_EMMC : SDM_CID_SD;
    cst = 2; send({2'b00, 6'h3F, body, sdm_crc7(body, 120), 1'b1}, 136);
  end else if (!em && i == 3 && (cst == 2 || cst == 3)) begin
    cst = 3; rca = SD_RCA;
    send({sdm_frame(6'd3, {SD_RCA, crc_e, ill, 2'b00, 3'(st), 1'b1, 2'b00, 1'b0, 5'h00}, 1'b0), 88'h0}, 48);
    crc_e = 0; ill = 0;
  end else if (em && i == 3 && cst == 2 && a[31:16] != 0) begin
    cst = 3; rca = a[31:16]; r1(i, st, 1'b0);
  end else if (i == 7 && (cst == 3 || cst == 4)) begin
    if (a[31:16] == rca) begin cst = 4; r1(i, st, 1'b0); dm = 6; end
    else if (cst == 4) cst = 3;
  end else if (i == 13 && cst >= 3) begin
    if (a[31:16] == rca) r1(i, st, 1'b0);
  end else if (!em && i == 6 && wa && cst == 4 && a[0] == 1'b0) begin
    w = a[1] ? 2'd1 : 2'd0; r1(i, st, 1'b1);
  end else if (em && i == 6 && cst == 4 && a[25:24] == 2'b11 && a[23:16] == 8'd183 && a[15:8] <= 2) begin
    w = a[9:8]; r1(i, st, 1'b0); dm = 6;
  end else if (i == 16 && cst == 4 && a != 0 && a <= 512) begin
    blklen = int'(a); r1(i, st, 1'b0);
  end else if ((i == 17 || i == 18 || i == 24 || i == 25) && cst == 4) begin
    r1(i, st, 1'b0);
    baddr = int'((a * blklen) % MEMB); multi = (i == 18 || i == 25); xcsd = 0;
    if (i == 17 || i == 18) begin dm = 7; cst = 5; end
    else begin dm = 1; cst = 6; end
  end else if (i == 12 && (cst == 5 || cst == 6)) begin
    r1(i, st, 1'b0); dm = 6; cst = 4; multi = 0; xcsd = 0;
  end else ill = 1;
endfunction
""",
    predict="""
if (!minit) begin for (int i = 0; i < MEMB; i++) mem[i] = sdm_init_byte(i); minit = 1; end
t.so.delete();
foreach (t.mo[i]) begin
  bit cl, em;
  bit [7:0] dl, m;
  em = t.mo[i][11];
  t.so.push_back({o_cmd_oe, o_cmd & o_cmd_oe, o_dat_oe, o_dat & o_dat_oe});
  cl = t.mo[i][10] ? t.mo[i][9] : (o_cmd_oe ? o_cmd : 1'b1);
  for (int l = 0; l < 8; l++) dl[l] = t.mo[i][8] ? t.mo[i][l] : (o_dat_oe[l] ? o_dat[l] : 1'b1);
  m = sdm_mask(w);
  // command receiver (not while a response goes out)
  if (txd == 0 && txn == 0) begin
    if (rxc == 0) begin if (!cl) begin rxc = 1; rxs = 0; end end
    else begin
      rxs = {rxs[46:0], cl}; rxc++;
      if (rxc == 48) begin rxc = 0; frame(rxs, em); m = sdm_mask(w); end
    end
  end
  // write block receiver
  case (dm)
    1: if (!dl[0]) begin dm = 2; dcnt = 0; c = '{0, 0, 0, 0, 0, 0, 0, 0}; end
    2: begin
         int s = dcnt % sdm_cpb(w), bi = dcnt / sdm_cpb(w);
         if (w == 2) wbuf[bi] = dl;
         else if (w == 1) begin if (s == 0) acc[7:4] = dl[3:0]; else wbuf[bi] = {acc[7:4], dl[3:0]}; end
         else begin acc = {acc[6:0], dl[0]}; if (s == 7) wbuf[bi] = acc; end
         for (int l = 0; l < 8; l++) if (m[l]) c[l] = sdm_crc16(c[l], dl[l]);
         if (++dcnt == nclk()) begin dm = 3; dcnt = 0; rc = '{0, 0, 0, 0, 0, 0, 0, 0}; end
       end
    3: begin
         for (int l = 0; l < 8; l++) if (m[l]) rc[l] = {rc[l][14:0], dl[l]};
         if (++dcnt == 16) dm = 4;
       end
    4: begin
         bit good = (dl & m) == m && rc == c;
         if (good) for (int k = 0; k < blklen; k++) mem[(baddr + k) % MEMB] = wbuf[k];
         tok = good ? 5'b0_010_1 : 5'b0_101_1;
         dm = 5; tokd = 1; tokn = 5; busyn = good ? BUSY : 0;
         baddr = (baddr + blklen) % MEMB;
       end
    default: ;
  endcase
  // outputs for the next period
  if (txd > 0) begin txd--; o_cmd_oe = 0; end
  else if (txn > 0) begin
    o_cmd_oe = 1; o_cmd = txs[135]; txs = txs << 1; txn--;
    if (txn == 0 && dm == 7) begin dm = 8; rdd = NAC; end
    if (txn == 0 && dm == 6) begin dm = 5; tokd = 2; tokn = 0; busyn = RBUSY; end
  end else o_cmd_oe = 0;
  case (dm)
    5: if (tokd > 0) begin tokd--; o_dat_oe = 0; end
       else if (tokn > 0) begin o_dat_oe = 8'h01; o_dat[0] = tok[4]; tok = tok << 1; tokn--; end
       else if (busyn > 0) begin o_dat_oe = 8'h01; o_dat[0] = 1'b0; busyn--; end
       else begin
         o_dat_oe = 0;
         if (cst == 6 && multi) dm = 1;
         else begin dm = 0; if (cst == 6) cst = 4; end
       end
    8: if (rdd > 0) begin rdd--; o_dat_oe = 0; end
       else begin o_dat_oe = m; o_dat = 8'h00; dm = 9; dcnt = 0; c = '{0, 0, 0, 0, 0, 0, 0, 0}; end
    9: begin
         bit [7:0] v = sdm_lines(w, rbyte(dcnt / sdm_cpb(w)), dcnt % sdm_cpb(w));
         o_dat_oe = m; o_dat = v & m;
         for (int l = 0; l < 8; l++) if (m[l]) c[l] = sdm_crc16(c[l], v[l]);
         if (++dcnt == nclk()) begin dm = 10; dcnt = 0; end
       end
    10: begin
          o_dat_oe = m;
          for (int l = 0; l < 8; l++) begin o_dat[l] = m[l] & c[l][15]; c[l] = c[l] << 1; end
          if (++dcnt == 16) dm = 11;
        end
    11: begin
          o_dat_oe = m; o_dat = m;
          if (multi) begin baddr = (baddr + blklen) % MEMB; rdd = NAC; dm = 8; end
          else dm = 12;
        end
    12: begin o_dat_oe = 0; dm = 0; cst = 4; xcsd = 0; end
    default: o_dat_oe = 0;
  endcase
end
""",
    checks="""
foreach (t.so[i]) begin
  if (t.so[i][17] && t.mo[i][10]) fail(t, "host and card drive CMD together");
  if (t.so[i][15:8] != 0 && t.mo[i][8]) fail(t, "host and card drive DAT together");
end
""",
    coverage="""
cp_idx  : coverpoint tr.idx { bins c0 = {0}; bins c1 = {1}; bins c2 = {2}; bins c3 = {3}; bins c6 = {6}; bins c7 = {7};
                              bins c8 = {8}; bins c12 = {12}; bins c13 = {13}; bins c16 = {16}; bins c17 = {17};
                              bins c18 = {18}; bins c24 = {24}; bins c25 = {25}; bins c41 = {41}; bins c55 = {55};
                              bins sw = {63}; }
cp_got  : coverpoint tr.got;
cp_len  : coverpoint tr.mo.size() { bins sw = {[1:40]}; bins cmd = {[100:260]}; bins blk = {[261:1500]};
                                    bins blk1 = {[1501:20000]}; }
""",
    directed="""
// SD in 1 and 4 bits, then eMMC in 1, 4 and 8 bits, with every error path
t = item(); t.set(9); send(t);              // illegal in idle
t = item(); t.set(0); send(t);
t = item(); t.set(1); send(t);              // R7
t = item(); t.set(3); send(t);              // ACMD41 without CMD55: illegal
for (int p = 0; p < 3; p++) begin t = item(); t.set(2); send(t); t = item(); t.set(3); send(t); end
t = item(); t.set(5); send(t);
t = item(); t.set(6); send(t);              // R6
t = item(); t.set(18); send(t);             // bad CRC7
t = item(); t.set(9); send(t);
t = item(); t.set(7); send(t);              // R1b
t = item(); t.set(13, 1); send(t);
t = item(); t.set(15, 1, 0, 32'h11); send(t);
t = item(); t.set(13, 1); send(t);
t = item(); t.set(2); send(t); t = item(); t.set(10, 0, 0, 32'h1); send(t);   // 4-bit
t = item(); t.set(16, 2, 1, 32'h22); send(t);
t = item(); t.set(14, 2, 1); send(t);
t = item(); t.set(17, 4, 0, 32'h33); send(t);
t = item(); t.set(13, 4); send(t);
t = item(); t.set(12, 0, 0, 32'h0); send(t); // 64-byte blocks
t = item(); t.set(15, 3, 0, 32'h44); send(t);
t = item(); t.set(14, 3, 2); send(t);
t = item(); t.set(20, 1); send(t);          // stopped mid-block
t = item(); t.set(19); send(t);             // CMD12 in tran: illegal
t = item(); t.set(9); send(t);
t = item(); t.set(8); send(t);              // deselect
t = item(); t.set(13); send(t);             // illegal in stby
t = item(); t.set(7); send(t);
t = item(); t.set(21); send(t);             // eMMC
t = item(); t.set(0); send(t);
for (int p = 0; p < 3; p++) begin t = item(); t.set(4); send(t); end
t = item(); t.set(5); send(t);
t = item(); t.set(6, 4); send(t);
t = item(); t.set(7); send(t);
t = item(); t.set(1); send(t);              // EXT_CSD, 1 bit
t = item(); t.set(11, 0, 0, 32'd2); send(t); // 8-bit
t = item(); t.set(1); send(t);
t = item(); t.set(13, 2); send(t);
t = item(); t.set(16, 5, 1, 32'h55); send(t);
t = item(); t.set(14, 5, 1); send(t);
t = item(); t.set(11, 0, 0, 32'd1); send(t); // 4-bit
t = item(); t.set(12, 0, 0, 32'h1); send(t); // 128-byte blocks
t = item(); t.set(15, 6, 0, 32'h66); send(t);
t = item(); t.set(13, 6); send(t);
t = item(); t.set(10); send(t);             // ACMD6 means nothing to eMMC
t = item(); t.set(2); send(t);              // nor CMD55
t = item(); t.set(9); send(t);
t = item(); t.set(0); send(t);              // CMD0 from tran
t = item(); t.set(13, 1); send(t);
""",
    drain_ns=20000,
    model="""
module sdm_model #(
  parameter int          NBLK   = 8,
  parameter int          NCR    = 2,
  parameter int          NAC    = 2,
  parameter int          BUSY   = 4,
  parameter int          RBUSY  = 3,
  parameter int          POLLS  = 2,
  parameter logic [15:0] SD_RCA = 16'hB37A
) (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       sd_clk,
  input  logic       emmc,
  input  logic       cmd_m,
  input  logic       cmd_m_oe,
  input  logic [7:0] dat_m,
  input  logic       dat_m_oe,
  output logic       cmd_s,
  output logic       cmd_s_oe,
  output logic [7:0] dat_s,
  output logic [7:0] dat_s_oe
);
  localparam int MEMB = NBLK * 512;
  localparam logic [119:0] CID_SD   = 120'h1D4F5653444D43311012345678016A;
  localparam logic [119:0] CID_EMMC = 120'h150100454D4D4344361087654321A8;
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
  // 8 CRC16s side by side, updated on the lines of mask m
  function automatic logic [127:0] crc8(input logic [127:0] c, input logic [7:0] v, input logic [7:0] m);
    for (int l = 0; l < 8; l++) if (m[l]) crc8[16 * l +: 16] = crc16(c[16 * l +: 16], v[l]);
    else crc8[16 * l +: 16] = c[16 * l +: 16];
  endfunction
  function automatic logic [47:0] frame(input logic [5:0] i, input logic [31:0] a);
    logic [39:0] b;
    b = {2'b00, i, a};
    frame = {b, crc7({80'h0, b}, 40), 1'b1};
  endfunction
  function automatic logic [7:0] mask(input logic [1:0] w);
    mask = (w == 2'd2) ? 8'hFF : (w == 2'd1) ? 8'h0F : 8'h01;
  endfunction
  function automatic logic [3:0] cpb(input logic [1:0] w);   // clocks per byte
    cpb = (w == 2'd2) ? 4'd1 : (w == 2'd1) ? 4'd2 : 4'd8;
  endfunction
  function automatic logic [7:0] lines(input logic [1:0] w, input logic [7:0] b, input logic [2:0] s);
    if (w == 2'd2) lines = b;
    else if (w == 2'd1) lines = {4'hF, (s == 3'd0) ? b[7:4] : b[3:0]};
    else lines = {7'h7F, b[3'd7 - s]};
  endfunction

  logic [7:0]   mem [0:MEMB-1];
  logic [7:0]   wbuf [0:511];
  logic [2:0]   cst;
  logic [3:0]   polls, dm;
  logic         app, crc_e, ill, multi, xcsd;
  logic [1:0]   w;
  logic [9:0]   blklen;
  logic [15:0]  rca;
  logic [5:0]   rxc;
  logic [47:0]  rxs;
  logic [7:0]   txn;
  logic [6:0]   txd;
  logic [135:0] txs;
  logic [12:0]  dcnt;
  logic [31:0]  baddr;
  logic [127:0] crc, rcrc;
  logic [7:0]   acc;
  logic [6:0]   rdd, tokd;
  logic [2:0]   tokn;
  logic [4:0]   tok;
  logic [7:0]   busyn;
  logic         n_cmd, n_cmd_oe;
  logic [7:0]   n_dat, n_dat_oe;
  wire          cl = cmd_m_oe ? cmd_m : (cmd_s_oe ? cmd_s : 1'b1);
  wire  [7:0]   dl = dat_m_oe ? dat_m : ((dat_s_oe & dat_s) | ~dat_s_oe);
  wire          _unused = &{1'b0, clk};

  function automatic logic [7:0] ext(input logic [8:0] i, input logic [1:0] wv);
    case (i)
      9'd183: ext = {6'h0, wv};
      9'd192: ext = 8'h08;
      9'd196: ext = 8'h07;
      9'd212: ext = 8'(NBLK);
      default: ext = 8'h00;
    endcase
  endfunction

  // rising sd_clk: receive, run the card, decide the next outputs
  always_ff @(posedge sd_clk or negedge rst_n) begin
    if (!rst_n) begin
      cst <= '0; polls <= '0; dm <= D_NONE; app <= 1'b0; crc_e <= 1'b0; ill <= 1'b0; multi <= 1'b0; xcsd <= 1'b0;
      w <= '0; blklen <= 10'd512; rca <= '0; rxc <= '0; rxs <= '0; txn <= '0; txd <= '0; txs <= '0;
      dcnt <= '0; baddr <= '0; crc <= '0; rcrc <= '0; acc <= '0; rdd <= '0; tokd <= '0; tokn <= '0; tok <= '0;
      busyn <= '0; n_cmd <= 1'b0; n_cmd_oe <= 1'b0; n_dat <= 8'h0; n_dat_oe <= 8'h0;
      for (int k = 0; k < MEMB; k++) mem[k] <= 8'(k ^ (k >> 8) ^ 8'hA5);
    end else begin : step
      logic [2:0]   v_cst, st;
      logic [3:0]   v_polls, v_dm;
      logic         v_app, v_crc_e, v_ill, v_multi, v_xcsd;
      logic [1:0]   v_w;
      logic [9:0]   v_blklen;
      logic [15:0]  v_rca;
      logic [5:0]   v_rxc;
      logic [47:0]  v_rxs, f;
      logic [7:0]   v_txn;
      logic [6:0]   v_txd;
      logic [135:0] v_txs;
      logic [12:0]  v_dcnt, nclk;
      logic [31:0]  v_baddr;
      logic [127:0] v_crc, v_rcrc;
      logic [7:0]   v_acc;
      logic [6:0]   v_rdd, v_tokd;
      logic [2:0]   v_tokn;
      logic [4:0]   v_tok;
      logic [7:0]   v_busyn;
      logic [7:0]   m, v, b;
      logic [3:0]   s;
      logic [12:0]  bi;
      logic         go, good, wa, rdy, ok1, ap, rb;
      logic [5:0]   i;
      logic [31:0]  a;
      logic [119:0] body;
      v_cst = cst; v_polls = polls; v_dm = dm; v_app = app; v_crc_e = crc_e; v_ill = ill; v_multi = multi;
      v_xcsd = xcsd; v_w = w; v_blklen = blklen; v_rca = rca; v_rxc = rxc; v_rxs = rxs; v_txn = txn;
      v_txd = txd; v_txs = txs; v_dcnt = dcnt; v_baddr = baddr; v_crc = crc; v_rcrc = rcrc; v_acc = acc;
      v_rdd = rdd; v_tokd = tokd; v_tokn = tokn; v_tok = tok; v_busyn = busyn;
      go = 1'b0; f = '0; ok1 = 1'b0; ap = 1'b0; rb = 1'b0;
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
          if (i == 6'd0) begin
            v_cst = 3'd0; v_polls = '0; v_rca = '0; v_w = 2'd0; v_blklen = 10'd512; v_dm = D_NONE; v_multi = 1'b0;
          end else if (!emmc && i == 6'd8 && v_cst == 3'd0) begin
            if (a[11:8] == 4'h1) begin v_txs = {frame(6'd8, {20'h0, a[11:0]}), 88'h0}; v_txn = 8'd48; v_txd = 7'(NCR - 1); end
          end else if (emmc && i == 6'd8 && v_cst == 3'd4) begin
            ok1 = 1'b1; v_xcsd = 1'b1; v_multi = 1'b0; v_baddr = '0; v_dm = D_RPEND; v_cst = 3'd5;
          end else if (!emmc && i == 6'd55 && v_cst != 3'd2 && v_cst <= 3'd4) begin
            v_app = 1'b1; ok1 = 1'b1; ap = 1'b1;
          end else if (!emmc && i == 6'd41 && wa && v_cst <= 3'd1) begin
            rdy = v_polls >= 4'(POLLS);
            if (v_polls != 4'd15) v_polls = v_polls + 4'd1;
            if (rdy) v_cst = 3'd1;
            v_txs = {2'b00, 6'h3F, rdy, rdy, 6'h00, 24'hFF8000, 8'hFF, 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1);
          end else if (emmc && i == 6'd1 && v_cst == 3'd0) begin
            rdy = v_polls >= 4'(POLLS);
            if (v_polls != 4'd15) v_polls = v_polls + 4'd1;
            if (rdy) v_cst = 3'd1;
            v_txs = {2'b00, 6'h3F, rdy, 2'b10, 29'h00FF_8080, 8'hFF, 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1);
          end else if (i == 6'd2 && v_cst == 3'd1) begin
            body = emmc ? CID_EMMC : CID_SD;
            v_cst = 3'd2; v_txs = {2'b00, 6'h3F, body, crc7(body, 120), 1'b1}; v_txn = 8'd136; v_txd = 7'(NCR - 1);
          end else if (!emmc && i == 6'd3 && (v_cst == 3'd2 || v_cst == 3'd3)) begin
            v_cst = 3'd3; v_rca = SD_RCA;
            v_txs = {frame(6'd3, {SD_RCA, v_crc_e, v_ill, 2'b00, st, 1'b1, 2'b00, 1'b0, 5'h00}), 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
          end else if (emmc && i == 6'd3 && v_cst == 3'd2 && a[31:16] != 16'h0) begin
            v_cst = 3'd3; v_rca = a[31:16]; ok1 = 1'b1;
          end else if (i == 6'd7 && (v_cst == 3'd3 || v_cst == 3'd4)) begin
            if (a[31:16] == v_rca) begin v_cst = 3'd4; ok1 = 1'b1; rb = 1'b1; end
            else if (v_cst == 3'd4) v_cst = 3'd3;
          end else if (i == 6'd13 && v_cst >= 3'd3) begin
            if (a[31:16] == v_rca) ok1 = 1'b1;
          end else if (!emmc && i == 6'd6 && wa && v_cst == 3'd4 && !a[0]) begin
            v_w = a[1] ? 2'd1 : 2'd0; ok1 = 1'b1; ap = 1'b1;
          end else if (emmc && i == 6'd6 && v_cst == 3'd4 && a[25:24] == 2'b11 && a[23:16] == 8'd183 &&
                       a[15:8] <= 8'd2) begin
            v_w = a[9:8]; ok1 = 1'b1; rb = 1'b1;
          end else if (i == 6'd16 && v_cst == 3'd4 && a != 0 && a <= 32'd512) begin
            v_blklen = a[9:0]; ok1 = 1'b1;
          end else if ((i == 6'd17 || i == 6'd18 || i == 6'd24 || i == 6'd25) && v_cst == 3'd4) begin
            ok1 = 1'b1;
            v_baddr = (a * 32'(v_blklen)) % 32'(MEMB); v_multi = (i == 6'd18 || i == 6'd25); v_xcsd = 1'b0;
            if (i == 6'd17 || i == 6'd18) begin v_dm = D_RPEND; v_cst = 3'd5; end
            else begin v_dm = D_WWAIT; v_cst = 3'd6; end
          end else if (i == 6'd12 && (v_cst == 3'd5 || v_cst == 3'd6)) begin
            ok1 = 1'b1; rb = 1'b1; v_cst = 3'd4; v_multi = 1'b0; v_xcsd = 1'b0;
          end else v_ill = 1'b1;
          if (ok1) begin
            v_txs = {frame(i, {8'h00, v_crc_e, v_ill, 9'h000, 1'b0, st, 1'b1, 2'b00, ap, 5'h00}), 88'h0};
            v_txn = 8'd48; v_txd = 7'(NCR - 1); v_crc_e = 1'b0; v_ill = 1'b0;
            if (rb) v_dm = D_BPEND;
          end
        end
      end
      m = mask(v_w);
      nclk = (v_xcsd ? 13'd512 : 13'(v_blklen)) * 13'(cpb(v_w));
      // write block receiver
      case (v_dm)
        D_WWAIT: if (!dl[0]) begin v_dm = D_WDATA; v_dcnt = '0; v_crc = '0; end
        D_WDATA: begin
          s = 4'(v_dcnt % 13'(cpb(v_w))); bi = v_dcnt / 13'(cpb(v_w));
          if (v_w == 2'd2) wbuf[bi[8:0]] <= dl;
          else if (v_w == 2'd1) begin if (s == 0) v_acc[7:4] = dl[3:0]; else wbuf[bi[8:0]] <= {v_acc[7:4], dl[3:0]}; end
          else begin v_acc = {v_acc[6:0], dl[0]}; if (s == 4'd7) wbuf[bi[8:0]] <= v_acc; end
          v_crc = crc8(v_crc, dl, m);
          v_dcnt = v_dcnt + 13'd1;
          if (v_dcnt == nclk) begin v_dm = D_WCRC; v_dcnt = '0; v_rcrc = '0; end
        end
        D_WCRC: begin
          for (int l = 0; l < 8; l++) if (m[l]) v_rcrc[16 * l +: 16] = {v_rcrc[16 * l +: 15], dl[l]};
          v_dcnt = v_dcnt + 13'd1;
          if (v_dcnt == 13'd16) v_dm = D_WEND;
        end
        D_WEND: begin
          good = (dl & m) == m && v_rcrc == v_crc;
          if (good) for (int k = 0; k < 512; k++) if (k < 32'(v_blklen)) mem[(v_baddr + k) % MEMB] <= wbuf[k];
          v_tok = good ? 5'b0_010_1 : 5'b0_101_1;
          v_dm = D_TOK; v_tokd = 7'd1; v_tokn = 3'd5; v_busyn = good ? 8'(BUSY) : 8'd0;
          v_baddr = (v_baddr + 32'(v_blklen)) % 32'(MEMB);
        end
        default: ;
      endcase
      // outputs for the next period
      if (v_txd != 0) begin v_txd = v_txd - 7'd1; n_cmd_oe <= 1'b0; end
      else if (v_txn != 0) begin
        n_cmd_oe <= 1'b1; n_cmd <= v_txs[135]; v_txs = v_txs << 1; v_txn = v_txn - 8'd1;
        if (v_txn == 0 && v_dm == D_RPEND) begin v_dm = D_RWAIT; v_rdd = 7'(NAC); end
        if (v_txn == 0 && v_dm == D_BPEND) begin v_dm = D_TOK; v_tokd = 7'd2; v_tokn = 3'd0; v_busyn = 8'(RBUSY); end
      end else n_cmd_oe <= 1'b0;
      case (v_dm)
        D_TOK:
          if (v_tokd != 0) begin v_tokd = v_tokd - 7'd1; n_dat_oe <= 8'h0; end
          else if (v_tokn != 0) begin n_dat_oe <= 8'h01; n_dat <= {7'h0, v_tok[4]}; v_tok = v_tok << 1; v_tokn = v_tokn - 3'd1; end
          else if (v_busyn != 0) begin n_dat_oe <= 8'h01; n_dat <= 8'h0; v_busyn = v_busyn - 8'd1; end
          else begin
            n_dat_oe <= 8'h0;
            if (v_cst == 3'd6 && v_multi) v_dm = D_WWAIT;
            else begin v_dm = D_NONE; if (v_cst == 3'd6) v_cst = 3'd4; end
          end
        D_RWAIT:
          if (v_rdd != 0) begin v_rdd = v_rdd - 7'd1; n_dat_oe <= 8'h0; end
          else begin n_dat_oe <= m; n_dat <= 8'h0; v_dm = D_RDATA; v_dcnt = '0; v_crc = '0; end
        D_RDATA: begin
          s = 4'(v_dcnt % 13'(cpb(v_w))); bi = v_dcnt / 13'(cpb(v_w));
          b = v_xcsd ? ext(bi[8:0], v_w) : mem[(v_baddr + 32'(bi)) % MEMB];
          v = lines(v_w, b, s[2:0]);
          n_dat_oe <= m; n_dat <= v & m;
          v_crc = crc8(v_crc, v, m);
          v_dcnt = v_dcnt + 13'd1;
          if (v_dcnt == nclk) begin v_dm = D_RCRC; v_dcnt = '0; end
        end
        D_RCRC: begin
          n_dat_oe <= m;
          for (int l = 0; l < 8; l++) begin v[l] = m[l] & v_crc[16 * l + 15]; v_crc[16 * l +: 16] = v_crc[16 * l +: 16] << 1; end
          n_dat <= v;
          v_dcnt = v_dcnt + 13'd1;
          if (v_dcnt == 13'd16) v_dm = D_REND;
        end
        D_REND: begin
          n_dat_oe <= m; n_dat <= m;
          if (v_multi) begin v_baddr = (v_baddr + 32'(v_blklen)) % 32'(MEMB); v_rdd = 7'(NAC); v_dm = D_RWAIT; end
          else v_dm = D_RREL;
        end
        D_RREL: begin n_dat_oe <= 8'h0; v_dm = D_NONE; v_cst = 3'd4; v_xcsd = 1'b0; end
        default: n_dat_oe <= 8'h0;
      endcase
      cst <= v_cst; polls <= v_polls; dm <= v_dm; app <= v_app; crc_e <= v_crc_e; ill <= v_ill; multi <= v_multi;
      xcsd <= v_xcsd; w <= v_w; blklen <= v_blklen; rca <= v_rca; rxc <= v_rxc; rxs <= v_rxs; txn <= v_txn;
      txd <= v_txd; txs <= v_txs; dcnt <= v_dcnt; baddr <= v_baddr; crc <= v_crc; rcrc <= v_rcrc; acc <= v_acc;
      rdd <= v_rdd; tokd <= v_tokd; tokn <= v_tokn; tok <= v_tok; busyn <= v_busyn;
    end
  end

  // falling sd_clk: the outputs change
  always_ff @(negedge sd_clk or negedge rst_n) begin
    if (!rst_n) begin
      cmd_s <= 1'b0; cmd_s_oe <= 1'b0; dat_s <= 8'h0; dat_s_oe <= 8'h0;
    end else begin
      cmd_s <= n_cmd; cmd_s_oe <= n_cmd_oe; dat_s <= n_dat; dat_s_oe <= n_dat_oe;
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({sd_clk, emmc, cmd_m_oe, dat_m_oe, cmd_s_oe, dat_s_oe}))
  else $error("SDM: X on sd_clk, emmc or an enable");
assert property (@(posedge clk) disable iff (!rst_n) !(cmd_m_oe && cmd_s_oe))
  else $error("SDM: host and card drive CMD together");
assert property (@(posedge clk) disable iff (!rst_n) !(dat_m_oe && dat_s_oe != 8'h0))
  else $error("SDM: host and card drive DAT together");
assert property (@(posedge clk) disable iff (!rst_n) dat_s_oe inside {8'h00, 8'h01, 8'h0F, 8'hFF})
  else $error("SDM: card drives a line set that is no bus width");
assert property (@(posedge clk) disable iff (!rst_n) $changed({cmd_s_oe, cmd_s, dat_s_oe, dat_s}) |-> !sd_clk)
  else $error("SDM: card output changed while sd_clk is high");
cover property (@(posedge clk) disable iff (!rst_n) dat_s_oe == 8'hFF);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;      // a falling edge: the card has no clock to see a level reset
logic sd_clk = 1'b1, emmc = 1'b0, cmd_m = 1'b0, cmd_m_oe = 1'b0, dat_m_oe = 1'b0;
logic [7:0] dat_m = 8'h0;
wire cmd_s, cmd_s_oe;
wire [7:0] dat_s, dat_s_oe;

always #5 clk = ~clk;

sdm_model u_dut (.clk(clk), .rst_n(rst_n), .sd_clk(sd_clk), .emmc(emmc), .cmd_m(cmd_m), .cmd_m_oe(cmd_m_oe),
                 .dat_m(dat_m), .dat_m_oe(dat_m_oe), .cmd_s(cmd_s), .cmd_s_oe(cmd_s_oe), .dat_s(dat_s),
                 .dat_s_oe(dat_s_oe));

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
logic [7:0] dl;
integer conflict = 0, badoe = 0;
task automatic clk1(input logic co, input logic c, input logic doe, input logic [7:0] d);
  @(negedge clk); sd_clk = 0; cmd_m_oe = co; cmd_m = c; dat_m_oe = doe; dat_m = d;
  @(negedge clk);
  sd_clk = 1;
  cl = co ? c : (cmd_s_oe ? cmd_s : 1'b1);
  for (int i = 0; i < 8; i++) dl[i] = doe ? d[i] : (dat_s_oe[i] ? dat_s[i] : 1'b1);
  if ((co && cmd_s_oe) || (doe && dat_s_oe != 0)) conflict = conflict + 1;
  if (!(dat_s_oe == 8'h00 || dat_s_oe == 8'h01 || dat_s_oe == 8'h0F || dat_s_oe == 8'hFF)) badoe = badoe + 1;
  @(negedge clk);
endtask
task automatic idle1(); clk1(0, 0, 0, 8'h0); endtask
logic [135:0] r;
integer ncr;
logic got;
task automatic cmd(input logic [5:0] i, input logic [31:0] a, input integer len = 48, input logic badcrc = 0,
                   input integer trail = 4);
  logic [39:0] b;
  logic [47:0] f;
  integer k;
  b = {2'b01, i, a}; f = {b, crc7({80'h0, b}, 40), 1'b1};
  if (badcrc) f[3] = ~f[3];
  repeat (2) idle1();
  for (int j = 47; j >= 0; j--) clk1(1, f[j], 0, 8'h0);
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
task automatic r1b();
  bk = 0;
  do begin idle1(); bk = bk + 1; end while (dl[0] && bk < 16);
  busy = 0;
  while (!dl[0] && busy < 64) begin busy = busy + 1; idle1(); end
  repeat (2) idle1();
endtask
// bus width code 0 / 1 / 2
integer w = 0;
function automatic logic [7:0] lm(); lm = (w == 2) ? 8'hFF : (w == 1) ? 8'h0F : 8'h01; endfunction
function automatic integer cpb(); cpb = (w == 2) ? 1 : (w == 1) ? 2 : 8; endfunction
function automatic logic [7:0] lv(input logic [7:0] b, input integer s);
  if (w == 2) lv = b; else if (w == 1) lv = {4'hF, (s == 0) ? b[7:4] : b[3:0]}; else lv = {7'h7F, b[7 - s]};
endfunction
logic [7:0] wb [0:511];
logic [7:0] rb [0:511];
logic [3:0] tok;
task automatic wr_blk(input integer n, input logic bad = 0);
  logic [15:0] c [0:7];
  logic [7:0] v, m;
  integer k;
  m = lm();
  for (int l = 0; l < 8; l++) c[l] = 0;
  clk1(0, 0, 1, 8'hFF); clk1(0, 0, 1, ~m);
  for (int i = 0; i < n; i++) for (int s = 0; s < cpb(); s++) begin
    v = lv(wb[i], s);
    for (int l = 0; l < 8; l++) if (m[l]) c[l] = crc16(c[l], v[l]);
    clk1(0, 0, 1, v);
  end
  if (bad) c[0][5] = ~c[0][5];
  for (int b = 15; b >= 0; b--) begin for (int l = 0; l < 8; l++) v[l] = m[l] ? c[l][b] : 1'b1; clk1(0, 0, 1, v); end
  clk1(0, 0, 1, 8'hFF);
  k = 0;
  do begin idle1(); k = k + 1; end while (dl[0] && k < 64);
  tokk = k;
  tok = {dl[0], 3'b000};
  for (int j = 2; j >= 0; j--) begin idle1(); tok[j] = dl[0]; end
  idle1();
  busy = 0;
  if (dl[0]) begin idle1(); while (!dl[0] && busy < 64) begin busy = busy + 1; idle1(); end end
  repeat (2) idle1();
endtask
logic rd_ok;
integer rk;
task automatic rd_blk(input integer n, input integer trail = 4);
  logic [15:0] c [0:7], x [0:7];
  logic [7:0] m, bb;
  logic se;
  m = lm();
  for (int l = 0; l < 8; l++) begin c[l] = 0; x[l] = 0; end
  rk = 0;
  do begin idle1(); rk = rk + 1; end while (dl[0] && rk < 64);
  se = (dl & m) == 8'h00 && (dl | m) == 8'hFF;
  for (int i = 0; i < n; i++) begin
    bb = 0;
    for (int s = 0; s < cpb(); s++) begin
      idle1();
      for (int l = 0; l < 8; l++) if (m[l]) c[l] = crc16(c[l], dl[l]);
      if (w == 2) bb = dl; else if (w == 1) bb = {bb[3:0], dl[3:0]}; else bb = {bb[6:0], dl[0]};
    end
    rb[i] = bb;
  end
  for (int b = 0; b < 16; b++) begin idle1(); for (int l = 0; l < 8; l++) x[l] = {x[l][14:0], dl[l]}; end
  idle1();
  rd_ok = se && (dl & m) == m;
  for (int l = 0; l < 8; l++) if (m[l] && c[l] != x[l]) rd_ok = 0;
  repeat (trail) idle1();
endtask
function automatic logic [7:0] ib(input integer i); ib = (i ^ (i >> 8) ^ 8'hA5); endfunction
function automatic logic same(input integer n, input integer base);
  same = 1;
  for (int i = 0; i < n; i++) if (rb[i] !== ib(base + i)) same = 0;
endfunction
function automatic logic same_wb(input integer n);
  same_wb = 1;
  for (int i = 0; i < n; i++) if (rb[i] !== wb[i]) same_wb = 0;
endfunction
task automatic fill(input integer n, input integer sd);
  for (int i = 0; i < n; i++) wb[i] = (i * 37 + sd * 11) ^ (i >> 3);
endtask
logic [15:0] rca;
logic ok;

initial begin
  repeat (3) @(posedge clk);
  chk(cmd_s_oe === 1'b0 && dat_s_oe === 8'h0, "card off the bus in reset");
  rst_n = 1;
  repeat (4) idle1();
  // ------------------------------ SD ------------------------------
  cmd(6'd41, 32'h40FF_8000); chk(!got, "ACMD41 as the first command after reset: illegal");
  cmd(6'd13, 32'h0); chk(!got, "SD: CMD13 in idle: illegal");
  cmd(6'd0, 32'h0); chk(!got, "CMD0: no response");
  cmd(6'd8, 32'h0000_02AA); chk(!got, "CMD8 with VHS 2: no response");
  cmd(6'd8, 32'h0000_01AA); chk(got && ncr == 2 && r48_ok(6'd8) && r[19:8] == 12'h1AA, "CMD8: R7 echo, NCR = 2");
  cmd(6'd41, 32'h40FF_8000); chk(!got, "ACMD41 without CMD55: illegal");
  cmd(6'd55, 32'h0); chk(got && r48_ok(6'd55) && r[39:8] == 32'h0040_0120, "CMD55: ILLEGAL_COMMAND, idle, APP_CMD");
  cmd(6'd41, 32'h40FF_8000); chk(got && r[45:40] == 6'h3F && r[7:0] == 8'hFF && r[39:8] == 32'h00FF_8000, "ACMD41: busy");
  cmd(6'd55, 32'h0); cmd(6'd41, 32'h40FF_8000); chk(r[39:8] == 32'h00FF_8000, "ACMD41: busy (POLLS = 2)");
  cmd(6'd55, 32'h0); cmd(6'd41, 32'h40FF_8000); chk(r[39:8] == 32'hC0FF_8000, "ACMD41: ready, CCS");
  cmd(6'd1, 32'h40FF_8080); chk(!got, "SD: CMD1 illegal");
  cmd(6'd2, 32'h0, 136);
  chk(got && ncr == 2 && r[133:128] == 6'h3F && r[0] && crc7(r[127:8], 120) == r[7:1] && r[127:8] == 120'h1D4F5653444D43311012345678016A,
      "CMD2: SD CID");
  cmd(6'd3, 32'h0); rca = r[39:24];
  chk(got && r48_ok(6'd3) && rca == 16'hB37A && r[23:8] == 16'h4500, "CMD3: R6, RCA B37A, ILLEGAL_COMMAND (CMD1), ident");
  cmd(6'd13, {rca, 16'h0}, 48, 1); chk(!got, "bad CRC7: no response");
  cmd(6'd13, {rca, 16'h0}); chk(got && ncr == 2 && r48_ok(6'd13) && r[39:8] == 32'h0080_0700, "CMD13: COM_CRC_ERROR, stby");
  cmd(6'd17, 32'd1); chk(!got, "CMD17 in stby: illegal");
  cmd(6'd7, {rca, 16'h0}, 48, 0, 0);
  chk(got && r48_ok(6'd7) && r[39:8] == 32'h0040_0700, "CMD7: R1, ILLEGAL_COMMAND, stby"); r1b();
  chk(bk == 2 && busy == 3, "CMD7: R1b busy 3 clocks, 2 clocks after the end bit");
  cmd(6'd17, 32'd1, 48, 0, 0); rd_blk(512); chk(got && rd_ok && rk == 2 && same(512, 512), "1-bit CMD17: block 1, NAC = 2");
  fill(512, 1);
  cmd(6'd24, 32'd1, 48, 0, 0); chk(got && r[39:8] == 32'h0000_0900, "CMD24: R1, tran");
  wr_blk(512); chk(tok == 4'b0010 && busy == 4 && tokk == 2, "1-bit write: token 010 after 2 clocks, 4 clocks busy");
  cmd(6'd17, 32'd1, 48, 0, 0); rd_blk(512); chk(rd_ok && same_wb(512), "1-bit read-back");
  cmd(6'd55, {rca, 16'h0}); cmd(6'd6, 32'h2); chk(got && r48_ok(6'd6) && r[39:8] == 32'h0000_0920, "ACMD6: 4-bit, R1 with APP_CMD");
  w = 1;
  fill(512, 2);
  cmd(6'd25, 32'd2, 48, 0, 0); chk(got && r[39:8] == 32'h0000_0900, "CMD25: R1");
  wr_blk(512); ok = tok == 4'b0010; fill(512, 3); wr_blk(512); ok = ok && tok == 4'b0010 && busy == 4;
  cmd(6'd12, 32'h0, 48, 0, 0); chk(ok && got && r[39:8] == 32'h0000_0D00, "CMD25: 2 blocks, CMD12 in rcv state"); r1b();
  chk(busy == 3, "CMD12: R1b busy");
  cmd(6'd18, 32'd2, 48, 0, 0); rd_blk(512, 0); ok = rd_ok && rk == 2; fill(512, 2); ok = ok && same_wb(512);
  rd_blk(512, 0); fill(512, 3); ok = ok && rd_ok && rk == 3 && same_wb(512);
  rd_blk(512, 0); ok = ok && rd_ok && same(512, 2048);
  cmd(6'd12, 32'h0, 48, 0, 0); chk(ok && got && r[39:8] == 32'h0000_0B00, "4-bit CMD18: 3 blocks, NAC between, CMD12 in data state");
  r1b();
  cmd(6'd13, {rca, 16'h0}); chk(got && r[39:8] == 32'h0000_0900, "back in tran");
  fill(512, 4);
  cmd(6'd24, 32'd5, 48, 0, 0); wr_blk(512, 1); chk(tok == 4'b0101 && busy == 0, "bad CRC16: token 101, no busy");
  cmd(6'd17, 32'd5, 48, 0, 0); rd_blk(512); chk(rd_ok && same(512, 5 * 512), "and nothing written");
  cmd(6'd16, 32'd64); chk(got && r[39:8] == 32'h0000_0900, "CMD16: 64-byte blocks");
  cmd(6'd17, 32'd3, 48, 0, 0); rd_blk(64); chk(rd_ok && same(64, 192), "64-byte block 3 is bytes 192..255");
  cmd(6'd16, 32'd513); chk(!got, "CMD16 513: illegal");
  cmd(6'd16, 32'd512);
  chk(got && r[39:8] == 32'h0040_0900, "CMD16 512, ILLEGAL_COMMAND reported");
  cmd(6'd18, 32'd0, 48, 0, 0);
  rk = 0; do begin idle1(); rk = rk + 1; end while (dl[0] && rk < 64); repeat (40) idle1();
  cmd(6'd12, 32'h0, 48, 0, 0); ok = got && r[39:8] == 32'h0000_0B00; r1b();
  chk(ok && dat_s_oe === 8'h0 && busy == 3, "CMD12 stops a read in the middle of a block");
  cmd(6'd12, 32'h0); chk(!got, "CMD12 in tran: illegal");
  cmd(6'd7, {rca ^ 16'h1, 16'h0}); chk(!got, "CMD7 to another RCA: deselect");
  cmd(6'd13, {rca, 16'h0}); chk(got && r[39:8] == 32'h0040_0700, "stby, ILLEGAL_COMMAND (CMD12)");
  // ------------------------------ eMMC ------------------------------
  emmc = 1; w = 0;
  cmd(6'd0, 32'h0);
  cmd(6'd55, 32'h0); chk(!got, "eMMC: CMD55 illegal");
  cmd(6'd1, 32'h40FF_8080); chk(got && ncr == 2 && r[45:40] == 6'h3F && r[39:8] == 32'h40FF_8080, "CMD1: busy, sector mode");
  cmd(6'd1, 32'h40FF_8080); cmd(6'd1, 32'h40FF_8080); chk(r[39:8] == 32'hC0FF_8080, "CMD1: ready on the third poll");
  cmd(6'd2, 32'h0, 136);
  chk(got && crc7(r[127:8], 120) == r[7:1] && r[127:8] == 120'h150100454D4D4344361087654321A8, "CMD2: eMMC CID");
  cmd(6'd3, 32'h0); chk(!got, "CMD3 with RCA 0: illegal");
  cmd(6'd3, 32'h0005_0000); chk(got && r48_ok(6'd3) && r[39:8] == 32'h0040_0500, "CMD3: R1, ident, ILLEGAL_COMMAND");
  cmd(6'd7, 32'h0005_0000, 48, 0, 0); r1b(); chk(busy == 3, "CMD7: R1b");
  cmd(6'd8, 32'h0, 48, 0, 0); chk(got && r[39:8] == 32'h0000_0900, "CMD8: R1"); rd_blk(512);
  chk(rd_ok && rb[183] == 8'd0 && rb[192] == 8'd8 && rb[196] == 8'd7 && rb[212] == 8'd8 && rb[0] == 8'd0,
      "EXT_CSD: BUS_WIDTH 0, rev 8, SEC_COUNT 8");
  cmd(6'd6, {6'h0, 2'b11, 8'd183, 8'd2, 8'h0}, 48, 0, 0); chk(got && r48_ok(6'd6), "CMD6 SWITCH: 8 bits"); r1b();
  w = 2;
  cmd(6'd8, 32'h0, 48, 0, 0); rd_blk(512); chk(rd_ok && rb[183] == 8'd2, "8-bit EXT_CSD read: BUS_WIDTH 2");
  cmd(6'd17, 32'd1, 48, 0, 0); rd_blk(512); fill(512, 1); chk(rd_ok && same_wb(512), "8-bit read of SD's block 1");
  fill(512, 9);
  cmd(6'd25, 32'd6, 48, 0, 0); wr_blk(512); ok = tok == 4'b0010;
  cmd(6'd12, 32'h0, 48, 0, 0); r1b();
  cmd(6'd18, 32'd6, 48, 0, 0); rd_blk(512, 0); ok = ok && rd_ok && same_wb(512); rd_blk(512, 0);
  cmd(6'd12, 32'h0, 48, 0, 0); r1b();
  chk(ok && rd_ok && same(512, 7 * 512), "8-bit CMD25 / CMD18 with CMD12");
  cmd(6'd6, {6'h0, 2'b11, 8'd183, 8'd3, 8'h0}); chk(!got, "BUS_WIDTH 3: illegal");
  cmd(6'd6, {6'h0, 2'b11, 8'd185, 8'd1, 8'h0}); chk(!got, "SWITCH of another byte: illegal");
  cmd(6'd6, {6'h0, 2'b11, 8'd183, 8'd1, 8'h0}, 48, 0, 0); r1b(); w = 1;
  cmd(6'd16, 32'd128);
  fill(128, 5);
  cmd(6'd24, 32'd2, 48, 0, 0); wr_blk(128); chk(tok == 4'b0010, "4-bit 128-byte write");
  cmd(6'd17, 32'd2, 48, 0, 0); rd_blk(128); chk(rd_ok && same_wb(128), "and read-back");
  cmd(6'd16, 32'd512);
  cmd(6'd17, 32'd0, 48, 0, 0); rd_blk(512);
  ok = rd_ok;
  for (int i = 0; i < 256; i++) if (rb[i] !== ib(i)) ok = 0;
  for (int i = 0; i < 128; i++) if (rb[256 + i] !== wb[i]) ok = 0;
  chk(ok, "the 128-byte block 2 sits at bytes 256..383");
  cmd(6'd13, 32'h0005_0000); chk(got && r[39:8] == 32'h0000_0900, "CMD13: tran, flags cleared by the R1s since");
  cmd(6'd0, 32'h0);
  cmd(6'd13, 32'h0005_0000); chk(!got, "CMD0 from tran: idle");
  chk(conflict == 0 && badoe == 0, "no bus contention, only bus-width line sets");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #200000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
