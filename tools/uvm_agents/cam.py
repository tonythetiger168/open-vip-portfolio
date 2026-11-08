# DVB Common Interface / CI+ CAM VIP: a conditional-access module model on the
# EN 50221 PC Card (8-bit) pins of a set-top box's CI host, with a host agent.
#
# Agent -> DUT (host): ci_vcc_en, ci_reset (high active), the address ci_a,
# the write data ci_d_o / ci_d_oe, the strobes ci_ce_n, ci_reg_n, ci_oe_n,
# ci_we_n, ci_iord_n, ci_iowr_n, and the transport stream into the CAM
# ci_mo_data / ci_mo_val / ci_mo_strt. DUT -> agent (CAM): ci_cd_n, read
# data ci_d_i, ci_wait_n, ci_ireq_n (READY, then IREQ#), and the stream out
# of the CAM ci_mi_data / ci_mi_val / ci_mi_strt. The pins are those of
# CI_Plus_Host_top in open-ip-portfolio. Everything is sampled on clk.
#
# tb/top_tb.sv cam_model is the CAM:
#   ci_cd_n is low (inserted). With VCC off everything is cleared. RESET high
#   clears the card (COR 0, memory mode, buffers empty); RDY_DLY clocks after
#   RESET falls READY (ci_ireq_n) goes high, and only then are bus cycles
#   answered. A strobe (OE#, WE#, IORD#, IOWR# low with CE# low) holds
#   ci_wait_n low for its first WAIT clocks; read data is driven while the
#   strobe is low (0x00 otherwise); a cycle takes effect when its strobe
#   ends, with the address and data of the strobe's last clock.
#   Attribute memory (REG# low): the CIS byte k at address 2k (57 bytes:
#   DEVICE_OA, DEVICE_OC, VERS_1 "DVB CAM", CONFIG with COR at 0x0FFE and
#   "DVB_CI_V1.00", CFTABLE_ENTRY 0x0F, NO_LINK, END), 0xFF at odd and
#   unused addresses; it is read-only except the COR at COR_ADDR, read back
#   as written. Writing a COR value whose bits 5..0 are the configuration
#   index CFG_IDX (0x0F) enters I/O mode; another value leaves it. Common
#   memory (REG# high) reads 0xFF and ignores writes.
#   I/O mode (REG# low): address 0 DATA, 1 COMMAND / STATUS, 2 SIZE_LS,
#   3 SIZE_MS. STATUS = {DA, FR, 0000, WE, RE}. COMMAND = {DAIE, FRIE, 00,
#   RS, SR, SW, HC}. FR (free) is high when the interface is not resetting,
#   no message is being processed and no reply waits to be read. RS clears
#   the buffers and WE / RE; FR returns RS_DLY clocks after RS is cleared.
#   SR set with no reply waiting queues the 2-byte buffer size (BUF). HC set
#   opens a host message (taken only if FR was high); SIZE_LS / SIZE_MS are
#   its size, DATA writes its bytes (up to BUF); HC cleared ends it: a
#   message whose byte count matches the size is processed for PROC clocks
#   and then answered with a reply of the same length (bytes 0 and 1, the
#   link header, kept, the rest XOR 0x5A); a mismatch, more than BUF bytes,
#   or a DATA write without an open message sets WE. DATA reads pop the
#   reply; a read with nothing to read sets RE. SIZE is the reply's length.
#   ci_ireq_n in I/O mode is low while (DAIE and DA) or (FRIE and FR).
#   Transport stream (VCC on): the CAM returns ci_mo_* one clock later; in a
#   packet whose scrambling control (byte 3 bits 7..6) is set, those bits
#   are cleared and every byte from 4 on is XORed with KEY ^ index
#   ("descrambled").
# In a SoC bench the CAM connects to CI_Plus_Host_top's card and ci_m* pins;
# with CI_Plus_Host, set COR_VAL = 0x0F and STROBE >= 2 (the CAM uses WAIT#).

CIS = ([0x1D, 0x04, 0x00, 0xDB, 0x08, 0xFF, 0x1C, 0x03, 0x00, 0x08, 0xFF, 0x15, 0x0E, 0x05, 0x00] + list(b"DVB CAM")
       + [0] + list(b"V1") + [0, 0xFF] + [0x1A, 0x15, 0x01, 0x0F, 0xFE, 0x0F, 0x01, 0xC0, 0x0E, 0x41, 0x02]
       + list(b"DVB_CI_V1.00") + [0x1B, 0x02, 0xCF, 0x00, 0x14, 0x00, 0xFF])
assert len(CIS) == 57


def _cis_case(ind, var, out):
    rows = [" " * ind + "case (%s)" % var]
    for i in range(0, len(CIS), 6):
        rows.append(" " * (ind + 2) + " ".join("14'd%d: %s = 8'h%02X;" % (j, out, CIS[j])
                                                for j in range(i, min(i + 6, len(CIS)))))
    rows.append(" " * (ind + 2) + "default: %s = 8'hFF;" % out)
    rows.append(" " * ind + "endcase")
    return "\n".join(rows)


CAM_FUNCS = """
function automatic bit [7:0] cam_cis(bit [13:0] k);
  bit [7:0] v;
%s
  return v;
endfunction
""" % _cis_case(2, "k", "v")

MODEL_CIS = """
  function automatic logic [7:0] cis(input logic [13:0] k);
%s
  endfunction
""" % _cis_case(4, "k", "cis")

# pin packing: mo = {vcc, reset, a[14:0], d_o, d_oe, ce_n, reg_n, oe_n, we_n, iord_n, iowr_n, mo_data, mo_val, mo_strt}
#              so = {cd_n, d_i, wait_n, ireq_n, mi_data, mi_val, mi_strt}

SPEC = dict(
    vip="CI_CAM-UVM-VIP", p="cam", P="CAM", dir="cam", family="Security",
    desc="DVB Common Interface / CI+ CAM VIP (EN 50221): CAM model with CIS, COR and I/O mode, WAIT#, READY / "
         "IREQ#, the command interface (FR / DA, RS, SR buffer size, HC messages, WE / RE) and TS descrambling; "
         "host agent with PC Card bus cycles and a clock-by-clock pin predictor (CI_Plus_Host pins).",
    about="""
A set-top box's CI+ slot holds a conditional-access module on an 8-bit PC
Card bus. The VIP's DUT model is that CAM, so a SoC bench can hang it on
CI_Plus_Host's card pins. The agent is the host: it powers and resets the
CAM, waits for READY, reads the CIS, writes the COR (into and out of I/O
mode), resets the command interface, negotiates the buffer size, sends
messages (with FR missing, too long, with a size mismatch, without HC) and
reads replies (and an empty DATA register), enables the interrupts, makes
common-memory and memory-mode I/O accesses, and sends clear and scrambled
TS packets through the CAM, all with varying setup, strobe and hold times.
The scoreboard runs its own copy of the CAM on the monitored host pins and
predicts every CAM output on every clock: read data, WAIT#, READY / IREQ#
and the stream out of the CAM.""",
    defs=CAM_FUNCS,
    timeout=4000000,
    cfg="""int unsigned gap = 4;      // idle clocks after each item""",
    ports=[("in", "logic", "ci_vcc_en"), ("in", "logic", "ci_reset"), ("in", "logic [14:0]", "ci_a"),
           ("in", "logic [7:0]", "ci_d_o"), ("in", "logic", "ci_d_oe"), ("in", "logic", "ci_ce_n"),
           ("in", "logic", "ci_reg_n"), ("in", "logic", "ci_oe_n"), ("in", "logic", "ci_we_n"),
           ("in", "logic", "ci_iord_n"), ("in", "logic", "ci_iowr_n"), ("in", "logic [7:0]", "ci_mo_data"),
           ("in", "logic", "ci_mo_val"), ("in", "logic", "ci_mo_strt"),
           ("out", "logic", "ci_cd_n"), ("out", "logic [7:0]", "ci_d_i"), ("out", "logic", "ci_wait_n"),
           ("out", "logic", "ci_ireq_n"), ("out", "logic [7:0]", "ci_mi_data"), ("out", "logic", "ci_mi_val"),
           ("out", "logic", "ci_mi_strt")],
    fields=[
        ("bit [41:0]", "mo", "req", "q"),       # host pins per clock
        ("bit [20:0]", "so", "rsp", "q"),       # CAM pins per clock
        ("bit [41:0]", "pre", "info", "q"),     # idle clocks before the item (not compared)
        ("bit [7:0]", "rd", "info", "q"),       # bytes the host read
        ("bit [3:0]", "kind", "info", "rand"),
        ("bit [6:0]", "cnt", "info", "rand"),
        ("bit [1:0]", "sup", "info", "rand"),
        ("bit [1:0]", "stb", "info", "rand"),
        ("bit [1:0]", "hld", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0 power up (VCC, RESET, wait READY), 1 power off, 2 CIS read (cnt % 64 + 1 bytes), 3 COR write
// (seed % 3: 01 / 0F / 4F) and read-back, 4 interface reset, 5 send a message (cnt % 66 + 1 bytes), 6 read
// a reply, 7 send and read, 8 DATA read with nothing to read, 9 buffer size (SR), 10 a TS packet
// (seed[0] scrambled, seed[1] with gaps), 11 I/O read in memory mode and a common-memory read, 12 write to
// the CIS and read it back, 13 COMMAND with DAIE / FRIE (seed[1:0]), 14 DATA write without HC, 15 a
// message whose size does not match
function void set(int k, int n = 0, bit [31:0] s = 32'h1); kind = k; cnt = n; seed = s; sup = 0; stb = 0; hld = 0; endfunction
function bit [7:0] wbyte(int i);
  bit [31:0] x = (seed | 1) ^ (32'(i) * 32'h9E37_79B9);
  x ^= x >> 13; x *= 32'h5BD1_E995; x ^= x >> 15;
  return x[7:0];
endfunction
""",
    drv_rsp=False,
    drv_members="""bit             vcc = 0, rs = 0, doe = 0, ce = 1, rg = 1, oe = 1, we = 1, ir = 1, iw = 1, tv = 0, tst = 0;
bit [14:0]      a = 15'h7FFF;
bit [7:0]       d = 0, td = 0;
bit [20:0]      rsp;
cam_transaction cur;""",
    drv_tasks="""
function bit [41:0] pk();
  return {vcc, rs, a, d, doe, ce, rg, oe, we, ir, iw, td, tv, tst};
endfunction
// one clock: drive the pins, record them, sample the CAM
task automatic clk1();
  vif.drv_cb.ci_vcc_en  <= vcc; vif.drv_cb.ci_reset <= rs; vif.drv_cb.ci_a <= a; vif.drv_cb.ci_d_o <= d;
  vif.drv_cb.ci_d_oe    <= doe; vif.drv_cb.ci_ce_n <= ce; vif.drv_cb.ci_reg_n <= rg; vif.drv_cb.ci_oe_n <= oe;
  vif.drv_cb.ci_we_n    <= we; vif.drv_cb.ci_iord_n <= ir; vif.drv_cb.ci_iowr_n <= iw;
  vif.drv_cb.ci_mo_data <= td; vif.drv_cb.ci_mo_val <= tv; vif.drv_cb.ci_mo_strt <= tst;
  cur.mo.push_back(pk());
  @(vif.drv_cb);
  rsp = {vif.drv_cb.ci_cd_n, vif.drv_cb.ci_d_i, vif.drv_cb.ci_wait_n, vif.drv_cb.ci_ireq_n,
         vif.drv_cb.ci_mi_data, vif.drv_cb.ci_mi_val, vif.drv_cb.ci_mi_strt};
endtask
task automatic idle(int n); repeat (n) clk1(); endtask
// a bus cycle: k 0 attribute read, 1 attribute write, 2 I/O read, 3 I/O write, 4 common-memory read
task automatic cyc(int k, bit [14:0] ad, bit [7:0] wd, output bit [7:0] rd);
  int n = 0;
  ce = 0; rg = (k == 4); a = ad;
  if (k == 1 || k == 3) begin d = wd; doe = 1; end
  repeat (cur.sup + 1) clk1();
  case (k) 1: we = 0; 2: ir = 0; 3: iw = 0; default: oe = 0; endcase
  repeat (cur.stb + 3) clk1();
  while (!rsp[11] && n < 64) begin clk1(); n++; end
  clk1();
  rd = rsp[19:12];
  oe = 1; we = 1; ir = 1; iw = 1;
  repeat (cur.hld + 1) clk1();
  ce = 1; rg = 1; doe = 0; d = 0; a = 0;
  clk1();
endtask
task automatic rd1(int k, bit [14:0] ad);
  bit [7:0] x;
  cyc(k, ad, 8'h00, x);
  cur.rd.push_back(x);
endtask
task automatic wr1(int k, bit [14:0] ad, bit [7:0] v);
  bit [7:0] x;
  cyc(k, ad, v, x);
endtask
task automatic status(output bit [7:0] s); cyc(2, 15'd1, 8'h00, s); cur.rd.push_back(s); endtask
// poll STATUS until bit b is set (at most n reads)
task automatic poll(int b, int n, output bit ok);
  bit [7:0] s;
  ok = 0;
  for (int i = 0; i < n && !ok; i++) begin status(s); ok = s[b]; end
endtask
task automatic send(int n, bit mism);
  bit ok;
  bit [7:0] s;
  poll(6, 12, ok);
  for (int t = 0; t < 3; t++) begin
    wr1(3, 15'd1, 8'h01);
    status(s);
    if (s[6]) break;
    wr1(3, 15'd1, 8'h00);
  end
  wr1(3, 15'd2, 8'(n)); wr1(3, 15'd3, 8'(n >> 8));
  for (int i = 0; i < n - mism; i++) wr1(3, 15'd0, cur.wbyte(i));
  wr1(3, 15'd1, 8'h00);
endtask
task automatic recv();
  bit ok;
  bit [7:0] lo, hi;
  poll(7, 12, ok);
  if (!ok) return;
  wr1(3, 15'd1, 8'h04);
  cyc(2, 15'd2, 8'h00, lo); cyc(2, 15'd3, 8'h00, hi);
  wr1(3, 15'd1, 8'h00);
  for (int i = 0; i < {hi, lo} && i < 80; i++) rd1(2, 15'd0);
  status(lo);
endtask
""",
    drv_desc="one item per host operation (power, CIS, COR, interface reset, message, reply, TS packet ...), each bus cycle with setup / strobe / hold of the item's sup / stb / hld, then cfg.gap idle clocks and one clock with CE# high and the address at 0x7FFF that ends the item",
    drv_idle="""
vif.drv_cb.ci_vcc_en <= 1'b0; vif.drv_cb.ci_reset <= 1'b0; vif.drv_cb.ci_a <= 15'h7FFF; vif.drv_cb.ci_d_o <= 8'h00;
vif.drv_cb.ci_d_oe <= 1'b0; vif.drv_cb.ci_ce_n <= 1'b1; vif.drv_cb.ci_reg_n <= 1'b1; vif.drv_cb.ci_oe_n <= 1'b1;
vif.drv_cb.ci_we_n <= 1'b1; vif.drv_cb.ci_iord_n <= 1'b1; vif.drv_cb.ci_iowr_n <= 1'b1;
vif.drv_cb.ci_mo_data <= 8'h00; vif.drv_cb.ci_mo_val <= 1'b0; vif.drv_cb.ci_mo_strt <= 1'b0;
""",
    drv_item="""
bit ok;
bit [7:0] s;
cur = t;
t.mo.delete(); t.rd.delete();
a = 0;
case (t.kind)
  0: begin
    vcc = 1; idle(4); rs = 1; idle(10); rs = 0; idle(2);
    for (int i = 0; i < 40 && !rsp[10]; i++) rd1(0, 15'd0);
  end
  1: begin vcc = 0; rs = 0; idle(10); end
  2: for (int i = 0; i <= t.cnt % 64; i++) rd1(0, 15'(2 * i));
  3: begin
    s = (t.seed % 3 == 0) ? 8'h01 : (t.seed % 3 == 1) ? 8'h0F : 8'h4F;
    wr1(1, 15'h0FFE, s); rd1(0, 15'h0FFE); status(s);
  end
  4: begin wr1(3, 15'd1, 8'h08); idle(2); wr1(3, 15'd1, 8'h00); poll(6, 12, ok); end
  5: send(t.cnt % 66 + 1, 1'b0);
  6: recv();
  7: begin send(t.cnt % 66 + 1, 1'b0); recv(); end
  8: begin rd1(2, 15'd0); rd1(2, 15'd0); status(s); end
  9: begin wr1(3, 15'd1, 8'h04); recv(); end
  10: begin
    for (int i = 0; i < 188; i++) begin
      td = (i == 0) ? 8'h47 : (i == 3) ? (t.seed[0] ? 8'hD3 : 8'h13) : t.wbyte(i);
      tv = 1; tst = (i == 0);
      clk1();
      if (t.seed[1] && i % 50 == 25) begin tv = 0; tst = 0; td = 0; idle(2); end
    end
    tv = 0; tst = 0; td = 0; idle(3);
  end
  11: begin rd1(2, 15'd1); rd1(4, 15'd0); rd1(4, 15'h0FFE); end
  12: begin wr1(1, 15'(2 * (t.cnt % 8)), 8'hAA); rd1(0, 15'(2 * (t.cnt % 8))); wr1(4, 15'h0FFE, 8'h00); rd1(0, 15'h0FFE); end
  13: begin wr1(3, 15'd1, {t.seed[0], t.seed[1], 6'b0}); status(s); idle(4); end
  14: begin wr1(3, 15'd0, 8'h33); status(s); end
  default: begin send(t.cnt % 20 + 2, 1'b1); idle(20); status(s); end
endcase
idle(cfg.gap);
a = 15'h7FFF; clk1(); a = 0;
""",
    mon_desc="every host and CAM pin at every clock; a clock with CE# high and the address at 0x7FFF ends an item (such clocks before an item's first clock are kept apart as idle)",
    mon_run="""
forever begin
  cam_transaction t;
  bit [41:0] m;
  t = cam_transaction::type_id::create("t");
  forever begin
    @(vif.mon_cb);
    m = {vif.mon_cb.ci_vcc_en, vif.mon_cb.ci_reset, vif.mon_cb.ci_a, vif.mon_cb.ci_d_o, vif.mon_cb.ci_d_oe,
         vif.mon_cb.ci_ce_n, vif.mon_cb.ci_reg_n, vif.mon_cb.ci_oe_n, vif.mon_cb.ci_we_n, vif.mon_cb.ci_iord_n,
         vif.mon_cb.ci_iowr_n, vif.mon_cb.ci_mo_data, vif.mon_cb.ci_mo_val, vif.mon_cb.ci_mo_strt};
    if (t.mo.size() == 0 && m[15] && m[39:25] == 15'h7FFF) begin t.pre.push_back(m); continue; end
    t.mo.push_back(m);
    t.so.push_back({vif.mon_cb.ci_cd_n, vif.mon_cb.ci_d_i, vif.mon_cb.ci_wait_n, vif.mon_cb.ci_ireq_n,
                    vif.mon_cb.ci_mi_data, vif.mon_cb.ci_mi_val, vif.mon_cb.ci_mi_strt});
    if ((m[15] && m[39:25] == 15'h7FFF) || t.mo.size() >= 65536) break;
  end
  publish(t);
end
""",
    sb_members="""// the CAM (scoreboard copy), kept across items
localparam int RDY_DLY = 20, WAIT = 2, RS_DLY = 10, PROC = 16, BUF = 64;
localparam bit [14:0] COR_ADDR = 15'h0FFE;
localparam bit [5:0] CFG_IDX = 6'h0F;
localparam bit [7:0] KEY = 8'hC5;
bit        rdy = 0, io = 0, hc = 0, hc_ok = 0, sr = 0, daie = 0, frie = 0, rsh = 0, we = 0, re = 0;
bit        proc = 0, regl = 0, tscr = 0, wn = 1, mv = 0, ms = 0;
int        rc = 0, rcnt = 0, icnt = 0, sz = 0, pc = 0, pn = 0, on = 0, op = 0, wc = 0, tidx = 0;
bit [7:0]  cor = 0, dl = 0, md = 0;
bit [14:0] al = 0;
bit [3:0]  st_q = 0;
bit [7:0]  ib [64], ob [64];

function bit fr(); return !rsh && rcnt == 0 && !proc && on == 0; endfunction
function bit [7:0] attr(bit [14:0] ad);
  if (ad[0]) return 8'hFF;
  if (ad == COR_ADDR) return cor;
  return cam_cis(ad[14:1]);
endfunction
// the CAM pins for host pins m with the state before the clock edge
function bit [20:0] outs(bit [41:0] m);
  bit [7:0] di = 0;
  bit da = on != 0;
  if (m[41] && !m[40] && rdy && !m[15]) begin
    if (!m[13]) di = m[14] ? 8'hFF : attr(m[39:25]);
    else if (!m[11] && io && !m[14])
      case (m[26:25])
        2'd0: di = da ? ob[op] : 8'h00;
        2'd1: di = {da, fr(), 4'h0, we, re};
        2'd2: di = 8'(on);
        default: di = 8'(on >> 8);
      endcase
  end
  return {1'b0, di, wn, io ? !((daie && da) || (frie && fr())) : rdy, md, mv, ms};
endfunction
function void clear();
  hc = 0; sr = 0; daie = 0; frie = 0; rsh = 0; rcnt = 0; we = 0; re = 0;
  proc = 0; on = 0; st_q = 0; wn = 1;
endfunction
function void step(bit [41:0] m);
  bit [3:0] st;
  if (!m[41]) begin
    rdy = 0; rc = 0; io = 0; cor = 0; clear(); mv = 0; ms = 0; md = 0; tidx = 0;
    return;
  end
  st = (rdy && !m[15]) ? {!m[10], !m[11], !m[12], !m[13]} : 4'h0;
  if (m[40]) begin rdy = 0; rc = 0; io = 0; cor = 0; clear(); end
  else begin
    if (!rdy) begin rc++; if (rc == RDY_DLY) rdy = 1; end
    if (rcnt != 0) rcnt--;
    if (proc) begin
      pc--;
      if (pc == 0) begin
        for (int i = 0; i < BUF; i++) ob[i] = (i < 2) ? ib[i] : ib[i] ^ 8'h5A;
        on = pn; op = 0; proc = 0;
      end
    end
    if (st != 0) begin al = m[39:25]; dl = m[24:17]; regl = m[14]; end
    if (st != 0 && st_q == 0) wc = WAIT;
    else if (st != 0 && wc != 0) wc--;
    wn = !(st != 0 && wc != 0);
    if (st == 0 && st_q != 0 && !regl) begin
      if (st_q[1] && al == COR_ADDR) begin cor = dl; io = dl[5:0] == CFG_IDX; end
      if (st_q[2] && io && al[1:0] == 2'd0) begin
        if (on != 0) begin op++; if (op == on) on = 0; end
        else re = 1;
      end
      if (st_q[3] && io)
        case (al[1:0])
          2'd0: begin
            if (hc && hc_ok) begin
              if (icnt < BUF) ib[icnt] = dl; else we = 1;
              if (icnt < 65535) icnt++;
            end else we = 1;
          end
          2'd1: begin
            daie = dl[7]; frie = dl[6];
            if (dl[3]) begin
              hc = 0; proc = 0; on = 0; we = 0; re = 0; rsh = 1;
            end else begin
              if (rsh) begin rsh = 0; rcnt = RS_DLY; end
              if (dl[2] && !sr && on == 0 && !proc) begin ob[0] = 8'(BUF >> 8); ob[1] = 8'(BUF); on = 2; op = 0; end
              sr = dl[2];
              if (dl[0] && !hc) begin hc = 1; hc_ok = fr(); icnt = 0; end
              else if (!dl[0] && hc) begin
                hc = 0;
                if (hc_ok && icnt != 0) begin
                  if (icnt == sz && icnt <= BUF) begin proc = 1; pc = PROC; pn = icnt; end
                  else we = 1;
                end
              end
            end
          end
          2'd2: sz = (sz & 32'hFF00) | int'(dl);
          default: sz = (sz & 32'h00FF) | (int'(dl) << 8);
        endcase
    end
    st_q = st;
  end
  // the stream through the CAM
  mv = m[1]; ms = m[1] && m[0];
  if (m[1]) begin
    tidx = m[0] ? 0 : (tidx == 255 ? 255 : tidx + 1);
    if (tidx == 3) begin tscr = m[9:8] != 0; md = {2'b00, m[7:2]}; end
    else if (tidx >= 4 && tscr) md = m[9:2] ^ (KEY ^ 8'(tidx));
    else md = m[9:2];
  end else md = 0;
endfunction
""",
    predict="""
foreach (t.pre[i]) step(t.pre[i]);
t.so.delete();
foreach (t.mo[i]) begin
  t.so.push_back(outs(t.mo[i]));
  step(t.mo[i]);
end
""",
    checks="",
    coverage="""
cp_kind : coverpoint tr.kind;
cp_tim  : coverpoint {tr.sup, tr.stb} { bins s[] = {[0:15]}; }
""",
    directed="""
t = item(); t.set(2, 3); send(t);            // off: nothing answers
t = item(); t.set(0); send(t);
t = item(); t.set(2, 63); send(t);           // the whole CIS and past it
t = item(); t.set(11); send(t);
t = item(); t.set(5, 4); send(t);            // memory mode: I/O ignored
t = item(); t.set(3, 0, 32'd0); send(t);     // COR 01: no I/O mode
t = item(); t.set(3, 0, 32'd2); send(t);     // COR 4F: I/O mode
t = item(); t.set(4); send(t);
t = item(); t.set(9); send(t);               // buffer size
t = item(); t.set(5, 9); send(t);
t = item(); t.set(6); send(t);
t = item(); t.set(7, 63, 32'h55); send(t);   // 64 bytes
t = item(); t.set(5, 64); send(t);           // 65 bytes: WE
t = item(); t.set(6); send(t);
t = item(); t.set(4); send(t);
t = item(); t.set(15, 5); send(t);
t = item(); t.set(14); send(t);
t = item(); t.set(8); send(t);
t = item(); t.set(4); send(t);
t = item(); t.set(5, 3); send(t);
t = item(); t.set(5, 3, 32'h9); send(t);     // FR low: the second message is refused
t = item(); t.set(6); send(t);
t = item(); t.set(13, 0, 32'd3); send(t);
t = item(); t.set(5, 7); send(t);
t = item(); t.set(13, 0, 32'd1); send(t);
t = item(); t.set(6); send(t);
t = item(); t.set(13, 0, 32'd0); send(t);
t = item(); t.set(10, 0, 32'd0); send(t);
t = item(); t.set(10, 0, 32'd1); send(t);
t = item(); t.set(10, 0, 32'd3); send(t);
t = item(); t.set(12, 2); send(t);
t = item(); t.set(3, 0, 32'd1); send(t);
t = item(); t.set(5, 2); send(t);
t = item(); t.set(0); send(t);               // RESET with a reply pending
t = item(); t.set(11); send(t);
t = item(); t.set(1); send(t);
t = item(); t.set(10, 0, 32'd1); send(t);    // off: no stream
t = item(); t.set(0); send(t);
t = item(); t.set(3, 0, 32'd1); send(t);
for (int i = 0; i < 4; i++) begin
  t = item(); t.set(7, 20 + i, i); t.sup = i; t.stb = 3 - i; t.hld = i % 3; send(t);
end
""",
    drain_ns=20000,
    model="""
module cam_model #(
  parameter int          RDY_DLY  = 20,
  parameter int          WAIT     = 2,
  parameter int          RS_DLY   = 10,
  parameter int          PROC     = 16,
  parameter int          BUF      = 64,
  parameter logic [14:0] COR_ADDR = 15'h0FFE,
  parameter logic [5:0]  CFG_IDX  = 6'h0F,
  parameter logic [7:0]  KEY      = 8'hC5
) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        ci_vcc_en,
  input  logic        ci_reset,
  input  logic [14:0] ci_a,
  input  logic [7:0]  ci_d_o,
  input  logic        ci_d_oe,
  input  logic        ci_ce_n,
  input  logic        ci_reg_n,
  input  logic        ci_oe_n,
  input  logic        ci_we_n,
  input  logic        ci_iord_n,
  input  logic        ci_iowr_n,
  input  logic [7:0]  ci_mo_data,
  input  logic        ci_mo_val,
  input  logic        ci_mo_strt,
  output logic        ci_cd_n,
  output logic [7:0]  ci_d_i,
  output logic        ci_wait_n,
  output logic        ci_ireq_n,
  output logic [7:0]  ci_mi_data,
  output logic        ci_mi_val,
  output logic        ci_mi_strt
);
  localparam int AW = $clog2(BUF);
%s
  logic        rdy, io, hc, hc_ok, sr, daie, frie, rsh, we, re, proc, regl, tscr, wn;
  logic [15:0] rc, rcnt, icnt, sz, pc, pn, on, op;
  logic [7:0]  cor, wc, dl, tidx;
  logic [14:0] al;
  logic [3:0]  st_q;
  logic [7:0]  ib [0:BUF-1];
  logic [7:0]  ob [0:BUF-1];
  wire         fr     = !rsh && rcnt == 16'd0 && !proc && on == 16'd0;
  wire         da     = on != 16'd0;
  wire  [3:0]  st_now = (rdy && !ci_ce_n) ? {!ci_iowr_n, !ci_iord_n, !ci_we_n, !ci_oe_n} : 4'h0;

  function automatic logic [7:0] attr(input logic [14:0] ad);
    if (ad[0]) attr = 8'hFF;
    else if (ad == COR_ADDR) attr = cor;
    else attr = cis(ad[14:1]);
  endfunction

  assign ci_cd_n   = 1'b0;                      // inserted
  assign ci_wait_n = wn;
  assign ci_ireq_n = io ? !((daie && da) || (frie && fr)) : rdy;
  always_comb begin
    ci_d_i = 8'h00;
    if (ci_vcc_en && !ci_reset && rdy && !ci_ce_n) begin
      if (!ci_oe_n) ci_d_i = ci_reg_n ? 8'hFF : attr(ci_a);
      else if (!ci_iord_n && io && !ci_reg_n)
        case (ci_a[1:0])
          2'd0:    ci_d_i = da ? ob[op[AW-1:0]] : 8'h00;
          2'd1:    ci_d_i = {da, fr, 4'h0, we, re};
          2'd2:    ci_d_i = on[7:0];
          default: ci_d_i = on[15:8];
        endcase
    end
  end

  // no reset of its own: a PC card starts over when VCC is off (rst_n and ci_d_oe are not used)
  always_ff @(posedge clk) begin
    begin : step
      logic        v_rdy, v_io, v_hc, v_hc_ok, v_sr, v_daie, v_frie, v_rsh, v_we, v_re, v_proc, v_regl,
                   v_tscr, v_wn, v_fr;
      logic [15:0] v_rc, v_rcnt, v_icnt, v_sz, v_pc, v_pn, v_on, v_op;
      logic [7:0]  v_cor, v_wc, v_dl, v_tidx, v_md;
      logic [14:0] v_al;
      logic [3:0]  v_st_q, st;
      v_rdy = rdy; v_io = io; v_hc = hc; v_hc_ok = hc_ok; v_sr = sr; v_daie = daie; v_frie = frie; v_rsh = rsh;
      v_we = we; v_re = re; v_proc = proc; v_regl = regl; v_tscr = tscr; v_wn = wn;
      v_rc = rc; v_rcnt = rcnt; v_icnt = icnt; v_sz = sz; v_pc = pc; v_pn = pn; v_on = on; v_op = op;
      v_cor = cor; v_wc = wc; v_dl = dl; v_tidx = tidx; v_al = al; v_st_q = st_q;
      st = st_now;
      if (!ci_vcc_en || ci_reset) begin
        // power off or RESET: the card starts over (power off also stops the stream)
        v_rdy = 1'b0; v_rc = '0; v_io = 1'b0; v_cor = '0;
        v_hc = 1'b0; v_sr = 1'b0; v_daie = 1'b0; v_frie = 1'b0; v_rsh = 1'b0; v_rcnt = '0;
        v_we = 1'b0; v_re = 1'b0; v_proc = 1'b0; v_on = '0; v_st_q = '0; v_wn = 1'b1;
      end else begin
        if (!v_rdy) begin v_rc = v_rc + 16'd1; if (v_rc == 16'(RDY_DLY)) v_rdy = 1'b1; end
        if (v_rcnt != 0) v_rcnt = v_rcnt - 16'd1;
        if (v_proc) begin
          v_pc = v_pc - 16'd1;
          if (v_pc == 0) begin
            for (int i = 0; i < BUF; i++) ob[i] <= (i < 2) ? ib[i] : ib[i] ^ 8'h5A;   // read up to v_pn
            v_on = v_pn; v_op = '0; v_proc = 1'b0;
          end
        end
        if (st != 0) begin v_al = ci_a; v_dl = ci_d_o; v_regl = ci_reg_n; end
        if (st != 0 && v_st_q == 0) v_wc = 8'(WAIT);
        else if (st != 0 && v_wc != 0) v_wc = v_wc - 8'd1;
        v_wn = !(st != 0 && v_wc != 0);
        if (st == 0 && v_st_q != 0 && !v_regl) begin
          if (v_st_q[1] && v_al == COR_ADDR) begin v_cor = v_dl; v_io = v_dl[5:0] == CFG_IDX; end
          if (v_st_q[2] && v_io && v_al[1:0] == 2'd0) begin
            if (v_on != 0) begin
              v_op = v_op + 16'd1;
              if (v_op == v_on) v_on = '0;
            end else v_re = 1'b1;
          end
          if (v_st_q[3] && v_io)
            case (v_al[1:0])
              2'd0: begin
                if (v_hc && v_hc_ok) begin
                  if (v_icnt < 16'(BUF)) ib[v_icnt[AW-1:0]] <= v_dl; else v_we = 1'b1;
                  if (v_icnt != 16'hFFFF) v_icnt = v_icnt + 16'd1;
                end else v_we = 1'b1;
              end
              2'd1: begin
                v_daie = v_dl[7]; v_frie = v_dl[6];
                if (v_dl[3]) begin
                  v_hc = 1'b0; v_proc = 1'b0; v_on = '0; v_we = 1'b0; v_re = 1'b0; v_rsh = 1'b1;
                end else begin
                  if (v_rsh) begin v_rsh = 1'b0; v_rcnt = 16'(RS_DLY); end
                  if (v_dl[2] && !v_sr && v_on == 0 && !v_proc) begin
                    {ob[0], ob[1]} <= 16'(BUF); v_on = 16'd2; v_op = '0;
                  end
                  v_sr = v_dl[2];
                  v_fr = !v_rsh && v_rcnt == 0 && !v_proc && v_on == 0;
                  if (v_dl[0] && !v_hc) begin v_hc = 1'b1; v_hc_ok = v_fr; v_icnt = '0; end
                  else if (!v_dl[0] && v_hc) begin
                    v_hc = 1'b0;
                    if (v_hc_ok && v_icnt != 0) begin
                      if (v_icnt == v_sz && v_icnt <= 16'(BUF)) begin v_proc = 1'b1; v_pc = 16'(PROC); v_pn = v_icnt; end
                      else v_we = 1'b1;
                    end
                  end
                end
              end
              2'd2:    v_sz[7:0]  = v_dl;
              default: v_sz[15:8] = v_dl;
            endcase
        end
        v_st_q = st;
      end
      // the stream through the CAM
      v_md = '0;
      if (!ci_vcc_en) begin
        v_tidx = '0;
        ci_mi_val <= 1'b0; ci_mi_strt <= 1'b0;
      end else begin
        if (ci_mo_val) begin
          v_tidx = ci_mo_strt ? 8'd0 : (v_tidx == 8'hFF) ? 8'hFF : v_tidx + 8'd1;
          if (v_tidx == 8'd3) begin v_tscr = ci_mo_data[7:6] != 2'b00; v_md = {2'b00, ci_mo_data[5:0]}; end
          else if (v_tidx >= 8'd4 && v_tscr) v_md = ci_mo_data ^ (KEY ^ v_tidx);
          else v_md = ci_mo_data;
        end
        ci_mi_val <= ci_mo_val; ci_mi_strt <= ci_mo_val && ci_mo_strt;
      end
      ci_mi_data <= v_md;
      rdy <= v_rdy; io <= v_io; hc <= v_hc; hc_ok <= v_hc_ok; sr <= v_sr; daie <= v_daie; frie <= v_frie;
      rsh <= v_rsh; we <= v_we; re <= v_re; proc <= v_proc; regl <= v_regl; tscr <= v_tscr;
      wn <= v_wn; rc <= v_rc; rcnt <= v_rcnt; icnt <= v_icnt; sz <= v_sz; pc <= v_pc; pn <= v_pn; on <= v_on;
      op <= v_op; cor <= v_cor; wc <= v_wc; dl <= v_dl; tidx <= v_tidx; al <= v_al; st_q <= v_st_q;
    end
  end
endmodule
""" % MODEL_CIS,
    sva="""
assert property (@(posedge clk) disable iff (!rst_n)
  !$isunknown({ci_cd_n, ci_d_i, ci_wait_n, ci_ireq_n, ci_mi_data, ci_mi_val, ci_mi_strt}))
  else $error("CAM: X on a CAM output");
assert property (@(posedge clk) disable iff (!rst_n) ci_ce_n |-> ci_d_i == 8'h00)
  else $error("CAM: data driven with CE# high");
assert property (@(posedge clk) disable iff (!rst_n) ci_mi_strt |-> ci_mi_val)
  else $error("CAM: MISTRT without MIVAL");
cover property (@(posedge clk) disable iff (!rst_n) !ci_wait_n);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;
always #5 clk = ~clk;

logic        vcc = 0, rs = 0, doe = 0, ce = 1, rg = 1, oe = 1, we = 1, ir = 1, iw = 1, tv = 0, tst = 0;
logic [14:0] a = 0;
logic [7:0]  d = 0, td = 0;
wire         cd_n, wait_n, ireq_n, mv, ms;
wire  [7:0]  di, md;

cam_model u_dut (.clk(clk), .rst_n(rst_n), .ci_vcc_en(vcc), .ci_reset(rs), .ci_a(a), .ci_d_o(d), .ci_d_oe(doe),
                 .ci_ce_n(ce), .ci_reg_n(rg), .ci_oe_n(oe), .ci_we_n(we), .ci_iord_n(ir), .ci_iowr_n(iw),
                 .ci_mo_data(td), .ci_mo_val(tv), .ci_mo_strt(tst), .ci_cd_n(cd_n), .ci_d_i(di),
                 .ci_wait_n(wait_n), .ci_ireq_n(ireq_n), .ci_mi_data(md), .ci_mi_val(mv), .ci_mi_strt(ms));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// one clock: inputs change after the falling edge, outputs are looked at just before the rising edge
integer nwait;
task automatic clk1();
  @(negedge clk);
  @(posedge clk); #1;
endtask
task automatic idle(input integer n); repeat (n) clk1(); endtask
integer sup = 0, stb = 3, hld = 0;
logic [7:0] rd;
// k 0 attribute read, 1 attribute write, 2 I/O read, 3 I/O write, 4 common read, 5 common write
task automatic cyc(input integer k, input logic [14:0] ad, input logic [7:0] wd);
  @(negedge clk);
  ce = 0; rg = (k >= 4); a = ad;
  if (k == 1 || k == 3 || k == 5) begin d = wd; doe = 1; end
  repeat (sup + 1) clk1();
  @(negedge clk);
  case (k) 1, 5: we = 0; 2: ir = 0; 3: iw = 0; default: oe = 0; endcase
  nwait = 0;
  repeat (stb + 1) begin @(posedge clk); #1; if (!wait_n) nwait = nwait + 1; @(negedge clk); end
  while (!wait_n) begin @(posedge clk); #1; if (!wait_n) nwait = nwait + 1; @(negedge clk); end
  rd = di;
  oe = 1; we = 1; ir = 1; iw = 1;
  repeat (hld + 1) clk1();
  @(negedge clk);
  ce = 1; rg = 1; doe = 0; d = 0; a = 0;
endtask
task automatic st_rd(); cyc(2, 15'd1, 8'h00); endtask
task automatic cmd(input logic [7:0] c); cyc(3, 15'd1, c); endtask
logic [7:0] r [0:127];
integer nr;
task automatic msg_out(input integer n, input integer seed, input integer short_by);
  cmd(8'h01); cyc(3, 15'd2, 8'(n)); cyc(3, 15'd3, 8'(n >> 8));
  for (int i = 0; i < n - short_by; i++) cyc(3, 15'd0, 8'(i * 13 + seed));
  cmd(8'h00);
endtask
task automatic msg_in();
  logic [7:0] lo, hi;
  cmd(8'h04); cyc(2, 15'd2, 0); lo = rd; cyc(2, 15'd3, 0); hi = rd; cmd(8'h00);
  nr = {hi, lo};
  for (int i = 0; i < nr && i < 128; i++) begin cyc(2, 15'd0, 0); r[i] = rd; end
endtask
function automatic logic [7:0] cisb(input integer k);
  logic [7:0] t [0:56];
  t = '{8'h1D, 8'h04, 8'h00, 8'hDB, 8'h08, 8'hFF, 8'h1C, 8'h03, 8'h00, 8'h08, 8'hFF, 8'h15, 8'h0E, 8'h05, 8'h00,
        8'h44, 8'h56, 8'h42, 8'h20, 8'h43, 8'h41, 8'h4D, 8'h00, 8'h56, 8'h31, 8'h00, 8'hFF, 8'h1A, 8'h15, 8'h01,
        8'h0F, 8'hFE, 8'h0F, 8'h01, 8'hC0, 8'h0E, 8'h41, 8'h02, 8'h44, 8'h56, 8'h42, 8'h5F, 8'h43, 8'h49, 8'h5F,
        8'h56, 8'h31, 8'h2E, 8'h30, 8'h30, 8'h1B, 8'h02, 8'hCF, 8'h00, 8'h14, 8'h00, 8'hFF};
  return t[k];
endfunction
logic ok;
integer n, cnt;

// the stream: send a packet, compare what comes out one clock later
logic [7:0] pin [0:187];
logic [7:0] pout [$];
logic       sop [$];
always @(posedge clk) if (mv) begin pout.push_back(md); sop.push_back(ms); end
task automatic ts_pkt(input logic scr, input logic gaps);
  pout.delete(); sop.delete();
  for (int i = 0; i < 188; i++) begin
    pin[i] = (i == 0) ? 8'h47 : (i == 3) ? (scr ? 8'hD3 : 8'h13) : 8'(i * 31 + 7);
    @(negedge clk); td = pin[i]; tv = 1; tst = (i == 0);
    if (gaps && i == 90) begin @(negedge clk); tv = 0; tst = 0; end
  end
  @(negedge clk); tv = 0; tst = 0; td = 0;
  idle(3);
endtask

initial begin
  repeat (3) @(posedge clk);
  rst_n = 1;
  idle(2);
  chk(cd_n === 1'b0, "card detect low");
  chk(ireq_n === 1'b0 && wait_n === 1'b1 && di === 8'h00 && md === 8'h00 && !mv, "VCC off: outputs idle");
  cyc(0, 15'd0, 0); chk(rd === 8'h00, "VCC off: no data");
  // power up: READY RDY_DLY clocks after RESET falls
  @(negedge clk); vcc = 1; idle(3);
  @(negedge clk); rs = 1; idle(10);
  chk(ireq_n === 1'b0, "READY low in RESET");
  @(negedge clk); rs = 0;
  cnt = 0;
  while (!ireq_n && cnt < 100) begin cyc(0, 15'd0, 0); cnt = cnt + 1; if (!ireq_n) chk(rd === 8'h00, "not ready: no data"); end
  chk(ireq_n === 1'b1, "READY after RESET");
  @(negedge clk); rs = 1; @(negedge clk); rs = 0; cnt = 0;
  while (!ireq_n) begin @(posedge clk); #1; cnt = cnt + 1; end
  chk(cnt == 20, "READY 20 clocks after RESET");
  // the CIS, odd addresses, beyond it, common memory, I/O in memory mode
  ok = 1;
  for (int k = 0; k < 57; k++) begin cyc(0, 15'(2 * k), 0); if (rd !== cisb(k)) ok = 0; end
  chk(ok, "CIS bytes at even addresses");
  cyc(0, 15'd1, 0); chk(rd === 8'hFF, "odd attribute address FF");
  cyc(0, 15'd114, 0); chk(rd === 8'hFF, "past the CIS FF");
  cyc(0, 15'h7FFE, 0); chk(rd === 8'hFF, "top of attribute memory FF");
  cyc(4, 15'd0, 0); chk(rd === 8'hFF, "common memory FF");
  chk(nwait == 2, "WAIT# low for 2 clocks of the strobe");
  cyc(2, 15'd1, 0); chk(rd === 8'h00, "I/O read in memory mode: not driven");
  cyc(0, 15'h0FFE, 0); chk(rd === 8'h00, "COR 00 after RESET");
  // read-only CIS; common writes ignored
  cyc(1, 15'd4, 8'h55); cyc(0, 15'd4, 0); chk(rd === 8'h00, "CIS not writable");
  cyc(5, 15'h0FFE, 8'h0F); cyc(0, 15'h0FFE, 0); chk(rd === 8'h00, "common-memory write is not the COR");
  // COR
  cyc(1, 15'h0FFE, 8'h01); cyc(0, 15'h0FFE, 0); chk(rd === 8'h01, "COR read back");
  st_rd(); chk(rd === 8'h00, "COR 01: still memory mode");
  chk(ireq_n === 1'b1, "memory mode: READY on IREQ#");
  cyc(1, 15'h0FFC, 8'h0F); st_rd(); chk(rd === 8'h00, "a write next to the COR is not the COR");
  cyc(1, 15'h0FFE, 8'h4F); st_rd(); chk(rd === 8'h40, "COR 4F: I/O mode, FR");
  cyc(1, 15'h0FFE, 8'h0E); st_rd(); chk(rd === 8'h00, "COR 0E leaves I/O mode");
  cyc(1, 15'h0FFE, 8'h0F); st_rd(); chk(rd === 8'h40, "COR 0F: I/O mode");
  // memory-mode reads still work in I/O mode
  cyc(0, 15'd2, 0); chk(rd === 8'h04, "attribute read in I/O mode");
  // interface reset
  cmd(8'h08); st_rd(); chk(rd === 8'h00, "RS: FR low");
  cmd(8'h00); cnt = 0;
  st_rd(); chk(rd === 8'h00, "FR still low just after RS");
  idle(10); st_rd(); chk(rd === 8'h40, "FR back after RS_DLY");
  // buffer size
  cmd(8'h04); st_rd(); chk(rd === 8'h80, "SR: DA, FR low");
  cyc(2, 15'd2, 0); chk(rd === 8'h02, "size 2");
  cyc(2, 15'd3, 0); chk(rd === 8'h00, "size MS 0");
  cmd(8'h00);
  cyc(2, 15'd0, 0); chk(rd === 8'h00, "buffer size MS");
  st_rd(); chk(rd === 8'h80, "one byte left, FR low while a reply waits");
  cyc(2, 15'd0, 0); chk(rd === 8'h40, "buffer size LS 64");
  st_rd(); chk(rd === 8'h40, "read out: DA clear, FR");
  cyc(2, 15'd0, 0); st_rd(); chk(rd === 8'h41, "empty DATA read: RE");
  cmd(8'h08); cmd(8'h00); idle(12); st_rd(); chk(rd === 8'h40, "RS clears RE");
  // a 10-byte message and its reply
  msg_out(10, 3, 0);
  st_rd(); chk(rd === 8'h00, "processing: FR low, no DA");
  idle(16); st_rd(); chk(rd === 8'h80, "reply ready: DA");
  msg_in(); ok = nr == 10;
  for (int i = 0; i < 10; i++) if (r[i] !== ((i < 2) ? 8'(i * 13 + 3) : 8'(i * 13 + 3) ^ 8'h5A)) ok = 0;
  chk(ok, "reply: link header kept, body XOR 5A");
  st_rd(); chk(rd === 8'h40, "reply read: FR");
  // processing time: HC cleared (with DAIE) to IREQ#
  cmd(8'h01); cyc(3, 15'd2, 8'h01); cyc(3, 15'd3, 8'h00); cyc(3, 15'd0, 8'h77);
  @(negedge clk); ce = 0; rg = 0; a = 15'd1; d = 8'h80; doe = 1; clk1(); @(negedge clk); iw = 0; repeat (4) clk1();
  @(negedge clk); iw = 1; cnt = 0;
  while (ireq_n && cnt < 100) begin @(posedge clk); #1; cnt = cnt + 1; end
  @(negedge clk); ce = 1; rg = 1; doe = 0; a = 0; d = 0;
  chk(cnt == 17, "reply PROC clocks after HC is cleared");
  cmd(8'h00); msg_in(); chk(nr == 1 && r[0] === 8'h77, "1-byte message");
  // 64 bytes is the most
  msg_out(64, 9, 0); idle(20); msg_in(); chk(nr == 64 && r[63] === (8'(63 * 13 + 9) ^ 8'h5A) && r[1] === 8'(13 + 9), "64-byte message");
  msg_out(65, 1, 0); st_rd(); chk(rd === 8'h42, "65 bytes: WE");
  idle(20); st_rd(); chk(rd === 8'h42, "and no reply");
  cmd(8'h08); cmd(8'h00); idle(12); st_rd(); chk(rd === 8'h40, "RS clears WE");
  // size mismatch, DATA without HC
  msg_out(6, 1, 1); idle(20); st_rd(); chk(rd === 8'h42, "size mismatch: WE, no reply");
  cmd(8'h08); cmd(8'h00); idle(12);
  cyc(3, 15'd0, 8'h11); st_rd(); chk(rd === 8'h42, "DATA write without HC: WE");
  cmd(8'h08); cmd(8'h00); idle(12);
  cmd(8'h00); cyc(3, 15'd0, 8'h11); st_rd(); chk(rd === 8'h42, "COMMAND 00 opens no message");
  cmd(8'h08); cmd(8'h00); idle(12);
  cmd(8'h01); cyc(3, 15'd0, 8'h21); cmd(8'h01); cyc(3, 15'd0, 8'h22); cyc(3, 15'd2, 8'h02); cyc(3, 15'd3, 8'h00);
  cmd(8'h00); idle(20); msg_in(); chk(nr == 2 && r[0] === 8'h21 && r[1] === 8'h22, "HC written twice: one message");
  cmd(8'h08); cmd(8'h00); idle(12);
  // HC while FR is low: refused
  msg_out(3, 5, 0); msg_out(3, 6, 0); st_rd(); chk(rd === 8'h82, "message while FR low (reply waiting): WE");
  idle(20); msg_in(); chk(nr == 3 && r[2] === (8'(26 + 5) ^ 8'h5A), "only the first is answered");
  cmd(8'h08); cmd(8'h00); idle(12);
  // the size registers follow the reply; SR with a reply waiting does not queue the buffer size
  msg_out(5, 2, 0); idle(20); cmd(8'h04); cyc(2, 15'd2, 0); chk(rd === 8'h05, "SIZE shows the reply");
  cmd(8'h00); for (int i = 0; i < 5; i++) cyc(2, 15'd0, 0); st_rd(); chk(rd === 8'h40, "no buffer size after a reply");
  // a message of 256 + 2 bytes: SIZE_MS counts
  cmd(8'h01); cyc(3, 15'd2, 8'h02); cyc(3, 15'd3, 8'h01); cyc(3, 15'd0, 8'h01); cyc(3, 15'd0, 8'h02); cmd(8'h00);
  st_rd(); chk(rd === 8'h42, "SIZE_MS: 258 does not match 2");
  cmd(8'h08); cmd(8'h00); idle(12);
  // IREQ#
  cmd(8'h40); chk(ireq_n === 1'b0, "FRIE with FR: IREQ# low");
  cmd(8'h80); chk(ireq_n === 1'b1, "DAIE without DA: IREQ# high");
  cmd(8'h81); cyc(3, 15'd2, 8'h02); cyc(3, 15'd3, 0); cyc(3, 15'd0, 8'hAA); cyc(3, 15'd0, 8'hBB); cmd(8'h80);
  idle(20); chk(ireq_n === 1'b0, "DAIE with DA: IREQ# low");
  cmd(8'hC0); chk(ireq_n === 1'b0, "both");
  cmd(8'h00); chk(ireq_n === 1'b1, "disabled");
  for (int i = 0; i < 2; i++) cyc(2, 15'd0, 0);
  chk(rd === 8'hBB, "the reply of the IREQ message");
  // the stream
  ts_pkt(0, 0); ok = pout.size() == 188 && sop.size() == 188 && sop[0] && !sop[1];
  for (int i = 0; i < 188 && ok; i++) if (pout[i] !== pin[i]) ok = 0;
  chk(ok, "clear packet passes unchanged");
  ts_pkt(1, 1); ok = pout.size() == 188 && pout[3] === 8'h13 && pout[0] === 8'h47 && pout[2] === pin[2];
  for (int i = 4; i < 188 && ok; i++) if (pout[i] !== (pin[i] ^ 8'hC5 ^ 8'(i))) ok = 0;
  chk(ok, "scrambled packet with a gap: SC cleared, payload descrambled");
  @(negedge clk); td = 8'h47; tv = 1; tst = 1; #1;
  chk(!mv, "the stream is registered"); @(posedge clk); #1; chk(mv && ms && md === 8'h47, "and comes out after the clock");
  @(negedge clk); td = 8'h12; tst = 0; tv = 0; @(posedge clk); #1; @(posedge clk); #1; chk(!mv && md === 8'h00, "MIVAL low: data 0");
  // RESET in I/O mode with a reply waiting: everything cleared
  msg_out(4, 7, 0); idle(20);
  @(negedge clk); rs = 1; @(posedge clk); #1; chk(di === 8'h00, "RESET: no data");
  idle(2); @(negedge clk); rs = 0; idle(25);
  st_rd(); chk(rd === 8'h00, "after RESET: memory mode");
  cyc(0, 15'h0FFE, 0); chk(rd === 8'h00, "COR cleared");
  cyc(1, 15'h0FFE, 8'h0F); st_rd(); chk(rd === 8'h40, "I/O mode again, no reply left");
  cyc(2, 15'd0, 0); chk(rd === 8'h00, "DATA empty");
  msg_out(3, 8, 0); idle(20); msg_in(); chk(nr == 3 && r[2] === (8'(26 + 8) ^ 8'h5A), "a message right after RESET");
  // the cycle uses the address and data of the strobe's last clock, not what follows it
  cmd(8'h08); cmd(8'h00); idle(12);
  @(negedge clk); ce = 0; rg = 0; a = 15'd1; d = 8'h40; doe = 1; clk1();
  @(negedge clk); iw = 0; repeat (5) clk1();
  @(negedge clk); iw = 1; a = 15'd0; d = 8'h99; clk1();
  @(negedge clk); ce = 1; rg = 1; doe = 0; a = 0; d = 0;
  chk(ireq_n === 1'b0, "COMMAND written from the strobe's address (FRIE)");
  cmd(8'h00); cyc(2, 15'd0, 0); st_rd(); chk(rd === 8'h41, "and no DATA write");
  cmd(8'h08); cmd(8'h00); idle(12);
  // power off (with SR set, the stream running)
  cmd(8'h04); msg_in();
  cmd(8'h04);
  ts_pkt(1, 0);
  @(negedge clk); vcc = 0; td = 8'h47; tv = 1; tst = 1; idle(3);
  chk(!mv && md === 8'h00 && ireq_n === 1'b0, "VCC off: no stream, no READY");
  @(negedge clk); tv = 0; tst = 0; vcc = 1; idle(25);
  st_rd(); chk(rd === 8'h00, "power cycle: memory mode");
  cyc(1, 15'h0FFE, 8'h0F); cmd(8'h04); st_rd(); chk(rd === 8'h80, "SR after power: buffer size");
  cmd(8'h00); msg_in(); cyc(1, 15'h0FFE, 8'h00);
  cyc(0, 15'h0FFE, 0); chk(rd === 8'h00, "COR cleared by power");
  // setup / strobe / hold variety: the CAM answers the same
  sup = 3; stb = 5; hld = 2; cyc(0, 15'd30, 0); chk(rd === cisb(15), "long cycle");
  sup = 0; stb = 0; hld = 0; cyc(0, 15'd30, 0); chk(rd === cisb(15), "short strobe: WAIT# stretches it");
  chk(nwait == 2, "WAIT# 2 clocks");
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
