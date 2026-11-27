# IEEE 802.3 MDIO station management, Clause 22 and Clause 45 (MDC = clk / 2).
#
# tb/top_tb.sv mdio_model is a PHY at port / PHY address 5. MDIO is sampled on
# MDC rising edges by both sides; the PHY changes MDIO one clock after the rise.
#   * every frame needs a preamble of 32 or more ones; a frame to another
#     address, an unimplemented MMD or an undefined OP gets no response (the
#     pulled-up bus reads all ones and the turnaround has no zero), and its
#     turnaround and data bits are let pass, so they never count as preamble.
#   * Clause 22 (ST 01, OP 10 read / 01 write): 32 registers.
#       0 BMCR (reset 0x1140; writing bit 15 resets registers 0 and 4..31 and
#         self-clears), 1 BMSR (the phy_status pins), 2/3 PHY identifier
#         (0x0141 / 0x0DD1, read-only), 13 MMD access control and 14 MMD
#         access address / data (22.2.4.3.11: function 00 address, 01 data,
#         10 data with post-increment on reads and writes, 11 data with
#         post-increment on writes only), others read / write.
#   * Clause 45 (ST 00): MMDs 1 (PMA/PMD), 3 (PCS) and 7 (AN), each with an
#     address register and 64 registers; OP 00 address, 01 write, 11 read,
#     10 post-read-increment-address. Registers 2/3 (device identifier,
#     0x0141 / 0x0DD0 + DEVAD) and 5 (devices in package, 0x008A) are
#     read-only; addresses 64 and up read 0 and ignore writes.
#   * mdio_status shows BMCR.
SPEC = dict(
    vip="MDIO-UVM-VIP", p="mdio", P="MDIO", dir="mdio", family="Networking",
    desc="IEEE 802.3 MDIO station management VIP: Clause 22 and Clause 45 frames (address, write, read, "
         "post-read-increment-address), MMD indirect access through registers 13/14, turnaround checking.",
    about="""
The DUT model is a PHY with a Clause 22 register set (BMCR reset, read-only status and
identifier registers, the MMD access registers 13 and 14) and three Clause 45 MMDs
with their own address registers. The scoreboard holds the same register model and
predicts every read, including post-increment addressing through both Clause 45
OP 10 and Clause 22 register 14. The SVA checks that MDIO never changes on an MDC
rising edge and that the PHY's mirror output is never unknown.""",
    timeout=400,
    interface="""interface mdio_if (input logic clk);
  logic rst_n;

  logic mdc;
  logic mdio_o;          // station management entity output
  logic mdio_oe;
  tri1  mdio;            // shared, pulled up when nobody drives it
  logic [15:0] phy_status;
  logic [15:0] mdio_status;

  assign mdio = mdio_oe ? mdio_o : 1'bz;

  modport DUT (input clk, rst_n, mdc, phy_status, output mdio_status, inout mdio);
  modport DRV (input clk, rst_n, mdio_status, mdio, output mdc, mdio_o, mdio_oe, phy_status);
  modport MON (input clk, rst_n, mdc, mdio, mdio_o, mdio_oe, phy_status, mdio_status);

  clocking drv_cb @(posedge clk);
    input rst_n, mdio, mdio_status;
    inout mdc, mdio_o, mdio_oe, phy_status;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, mdc, mdio, mdio_o, mdio_oe, phy_status, mdio_status;
  endclocking
endinterface
""",
    ports=[
        ("in", "logic", "mdc"), ("inout", "logic", "mdio"),
        ("in", "logic [15:0]", "phy_status"), ("out", "logic [15:0]", "mdio_status"),
    ],
    cfg="bit [4:0] phy_addr = 5'h05;   // mdio_model port / PHY address",
    defs="""
// Clause 45 MMDs of the PHY
function automatic bit mdio_mmd_ok(bit [4:0] d); return d == 5'd1 || d == 5'd3 || d == 5'd7; endfunction
function automatic int mdio_mmd_idx(bit [4:0] d); return (d == 5'd1) ? 0 : (d == 5'd3) ? 1 : 2; endfunction
""",
    fields=[
        ("bit", "c45", "req", "rand"),          # ST 00 (Clause 45) instead of 01
        ("bit [1:0]", "op", "req", "rand"),     # OP field as sent
        ("bit [4:0]", "phyad", "req", "rand"),  # PHYAD / PRTAD
        ("bit [4:0]", "regad", "req", "rand"),  # REGAD / DEVAD
        ("bit [15:0]", "wdata", "req", "rand"), # write data / Clause 45 address
        ("bit [15:0]", "phy_status", "req", "rand"),
        ("bit [15:0]", "rdata", "rsp"),
        ("bit", "ta_ack", "rsp"),               # the PHY drove the second turnaround bit low
        ("bit [15:0]", "mdio_status", "rsp"),
        ("bit [1:0]", "ta", "info"),            # turnaround bits as seen on the bus
        ("bit [5:0]", "pre", "info", "rand"),   # preamble length
    ],
    constraints="""
constraint c_pre  { pre dist { 6'd32 := 8, [6'd33:6'd40] :/ 1, 6'd31 := 1 }; }
constraint c_phy  { phyad dist { 5'h05 := 8, [0:4] :/ 1, [6:31] :/ 1 }; }
constraint c_c22  { !c45 -> op dist { 2'b10 := 5, 2'b01 := 4, 2'b00 := 1 };
                    !c45 -> regad dist { [0:3] :/ 4, [13:14] :/ 6, [4:12] :/ 2, [15:31] :/ 2 }; }
constraint c_c45  { c45 -> regad dist { 5'd1 := 3, 5'd3 := 3, 5'd7 := 3, [0:31] :/ 1 }; }
constraint c_wd   { (c45 && op == 2'b00) -> wdata[15:6] dist { 0 := 9, [1:1023] :/ 1 };
                    (!c45 && regad == 0) -> wdata[15] dist { 0 := 9, 1 := 1 };
                    (!c45 && regad == 13) -> wdata[4:0] inside {1, 3, 7, 2}; }
""",
    drv_members="bit sampled;   // MDIO at the last MDC rising edge",
    drv_desc="preamble, ST, OP, PHYAD/PRTAD, REGAD/DEVAD, TA, DATA; MDIO set while MDC is low, released on read-type frames",
    drv_idle="vif.drv_cb.mdc <= 1'b0; vif.drv_cb.mdio_oe <= 1'b0; vif.drv_cb.mdio_o <= 1'b1; vif.drv_cb.phy_status <= '0;",
    drv_item="""
begin
  // read-type frames: Clause 22 OP 10, Clause 45 OP 11 and OP 10
  bit rd = t.c45 ? t.op[1] : (t.op == 2'b10);
  @(vif.drv_cb);
  vif.drv_cb.phy_status <= t.phy_status;
  repeat (t.pre) mdc_bit(1'b1, 1'b1);            // preamble
  mdc_bit(1'b1, 1'b0); mdc_bit(1'b1, !t.c45);    // ST: 01 Clause 22, 00 Clause 45
  mdc_bit(1'b1, t.op[1]); mdc_bit(1'b1, t.op[0]);
  for (int i = 4; i >= 0; i--) mdc_bit(1'b1, t.phyad[i]);
  for (int i = 4; i >= 0; i--) mdc_bit(1'b1, t.regad[i]);
  if (rd) begin
    mdc_bit(1'b0, 1'b1);                         // TA: Z
    mdc_bit(1'b0, 1'b1); t.ta_ack = !sampled;    // TA: 0 from the PHY
    for (int i = 15; i >= 0; i--) begin mdc_bit(1'b0, 1'b1); t.rdata[i] = sampled; end
    t.wdata = 0;
  end else begin
    mdc_bit(1'b1, 1'b1); mdc_bit(1'b1, 1'b0);    // TA = 10
    for (int i = 15; i >= 0; i--) mdc_bit(1'b1, t.wdata[i]);
    t.ta_ack = 0;
    t.rdata = 0;
  end
  vif.drv_cb.mdio_oe <= 1'b0;
  repeat (2) @(vif.drv_cb);
  t.mdio_status = vif.drv_cb.mdio_status;
end
""",
    drv_tasks="""
// one MDC period: MDC low with MDIO set up, then MDC high (the PHY samples
// on the rising edge, the station samples a PHY-driven bit there too)
task mdc_bit(bit drive, bit b);
  vif.drv_cb.mdc <= 1'b0;
  vif.drv_cb.mdio_oe <= drive;
  vif.drv_cb.mdio_o <= b;
  @(vif.drv_cb);
  vif.drv_cb.mdc <= 1'b1;
  @(vif.drv_cb);
  sampled = vif.drv_cb.mdio;
endtask
""",
    mon_desc="decodes Clause 22 and Clause 45 frames from MDIO sampled on MDC rising edges",
    mon_run="""
bit [63:0] sh = 0;
int unsigned ones = 0, n = 0, npre = 0;
bit mdc_d = 0, in_frame = 0;
mdio_transaction t;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.mdc && !mdc_d) begin           // MDC rising edge: one bit
    bit b = (vif.mon_cb.mdio !== 1'b0);
    if (!in_frame) begin
      // the first zero after a run of ones starts ST; 31 ones are a short preamble
      if (ones >= 31 && b == 1'b0) begin in_frame = 1; n = 1; sh = 0; npre = ones; end
      ones = b ? ones + 1 : 0;
    end else begin
      sh = {sh[62:0], b};
      n++;
      if (n == 32) begin                        // ST OP PHYAD REGAD TA DATA
        t = mdio_transaction::type_id::create("t");
        t.c45   = (sh[30] == 1'b0);
        t.op    = sh[29:28];
        t.phyad = sh[27:23];
        t.regad = sh[22:18];
        t.ta    = sh[17:16];
        t.pre   = (npre > 63) ? 63 : npre;
        if (t.c45 ? t.op[1] : (t.op == 2'b10)) begin
          t.ta_ack = (sh[16] == 1'b0); t.rdata = sh[15:0];
        end else t.wdata = sh[15:0];
        t.phy_status = vif.mon_cb.phy_status;
        in_frame = 0; ones = 0;
        repeat (3) @(vif.mon_cb);
        t.mdio_status = vif.mon_cb.mdio_status;
        publish(t);
      end
    end
  end
  mdc_d = vif.mon_cb.mdc;
end
""",
    sb_members="""bit [15:0] c22 [32];               // Clause 22 read / write registers (0 = BMCR, 13 = MMD control)
bit [15:0] mmd [3][64];
bit [15:0] maddr [3];
bit        init_done;
function void phy_reset22();
  c22[0] = 16'h1140;
  for (int i = 4; i < 32; i++) c22[i] = 0;
endfunction
function bit [15:0] mmd_rd(bit [4:0] d, bit [15:0] a);
  if (a == 2) return 16'h0141;
  if (a == 3) return 16'h0DD0 + d;
  if (a == 5) return 16'h008A;
  if (a >= 64) return 0;
  return mmd[mdio_mmd_idx(d)][a];
endfunction
function void mmd_wr(bit [4:0] d, bit [15:0] a, bit [15:0] v);
  if (a == 2 || a == 3 || a == 5 || a >= 64) return;
  mmd[mdio_mmd_idx(d)][a] = v;
endfunction""",
    predict="""
begin
  bit rd = t.c45 ? t.op[1] : (t.op == 2'b10);
  bit mine = (t.pre >= 32) && t.phyad == cfg.phy_addr &&
             (t.c45 ? mdio_mmd_ok(t.regad) : (t.op == 2'b10 || t.op == 2'b01));
  bit [15:0] v = 16'hFFFF;
  if (!init_done) begin phy_reset22(); init_done = 1; end
  if (mine && t.c45) begin
    int k = mdio_mmd_idx(t.regad);
    case (t.op)
      2'b00: maddr[k] = t.wdata;
      2'b01: mmd_wr(t.regad, maddr[k], t.wdata);
      2'b11: v = mmd_rd(t.regad, maddr[k]);
      2'b10: begin v = mmd_rd(t.regad, maddr[k]); maddr[k]++; end
    endcase
  end else if (mine) begin
    bit [1:0] f = c22[13][15:14];
    bit [4:0] d = c22[13][4:0];
    if (rd) begin
      case (t.regad)
        0: v = c22[0];
        1: v = t.phy_status;
        2: v = 16'h0141;
        3: v = 16'h0DD1;
        14: if (!mdio_mmd_ok(d)) v = 0;
            else if (f == 2'b00) v = maddr[mdio_mmd_idx(d)];
            else begin v = mmd_rd(d, maddr[mdio_mmd_idx(d)]); if (f == 2'b10) maddr[mdio_mmd_idx(d)]++; end
        default: v = c22[t.regad];
      endcase
    end else begin
      case (t.regad)
        0: if (t.wdata[15]) phy_reset22(); else c22[0] = t.wdata;
        1, 2, 3: ;
        14: if (mdio_mmd_ok(d)) begin
              if (f == 2'b00) maddr[mdio_mmd_idx(d)] = t.wdata;
              else begin mmd_wr(d, maddr[mdio_mmd_idx(d)], t.wdata); if (f != 2'b01) maddr[mdio_mmd_idx(d)]++; end
            end
        default: c22[t.regad] = t.wdata;
      endcase
    end
  end
  t.ta_ack = rd && mine;
  t.rdata  = rd ? v : 16'h0;
  t.mdio_status = c22[0];
end
""",
    checks="""
if (!(t.c45 ? t.op[1] : (t.op == 2'b10)) && t.ta != 2'b10) fail(t, "write-type frame turnaround is not 10");
if (t.ta_ack && t.ta != 2'b10) fail(t, "read turnaround is not Z, 0");
""",
    coverage="""
cp_st    : coverpoint tr.c45 { bins c22 = {0}; bins c45 = {1}; }
cp_op22  : coverpoint tr.op iff (!tr.c45 && tr.ta_ack | (tr.op == 2'b01)) { bins write = {2'b01}; bins read = {2'b10}; }
cp_op45  : coverpoint tr.op iff (tr.c45) { bins addr = {2'b00}; bins write = {2'b01}; bins read = {2'b11}; bins pria = {2'b10}; }
cp_reg   : coverpoint tr.regad iff (!tr.c45) { bins bmcr = {0}; bins bmsr = {1}; bins id = {[2:3]}; bins mmdctl = {13}; bins mmdad = {14}; bins other = default; }
cp_dev   : coverpoint tr.regad iff (tr.c45) { bins pma = {1}; bins pcs = {3}; bins an = {7}; bins none = default; }
cp_fn    : coverpoint tr.wdata[15:14] iff (!tr.c45 && tr.op == 2'b01 && tr.regad == 13) { bins addr = {0}; bins data = {1}; bins inc = {2}; bins incw = {3}; }
cp_ack   : coverpoint tr.ta_ack iff (tr.c45 ? tr.op[1] : (tr.op == 2'b10)) { bins none = {0}; bins ack = {1}; }
cp_pre   : coverpoint tr.pre { bins short_ = {31}; bins min = {32}; bins long_ = {[33:63]}; }
cp_rst   : coverpoint tr.wdata[15] iff (!tr.c45 && tr.op == 2'b01 && tr.regad == 0) { bins rst = {1}; bins norm = {0}; }
x_op_dev : cross cp_op45, cp_dev;
""",
    directed="""
// Clause 22: BMCR, BMSR, identifiers, read-only writes, reset
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 0; t.pre = 32; t.phy_status = 16'h7849; send(t);
t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 0; t.pre = 32; t.wdata = 16'h0100; send(t);
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 1; t.pre = 32; t.phy_status = 16'h796D; send(t);
for (int r = 2; r < 4; r++) begin
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = r; t.pre = 32; t.wdata = 16'hFFFF; send(t);
  t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = r; t.pre = 32; send(t);
end
t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 9; t.pre = 32; t.wdata = 16'h0300; send(t);
t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 0; t.pre = 32; t.wdata = 16'h8000; send(t);
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 9; t.pre = 32; send(t);
// Clause 45 on every MMD: address, write, read, post-read-increment
for (int i = 0; i < 3; i++) begin
  bit [4:0] dv;
  dv = (i == 0) ? 5'd1 : (i == 1) ? 5'd3 : 5'd7;
  t = item(); t.c45 = 1; t.op = 2'b00; t.phyad = 5; t.regad = dv; t.pre = 32; t.wdata = 16'd8; send(t);
  for (int k = 0; k < 3; k++) begin t = item(); t.c45 = 1; t.op = 2'b01; t.phyad = 5; t.regad = dv; t.pre = 32; t.wdata = 16'hA000 + 16 * i + k; send(t); end
  t = item(); t.c45 = 1; t.op = 2'b10; t.phyad = 5; t.regad = dv; t.pre = 32; send(t);
  t = item(); t.c45 = 1; t.op = 2'b10; t.phyad = 5; t.regad = dv; t.pre = 32; send(t);
  t = item(); t.c45 = 1; t.op = 2'b11; t.phyad = 5; t.regad = dv; t.pre = 32; send(t);
  t = item(); t.c45 = 1; t.op = 2'b00; t.phyad = 5; t.regad = dv; t.pre = 32; t.wdata = 16'd3; send(t);
  t = item(); t.c45 = 1; t.op = 2'b11; t.phyad = 5; t.regad = dv; t.pre = 32; send(t);
end
// Clause 22 indirect MMD access, every function
for (int f = 0; f < 4; f++) begin
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 13; t.pre = 32; t.wdata = 16'h0003; send(t);
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 14; t.pre = 32; t.wdata = 16'd20 + f; send(t);
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 13; t.pre = 32; t.wdata = {f[1:0], 14'h0003}; send(t);
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 14; t.pre = 32; t.wdata = 16'hBEE0 + f; send(t);
  t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 14; t.pre = 32; send(t);
  t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 14; t.pre = 32; send(t);
end
// indirect access to the identifiers and past the last register
t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 13; t.pre = 32; t.wdata = 16'h4001; send(t);
for (int a = 2; a < 66; a += 62) begin
  t = item(); t.c45 = 1; t.op = 2'b00; t.phyad = 5; t.regad = 1; t.pre = 32; t.wdata = a; send(t);
  t = item(); t.c45 = 0; t.op = 2'b01; t.phyad = 5; t.regad = 14; t.pre = 32; t.wdata = 16'h5A5A; send(t);
  t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 14; t.pre = 32; send(t);
end
t = item(); t.c45 = 1; t.op = 2'b00; t.phyad = 5; t.regad = 1; t.pre = 32; t.wdata = 16'd3; send(t);
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 14; t.pre = 32; send(t);
// no response: other address, unimplemented MMD, undefined OP, short preamble
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 4; t.regad = 0; t.pre = 32; send(t);
t = item(); t.c45 = 1; t.op = 2'b11; t.phyad = 5; t.regad = 2; t.pre = 32; send(t);
t = item(); t.c45 = 0; t.op = 2'b00; t.phyad = 5; t.regad = 0; t.pre = 32; t.wdata = 16'h0040; send(t);
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 0; t.pre = 31; send(t);
t = item(); t.c45 = 0; t.op = 2'b10; t.phyad = 5; t.regad = 0; t.pre = 40; send(t);
""",
    drain_ns=4000,
    model="""
module mdio_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        mdc,
  inout  logic        mdio,
  input  logic [15:0] phy_status,
  output logic [15:0] mdio_status
);
  localparam logic [4:0] PHY_ADDR = 5'h05;
  localparam logic [1:0] S_IDLE = 2'd0, S_HDR = 2'd1, S_RD = 2'd2, S_WR = 2'd3;
  logic [1:0]  st;
  logic        mdc_q;
  logic [5:0]  pre_cnt;
  logic [4:0]  hcnt, fcnt;
  logic [12:0] sh;
  logic [17:0] wsh;              // write frame: TA and data
  logic        drive, dout;
  logic [15:0] sreg;
  logic [15:0] c22 [0:31];
  logic [15:0] mmd [0:191];
  logic [15:0] maddr [0:2];
  logic [1:0]  hst, hop;
  logic [4:0]  hpa, hra;
  logic        c45, mine, rdf;
  logic        skip;
  logic        shortp;           // the frame's preamble was 31 bits             // frame for someone else: let its 18 bits pass
  logic [15:0] v;
  logic [1:0]  k, kd;
  logic [1:0]  fn;
  logic [4:0]  dv;
  wire         bit_in = (mdio !== 1'b0);         // released line reads 1
  wire         mdc_rise = mdc && !mdc_q;
  wire  [13:0] hdr = {sh, bit_in};

  function automatic logic ok(input logic [4:0] d);
    ok = (d == 5'd1) || (d == 5'd3) || (d == 5'd7);
  endfunction
  function automatic logic [1:0] idx(input logic [4:0] d);
    idx = (d == 5'd1) ? 2'd0 : (d == 5'd3) ? 2'd1 : 2'd2;
  endfunction
  // registers 2, 3 and 5 always read their constants, so only the
  // addresses past the 64 implemented registers need guarding on writes
  function automatic logic ro(input logic [15:0] a);
    ro = (a >= 16'd64);
  endfunction

  assign mdio_status = c22[0];
  assign fn = c22[13][15:14];
  assign dv = c22[13][4:0];
  assign kd = idx(dv);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= S_IDLE; mdc_q <= 1'b0; pre_cnt <= '0; hcnt <= '0; fcnt <= '0; sh <= '0; wsh <= '0;
      drive <= 1'b0; dout <= 1'b1; sreg <= '0; skip <= 1'b0; shortp <= 1'b0;
      hst <= '0; hop <= '0; hpa <= '0; hra <= '0;
      c22[0] <= 16'h1140;
      for (int i = 1; i < 32; i++) c22[i] <= 16'h0;
      for (int i = 0; i < 192; i++) mmd[i] <= 16'h0;
      for (int i = 0; i < 3; i++) maddr[i] <= 16'h0;
    end else begin
      mdc_q <= mdc;
      case (st)
        S_IDLE: if (mdc_rise) begin
          if (bit_in) pre_cnt <= (pre_cnt == 6'd63) ? pre_cnt : pre_cnt + 1'b1;
          else if (pre_cnt >= 6'd31) begin       // first ST bit after the preamble
            // a 31-bit preamble is one bit short: the frame is let pass unanswered
            st <= S_HDR; sh <= '0; hcnt <= 5'd1; shortp <= (pre_cnt == 6'd31);
          end else pre_cnt <= '0;
        end
        S_HDR: if (mdc_rise) begin
          sh   <= hdr[12:0];
          hcnt <= hcnt + 1'b1;
          if (hcnt == 5'd13) begin               // ST OP PHYAD REGAD complete
            pre_cnt <= '0;
            c45  = (hdr[13:12] == 2'b00);
            rdf  = c45 ? hdr[11] : (hdr[11:10] == 2'b10);
            mine = !shortp && hdr[9:5] == PHY_ADDR &&
                   (c45 ? ok(hdr[4:0]) : (hdr[13:12] == 2'b01 && (hdr[11:10] == 2'b10 || hdr[11:10] == 2'b01)));
            hst <= hdr[13:12]; hop <= hdr[11:10]; hpa <= hdr[9:5]; hra <= hdr[4:0];
            skip <= !mine;
            if (!mine) begin st <= S_WR; fcnt <= '0; end
            else if (rdf) begin
              // read data and the read's side effects (post-increment)
              k = idx(hdr[4:0]);
              v = 16'h0;
              if (c45) begin
                v = (maddr[k] == 16'd2) ? 16'h0141 : (maddr[k] == 16'd3) ? 16'h0DD0 + {11'h0, hdr[4:0]} :
                    (maddr[k] == 16'd5) ? 16'h008A : (maddr[k] >= 16'd64) ? 16'h0 : mmd[64 * k + maddr[k][5:0]];
                if (hdr[11:10] == 2'b10) maddr[k] <= maddr[k] + 16'd1;
              end else case (hdr[4:0])
                5'd1:  v = phy_status;
                5'd2:  v = 16'h0141;
                5'd3:  v = 16'h0DD1;
                5'd14: if (ok(dv)) begin
                         if (fn == 2'b00) v = maddr[kd];
                         else begin
                           v = (maddr[kd] == 16'd2) ? 16'h0141 : (maddr[kd] == 16'd3) ? 16'h0DD0 + {11'h0, dv} :
                               (maddr[kd] == 16'd5) ? 16'h008A : (maddr[kd] >= 16'd64) ? 16'h0 : mmd[64 * kd + maddr[kd][5:0]];
                           if (fn == 2'b10) maddr[kd] <= maddr[kd] + 16'd1;
                         end
                       end
                default: v = c22[hdr[4:0]];
              endcase
              sreg <= v; st <= S_RD; fcnt <= '0;
            end else begin
              st <= S_WR; fcnt <= '0;
            end
          end
        end
        S_RD: if (mdc_rise) begin
          // fcnt 0 = rise of the first TA bit (left Z), 1..16 = rises of
          // TA bit 2 and data bits 15..1, 17 = rise of data bit 0
          fcnt <= fcnt + 1'b1;
          if (fcnt == 5'd0) begin drive <= 1'b1; dout <= 1'b0; end
          else if (fcnt <= 5'd16) dout <= sreg[5'd16 - fcnt];
          else begin drive <= 1'b0; st <= S_IDLE; end
        end
        S_WR: if (mdc_rise) begin
          wsh  <= {wsh[16:0], bit_in};
          fcnt <= fcnt + 1'b1;
          if (fcnt == 5'd17) begin               // TA and the 16 data bits are in
            v = {wsh[14:0], bit_in};
            st <= S_IDLE;
            if (skip) ;
            else if (hst == 2'b00) begin
              k = idx(hra);
              if (hop == 2'b00) maddr[k] <= v;
              else if (!ro(maddr[k])) mmd[64 * k + maddr[k][5:0]] <= v;
            end else case (hra)
              5'd0: if (v[15]) begin
                      c22[0] <= 16'h1140;
                      for (int i = 4; i < 32; i++) c22[i] <= 16'h0;
                    end else c22[0] <= v;
              5'd1, 5'd2, 5'd3: ;
              5'd14: if (ok(dv)) begin
                       if (fn == 2'b00) maddr[kd] <= v;
                       else begin
                         if (!ro(maddr[kd])) mmd[64 * kd + maddr[kd][5:0]] <= v;
                         if (fn != 2'b01) maddr[kd] <= maddr[kd] + 16'd1;
                       end
                     end
              default: c22[hra] <= v;
            endcase
          end
        end
      endcase
    end
  end
  assign mdio = drive ? dout : 1'bz;
endmodule
""",
    sva="""
logic mdc_q;
always @(posedge clk or negedge rst_n) if (!rst_n) mdc_q <= 1'b0; else mdc_q <= mdc;
// MDIO is set up before the MDC rising edge (station: while MDC is low; PHY: one clock after the rise)
assert property (@(posedge clk) disable iff (!rst_n) mdc && !mdc_q |-> $stable(mdio))
  else $error("MDIO: MDIO changed on an MDC rising edge");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(mdio_status))
  else $error("MDIO: X on the PHY's BMCR mirror");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(mdc))
  else $error("MDIO: X on MDC");
cover property (@(posedge clk) disable iff (!rst_n) mdc && !mdc_q && mdio == 1'b0 ##2 mdc && !mdc_q && mdio == 1'b0);
cover property (@(posedge clk) disable iff (!rst_n) $changed(mdio_status));
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic mdc = 0, mdo = 1, moe = 0;
logic [15:0] phy_status = 16'h7849;
wire [15:0] mdio_status;
tri1 mdio;
assign mdio = moe ? mdo : 1'bz;

always #5 clk = ~clk;

mdio_model u_dut (.clk(clk), .rst_n(rst_n), .mdc(mdc), .mdio(mdio), .phy_status(phy_status), .mdio_status(mdio_status));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

logic smp;
// one MDC period (4 clocks), MDIO set while MDC is low, sampled at the rise
task automatic bitp(input bit drv, input bit b);
  @(negedge clk); mdc = 0; moe = drv; mdo = b;
  @(negedge clk);
  @(negedge clk); smp = (mdio !== 1'b0); mdc = 1;   // value the PHY sees at the rise
  @(negedge clk);
endtask
logic [15:0] rv; logic ack;
task automatic frame(input int pre, input bit [1:0] stc, input bit [1:0] op, input bit [4:0] pa, input bit [4:0] ra,
                     input bit [15:0] wd, input bit rd);
  for (int i = 0; i < pre; i++) bitp(1, 1);
  bitp(1, stc[1]); bitp(1, stc[0]); bitp(1, op[1]); bitp(1, op[0]);
  for (int i = 4; i >= 0; i--) bitp(1, pa[i]);
  for (int i = 4; i >= 0; i--) bitp(1, ra[i]);
  if (rd) begin
    bitp(0, 1); chk(smp == 1'b1, "first TA bit left high");
    bitp(0, 1); ack = !smp;
    for (int i = 15; i >= 0; i--) begin bitp(0, 1); rv[i] = smp; end
  end else begin
    bitp(1, 1); bitp(1, 0);
    for (int i = 15; i >= 0; i--) bitp(1, wd[i]);
    ack = 0; rv = 0;
  end
  moe = 0; repeat (6) @(negedge clk);           // idle, MDC low: no extra preamble bit
endtask
task automatic r22(input bit [4:0] r); frame(32, 2'b01, 2'b10, 5, r, 0, 1); endtask
task automatic w22(input bit [4:0] r, input bit [15:0] d); frame(32, 2'b01, 2'b01, 5, r, d, 0); endtask
task automatic a45(input bit [4:0] d, input bit [15:0] a); frame(32, 2'b00, 2'b00, 5, d, a, 0); endtask
task automatic w45(input bit [4:0] d, input bit [15:0] v); frame(32, 2'b00, 2'b01, 5, d, v, 0); endtask
task automatic r45(input bit [4:0] d); frame(32, 2'b00, 2'b11, 5, d, 0, 1); endtask
task automatic p45(input bit [4:0] d); frame(32, 2'b00, 2'b10, 5, d, 0, 1); endtask

initial begin
  repeat (3) @(posedge clk);
  chk(mdio === 1'b1 && mdio_status == 16'h1140, "released bus, BMCR 0x1140 in reset");
  moe = 1; mdo = 0; #1; chk(mdio === 1'b0, "the PHY does not drive MDIO in reset"); moe = 0;
  rst_n = 1;
  repeat (2) @(posedge clk);

  // Clause 22 registers
  r22(0); chk(ack && rv == 16'h1140, $sformatf("BMCR reset value (%h)", rv));
  phy_status = 16'h796D; r22(1); chk(ack && rv == 16'h796D, "BMSR = phy_status pins");
  r22(2); chk(ack && rv == 16'h0141, "PHY identifier 1");
  r22(3); chk(ack && rv == 16'h0DD1, "PHY identifier 2");
  w22(2, 16'hFFFF); w22(3, 16'h0); w22(1, 16'h0);
  r22(2); chk(rv == 16'h0141, "identifier 1 is read-only");
  r22(3); chk(rv == 16'h0DD1, "identifier 2 is read-only");
  r22(1); chk(rv == 16'h796D, "BMSR is read-only");
  w22(0, 16'h0100); chk(mdio_status == 16'h0100, "BMCR write shows on mdio_status");
  r22(0); chk(rv == 16'h0100, "BMCR read back");
  w22(4, 16'h01E1); w22(31, 16'hC0DE); w22(13, 16'h0003); w22(12, 16'h1234);
  r22(4); chk(rv == 16'h01E1, "register 4 read / write");
  r22(31); chk(rv == 16'hC0DE, "register 31 read / write");
  r22(5); chk(rv == 16'h0, "register 5 still 0");
  // BMCR reset: registers 0 and 4..31, self-clearing
  w22(0, 16'h8000);
  r22(0); chk(rv == 16'h1140 && mdio_status == 16'h1140, "BMCR reset: back to 0x1140, bit 15 self-clears");
  r22(4); chk(rv == 16'h0, "BMCR reset clears register 4");
  r22(31); chk(rv == 16'h0, "BMCR reset clears register 31");
  r22(12); chk(rv == 16'h0, "BMCR reset clears register 12");
  r22(13); chk(rv == 16'h0, "BMCR reset clears the MMD control register");
  r22(1); chk(rv == 16'h796D, "BMSR unaffected");
  w22(0, 16'h7FFF); chk(mdio_status == 16'h7FFF, "BMCR without bit 15 is a plain write");

  // Clause 45: address, write, read, post-read-increment, on each MMD
  a45(1, 16'd10); w45(1, 16'hAA01); a45(3, 16'd10); w45(3, 16'hAA03); a45(7, 16'd10); w45(7, 16'hAA07);
  a45(1, 16'd10); r45(1); chk(ack && rv == 16'hAA01, "MMD 1 register 10");
  a45(3, 16'd10); r45(3); chk(ack && rv == 16'hAA03, "MMD 3 register 10: own storage");
  r45(7); chk(ack && rv == 16'hAA07, "MMD 7 keeps its own address register");
  a45(1, 16'd11); w45(1, 16'h1111); w45(1, 16'h2222);
  r45(1); chk(rv == 16'h2222, "a write does not move the address");
  a45(1, 16'd10); p45(1); chk(rv == 16'hAA01, "post-read-increment reads at the address");
  p45(1); chk(rv == 16'h2222, "then the next register");
  r45(1); chk(rv == 16'h0, "address now 12");
  a45(1, 16'd2); r45(1); chk(rv == 16'h0141, "MMD device identifier 1");
  a45(3, 16'd3); r45(3); chk(rv == 16'h0DD3, "MMD 3 device identifier 2");
  a45(7, 16'd3); r45(7); chk(rv == 16'h0DD7, "MMD 7 device identifier 2");
  a45(7, 16'd5); r45(7); chk(rv == 16'h008A, "devices in package: MMD 1, 3, 7");
  w45(7, 16'h0); r45(7); chk(rv == 16'h008A, "devices in package is read-only");
  a45(3, 16'd2); w45(3, 16'h0); r45(3); chk(rv == 16'h0141, "identifier is read-only");
  a45(1, 16'd63); w45(1, 16'h6363); r45(1); chk(rv == 16'h6363, "register 63 is the last one");
  a45(1, 16'd64); w45(1, 16'h6464); r45(1); chk(ack && rv == 16'h0, "register 64 reads 0");
  a45(1, 16'd0); r45(1); chk(rv == 16'h0, "register 64 write did not alias register 0");
  a45(1, 16'hFFFF); p45(1); a45(1, 16'd0); r45(1); chk(rv == 16'h0, "address 0xFFFF wraps cleanly");
  a45(1, 16'd63); p45(1); p45(1); chk(rv == 16'h0, "post-increment past 63");
  // unimplemented MMD / other port: no response, nothing changes
  a45(2, 16'd10); r45(2); chk(!ack && rv == 16'hFFFF, "MMD 2 is not implemented: no response");
  frame(32, 2'b00, 2'b11, 4, 1, 0, 1); chk(!ack && rv == 16'hFFFF, "other port address: no response");
  frame(32, 2'b00, 2'b00, 4, 1, 16'd11, 0); r45(1); chk(rv == 16'h0, "another port's address frame is ignored");
  a45(1, 16'd10); r45(1); chk(rv == 16'hAA01, "MMD 1 register 10 unchanged");

  // Clause 22 indirect MMD access (registers 13 / 14)
  w22(13, 16'h0003); w22(14, 16'd20);                   // function 00: address 20 of MMD 3
  r22(14); chk(rv == 16'd20, "register 14 reads the MMD address");
  w22(13, 16'h4003); w22(14, 16'hD001); w22(14, 16'hD002);
  r22(14); chk(rv == 16'hD002, "function 01: data, no increment");
  w22(13, 16'h8003); w22(14, 16'hE014); w22(14, 16'hE015);   // function 10: increments on writes
  w22(13, 16'h0003); r22(14); chk(rv == 16'd22, "function 10: two writes moved the address to 22");
  w22(14, 16'd20); w22(13, 16'h8003);
  r22(14); chk(rv == 16'hE014, "function 10: read at 20");
  r22(14); chk(rv == 16'hE015, "function 10: read moved to 21");
  w22(13, 16'hC003); r22(14); chk(rv == 16'h0, "function 11: read at 22");
  r22(14); chk(rv == 16'h0, "function 11: reads do not increment (still 22)");
  w22(14, 16'hF016); w22(13, 16'h0003); r22(14); chk(rv == 16'd23, "function 11: a write increments");
  a45(3, 16'd20); r45(3); chk(rv == 16'hE014, "Clause 45 sees the indirect writes");
  a45(3, 16'd22); r45(3); chk(rv == 16'hF016, "indirect write at 22");
  w22(13, 16'h4007); a45(7, 16'd5); r22(14); chk(rv == 16'h008A, "indirect read of an MMD 7 read-only register");
  w22(13, 16'h4001); a45(1, 16'd2); r22(14); chk(rv == 16'h0141, "indirect read of the MMD 1 identifier 1");
  a45(1, 16'd3); r22(14); chk(rv == 16'h0DD1, "indirect read of the MMD 1 identifier 2");
  a45(1, 16'd64); w22(14, 16'h5A5A); r22(14); chk(rv == 16'h0, "indirect access past register 63: reads 0, write ignored");
  a45(1, 16'd0); r22(14); chk(rv == 16'h0, "the write at 64 did not alias register 0");
  w22(13, 16'h4002); r22(14); chk(ack && rv == 16'h0, "indirect access to an MMD that is not implemented reads 0");
  w22(14, 16'h1234); w22(13, 16'h0002); r22(14); chk(rv == 16'h0, "and ignores writes");
  w22(13, 16'h4007); w22(14, 16'h0); r22(14); chk(rv == 16'h008A, "indirect write to a read-only register ignored");
  w22(13, 16'h8007); w22(14, 16'h0); w22(13, 16'h0007); r22(14); chk(rv == 16'd6, "but the address still increments");

  // no response: other PHY address, undefined OP, short preamble; long preamble is fine
  frame(32, 2'b01, 2'b10, 4, 0, 0, 1); chk(!ack && rv == 16'hFFFF, "PHY address 4: no response");
  frame(32, 2'b01, 2'b10, 6, 0, 0, 1); chk(!ack, "PHY address 6: no response");
  frame(32, 2'b01, 2'b00, 5, 0, 16'h0040, 0); chk(mdio_status == 16'h7FFF, "Clause 22 OP 00 ignored");
  frame(32, 2'b01, 2'b11, 5, 0, 16'h0040, 0); chk(mdio_status == 16'h7FFF, "Clause 22 OP 11 ignored");
  frame(32, 2'b01, 2'b01, 4, 0, 16'h0040, 0); chk(mdio_status == 16'h7FFF, "write to another PHY ignored");
  frame(31, 2'b01, 2'b10, 5, 0, 0, 1); chk(!ack, "31-bit preamble: ignored");
  frame(31, 2'b01, 2'b01, 5, 0, 16'h0040, 0); chk(mdio_status == 16'h7FFF, "31-bit preamble write ignored");
  frame(45, 2'b01, 2'b10, 5, 0, 0, 1); chk(ack && rv == 16'h7FFF, "45-bit preamble accepted");
  frame(70, 2'b01, 2'b10, 5, 0, 0, 1); chk(ack && rv == 16'h7FFF, "a preamble longer than 63 still counts");
  frame(32, 2'b11, 2'b10, 5, 0, 0, 1); chk(!ack, "ST 11 is not a frame");
  frame(32, 2'b10, 2'b10, 5, 0, 0, 1); chk(!ack, "ST 10 is not a frame");

  // reset
  rst_n = 0; repeat (2) @(posedge clk);
  chk(mdio === 1'b1 && mdio_status == 16'h1140, "reset");
  rst_n = 1; repeat (2) @(posedge clk);
  a45(1, 16'd10); r45(1); chk(rv == 16'h0, "reset clears MMD 1");
  r45(3); chk(rv == 16'h0, "reset clears the MMD 3 address and data");
  a45(7, 16'd0); r45(7); chk(rv == 16'h0, "reset clears MMD 7 register 0");
  r22(4); chk(rv == 16'h0, "reset clears register 4");
  r22(1); chk(rv == phy_status, "BMSR after reset");
  w22(13, 16'h0007); r22(14); chk(rv == 16'h0, "reset clears the MMD 7 address");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #4000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
