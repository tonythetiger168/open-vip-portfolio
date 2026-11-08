# V-by-One HS panel sink VIP (TV TCON -> panel link), at the symbol level
# (8b/10b and the serialiser are abstracted: each lane carries an 8-bit
# symbol and its K flag).
#
# Link rules (as implemented by TCON_VbyOne_top in open-ip-portfolio):
#   * vbo_sym is high on the first clock of each symbol; a new symbol comes
#     every SYM_DIV clocks, so the sink samples the lanes when vbo_sym = 1.
#   * While vbo_htpdn_n or vbo_lockn_n is high every lane sends the CDR
#     training pattern D10.2 (8'h4A, k = 0). Locked and idle: K28.5 (8'hBC).
#   * Each line starts with one control symbol on all lanes: K28.2 (8'h5C)
#     before line 0 of a frame, K28.0 (8'h1C) before every other line.
#   * 4-byte mode: pixel p of a line goes on lane p % LANES, byte j (bits
#     8j+7:8j of the 32-bit pixel word) in symbol j of the group; a partial last
#     group is padded with zero words; an underrun inserts K28.5 between groups.
# The panel (this agent) pulls vbo_htpdn_n low when connected and vbo_lockn_n
# low once it has seen cfg.train_syms training symbols; an item may drop the
# lock first, so the transmitter trains again. The panel knows its line width
# (cfg.h_active). To make the bench self-contained the agent also drives the
# transmitter's pixel input (pix_*), one line per item; in a SoC bench those
# pins are left to the display pipeline and the monitor is used passively.
#
# tb/top_tb.sv vbo_model: the transmitter (LANES = 8, SYM_DIV = 2) with a
# one-line pixel buffer. DUT -> agent: the lanes; the monitor decodes every
# line (control symbol, groups, fillers, padding) like the panel does.

SPEC = dict(
    vip="VbyOne_HS-UVM-VIP", p="vbo", P="VbyOne", dir="vbo", family="Video",
    desc="V-by-One HS panel sink VIP (symbol level, 8 lanes, 4-byte mode): HTPDN / LOCKN handshake with CDR training, "
         "K28.2 / K28.0 line control symbols, pixel groups with zero padding and K28.5 underrun fillers; transmitter model "
         "matching the open-ip TCON.",
    about="""
A TV's timing controller drives the panel over V-by-One HS: 8 or 16 lanes
that train (CDR pattern until the panel's LOCKN goes low), then carry pixels
distributed across the lanes, a control symbol at the start of each line and
fill symbols when the source runs dry. This agent is the panel: it drives
HTPDN / LOCKN, locks after the training pattern, drops and re-acquires the
lock on request, and its monitor decodes every line from the lanes (line /
frame start, the pixel groups of `cfg.h_active` pixels, padding, fillers),
checking that K symbols agree on all lanes, that fillers only sit between
groups and that padding is zero. For a self-contained bench the agent also
feeds the transmitter model's pixel port (with input gaps that force
underruns); the scoreboard checks each decoded line against the pixels that
went in. Pins match TCON_VbyOne_top in open-ip-portfolio.""",
    timeout=4000,
    cfg="""int unsigned h_active   = 12;   // pixels per line (a partial last group of 4 with LANES = 8)
int unsigned lanes      = 8;    // model parameter LANES
int unsigned train_syms = 8;    // training symbols the panel waits for before LOCKN low
int unsigned line_wait  = 200;  // clocks after the last pixel for the line to leave the link""",
    ports=[
        ("in", "logic", "pix_valid"), ("in", "logic", "pix_sol"), ("in", "logic", "pix_sof"), ("in", "logic", "pix_eol"),
        ("in", "logic [31:0]", "pix_data"), ("in", "logic", "vbo_htpdn_n"), ("in", "logic", "vbo_lockn_n"),
        ("out", "logic [7:0][7:0]", "vbo_lane_d"), ("out", "logic [7:0]", "vbo_lane_k"), ("out", "logic", "vbo_sym"),
    ],
    fields=[
        ("bit [31:0]", "pix", "req", "q"),
        ("bit", "sof", "req", "norand"),
        ("bit [31:0]", "rpix", "rsp", "q"),
        ("bit", "rsof", "rsp"),
        ("bit", "rpad", "rsp"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("int unsigned", "nfill", "info"),
        ("int unsigned", "ntrain", "info"),
    ],
    tr_functions="""
// kind: 0-3 frame start, 4-7 pixel gaps (underruns), 8 drop and re-acquire the
// lock first, 9 all-zero pixels, 10 all-one pixels, 11-31 plain lines
function void set(int k, bit [31:0] s = 1); kind = k; seed = s; endfunction
function bit relock(); return kind == 8; endfunction
function void build(int unsigned n);
  bit [31:0] x = seed | 1;
  sof = (kind inside {[0:3]});
  pix.delete();
  for (int i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    pix.push_back((kind == 9) ? 32'h0 : (kind == 10) ? 32'hFFFF_FFFF : x);
  end
endfunction
""",
    drv_rsp=False,
    drv_desc="one line of pixels per item into the transmitter (random gaps for kinds 4-7), after the HTPDN / LOCKN handshake (again for a relock item); then waits for the line to leave the link",
    drv_members="bit locked = 0;",
    drv_idle="""
vif.drv_cb.pix_valid   <= 1'b0;
vif.drv_cb.pix_sol     <= 1'b0;
vif.drv_cb.pix_sof     <= 1'b0;
vif.drv_cb.pix_eol     <= 1'b0;
vif.drv_cb.pix_data    <= '0;
vif.drv_cb.vbo_htpdn_n <= 1'b0;
vif.drv_cb.vbo_lockn_n <= 1'b1;
""",
    drv_item="""
bit [31:0] x = t.seed ^ 32'h5bd1_e995;
t.build(cfg.h_active);
@(vif.drv_cb);
if (t.relock() && locked) begin
  vif.drv_cb.vbo_lockn_n <= 1'b1;
  locked = 0;
  repeat (8) @(vif.drv_cb);
end
if (!locked) begin
  int n = 0, to = 0;
  vif.drv_cb.vbo_lockn_n <= 1'b1;
  while (n < cfg.train_syms && to < cfg.timeout_cycles) begin
    @(vif.drv_cb); to++;
    if (vif.drv_cb.vbo_sym) n = training() ? n + 1 : 0;
  end
  if (n < cfg.train_syms) `uvm_error("DRV", "VbyOne: no CDR training pattern")
  vif.drv_cb.vbo_lockn_n <= 1'b0;
  locked = 1;
  repeat (16) @(vif.drv_cb);
end
foreach (t.pix[i]) begin
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  if (t.kind inside {[4:7]} && x[1:0] == 0) begin
    vif.drv_cb.pix_valid <= 1'b0; vif.drv_cb.pix_sol <= 1'b0; vif.drv_cb.pix_sof <= 1'b0; vif.drv_cb.pix_eol <= 1'b0;
    repeat (2 + x[5:2]) @(vif.drv_cb);
  end
  vif.drv_cb.pix_valid <= 1'b1; vif.drv_cb.pix_data <= t.pix[i];
  vif.drv_cb.pix_sol <= (i == 0); vif.drv_cb.pix_sof <= t.sof && (i == 0);
  vif.drv_cb.pix_eol <= (i == t.pix.size() - 1);
  @(vif.drv_cb);
end
vif.drv_cb.pix_valid <= 1'b0; vif.drv_cb.pix_sol <= 1'b0; vif.drv_cb.pix_sof <= 1'b0; vif.drv_cb.pix_eol <= 1'b0;
repeat (cfg.line_wait) @(vif.drv_cb);
""",
    drv_tasks="""
function bit training();
  for (int l = 0; l < cfg.lanes; l++)
    if (vif.drv_cb.vbo_lane_k[l] !== 1'b0 || vif.drv_cb.vbo_lane_d[l] !== 8'h4A) return 0;
  return 1;
endfunction
""",
    mon_desc="the pixel lines into the transmitter, and every line the panel decodes from the lanes (control symbol, groups of 4 symbols, K28.5 fillers, zero padding)",
    mon_run="""
bit [31:0] in_l[$][$];
bit in_s[$];
bit [31:0] cur[$];
bit cur_s = 0;
int st = 0, g = 0, j = 0, ng = 0, ntr = 0;
bit [31:0] grp[8];
vbo_transaction t;
forever begin
  @(vif.mon_cb);
  // transmitter input
  if (vif.mon_cb.pix_valid) begin
    if (vif.mon_cb.pix_sol) begin cur.delete(); cur_s = vif.mon_cb.pix_sof; end
    cur.push_back(vif.mon_cb.pix_data);
    if (vif.mon_cb.pix_eol) begin in_l.push_back(cur); in_s.push_back(cur_s); end
  end
  if (!vif.mon_cb.vbo_sym) continue;
  // panel side: one symbol on every lane
  begin
    bit allk = 1, anyk = 0, same = 1;
    bit [7:0] d0 = vif.mon_cb.vbo_lane_d[0];
    for (int l = 0; l < cfg.lanes; l++) begin
      if (vif.mon_cb.vbo_lane_k[l]) anyk = 1; else allk = 0;
      if (vif.mon_cb.vbo_lane_d[l] != d0) same = 0;
    end
    if (anyk && !(allk && same)) `uvm_error("MON", "VbyOne: K symbol not on every lane")
    if (!anyk && same && d0 == 8'h4A && st == 0) begin ntr++; continue; end
    case (st)
      0: if (allk && (d0 == 8'h5C || d0 == 8'h1C)) begin
           t = vbo_transaction::type_id::create("t");
           t.rsof = (d0 == 8'h5C); t.ntrain = ntr; ntr = 0;
           ng = (cfg.h_active + cfg.lanes - 1) / cfg.lanes;
           g = 0; j = 0; st = 1; t.rpad = 1;
         end else if (!(allk && d0 == 8'hBC)) `uvm_error("MON", $sformatf("VbyOne: symbol %02h outside a line", d0))
      1: if (allk) begin
           if (d0 == 8'hBC && j == 0) t.nfill++;
           else begin
             `uvm_error("MON", $sformatf("VbyOne: K symbol %02h inside a line (group %0d, symbol %0d)", d0, g, j))
             st = 0;
           end
         end else begin
           for (int l = 0; l < cfg.lanes; l++) begin
             if (j == 0) grp[l] = 0;
             grp[l][8 * j +: 8] = vif.mon_cb.vbo_lane_d[l];
           end
           j++;
           if (j == 4) begin
             for (int l = 0; l < cfg.lanes; l++)
               if (g * cfg.lanes + l < cfg.h_active) t.rpix.push_back(grp[l]);
               else if (grp[l] != 0) t.rpad = 0;
             j = 0; g++;
             if (g == ng) begin
               if (in_l.size()) begin t.pix = in_l.pop_front(); t.sof = in_s.pop_front(); end
               publish(t);
               st = 0;
             end
           end
         end
    endcase
  end
end
""",
    predict="""
// the link is a transport: the panel gets the line that went in
t.rpix = t.pix;
t.rsof = t.sof;
t.rpad = 1;
""",
    checks="""
if (t.rpix.size() != cfg.h_active) fail(t, "line width");
if (!t.rpad) fail(t, "padding of the last group is not zero");
""",
    coverage="""
cp_sof   : coverpoint tr.rsof;
cp_fill  : coverpoint tr.nfill { bins none = {0}; bins some = {[1:$]}; }
cp_train : coverpoint tr.ntrain { bins none = {0}; bins trained = {[1:$]}; }
""",
    directed="""
// a frame of 4 lines, gaps, a relock, extreme pixels, a second frame
t = item(); t.set(0, 32'h10); send(t);
for (int i = 0; i < 3; i++) begin t = item(); t.set(11, 32'h20 + i); send(t); end
for (int i = 0; i < 4; i++) begin t = item(); t.set(4, 32'h30 + i); send(t); end
t = item(); t.set(8, 32'h40); send(t);
t = item(); t.set(9); send(t);
t = item(); t.set(10); send(t);
t = item(); t.set(1, 32'h50); send(t);
t = item(); t.set(8, 32'h60); send(t);
t = item(); t.set(5, 32'h70); send(t);
""",
    drain_ns=4000,
    model="""
module vbo_model #(parameter int LANES = 8, parameter int SYM_DIV = 2) (
  input  logic                  clk,
  input  logic                  rst_n,
  input  logic                  pix_valid,
  input  logic                  pix_sol,
  input  logic                  pix_sof,
  input  logic                  pix_eol,
  input  logic [31:0]           pix_data,
  input  logic                  vbo_htpdn_n,
  input  logic                  vbo_lockn_n,
  output logic [LANES-1:0][7:0] vbo_lane_d,
  output logic [LANES-1:0]      vbo_lane_k,
  output logic                  vbo_sym
);
  logic [31:0] pb [0:63];
  logic [6:0]  nw;
  logic        eol, sof, pend;
  logic [3:0]  sdiv;
  logic [1:0]  st;          // 0 idle, 1 in a line
  logic [3:0]  g;
  logic [1:0]  j;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nw <= '0; eol <= 1'b0; sof <= 1'b0; pend <= 1'b0; sdiv <= '0; st <= '0; g <= '0; j <= '0;
      vbo_lane_d <= '0; vbo_lane_k <= '0; vbo_sym <= 1'b0;
    end else begin : step
      logic [6:0]  n;
      logic        e, ready;
      n = nw; e = eol;
      if (pix_valid) begin
        if (pix_sol) begin
          pb[0] <= pix_data; n = 7'd1; e = pix_eol; sof <= pix_sof; pend <= 1'b1;
        end else if (nw < 7'd64) begin
          pb[nw[5:0]] <= pix_data; n = nw + 7'd1; if (pix_eol) e = 1'b1;
        end
      end
      nw <= n; eol <= e;
      vbo_sym <= 1'b0;
      sdiv <= (sdiv == SYM_DIV - 1) ? 4'd0 : sdiv + 4'd1;
      if (sdiv == 4'd0) begin
        vbo_sym <= 1'b1;
        if (vbo_htpdn_n || vbo_lockn_n) begin
          for (int l = 0; l < LANES; l++) begin vbo_lane_d[l] <= 8'h4A; vbo_lane_k[l] <= 1'b0; end
          st <= 2'd0;
        end else if (st == 2'd0) begin
          for (int l = 0; l < LANES; l++) begin
            vbo_lane_k[l] <= 1'b1;
            vbo_lane_d[l] <= pend ? (sof ? 8'h5C : 8'h1C) : 8'hBC;
          end
          if (pend) begin pend <= 1'b0; st <= 2'd1; g <= '0; j <= '0; end
        end else begin
          ready = (nw >= (g + 1) * LANES) || (eol && nw > g * LANES);
          if (j == 2'd0 && !ready) begin
            for (int l = 0; l < LANES; l++) begin vbo_lane_d[l] <= 8'hBC; vbo_lane_k[l] <= 1'b1; end
          end else begin
            for (int l = 0; l < LANES; l++) begin
              vbo_lane_k[l] <= 1'b0;
              vbo_lane_d[l] <= (g * LANES + l < nw) ? pb[g * LANES + l][8 * j +: 8] : 8'h00;
            end
            j <= j + 2'd1;
            if (j == 2'd3) begin
              g <= g + 4'd1;
              if (eol && (g + 1) * LANES >= nw) st <= 2'd0;
            end
          end
        end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({vbo_sym, vbo_lane_k, vbo_htpdn_n, vbo_lockn_n}))
  else $error("VbyOne: X on the link control");
assert property (@(posedge clk) disable iff (!rst_n) vbo_sym |-> !$isunknown(vbo_lane_d))
  else $error("VbyOne: X on a lane");
assert property (@(posedge clk) disable iff (!rst_n) vbo_sym && $past(vbo_lockn_n) && $past(vbo_lockn_n, 2) |-> vbo_lane_k == '0 && vbo_lane_d[0] == 8'h4A)
  else $error("VbyOne: not training while LOCKN is high");
assert property (@(posedge clk) disable iff (!rst_n) vbo_sym |-> vbo_lane_k == '0 || vbo_lane_k == '1)
  else $error("VbyOne: K symbol on some lanes only");
assert property (@(posedge clk) disable iff (!rst_n) pix_sof |-> pix_sol && pix_valid)
  else $error("VbyOne: frame start without line start");
cover property (@(posedge clk) disable iff (!rst_n) vbo_sym && vbo_lane_k[0] && vbo_lane_d[0] == 8'h5C);
""",
    smoke="""
int checks = 0;
int fails  = 0;
localparam integer L = 8, H = 12;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic pix_valid = 1'b0, pix_sol = 1'b0, pix_sof = 1'b0, pix_eol = 1'b0;
logic [31:0] pix_data = 32'h0;
logic vbo_htpdn_n = 1'b1, vbo_lockn_n = 1'b1;
wire [7:0][7:0] vbo_lane_d;
wire [7:0] vbo_lane_k;
wire vbo_sym;

always #5 clk = ~clk;

vbo_model u_dut (.clk(clk), .rst_n(rst_n), .pix_valid(pix_valid), .pix_sol(pix_sol), .pix_sof(pix_sof),
                 .pix_eol(pix_eol), .pix_data(pix_data), .vbo_htpdn_n(vbo_htpdn_n), .vbo_lockn_n(vbo_lockn_n),
                 .vbo_lane_d(vbo_lane_d), .vbo_lane_k(vbo_lane_k), .vbo_sym(vbo_sym));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// symbol log: kind 0 training, 1 idle, 2 K28.2, 3 K28.0, 4 data, 5 other
integer nsym = 0, ntrain = 0, nidle = 0, nk2 = 0, nk0 = 0, ndat = 0, nbad = 0, nsym_clk = 0, last_sym = 0;
logic [31:0] got [0:63];
integer ng, gj, gi;
always @(posedge clk) if (rst_n) begin
  nsym_clk = nsym_clk + 1;
  if (vbo_sym) begin
    logic allk, nok, same;
    allk = 1; nok = 1; same = 1;
    for (int l = 0; l < L; l++) begin
      if (vbo_lane_k[l]) nok = 0; else allk = 0;
      if (vbo_lane_d[l] != vbo_lane_d[0]) same = 0;
    end
    if (nsym != 0 && nsym_clk - last_sym != 2) nbad = nbad + 1;
    last_sym = nsym_clk;
    nsym = nsym + 1;
    if (nok && same && vbo_lane_d[0] == 8'h4A) ntrain = ntrain + 1;
    else if (allk && same && vbo_lane_d[0] == 8'hBC) nidle = nidle + 1;
    else if (allk && same && vbo_lane_d[0] == 8'h5C) begin nk2 = nk2 + 1; gi = 0; gj = 0; end
    else if (allk && same && vbo_lane_d[0] == 8'h1C) begin nk0 = nk0 + 1; gi = 0; gj = 0; end
    else if (nok) begin
      ndat = ndat + 1;
      for (int l = 0; l < L; l++) begin
        if (gj == 0) got[gi + l] = 0;
        got[gi + l][8 * gj +: 8] = vbo_lane_d[l];
      end
      gj = gj + 1;
      if (gj == 4) begin gj = 0; gi = gi + L; end
    end else nbad = nbad + 1;
  end
end

logic [31:0] pv [0:63];
task automatic line(input integer n, input logic sof, input integer gap = 0, input logic [31:0] v0 = 32'h01020304);
  for (int i = 0; i < 64; i++) pv[i] = v0 * (i + 1) ^ {i[7:0], 24'h0};
  for (int i = 0; i < 64; i++) if (i < n) begin
    if (gap != 0 && i % gap == gap - 1) begin pix_valid = 0; pix_sol = 0; pix_sof = 0; pix_eol = 0; repeat (12) @(negedge clk); end
    pix_valid = 1; pix_data = pv[i]; pix_sol = (i == 0); pix_sof = sof && (i == 0); pix_eol = (i == n - 1);
    @(negedge clk);
  end
  pix_valid = 0; pix_sol = 0; pix_sof = 0; pix_eol = 0;
  repeat (120) @(negedge clk);
endtask
function automatic logic same_px(input integer n);
  logic ok;
  ok = 1;
  for (int i = 0; i < 64; i++) if (i < n && got[i] !== pv[i]) ok = 0;
  for (int i = 0; i < 64; i++) if (i >= n && i < ((n + L - 1) / L) * L && got[i] !== 32'h0) ok = 0;
  same_px = ok;
endfunction

integer d0, i0, t0;
initial begin
  repeat (3) @(posedge clk);
  rst_n = 1;
  repeat (40) @(negedge clk);
  chk(ntrain > 10 && nidle == 0 && nbad == 0, "unplugged: training only, a symbol every 2 clocks");
  vbo_htpdn_n = 0; repeat (20) @(negedge clk);
  chk(nidle == 0, "HTPDN low, LOCKN high: still training");
  vbo_lockn_n = 0; repeat (20) @(negedge clk);
  chk(nidle > 5, "locked: K28.5 idle");
  d0 = ndat; line(H, 1); chk(nk2 == 1 && ndat - d0 == 8 && same_px(H), "frame start: K28.2, 2 groups, 4 padded pixels");
  d0 = ndat; line(H, 0); chk(nk0 == 1 && ndat - d0 == 8 && same_px(H), "next line: K28.0");
  d0 = ndat; line(16, 0); chk(ndat - d0 == 8 && same_px(16), "two full groups");
  d0 = ndat; line(1, 0); chk(ndat - d0 == 4 && same_px(1), "one pixel, 7 padded");
  d0 = ndat; i0 = nidle; line(24, 0, 6); chk(ndat - d0 == 12 && same_px(24) && nidle - i0 > 60, "input gaps: K28.5 between groups");
  d0 = ndat; line(40, 1); chk(nk2 == 2 && ndat - d0 == 20 && same_px(40), "40 pixels");
  t0 = ntrain; vbo_lockn_n = 1; repeat (20) @(negedge clk); chk(ntrain - t0 >= 9, "LOCKN high: training again");
  vbo_lockn_n = 0; repeat (10) @(negedge clk);
  d0 = ndat; line(H, 0, 0, 32'hFFFFFFFF); chk(ndat - d0 == 8 && same_px(H), "line after the relock");
  chk(nbad == 0, "no malformed symbol");
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
