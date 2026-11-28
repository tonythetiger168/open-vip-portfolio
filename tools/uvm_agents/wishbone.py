# Wishbone B4 pipelined master agent.
#
# One item is one bus cycle (CYC high): 1..8 requests issued back to back
# (STB, held while STALL), answered in order by ACK, ERR or RTY. Cycle types
# follow CTI: classic (000) single requests, constant-address burst (001),
# incrementing burst (010) with BTE linear / wrap-4 / wrap-8 / wrap-16, and
# end-of-burst (111). A cycle may be aborted by dropping CYC with responses
# still outstanding.
#
# tb/top_tb.sv wishbone_model (slave):
#   * ADR[11:0]: 0x000-0x3FF 256 words of memory with SEL byte lanes;
#     0x800-0x83F 16 words behind a busy device that answers RTY to the first
#     two attempts at a word and ACK to the third; everything else ERR.
#   * STALL from an LFSR (about one clock in four) and while four responses
#     are queued; responses return in order, with gaps, and are discarded when
#     CYC drops.
#   * burst checking: inside a burst, a request whose address is not the next
#     one for CTI/BTE gets ERR, as does a reserved CTI (011-110); neither
#     writes.
from _lib import wait_cb

SPEC = dict(
    vip="Wishbone-UVM-VIP", p="wishbone", P="Wishbone", dir="wishbone", family="Interconnect",
    desc="Wishbone B4 pipelined master VIP: STALL flow control, in-order ACK / ERR / RTY, SEL byte lanes, "
         "CTI / BTE registered-feedback bursts (constant, incrementing, wrap 4/8/16) and aborted cycles.",
    about="""
The DUT model is a pipelined Wishbone slave: memory, a busy device that answers RTY
before it accepts, and an error region. It stalls from an LFSR and when its
response queue is full, and checks that burst addresses follow CTI / BTE. The
scoreboard keeps its own memory and retry counters and predicts every response of
every request of a bus cycle. The SVA checks the B4 pipelined handshake: STB only
inside CYC, request held while STALL, one termination signal at a time, never
more responses than requests.""",
    timeout=200,
    ports=[
        ("in", "logic", "wb_cyc_i"), ("in", "logic", "wb_stb_i"), ("in", "logic", "wb_we_i"),
        ("in", "logic [31:0]", "wb_adr_i"), ("in", "logic [3:0]", "wb_sel_i"), ("in", "logic [31:0]", "wb_dat_i"),
        ("in", "logic [2:0]", "wb_cti_i"), ("in", "logic [1:0]", "wb_bte_i"),
        ("out", "logic", "wb_stall_o"), ("out", "logic", "wb_ack_o"), ("out", "logic", "wb_err_o"),
        ("out", "logic", "wb_rty_o"), ("out", "logic [31:0]", "wb_dat_o"),
    ],
    defs="""
typedef enum bit [1:0] { WB_CLASSIC = 0, WB_CONST = 1, WB_INCR = 2, WB_SINGLES = 3 } wb_mode_e;
typedef enum bit [1:0] { WB_INJ_NONE = 0, WB_INJ_ADDR = 1, WB_INJ_CTI = 2 } wb_inj_e;
// next address of an incrementing burst
function automatic bit [11:0] wb_next(bit [11:0] a, bit [1:0] bte);
  case (bte)
    2'd1: return {a[11:4], a[3:2] + 2'd1, 2'b00};
    2'd2: return {a[11:5], a[4:2] + 3'd1, 2'b00};
    2'd3: return {a[11:6], a[5:2] + 4'd1, 2'b00};
    default: return a + 12'd4;
  endcase
endfunction
""",
    fields=[
        ("bit", "we", "req"),
        ("bit [3:0]", "n", "req", "rand"),          # requests in the cycle
        ("wb_mode_e", "mode", "info", "rand"),
        ("bit [1:0]", "bte", "info", "rand"),
        ("bit [11:0]", "adr", "info", "rand"),      # first address
        ("bit [95:0]", "badr", "req"),              # address of request i at [12i+11:12i]
        ("bit [23:0]", "bcti", "req"),              # CTI of request i at [3i+2:3i]
        ("bit [31:0]", "sel", "req"),               # SEL of request i at [4i+3:4i]
        ("bit [255:0]", "wdat", "req"),
        ("bit [255:0]", "rdat", "rsp"),
        ("bit [15:0]", "rsp", "rsp"),               # request i: 0 ACK, 1 ERR, 2 RTY, 3 none (aborted)
        ("bit [3:0]", "nrsp", "rsp"),               # responses received before CYC dropped
        ("bit [2:0]", "gap", "info", "rand"),
        ("bit [7:0]", "bgap", "info", "rand"),      # an idle clock (STB low) before request i
        ("bit [3:0]", "abort_at", "info", "rand"),  # 0: no abort; k: drop CYC once k requests are accepted
        ("wb_inj_e", "inj", "info", "rand"),
        ("bit [2:0]", "inj_at", "info", "rand"),
        ("int unsigned", "stalls", "info"),         # clocks a request waited on STALL
    ],
    constraints="""
constraint c_n    { n inside {[1:8]}; mode == WB_CLASSIC -> n == 1; mode == WB_SINGLES -> n >= 2; }
constraint c_mode { mode dist { WB_CLASSIC := 2, WB_CONST := 1, WB_INCR := 4, WB_SINGLES := 2 }; }
constraint c_adr  { adr[1:0] == 2'b00; adr[11:8] dist { 4'h0 := 6, 4'h1 := 2, 4'h3 := 2, 4'h4 := 1, 4'h8 := 3, 4'hF := 1 };
                    adr[11:8] == 4'h8 -> adr[7:6] == 2'b00; }
constraint c_ab   { abort_at dist { 0 := 8, [1:8] :/ 1 }; abort_at <= n; }
constraint c_inj  { inj dist { WB_INJ_NONE := 8, WB_INJ_ADDR := 1, WB_INJ_CTI := 1 }; inj_at < n;
                    (mode == WB_CLASSIC || mode == WB_SINGLES) -> inj != WB_INJ_ADDR; }
constraint c_gap  { gap dist { 0 := 6, [1:7] :/ 2 }; }
""",
    drv_desc="one bus cycle per item: requests issued while STALL is low (optionally with idle clocks), "
             "responses counted until all are in or the cycle is aborted",
    drv_idle="""
vif.drv_cb.wb_cyc_i <= 1'b0; vif.drv_cb.wb_stb_i <= 1'b0; vif.drv_cb.wb_we_i <= 1'b0;
vif.drv_cb.wb_adr_i <= '0; vif.drv_cb.wb_sel_i <= '0; vif.drv_cb.wb_dat_i <= '0;
vif.drv_cb.wb_cti_i <= '0; vif.drv_cb.wb_bte_i <= '0;
""",
    drv_item="""
begin
  bit [11:0] a = t.adr;
  int unsigned sent = 0, got = 0, to = 0, n = (t.n == 0) ? 1 : t.n;
  bit req, gapped = 0;
  // addresses and CTI of every request; beats past n carry nothing
  t.badr = 0; t.bcti = 0; t.rdat = 0; t.rsp = 0; t.stalls = 0;
  for (int i = 0; i < 8; i++) begin
    if (i >= n) begin t.sel[4 * i +: 4] = 0; t.wdat[32 * i +: 32] = 0; t.bgap[i] = 0; continue; end
    t.badr[12 * i +: 12] = a;
    t.bcti[3 * i +: 3] = (t.mode == WB_CLASSIC || t.mode == WB_SINGLES) ? 3'b000 :
                         (i == n - 1) ? 3'b111 : (t.mode == WB_CONST) ? 3'b001 : 3'b010;
    if (t.inj == WB_INJ_ADDR && i == t.inj_at && i != 0) t.badr[12 * i +: 12] = a + 12'h40;
    if (t.inj == WB_INJ_CTI && i == t.inj_at) t.bcti[3 * i +: 3] = 3'b011 + (a[3:2] % 4);
    if (!t.we) begin t.sel[4 * i +: 4] = 4'hF; t.wdat[32 * i +: 32] = 0; end
    a = (t.mode == WB_CONST) ? a : (t.mode == WB_INCR) ? wb_next(a, t.bte) : a + 12'd4;
  end
  if (t.mode != WB_INCR) t.bte = 0;
  t.bgap[0] = 0;
  repeat (t.gap) @(vif.drv_cb);
  vif.drv_cb.wb_cyc_i <= 1'b1;
  while ((sent < n || got < sent) && to < cfg.timeout_cycles && !(t.abort_at != 0 && sent >= t.abort_at)) begin
    req = (sent < n);
    if (req && t.bgap[sent] && !gapped) begin req = 0; gapped = 1; end   // one idle clock before this request
    vif.drv_cb.wb_stb_i <= req;
    if (req) begin
      vif.drv_cb.wb_we_i <= t.we; vif.drv_cb.wb_adr_i <= {20'h0, t.badr[12 * sent +: 12]};
      vif.drv_cb.wb_sel_i <= t.sel[4 * sent +: 4]; vif.drv_cb.wb_dat_i <= t.wdat[32 * sent +: 32];
      vif.drv_cb.wb_cti_i <= t.bcti[3 * sent +: 3]; vif.drv_cb.wb_bte_i <= t.bte;
    end
    @(vif.drv_cb); to++;
    if (vif.drv_cb.wb_ack_o === 1'b1 || vif.drv_cb.wb_err_o === 1'b1 || vif.drv_cb.wb_rty_o === 1'b1) begin
      t.rsp[2 * got +: 2] = vif.drv_cb.wb_ack_o ? 2'd0 : vif.drv_cb.wb_err_o ? 2'd1 : 2'd2;
      t.rdat[32 * got +: 32] = vif.drv_cb.wb_dat_o;
      got++;
    end
    if (req) begin
      if (vif.drv_cb.wb_stall_o === 1'b0) begin sent++; gapped = 0; end
      else t.stalls++;
    end
  end
  if (to >= cfg.timeout_cycles) `uvm_error("TIMEOUT", "Wishbone: bus cycle did not complete")
  for (int i = got; i < 8; i++) t.rsp[2 * i +: 2] = (i < sent) ? 2'd3 : 2'd0;
  t.nrsp = got;
  // an aborted cycle carries only the requests that went out
  for (int i = sent; i < 8; i++) begin
    t.badr[12 * i +: 12] = 0; t.bcti[3 * i +: 3] = 0; t.sel[4 * i +: 4] = 0; t.wdat[32 * i +: 32] = 0;
  end
  t.n = sent;
  vif.drv_cb.wb_stb_i <= 1'b0; vif.drv_cb.wb_cyc_i <= 1'b0;
  @(vif.drv_cb);
end
""",
    mon_desc="one item per bus cycle: requests taken on STB without STALL, responses paired in order until CYC drops",
    mon_run="""
wishbone_transaction t;
int unsigned nreq = 0, waits = 0;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin t = null; nreq = 0; continue; end
  if (vif.mon_cb.wb_cyc_i) begin
    if (t == null) begin t = wishbone_transaction::type_id::create("t"); nreq = 0; waits = 0; end
    if (vif.mon_cb.wb_ack_o || vif.mon_cb.wb_err_o || vif.mon_cb.wb_rty_o) begin
      if (t.nrsp >= nreq) `uvm_error("MON", "Wishbone: response without an outstanding request")
      else begin
        t.rsp[2 * t.nrsp +: 2] = vif.mon_cb.wb_ack_o ? 2'd0 : vif.mon_cb.wb_err_o ? 2'd1 : 2'd2;
        t.rdat[32 * t.nrsp +: 32] = vif.mon_cb.wb_dat_o;
        t.nrsp++;
      end
    end
    if (vif.mon_cb.wb_stb_i) begin
      if (vif.mon_cb.wb_stall_o) waits++;
      else if (nreq < 8) begin
        t.we = vif.mon_cb.wb_we_i;
        t.badr[12 * nreq +: 12] = vif.mon_cb.wb_adr_i[11:0];
        t.bcti[3 * nreq +: 3] = vif.mon_cb.wb_cti_i;
        t.bte = vif.mon_cb.wb_bte_i;
        t.sel[4 * nreq +: 4] = vif.mon_cb.wb_sel_i;
        t.wdat[32 * nreq +: 32] = vif.mon_cb.wb_we_i ? vif.mon_cb.wb_dat_i : 32'h0;
        nreq++;
      end
    end
  end else if (t != null) begin
    t.n = nreq; t.stalls = waits;
    t.adr = t.badr[11:0];
    t.mode = (t.bcti[2:0] == 3'b001) ? WB_CONST : (t.bcti[2:0] == 3'b010) ? WB_INCR :
             (nreq > 1) ? WB_SINGLES : (t.bcti[2:0] == 3'b111 || t.bcti[2:0] == 3'b000) ? WB_CLASSIC : WB_SINGLES;
    if (t.mode != WB_INCR) t.bte = 0;
    for (int i = t.nrsp; i < 8; i++) t.rsp[2 * i +: 2] = (i < nreq) ? 2'd3 : 2'd0;
    publish(t);
    t = null;
  end
end
""",
    sb_members="""bit [31:0] mem  [256];   // reset value 0
bit [31:0] dev  [16];    // busy device behind RTY
bit [1:0]  tries[16];
function bit [1:0] region(bit [31:0] a);   // 0 memory, 1 busy device, 2 error
  if (a[31:10] == 0) return 0;
  if (a[31:6] == 26'h20) return 1;
  return 2;
endfunction""",
    pair_skip="t.n == 0",
    predict="""
begin
  bit bact = 0;
  bit [11:0] bnext = 0;
  for (int i = 0; i < t.n; i++) begin
    bit [11:0] a = t.badr[12 * i +: 12];
    bit [2:0]  c = t.bcti[3 * i +: 3];
    bit [1:0]  r;
    bit [31:0] d = 0;
    bit e = (c inside {[3'b011:3'b110]}) || (bact && a != bnext);
    bact = (c == 3'b001 || c == 3'b010);
    bnext = (c == 3'b001) ? a : wb_next(a, t.bte);
    if (e || region({20'h0, a}) == 2) r = 2'd1;
    else if (region({20'h0, a}) == 1) begin
      if (tries[a[5:2]] < 2) begin r = 2'd2; tries[a[5:2]]++; end
      else begin
        r = 2'd0; tries[a[5:2]] = 0;
        if (t.we) begin for (int b = 0; b < 4; b++) if (t.sel[4 * i + b]) dev[a[5:2]][8 * b +: 8] = t.wdat[32 * i + 8 * b +: 8]; end
        else d = dev[a[5:2]];
      end
    end else begin
      r = 2'd0;
      if (t.we) begin for (int b = 0; b < 4; b++) if (t.sel[4 * i + b]) mem[a[9:2]][8 * b +: 8] = t.wdat[32 * i + 8 * b +: 8]; end
      else d = mem[a[9:2]];
    end
    // a request whose response was dropped by the abort keeps the observed "none"
    if (i < t.nrsp) begin t.rsp[2 * i +: 2] = r; t.rdat[32 * i +: 32] = d; end
  end
end
""",
    checks="""
if (t.n == 0 || t.n > 8) fail(t, $sformatf("%0d requests in the bus cycle", t.n));
if (t.nrsp > t.n) fail(t, "more responses than requests");
for (int i = 0; i < t.n; i++) if (t.badr[12 * i +: 2] != 2'b00) fail(t, "unaligned word address");
if (t.stalls > 40) fail(t, $sformatf("requests waited %0d clocks on STALL", t.stalls));
""",
    coverage="""
cp_we    : coverpoint tr.we;
cp_mode  : coverpoint tr.mode iff (tr.n > 0);
cp_n     : coverpoint tr.n { bins one = {1}; bins few = {[2:4]}; bins many = {[5:7]}; bins max = {8}; }
cp_bte   : coverpoint tr.bte iff (tr.mode == WB_INCR) { bins linear = {0}; bins wrap4 = {1}; bins wrap8 = {2}; bins wrap16 = {3}; }
cp_rsp0  : coverpoint tr.rsp[1:0] iff (tr.nrsp > 0) { bins ack = {0}; bins err = {1}; bins rty = {2}; }
cp_abort : coverpoint (tr.nrsp < tr.n) { bins full = {0}; bins aborted = {1}; }
cp_sel   : coverpoint tr.sel[3:0] iff (tr.we) { bins full = {4'hF}; bins none = {0}; bins part = {[1:14]}; }
cp_stall : coverpoint tr.stalls { bins none = {0}; bins some = {[1:3]}; bins many = {[4:$]}; }
x_mode_we : cross cp_mode, cp_we;
x_bte_we  : cross cp_bte, cp_we;
""",
    directed="""
// every cycle type, then read back
t = item(); t.we = 1; t.mode = WB_CLASSIC; t.n = 1; t.adr = 12'h010; t.sel = 32'hF; t.wdat = 32'hCAFE_F00D; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
t = item(); t.we = 0; t.mode = WB_CLASSIC; t.n = 1; t.adr = 12'h010; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
for (int b = 0; b < 4; b++) begin
  t = item(); t.we = 1; t.mode = WB_INCR; t.bte = b; t.n = 8; t.adr = 12'h100 + 12'h40 * b + 12'h8; t.sel = '1;
  for (int i = 0; i < 8; i++) t.wdat[32 * i +: 32] = 32'h1000 * b + i;
  t.inj = WB_INJ_NONE; t.abort_at = 0; t.bgap = (b == 2) ? 8'b0101_0100 : 0; send(t);
  t = item(); t.we = 0; t.mode = WB_INCR; t.bte = b; t.n = 8; t.adr = 12'h100 + 12'h40 * b + 12'h8; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
end
t = item(); t.we = 1; t.mode = WB_CONST; t.n = 4; t.adr = 12'h200; t.sel = 32'h0000_8421; t.wdat = '1; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
t = item(); t.we = 0; t.mode = WB_SINGLES; t.n = 8; t.adr = 12'h1F8; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
t = item(); t.we = 0; t.mode = WB_CONST; t.n = 3; t.adr = 12'h200; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
t = item(); t.we = 1; t.mode = WB_CLASSIC; t.n = 1; t.adr = 12'h200; t.sel = 32'h0; t.wdat = 32'h1; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
// busy device: RTY, RTY, ACK
for (int k = 0; k < 3; k++) begin t = item(); t.we = 1; t.mode = WB_CLASSIC; t.n = 1; t.adr = 12'h804; t.sel = 32'hF; t.wdat = 32'h5EED; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t); end
t = item(); t.we = 0; t.mode = WB_SINGLES; t.n = 3; t.adr = 12'h804; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
// error region, burst errors, abort
t = item(); t.we = 0; t.mode = WB_SINGLES; t.n = 4; t.adr = 12'h3F8; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
t = item(); t.we = 1; t.mode = WB_INCR; t.bte = 0; t.n = 6; t.adr = 12'h300; t.sel = '1; t.wdat = '1; t.inj = WB_INJ_ADDR; t.inj_at = 3; t.abort_at = 0; send(t);
t = item(); t.we = 0; t.mode = WB_INCR; t.bte = 1; t.n = 4; t.adr = 12'h300; t.inj = WB_INJ_CTI; t.inj_at = 1; t.abort_at = 0; send(t);
t = item(); t.we = 1; t.mode = WB_INCR; t.bte = 0; t.n = 8; t.adr = 12'h380; t.sel = '1; t.wdat = '1; t.inj = WB_INJ_NONE; t.abort_at = 3; send(t);
t = item(); t.we = 0; t.mode = WB_INCR; t.bte = 0; t.n = 8; t.adr = 12'h380; t.inj = WB_INJ_NONE; t.abort_at = 0; send(t);
""",
    drain_ns=3000,
    model="""
module wishbone_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        wb_cyc_i,
  input  logic        wb_stb_i,
  input  logic        wb_we_i,
  input  logic [31:0] wb_adr_i,
  input  logic [3:0]  wb_sel_i,
  input  logic [31:0] wb_dat_i,
  input  logic [2:0]  wb_cti_i,
  input  logic [1:0]  wb_bte_i,
  output logic        wb_stall_o,
  output logic        wb_ack_o,
  output logic        wb_err_o,
  output logic        wb_rty_o,
  output logic [31:0] wb_dat_o
);
  logic [31:0] mem [0:255];
  logic [31:0] dev [0:15];
  logic [1:0]  tries [0:15];
  // response queue: {kind (0 ACK, 1 ERR, 2 RTY), data}
  logic [1:0]  q_k [0:3];
  logic [31:0] q_d [0:3];
  logic [1:0]  wp, rp;
  logic [2:0]  cnt;
  logic [7:0]  lfsr;
  logic        bact;             // inside a CTI burst
  logic [11:0] bnext;            // the address the burst must use next
  logic        acc, give, bad;
  logic [1:0]  kind;
  logic [31:0] rd;
  logic [1:0]  reg_;
  logic        ack_q, err_q, rty_q;
  logic [31:0] dat_q;

  function automatic logic [11:0] nxt(input logic [11:0] a, input logic [1:0] bte);
    case (bte)
      2'd1: nxt = {a[11:4], a[3:2] + 2'd1, 2'b00};
      2'd2: nxt = {a[11:5], a[4:2] + 3'd1, 2'b00};
      2'd3: nxt = {a[11:6], a[5:2] + 4'd1, 2'b00};
      default: nxt = a + 12'd4;
    endcase
  endfunction

  // registered terminations, qualified with CYC so that none is seen after the master drops it
  assign wb_ack_o = ack_q && wb_cyc_i;
  assign wb_err_o = err_q && wb_cyc_i;
  assign wb_rty_o = rty_q && wb_cyc_i;
  assign wb_dat_o = wb_cyc_i ? dat_q : 32'h0;
  assign wb_stall_o = rst_n && wb_cyc_i && wb_stb_i && (lfsr[1:0] == 2'b00 || cnt == 3'd4);
  assign acc  = wb_cyc_i && wb_stb_i && !wb_stall_o;
  assign give = wb_cyc_i && cnt != 3'd0 && !lfsr[4];
  assign bad  = (wb_cti_i >= 3'b011 && wb_cti_i <= 3'b110) || (bact && wb_adr_i[11:0] != bnext);
  assign reg_ = (wb_adr_i[31:10] == 22'h0) ? 2'd0 : (wb_adr_i[31:6] == 26'h20) ? 2'd1 : 2'd2;

  always_comb begin
    kind = 2'd0; rd = 32'h0;
    if (bad || reg_ == 2'd2) kind = 2'd1;
    else if (reg_ == 2'd1) begin
      if (tries[wb_adr_i[5:2]] != 2'd2) kind = 2'd2;
      else if (!wb_we_i) rd = dev[wb_adr_i[5:2]];
    end else if (!wb_we_i) rd = mem[wb_adr_i[9:2]];
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 256; i++) mem[i] <= 32'h0;
      for (int i = 0; i < 16; i++) begin dev[i] <= 32'h0; tries[i] <= 2'd0; end
      for (int i = 0; i < 4; i++) begin q_k[i] <= 2'd0; q_d[i] <= 32'h0; end
      wp <= 2'd0; rp <= 2'd0; cnt <= 3'd0; lfsr <= 8'hC3; bact <= 1'b0; bnext <= 12'h0;
      ack_q <= 1'b0; err_q <= 1'b0; rty_q <= 1'b0; dat_q <= 32'h0;
    end else begin
      lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
      ack_q <= 1'b0; err_q <= 1'b0; rty_q <= 1'b0; dat_q <= 32'h0;
      if (!wb_cyc_i) begin
        // CYC low ends the bus cycle: queued responses are dropped, the burst is over
        cnt <= 3'd0; rp <= wp; bact <= 1'b0;
      end else begin
        if (acc) begin
          q_k[wp] <= kind; q_d[wp] <= rd; wp <= wp + 2'd1;
          bact  <= (wb_cti_i == 3'b001 || wb_cti_i == 3'b010);
          bnext <= (wb_cti_i == 3'b001) ? wb_adr_i[11:0] : nxt(wb_adr_i[11:0], wb_bte_i);
          if (kind == 2'd2) tries[wb_adr_i[5:2]] <= tries[wb_adr_i[5:2]] + 2'd1;
          else if (!bad && reg_ == 2'd1) tries[wb_adr_i[5:2]] <= 2'd0;
          if (kind == 2'd0 && wb_we_i)
            for (int b = 0; b < 4; b++) if (wb_sel_i[b]) begin
              if (reg_ == 2'd1) dev[wb_adr_i[5:2]][8 * b +: 8] <= wb_dat_i[8 * b +: 8];
              else mem[wb_adr_i[9:2]][8 * b +: 8] <= wb_dat_i[8 * b +: 8];
            end
        end
        if (give) begin
          ack_q <= (q_k[rp] == 2'd0); err_q <= (q_k[rp] == 2'd1); rty_q <= (q_k[rp] == 2'd2);
          dat_q <= q_d[rp]; rp <= rp + 2'd1;
        end
        cnt <= cnt + {2'b0, acc} - {2'b0, give};
      end
    end
  end
endmodule
""",
    sva="""
logic [3:0] outst;      // accepted requests not yet answered in this bus cycle
always @(posedge clk or negedge rst_n)
  if (!rst_n) outst <= 4'd0;
  else if (!wb_cyc_i) outst <= 4'd0;
  else outst <= outst + (wb_stb_i && !wb_stall_o) - (wb_ack_o || wb_err_o || wb_rty_o);
// no X on the slave's outputs out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({wb_stall_o, wb_ack_o, wb_err_o, wb_rty_o}))
  else $error("Wishbone: X on STALL / ACK / ERR / RTY");
assert property (@(posedge clk) disable iff (!rst_n) wb_ack_o |-> !$isunknown(wb_dat_o))
  else $error("Wishbone: X on DAT_O with ACK");
// master rules
assert property (@(posedge clk) disable iff (!rst_n) wb_stb_i |-> wb_cyc_i)
  else $error("Wishbone: STB outside CYC");
assert property (@(posedge clk) disable iff (!rst_n) wb_stb_i && wb_stall_o |=>
                 wb_stb_i && $stable({wb_we_i, wb_adr_i, wb_sel_i, wb_dat_i, wb_cti_i, wb_bte_i}) || !wb_cyc_i)
  else $error("Wishbone: request changed while STALL");
// slave rules
assert property (@(posedge clk) disable iff (!rst_n) $onehot0({wb_ack_o, wb_err_o, wb_rty_o}))
  else $error("Wishbone: more than one of ACK / ERR / RTY");
assert property (@(posedge clk) disable iff (!rst_n) (wb_ack_o || wb_err_o || wb_rty_o) |-> wb_cyc_i && outst != 0)
  else $error("Wishbone: termination without an outstanding request");
cover property (@(posedge clk) disable iff (!rst_n) wb_stb_i && wb_stall_o ##1 wb_stb_i && !wb_stall_o);
cover property (@(posedge clk) disable iff (!rst_n) wb_rty_o);
cover property (@(posedge clk) disable iff (!rst_n) wb_cyc_i && outst != 0 ##1 !wb_cyc_i);
cover property (@(posedge clk) disable iff (!rst_n) wb_stb_i && wb_cti_i == 3'b010 && wb_bte_i == 2'd3);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic wb_cyc_i = 0, wb_stb_i = 0, wb_we_i = 0;
logic [31:0] wb_adr_i = 0, wb_dat_i = 0;
logic [3:0] wb_sel_i = 4'hF;
logic [2:0] wb_cti_i = 0;
logic [1:0] wb_bte_i = 0;
wire wb_stall_o, wb_ack_o, wb_err_o, wb_rty_o;
wire [31:0] wb_dat_o;

always #5 clk = ~clk;

wishbone_model u_dut (.clk(clk), .rst_n(rst_n), .wb_cyc_i(wb_cyc_i), .wb_stb_i(wb_stb_i), .wb_we_i(wb_we_i),
                      .wb_adr_i(wb_adr_i), .wb_sel_i(wb_sel_i), .wb_dat_i(wb_dat_i), .wb_cti_i(wb_cti_i),
                      .wb_bte_i(wb_bte_i), .wb_stall_o(wb_stall_o), .wb_ack_o(wb_ack_o), .wb_err_o(wb_err_o),
                      .wb_rty_o(wb_rty_o), .wb_dat_o(wb_dat_o));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// response log
logic [1:0]  r_k [0:255];
logic [31:0] r_d [0:255];
int nr = 0, nstall = 0, nacc = 0;
always @(posedge clk) begin
  if (wb_ack_o || wb_err_o || wb_rty_o) begin
    r_k[nr % 256] = wb_ack_o ? 0 : wb_err_o ? 1 : 2; r_d[nr % 256] = wb_dat_o; nr++;
  end
  if (wb_stb_i && wb_stall_o) nstall++;
  if (wb_stb_i && wb_cyc_i && !wb_stall_o) nacc++;
end

task automatic idle(input int n); repeat (n) @(negedge clk); endtask
// one request, held until a clock without STALL
task automatic rq(input logic w, input logic [31:0] a, input logic [3:0] s, input logic [31:0] d,
                  input logic [2:0] c, input logic [1:0] b);
  bit st;
  wb_stb_i = 1; wb_we_i = w; wb_adr_i = a; wb_sel_i = s; wb_dat_i = d; wb_cti_i = c; wb_bte_i = b;
  do begin @(posedge clk); st = wb_stall_o; @(negedge clk); end while (st);
  wb_stb_i = 0;
endtask
int r0;
task automatic wait_rsp(input int k);
  int t = 0;
  while (nr < r0 + k && t < 200) begin @(negedge clk); t++; end
  chk(nr >= r0 + k, $sformatf("%0d responses", k));
endtask
task automatic cyc_on(); wb_cyc_i = 1; r0 = nr; endtask
task automatic cyc_off(input int k); wait_rsp(k); wb_cyc_i = 0; idle(1); endtask
// a whole classic single cycle
task automatic single(input logic w, input logic [31:0] a, input logic [3:0] s, input logic [31:0] d);
  cyc_on(); rq(w, a, s, d, 3'b000, 2'b00); cyc_off(1);
endtask

initial begin
  idle(3);
  chk(!wb_ack_o && !wb_err_o && !wb_rty_o && wb_dat_o == 0, "quiet in reset");
  wb_cyc_i = 1; wb_stb_i = 1; #1; chk(!wb_stall_o, "no STALL in reset"); wb_cyc_i = 0; wb_stb_i = 0;
  @(negedge clk); rst_n = 1; idle(2);
  wb_stb_i = 1; #1; chk(!wb_stall_o, "no STALL without CYC"); wb_stb_i = 0;

  single(1, 32'h010, 4'hF, 32'hCAFE_F00D);
  chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 0, "write: ACK, DAT_O 0");
  single(0, 32'h010, 4'hF, 0);
  chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 32'hCAFE_F00D, "read back");
  single(1, 32'h010, 4'h2, 32'h0000_AB00); single(1, 32'h010, 4'h8, 32'h7700_0000); single(1, 32'h010, 4'h0, 32'hFFFF_FFFF);
  single(0, 32'h010, 4'h0, 0);
  chk(r_d[r0 % 256] == 32'h77FE_AB0D, $sformatf("SEL byte lanes (%h)", r_d[r0 % 256]));
  single(1, 32'h3FC, 4'hF, 32'h1357); single(0, 32'h3FC, 4'hF, 0);
  chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 32'h1357, "0x3FC is memory");
  single(0, 32'h014, 4'hF, 0);
  chk(r_d[r0 % 256] == 0, "neighbour still 0");

  // error region and the 32-bit decode
  single(0, 32'h400, 4'hF, 0); chk(r_k[r0 % 256] == 1 && r_d[r0 % 256] == 0, "0x400: ERR");
  single(1, 32'h7FC, 4'hF, 32'h1); chk(r_k[r0 % 256] == 1, "0x7FC: ERR");
  single(0, 32'h840, 4'hF, 0); chk(r_k[r0 % 256] == 1, "0x840 (past the device): ERR");
  single(0, 32'h1000, 4'hF, 0); chk(r_k[r0 % 256] == 1, "0x1000 (ADR above bit 11): ERR");
  single(0, 32'h1000_0010, 4'hF, 0); chk(r_k[r0 % 256] == 1, "upper ADR bits decoded");
  single(0, 32'h010, 4'hF, 0); chk(r_d[r0 % 256] == 32'h77FE_AB0D, "error-region accesses wrote nothing");

  // busy device: RTY, RTY, ACK per word
  single(1, 32'h804, 4'hF, 32'h5EED); chk(r_k[r0 % 256] == 2, "busy device: first try RTY");
  single(1, 32'h804, 4'hF, 32'h5EED); chk(r_k[r0 % 256] == 2, "second try RTY");
  single(0, 32'h808, 4'hF, 0); chk(r_k[r0 % 256] == 2, "another word counts its own tries");
  single(1, 32'h804, 4'hF, 32'h5EED); chk(r_k[r0 % 256] == 0, "third try ACK");
  single(0, 32'h804, 4'hF, 0); chk(r_k[r0 % 256] == 2, "the count restarts after an ACK");
  single(0, 32'h804, 4'hF, 0); single(0, 32'h804, 4'hF, 0);
  chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 32'h5EED, "device word written once accepted");
  single(0, 32'h808, 4'hF, 0); single(0, 32'h808, 4'hF, 0);
  chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 0, "RTY attempts wrote nothing");
  single(1, 32'h83C, 4'h1, 32'hAA); single(1, 32'h83C, 4'h1, 32'hAA); single(1, 32'h83C, 4'h1, 32'hAA);
  single(0, 32'h83C, 4'hF, 0); single(0, 32'h83C, 4'hF, 0); single(0, 32'h83C, 4'hF, 0);
  chk(r_d[r0 % 256] == 32'hAA, "last device word, SEL lane 0");
  single(0, 32'h03C, 4'hF, 0); chk(r_d[r0 % 256] == 0, "device word does not alias memory");
  // a request rejected for its CTI is not a try and does not restart the count
  single(0, 32'h820, 4'hF, 0); chk(r_k[r0 % 256] == 2, "device word 8: first try RTY");
  cyc_on(); rq(0, 32'h820, 4'hF, 0, 3'b100, 2'd0); cyc_off(1); chk(r_k[r0 % 256] == 1, "reserved CTI to the device: ERR");
  single(0, 32'h820, 4'hF, 0); chk(r_k[r0 % 256] == 2, "second try RTY");
  single(0, 32'h820, 4'hF, 0); chk(r_k[r0 % 256] == 0, "third try ACK: the ERR did not count");

  // pipelined incrementing burst, 8 requests, linear
  cyc_on();
  for (int i = 0; i < 8; i++) rq(1, 32'h100 + 4 * i, 4'hF, 32'h11 * (i + 1), (i == 7) ? 3'b111 : 3'b010, 2'd0);
  cyc_off(8);
  begin bit ok = 1; for (int i = 0; i < 8; i++) if (r_k[(r0 + i) % 256] != 0) ok = 0; chk(ok, "8 ACKs for the linear burst"); end
  cyc_on();
  for (int i = 0; i < 8; i++) rq(0, 32'h100 + 4 * i, 4'hF, 0, (i == 7) ? 3'b111 : 3'b010, 2'd0);
  cyc_off(8);
  begin bit ok = 1; for (int i = 0; i < 8; i++) if (r_d[(r0 + i) % 256] != 32'h11 * (i + 1) || r_k[(r0 + i) % 256] != 0) ok = 0;
        chk(ok, "8 read beats in order"); end
  // wrap-4 from the third word: 0x188, 0x18C, 0x180, 0x184
  cyc_on();
  rq(0, 32'h188, 4'hF, 0, 3'b010, 2'd1); rq(0, 32'h18C, 4'hF, 0, 3'b010, 2'd1);
  rq(0, 32'h180, 4'hF, 0, 3'b010, 2'd1); rq(0, 32'h184, 4'hF, 0, 3'b111, 2'd1);
  cyc_off(4);
  begin bit ok = 1; for (int i = 0; i < 4; i++) if (r_k[(r0 + i) % 256] != 0) ok = 0; chk(ok, "wrap-4 burst accepted"); end
  cyc_on();
  rq(0, 32'h188, 4'hF, 0, 3'b010, 2'd1); rq(0, 32'h18C, 4'hF, 0, 3'b010, 2'd1); rq(0, 32'h190, 4'hF, 0, 3'b111, 2'd1);
  cyc_off(3);
  chk(r_k[r0 % 256] == 0 && r_k[(r0 + 1) % 256] == 0 && r_k[(r0 + 2) % 256] == 1, "wrap-4 without the wrap: ERR");
  // wrap-8: 0x11C -> 0x100; wrap-16: 0x13C -> 0x100
  cyc_on(); rq(0, 32'h118, 4'hF, 0, 3'b010, 2'd2); rq(0, 32'h11C, 4'hF, 0, 3'b010, 2'd2); rq(0, 32'h100, 4'hF, 0, 3'b111, 2'd2); cyc_off(3);
  chk(r_k[(r0 + 2) % 256] == 0 && r_d[(r0 + 2) % 256] == 32'h11 && r_d[(r0 + 1) % 256] == 32'h88, "wrap-8 back to 0x100");
  cyc_on(); rq(0, 32'h13C, 4'hF, 0, 3'b010, 2'd3); rq(0, 32'h100, 4'hF, 0, 3'b111, 2'd3); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 0, "wrap-16 back to 0x100");
  cyc_on(); rq(0, 32'h13C, 4'hF, 0, 3'b010, 2'd2); rq(0, 32'h120, 4'hF, 0, 3'b111, 2'd2); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 0, "wrap-8 from 0x13C wraps to 0x120");
  cyc_on(); rq(0, 32'h13C, 4'hF, 0, 3'b010, 2'd0); rq(0, 32'h140, 4'hF, 0, 3'b111, 2'd0); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 0, "linear crosses 0x140");
  cyc_on(); rq(0, 32'h13C, 4'hF, 0, 3'b010, 2'd0); rq(0, 32'h100, 4'hF, 0, 3'b111, 2'd0); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 1, "linear does not wrap: ERR");
  // constant-address burst
  cyc_on(); for (int i = 0; i < 4; i++) rq(1, 32'h200, 4'h1 << i, 32'hFFFF_FFFF, (i == 3) ? 3'b111 : 3'b001, 2'd0); cyc_off(4);
  single(0, 32'h200, 4'hF, 0); chk(r_d[r0 % 256] == 32'hFFFF_FFFF, "constant burst: four lanes into one word");
  cyc_on(); rq(0, 32'h200, 4'hF, 0, 3'b001, 2'd0); rq(0, 32'h204, 4'hF, 0, 3'b111, 2'd0); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 1, "constant burst with a new address: ERR");
  // a burst address error writes nothing and the burst goes on from the received address
  cyc_on(); rq(1, 32'h220, 4'hF, 32'h1, 3'b010, 2'd0); rq(1, 32'h230, 4'hF, 32'h2, 3'b010, 2'd0);
  rq(1, 32'h234, 4'hF, 32'h3, 3'b111, 2'd0); cyc_off(3);
  chk(r_k[r0 % 256] == 0 && r_k[(r0 + 1) % 256] == 1 && r_k[(r0 + 2) % 256] == 0, "ERR on the jump, the next request follows it");
  single(0, 32'h230, 4'hF, 0); chk(r_d[r0 % 256] == 0, "the ERR request wrote nothing");
  single(0, 32'h234, 4'hF, 0); chk(r_d[r0 % 256] == 32'h3, "the request after it was written");
  // end of burst, classic after a burst, reserved CTI
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b010, 2'd0); rq(0, 32'h104, 4'hF, 0, 3'b111, 2'd0); rq(0, 32'h300, 4'hF, 0, 3'b000, 2'd0); cyc_off(3);
  chk(r_k[(r0 + 2) % 256] == 0, "after end-of-burst any address is fine");
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b000, 2'd0); rq(0, 32'h300, 4'hF, 0, 3'b000, 2'd0); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 0, "classic requests are not a burst");
  for (int c = 3; c <= 6; c++) begin
    cyc_on(); rq(1, 32'h240, 4'hF, 32'h99, c[2:0], 2'd0); cyc_off(1);
    chk(r_k[r0 % 256] == 1, $sformatf("reserved CTI %0d: ERR", c));
  end
  single(0, 32'h240, 4'hF, 0); chk(r_d[r0 % 256] == 0, "reserved-CTI writes landed nowhere");
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b111, 2'd0); rq(0, 32'h300, 4'hF, 0, 3'b111, 2'd0); cyc_off(2);
  chk(r_k[r0 % 256] == 0 && r_k[(r0 + 1) % 256] == 0, "end-of-burst alone is a single");
  // the burst state ends with CYC
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b010, 2'd0); cyc_off(1);
  cyc_on(); rq(0, 32'h300, 4'hF, 0, 3'b111, 2'd0); cyc_off(1);
  chk(r_k[r0 % 256] == 0, "a new bus cycle starts outside any burst");

  // four outstanding, STALL while full
  begin : full
    int acc = 0, early = 0, t = 0;
    cyc_on(); wb_stb_i = 1; wb_we_i = 0; wb_adr_i = 32'h100; wb_cti_i = 3'b000;
    while (acc < 6 && t < 100) begin
      #4; if (!wb_stall_o) begin acc++; if (acc == 5 && nr == r0) early = 1; end
      @(negedge clk); t++;
    end
    wb_stb_i = 0;
    chk(!early, "no fifth request accepted before a response");
    cyc_off(6);
    chk(nr == r0 + 6, "six responses for six requests");
  end
  // abort: CYC dropped with responses outstanding
  cyc_on();
  for (int i = 0; i < 4; i++) rq(1, 32'h2C0 + 4 * i, 4'hF, 32'hAB0 + i, (i == 3) ? 3'b111 : 3'b010, 2'd0);
  wb_cyc_i = 0; idle(1);
  begin int n1; n1 = nr; idle(10); chk(nr == n1, "no response after CYC drops"); end
  cyc_on(); for (int i = 0; i < 4; i++) rq(0, 32'h2C0 + 4 * i, 4'hF, 0, (i == 3) ? 3'b111 : 3'b010, 2'd0); cyc_off(4);
  chk(r_d[r0 % 256] == 32'hAB0 && r_d[(r0 + 3) % 256] == 32'hAB3, "aborted writes were performed when accepted");
  chk(r_k[r0 % 256] == 0 && nr == r0 + 4, "the next cycle gets only its own responses");
  // gaps: STB low between requests of a burst
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b010, 2'd0); idle(3); rq(0, 32'h104, 4'hF, 0, 3'b111, 2'd0); cyc_off(2);
  chk(r_k[(r0 + 1) % 256] == 0 && r_d[(r0 + 1) % 256] == 32'h22, "idle clocks inside a burst");
  // wait states: the LFSR pattern
  chk(nstall == 32 && nacc == 111, $sformatf("STALL pattern: %0d stalls for %0d requests", nstall, nacc));

  // reset clears memory, device, retry counts and the queue
  single(1, 32'h000, 4'hF, 32'h600D);
  single(1, 32'h800, 4'hF, 32'hD0D0); single(1, 32'h800, 4'hF, 32'hD0D0); single(1, 32'h800, 4'hF, 32'hD0D0);
  single(0, 32'h800, 4'hF, 0); chk(r_k[r0 % 256] == 2, "device word 0: one try counted before the reset");
  cyc_on(); rq(0, 32'h100, 4'hF, 0, 3'b000, 2'd0);
  @(negedge clk); rst_n = 0; idle(2);
  chk(!wb_ack_o && !wb_err_o && !wb_rty_o, "reset clears the responses");
  wb_cyc_i = 0; rst_n = 1; idle(2);
  single(0, 32'h100, 4'hF, 0); chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 0, "memory cleared");
  single(0, 32'h808, 4'hF, 0); chk(r_k[r0 % 256] == 2, "retry count cleared");
  single(0, 32'h000, 4'hF, 0); chk(r_d[r0 % 256] == 0, "word 0 cleared");
  single(0, 32'h800, 4'hF, 0); chk(r_k[r0 % 256] == 2, "device word 0: count cleared, first try RTY");
  single(0, 32'h800, 4'hF, 0); chk(r_k[r0 % 256] == 2, "device word 0: second try RTY");
  single(0, 32'h800, 4'hF, 0); chk(r_k[r0 % 256] == 0 && r_d[r0 % 256] == 0, "device word 0 cleared");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #500000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
    ral=dict(
        n_regs=16,
        desc="wishbone_model memory words 0..15 (ADR 0x00-0x3C), reset 0",
        reg2bus="""
t.we       = (rw.kind == UVM_WRITE);
t.adr      = rw.addr[11:0];
t.n        = 1;
t.mode     = WB_CLASSIC;
t.bte      = 0;
t.sel      = 32'hF;
t.wdat     = t.we ? {224'h0, rw.data[31:0]} : 256'h0;
t.inj      = WB_INJ_NONE;
t.abort_at = 0;
""",
        bus2reg="""
rw.kind   = t.we ? UVM_WRITE : UVM_READ;
rw.addr   = t.badr[11:0];
rw.data   = t.we ? t.wdat[31:0] : t.rdat[31:0];
rw.status = (t.rsp[1:0] == 2'd0) ? UVM_IS_OK : UVM_NOT_OK;
""",
    ),
)
