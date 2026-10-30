# Intel eSPI (Enhanced Serial Peripheral Interface, base spec rev 1.x)
# controller agent, single I/O mode: CS#, SCLK, MOSI (IO0) from the
# controller, MISO (IO1) from the target. The bus clock is a divided system
# clock (cfg.half system clocks per SCLK half period); data changes while
# SCLK is low and is sampled on its rising edge.
#
# Transaction: command phase (opcode, header, data, CRC-8), two turn-around
# SCLK cycles, response phase (response code, data, 16-bit status LSB first,
# CRC-8). CRC-8 is x^8 + x^2 + x + 1, init 0, over the bytes of the phase.
#   0x25 GET_STATUS            0x21 GET_CONFIGURATION  (2-byte address)
#   0x22 SET_CONFIGURATION     (2-byte address, 4 data bytes LSB first)
#   0x40 / 0x44 PUT_IORD / PUT_IOWR_SHORT     (2-byte I/O address, 1/2/4 bytes)
#   0x48 / 0x4C PUT_MEMRD32 / PUT_MEMWR32_SHORT (4-byte address, 1/2/4 bytes)
# The low two opcode bits of the short cycles give the length: 0 = 1 byte,
# 1 = 2, 3 = 4 (2 is not a length). Addresses go MSB first, data LSB first.
#
# tb/top_tb.sv espi_model: an eSPI target (an embedded controller) with a
# 16-byte I/O window at 0x0060-0x006F, a 64-byte memory window at
# 0xFE0B_0000-0xFE0B_003F and three configuration registers: 0x04 device ID
# (read-only 0x00000001), 0x08 general capabilities (reset 0x0000000F,
# bits 31:16 writable), 0x10 peripheral channel (bit 0 enable, reset 1;
# bit 1 ready, read-only 1). Unimplemented registers read 0 and ignore writes.
# Responses: ACCEPT (0x08) with data, status 0x030F (PC / NP / VW / OOB /
# flash free) and CRC; NON_FATAL_ERROR (0x02) with status and CRC for a short
# cycle outside its window (the whole access must fit) or with the peripheral
# channel disabled; no response at all (MISO left high) for a command CRC
# error or an unsupported opcode. Unsupported opcodes are sent as opcode,
# two header bytes and CRC.

ESPI_FUNCS = """
// eSPI CRC-8: x^8 + x^2 + x + 1, init 0, MSB first
function automatic bit [7:0] espi_crc8(bit [7:0] c, bit [7:0] b);
  c ^= b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction
localparam bit [15:0] ESPI_STATUS = 16'h030F;
// 0 GET_STATUS, 1 GET_CONFIGURATION, 2 SET_CONFIGURATION, 3 I/O read,
// 4 I/O write, 5 memory read, 6 memory write, 7 not supported
function automatic int espi_cls(bit [7:0] op);
  case (op)
    8'h25: return 0;
    8'h21: return 1;
    8'h22: return 2;
    8'h40, 8'h41, 8'h43: return 3;
    8'h44, 8'h45, 8'h47: return 4;
    8'h48, 8'h49, 8'h4B: return 5;
    8'h4C, 8'h4D, 8'h4F: return 6;
    default: return 7;
  endcase
endfunction
function automatic int espi_n(bit [7:0] op); return (op[1:0] == 2'd3) ? 4 : op[1:0] + 1; endfunction
function automatic int espi_addr_len(bit [7:0] op);
  int c = espi_cls(op);
  return (c == 0) ? 0 : (c == 5 || c == 6) ? 4 : 2;
endfunction
function automatic int espi_wdata_len(bit [7:0] op);
  int c = espi_cls(op);
  return (c == 2) ? 4 : (c == 4 || c == 6) ? espi_n(op) : 0;
endfunction
function automatic int espi_rdata_len(bit [7:0] op);
  int c = espi_cls(op);
  return (c == 1) ? 4 : (c == 3 || c == 5) ? espi_n(op) : 0;
endfunction
// bytes the controller sends (with the CRC) and clocks back (an ACCEPT)
function automatic int espi_cmd_len(bit [7:0] op); return 2 + espi_addr_len(op) + espi_wdata_len(op); endfunction
function automatic int espi_rsp_len(bit [7:0] op); return 4 + espi_rdata_len(op); endfunction
"""

SPEC = dict(
    vip="eSPI-UVM-VIP", p="espi", P="eSPI", dir="espi", family="Power / Management",
    desc="Intel eSPI controller VIP (single I/O mode): command / turn-around / response phases with CRC-8, "
         "GET_STATUS, GET / SET_CONFIGURATION, short I/O and memory cycles, ACCEPT / NON_FATAL_ERROR / no response.",
    about="""
eSPI replaced LPC as the link between a PC chipset and its embedded
controller, super I/O, BMC and boot flash. Every transaction is a command
phase from the controller, two turn-around clocks and a response phase from
the target, each closed by a CRC-8. The DUT model is an embedded controller
with an I/O window, a memory window and the configuration registers; the
scoreboard keeps its own copy of all three and predicts every response code,
data byte, status and CRC, including the NON_FATAL_ERROR for an access that
leaves its window or hits a disabled channel and the silence after a command
CRC error. The monitor rebuilds both phases from the four wires.""",
    defs=ESPI_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "cs_n"), ("in", "logic", "sclk"), ("in", "logic", "mosi"),
        ("out", "logic", "miso"), ("out", "logic", "miso_oe"),
    ],
    cfg="int unsigned half = 2;    // system clocks per SCLK half period",
    fields=[
        ("bit [7:0]", "opcode", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [7:0]", "wdata", "req", "q"),
        ("bit", "bad_crc", "req"),            # command CRC inverted in bit 0
        ("bit [7:0]", "rcode", "rsp"),        # 0x08 ACCEPT, 0x02 NON_FATAL_ERROR, 0xFF none
        ("bit [7:0]", "rdata", "rsp", "q"),
        ("bit [15:0]", "status", "rsp"),
        ("bit", "rcrc_ok", "rsp"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [1:0]", "where", "info", "rand"),  # address in its window (0) or just below / above it
    ],
    constraints="""
constraint c_op   { opcode dist { 8'h25 := 2, 8'h21 := 3, 8'h22 := 2,
                                  8'h40 := 3, 8'h41 := 3, 8'h43 := 3, 8'h44 := 3, 8'h45 := 3, 8'h47 := 3,
                                  8'h48 := 3, 8'h49 := 3, 8'h4B := 3, 8'h4C := 3, 8'h4D := 3, 8'h4F := 3,
                                  8'h42 := 1, 8'h30 := 1 }; }
constraint c_crc  { bad_crc dist { 0 := 24, 1 := 1 }; }
constraint c_where { where dist { 0 := 12, 1 := 1, 2 := 1 }; }
constraint c_addr {
  (opcode == 8'h25) -> addr == 0;
  (opcode inside {8'h21, 8'h22}) -> addr inside {32'h004, 32'h008, 32'h010, 32'h020};
  (opcode inside {[8'h40:8'h47], 8'h30}) -> addr[31:16] == 0;
  (opcode inside {[8'h40:8'h47], 8'h30} && where == 0) -> addr[15:4] == 12'h006;
  (opcode inside {[8'h40:8'h47], 8'h30} && where == 1) -> addr[15:4] == 12'h005;
  (opcode inside {[8'h40:8'h47], 8'h30} && where == 2) -> addr[15:4] == 12'h007;
  (opcode inside {[8'h48:8'h4F]} && where == 0) -> addr[31:6] == 26'h3F8_2C00;
  (opcode inside {[8'h48:8'h4F]} && where == 1) -> addr[31:4] == 28'hFE0_AFFF;
  (opcode inside {[8'h48:8'h4F]} && where == 2) -> addr[31:4] == 28'hFE0_B004;
}
""",
    tr_functions="""
function int cls(); return espi_cls(opcode); endfunction

// write data from the seed; a SET_CONFIGURATION of the channel register
// mostly keeps the channel enabled
function void post_randomize();
  bit [31:0] x = seed | 1;
  wdata.delete();
  for (int i = 0; i < espi_wdata_len(opcode); i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    wdata.push_back(x[7:0]);
  end
  if (opcode == 8'h22 && addr == 32'h010) wdata[0][0] = (x[9:8] != 2'd0);
endfunction

// command fields from the controller's bytes (CRC included)
function void from_cmd(bit [7:0] b[$]);
  bit [7:0] c = 0;
  int na, nw;
  opcode = b[0]; na = espi_addr_len(opcode); nw = espi_wdata_len(opcode);
  addr = 0; wdata.delete();
  for (int k = 1; k <= na; k++) addr = {addr[23:0], b[k]};
  for (int k = 0; k < nw; k++) wdata.push_back(b[1 + na + k]);
  for (int k = 0; k + 1 < b.size(); k++) c = espi_crc8(c, b[k]);
  bad_crc = (b[b.size() - 1] != c);
endfunction

// response fields from the bytes clocked back (0xFF where nobody drove)
function void from_rsp(bit [7:0] r[$]);
  bit [7:0] c = 0;
  int nd;
  rcode = (r.size() != 0) ? r[0] : 8'hFF;
  rdata.delete(); status = 0; rcrc_ok = 0;
  nd = (rcode == 8'h08) ? espi_rdata_len(opcode) : (rcode == 8'h02) ? 0 : -1;
  if (nd >= 0 && r.size() >= nd + 4) begin
    for (int i = 0; i < nd; i++) rdata.push_back(r[1 + i]);
    status = {r[nd + 2], r[nd + 1]};
    for (int i = 0; i < nd + 3; i++) c = espi_crc8(c, r[i]);
    rcrc_ok = (r[nd + 3] == c);
  end
endfunction
""",
    drv_rsp=True,
    drv_desc="one eSPI transaction per item: command bytes and CRC on MOSI, two turn-around cycles, the response clocked back from MISO",
    drv_idle="""
vif.drv_cb.cs_n <= 1'b1;
vif.drv_cb.sclk <= 1'b0;
vif.drv_cb.mosi <= 1'b1;
""",
    drv_tasks="""
// one SCLK cycle: MOSI changes with SCLK low, MISO taken as SCLK rises
task cyc(bit o, output bit i);
  vif.drv_cb.sclk <= 1'b0; vif.drv_cb.mosi <= o;
  repeat (cfg.half) @(vif.drv_cb);
  i = vif.drv_cb.miso;
  vif.drv_cb.sclk <= 1'b1;
  repeat (cfg.half) @(vif.drv_cb);
endtask
""",
    drv_item="""
bit [7:0] b[$], r[$];
bit [7:0] c = 0;
bit in;
b.push_back(t.opcode);
for (int i = espi_addr_len(t.opcode) - 1; i >= 0; i--) b.push_back(t.addr[8*i +: 8]);
foreach (t.wdata[i]) b.push_back(t.wdata[i]);
foreach (b[i]) c = espi_crc8(c, b[i]);
b.push_back(c ^ {7'h0, t.bad_crc});
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b0; vif.drv_cb.sclk <= 1'b0; vif.drv_cb.mosi <= 1'b1;
repeat (cfg.half) @(vif.drv_cb);
foreach (b[i]) for (int k = 7; k >= 0; k--) cyc(b[i][k], in);
repeat (2) cyc(1'b1, in);                                 // turn-around
for (int i = 0; i < espi_rsp_len(t.opcode); i++) begin
  bit [7:0] x;
  for (int k = 7; k >= 0; k--) begin cyc(1'b1, in); x[k] = in; end
  r.push_back(x);
end
vif.drv_cb.sclk <= 1'b0;
repeat (cfg.half) @(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b1;
repeat (2 * cfg.half) @(vif.drv_cb);
t.from_rsp(r);
""",
    mon_desc="transactions between CS# fall and rise: command bytes from MOSI, two turn-around cycles, response bytes from MISO, all on SCLK rising edges",
    mon_run="""
bit [7:0] b[$], r[$];
bit [7:0] sh = 0;
int unsigned nbit = 0, len = 0;
bit sclk_p = 0, cs_p = 1;
forever begin
  @(vif.mon_cb);
  if (!vif.mon_cb.cs_n && cs_p) begin b.delete(); r.delete(); nbit = 0; len = 1; end
  if (!vif.mon_cb.cs_n && vif.mon_cb.sclk && !sclk_p) begin
    // bits 0 .. 8*len-1 command, then two turn-around cycles, then response
    if (nbit < 8 * len) sh = {sh[6:0], vif.mon_cb.mosi};
    else if (nbit >= 8 * len + 2) sh = {sh[6:0], vif.mon_cb.miso};
    nbit++;
    if (nbit <= 8 * len && nbit % 8 == 0) begin
      b.push_back(sh);
      if (nbit == 8) len = espi_cmd_len(sh);
    end else if (nbit > 8 * len + 2 && (nbit - 8 * len - 2) % 8 == 0) r.push_back(sh);
  end
  if (vif.mon_cb.cs_n && !cs_p) begin
    if (b.size() != len || b.size() < 2)
      `uvm_error("MON", $sformatf("eSPI: transaction cut short (%0d of %0d command bytes)", b.size(), len))
    else begin
      espi_transaction t = espi_transaction::type_id::create("t");
      t.from_cmd(b);
      t.from_rsp(r);
      publish(t);
    end
  end
  sclk_p = vif.mon_cb.sclk; cs_p = vif.mon_cb.cs_n;
end
""",
    sb_members="""bit [7:0] io [16];
bit [7:0] mem [64];
bit [31:0] gen = 32'h0000_000F;
bit pc_en = 1;""",
    predict="""
// independent embedded-controller model: windows, registers, response codes
int cl = espi_cls(t.opcode), n = espi_n(t.opcode);
bit [31:0] w = 0, v = 0;
foreach (t.wdata[i]) if (i < 4) w[8*i +: 8] = t.wdata[i];
t.rdata.delete(); t.status = 0; t.rcrc_ok = 0; t.rcode = 8'hFF;
if (cl != 7 && !t.bad_crc) begin
  t.rcode = 8'h08; t.status = ESPI_STATUS; t.rcrc_ok = 1;
  if ((cl == 3 || cl == 4) && (!pc_en || t.addr[15:4] != 12'h006 || int'(t.addr[3:0]) + n > 16)) t.rcode = 8'h02;
  if ((cl == 5 || cl == 6) && (!pc_en || t.addr[31:6] != 26'h3F8_2C00 || int'(t.addr[5:0]) + n > 64)) t.rcode = 8'h02;
  if (t.rcode == 8'h08) case (cl)
    1: begin
      case (t.addr[11:0])
        12'h004: v = 32'h0000_0001;
        12'h008: v = gen;
        12'h010: v = {30'h0, 1'b1, pc_en};
        default: v = 0;
      endcase
      for (int i = 0; i < 4; i++) t.rdata.push_back(v[8*i +: 8]);
    end
    2: begin
      if (t.addr[11:0] == 12'h008) gen[31:16] = w[31:16];
      if (t.addr[11:0] == 12'h010) pc_en = w[0];
    end
    3: for (int i = 0; i < n; i++) t.rdata.push_back(io[int'(t.addr[3:0]) + i]);
    4: for (int i = 0; i < n; i++) io[int'(t.addr[3:0]) + i] = t.wdata[i];
    5: for (int i = 0; i < n; i++) t.rdata.push_back(mem[int'(t.addr[5:0]) + i]);
    6: for (int i = 0; i < n; i++) mem[int'(t.addr[5:0]) + i] = t.wdata[i];
    default: ;
  endcase
end
""",
    checks="""
if (!(t.rcode inside {8'h08, 8'h02, 8'hFF})) fail(t, $sformatf("response code 0x%02h", t.rcode));
if (t.rcode != 8'hFF && !t.rcrc_ok) fail(t, "response CRC");
if (t.rcode != 8'hFF && t.bad_crc) fail(t, "target answered a command with a CRC error");
if (t.rcode == 8'h08 && t.rdata.size() != espi_rdata_len(t.opcode)) fail(t, "ACCEPT with the wrong amount of data");
""",
    coverage="""
cp_cls  : coverpoint tr.cls() { bins status = {0}; bins get_cfg = {1}; bins set_cfg = {2}; bins iord = {3};
                                bins iowr = {4}; bins memrd = {5}; bins memwr = {6}; bins unsupported = {7}; }
cp_n    : coverpoint espi_n(tr.opcode) { bins one = {1}; bins two = {2}; bins four = {4}; }
cp_code : coverpoint tr.rcode { bins accept = {8'h08}; bins non_fatal = {8'h02}; bins none = {8'hFF}; }
cp_crc  : coverpoint tr.bad_crc;
x_cls_code : cross cp_cls, cp_code {
  ignore_bins cfg_nf = (binsof(cp_cls.status) || binsof(cp_cls.get_cfg) || binsof(cp_cls.set_cfg)) && binsof(cp_code.non_fatal);
  ignore_bins unsup = binsof(cp_cls.unsupported) && !binsof(cp_code.none);
}
""",
    directed="""
// status and the configuration registers (read-only, partly writable, unimplemented)
t = item(); t.opcode = 8'h25; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h004; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h008; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h010; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h020; send(t);
t = item(); t.opcode = 8'h22; t.addr = 32'h008; t.wdata = '{8'h5A, 8'h5A, 8'hA5, 8'hA5}; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h008; send(t);
t = item(); t.opcode = 8'h22; t.addr = 32'h004; t.wdata = '{8'hFF, 8'hFF, 8'hFF, 8'hFF}; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h004; send(t);
// I/O cycles of every length, the window edges, outside the window
t = item(); t.opcode = 8'h47; t.addr = 32'h60; t.wdata = '{8'h11, 8'h22, 8'h33, 8'h44}; send(t);
t = item(); t.opcode = 8'h43; t.addr = 32'h60; send(t);
t = item(); t.opcode = 8'h40; t.addr = 32'h63; send(t);
t = item(); t.opcode = 8'h45; t.addr = 32'h6E; t.wdata = '{8'hAA, 8'hBB}; send(t);
t = item(); t.opcode = 8'h41; t.addr = 32'h6E; send(t);
t = item(); t.opcode = 8'h43; t.addr = 32'h6E; send(t);
t = item(); t.opcode = 8'h44; t.addr = 32'h80; t.wdata = '{8'h01}; send(t);
t = item(); t.opcode = 8'h44; t.addr = 32'h5F; t.wdata = '{8'h01}; send(t);
// memory cycles
t = item(); t.opcode = 8'h4F; t.addr = 32'hFE0B_0000; t.wdata = '{8'hDE, 8'hAD, 8'hBE, 8'hEF}; send(t);
t = item(); t.opcode = 8'h4B; t.addr = 32'hFE0B_0000; send(t);
t = item(); t.opcode = 8'h4D; t.addr = 32'hFE0B_003E; t.wdata = '{8'h12, 8'h34}; send(t);
t = item(); t.opcode = 8'h49; t.addr = 32'hFE0B_003E; send(t);
t = item(); t.opcode = 8'h4B; t.addr = 32'hFE0B_003E; send(t);
t = item(); t.opcode = 8'h48; t.addr = 32'hFE0C_0000; send(t);
// command CRC error and unsupported opcodes: no response, no side effect
t = item(); t.opcode = 8'h44; t.addr = 32'h60; t.wdata = '{8'h99}; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h40; t.addr = 32'h60; send(t);
t = item(); t.opcode = 8'h42; t.addr = 32'h60; send(t);
t = item(); t.opcode = 8'h25; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h008; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h22; t.addr = 32'h008; t.wdata = '{8'h00, 8'h00, 8'h00, 8'h00}; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h43; t.addr = 32'h64; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h4B; t.addr = 32'hFE0B_0010; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h4F; t.addr = 32'hFE0B_0010; t.wdata = '{8'h01, 8'h02, 8'h03, 8'h04}; t.bad_crc = 1; send(t);
t = item(); t.opcode = 8'h4D; t.addr = 32'hFE0B_0040; t.wdata = '{8'h01, 8'h02}; send(t);
t = item(); t.opcode = 8'h30; t.addr = 32'h60; send(t);
// peripheral channel disabled, then enabled again
t = item(); t.opcode = 8'h22; t.addr = 32'h010; t.wdata = '{8'h00, 8'h00, 8'h00, 8'h00}; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h010; send(t);
t = item(); t.opcode = 8'h40; t.addr = 32'h60; send(t);
t = item(); t.opcode = 8'h4C; t.addr = 32'hFE0B_0000; t.wdata = '{8'h00}; send(t);
t = item(); t.opcode = 8'h22; t.addr = 32'h010; t.wdata = '{8'hFF, 8'hFF, 8'hFF, 8'hFF}; send(t);
t = item(); t.opcode = 8'h40; t.addr = 32'h60; send(t);
""",
    drain_ns=2000,
    model="""
module espi_model (
  input  logic clk,
  input  logic rst_n,
  input  logic cs_n,
  input  logic sclk,
  input  logic mosi,
  output logic miso,
  output logic miso_oe
);
  localparam logic [15:0] ESPI_ST = 16'h030F;   // PC / NP / VW / OOB / flash free
  logic [7:0]  io  [0:15];
  logic [7:0]  mem [0:63];
  logic [7:0]  cb  [0:9];     // command bytes before the CRC
  logic [31:0] gen;
  logic        pc_en, cs_p, sclk_p, tar;
  logic [3:0]  nb, len;
  logic [2:0]  bitc;
  logic [6:0]  sh;
  logic [7:0]  crc;
  logic [1:0]  ph;            // 0 command, 1 turn-around, 2 response, 3 idle / ignore
  logic [63:0] rsp;
  logic [6:0]  rbits;

  wire       rise = !cs_n && sclk && !sclk_p;
  wire       fall = !cs_n && !sclk && sclk_p;
  wire [7:0] byte_in = {sh, mosi};

  function automatic logic [7:0] crc8(input logic [7:0] c, input logic [7:0] b);
    logic [7:0] x;
    x = c ^ b;
    for (int k = 0; k < 8; k++) x = x[7] ? ((x << 1) ^ 8'h07) : (x << 1);
    crc8 = x;
  endfunction

  // command length in bytes with the CRC; 0 = not supported
  function automatic logic [3:0] cmd_len(input logic [7:0] op);
    logic [3:0] n;
    n = (op[1:0] == 2'd3) ? 4'd4 : {2'b0, op[1:0]} + 4'd1;
    case (op)
      8'h25:               cmd_len = 4'd2;
      8'h21:               cmd_len = 4'd4;
      8'h22:               cmd_len = 4'd8;
      8'h40, 8'h41, 8'h43: cmd_len = 4'd4;
      8'h44, 8'h45, 8'h47: cmd_len = 4'd4 + n;
      8'h48, 8'h49, 8'h4B: cmd_len = 4'd6;
      8'h4C, 8'h4D, 8'h4F: cmd_len = 4'd6 + n;
      default:             cmd_len = 4'd0;
    endcase
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 16; i++) io[i] <= '0;
      for (int i = 0; i < 64; i++) mem[i] <= '0;
      for (int i = 0; i < 10; i++) cb[i] <= '0;
      gen <= 32'h0000_000F; pc_en <= 1'b1; cs_p <= 1'b1; sclk_p <= 1'b0; tar <= 1'b0;
      nb <= '0; len <= '0; bitc <= '0; sh <= '0; crc <= '0; ph <= 2'd3;
      rsp <= '0; rbits <= '0; miso <= 1'b1; miso_oe <= 1'b0;
    end else begin
      cs_p <= cs_n; sclk_p <= sclk;
      if (cs_n) begin
        ph <= 2'd3; miso <= 1'b1; miso_oe <= 1'b0; rbits <= '0;
      end else if (cs_p) begin                     // CS# fall: a new command
        ph <= 2'd0; nb <= '0; len <= '0; bitc <= '0; crc <= '0; tar <= 1'b0;
      end else if (rise && ph == 2'd0) begin
        bitc <= bitc + 3'd1;
        sh <= byte_in[6:0];
        if (bitc == 3'd7) begin : got_byte
          logic [3:0]  l, rl;
          logic [7:0]  op, code, c;
          logic [31:0] a, w, v;
          logic [2:0]  n;
          logic [63:0] r;
          l = (nb == 4'd0) ? cmd_len(byte_in) : len;
          cb[nb] <= byte_in;
          nb <= nb + 4'd1;
          if (nb == 4'd0) len <= l;
          if (l == 4'd0) ph <= 2'd3;                 // not supported: stay silent
          else if (nb + 4'd1 < l) crc <= crc8(crc, byte_in);
          else begin                                 // byte_in is the command CRC
            op = cb[0];
            n = (op[1:0] == 2'd3) ? 3'd4 : {1'b0, op[1:0]} + 3'd1;
            a = (op[7:3] == 5'b01001) ? {cb[1], cb[2], cb[3], cb[4]} : {16'h0, cb[1], cb[2]};
            w = {cb[6], cb[5], cb[4], cb[3]};
            code = 8'h08;
            if (byte_in != crc) code = 8'hFF;
            else if (op[7:3] == 5'b01000 &&
                     (!pc_en || a[15:4] != 12'h006 || {1'b0, a[3:0]} + {2'b0, n} > 5'd16)) code = 8'h02;
            else if (op[7:3] == 5'b01001 &&
                     (!pc_en || a[31:6] != 26'h3F8_2C00 || {1'b0, a[5:0]} + {4'b0, n} > 7'd64)) code = 8'h02;
            if (code == 8'hFF) ph <= 2'd3;           // CRC error: no response
            else begin
              r = {56'h0, code}; rl = 4'd1;
              if (code == 8'h08) begin
                if (op == 8'h21) begin
                  case (a[11:0])
                    12'h004: v = 32'h0000_0001;
                    12'h008: v = gen;
                    12'h010: v = {30'h0, 1'b1, pc_en};
                    default: v = 32'h0;
                  endcase
                  r = {r[31:0], v[7:0], v[15:8], v[23:16], v[31:24]}; rl = rl + 4'd4;
                end
                if (op == 8'h22) begin
                  if (a[11:0] == 12'h008) gen <= {w[31:16], gen[15:0]};
                  if (a[11:0] == 12'h010) pc_en <= w[0];
                end
                for (int k = 0; k < 4; k++)
                  if (k < n) begin
                    if (op[7:2] == 6'b010000) begin r = {r[55:0], io[a[3:0] + 4'(k)]}; rl = rl + 4'd1; end
                    if (op[7:2] == 6'b010001) io[a[3:0] + 4'(k)] <= cb[3 + k];
                    if (op[7:2] == 6'b010010) begin r = {r[55:0], mem[a[5:0] + 6'(k)]}; rl = rl + 4'd1; end
                    if (op[7:2] == 6'b010011) mem[a[5:0] + 6'(k)] <= cb[5 + k];
                  end
              end
              r = {r[47:0], ESPI_ST[7:0], ESPI_ST[15:8]}; rl = rl + 4'd2;
              c = 8'h00;
              for (int k = 0; k < 8; k++) if (k < rl) c = crc8(c, r[8 * (rl - 1 - k) +: 8]);
              r = {r[55:0], c}; rl = rl + 4'd1;
              rsp <= r << (7'd64 - {rl, 3'b000});
              rbits <= {rl, 3'b000};
              ph <= 2'd1; tar <= 1'b0;
            end
          end
        end
      end else if (rise && ph == 2'd1) begin       // two turn-around cycles
        tar <= 1'b1;
        if (tar) ph <= 2'd2;
      end else if (fall && ph == 2'd2) begin        // response: MISO changes with SCLK low
        if (rbits != 0) begin
          miso <= rsp[63]; miso_oe <= 1'b1; rsp <= rsp << 1; rbits <= rbits - 7'd1;
        end else begin
          miso <= 1'b1; miso_oe <= 1'b0;
        end
      end
    end
  end
endmodule
""",
    sva="""
logic sclk_d, cs_d;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin sclk_d <= 1'b0; cs_d <= 1'b1; end else begin sclk_d <= sclk; cs_d <= cs_n; end
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({cs_n, miso, miso_oe}))
  else $error("eSPI: X on CS# / MISO");
// the target only drives MISO while selected
assert property (@(posedge clk) disable iff (!rst_n) cs_n && cs_d |-> !miso_oe)
  else $error("eSPI: target drives MISO while CS# is high");
// MISO changes only after a SCLK falling edge (or when released at CS# rise)
assert property (@(posedge clk) disable iff (!rst_n) $changed(miso) |-> $past(cs_n) || ($past(!sclk) && $past(sclk_d)))
  else $error("eSPI: MISO changed outside a SCLK low phase");
// a released MISO reads high
assert property (@(posedge clk) disable iff (!rst_n) !miso_oe |-> miso)
  else $error("eSPI: MISO low while released");
cover property (@(posedge clk) disable iff (!rst_n) $rose(miso_oe));
cover property (@(posedge clk) disable iff (!rst_n) $rose(cs_n) && !$past(miso_oe, 2));
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic cs_n = 1, sclk = 0, mosi = 1;
wire miso, miso_oe;

always #5 clk = ~clk;

espi_model u_dut (.clk(clk), .rst_n(rst_n), .cs_n(cs_n), .sclk(sclk), .mosi(mosi), .miso(miso), .miso_oe(miso_oe));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic bit [7:0] crc8(bit [7:0] c, bit [7:0] b);
  c ^= b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction

// bus rules watched all the time
int oe_hi = 0, miso_chg = 0, oe_cnt = 0;
logic sclk_q = 1'b0, miso_q = 1'b1, cs_q = 1'b1;
always @(posedge clk) begin
  if (rst_n && cs_n && cs_q && miso_oe) oe_hi++;
  if (rst_n && sclk && sclk_q && miso !== miso_q) miso_chg++;
  if (miso_oe) oe_cnt++;
  sclk_q <= sclk; miso_q <= miso; cs_q <= cs_n;
end

task automatic w(input int n); repeat (n) @(posedge clk); #1; endtask
task automatic cyc(input logic o, output logic i);
  sclk = 0; mosi = o; w(2); i = miso; sclk = 1; w(2);
endtask

// pk: command bytes (the CRC is appended); rr: nr response bytes clocked back
bit [7:0] pk[$], rr[$];
logic tar_oe;
task automatic xfer(input int nr, input bit bad = 0, input int cut = -1);
  bit [7:0] c, x;
  logic b;
  int nbt;
  c = 0; nbt = 0; x = 0;
  rr.delete();
  foreach (pk[i]) c = crc8(c, pk[i]);
  pk.push_back(c ^ {7'h0, bad});
  cs_n = 0; w(2);
  foreach (pk[i]) begin
    x = pk[i];
    for (int k = 7; k >= 0; k--)
      if (cut < 0 || nbt < cut) begin cyc(x[k], b); nbt++; end
  end
  tar_oe = 0;
  if (cut < 0) begin
    cyc(1, b); tar_oe = tar_oe | miso_oe;
    cyc(1, b); tar_oe = tar_oe | miso_oe;
    for (int i = 0; i < nr; i++) begin
      for (int k = 7; k >= 0; k--) begin cyc(1, b); x[k] = b; end
      rr.push_back(x);
    end
  end
  sclk = 0; w(2); cs_n = 1; w(4);
  pk.delete();
endtask

// response: code, nd data bytes, status 0x030F LSB first, CRC, then 0xFF
task automatic chk_rsp(input bit [7:0] code, input int nd, input string msg);
  bit [7:0] c;
  bit ok;
  c = 0;
  ok = (rr.size() >= nd + 4) && rr[0] == code && rr[nd + 1] == 8'h0F && rr[nd + 2] == 8'h03;
  for (int i = 0; i < nd + 3; i++) c = crc8(c, rr[i]);
  ok = ok && rr[nd + 3] == c;
  for (int i = nd + 4; i < rr.size(); i++) ok = ok && rr[i] == 8'hFF;
  chk(ok && tar_oe === 1'b0, msg);
endtask
task automatic chk_none(input string msg);
  bit ok;
  ok = 1;
  foreach (rr[i]) ok = ok && rr[i] == 8'hFF;
  chk(ok, msg);
endtask

task automatic get_cfg(input bit [11:0] a);
  pk.push_back(8'h21); pk.push_back({4'h0, a[11:8]}); pk.push_back(a[7:0]); xfer(8);
endtask
task automatic set_cfg(input bit [11:0] a, input bit [31:0] v, input bit bad = 0);
  pk.push_back(8'h22); pk.push_back({4'h0, a[11:8]}); pk.push_back(a[7:0]);
  pk.push_back(v[7:0]); pk.push_back(v[15:8]); pk.push_back(v[23:16]); pk.push_back(v[31:24]);
  xfer(4, bad);
endtask
task automatic io(input bit [7:0] op, input bit [15:0] a, input bit [31:0] d, input bit bad = 0);
  int n;
  n = (op[1:0] == 2'd3) ? 4 : op[1:0] + 1;
  pk.push_back(op); pk.push_back(a[15:8]); pk.push_back(a[7:0]);
  if (op[2]) for (int i = 0; i < n; i++) pk.push_back(d[8*i +: 8]);
  xfer(op[2] ? 4 : 4 + n, bad);
endtask
task automatic memop(input bit [7:0] op, input bit [31:0] a, input bit [31:0] d);
  int n;
  n = (op[1:0] == 2'd3) ? 4 : op[1:0] + 1;
  pk.push_back(op); pk.push_back(a[31:24]); pk.push_back(a[23:16]); pk.push_back(a[15:8]); pk.push_back(a[7:0]);
  if (op[2]) for (int i = 0; i < n; i++) pk.push_back(d[8*i +: 8]);
  xfer(op[2] ? 4 : 4 + n);
endtask
function automatic bit [31:0] rd32();
  rd32 = {rr[4], rr[3], rr[2], rr[1]};
endfunction

initial begin
  int oe0;
  repeat (3) @(posedge clk);
  chk(miso === 1'b1 && miso_oe === 1'b0, "MISO released during reset");
  rst_n = 1;
  w(3);

  pk.push_back(8'h25); xfer(4);
  chk_rsp(8'h08, 0, "GET_STATUS: ACCEPT, status 0x030F, CRC");

  // configuration registers
  get_cfg(12'h004); chk_rsp(8'h08, 4, "GET_CONFIGURATION: ACCEPT with 4 data bytes");
  chk(rd32() == 32'h0000_0001, $sformatf("device ID 0x00000001 (%h)", rd32()));
  get_cfg(12'h008); chk(rd32() == 32'h0000_000F, "general capabilities 0x0000000F after reset");
  get_cfg(12'h010); chk(rd32() == 32'h0000_0003, "peripheral channel enabled and ready after reset");
  get_cfg(12'h020); chk(rd32() == 32'h0, "unimplemented register reads 0");
  set_cfg(12'h008, 32'hA5A5_5A5A); chk_rsp(8'h08, 0, "SET_CONFIGURATION: ACCEPT, no data");
  get_cfg(12'h008); chk(rd32() == 32'hA5A5_000F, $sformatf("only bits 31:16 of 0x08 written (%h)", rd32()));
  set_cfg(12'h008, 32'h1234_0000, 1); chk_none("SET_CONFIGURATION with a CRC error: no response");
  get_cfg(12'h008); chk(rd32() == 32'hA5A5_000F, "and no write");
  set_cfg(12'h004, 32'hFFFF_FFFF); get_cfg(12'h004);
  chk(rd32() == 32'h0000_0001, "device ID is read-only");
  set_cfg(12'h020, 32'hFFFF_FFFF); get_cfg(12'h020);
  chk(rd32() == 32'h0, "unimplemented register ignores writes");

  // peripheral channel disabled: short cycles get NON_FATAL_ERROR
  set_cfg(12'h010, 32'hFFFF_FFFE); get_cfg(12'h010);
  chk(rd32() == 32'h0000_0002, "channel disabled, ready bit read-only");
  io(8'h40, 16'h0060, 0); chk_rsp(8'h02, 0, "I/O read, channel disabled: NON_FATAL_ERROR");
  memop(8'h48, 32'hFE0B_0000, 0); chk_rsp(8'h02, 0, "memory read, channel disabled: NON_FATAL_ERROR");
  io(8'h44, 16'h0061, 32'h77); chk_rsp(8'h02, 0, "I/O write, channel disabled: NON_FATAL_ERROR");
  set_cfg(12'h010, 32'h0000_0001); get_cfg(12'h010);
  chk(rd32() == 32'h0000_0003, "channel enabled again");

  // I/O window
  io(8'h43, 16'h0060, 0); chk_rsp(8'h08, 4, "I/O read 4 bytes: ACCEPT");
  chk(rd32() == 32'h0, "I/O registers 0 after reset (and the disabled write did nothing)");
  io(8'h47, 16'h0060, 32'h4433_2211); chk_rsp(8'h08, 0, "I/O write 4 bytes: ACCEPT, no data");
  io(8'h43, 16'h0060, 0); chk(rd32() == 32'h4433_2211, $sformatf("I/O read back, LSB first (%h)", rd32()));
  io(8'h40, 16'h0063, 0); chk_rsp(8'h08, 1, "I/O read 1 byte"); chk(rr[1] == 8'h44, "1-byte read at an offset");
  io(8'h41, 16'h0061, 0); chk_rsp(8'h08, 2, "I/O read 2 bytes"); chk(rr[1] == 8'h22 && rr[2] == 8'h33, "2-byte read");
  io(8'h45, 16'h006E, 32'hBBAA); io(8'h41, 16'h006E, 0);
  chk(rr[1] == 8'hAA && rr[2] == 8'hBB, "2-byte write and read at the window end");
  io(8'h44, 16'h0062, 32'h5C); io(8'h43, 16'h0060, 0);
  chk(rd32() == 32'h445C_2211, "1-byte write leaves the neighbours");
  io(8'h43, 16'h006E, 0); chk_rsp(8'h02, 0, "4-byte read across the window end: NON_FATAL_ERROR, rest released");
  io(8'h44, 16'h0080, 32'h1); chk_rsp(8'h02, 0, "I/O write above the window: NON_FATAL_ERROR");
  io(8'h44, 16'h005F, 32'h1); chk_rsp(8'h02, 0, "I/O write below the window: NON_FATAL_ERROR");
  io(8'h44, 16'h0160, 32'h1); chk_rsp(8'h02, 0, "I/O 0x0160 (upper address bits) outside the window");
  io(8'h43, 16'h0060, 0); chk(rd32() == 32'h445C_2211, "rejected writes changed nothing");

  // memory window
  memop(8'h4B, 32'hFE0B_0000, 0); chk_rsp(8'h08, 4, "memory read 4 bytes: ACCEPT");
  chk(rd32() == 32'h0, "memory 0 after reset");
  memop(8'h4F, 32'hFE0B_0000, 32'hEFBE_ADDE); chk_rsp(8'h08, 0, "memory write 4 bytes: ACCEPT");
  memop(8'h4B, 32'hFE0B_0000, 0); chk_rsp(8'h08, 4, "memory read 4 bytes");
  chk(rr[1] == 8'hDE && rr[2] == 8'hAD && rr[3] == 8'hBE && rr[4] == 8'hEF, "memory read back");
  memop(8'h48, 32'hFE0B_0001, 0); chk(rr[1] == 8'hAD, "1-byte memory read at an offset");
  memop(8'h4D, 32'hFE0B_003E, 32'h3412); memop(8'h49, 32'hFE0B_003E, 0);
  chk_rsp(8'h08, 2, "2-byte memory read at the window end"); chk(rr[1] == 8'h12 && rr[2] == 8'h34, "window end data");
  memop(8'h4B, 32'hFE0B_003E, 0); chk_rsp(8'h02, 0, "memory read across the window end: NON_FATAL_ERROR");
  memop(8'h48, 32'hFE0B_0040, 0); chk_rsp(8'h02, 0, "memory read above the window: NON_FATAL_ERROR");
  memop(8'h48, 32'hFE0A_FFFF, 0); chk_rsp(8'h02, 0, "memory read below the window: NON_FATAL_ERROR");
  memop(8'h48, 32'hFF0B_0000, 0); chk_rsp(8'h02, 0, "memory read with other upper address bits: NON_FATAL_ERROR");

  // no response: CRC error, bad length code, unknown opcode
  oe0 = oe_cnt;
  io(8'h44, 16'h0060, 32'h99, 1); chk_none("I/O write with a command CRC error: no response");
  pk.push_back(8'h42); pk.push_back(8'h00); pk.push_back(8'h60); xfer(4);
  chk_none("length code 0b10: no response");
  pk.push_back(8'h30); pk.push_back(8'h00); pk.push_back(8'h60); xfer(4);
  chk_none("unknown opcode: no response");
  chk(oe_cnt == oe0, "MISO never driven for those");
  io(8'h40, 16'h0060, 0); chk(rr[1] == 8'h11, "the write with the CRC error did not happen");

  // a command cut short by CS#, then a normal one
  pk.push_back(8'h21); pk.push_back(8'h00); pk.push_back(8'h08); xfer(0, 0, 12);
  pk.push_back(8'h25); xfer(4);
  chk_rsp(8'h08, 0, "command cut short by CS#: the next one is fine");
  // a response cut short by CS#, then a normal one
  pk.push_back(8'h21); pk.push_back(8'h00); pk.push_back(8'h04); xfer(2);
  get_cfg(12'h004); chk_rsp(8'h08, 4, "response cut short by CS#: the next one is fine");

  chk(oe_hi == 0, "MISO released whenever CS# is high");
  chk(miso_chg == 0, $sformatf("MISO changes only while SCLK is low (%0d)", miso_chg));
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #3000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
