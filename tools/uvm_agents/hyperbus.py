# HyperBus host agent (HyperRAM-style memory): CS#, CK, DQ[7:0] and RWDS,
# double data rate. One DDR beat per system clock: the host toggles CK on
# every beat; the device samples DQ on every CK edge and answers a beat on the
# following clock.
#
# Wires: cs_n, ck, the host and device halves of DQ (dq_m with dq_m_oe, dq_s
# with dq_s_oe) and of RWDS (rwds_m with rwds_m_oe, rwds_s with rwds_s_oe).
#
# Transaction: 48-bit command-address in 6 beats (CA[47] read, CA[46]
# register space, CA[45] linear burst (0 = wrapped), CA[44:16] upper and
# CA[2:0] lower word address), then for memory reads / writes and register
# reads an initial latency, then 16-bit words as two beats each, bits 15:8
# first. While CA is sent the device drives RWDS: high = latency doubled.
# During a read the device toggles RWDS with every byte it drives; during a
# memory write the host drives RWDS as a byte mask (1 = byte not written).
# Register writes have no latency and no mask.
#
# tb/top_tb.sv hyperbus_model: 256 words of memory (word address bits 7:0)
# and the registers ID0 (0x0000, 0x0C81), ID1 (0x0001, 0x0001) and CR0
# (0x0800, reset 0x8F1F). CR0[7:4] initial latency (0 = 5, 1 = 6, 2 = 7,
# 0xE = 3, 0xF = 4 clocks, others 6), CR0[3] fixed latency (always doubled;
# 0 = doubled only when a refresh is due, which the model takes from a
# free-running counter at CS# fall), CR0[1:0] wrapped burst length (0 = 128,
# 1 = 64, 2 = 16, 3 = 32 bytes); only CR0 bits 7:3 and 1:0 are writable,
# other register writes are ignored, unmapped registers read 0. A register
# read returns the same register for every word. Latency is counted in CK
# edges after the last CA beat: 2 x latency (4 x when doubled); a write beat
# inside the latency is ignored.

HB_FUNCS = """
// initial latency in clocks from CR0[7:4]
function automatic int hb_lat(bit [3:0] code);
  case (code)
    4'h0: return 5;
    4'h1: return 6;
    4'h2: return 7;
    4'hE: return 3;
    4'hF: return 4;
    default: return 6;
  endcase
endfunction
// wrapped burst length in words from CR0[1:0]
function automatic int hb_wrap(bit [1:0] bl);
  case (bl)
    2'd0: return 64;
    2'd1: return 32;
    2'd2: return 8;
    default: return 16;
  endcase
endfunction
localparam bit [15:0] HB_CR0_RESET = 16'h8F1F;
localparam bit [15:0] HB_CR0_WMASK = 16'h00FB;
"""

SPEC = dict(
    vip="HyperBus-UVM-VIP", p="hyperbus", P="HyperBus", dir="hyperbus", family="Memory / Flash",
    desc="HyperBus / HyperRAM host VIP: 48-bit command-address, RWDS latency indication (fixed / variable, "
         "doubled), read strobe, write byte mask, linear and wrapped bursts, ID / CR0 registers.",
    about="""
HyperBus is the 12-pin DDR memory bus of HyperRAM and HyperFlash parts used as
external RAM and execute-in-place flash on MCUs and FPGAs. A transaction is a
48-bit command-address, an initial latency the device may double by driving
RWDS high, then 16-bit words; RWDS is the read data strobe and the write byte
mask. The DUT model is a HyperRAM with its ID and configuration registers; the
scoreboard keeps its own memory and CR0 and predicts every read word, the
latency in clocks (from CR0 and the RWDS level seen during the command) and
the wrapped-burst address order, so a wrong latency count, a mask applied to
the wrong byte or a wrap at the wrong boundary is a mismatch. The monitor
rebuilds each transaction from the wires.""",
    defs=HB_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "cs_n"), ("in", "logic", "ck"),
        ("in", "logic [7:0]", "dq_m"), ("in", "logic", "dq_m_oe"),
        ("in", "logic", "rwds_m"), ("in", "logic", "rwds_m_oe"),
        ("out", "logic [7:0]", "dq_s"), ("out", "logic", "dq_s_oe"),
        ("out", "logic", "rwds_s"), ("out", "logic", "rwds_s_oe"),
    ],
    fields=[
        ("bit", "rw", "req"),                   # 1 = read
        ("bit", "regsp", "req"),                # 1 = register space (named so: "as" is an SMT-LIB keyword)
        ("bit", "burst", "req"),                # 1 = linear, 0 = wrapped
        ("bit [31:0]", "addr", "req"),          # word address
        ("bit [5:0]", "nwords", "req"),
        ("bit [15:0]", "wdata", "req", "q"),
        ("bit [1:0]", "wmask", "req", "q"),     # per word: bit 1 masks bits 15:8, bit 0 bits 7:0
        ("bit [15:0]", "rdata", "rsp", "q"),
        ("bit", "lat2x", "rsp"),                # RWDS during the command-address
        ("bit [4:0]", "lat_clk", "rsp"),        # clocks between the command-address and the data
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [1:0]", "rsel", "info", "rand"),  # register: ID0, ID1, unmapped, CR0
    ],
    constraints="""
constraint c_kind { regsp dist { 0 := 10, 1 := 2 }; }
constraint c_mem  { !regsp -> addr < 256 && nwords >= 1 && nwords <= 20; }
constraint c_reg  { regsp -> nwords == 1 && addr == (rsel == 0 ? 32'h0 : rsel == 1 ? 32'h1 : rsel == 2 ? 32'h2 : 32'h800);
                    (regsp && !rw) -> rsel == 3; }
""",
    tr_functions="""
// write data and masks from the seed; a CR0 write picks a valid latency code
function void post_randomize();
  bit [31:0] x = seed | 1;
  wdata.delete(); wmask.delete();
  if (!rw)
    for (int i = 0; i < nwords; i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      wdata.push_back(x[15:0]);
      wmask.push_back((!regsp && x[20:18] == 0) ? x[17:16] : 2'b00);
    end
  if (regsp && !rw) begin
    bit [3:0] code;
    case (x[26:24] % 5) 0: code = 4'h0; 1: code = 4'h1; 2: code = 4'h2; 3: code = 4'hE; default: code = 4'hF; endcase
    wdata[0] = {8'h8F, code, x[27], 1'b1, x[29:28]};
  end
endfunction
""",
    drv_rsp=True,
    drv_desc="one transaction per item: command-address, RWDS latency level, latency clocks, data words (read bytes on RWDS edges, write bytes with the RWDS mask)",
    drv_members="bit [15:0] cr0 = HB_CR0_RESET;   // the host's copy of CR0 (it programs the latency)",
    drv_idle="""
vif.drv_cb.cs_n      <= 1'b1;
vif.drv_cb.ck        <= 1'b0;
vif.drv_cb.dq_m      <= '0;
vif.drv_cb.dq_m_oe   <= 1'b0;
vif.drv_cb.rwds_m    <= 1'b0;
vif.drv_cb.rwds_m_oe <= 1'b0;
""",
    drv_tasks="""
// one beat: toggle CK, drive (oe) or release DQ and RWDS
task beat(bit oe, bit [7:0] d, bit moe, bit m);
  vif.drv_cb.ck        <= !vif.drv_cb.ck;
  vif.drv_cb.dq_m_oe   <= oe;
  vif.drv_cb.dq_m      <= oe ? d : 8'h0;
  vif.drv_cb.rwds_m_oe <= moe;
  vif.drv_cb.rwds_m    <= moe ? m : 1'b0;
  @(vif.drv_cb);
endtask
""",
    drv_item="""
bit [47:0] ca = {t.rw, t.regsp, t.burst, t.addr[31:3], 13'h0, t.addr[2:0]};
bit [7:0] rb[$];
bit rp;
int lat = 0;
t.rdata.delete();
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b0;
@(vif.drv_cb);
for (int i = 5; i >= 0; i--) begin
  beat(1'b1, ca[8*i +: 8], 1'b0, 1'b0);
  if (i == 4) t.lat2x = vif.drv_cb.rwds_s;
end
if (!(!t.rw && t.regsp)) lat = hb_lat(cr0[7:4]) * (t.lat2x ? 2 : 1);
t.lat_clk = lat;
if (t.rw) begin
  rp = vif.drv_cb.rwds_s;
  for (int i = 0; i < 2 * lat + 2 * t.nwords + 3; i++) begin
    if (i < 2 * lat + 2 * t.nwords) beat(1'b0, 8'h0, 1'b0, 1'b0);
    else @(vif.drv_cb);
    if (vif.drv_cb.rwds_s != rp && vif.drv_cb.dq_s_oe) rb.push_back(vif.drv_cb.dq_s);
    rp = vif.drv_cb.rwds_s;
  end
  for (int i = 0; i + 1 < rb.size(); i += 2) t.rdata.push_back({rb[i], rb[i + 1]});
end else begin
  repeat (2 * lat) beat(1'b0, 8'h0, 1'b0, 1'b0);
  foreach (t.wdata[i]) begin
    beat(1'b1, t.wdata[i][15:8], !t.regsp, t.wmask[i][1]);
    beat(1'b1, t.wdata[i][7:0],  !t.regsp, t.wmask[i][0]);
  end
  if (t.regsp && t.addr == 32'h800 && t.wdata.size() != 0)
    cr0 = (cr0 & ~HB_CR0_WMASK) | (t.wdata[0] & HB_CR0_WMASK);
end
vif.drv_cb.dq_m_oe <= 1'b0; vif.drv_cb.rwds_m_oe <= 1'b0;
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b1;
repeat (3) @(vif.drv_cb);
""",
    mon_desc="transactions between CS# fall and rise: command-address and write beats from DQ on CK edges, read bytes on RWDS edges, latency from the released CK edges",
    mon_run="""
bit [7:0] hb[$], db[$];
bit [1:0] mb[$];
bit mk[$];
int ne = 0, nrel = 0, first = -1, firstw = -1;
bit ck_p = 0, rw_p = 0, cs_p = 1, l2x = 0;
forever begin
  @(vif.mon_cb);
  if (!vif.mon_cb.cs_n) begin
    if (cs_p) begin hb.delete(); db.delete(); mk.delete(); ne = 0; nrel = 0; first = -1; firstw = -1; end
    if (vif.mon_cb.rwds_s != rw_p && vif.mon_cb.dq_s_oe) begin
      if (first < 0) first = nrel;
      db.push_back(vif.mon_cb.dq_s);
    end
    if (vif.mon_cb.ck != ck_p) begin
      ne++;
      if (vif.mon_cb.dq_m_oe) begin
        hb.push_back(vif.mon_cb.dq_m);
        mk.push_back(vif.mon_cb.rwds_m_oe && vif.mon_cb.rwds_m);
        if (ne > 6 && firstw < 0) firstw = nrel;
      end else nrel++;
      if (ne == 2) l2x = vif.mon_cb.rwds_s;
    end
  end else if (!cs_p) build(hb, mk, db, l2x, nrel, first, firstw);
  ck_p = vif.mon_cb.ck; rw_p = vif.mon_cb.rwds_s; cs_p = vif.mon_cb.cs_n;
end
""",
    mon_tasks="""
function void build(bit [7:0] hb[$], bit mk[$], bit [7:0] db[$], bit l2x, int nrel, int first, int firstw);
  hyperbus_transaction t = hyperbus_transaction::type_id::create("t");
  bit [47:0] ca = 0;
  if (hb.size() < 6) begin
    `uvm_error("MON", $sformatf("HyperBus: transaction with %0d command-address beats", hb.size()))
    return;
  end
  for (int i = 0; i < 6; i++) ca = {ca[39:0], hb[i]};
  t.rw = ca[47]; t.regsp = ca[46]; t.burst = ca[45]; t.addr = {ca[44:16], ca[2:0]};
  t.lat2x = l2x;
  if (t.rw) begin
    // the first byte answers the first CK edge after the latency
    t.lat_clk = (first > 0) ? (first - 1) / 2 : 0;
    t.nwords = (first > 0) ? (nrel - (first - 1)) / 2 : 0;
    for (int i = 0; i + 1 < db.size(); i += 2) t.rdata.push_back({db[i], db[i + 1]});
  end else begin
    t.lat_clk = (firstw > 0) ? firstw / 2 : 0;
    t.nwords = (hb.size() - 6) / 2;
    for (int i = 6; i + 1 < hb.size(); i += 2) begin
      t.wdata.push_back({hb[i], hb[i + 1]});
      t.wmask.push_back({mk[i], mk[i + 1]});
    end
  end
  publish(t);
endfunction
""",
    sb_members="""bit [15:0] mem [256];
bit [15:0] cr0 = HB_CR0_RESET;""",
    predict="""
// independent HyperRAM model: latency from CR0, wrapped bursts, byte masks
int L = hb_lat(cr0[7:4]), W = hb_wrap(cr0[1:0]);
bit [31:0] a;
if (cr0[3]) t.lat2x = 1;                 // fixed latency: always doubled
t.lat_clk = (!t.rw && t.regsp) ? 0 : L * (t.lat2x ? 2 : 1);
t.rdata.delete();
for (int i = 0; i < t.nwords; i++) begin
  a = t.burst ? t.addr + i : ((t.addr & ~(W - 1)) | ((t.addr + i) & (W - 1)));
  if (t.rw) begin
    if (!t.regsp) t.rdata.push_back(mem[a[7:0]]);
    else t.rdata.push_back(t.addr == 0 ? 16'h0C81 : t.addr == 1 ? 16'h0001 : t.addr == 32'h800 ? cr0 : 16'h0);
  end else if (!t.regsp && i < t.wdata.size()) begin
    if (!t.wmask[i][1]) mem[a[7:0]][15:8] = t.wdata[i][15:8];
    if (!t.wmask[i][0]) mem[a[7:0]][7:0]  = t.wdata[i][7:0];
  end
end
if (!t.rw && t.regsp && t.addr == 32'h800 && t.wdata.size() != 0)
  cr0 = (cr0 & ~HB_CR0_WMASK) | (t.wdata[0] & HB_CR0_WMASK);
""",
    checks="""
if (t.rw && t.rdata.size() != t.nwords) fail(t, $sformatf("%0d words read for %0d requested", t.rdata.size(), t.nwords));
if (!t.rw && t.regsp && t.addr != 32'h800) fail(t, "write to a read-only register");
if (!t.regsp && t.addr > 255) fail(t, "address beyond the memory");
""",
    coverage="""
cp_op    : coverpoint {tr.rw, tr.regsp} { bins mem_wr = {2'b00}; bins reg_wr = {2'b01}; bins mem_rd = {2'b10}; bins reg_rd = {2'b11}; }
cp_burst : coverpoint tr.burst;
cp_n     : coverpoint tr.nwords { bins one = {1}; bins few = {[2:7]}; bins many = {[8:$]}; }
cp_lat   : coverpoint tr.lat_clk { bins zero = {0}; bins l[] = {3, 4, 5, 6, 7, 8, 10, 12, 14}; }
cp_2x    : coverpoint tr.lat2x;
cp_wrap8 : coverpoint (!tr.burst && tr.nwords > 1 && (tr.addr % 8) + tr.nwords > 8) { bins crosses = {1}; }
cp_mask  : coverpoint (!tr.rw && !tr.regsp && tr.wmask.size() != 0 && tr.wmask[0] != 0) { bins masked = {1}; }
x_op_burst : cross cp_op, cp_burst { ignore_bins regs = binsof(cp_op.reg_wr) || binsof(cp_op.reg_rd); }
""",
    directed="""
// registers after reset (fixed, doubled latency of 6 clocks)
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h800; t.nwords = 1; send(t);
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h0; t.nwords = 1; send(t);
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h1; t.nwords = 1; send(t);
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h2; t.nwords = 1; send(t);
// linear write and read, byte masks
t = item(); t.burst = 1; t.addr = 32'h10; t.nwords = 4; t.wdata = '{16'h1122, 16'h3344, 16'h5566, 16'h7788}; t.wmask = '{0, 0, 0, 0}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h10; t.nwords = 4; send(t);
t = item(); t.burst = 1; t.addr = 32'h10; t.nwords = 2; t.wdata = '{16'hAAAA, 16'hBBBB}; t.wmask = '{2'b10, 2'b01}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h10; t.nwords = 2; send(t);
// wrapped bursts at the 16-word boundary, linear across it
t = item(); t.burst = 1; t.addr = 32'h1E; t.nwords = 2; t.wdata = '{16'hE1E1, 16'hF1F1}; t.wmask = '{0, 0}; send(t);
t = item(); t.rw = 1; t.burst = 0; t.addr = 32'h1E; t.nwords = 4; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h1F; t.nwords = 3; send(t);
t = item(); t.burst = 0; t.addr = 32'h2F; t.nwords = 2; t.wdata = '{16'h2F2F, 16'h2020}; t.wmask = '{0, 0}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h20; t.nwords = 16; send(t);
// variable latency of 3 clocks, 16-byte wrap
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h00E2}; t.wmask = '{0}; send(t);
for (int i = 0; i < 6; i++) begin
  t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h800; t.nwords = 1; send(t);
end
t = item(); t.rw = 1; t.burst = 0; t.addr = 32'h0E; t.nwords = 3; send(t);
t = item(); t.burst = 0; t.addr = 32'h17; t.nwords = 3; t.wdata = '{16'h1717, 16'h1010, 16'h1111}; t.wmask = '{0, 0, 0}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h10; t.nwords = 8; send(t);
// every latency code, fixed
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h000B}; t.wmask = '{0}; send(t);
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h800; t.nwords = 1; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h001B}; t.wmask = '{0}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h40; t.nwords = 1; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h002B}; t.wmask = '{0}; send(t);
t = item(); t.rw = 1; t.burst = 1; t.addr = 32'h40; t.nwords = 1; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h00EB}; t.wmask = '{0}; send(t);
t = item(); t.burst = 1; t.addr = 32'h40; t.nwords = 1; t.wdata = '{16'h4040}; t.wmask = '{0}; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h00FA}; t.wmask = '{0}; send(t);
t = item(); t.rw = 1; t.burst = 0; t.addr = 32'h7F; t.nwords = 33; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'hFFFF}; t.wmask = '{0}; send(t);
t = item(); t.rw = 1; t.regsp = 1; t.addr = 32'h800; t.nwords = 1; send(t);
t = item(); t.regsp = 1; t.addr = 32'h800; t.nwords = 1; t.wdata = '{16'h001F}; t.wmask = '{0}; send(t);
""",
    drain_ns=1000,
    model="""
module hyperbus_model (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       cs_n,
  input  logic       ck,
  input  logic [7:0] dq_m,
  input  logic       dq_m_oe,
  input  logic       rwds_m,
  input  logic       rwds_m_oe,
  output logic [7:0] dq_s,
  output logic       dq_s_oe,
  output logic       rwds_s,
  output logic       rwds_s_oe
);
  logic [15:0] mem [0:255];
  logic [15:0] cr0;
  logic [47:0] ca;
  logic [5:0]  fr;            // free-running: refresh due when bit 5 is set
  logic        cs_p, ck_p, lat2x, hi;
  logic [2:0]  nca;
  logic [1:0]  ph;            // 0 command-address, 1 latency, 2 data, 3 idle
  logic [7:0]  lcnt, latn, widx, ub;

  function automatic logic [3:0] lat_clk(input logic [3:0] code);
    case (code)
      4'h0: lat_clk = 4'd5;
      4'h1: lat_clk = 4'd6;
      4'h2: lat_clk = 4'd7;
      4'hE: lat_clk = 4'd3;
      4'hF: lat_clk = 4'd4;
      default: lat_clk = 4'd6;
    endcase
  endfunction
  function automatic logic [7:0] wrap_mask(input logic [1:0] bl);   // burst words - 1
    case (bl)
      2'd0: wrap_mask = 8'd63;
      2'd1: wrap_mask = 8'd31;
      2'd2: wrap_mask = 8'd7;
      default: wrap_mask = 8'd15;
    endcase
  endfunction

  wire        edge_ = !cs_n && (ck != ck_p);
  wire [31:0] wa    = {ca[44:16], ca[2:0]};
  wire [31:0] wm    = {24'h0, wrap_mask(cr0[1:0])};
  wire [31:0] ai    = ca[45] ? wa + {24'h0, widx} : ((wa & ~wm) | ((wa + {24'h0, widx}) & wm));
  wire [15:0] rword = !ca[46] ? mem[ai[7:0]] :
                      (wa == 32'h0) ? 16'h0C81 : (wa == 32'h1) ? 16'h0001 : (wa == 32'h800) ? cr0 : 16'h0;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 256; i++) mem[i] <= '0;
      cr0 <= 16'h8F1F; ca <= '0; fr <= '0; cs_p <= 1'b1; ck_p <= 1'b0; lat2x <= 1'b0; hi <= 1'b1;
      nca <= '0; ph <= 2'd3; lcnt <= '0; latn <= '0; widx <= '0; ub <= '0;
      dq_s <= '0; dq_s_oe <= 1'b0; rwds_s <= 1'b0; rwds_s_oe <= 1'b0;
    end else begin
      fr <= fr + 6'd1;
      cs_p <= cs_n; ck_p <= ck;
      if (cs_n) begin
        ph <= 2'd3; dq_s_oe <= 1'b0; rwds_s_oe <= 1'b0; rwds_s <= 1'b0;
      end else if (cs_p) begin                     // CS# fall: RWDS gives the latency
        ph <= 2'd0; nca <= '0; hi <= 1'b1; widx <= '0; lcnt <= '0;
        lat2x <= cr0[3] | fr[5];
        rwds_s <= cr0[3] | fr[5]; rwds_s_oe <= 1'b1;
      end else if (edge_) begin
        case (ph)
          2'd0: if (dq_m_oe) begin
            ca <= {ca[39:0], dq_m};
            nca <= nca + 3'd1;
            if (nca == 3'd5) begin : ca_done
              logic [47:0] c;
              logic [7:0]  l;
              c = {ca[39:0], dq_m};
              l = {3'b000, lat_clk(cr0[7:4]), 1'b0};
              if (lat2x) l = l << 1;
              if (!c[47] && c[46]) begin             // register write: data right away
                ph <= 2'd2; rwds_s_oe <= 1'b0;
              end else begin
                ph <= 2'd1; latn <= l;
                rwds_s_oe <= c[47]; rwds_s <= 1'b0;  // a read keeps RWDS (low until data)
              end
            end
          end
          2'd1: begin
            lcnt <= lcnt + 8'd1;
            if (lcnt + 8'd1 == latn) ph <= 2'd2;
          end
          2'd2: if (ca[47]) begin
            dq_s <= hi ? rword[15:8] : rword[7:0];
            dq_s_oe <= 1'b1;
            rwds_s <= !rwds_s;
            hi <= !hi;
            if (!hi) widx <= widx + 8'd1;
          end else if (dq_m_oe) begin
            if (ca[46]) begin
              if (hi) ub <= dq_m;
              else if (wa == 32'h800 && widx == 8'd0) cr0 <= (cr0 & ~16'h00FB) | ({ub, dq_m} & 16'h00FB);
            end else if (!(rwds_m_oe && rwds_m)) begin
              if (hi) mem[ai[7:0]][15:8] <= dq_m;
              else    mem[ai[7:0]][7:0]  <= dq_m;
            end
            hi <= !hi;
            if (!hi) widx <= widx + 8'd1;
          end
          default: ;
        endcase
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({dq_s_oe, rwds_s_oe, rwds_s}))
  else $error("HyperBus: X on device outputs");
// one driver at a time on DQ and on RWDS
assert property (@(posedge clk) disable iff (!rst_n) !(dq_s_oe && dq_m_oe))
  else $error("HyperBus: DQ driven by host and device at once");
assert property (@(posedge clk) disable iff (!rst_n) !(rwds_s_oe && rwds_m_oe))
  else $error("HyperBus: RWDS driven by host and device at once");
// the device lets go of the bus while deselected and drives RWDS from CS# fall
assert property (@(posedge clk) disable iff (!rst_n) cs_n && $past(cs_n) |-> !dq_s_oe && !rwds_s_oe)
  else $error("HyperBus: device drives the bus while CS# is high");
assert property (@(posedge clk) disable iff (!rst_n) $fell(cs_n) |=> rwds_s_oe)
  else $error("HyperBus: RWDS latency level not driven during the command-address");
// a read strobe edge comes with valid data
assert property (@(posedge clk) disable iff (!rst_n) $changed(rwds_s) && dq_s_oe |-> !$isunknown(dq_s))
  else $error("HyperBus: RWDS edge without valid read data");
// CK only toggles while selected
assert property (@(posedge clk) disable iff (!rst_n) cs_n && $past(cs_n) |-> $stable(ck))
  else $error("HyperBus: CK toggles while CS# is high");
cover property (@(posedge clk) disable iff (!rst_n) $fell(cs_n) ##1 !rwds_s);
cover property (@(posedge clk) disable iff (!rst_n) rwds_m_oe && rwds_m);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic cs_n = 1, ck = 0, dq_m_oe = 0, rwds_m = 0, rwds_m_oe = 0;
logic [7:0] dq_m = 0;
wire [7:0] dq_s;
wire dq_s_oe, rwds_s, rwds_s_oe;

always #5 clk = ~clk;

hyperbus_model u_dut (.clk(clk), .rst_n(rst_n), .cs_n(cs_n), .ck(ck), .dq_m(dq_m), .dq_m_oe(dq_m_oe),
                      .rwds_m(rwds_m), .rwds_m_oe(rwds_m_oe), .dq_s(dq_s), .dq_s_oe(dq_s_oe),
                      .rwds_s(rwds_s), .rwds_s_oe(rwds_s_oe));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// bus rules watched all the time
int clash = 0, idle_drv = 0;
logic cs_q = 1'b1;
always @(posedge clk) begin
  if (rst_n && ((dq_s_oe && dq_m_oe) || (rwds_s_oe && rwds_m_oe))) clash++;
  if (rst_n && cs_n && cs_q && (dq_s_oe || rwds_s_oe)) idle_drv++;
  cs_q <= cs_n;
end

task automatic bt(input logic oe, input logic [7:0] d, input logic moe, input logic m);
  @(negedge clk); ck = !ck; dq_m_oe = oe; dq_m = d; rwds_m_oe = moe; rwds_m = m;
endtask

logic [15:0] rbuf [0:63];
int nrd, first, l2x;
logic l2x_oe, wr_rwds_oe;
logic [1:0] lat_rwds;
task automatic ca(input logic rw, input logic as_, input logic lin, input logic [31:0] a);
  logic [47:0] c;
  logic [7:0] b;
  c = {rw, as_, lin, a[31:3], 13'h0, a[2:0]};
  @(negedge clk); cs_n = 0;
  for (int i = 5; i >= 0; i--) begin
    b = c[8*i +: 8];
    bt(1, b, 0, 0);
    if (i == 4) begin l2x = rwds_s; l2x_oe = rwds_s_oe; end
  end
endtask
task automatic finish_xfer;
  @(negedge clk); dq_m_oe = 0; rwds_m_oe = 0;
  @(negedge clk); cs_n = 1;
  repeat (3) @(negedge clk);
endtask
// read n words, the host waiting lat clocks (2 x lat CK edges)
task automatic rd(input logic as_, input logic lin, input logic [31:0] a, input int n, input int lat);
  logic rp;
  logic [7:0] hb;
  int k, ne;
  ca(1, as_, lin, a);
  k = 0; ne = 0; first = -1; rp = rwds_s; hb = 0;
  for (int i = 0; i < 2 * lat + 2 * n + 3; i++) begin
    if (i < 2 * lat + 2 * n) begin bt(0, 0, 0, 0); ne++; end
    else @(negedge clk);
    if (ne == 3) lat_rwds = {rwds_s_oe, rwds_s};
    if (rwds_s !== rp && dq_s_oe) begin
      if (first < 0) first = ne - 2;   // CK edges before the one the first byte answers
      if (k % 2 == 0) hb = dq_s; else rbuf[k / 2] = {hb, dq_s};
      k++;
    end
    rp = rwds_s;
  end
  nrd = k / 2;
  finish_xfer();
endtask
// write n words d0 + 0x0101 * i after lat clocks (lat < 0: -lat clocks,
// doubled when RWDS says so); m0 masks word 0
task automatic wr(input logic as_, input logic lin, input logic [31:0] a, input int n, input logic [15:0] d0,
                  input int lat, input logic [1:0] m0 = 2'b00);
  logic [15:0] d;
  ca(0, as_, lin, a);
  if (lat < 0) lat = l2x ? -2 * lat : -lat;
  repeat (2 * lat) bt(0, 0, 0, 0);
  wr_rwds_oe = 0;
  for (int i = 0; i < n; i++) begin
    d = d0 + 16'h0101 * i;
    bt(1, d[15:8], !as_, (i == 0) && m0[1]);
    bt(1, d[7:0],  !as_, (i == 0) && m0[0]);
    wr_rwds_oe = wr_rwds_oe | rwds_s_oe;
  end
  finish_xfer();
endtask
// a register read in variable latency mode: the latency follows RWDS
int lat_now;
task automatic rd_var(input logic as_, input logic lin, input logic [31:0] a, input int n, input int lc);
  // RWDS is known only after the command-address: read with the longer
  // wait, the data starts where the level says
  rd(as_, lin, a, n, 2 * lc);
  lat_now = l2x ? 2 * lc : lc;
endtask

initial begin
  int seen0, seen1, bad_lat;
  repeat (3) @(posedge clk);
  chk(dq_s_oe === 1'b0 && rwds_s_oe === 1'b0, "bus released during reset");
  rst_n = 1;
  repeat (3) @(posedge clk);

  // registers after reset: fixed latency, 6 clocks doubled
  rd(1, 1, 32'h800, 1, 12);
  chk(nrd == 1 && rbuf[0] === 16'h8F1F, $sformatf("CR0 reads 0x8F1F after reset (%h)", rbuf[0]));
  chk(l2x === 1'b1 && l2x_oe === 1'b1, "fixed latency: device drives RWDS high during the command-address");
  chk(lat_rwds === 2'b10, "and drives it low through the latency of a read");
  chk(first == 24, $sformatf("read data after 2 x 6 clocks (24 CK edges, saw %0d)", first));
  rd(1, 1, 32'h0, 1, 12); chk(rbuf[0] === 16'h0C81, "ID0");
  rd(1, 1, 32'h1, 1, 12); chk(rbuf[0] === 16'h0001, "ID1");
  rd(1, 1, 32'h2, 1, 12); chk(rbuf[0] === 16'h0000, "unmapped register reads 0");
  rd(1, 1, 32'h800, 2, 12); chk(nrd == 2 && rbuf[1] === 16'h8F1F, "a register read repeats the register");

  // memory: linear write / read, masks
  rd(0, 1, 32'h0, 2, 12); chk(nrd == 2 && rbuf[0] === 16'h0 && rbuf[1] === 16'h0, "memory 0 after reset");
  rd(0, 1, 32'hFF, 1, 12); chk(rbuf[0] === 16'h0, "last word 0 after reset");
  wr(0, 1, 32'h10, 4, 16'h1122, 12);
  chk(wr_rwds_oe === 1'b0, "device releases RWDS for the write mask");
  rd(0, 1, 32'h10, 4, 12);
  chk(nrd == 4 && rbuf[0] === 16'h1122 && rbuf[1] === 16'h1223 && rbuf[2] === 16'h1324 && rbuf[3] === 16'h1425,
      "linear write and read of 4 words, bits 15:8 first");
  wr(0, 1, 32'h10, 1, 16'hAAAA, 12, 2'b10);
  wr(0, 1, 32'h11, 1, 16'hBBBB, 12, 2'b01);
  rd(0, 1, 32'h10, 2, 12);
  chk(rbuf[0] === 16'h11AA && rbuf[1] === 16'hBB23, $sformatf("RWDS byte masks (%h %h)", rbuf[0], rbuf[1]));
  rd(0, 1, 32'h12, 1, 12); chk(rbuf[0] === 16'h1324, "masked burst left the next word");

  // wrapped bursts, 16 words after reset
  wr(0, 1, 32'h1E, 2, 16'hE1E1, 12);
  rd(0, 0, 32'h1E, 4, 12);
  chk(rbuf[0] === 16'hE1E1 && rbuf[1] === 16'hE2E2 && rbuf[2] === 16'h11AA && rbuf[3] === 16'hBB23,
      "wrapped read wraps at the 16-word boundary");
  rd(0, 1, 32'h1F, 2, 12); chk(rbuf[1] === 16'h0000, "linear read runs on past it");
  wr(0, 0, 32'h2F, 2, 16'h2F2F, 12);
  rd(0, 1, 32'h20, 1, 12); chk(rbuf[0] === 16'h3030, "wrapped write wraps too");
  rd(0, 1, 32'h30, 1, 12); chk(rbuf[0] === 16'h0000, "and does not reach the next group");

  // CR0: latency 3 clocks, variable latency, 16-byte (8-word) wrap; only bits 7:3, 1:0 written
  wr(1, 1, 32'h800, 1, 16'h00E2, 0);
  chk(wr_rwds_oe === 1'b0, "device releases RWDS for a register write");
  rd(1, 1, 32'h800, 1, 6);
  chk(rbuf[0] === 16'h8FE6, $sformatf("CR0 written (%h)", rbuf[0]));
  seen0 = 0; seen1 = 0; bad_lat = 0;
  for (int i = 0; i < 12; i++) begin
    rd_var(0, 1, 32'h10, 1, 3);
    if (l2x) seen1++; else seen0++;
    if (first != 2 * lat_now || rbuf[0] !== 16'h11AA) bad_lat++;
    repeat (i * 3) @(negedge clk);
  end
  chk(seen0 > 0 && seen1 > 0, $sformatf("variable latency: RWDS low (%0d) and high (%0d)", seen0, seen1));
  chk(bad_lat == 0, "variable latency: data after 3 or 6 clocks as RWDS says");
  rd_var(0, 0, 32'h0E, 3, 3);
  chk(rbuf[0] === 16'h0 && rbuf[1] === 16'h0 && rbuf[2] === 16'h0, "8-word wrap read");
  wr(0, 1, 32'h0E, 1, 16'h0E0E, -3);
  wr(0, 1, 32'h08, 1, 16'h0808, -3);
  rd_var(0, 0, 32'h0F, 2, 3);
  chk(rbuf[0] === 16'h0 && rbuf[1] === 16'h0808, "8-word wrap: 0x0F then 0x08");

  // back to fixed latency, each code
  wr(1, 1, 32'h800, 1, 16'h000B, 0); rd(0, 1, 32'h10, 1, 10); chk(first == 20, "code 0: 5 clocks doubled");
  wr(1, 1, 32'h800, 1, 16'h001B, 0); rd(0, 1, 32'h10, 1, 12); chk(first == 24, "code 1: 6 clocks doubled");
  wr(1, 1, 32'h800, 1, 16'h002B, 0); rd(0, 1, 32'h10, 1, 14); chk(first == 28, "code 2: 7 clocks doubled");
  wr(1, 1, 32'h800, 1, 16'h00FB, 0); rd(0, 1, 32'h10, 1, 8);  chk(first == 16, "code F: 4 clocks doubled");
  wr(1, 1, 32'h800, 1, 16'h00EB, 0); rd(0, 1, 32'h10, 1, 6);  chk(first == 12, "code E: 3 clocks doubled");
  wr(1, 1, 32'h800, 1, 16'h005B, 0); rd(0, 1, 32'h10, 1, 12); chk(first == 24, "reserved code: 6 clocks");
  // write beats inside the latency are ignored
  wr(1, 1, 32'h800, 1, 16'h001B, 0);
  wr(0, 1, 32'h40, 2, 16'h4040, 11);
  rd(0, 1, 32'h40, 2, 12);
  chk(rbuf[0] === 16'h4141 && rbuf[1] === 16'h0000, "write data inside the latency ignored");
  // 128-byte and 64-byte wraps
  wr(1, 1, 32'h800, 1, 16'h0018, 0);
  wr(0, 1, 32'h80, 1, 16'h8080, 12);
  rd(0, 0, 32'hBF, 2, 12); chk(rbuf[1] === 16'h8080, "64-word wrap");
  wr(1, 1, 32'h800, 1, 16'h0019, 0);
  wr(0, 1, 32'hA0, 1, 16'hA0A0, 12);
  rd(0, 0, 32'hBF, 2, 12); chk(rbuf[1] === 16'hA0A0, "32-word wrap");
  // ID registers are read-only, CR0 keeps its fixed bits
  wr(1, 1, 32'h0, 1, 16'hFFFF, 0);
  rd(1, 1, 32'h0, 1, 12); chk(rbuf[0] === 16'h0C81, "ID0 is read-only");
  rd(1, 1, 32'h800, 1, 12); chk(rbuf[0] === 16'h8F1D, $sformatf("a write to ID0 does not reach CR0 (%h)", rbuf[0]));
  wr(1, 1, 32'h800, 1, 16'h0000, 0);
  rd(1, 1, 32'h800, 1, 10); chk(rbuf[0] === 16'h8F04, $sformatf("CR0 bits 15:8 and 2 are fixed (%h)", rbuf[0]));
  // CS# cut in the middle of the command-address: the next transaction is clean
  @(negedge clk); cs_n = 0; bt(1, 8'hA0, 0, 0); bt(1, 8'h00, 0, 0); finish_xfer();
  wr(1, 1, 32'h800, 1, 16'h001F, 0);
  rd(1, 1, 32'h800, 1, 12); chk(rbuf[0] === 16'h8F1F && first == 24, "transaction after a cut command-address");

  chk(clash == 0, "DQ / RWDS never driven by both sides");
  chk(idle_drv == 0, "device releases the bus while CS# is high");
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
