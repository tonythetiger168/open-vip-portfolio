# Quad-SPI NOR flash VIP: a flash device model (the boot / XIP flash of an IP
# camera SoC) with a host agent that exercises it, SPI mode 0.
#
# Agent -> DUT (host side of the bus): sclk, csn, the host's IO drive io_m[3:0]
# with its enables io_m_oe[3:0] (IO2 / IO3 = WP# / HOLD# held high outside a
# quad data phase, as QSPI_XIP_top does). DUT -> agent: the flash's IO drive
# fl_io[3:0] with fl_oe[3:0]. Command, address and data bits are sampled on
# the sclk rising edge; the flash changes its outputs on the falling edge.
#
# tb/top_tb.sv snor_model is the flash: the command set and behaviour of
# tb/spi_nor_model.svh in open-ip-portfolio (the QSPI_XIP_top benches), a
# 64 KB array (the 24-bit address wraps at 64 KB) preloaded with byte
# a = a[7:0] ^ a[15:8] ^ 0xA5 (or $readmemh of INIT_FILE):
#   0x03 read, 0x0B fast read (8 dummy clocks), 0x6B quad output fast read
#   (8 dummy clocks, data on IO3..0, high nibble first), 0x05 read status
#   ({WEL, WIP = 0} in bits 1:0, repeated), 0x06 write enable, 0x04 write
#   disable, 0x02 page program (needs WEL; bits are ANDed in, the address
#   wraps inside the 256-byte page, WEL clears when CS# rises after at least
#   one data bit), 0x20 4 KB sector erase (needs WEL; at CS# rise after the
#   address; WEL clears), 0x9F JEDEC ID (EF 40 18, then zeros). Any other
#   command is ignored until CS# rises.
# In a SoC bench the flash connects to a QSPI host's pins: io_m <= io (the
# resolved lines), io_m_oe <= 4'hF, and io[i] driven with fl_io[i] while
# fl_oe[i]; the agent can then run passive and its monitor decodes every
# command on the bus.

SNOR_FUNCS = """
function automatic bit snor_has_addr(bit [7:0] c);
  return c == 8'h03 || c == 8'h0B || c == 8'h6B || c == 8'h02 || c == 8'h20;
endfunction
function automatic int snor_start(bit [7:0] c);   // rising edge of the first data bit
  return 8 + (snor_has_addr(c) ? 24 : 0) + ((c == 8'h0B || c == 8'h6B) ? 8 : 0);
endfunction
function automatic bit [7:0] snor_init(int a);
  return a[7:0] ^ a[15:8] ^ 8'hA5;
endfunction
"""

SPEC = dict(
    vip="SPI_NOR-UVM-VIP", p="snor", P="SNOR", dir="snor", family="Memory",
    desc="Quad-SPI NOR flash VIP: flash device model (read, fast read, quad output read, status, WREN / WRDI, "
         "page program, 4 KB sector erase, JEDEC ID; QSPI_XIP_top's spi_nor_model command set) with a host agent "
         "and a bus monitor that decodes every command.",
    about="""
An IP camera boots from, and executes in place out of, a quad-SPI NOR
flash behind the SoC's QSPI controller. The VIP's DUT model is that flash,
with the command set the QSPI_XIP_top benches in open-ip-portfolio use, so
it drops into a SoC bench on the controller's pins. The agent is a host
that sends every command: single, fast and quad reads (including reads
that wrap at the end of the array and read back programmed data), status
polls before and after WREN / WRDI, page programs with and without WEL and
wrapping inside the page, sector erases with and without WEL, JEDEC ID,
unknown commands, and transfers cut inside the address, the dummy cycles
or a data byte. The scoreboard keeps its own copy of the array and WEL and
predicts what the flash drives at every sclk rising edge (enables and
data), so a wrong byte, a late output enable or IO contention all show up.
The monitor also decodes each transfer into command, address and data
bytes for SoC scoreboards.""",
    defs=SNOR_FUNCS,
    timeout=20000,
    cfg="""int unsigned half = 2;     // clocks per sclk half period
int unsigned gap  = 4;     // clocks with CS# high between transfers""",
    ports=[
        ("in", "logic", "sclk"), ("in", "logic", "csn"), ("in", "logic [3:0]", "io_m"), ("in", "logic [3:0]", "io_m_oe"),
        ("out", "logic [3:0]", "fl_io"), ("out", "logic [3:0]", "fl_oe"),
    ],
    fields=[
        ("bit [7:0]", "mo", "req", "q"),        # {io_m_oe, io_m & io_m_oe} at each sclk rise
        ("bit [7:0]", "so", "rsp", "q"),        # {fl_oe, fl_io & fl_oe} at each sclk rise
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [15:0]", "addr", "info", "rand"),
        ("bit [4:0]", "n", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [7:0]", "op", "info"),
        ("bit [7:0]", "rd", "info", "q"),       # decoded: bytes the flash returned
    ],
    tr_functions="""
// kind: 0-3 read 0x03, 4-6 fast read 0x0B, 7-9 quad read 0x6B, 10 JEDEC ID,
// 11 read status, 12 / 25-27 WREN, 13 WRDI, 14-17 page program, 18-19 sector
// erase, 20 unknown command 0xAB, 21 read cut in the address, 22 quad read cut
// in the dummy cycles, 23 quad read wrapping at 0xFFFF, 24 page program
// wrapping in the page, 28-31 read of the programmed area 0x1000-0x10FF
function void set(int k, bit [15:0] a = 16'h0, int cnt = 8, bit [31:0] s = 32'h1); kind = k; addr = a; n = cnt; seed = s; endfunction
function bit [7:0] op_of();
  case (kind)
    0, 1, 2, 3, 21, 28, 29: return 8'h03;
    4, 5, 6, 30: return 8'h0B;
    7, 8, 9, 22, 23, 31: return 8'h6B;
    10: return 8'h9F;
    11: return 8'h05;
    12, 25, 26, 27: return 8'h06;
    13: return 8'h04;
    14, 15, 16, 17, 24: return 8'h02;
    18, 19: return 8'h20;
    default: return 8'hAB;
  endcase
endfunction
// host cells, one per sclk rising edge: {oe, value}
function void build();
  bit [31:0] x = seed | 1;
  bit [23:0] a = {8'h00, addr};
  int nd = n, cut = -1;
  op = op_of();
  if (kind inside {[28:31]}) a = {12'h001, addr[7:0] & 8'hF0};
  if (kind == 23) a = 24'h00_FFF8 + addr[2:0];
  if (kind == 24) a = {8'h00, addr[15:8], 8'hF8};
  if (kind inside {[14:17], 24} && nd == 0) nd = 1;
  if (op == 8'h9F) nd = 3 + n % 3;
  if (op == 8'h05) nd = 1 + n % 3;
  mo.delete();
  for (int i = 7; i >= 0; i--) mo.push_back({4'b1101, 3'b110, op[i]});
  if (snor_has_addr(op)) for (int i = 23; i >= 0; i--) mo.push_back({4'b1101, 3'b110, a[i]});
  if (op == 8'h0B || op == 8'h6B) repeat (8) mo.push_back({4'b1101, 4'b1100});
  if (op == 8'h02)
    for (int b = 0; b < nd; b++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      for (int i = 7; i >= 0; i--) mo.push_back({4'b1101, 3'b110, x[i]});
    end
  else if (op == 8'h6B) repeat (2 * nd) mo.push_back(8'h00);
  else if (op inside {8'h03, 8'h0B, 8'h9F, 8'h05}) repeat (8 * nd) mo.push_back({4'b1101, 4'b1100});
  if (kind == 21) cut = 8 + 1 + x[3:0];
  if (kind == 22) cut = 32 + 1 + x[2:0] % 7;
  if (kind == 24 && x[0]) cut = mo.size() - 1 - x[3:1];
  if (cut >= 0) while (mo.size() > cut) void'(mo.pop_back());
endfunction
// monitor side: the bytes the flash drove after the first data edge
function void decode();
  int s;
  rd.delete();
  if (mo.size() < 8) return;
  op = 0;
  for (int i = 0; i < 8; i++) op = {op[6:0], mo[i][4] ? mo[i][0] : 1'b1};
  s = snor_start(op);
  if (op == 8'h6B) for (int i = s; i + 1 < so.size(); i += 2) rd.push_back({so[i][3:0], so[i + 1][3:0]});
  else if (op inside {8'h03, 8'h0B, 8'h9F, 8'h05})
    for (int i = s; i + 7 < so.size(); i += 8) begin
      bit [7:0] b;
      for (int j = 0; j < 8; j++) b[7 - j] = so[i + j][1];
      rd.push_back(b);
    end
endfunction
""",
    drv_rsp=False,
    drv_desc="one CS# transfer per item: CS# low, one host cell per sclk period (outputs set while sclk is low, sclk high for the second half), sclk low with the host off the bus, CS# high for cfg.gap clocks",
    drv_idle="""
vif.drv_cb.sclk    <= 1'b0;
vif.drv_cb.csn     <= 1'b1;
vif.drv_cb.io_m    <= 4'b1100;
vif.drv_cb.io_m_oe <= 4'b1100;
""",
    drv_item="""
t.build();
@(vif.drv_cb);
vif.drv_cb.csn <= 1'b0;
foreach (t.mo[i]) begin
  vif.drv_cb.sclk    <= 1'b0;
  vif.drv_cb.io_m_oe <= t.mo[i][7:4];
  vif.drv_cb.io_m    <= t.mo[i][3:0];
  repeat (cfg.half) @(vif.drv_cb);
  vif.drv_cb.sclk <= 1'b1;
  repeat (cfg.half) @(vif.drv_cb);
end
vif.drv_cb.sclk    <= 1'b0;
vif.drv_cb.io_m_oe <= 4'b0000;              // the flash may drive until CS# rises
repeat (cfg.half) @(vif.drv_cb);
vif.drv_cb.csn <= 1'b1;
@(vif.drv_cb);
vif.drv_cb.io_m_oe <= 4'b1100;
vif.drv_cb.io_m    <= 4'b1100;
repeat (cfg.gap) @(vif.drv_cb);
""",
    mon_desc="host and flash drive (masked by their enables) at every sclk rising edge from CS# low to CS# high, decoded into command and returned bytes",
    mon_run="""
forever begin
  snor_transaction t;
  bit ps;
  while (vif.mon_cb.csn !== 1'b0) @(vif.mon_cb);
  t = snor_transaction::type_id::create("t");
  ps = vif.mon_cb.sclk;
  while (vif.mon_cb.csn === 1'b0) begin
    @(vif.mon_cb);
    if (ps === 1'b0 && vif.mon_cb.sclk === 1'b1 && vif.mon_cb.csn === 1'b0) begin
      t.mo.push_back({vif.mon_cb.io_m_oe, vif.mon_cb.io_m & vif.mon_cb.io_m_oe});
      t.so.push_back({vif.mon_cb.fl_oe, vif.mon_cb.fl_io & vif.mon_cb.fl_oe});
    end
    ps = vif.mon_cb.sclk;
  end
  t.decode();
  publish(t);
end
""",
    sb_members="""bit [7:0] mem [65536];
bit       minit = 0;
bit       wel = 0;""",
    predict="""
// the flash, edge by edge: output for this rise (set at the falling edge
// before it), the rising edge, then the falling edge after it; CS# rise last
int nb = 0;
bit [7:0] cmd = 0, pp = 0;
bit [23:0] ad = 0;
bit [3:0] oe = 0, o = 0;
if (!minit) begin for (int i = 0; i < 65536; i++) mem[i] = snor_init(i); minit = 1; end
t.so.delete();
foreach (t.mo[i]) begin
  bit io0 = t.mo[i][4] ? t.mo[i][0] : 1'b1;
  t.so.push_back({oe, o & oe});
  if (nb < 8) cmd = {cmd[6:0], io0};
  else if (snor_has_addr(cmd) && nb < 32) ad = {ad[22:0], io0};
  else if (cmd == 8'h02 && nb >= 32) begin
    pp = {pp[6:0], io0};
    if ((nb - 32) % 8 == 7) begin
      if (wel) mem[ad[15:0]] = mem[ad[15:0]] & pp;
      ad[7:0] = ad[7:0] + 8'd1;
    end
  end
  nb++;
  if (nb >= 8) begin
    int k = nb - snor_start(cmd);
    if (k >= 0)
      case (cmd)
        8'h03, 8'h0B: begin oe = 4'b0010; o[1] = mem[ad[15:0] + 16'(k / 8)][7 - k % 8]; end
        8'h6B: begin
                 bit [7:0] b = mem[ad[15:0] + 16'(k / 2)];
                 oe = 4'b1111; o = (k % 2 == 0) ? b[7:4] : b[3:0];
               end
        8'h05: begin oe = 4'b0010; o[1] = (k % 8 == 6) ? wel : 1'b0; end
        8'h9F: begin oe = 4'b0010; o[1] = (k < 24) ? 24'hEF4018 >> (23 - k) : 1'b0; end
        default: oe = 4'b0000;
      endcase
  end
end
if (nb >= 8) begin
  if (cmd == 8'h06) wel = 1;
  if (cmd == 8'h04) wel = 0;
  if (cmd == 8'h20 && nb >= 32) begin
    if (wel) for (int i = 0; i < 4096; i++) mem[{ad[15:12], 12'h000} + i] = 8'hFF;
    wel = 0;
  end
  if (cmd == 8'h02 && nb > 32) wel = 0;
end
t.decode();
""",
    checks="""
foreach (t.so[i]) if ((t.so[i][7:4] & t.mo[i][7:4]) != 4'h0) fail(t, "host and flash drive the same IO line");
if (t.op == 8'h9F && t.rd.size() >= 3 && {t.rd[0], t.rd[1], t.rd[2]} != 24'hEF4018) fail(t, "wrong JEDEC ID");
""",
    coverage="""
cp_op  : coverpoint tr.op { bins rd = {8'h03}; bins fast = {8'h0B}; bins quad = {8'h6B}; bins rdsr = {8'h05};
                            bins wren = {8'h06}; bins wrdi = {8'h04}; bins pp = {8'h02}; bins se = {8'h20};
                            bins id = {8'h9F}; bins other = {8'hAB}; }
cp_len : coverpoint tr.mo.size() { bins cut = {[9:39]}; bins cmd = {8}; bins addr = {32}; bins data = {[40:400]}; }
cp_rd  : coverpoint tr.rd.size() { bins none = {0}; bins one = {1}; bins some = {[2:31]}; }
""",
    directed="""
// ID and status, WEL handling, program / read back in every read mode, erase, wraps, cuts
t = item(); t.set(10, 0, 3); send(t);
t = item(); t.set(11, 0, 1); send(t);
t = item(); t.set(14, 16'h1000, 16, 32'h21); send(t);      // no WEL: ignored
t = item(); t.set(12); send(t);
t = item(); t.set(11, 0, 2); send(t);
t = item(); t.set(14, 16'h1000, 16, 32'h22); send(t);
t = item(); t.set(11, 0, 1); send(t);
t = item(); t.set(28, 16'h0000, 20); send(t);
t = item(); t.set(30, 16'h0004, 12); send(t);
t = item(); t.set(31, 16'h0008, 9); send(t);
t = item(); t.set(18, 16'h1234); send(t);                  // no WEL
t = item(); t.set(12); send(t);
t = item(); t.set(13); send(t);
t = item(); t.set(11, 0, 1); send(t);
t = item(); t.set(12); send(t);
t = item(); t.set(18, 16'h1F00); send(t);
t = item(); t.set(28, 16'h0000, 24); send(t);
t = item(); t.set(12); send(t);
t = item(); t.set(24, 16'h1000, 12, 32'h44); t.seed[0] = 1'b0; send(t);
t = item(); t.set(29, 16'h00F0, 16); send(t);
t = item(); t.set(29, 16'h0000, 8); send(t);
t = item(); t.set(23, 16'h0001, 12); send(t);
t = item(); t.set(20, 0, 4); send(t);
t = item(); t.set(21, 16'h0100, 4); send(t);
t = item(); t.set(22, 16'h0200, 4); send(t);
t = item(); t.set(12); send(t);
t = item(); t.set(24, 16'h2000, 9, 32'h3); t.seed[0] = 1'b1; send(t);
t = item(); t.set(11, 0, 1); send(t);
for (int i = 0; i < 6; i++) begin t = item(); t.set(7 + i % 3, 16'h2000 + 16'(i * 37), 6 + i); send(t); end
""",
    drain_ns=4000,
    model="""
module snor_model #(parameter string INIT_FILE = "") (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       sclk,
  input  logic       csn,
  input  logic [3:0] io_m,
  input  logic [3:0] io_m_oe,
  output logic [3:0] fl_io,
  output logic [3:0] fl_oe
);
  logic [7:0]  mem [0:65535];
  logic        wel;
  logic [7:0]  cmd, pp;
  logic [23:0] addr;
  logic [15:0] nbit;
  wire         io0 = io_m_oe[0] ? io_m[0] : 1'b1;
  wire  [7:0]  pp_v = {pp[6:0], io0};
  wire         _unused = &{1'b0, clk, io_m[3:1], io_m_oe[3:1]};

  function automatic logic has_addr(input logic [7:0] c);
    has_addr = c == 8'h03 || c == 8'h0B || c == 8'h6B || c == 8'h02 || c == 8'h20;
  endfunction
  function automatic integer data_start(input logic [7:0] c);
    data_start = 8 + (has_addr(c) ? 24 : 0) + ((c == 8'h0B || c == 8'h6B) ? 8 : 0);
  endfunction

  initial begin
    for (int i = 0; i < 65536; i++) mem[i] = i ^ (i >> 8) ^ 8'hA5;
    if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
  end

  // rising sclk: command, address, program data; CS# rise ends the command
  always_ff @(posedge sclk or posedge csn or negedge rst_n) begin
    if (!rst_n) begin
      wel <= 1'b0; cmd <= '0; pp <= '0; addr <= '0; nbit <= '0;
    end else if (csn) begin
      if (nbit >= 16'd8) begin
        if (cmd == 8'h06) wel <= 1'b1;
        if (cmd == 8'h04) wel <= 1'b0;
        if (cmd == 8'h20 && nbit >= 16'd32) begin
          if (wel) for (int i = 0; i < 4096; i++) mem[{addr[15:12], 12'h000} + 16'(i)] <= 8'hFF;
          wel <= 1'b0;
        end
        if (cmd == 8'h02 && nbit > 16'd32) wel <= 1'b0;
      end
      nbit <= '0; cmd <= '0; addr <= '0;
    end else begin
      if (nbit < 16'd8) cmd <= {cmd[6:0], io0};
      else if (has_addr(cmd) && nbit < 16'd32) addr <= {addr[22:0], io0};
      else if (cmd == 8'h02) begin
        pp <= pp_v;
        if (nbit[2:0] == 3'd7) begin
          if (wel) mem[addr[15:0]] <= mem[addr[15:0]] & pp_v;
          addr[7:0] <= addr[7:0] + 8'd1;
        end
      end
      if (nbit != 16'hFFFF) nbit <= nbit + 16'd1;
    end
  end

  // falling sclk: drive the next output bit / nibble
  always_ff @(negedge sclk or posedge csn or negedge rst_n) begin
    if (!rst_n || csn) begin
      fl_oe <= 4'b0000; fl_io <= 4'b0000;
    end else if (nbit >= 16'd8) begin : drive
      integer k;
      logic [7:0] b;
      k = nbit;
      k = k - data_start(cmd);
      if (k >= 0)
        case (cmd)
          8'h03, 8'h0B: begin b = mem[addr[15:0] + 16'(k / 8)]; fl_oe <= 4'b0010; fl_io[1] <= b[7 - k % 8]; end
          8'h6B: begin
            b = mem[addr[15:0] + 16'(k / 2)];
            fl_oe <= 4'b1111; fl_io <= (k % 2 == 0) ? b[7:4] : b[3:0];
          end
          8'h05: begin fl_oe <= 4'b0010; fl_io[1] <= (k % 8 == 6) ? wel : 1'b0; end
          8'h9F: begin fl_oe <= 4'b0010; fl_io[1] <= (k < 24) ? 1'(24'hEF4018 >> (23 - k)) : 1'b0; end
          default: fl_oe <= 4'b0000;
        endcase
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({sclk, csn, fl_oe}))
  else $error("SNOR: X on sclk / CS# / flash enables");
assert property (@(posedge clk) disable iff (!rst_n) !csn |-> (io_m_oe & fl_oe) == 4'h0)
  else $error("SNOR: host and flash drive the same IO line");
assert property (@(posedge clk) disable iff (!rst_n) csn |-> fl_oe == 4'h0)
  else $error("SNOR: flash drives IO with CS# high");
assert property (@(posedge clk) disable iff (!rst_n) $fell(csn) |-> !sclk)
  else $error("SNOR: CS# fell with sclk high (not mode 0)");
cover property (@(posedge clk) disable iff (!rst_n) fl_oe == 4'hF);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b1;
initial #1 rst_n = 1'b0;      // a falling edge: the flash has no clock to see a level reset
logic sclk = 1'b0, csn = 1'b1;
logic [3:0] io_m = 4'b1100, io_m_oe = 4'b1100;
wire [3:0] fl_io, fl_oe;

always #5 clk = ~clk;

snor_model u_dut (.clk(clk), .rst_n(rst_n), .sclk(sclk), .csn(csn), .io_m(io_m), .io_m_oe(io_m_oe),
                  .fl_io(fl_io), .fl_oe(fl_oe));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

logic [7:0] wb [0:255], rb [0:255];
logic [3:0] so [0:4095], soe [0:4095];
integer nr = 0, conflict = 0;
// one transfer: command, optional address, dummy clocks, nwr written bytes, nrd read bytes (quad
// reads release the bus); cut: rising edges to stop after (-1 = none)
task automatic xfer(input logic [7:0] c, input logic ha, input logic [23:0] a, input integer dum,
                    input integer nwr, input integer nrd, input logic q, input integer cut = -1);
  logic [3:0] v [0:4095], e [0:4095];
  integer n, s;
  n = 0;
  for (int i = 7; i >= 0; i--) begin v[n] = {3'b110, c[i]}; e[n] = 4'b1101; n = n + 1; end
  if (ha) for (int i = 23; i >= 0; i--) begin v[n] = {3'b110, a[i]}; e[n] = 4'b1101; n = n + 1; end
  for (int i = 0; i < dum; i++) begin v[n] = 4'b1100; e[n] = 4'b1101; n = n + 1; end
  for (int b = 0; b < nwr; b++) for (int i = 7; i >= 0; i--) begin v[n] = {3'b110, wb[b][i]}; e[n] = 4'b1101; n = n + 1; end
  s = n;
  for (int i = 0; i < (q ? 2 : 8) * nrd; i++) begin v[n] = 4'b0000; e[n] = q ? 4'b0000 : 4'b1101; n = n + 1; end
  if (cut >= 0) n = cut;
  @(negedge clk); csn = 0;
  for (int i = 0; i < n; i++) begin
    @(negedge clk); sclk = 0; io_m = v[i]; io_m_oe = e[i];
    repeat (2) @(negedge clk);
    sclk = 1;
    so[i] = fl_io; soe[i] = fl_oe;
    if ((fl_oe & io_m_oe) != 4'h0) conflict = conflict + 1;
    @(negedge clk);
  end
  @(negedge clk); sclk = 0; io_m_oe = 4'b0000;
  repeat (2) @(negedge clk); csn = 1;
  @(negedge clk); io_m = 4'b1100; io_m_oe = 4'b1100;
  repeat (2) @(negedge clk);
  nr = 0;
  if (q) for (int i = s; i + 1 < n; i += 2) begin rb[nr] = {so[i] & soe[i], so[i + 1] & soe[i + 1]}; nr = nr + 1; end
  else for (int i = s; i + 7 < n; i += 8) begin
    for (int j = 0; j < 8; j++) rb[nr][7 - j] = so[i + j][1] & soe[i + j][1];
    nr = nr + 1;
  end
endtask
function automatic logic [7:0] init(input integer a);
  init = a[7:0] ^ a[15:8] ^ 8'hA5;
endfunction
function automatic logic rd_is(input integer a0, input integer n, input logic prog = 0);
  logic ok;
  ok = nr == n;
  for (int i = 0; i < 256; i++) if (i < n && rb[i] !== (prog ? (init(a0 + i) & wb[i]) : init((a0 + i) % 65536))) ok = 0;
  rd_is = ok;
endfunction
logic [7:0] st;

initial begin
  repeat (3) @(posedge clk);
  chk(fl_oe === 4'h0, "flash IO released");
  rst_n = 1;
  repeat (4) @(negedge clk);
  xfer(8'h9F, 0, 0, 0, 0, 4, 0);
  chk(nr == 4 && rb[0] == 8'hEF && rb[1] == 8'h40 && rb[2] == 8'h18 && rb[3] == 8'h00, "JEDEC ID EF 40 18, then 00");
  xfer(8'h05, 0, 0, 0, 0, 2, 0);
  chk(nr == 2 && rb[0] == 8'h00 && rb[1] == 8'h00, "status after reset: WEL 0");
  xfer(8'h03, 1, 24'h000010, 0, 0, 8, 0);
  chk(rd_is(16'h0010, 8), "read 0x03 of the preloaded array");
  xfer(8'h0B, 1, 24'h000123, 8, 0, 6, 0);
  chk(rd_is(16'h0123, 6), "fast read 0x0B with 8 dummy clocks");
  xfer(8'h6B, 1, 24'h000456, 8, 0, 9, 1);
  chk(rd_is(16'h0456, 9) && soe[8 + 24 + 8] == 4'hF, "quad read 0x6B: four lines, high nibble first");
  xfer(8'h6B, 1, 24'h12FFFC, 8, 0, 8, 1);
  chk(rd_is(16'hFFFC, 8), "quad read wraps at 64 KB (address bits 23:16 ignored)");
  for (int i = 0; i < 16; i++) wb[i] = 8'h0F ^ (8'h11 * i);
  xfer(8'h02, 1, 24'h001000, 0, 16, 0, 0);
  xfer(8'h03, 1, 24'h001000, 0, 0, 16, 0);
  chk(rd_is(16'h1000, 16), "page program without WEL is ignored");
  xfer(8'h06, 0, 0, 0, 0, 0, 0);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h02, "WREN sets WEL");
  xfer(8'h02, 1, 24'h001000, 0, 16, 0, 0);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h00, "page program clears WEL");
  xfer(8'h03, 1, 24'h001000, 0, 0, 16, 0);
  chk(rd_is(16'h1000, 16, 1), "programmed bytes are ANDed into the array");
  xfer(8'h6B, 1, 24'h001000, 8, 0, 16, 1);
  chk(rd_is(16'h1000, 16, 1), "and read the same in quad mode");
  xfer(8'h06, 0, 0, 0, 0, 0, 0);
  xfer(8'h04, 0, 0, 0, 0, 0, 0);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h00, "WRDI clears WEL");
  xfer(8'h20, 1, 24'h001000, 0, 0, 0, 0);
  xfer(8'h03, 1, 24'h001000, 0, 0, 4, 0);
  chk(rd_is(16'h1000, 4, 1), "sector erase without WEL is ignored");
  xfer(8'h06, 0, 0, 0, 0, 0, 0);
  xfer(8'h20, 1, 24'h001ABC, 0, 0, 0, 0);
  xfer(8'h03, 1, 24'h000FFE, 0, 0, 4, 0);
  chk(nr == 4 && rb[0] == init(16'h0FFE) && rb[1] == init(16'h0FFF) && rb[2] == 8'hFF && rb[3] == 8'hFF,
      "sector erase clears the whole 4 KB sector to FF, not the one before");
  xfer(8'h03, 1, 24'h001FFF, 0, 0, 2, 0);
  chk(rb[0] == 8'hFF && rb[1] == init(16'h2000), "and not the one after");
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h00, "erase clears WEL");
  for (int i = 0; i < 12; i++) wb[i] = 8'hFF ^ (8'h01 << (i % 8));
  xfer(8'h06, 0, 0, 0, 0, 0, 0);
  xfer(8'h02, 1, 24'h0030F8, 0, 12, 0, 0);
  xfer(8'h03, 1, 24'h0030F8, 0, 0, 8, 0);
  chk(rb[0] == (init(16'h30F8) & wb[0]) && rb[7] == (init(16'h30FF) & wb[7]), "program to the end of the page");
  xfer(8'h03, 1, 24'h003000, 0, 0, 4, 0);
  chk(rb[0] == (init(16'h3000) & wb[8]) && rb[3] == (init(16'h3003) & wb[11]) , "then wraps to the page start");
  xfer(8'h06, 0, 0, 0, 0, 0, 0);
  xfer(8'h02, 1, 24'h004000, 0, 0, 0, 0);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h02, "page program with no data bit keeps WEL");
  wb[0] = 8'h00;
  xfer(8'h02, 1, 24'h004000, 0, 1, 0, 0, 32 + 5);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h00, "a partial data byte clears WEL");
  xfer(8'h03, 1, 24'h004000, 0, 0, 1, 0);
  chk(rb[0] == init(16'h4000), "and programs nothing");
  xfer(8'hAB, 0, 0, 0, 0, 2, 0);
  chk(nr == 2 && rb[0] == 8'h00 && soe[8] == 4'h0, "unknown command: the flash stays off the bus");
  xfer(8'h03, 1, 24'h000500, 0, 0, 2, 0, 20);
  xfer(8'h03, 1, 24'h000500, 0, 0, 2, 0);
  chk(rd_is(16'h0500, 2), "a transfer cut in the address leaves no state behind");
  xfer(8'h06, 0, 0, 0, 0, 0, 0, 5);
  xfer(8'h05, 0, 0, 0, 0, 1, 0);
  chk(rb[0] == 8'h00, "WREN cut before 8 bits is ignored");
  chk(conflict == 0, "no IO contention");
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
