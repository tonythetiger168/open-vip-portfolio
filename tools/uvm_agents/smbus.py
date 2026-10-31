# SMBus 3.x host agent with PMBus 1.3 commands and Packet Error Checking.
# tb/top_tb.sv smbus_model: PMBus device at 7-bit address 0x5A on an
# open-drain bus (scl = host & device, sda = host & device), sampled on the
# system clock; it stretches SCL after every address ACK.
#
# Commands of the model (write length / read length in bytes):
#   0x01 OPERATION      1 / 1   reset 0x80
#   0x03 CLEAR_FAULTS   0 / -   send byte, clears STATUS_CML
#   0x21 VOUT_COMMAND   2 / 2   reset 0x0000
#   0x78 STATUS_BYTE    - / 1   bit 1 = CML (STATUS_CML != 0)
#   0x7E STATUS_CML     - / 1   bit 7 invalid command, 6 invalid data, 5 PEC failed
#   0x8B READ_VOUT      - / 2   = VOUT_COMMAND
#   0x98 PMBUS_REVISION - / 1   0x33
# An unsupported command is NACKed and sets STATUS_CML[7]; a data byte to a
# read-only command, or a byte after the PEC, is NACKed and sets
# STATUS_CML[6]; a wrong PEC is NACKed, sets STATUS_CML[5] and the write is
# discarded. A write takes effect at STOP. Reads: A(W) C Sr A(R) data
# [PEC] then 0xFF; PEC = CRC-8 (x^8+x^2+x+1) over every byte of the
# transaction, addresses included.
#
# The host sends every byte of a transfer even after a NACK (then STOP), so
# the monitor can rebuild the transfer; it uses the PMBus command table above
# to tell data bytes from the PEC byte.

SMBUS_FUNCS = """
// SMBus PEC: CRC-8, polynomial x^8 + x^2 + x + 1, initial value 0, MSB first
function automatic bit [7:0] crc8(bit [7:0] c, bit [7:0] b);
  c ^= b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction

// PMBus command table of the device: bytes written / read, -1 = not allowed
function automatic int wlen(bit [7:0] cmd);
  case (cmd)
    8'h01: return 1;
    8'h03: return 0;
    8'h21: return 2;
    default: return -1;
  endcase
endfunction

function automatic int rlen(bit [7:0] cmd);
  case (cmd)
    8'h01, 8'h78, 8'h7E, 8'h98: return 1;
    8'h21, 8'h8B: return 2;
    default: return -1;
  endcase
endfunction

function automatic bit valid_cmd(bit [7:0] cmd);
  return wlen(cmd) >= 0 || rlen(cmd) >= 0;
endfunction
"""

SPEC = dict(
    vip="SMBus-UVM-VIP", p="smbus", P="SMBus/PMBus", dir="smbus", family="Power / Management",
    desc="SMBus 3.x host VIP with PMBus 1.3 command set: open-drain bit-level driver, START / repeated "
         "START / STOP, clock stretching, Packet Error Checking (CRC-8) and STATUS_CML fault reporting.",
    about="""
SMBus and PMBus carry board management and power control in servers (BMC to
voltage regulators and power supplies). The scoreboard holds its own copy of the
device registers and of the PMBus fault rules and predicts, for every transfer,
which bytes the device ACKs, the data and PEC it returns, and the STATUS_CML bits
a fault sets. The monitor decodes transfers from the SCL/SDA wires alone and
checks the PEC of every read.""",
    defs="""
typedef enum bit [2:0] {SEND_BYTE, WRITE_BYTE, WRITE_WORD, READ_BYTE, READ_WORD} smbus_kind_e;
localparam bit [6:0] SMBUS_DEV_ADDR = 7'h5A;
""" + SMBUS_FUNCS,
    timeout=400,
    interface="""
// Open-drain bus: each side pulls low (0) or releases (1); the wires are
// the wired AND of both sides.
interface smbus_if (input logic clk);
  logic rst_n;

  logic scl_m, sda_m;     // host (agent) side
  logic scl_o, sda_o;     // device (DUT) side
  wire  scl = scl_m & scl_o;
  wire  sda = sda_m & sda_o;

  modport DUT (input clk, rst_n, scl, sda, output scl_o, sda_o);
  modport MON (input clk, rst_n, scl, sda, scl_o, sda_o);

  clocking drv_cb @(posedge clk);
    input rst_n, scl, sda;
    inout scl_m, sda_m;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, scl, sda, scl_o, sda_o;
  endclocking
endinterface
""",
    ports=[("in", "logic", "scl"), ("in", "logic", "sda"),
           ("out", "logic", "scl_o"), ("out", "logic", "sda_o")],
    cfg="int unsigned half = 4;   // system clocks per SCL half period",
    fields=[
        ("smbus_kind_e", "kind", "req"),
        ("bit [6:0]", "addr", "req"),
        ("bit [7:0]", "cmd", "req"),
        ("bit [15:0]", "wdata", "req"),
        ("bit", "use_pec", "req"),
        ("bit", "bad_pec", "req"),
        ("bit [7:0]", "acks", "rsp"),        # bit i: host-written byte i was ACKed
        ("bit [15:0]", "rdata", "rsp"),
        ("bit [7:0]", "rpec", "rsp"),
        ("int unsigned", "stretch", "info"), # clocks SCL was held low by the device
    ],
    constraints="""
constraint c_addr { addr dist { SMBUS_DEV_ADDR := 9, [7'h00 : 7'h7F] :/ 1 }; }
constraint c_cmd  { cmd inside {8'h01, 8'h03, 8'h21, 8'h78, 8'h7E, 8'h8B, 8'h98, 8'h55, 8'hD0}; }
constraint c_kind {
  (cmd == 8'h01) -> kind inside {WRITE_BYTE, READ_BYTE};
  (cmd == 8'h03) -> kind == SEND_BYTE;
  (cmd == 8'h21) -> kind inside {WRITE_WORD, READ_WORD};
  (cmd inside {8'h78, 8'h7E, 8'h98}) -> kind inside {READ_BYTE, WRITE_BYTE};
  (cmd == 8'h8B) -> kind inside {READ_WORD, WRITE_WORD};
  (cmd inside {8'h55, 8'hD0}) -> kind inside {WRITE_BYTE, READ_BYTE};
}
// PEC only where the monitor can tell it from data (the command allows the kind)
constraint c_pec {
  (cmd inside {8'h55, 8'hD0}) -> !use_pec;
  (cmd inside {8'h78, 8'h7E, 8'h98, 8'h8B} && kind inside {WRITE_BYTE, WRITE_WORD}) -> !use_pec;
  bad_pec -> use_pec;
  (kind inside {READ_BYTE, READ_WORD}) -> !bad_pec;
  bad_pec dist { 0 := 4, 1 := 1 };
}
constraint c_wd {
  (kind == WRITE_BYTE) -> wdata[15:8] == 0;
  (kind inside {SEND_BYTE, READ_BYTE, READ_WORD}) -> wdata == 0;
}
""",
    tr_functions="""
function int unsigned nwrite();   // data bytes written
  case (kind) WRITE_BYTE: return 1; WRITE_WORD: return 2; default: return 0; endcase
endfunction
function int unsigned nread();    // data bytes read
  case (kind) READ_BYTE: return 1; READ_WORD: return 2; default: return 0; endcase
endfunction
function bit is_read(); return kind inside {READ_BYTE, READ_WORD}; endfunction
""",
    drv_rsp=True,
    drv_desc="bit-level open-drain host: START, bytes MSB first with ACK, repeated START, STOP; honours clock stretching",
    drv_idle="""
vif.drv_cb.scl_m <= 1'b1;
vif.drv_cb.sda_m <= 1'b1;
""",
    drv_tasks="""
task wait_clk(int unsigned n); repeat (n) @(vif.drv_cb); endtask

// release SCL and wait until the wire is high (the device may stretch)
task scl_high(smbus_transaction t);
  int unsigned to = 0;
  vif.drv_cb.scl_m <= 1'b1;
  @(vif.drv_cb);
  while (vif.drv_cb.scl !== 1'b1 && to < cfg.timeout_cycles) begin @(vif.drv_cb); to++; t.stretch++; end
  if (vif.drv_cb.scl !== 1'b1) `uvm_error("TIMEOUT", "SMBus: SCL held low")
endtask

task start_cond(smbus_transaction t, bit repeated);
  if (repeated) begin
    vif.drv_cb.sda_m <= 1'b1; wait_clk(cfg.half / 2);
    scl_high(t); wait_clk(cfg.half);
  end
  vif.drv_cb.sda_m <= 1'b0; wait_clk(cfg.half);
  vif.drv_cb.scl_m <= 1'b0; wait_clk(cfg.half / 2);
endtask

task stop_cond(smbus_transaction t);
  vif.drv_cb.sda_m <= 1'b0; wait_clk(cfg.half / 2);
  scl_high(t); wait_clk(cfg.half);
  vif.drv_cb.sda_m <= 1'b1; wait_clk(2 * cfg.half);
endtask

// one bit: SDA set while SCL is low, sampled half way through SCL high
task bit_xfer(smbus_transaction t, bit out, output bit in);
  vif.drv_cb.sda_m <= out; wait_clk(cfg.half / 2);
  scl_high(t); wait_clk(cfg.half / 2);
  in = vif.drv_cb.sda;
  wait_clk(cfg.half / 2);
  vif.drv_cb.scl_m <= 1'b0; wait_clk(cfg.half / 2);
endtask

task wr_byte(smbus_transaction t, bit [7:0] b, output bit ack);
  bit in;
  for (int i = 7; i >= 0; i--) bit_xfer(t, b[i], in);
  bit_xfer(t, 1'b1, in);
  ack = !in;
endtask

task rd_byte(smbus_transaction t, bit ack, output bit [7:0] b);
  bit in;
  for (int i = 7; i >= 0; i--) begin bit_xfer(t, 1'b1, in); b[i] = in; end
  bit_xfer(t, !ack, in);
endtask
""",
    drv_item="""
bit [7:0] crc = 0, b, wb[$];
bit ack;
int unsigned nb = 0, nr;
t.acks = 0; t.rdata = 0; t.rpec = 0; t.stretch = 0;
// host-written bytes of the first segment
wb.push_back({t.addr, 1'b0});
wb.push_back(t.cmd);
for (int i = 0; i < t.nwrite(); i++) wb.push_back(t.wdata[8*i +: 8]);
if (t.use_pec && !t.is_read()) begin
  foreach (wb[i]) crc = crc8(crc, wb[i]);
  wb.push_back(crc ^ {7'h0, t.bad_pec});
end
@(vif.drv_cb);
start_cond(t, 0);
foreach (wb[i]) begin wr_byte(t, wb[i], ack); t.acks[nb++] = ack; end
if (t.is_read()) begin
  start_cond(t, 1);
  wr_byte(t, {t.addr, 1'b1}, ack); t.acks[nb++] = ack;
  nr = t.nread() + (t.use_pec ? 1 : 0);
  for (int i = 0; i < nr; i++) begin
    rd_byte(t, i != nr - 1, b);
    if (i < t.nread()) t.rdata[8*i +: 8] = b; else t.rpec = b;
  end
end
stop_cond(t);
""",
    mon_desc="START / repeated START / STOP and bytes with their ACK bit from the SCL/SDA wires; decoded with the PMBus command table",
    mon_members="bit [7:0] seg0[$], seg1[$]; bit ack0[$], ack1[$];",
    mon_run="""
bit scl_p = 1, sda_p = 1, in_xfer = 0, rep = 0;
int unsigned nbit = 0, held = 0;
bit [7:0] sh = 0;
forever begin
  bit scl, sda;
  @(vif.mon_cb);
  scl = vif.mon_cb.scl; sda = vif.mon_cb.sda;
  if (!scl && !vif.mon_cb.scl_o) held++;
  if (scl && scl_p && sda_p && !sda) begin            // START or repeated START
    if (!in_xfer) begin seg0.delete(); seg1.delete(); ack0.delete(); ack1.delete(); held = 0; rep = 0; end
    else rep = 1;
    in_xfer = 1; nbit = 0;
  end else if (scl && scl_p && !sda_p && sda) begin   // STOP
    if (in_xfer) decode(held);
    in_xfer = 0;
  end else if (in_xfer && scl && !scl_p) begin        // SCL rising: sample
    if (nbit < 8) sh = {sh[6:0], sda};
    else if (rep) begin seg1.push_back(sh); ack1.push_back(!sda); end
    else begin seg0.push_back(sh); ack0.push_back(!sda); end
    nbit = (nbit == 8) ? 0 : nbit + 1;
  end
  scl_p = scl; sda_p = sda;
end
""",
    mon_tasks="""
// rebuild the transfer from the two segments (before / after repeated START)
function void decode(int unsigned held);
  smbus_transaction t = smbus_transaction::type_id::create("t");
  int nb = 0, d, L;
  bit [7:0] crc = 0;
  if (seg0.size() < 2) begin
    `uvm_error("MON", $sformatf("SMBus: transfer with %0d bytes before STOP / repeated START", seg0.size()))
    return;
  end
  t.addr = seg0[0][7:1];
  t.cmd  = seg0[1];
  t.stretch = held;
  foreach (seg0[i]) t.acks[nb++] = ack0[i];
  d = seg0.size() - 2;
  if (seg1.size() == 0) begin                       // write: A C data [PEC]
    L = wlen(t.cmd);
    t.use_pec = (L >= 0 && d == L + 1);
    if (L < 0 || !t.use_pec) L = d;
    t.kind = (L == 0) ? SEND_BYTE : (L == 1) ? WRITE_BYTE : WRITE_WORD;
    for (int i = 0; i < L && i < 2; i++) t.wdata[8*i +: 8] = seg0[2 + i];
    if (t.use_pec) begin
      for (int i = 0; i < 2 + L; i++) crc = crc8(crc, seg0[i]);
      t.bad_pec = (seg0[2 + L] != crc);
    end
  end else begin                                    // read: A C Sr A data [PEC]
    int r = seg1.size() - 1;
    t.acks[nb++] = ack1[0];
    L = rlen(t.cmd);
    t.use_pec = (L >= 0 && r == L + 1);
    if (L < 0 || !t.use_pec) L = r;
    t.kind = (L == 1) ? READ_BYTE : READ_WORD;
    for (int i = 0; i < L && i < 2; i++) t.rdata[8*i +: 8] = seg1[1 + i];
    if (t.use_pec) t.rpec = seg1[1 + L];
    // the host ACKs every byte but the last
    for (int i = 1; i < seg1.size(); i++)
      if (ack1[i] != (i != seg1.size() - 1))
        `uvm_error("MON", $sformatf("SMBus: host ACK/NACK wrong on read byte %0d", i - 1))
  end
  publish(t);
endfunction
""",
    sb_members="""bit [7:0]  operation = 8'h80;
bit [15:0] vout = 16'h0;
bit [7:0]  cml = 8'h0;""",
    predict="""
// independent model of the device: ACK of every host byte, data, PEC, faults
bit drop = 0, ok;
bit [7:0] crc = 0, val[2];
int nb = 0, L;
t.acks = 0; t.rdata = 0; t.rpec = 0;
// address (write)
ok = (t.addr == SMBUS_DEV_ADDR);
t.acks[nb++] = ok; drop = !ok;
crc = crc8(crc, {t.addr, 1'b0});
// command
if (!drop) begin
  ok = valid_cmd(t.cmd);
  if (!ok) begin cml[7] = 1; drop = 1; end
  t.acks[nb++] = ok;
end else nb++;
crc = crc8(crc, t.cmd);
if (!t.is_read()) begin
  bit [7:0] wb[$];
  for (int i = 0; i < t.nwrite(); i++) wb.push_back(t.wdata[8*i +: 8]);
  if (t.use_pec) begin
    bit [7:0] c = crc;
    foreach (wb[i]) c = crc8(c, wb[i]);
    wb.push_back(c ^ {7'h0, t.bad_pec});
  end
  L = wlen(t.cmd);
  foreach (wb[i]) begin
    if (drop) ok = 0;
    else if (L < 0 || i > L) begin ok = 0; cml[6] = 1; drop = 1; end
    else if (i < L) begin ok = 1; crc = crc8(crc, wb[i]); end
    else begin                                      // i == L: PEC
      ok = (wb[i] == crc);
      if (!ok) begin cml[5] = 1; drop = 1; end
    end
    t.acks[nb++] = ok;
  end
  // STOP: a complete, error-free write takes effect
  if (!drop && L >= 0 && wb.size() >= L) begin
    case (t.cmd)
      8'h01: operation = t.wdata[7:0];
      8'h03: cml = 8'h0;
      8'h21: vout = t.wdata;
    endcase
  end
end else begin
  bit ra;
  int nr = t.nread() + (t.use_pec ? 1 : 0);
  ra = !drop && t.addr == SMBUS_DEV_ADDR && rlen(t.cmd) >= 0;
  if (!drop && t.addr == SMBUS_DEV_ADDR && rlen(t.cmd) < 0) cml[7] = 1;
  t.acks[nb++] = ra;
  if (ra) begin
    crc = crc8(crc, {t.addr, 1'b1});
    case (t.cmd)
      8'h01: begin val[0] = operation; val[1] = 8'h0; end
      8'h21, 8'h8B: begin val[0] = vout[7:0]; val[1] = vout[15:8]; end
      8'h78: begin val[0] = {6'h0, cml != 8'h0, 1'b0}; val[1] = 8'h0; end
      8'h7E: begin val[0] = cml; val[1] = 8'h0; end
      8'h98: begin val[0] = 8'h33; val[1] = 8'h0; end
    endcase
    L = rlen(t.cmd);
    for (int i = 0; i < nr; i++) begin
      bit [7:0] b = (i < L) ? val[i] : (i == L) ? crc : 8'hFF;
      if (i < L) crc = crc8(crc, b);
      if (i < t.nread()) t.rdata[8*i +: 8] = b; else t.rpec = b;
    end
  end else begin
    for (int i = 0; i < t.nread(); i++) t.rdata[8*i +: 8] = 8'hFF;
    if (t.use_pec) t.rpec = 8'hFF;
  end
end
""",
    checks="""
// every byte the device returns with PEC must carry a correct PEC
if (t.is_read() && t.use_pec && t.acks[2]) begin
  bit [7:0] c = 0;
  c = crc8(c, {t.addr, 1'b0}); c = crc8(c, t.cmd); c = crc8(c, {t.addr, 1'b1});
  for (int i = 0; i < t.nread(); i++) c = crc8(c, t.rdata[8*i +: 8]);
  if (t.rpec != c) fail(t, $sformatf("read PEC 0x%02h, expected 0x%02h", t.rpec, c));
end
if (t.acks[0] && t.stretch == 0) fail(t, "device ACKed its address but never stretched SCL");
""",
    coverage="""
cp_kind : coverpoint tr.kind;
cp_cmd  : coverpoint tr.cmd { bins op = {8'h01}; bins clr = {8'h03}; bins vcmd = {8'h21};
                              bins sb = {8'h78}; bins cml = {8'h7E}; bins rv = {8'h8B};
                              bins rev = {8'h98}; bins bad = {8'h55, 8'hD0}; }
cp_pec  : coverpoint {tr.use_pec, tr.bad_pec} { bins none = {2'b00}; bins good = {2'b10}; bins bad = {2'b11}; }
cp_addr : coverpoint tr.acks[0] { bins nack = {0}; bins ack = {1}; }
x_kind_pec : cross cp_kind, cp_pec { ignore_bins rd_bad = binsof(cp_kind) intersect {READ_BYTE, READ_WORD} && binsof(cp_pec.bad); }
""",
    directed="""
// revision, defaults, then VOUT write / read back with and without PEC
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h98; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h01; t.use_pec = 1; send(t);
t = item(); t.kind = WRITE_WORD; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h21; t.wdata = 16'h0CE4; send(t);
t = item(); t.kind = READ_WORD;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h8B; t.use_pec = 1; send(t);
t = item(); t.kind = WRITE_WORD; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h21; t.wdata = 16'h1A2B; t.use_pec = 1; send(t);
t = item(); t.kind = READ_WORD;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h21; send(t);
// bad PEC: write discarded, CML[5] set, visible in STATUS_BYTE and STATUS_CML
t = item(); t.kind = WRITE_WORD; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h21; t.wdata = 16'hFFFF; t.use_pec = 1; t.bad_pec = 1; send(t);
t = item(); t.kind = READ_WORD;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h8B; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h78; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h7E; t.use_pec = 1; send(t);
// unsupported command (CML[7]), data to a read-only command (CML[6])
t = item(); t.kind = WRITE_BYTE; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h55; t.wdata = 16'h12; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'hD0; send(t);
t = item(); t.kind = WRITE_BYTE; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h78; t.wdata = 16'h01; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h7E; send(t);
// CLEAR_FAULTS with a bad PEC is ignored, with a good PEC clears STATUS_CML
t = item(); t.kind = SEND_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h03; t.use_pec = 1; t.bad_pec = 1; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h7E; send(t);
t = item(); t.kind = SEND_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h03; t.use_pec = 1; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h78; t.use_pec = 1; send(t);
// another address: nothing ACKed, reads float high
t = item(); t.kind = WRITE_BYTE; t.addr = 7'h10; t.cmd = 8'h01; t.wdata = 16'h00; send(t);
t = item(); t.kind = READ_WORD;  t.addr = 7'h10; t.cmd = 8'h21; send(t);
t = item(); t.kind = WRITE_BYTE; t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h01; t.wdata = 16'h40; t.use_pec = 1; send(t);
t = item(); t.kind = READ_BYTE;  t.addr = SMBUS_DEV_ADDR; t.cmd = 8'h01; send(t);
""",
    drain_ns=2000,
    model="""
module smbus_model (
  input  logic clk,
  input  logic rst_n,
  input  logic scl,
  input  logic sda,
  output logic scl_o,
  output logic sda_o
);
  localparam logic [6:0] ADDR = 7'h5A;

  logic       scl_p, sda_p, active, rep, drop, tx, mack, pec_ok, pre;
  logic [3:0] bitn;
  logic [7:0] sh, crc, cmd, txb, cml, operation;
  logic [15:0] vout;
  logic [7:0] wb [0:3];
  logic [7:0] rv0, rv1;
  logic [3:0] nb, nw, ntx;
  logic [2:0] stretch;

  function automatic logic [7:0] f_crc8(input logic [7:0] c, input logic [7:0] b);
    logic [7:0] x;
    x = c ^ b;
    for (int k = 0; k < 8; k++) x = x[7] ? ((x << 1) ^ 8'h07) : (x << 1);
    return x;
  endfunction

  // PMBus command table: bytes written / read (4'hF = not allowed)
  function automatic logic [3:0] f_wlen(input logic [7:0] c);
    case (c) 8'h01: f_wlen = 4'd1; 8'h03: f_wlen = 4'd0; 8'h21: f_wlen = 4'd2; default: f_wlen = 4'hF; endcase
  endfunction
  function automatic logic [3:0] f_rlen(input logic [7:0] c);
    case (c)
      8'h01, 8'h78, 8'h7E, 8'h98: f_rlen = 4'd1;
      8'h21, 8'h8B: f_rlen = 4'd2;
      default: f_rlen = 4'hF;
    endcase
  endfunction

  wire start = scl && scl_p && sda_p && !sda;
  wire stop  = scl && scl_p && !sda_p && sda;
  wire rise  = scl && !scl_p;
  wire fall  = !scl && scl_p;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      scl_p <= 1'b1; sda_p <= 1'b1; scl_o <= 1'b1; sda_o <= 1'b1;
      active <= 1'b0; rep <= 1'b0; drop <= 1'b0; tx <= 1'b0; mack <= 1'b0; pec_ok <= 1'b0; pre <= 1'b0;
      bitn <= '0; sh <= '0; crc <= '0; cmd <= '0; txb <= '0; nb <= '0; nw <= '0; ntx <= '0;
      cml <= 8'h00; operation <= 8'h80; vout <= 16'h0; stretch <= '0; rv0 <= '0; rv1 <= '0;
      for (int i = 0; i < 4; i++) wb[i] <= '0;
    end else begin
      scl_p <= scl; sda_p <= sda;
      if (stretch != 0) begin
        stretch <= stretch - 3'd1;
        if (stretch == 3'd1) scl_o <= 1'b1;
      end
      if (start) begin
        if (!active) begin
          rep <= 1'b0; drop <= 1'b0; nb <= '0; nw <= '0; crc <= '0; pec_ok <= 1'b0;
        end else
          rep <= 1'b1;
        active <= 1'b1; tx <= 1'b0; bitn <= '0; sda_o <= 1'b1;
        pre <= 1'b1;                                   // the SCL fall of the START itself
      end else if (stop) begin
        // a complete, error-free write takes effect at STOP
        if (active && !rep && !drop && nb >= 4'd2 && f_wlen(cmd) != 4'hF && nw >= f_wlen(cmd)) begin
          case (cmd)
            8'h01: operation <= wb[0];
            8'h03: cml <= 8'h00;
            8'h21: vout <= {wb[1], wb[0]};
            default: ;
          endcase
        end
        active <= 1'b0; tx <= 1'b0; sda_o <= 1'b1;
      end else if (active && rise) begin
        if (bitn < 4'd8) begin
          if (!tx) sh <= {sh[6:0], sda};
        end else if (tx)
          mack <= !sda;
      end else if (active && fall && pre) begin
        pre <= 1'b0;
      end else if (active && fall) begin
        if (bitn == 4'd7) begin
          bitn <= 4'd8;
          if (tx) sda_o <= 1'b1;                       // release for the host's ACK
          else begin : rx_byte
            logic ack;
            ack = 1'b0;
            if (drop) ack = 1'b0;
            else if (nb == 4'd0) begin                 // address, write
              ack = (sh[7:1] == ADDR) && !sh[0];
              crc <= f_crc8(8'h00, sh);
              if (!ack) drop <= 1'b1;
            end else if (!rep && nb == 4'd1) begin     // command
              ack = (f_wlen(sh) != 4'hF) || (f_rlen(sh) != 4'hF);
              cmd <= sh;
              crc <= f_crc8(crc, sh);
              if (!ack) begin cml[7] <= 1'b1; drop <= 1'b1; end
            end else if (!rep) begin                   // data / PEC
              if (f_wlen(cmd) == 4'hF || nw > f_wlen(cmd)) begin
                cml[6] <= 1'b1; drop <= 1'b1;
              end else if (nw < f_wlen(cmd)) begin
                ack = 1'b1; wb[nw[1:0]] <= sh; crc <= f_crc8(crc, sh);
              end else if (sh == crc) begin
                ack = 1'b1; pec_ok <= 1'b1;
              end else begin
                cml[5] <= 1'b1; drop <= 1'b1;
              end
              nw <= nw + 4'd1;
            end else begin                             // address after repeated START
              ack = (sh[7:1] == ADDR) && sh[0] && nb == 4'd2 && f_rlen(cmd) != 4'hF;
              if (sh[7:1] == ADDR && sh[0] && nb == 4'd2 && f_rlen(cmd) == 4'hF) cml[7] <= 1'b1;
              if (ack) begin
                crc <= f_crc8(crc, sh);
                case (cmd)
                  8'h01: begin rv0 <= operation; rv1 <= 8'h00; end
                  8'h21, 8'h8B: begin rv0 <= vout[7:0]; rv1 <= vout[15:8]; end
                  8'h78: begin rv0 <= {6'h0, cml != 8'h00, 1'b0}; rv1 <= 8'h00; end
                  8'h7E: begin rv0 <= cml; rv1 <= 8'h00; end
                  default: begin rv0 <= 8'h33; rv1 <= 8'h00; end
                endcase
              end else
                drop <= 1'b1;
            end
            nb <= nb + 4'd1;
            sda_o <= !ack;
          end
        end else if (bitn == 4'd8) begin              // end of the ACK bit
          bitn <= '0;
          if (!tx) begin
            sda_o <= 1'b1;
            if (sda_o == 1'b0 && (nb == 4'd1 || (rep && nb == 4'd3))) begin
              // stretch SCL after an address ACK
              scl_o <= 1'b0; stretch <= 3'd6;
            end
            if (rep && nb == 4'd3 && !drop) begin       // start sending read data
              tx <= 1'b1; ntx <= 4'd1;
              txb <= rv0; sda_o <= rv0[7];
              crc <= f_crc8(crc, rv0);
            end
          end else if (mack) begin                     // host wants another byte
            logic [7:0] nxt;
            nxt = (ntx == 4'd1 && f_rlen(cmd) == 4'd2) ? rv1
                : (ntx == f_rlen(cmd)) ? crc : 8'hFF;
            if (ntx < f_rlen(cmd)) crc <= f_crc8(crc, nxt);
            ntx <= ntx + 4'd1;
            txb <= nxt; sda_o <= nxt[7];
          end else begin
            tx <= 1'b0; drop <= 1'b1; sda_o <= 1'b1;   // host NACK: done until STOP
          end
        end else begin
          bitn <= bitn + 4'd1;
          if (tx) sda_o <= txb[3'd6 - bitn[2:0]];
        end
      end
    end
  end
endmodule
""",
    sva="""
// device outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({scl_o, sda_o}))
  else $error("SMBus: X on device outputs");
// the device changes SDA only while SCL is low (a change while SCL is high
// would be a START or STOP)
assert property (@(posedge clk) disable iff (!rst_n) scl && $past(scl) |-> $stable(sda_o))
  else $error("SMBus: device changed SDA while SCL was high");
// clock stretching is bounded
assert property (@(posedge clk) disable iff (!rst_n) $fell(scl_o) |-> ##[1:8] scl_o)
  else $error("SMBus: device held SCL low too long");
// the device never pulls SCL low while the host holds it high in the middle of a bit
cover property (@(posedge clk) disable iff (!rst_n) !scl_o);
cover property (@(posedge clk) disable iff (!rst_n) scl && $fell(sda));
cover property (@(posedge clk) disable iff (!rst_n) scl && $rose(sda));
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic scl_m = 1, sda_m = 1;
wire  scl_o, sda_o;
wire  scl = scl_m & scl_o;
wire  sda = sda_m & sda_o;

always #5 clk = ~clk;

smbus_model u_dut (.clk(clk), .rst_n(rst_n), .scl(scl), .sda(sda), .scl_o(scl_o), .sda_o(sda_o));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [7:0] crc8(input logic [7:0] c, input logic [7:0] b);
  c = c ^ b;
  for (int k = 0; k < 8; k++) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
  return c;
endfunction

task automatic clks(input int n); repeat (n) @(posedge clk); #1; endtask
task automatic scl_up; scl_m = 1; clks(1); while (!scl) clks(1); endtask
task automatic start_c; sda_m = 1; clks(2); scl_up(); clks(4); sda_m = 0; clks(4); scl_m = 0; clks(2); endtask
task automatic stop_c; sda_m = 0; clks(2); scl_up(); clks(4); sda_m = 1; clks(8); endtask
task automatic bitx(input logic o, output logic i);
  sda_m = o; clks(2); scl_up(); clks(2); i = sda; clks(2); scl_m = 0; clks(2);
endtask
task automatic wbyte(input logic [7:0] b, output logic ack);
  logic i;
  for (int k = 7; k >= 0; k--) bitx(b[k], i);
  bitx(1'b1, i); ack = !i;
endtask
task automatic rbyte(input logic ack, output logic [7:0] b);
  logic i;
  for (int k = 7; k >= 0; k--) begin bitx(1'b1, i); b[k] = i; end
  bitx(!ack, i);
  if (!ack) chk(i === 1'b1, "device releases SDA for the master NACK");
endtask

// clock stretches by the device (falling edges of scl_o)
int nstr = 0;
logic scl_o_p = 1'b1;
always @(posedge clk) begin scl_o_p <= scl_o; if (scl_o_p && !scl_o) nstr++; end

// read one byte of command c, with PEC
task automatic rd1(input logic [7:0] c, output logic [7:0] d, output logic pec_ok);
  logic a; logic [7:0] p, x;
  start_c(); wbyte(8'hB4, a); wbyte(c, a);
  start_c(); wbyte(8'hB5, a);
  rbyte(1, d); rbyte(0, p); stop_c();
  x = crc8(crc8(crc8(crc8(0, 8'hB4), c), 8'hB5), d);
  pec_ok = (p == x);
endtask

initial begin
  logic a, ok; logic [7:0] d, d1;
  clks(3);
  chk(scl_o === 1'b1 && sda_o === 1'b1, "bus released in reset");
  rst_n = 1; clks(4);

  // PMBUS_REVISION and OPERATION default, PEC checked
  rd1(8'h98, d, ok); chk(d === 8'h33 && ok, "PMBUS_REVISION = 0x33 with a good PEC");
  rd1(8'h01, d, ok); chk(d === 8'h80 && ok, "OPERATION resets to 0x80");

  // write VOUT_COMMAND with PEC, read it back through READ_VOUT
  start_c(); wbyte(8'hB4, a); chk(a, "address ACK");
  wbyte(8'h21, a); chk(a, "VOUT_COMMAND ACK");
  wbyte(8'hE4, a); wbyte(8'h0C, a);
  wbyte(crc8(crc8(crc8(crc8(0, 8'hB4), 8'h21), 8'hE4), 8'h0C), a); chk(a, "good PEC ACKed");
  stop_c();
  start_c(); wbyte(8'hB4, a); wbyte(8'h8B, a); start_c(); wbyte(8'hB5, a);
  rbyte(1, d); rbyte(0, d1); stop_c();
  chk({d1, d} === 16'h0CE4, "READ_VOUT returns the commanded value");

  // bad PEC: NACK, write discarded, STATUS_CML[5]
  start_c(); wbyte(8'hB4, a); wbyte(8'h21, a); wbyte(8'h00, a); wbyte(8'h00, a);
  wbyte(8'h5A, a); chk(!a, "bad PEC NACKed"); stop_c();
  rd1(8'h7E, d, ok); chk(d === 8'h20, "STATUS_CML[5] PEC failed");
  rd1(8'h78, d, ok); chk(d === 8'h02, "STATUS_BYTE CML bit");
  start_c(); wbyte(8'hB4, a); wbyte(8'h21, a); start_c(); wbyte(8'hB5, a);
  rbyte(1, d); rbyte(0, d1); stop_c();
  chk({d1, d} === 16'h0CE4, "discarded write left VOUT_COMMAND unchanged");

  // unsupported command, wrong address, CLEAR_FAULTS
  start_c(); wbyte(8'hB4, a); wbyte(8'h55, a); chk(!a, "unsupported command NACKed"); stop_c();
  rd1(8'h7E, d, ok); chk(d === 8'hA0, "STATUS_CML[7] invalid command");
  start_c(); wbyte(8'h20, a); chk(!a, "other address NACKed"); stop_c();
  start_c(); wbyte(8'hB4, a); wbyte(8'h03, a); stop_c();
  rd1(8'h7E, d, ok); chk(d === 8'h00, "CLEAR_FAULTS clears STATUS_CML");

  // clock stretching only after an ACKed address: once per write, twice per read
  begin : stretch
    int n0;
    n0 = nstr;
    start_c(); wbyte(8'hB4, a); wbyte(8'h01, a); wbyte(8'h80, a); stop_c();
    chk(nstr - n0 == 1, "one stretch in a write (after the address)");
    n0 = nstr;
    rd1(8'h98, d, ok);
    chk(nstr - n0 == 2, "two stretches in a read (after each address)");
    n0 = nstr;
    start_c(); wbyte(8'h20, a); stop_c();
    chk(nstr - n0 == 0, "no stretch after a NACKed address");
  end
  // too many data bytes: NACK and STATUS_CML[6]
  start_c(); wbyte(8'hB4, a); wbyte(8'h01, a); wbyte(8'h40, a);
  wbyte(crc8(crc8(crc8(0, 8'hB4), 8'h01), 8'h40), a); chk(a, "PEC after one data byte ACKed");
  wbyte(8'h12, a); chk(!a, "extra byte after the PEC NACKed"); stop_c();
  rd1(8'h7E, d, ok); chk(d === 8'h40, "STATUS_CML[6] invalid data");
  rd1(8'h01, d, ok); chk(d === 8'h80, "write with extra bytes discarded");
  start_c(); wbyte(8'hB4, a); wbyte(8'h03, a); stop_c();
  // read of a write-only command and read with another address: NACK
  start_c(); wbyte(8'hB4, a); wbyte(8'h03, a); start_c(); wbyte(8'hB5, a); stop_c();
  chk(!a, "read of a send-byte command NACKed");
  rd1(8'h7E, d, ok); chk(d === 8'h80, "STATUS_CML[7] for the read of a write-only command");
  start_c(); wbyte(8'hB4, a); wbyte(8'h03, a); stop_c();
  start_c(); wbyte(8'hB4, a); wbyte(8'h98, a); start_c(); wbyte(8'h21, a); stop_c();
  chk(!a, "repeated start to another address NACKed");
  start_c(); wbyte(8'hB4, a); wbyte(8'h98, a); start_c(); wbyte(8'hB4, a); stop_c();
  chk(!a, "repeated start with the write bit NACKed");
  rd1(8'h7E, d, ok); chk(d === 8'h00, "no fault from a foreign or write repeated start");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
