# SCCB / I2C camera sensor control VIP: a sensor register target model (the
# image sensor's control port on an IP camera) with a controller agent.
#
# Agent -> DUT: scl (push-pull, as I2C_Host_top drives it) and sda_m_lo (the
# controller pulls SDA low). DUT -> agent: sda_s_lo (the target pulls SDA
# low). The line is SDA = !(sda_m_lo | sda_s_lo); one quarter of the SCL
# period is cfg.q clocks.
#
# tb/top_tb.sv sccb_model is the sensor's control target, 7-bit address 0x3C,
# 16-bit register addresses, 8-bit data (the usual camera sensor layout):
#   write   S, 0x78, ACK, REG[15:8], ACK, REG[7:0], ACK, {DATA, ACK}..., P
#           (the register address auto-increments; one byte only sets the
#           high half, the pointer is unchanged)
#   read    S, 0x78, REG hi, REG lo, then Sr (I2C) or P, S (SCCB two-phase),
#           0x79, ACK, {DATA, ACK / NACK}..., P: data from the pointer, which
#           increments per byte; a NACK ends the read
#   registers 0x0000 / 0x0001 = chip ID 0x5A / 0x31 (read only), 0x0002 -
#   0x01FF read / write (reset 0x00), the rest read 0x00 and ignore writes.
#   Any other device address gets no ACK and the target ignores the bus until
#   the next START. The target samples SCL / SDA on its own clock (two-flop
#   synchronisers), so a quarter period must be 3 clocks or more.
# In a SoC bench it connects to I2C_Host_top (open-ip-portfolio):
# sda_m_lo <= (sda == 0) and sda pulled low while sda_s_lo; the agent then
# runs passive and its monitor decodes every transaction.

SPEC = dict(
    vip="SCCB_Sensor-UVM-VIP", p="sccb", P="SCCB", dir="sccb", family="Peripherals",
    desc="SCCB / I2C camera sensor control VIP: sensor register target model (16-bit register addresses, "
         "auto-increment, chip ID, I2C repeated-START and SCCB two-phase reads, address NACK) with a "
         "controller agent and a bus monitor.",
    about="""
An IP camera's SoC sets up its image sensor over SCCB / I2C: exposure,
gain, window and test pattern registers behind a 16-bit register address.
The VIP's DUT model is that sensor's control target, so a SoC bench can hang
it on the I2C controller's pins (I2C_Host_top in open-ip-portfolio). The
agent is a controller that writes register blocks, reads them back with a
repeated START and with SCCB's STOP / START two-phase read, reads the chip
ID, writes the read-only ID and unmapped registers, reads across the end of
the register file, sets only half a register address, NACKs the address of
another device and sends empty START / STOP pairs. The scoreboard keeps its
own copy of the register file and pointer and predicts the target's SDA
drive at every SCL rising edge (address and data ACKs, every read data bit,
the release for the controller's ACK / NACK).""",
    timeout=20000,
    cfg="""int unsigned q = 4;          // clocks per SCL quarter period (>= 3)
bit [6:0]    dev = 7'h3C;    // the sensor's 7-bit address""",
    ports=[
        ("in", "logic", "scl"), ("in", "logic", "sda_m_lo"),
        ("out", "logic", "sda_s_lo"),
    ],
    fields=[
        ("bit [1:0]", "ev", "req", "q"),       # per SCL rise {0, sda_m_lo}; 2'b10 START, 2'b11 STOP
        ("bit", "so", "rsp", "q"),             # sda_s_lo at each SCL rise
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [15:0]", "reg_a", "info", "rand"),
        ("bit [2:0]", "n", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [7:0]", "rd", "info", "q"),      # decoded: bytes the target sent
    ],
    tr_functions="""
// kind: 0-7 write 1-8 registers, 8-13 read with a repeated START, 14 write
// the pointer only (SCCB phase 1), 15 current-address read (SCCB phase 2),
// 16 write to another address, 17 read from another address, 18 write the
// chip ID, 19 read the chip ID, 20 write past 0x01FF, 21 read across 0x0200,
// 22 START + STOP, 23 one address byte only, 24 write, repeated START, write,
// 25-31 write (seed bit 0 = 0) or read
function void set(int k, bit [15:0] a = 16'h0010, int cnt = 2, bit [31:0] s = 32'h1); kind = k; reg_a = a; n = cnt - 1; seed = s; endfunction
function void wbyte(bit [7:0] b);
  for (int i = 7; i >= 0; i--) ev.push_back({1'b0, !b[i]});
  ev.push_back(2'b00);                         // release for the target's ACK
endfunction
function void rbytes(int cnt);
  for (int j = 0; j < cnt; j++) begin
    repeat (8) ev.push_back(2'b00);
    ev.push_back({1'b0, j != cnt - 1});        // ACK all but the last, NACK it
  end
endfunction
function void rstart(); ev.push_back(2'b00); ev.push_back(2'b10); endfunction
function void stop(); ev.push_back(2'b01); ev.push_back(2'b11); endfunction
function void build(bit [6:0] dev);
  bit [31:0] x = seed | 1;
  bit [15:0] a = (kind inside {[0:13], 24, [25:31]}) ? {7'h00, reg_a[8:0]} : reg_a;
  bit [6:0] d = (kind inside {16, 17}) ? dev ^ 7'h01 : dev;
  int cnt = n + 1;
  bit rd_k = kind inside {[8:13], 15, 17, 19, 21} || (kind >= 25 && seed[0]);
  if (kind == 18 || kind == 19) a = 16'h0000;
  if (kind == 20) a = 16'h0200 + reg_a[7:0];
  if (kind == 21) a = 16'h01FE;
  ev.delete();
  ev.push_back(2'b10);
  if (kind == 22) begin stop(); return; end
  if (kind == 15) begin wbyte({d, 1'b1}); rbytes(cnt); stop(); return; end
  wbyte({d, 1'b0});
  if (kind == 16) begin stop(); return; end
  if (kind == 17) begin rstart(); wbyte({d, 1'b1}); stop(); return; end
  wbyte(a[15:8]);
  if (kind == 23) begin stop(); return; end
  wbyte(a[7:0]);
  if (kind == 14) begin stop(); return; end
  if (rd_k) begin
    rstart(); wbyte({d, 1'b1}); rbytes((kind == 21) ? 4 : cnt);
  end else begin
    for (int j = 0; j < cnt; j++) begin x ^= x << 13; x ^= x >> 17; x ^= x << 5; wbyte(x[7:0]); end
    if (kind == 24) begin
      rstart(); wbyte({d, 1'b0}); wbyte(8'h00); wbyte(8'h40);
      x ^= x << 13; x ^= x >> 17; x ^= x << 5; wbyte(x[7:0]);
    end
  end
  stop();
endfunction
// monitor side: data bytes of the read frames (after an ACKed address byte with R = 1)
function void decode();
  int k = 0, fr = 0;
  bit rmode = 0;
  bit [7:0] b = 0;
  rd.delete();
  foreach (ev[i]) begin
    if (ev[i][1]) begin k = 0; fr = 0; rmode = 0; continue; end
    if (k < 8) b = {b[6:0], !(ev[i][0] || so[i])};
    k++;
    if (k == 9) begin
      if (fr == 0) rmode = b[0] && so[i];
      else if (rmode) rd.push_back(b);
      fr++; k = 0;
    end
  end
endfunction
""",
    drv_rsp=False,
    drv_desc="one START .. STOP transaction per item: START from an idle bus (SDA low, then SCL low), each bit set a quarter after SCL falls and clocked for two quarters, repeated START and STOP as I2C conditions; the bus then idles for four quarters",
    drv_idle="""
vif.drv_cb.scl      <= 1'b1;
vif.drv_cb.sda_m_lo <= 1'b0;
""",
    drv_item="""
t.build(cfg.dev);
@(vif.drv_cb);
foreach (t.ev[i]) begin
  if (t.ev[i] == 2'b10) begin                  // START: SCL is high
    vif.drv_cb.sda_m_lo <= 1'b1;
    repeat (cfg.q) @(vif.drv_cb);
    vif.drv_cb.scl <= 1'b0;
    repeat (cfg.q) @(vif.drv_cb);
  end else if (t.ev[i] == 2'b11) begin         // STOP: SCL is high
    vif.drv_cb.sda_m_lo <= 1'b0;
    repeat (4 * cfg.q) @(vif.drv_cb);
  end else begin                               // a bit; a rise right before START / STOP stays high
    vif.drv_cb.sda_m_lo <= t.ev[i][0];
    repeat (cfg.q) @(vif.drv_cb);
    vif.drv_cb.scl <= 1'b1;
    repeat (cfg.q) @(vif.drv_cb);
    if (i + 1 < t.ev.size() && !t.ev[i + 1][1]) begin
      repeat (cfg.q) @(vif.drv_cb);
      vif.drv_cb.scl <= 1'b0;
      repeat (cfg.q) @(vif.drv_cb);
    end
  end
end
""",
    mon_desc="from START to STOP: {sda_m_lo} and sda_s_lo at every SCL rising edge, START (SDA falling with SCL high) and STOP (SDA rising with SCL high) markers; decoded into the bytes the target sent",
    mon_run="""
sccb_transaction t;
bit pscl = 1, psda = 1;
forever begin
  bit sda;
  @(vif.mon_cb);
  sda = !(vif.mon_cb.sda_m_lo === 1'b1 || vif.mon_cb.sda_s_lo === 1'b1);
  if (pscl && vif.mon_cb.scl === 1'b1 && psda && !sda) begin
    if (t == null) t = sccb_transaction::type_id::create("t");
    t.ev.push_back(2'b10); t.so.push_back(1'b0);
  end else if (pscl && vif.mon_cb.scl === 1'b1 && !psda && sda && t != null) begin
    t.ev.push_back(2'b11); t.so.push_back(1'b0);
    t.decode();
    publish(t);
    t = null;
  end else if (!pscl && vif.mon_cb.scl === 1'b1 && t != null) begin
    t.ev.push_back({1'b0, vif.mon_cb.sda_m_lo === 1'b1});
    t.so.push_back(vif.mon_cb.sda_s_lo === 1'b1);
  end
  pscl = (vif.mon_cb.scl === 1'b1); psda = sda;
end
""",
    sb_members="""bit [7:0]  regs [512];
bit        rinit = 0;
bit [15:0] ptr = 0;
bit [7:0]  hi = 0;""",
    predict="""
// target state per event: the falling edge before each rise sets its SDA drive
int st = 0;                  // 0 idle 1 address 2 write 3 read 4 ignore
int p = 0, wb = 0;
bit [7:0] sh = 0, txb = 0;
bit ack = 0, rw = 0, slo = 0;
if (!rinit) begin foreach (regs[i]) regs[i] = 8'h00; rinit = 1; end
t.so.delete();
foreach (t.ev[i]) begin
  if (t.ev[i] == 2'b10) begin st = 1; p = 0; slo = 0; t.so.push_back(1'b0); end
  else if (t.ev[i] == 2'b11) begin st = 0; slo = 0; t.so.push_back(1'b0); end
  else begin
    bit line;
    case (st)
      3: slo = (p < 8) ? !txb[7 - p] : 1'b0;
      1, 2: slo = (p == 8) && ack;
      default: slo = 0;
    endcase
    t.so.push_back(slo);
    line = !(t.ev[i][0] || slo);
    if (p == 8) begin
      p = 0;
      if (st == 1) begin
        if (!ack) st = 4;
        else if (rw) begin st = 3; txb = sccb_rd(regs, ptr); end
        else begin st = 2; wb = 0; end
      end else if (st == 3) begin
        ptr++;
        if (!line) txb = sccb_rd(regs, ptr); else st = 4;
      end
    end else begin
      bit [7:0] shn = {sh[6:0], line};
      p++;
      if (st == 1 || st == 2) begin
        sh = shn;
        if (p == 8) begin
          if (st == 1) begin ack = shn[7:1] == cfg.dev; rw = shn[0]; end
          else begin
            ack = 1;
            if (wb == 0) hi = shn;
            else if (wb == 1) ptr = {hi, shn};
            else begin if (ptr >= 2 && ptr < 512) regs[ptr[8:0]] = shn; ptr++; end
            if (wb != 2) wb++;
          end
        end
      end
    end
  end
end
t.decode();
""",
    defs="""
function automatic bit [7:0] sccb_rd(const ref bit [7:0] r [512], input bit [15:0] a);
  if (a == 16'h0000) return 8'h5A;
  if (a == 16'h0001) return 8'h31;
  if (a < 16'h0200) return r[a[8:0]];
  return 8'h00;
endfunction
""",
    checks="""
foreach (t.ev[i]) if (t.ev[i] == 2'b01 && t.so[i]) fail(t, "target holds SDA low at a STOP");
if (t.ev.size() && t.ev[0] != 2'b10) fail(t, "transaction without a START");
""",
    coverage="""
cp_kind : coverpoint tr.ev.size() { bins empty = {[1:4]}; bins addr = {[5:14]}; bins short_t = {[15:40]}; bins long_t = {[41:200]}; }
cp_rd   : coverpoint tr.rd.size() { bins none = {0}; bins one = {1}; bins some = {[2:8]}; }
cp_ack  : coverpoint (tr.so.size() > 9 ? tr.so[9] : 1'b0) { bins nack = {0}; bins ack = {1}; }
""",
    directed="""
// ID, register blocks with both read styles, read-only and unmapped registers, NACKs, wraps
t = item(); t.set(19, 0, 2); send(t);
t = item(); t.set(0, 16'h0010, 8, 32'h11); send(t);
t = item(); t.set(8, 16'h0010, 8); send(t);
t = item(); t.set(14, 16'h0012); send(t);
t = item(); t.set(15, 0, 3); send(t);
t = item(); t.set(15, 0, 1); send(t);
t = item(); t.set(18, 0, 2, 32'h7); send(t);
t = item(); t.set(19, 0, 3); send(t);
t = item(); t.set(20, 16'h0033, 2, 32'h9); send(t);
t = item(); t.set(21, 0, 4); send(t);
t = item(); t.set(16, 16'h0010, 2); send(t);
t = item(); t.set(17); send(t);
t = item(); t.set(22); send(t);
t = item(); t.set(23, 16'h0100); send(t);
t = item(); t.set(15, 0, 2); send(t);
t = item(); t.set(24, 16'h01FF, 1, 32'h5); send(t);
t = item(); t.set(8, 16'h01FF, 1); send(t);
t = item(); t.set(8, 16'h0040, 2); send(t);
t = item(); t.set(0, 16'h01FE, 4, 32'h99); send(t);
t = item(); t.set(8, 16'h01FE, 3); send(t);
""",
    drain_ns=4000,
    model="""
module sccb_model #(parameter logic [6:0] ADDR = 7'h3C) (
  input  logic clk,
  input  logic rst_n,
  input  logic scl,
  input  logic sda_m_lo,
  output logic sda_s_lo
);
  localparam logic [2:0] S_IDLE = 3'd0, S_ADDR = 3'd1, S_WR = 3'd2, S_RD = 3'd3, S_IGN = 3'd4;
  logic [2:0]  st;
  logic [3:0]  p;
  logic [1:0]  wb;
  logic [7:0]  sh, txb, hi;
  logic [15:0] ptr;
  logic        ack, rw;
  logic [7:0]  regs [0:511];
  logic        scl_s, scl_d, sda_s, sda_d;
  wire         line  = !(sda_m_lo || sda_s_lo);
  wire         rise  = scl_s && !scl_d;
  wire         fall  = !scl_s && scl_d;
  wire         start = scl_s && scl_d && sda_d && !sda_s;
  wire         stop  = scl_s && scl_d && !sda_d && sda_s;
  wire  [7:0]  shn   = {sh[6:0], sda_s};
  wire  [15:0] ptr1  = ptr + 16'd1;

  function automatic logic [7:0] rd_reg(input logic [15:0] a);
    if (a == 16'h0000) rd_reg = 8'h5A;
    else if (a == 16'h0001) rd_reg = 8'h31;
    else if (a < 16'h0200) rd_reg = regs[a[8:0]];
    else rd_reg = 8'h00;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= S_IDLE; p <= '0; wb <= '0; sh <= '0; txb <= '0; hi <= '0; ptr <= '0; ack <= 1'b0; rw <= 1'b0;
      scl_s <= 1'b1; scl_d <= 1'b1; sda_s <= 1'b1; sda_d <= 1'b1; sda_s_lo <= 1'b0;
      for (int i = 0; i < 512; i++) regs[i] <= 8'h00;
    end else begin
      scl_s <= scl; scl_d <= scl_s; sda_s <= line; sda_d <= sda_s;
      if (start) begin
        st <= S_ADDR; p <= '0; sda_s_lo <= 1'b0;
      end else if (stop) begin
        st <= S_IDLE; sda_s_lo <= 1'b0;
      end else if (fall) begin
        case (st)
          S_RD:          sda_s_lo <= (p < 4'd8) ? !txb[3'd7 - p[2:0]] : 1'b0;
          S_ADDR, S_WR:  sda_s_lo <= (p == 4'd8) && ack;
          default:       sda_s_lo <= 1'b0;
        endcase
      end else if (rise) begin
        if (p == 4'd8) begin
          p <= '0;
          if (st == S_ADDR) begin
            if (!ack) st <= S_IGN;
            else if (rw) begin st <= S_RD; txb <= rd_reg(ptr); end
            else begin st <= S_WR; wb <= '0; end
          end else if (st == S_RD) begin
            ptr <= ptr1;
            if (!sda_s) txb <= rd_reg(ptr1);
            else st <= S_IGN;
          end
        end else begin
          p <= p + 4'd1;
          if (st == S_ADDR || st == S_WR) begin
            sh <= shn;
            if (p == 4'd7) begin
              if (st == S_ADDR) begin ack <= shn[7:1] == ADDR; rw <= shn[0]; end
              else begin
                ack <= 1'b1;
                if (wb == 2'd0) hi <= shn;
                else if (wb == 2'd1) ptr <= {hi, shn};
                else begin
                  if (ptr >= 16'd2 && ptr < 16'h0200) regs[ptr[8:0]] <= shn;
                  ptr <= ptr1;
                end
                if (wb != 2'd2) wb <= wb + 2'd1;
              end
            end
          end
        end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({scl, sda_m_lo, sda_s_lo}))
  else $error("SCCB: X on the bus");
assert property (@(posedge clk) disable iff (!rst_n) $changed(sda_s_lo) |-> !scl)
  else $error("SCCB: target changed SDA while SCL is high");
assert property (@(posedge clk) disable iff (!rst_n) scl && $past(scl) && $changed(sda_m_lo) |-> !sda_s_lo)
  else $error("SCCB: START / STOP while the target holds SDA low");
cover property (@(posedge clk) disable iff (!rst_n) $rose(scl) && sda_s_lo);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic scl = 1'b1, sda_m_lo = 1'b0;
wire sda_s_lo;
integer q = 4;

always #5 clk = ~clk;

sccb_model u_dut (.clk(clk), .rst_n(rst_n), .scl(scl), .sda_m_lo(sda_m_lo), .sda_s_lo(sda_s_lo));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

logic s_at_rise;
integer slo_hi = 0;
logic pscl = 1'b1, pm = 1'b0;
always @(posedge clk) begin
  if (scl && pscl && pm != sda_m_lo && sda_s_lo) slo_hi = slo_hi + 1;
  pscl <= scl; pm <= sda_m_lo;
end
task automatic start();
  @(negedge clk); sda_m_lo = 1; repeat (q) @(negedge clk);
  scl = 0; repeat (q) @(negedge clk);
endtask
task automatic bitc(input logic m, input logic last = 0);
  sda_m_lo = m; repeat (q) @(negedge clk);
  scl = 1; s_at_rise = sda_s_lo; repeat (q) @(negedge clk);
  if (!last) begin repeat (q) @(negedge clk); scl = 0; repeat (q) @(negedge clk); end
endtask
integer idle_lo = 0;
task automatic stop();
  bitc(1, 1);
  sda_m_lo = 0;
  repeat (4 * q) begin @(negedge clk); if (sda_s_lo !== 1'b0) idle_lo = idle_lo + 1; end
endtask
task automatic rstart();
  bitc(0, 1);
  sda_m_lo = 1; repeat (q) @(negedge clk);
  scl = 0; repeat (q) @(negedge clk);
endtask
logic ack;
task automatic wbyte(input logic [7:0] b);
  for (int i = 7; i >= 0; i--) bitc(!b[i]);
  bitc(0); ack = s_at_rise;
endtask
logic [7:0] rb [0:15];
task automatic rbytes(input integer n);
  for (int j = 0; j < n; j++) begin
    for (int i = 7; i >= 0; i--) begin bitc(0); rb[j][i] = !s_at_rise; end
    bitc(j != n - 1);
  end
endtask
logic a0, a1, a2;
task automatic wr(input logic [6:0] d, input logic [15:0] a, input integer n, input logic [7:0] v0);
  start(); wbyte({d, 1'b0}); a0 = ack; wbyte(a[15:8]); a1 = ack; wbyte(a[7:0]); a2 = ack;
  for (int i = 0; i < n; i++) wbyte(v0 + 8'h11 * i);
  stop();
endtask
task automatic rd(input logic [15:0] a, input integer n);
  start(); wbyte({7'h3C, 1'b0}); wbyte(a[15:8]); wbyte(a[7:0]);
  rstart(); wbyte({7'h3C, 1'b1}); a0 = ack; rbytes(n); stop();
endtask

initial begin
  repeat (3) @(posedge clk);
  chk(sda_s_lo === 1'b0, "SDA released in reset");
  rst_n = 1;
  repeat (8) @(negedge clk);
  rd(16'h0000, 2);
  chk(a0 && rb[0] == 8'h5A && rb[1] == 8'h31, "chip ID 5A 31");
  wr(7'h3C, 16'h0010, 4, 8'h21);
  chk(a0 && a1 && a2 && ack, "device address, register address and data bytes ACKed");
  rd(16'h0010, 4);
  chk(rb[0] == 8'h21 && rb[1] == 8'h32 && rb[2] == 8'h43 && rb[3] == 8'h54, "auto-increment write, repeated-START read");
  start(); wbyte(8'h78); wbyte(8'h00); wbyte(8'h12); stop();
  start(); wbyte(8'h79); a0 = ack; rbytes(2); stop();
  chk(a0 && rb[0] == 8'h43 && rb[1] == 8'h54, "SCCB two-phase read: pointer kept across STOP");
  start(); wbyte(8'h79); rbytes(1); stop();
  chk(rb[0] == 8'h00, "pointer advanced past the read bytes");
  wr(7'h3C, 16'h0000, 2, 8'h00);
  rd(16'h0000, 2);
  chk(rb[0] == 8'h5A && rb[1] == 8'h31, "chip ID is read only");
  wr(7'h3C, 16'h0233, 1, 8'h77);
  rd(16'h0233, 1);
  chk(ack && rb[0] == 8'h00, "unmapped register: write ACKed and ignored, reads 0");
  wr(7'h3C, 16'h01FE, 2, 8'hA0);
  rd(16'h01FE, 3);
  chk(rb[0] == 8'hA0 && rb[1] == 8'hB1 && rb[2] == 8'h00, "last registers, then 0 past 0x01FF");
  wr(7'h3D, 16'h0010, 1, 8'hEE);
  chk(!a0 && !a1 && !a2, "another device address: no ACK, bus ignored");
  rd(16'h0010, 1);
  chk(rb[0] == 8'h21, "and nothing written");
  start(); wbyte(8'h79 ^ 8'h02); a0 = ack; stop();
  chk(!a0, "read from another address: no ACK");
  start(); stop();
  rd(16'h0011, 1);
  chk(rb[0] == 8'h32, "an empty START / STOP changes nothing");
  start(); wbyte(8'h78); wbyte(8'h00); wbyte(8'h13); stop();
  start(); wbyte(8'h78); wbyte(8'h01); stop();
  start(); wbyte(8'h79); rbytes(1); stop();
  chk(rb[0] == 8'h54, "one address byte leaves the pointer unchanged");
  start(); wbyte(8'h78); wbyte(8'h00); wbyte(8'h20); wbyte(8'h99);
  rstart(); wbyte(8'h78); wbyte(8'h00); wbyte(8'h30); wbyte(8'h66); stop();
  rd(16'h0020, 1); a1 = (rb[0] == 8'h99);
  rd(16'h0030, 1);
  chk(a1 && rb[0] == 8'h66, "write, repeated START, write");
  start(); wbyte(8'h79); rbytes(3); stop();
  chk(rb[0] == 8'h00 && rb[1] == 8'h00 && rb[2] == 8'h00, "read with ACKs continues, NACK ends it");
  chk(slo_hi == 0, "the target never holds SDA low at a START or STOP");
  chk(idle_lo == 0, "the target leaves SDA alone on an idle bus");
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
