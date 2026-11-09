# S/PDIF (IEC 60958-1 / -3 consumer digital audio) transmitter VIP: biphase-
# mark coded subframes on one line, oversampled by the receiver.
#
# Agent -> DUT: spdif_in. A unit interval (UI, half a bit cell) is cfg.ui
# clocks (model parameter W, default 8). A subframe is 32 time slots = 64 UI:
# preamble (slots 0-3, 8 UI, breaks the biphase rule), aux + audio sample
# (slots 4-27, 24 bits LSB first), V, U, C, P (even parity over slots 4-31).
# Every bit cell starts with a transition; a 1 has a second one in the middle.
# On the line, as run lengths in UI: preamble B (block start, channel A)
# 3,1,1,3; M (channel A) 3,3,1,1; W (channel B) 3,2,1,2; a 0 bit 2; a 1 bit 1,1.
# Each item is a burst of frames (A, B subframes) followed by one more
# transition and an idle line (the receiver loses lock and hunts again).
# DUT -> agent: one report per subframe (rep_valid; rep_pre 0 B, 1 M, 2 W,
# 3 no valid preamble; rep_data, rep_vucp, rep_status 0 ok, 1 parity error,
# 2 biphase / preamble violation) and with the report of frame 31's channel A
# subframe of a block, the first 32 channel status bits (rep_cs_valid, rep_cs).
#
# tb/top_tb.sv spdif_model: measures the clocks between transitions and
# classifies each run as 1 UI [W/2, 3W/2), 2 UI [3W/2, 5W/2) or 3 UI
# [5W/2, 7W/2). Hunting, a 3 UI run starts a preamble; the next three runs
# select B / M / W (anything else: status 2). Then 28 bit cells; a 3 UI or
# out-of-range run, a 2 UI run in the middle of a cell, or no transition for
# 7W/2 clocks: status 2, and the model hunts again. B resets the frame
# counter (and arms channel status), M advances it.

SPDIF_FUNCS = """
function automatic int spdif_cls(int n, int w);   // run length in UI, 0 when out of range
  if (2 * n < w) return 0;
  if (2 * n < 3 * w) return 1;
  if (2 * n < 5 * w) return 2;
  if (2 * n < 7 * w) return 3;
  return 0;
endfunction
"""

SPEC = dict(
    vip="SPDIF-UVM-VIP", p="spdif", P="SPDIF", dir="spdif", family="Audio",
    desc="S/PDIF IEC 60958 transmitter VIP: biphase-mark subframes with B / M / W preambles, 24-bit samples, "
         "V / U / C / P and 192-frame channel status blocks; oversampling receiver model with parity, biphase and "
         "preamble error detection and re-lock.",
    about="""
S/PDIF carries stereo PCM (or compressed IEC 61937 bursts) from a set-top box,
console or the TV's own HDMI ARC path on one biphase-mark line. The agent is
the transmitter: it sends bursts of frames with random 24-bit samples and
validity bits, starts channel status blocks with the B preamble and spreads a
channel status word (`cfg.cs_word`, default consumer PCM 48 kHz) over the C
bits, and plants faults (a flipped parity bit, a missing cell transition, an
illegal preamble) and edge jitter inside the receiver's windows. The DUT
model is the oversampling receiver; the scoreboard decodes the same run
lengths with its own decoder, keeps the frame counter and channel status
bits across bursts and predicts every report. The pin matches SPDIF_eARC_top
in open-ip-portfolio (spdif_in); `cfg.ui` is the IP's clocks per half cell.""",
    defs=SPDIF_FUNCS,
    timeout=20000,
    cfg="""int unsigned ui = 8;                       // clocks per UI (half bit cell), model parameter W
int unsigned gap_ui = 16;                  // idle UI after each burst
bit [31:0]   cs_word = 32'h0200_0004;      // channel status bits 0-31: consumer, PCM, 48 kHz (bit 0 first)""",
    ports=[
        ("in", "logic", "spdif_in"),
        ("out", "logic", "rep_valid"), ("out", "logic [1:0]", "rep_pre"), ("out", "logic [23:0]", "rep_data"),
        ("out", "logic [3:0]", "rep_vucp"), ("out", "logic [1:0]", "rep_status"),
        ("out", "logic", "rep_cs_valid"), ("out", "logic [31:0]", "rep_cs"),
    ],
    fields=[
        ("bit [15:0]", "seg", "req", "q"),
        ("bit [31:0]", "rep", "rsp", "q"),     # {status, pre, V U C P, data} per subframe
        ("bit [31:0]", "csq", "rsp", "q"),     # channel status words reported
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "nfr", "info", "rand"),
        ("bit", "valid", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-19 burst of M frames, 20 parity flip, 21 missing transition at a cell
// boundary, 22 illegal preamble, 23 jitter, 24-27 block start (B), 28-31 M frames.
// nfr + 1 frames per burst. Returns the frame counter after the burst.
function void set(int k, int frames, bit [31:0] s = 32'h1); kind = k; nfr = frames - 1; seed = s; endfunction
function int build(int unsigned w, int f, bit [31:0] csw);
  bit [31:0] x = seed | 1;
  int ru [$];                 // run lengths in UI
  int cell0 [$];              // index in ru of the first run of each data cell (for kind 21)
  int nsub = 2 * (nfr + 1);
  int fs = x[7:0] % nsub;     // subframe that carries the fault
  for (int s = 0; s < nsub; s++) begin
    bit [27:0] b;
    bit c;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    if (s % 2 == 0) begin
      if (s == 0 && kind inside {[24:27]}) f = 0; else f = f + 1;
    end
    c = (f < 32) ? csw[f] : 1'b0;
    b = {1'b0, c, 1'b0, !valid, x[23:0]};
    b[27] = ^b[26:0];
    if (kind == 20 && s == fs) b[27] = ~b[27];
    if (kind == 22 && s == fs) begin ru.push_back(3); ru.push_back(1); ru.push_back(3); ru.push_back(1); end
    else if (s % 2) begin ru.push_back(3); ru.push_back(2); ru.push_back(1); ru.push_back(2); end
    else if (s == 0 && kind inside {[24:27]}) begin ru.push_back(3); ru.push_back(1); ru.push_back(1); ru.push_back(3); end
    else begin ru.push_back(3); ru.push_back(3); ru.push_back(1); ru.push_back(1); end
    for (int i = 0; i < 28; i++) begin
      if (s == fs) cell0.push_back(ru.size());
      if (b[i]) begin ru.push_back(1); ru.push_back(1); end else ru.push_back(2);
    end
  end
  if (kind == 21) begin
    int j = cell0[1 + x[11:8] % 26];        // merge the run before a cell boundary with the one after
    ru[j - 1] = ru[j - 1] + ru[j];
    ru.delete(j);
  end
  seg.delete();
  foreach (ru[i]) begin
    int n = ru[i] * w;
    if (kind == 23) begin x ^= x << 13; x ^= x >> 17; x ^= x << 5; n = n + x[2:0] % 5 - 2; end
    seg.push_back(n);
  end
  return f;
endfunction
""",
    drv_rsp=False,
    drv_desc="one burst of biphase-mark frames per item (a transition then seg[i] clocks of each run), one closing transition and cfg.gap_ui idle UI; the frame counter for B / M and channel status runs across items",
    drv_members="int fidx = 0;\nbit lvl = 0;",
    drv_idle="vif.drv_cb.spdif_in <= 1'b0;",
    drv_item="""
fidx = t.build(cfg.ui, fidx, cfg.cs_word);
@(vif.drv_cb);
foreach (t.seg[i]) begin
  lvl = !lvl;
  vif.drv_cb.spdif_in <= lvl;
  repeat (t.seg[i]) @(vif.drv_cb);
end
lvl = !lvl;
vif.drv_cb.spdif_in <= lvl;
repeat (cfg.gap_ui * cfg.ui) @(vif.drv_cb);
""",
    mon_desc="run lengths on spdif_in from the first transition of a burst to an idle line, with every subframe report the receiver gave meanwhile",
    mon_run="""
forever begin
  spdif_transaction t;
  int unsigned n = 0;
  bit lv;
  lv = vif.mon_cb.spdif_in;
  do @(vif.mon_cb); while (vif.mon_cb.spdif_in === lv);
  lv = vif.mon_cb.spdif_in;
  t = spdif_transaction::type_id::create("t");
  n = 1;
  forever begin
    @(vif.mon_cb);
    if (vif.mon_cb.rep_valid)
      t.rep.push_back({vif.mon_cb.rep_status, vif.mon_cb.rep_pre, vif.mon_cb.rep_vucp, vif.mon_cb.rep_data});
    if (vif.mon_cb.rep_valid && vif.mon_cb.rep_cs_valid) t.csq.push_back(vif.mon_cb.rep_cs);
    if (vif.mon_cb.spdif_in === lv) begin
      n++;
      if (n >= 8 * cfg.ui) break;
    end else begin
      t.seg.push_back(n);
      lv = vif.mon_cb.spdif_in; n = 1;
    end
  end
  publish(t);
end
""",
    sb_members="""int fidx = 0;
bit blk = 0;
bit [31:0] csb = 0;""",
    predict="""
// receiver run on the run lengths of the burst (the run after the last one
// is the idle line)
int w = cfg.ui, st = 0, np = 0, nb = 0;
int pr [4];
bit half = 0;
bit [1:0] pre = 3;
bit [27:0] sb;
t.rep.delete(); t.csq.delete();
foreach (t.seg[i]) begin
  int c = spdif_cls(t.seg[i], w);
  case (st)
    0: if (c == 3) begin st = 1; np = 1; pr[0] = 3; end
    1: begin
         pr[np++] = c;
         if (np == 4) begin
           if (pr[1] == 1 && pr[2] == 1 && pr[3] == 3) pre = 0;
           else if (pr[1] == 3 && pr[2] == 1 && pr[3] == 1) pre = 1;
           else if (pr[1] == 2 && pr[2] == 1 && pr[3] == 2) pre = 2;
           else pre = 3;
           if (pre == 3) begin t.rep.push_back({2'd2, 2'd3, 28'h0}); st = 0; end
           else begin
             if (pre == 0) begin fidx = 0; blk = 1; end
             else if (pre == 1 && fidx < 255) fidx++;
             st = 2; nb = 0; half = 0;
           end
         end
       end
    2: begin
         bit err = 0, done = 0, v = 0;
         if (c == 1) begin if (half) begin done = 1; v = 1; end else half = 1; end
         else if (c == 2 && !half) begin done = 1; v = 0; end
         else err = 1;
         if (err) begin t.rep.push_back({2'd2, pre, 28'h0}); st = 0; end
         else if (done) begin
           sb[nb] = v; half = 0;
           if (nb == 27) begin
             t.rep.push_back({(^sb) ? 2'd1 : 2'd0, pre, sb[24], sb[25], sb[26], sb[27], sb[23:0]});
             if (pre != 2 && fidx < 32) begin
               csb[fidx] = sb[26];
               if (fidx == 31 && blk) t.csq.push_back(csb);
             end
             st = 0;
           end else nb++;
         end
       end
  endcase
end
// no transition for 7W/2 clocks in the middle of a subframe
if (st == 2) t.rep.push_back({2'd2, pre, 28'h0});
""",
    checks="""
foreach (t.rep[i]) begin
  if (t.rep[i][31:30] == 2'd3) fail(t, "reserved status");
  if (t.rep[i][31:30] == 2'd2 && t.rep[i][27:0] != 0) fail(t, "data reported with a violation");
  if (t.rep[i][31:30] != 2'd2 && t.rep[i][29:28] == 2'd3) fail(t, "data without a preamble");
end
""",
    coverage="""
cp_n      : coverpoint tr.rep.size() { bins frame = {2}; bins burst = {[3:8]}; }
cp_status : coverpoint (tr.rep.size() ? tr.rep[tr.rep.size() - 1][31:30] : 2'd0) { bins ok = {0}; bins parity = {1}; bins bmc = {2}; }
cp_cs     : coverpoint tr.csq.size() { bins none = {0}; bins block = {1}; }
cp_first  : coverpoint (tr.rep.size() ? tr.rep[0][29:28] : 2'd3) { bins b = {0}; bins m = {1}; bins bad = {3}; }
""",
    directed="""
// a 48-frame block in bursts, then every fault, jitter, and a second block
t = item(); t.set(24, 4, 32'h11); send(t);
for (int i = 0; i < 11; i++) begin t = item(); t.set(0, 4, 32'h100 + i); t.valid = i[0]; send(t); end
t = item(); t.set(0, 1, 32'h7); send(t);
for (int s = 0; s < 3; s++) begin
  t = item(); t.set(20, 2, 32'h33 * (s + 1)); send(t);
  t = item(); t.set(21, 2, 32'h55 * (s + 1)); send(t);
  t = item(); t.set(22, 2, 32'h77 * (s + 1)); send(t);
  t = item(); t.set(23, 3, 32'h99 * (s + 1)); send(t);
end
t = item(); t.set(25, 4, 32'h1234); send(t);
for (int i = 0; i < 8; i++) begin t = item(); t.set(23, 4, 32'h4000 + i); send(t); end
""",
    drain_ns=20000,
    model="""
module spdif_model #(parameter int W = 8) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        spdif_in,
  output logic        rep_valid,
  output logic [1:0]  rep_pre,
  output logic [23:0] rep_data,
  output logic [3:0]  rep_vucp,
  output logic [1:0]  rep_status,
  output logic        rep_cs_valid,
  output logic [31:0] rep_cs
);
  function automatic logic [1:0] cls(input logic [15:0] n);
    if (2 * n < W) cls = 2'd0;
    else if (2 * n < 3 * W) cls = 2'd1;
    else if (2 * n < 5 * W) cls = 2'd2;
    else if (2 * n < 7 * W) cls = 2'd3;
    else cls = 2'd0;
  endfunction

  logic [1:0]  st, pre, np;
  logic [1:0]  pr1, pr2;
  logic        lv, half, blk;
  logic [15:0] cnt;
  logic [4:0]  nb;
  logic [27:0] sb;
  logic [7:0]  fidx;
  logic [31:0] csb;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= 2'd0; pre <= 2'd3; np <= '0; pr1 <= '0; pr2 <= '0; lv <= 1'b0; half <= 1'b0; blk <= 1'b0;
      cnt <= 16'hFFFF; nb <= '0; sb <= '0; fidx <= '0; csb <= '0;
      rep_valid <= 1'b0; rep_pre <= '0; rep_data <= '0; rep_vucp <= '0; rep_status <= '0;
      rep_cs_valid <= 1'b0; rep_cs <= '0;
    end else begin
      rep_valid <= 1'b0; rep_cs_valid <= 1'b0;
      if (spdif_in == lv) begin
        if (cnt != 16'hFFFF) cnt <= cnt + 16'd1;
        if (2 * (cnt + 16'd1) >= 7 * W && st != 2'd0) begin
          if (st == 2'd2) begin
            rep_valid <= 1'b1; rep_status <= 2'd2; rep_pre <= pre; rep_data <= '0; rep_vucp <= '0;
          end
          st <= 2'd0;
        end
      end else begin : run_end
        logic [1:0]  c, p;
        logic [27:0] s;
        logic [31:0] cs;
        lv <= spdif_in;
        cnt <= 16'd1;
        c = cls(cnt);
        case (st)
          2'd0: if (c == 2'd3) begin st <= 2'd1; np <= 2'd1; end
          2'd1: begin
                  if (np == 2'd1) begin pr1 <= c; np <= 2'd2; end
                  else if (np == 2'd2) begin pr2 <= c; np <= 2'd3; end
                  else begin
                    if (pr1 == 2'd1 && pr2 == 2'd1 && c == 2'd3) p = 2'd0;
                    else if (pr1 == 2'd3 && pr2 == 2'd1 && c == 2'd1) p = 2'd1;
                    else if (pr1 == 2'd2 && pr2 == 2'd1 && c == 2'd2) p = 2'd2;
                    else p = 2'd3;
                    pre <= p;
                    if (p == 2'd3) begin
                      rep_valid <= 1'b1; rep_status <= 2'd2; rep_pre <= 2'd3; rep_data <= '0; rep_vucp <= '0;
                      st <= 2'd0;
                    end else begin
                      if (p == 2'd0) begin fidx <= '0; blk <= 1'b1; end
                      else if (p == 2'd1 && fidx != 8'hFF) fidx <= fidx + 8'd1;
                      st <= 2'd2; nb <= '0; half <= 1'b0;
                    end
                  end
                end
          2'd2: begin
                  logic err, done, v;
                  err = 1'b0; done = 1'b0; v = 1'b0;
                  if (c == 2'd1) begin if (half) begin done = 1'b1; v = 1'b1; end else half <= 1'b1; end
                  else if (c == 2'd2 && !half) done = 1'b1;
                  else err = 1'b1;
                  if (err) begin
                    rep_valid <= 1'b1; rep_status <= 2'd2; rep_pre <= pre; rep_data <= '0; rep_vucp <= '0;
                    st <= 2'd0;
                  end else if (done) begin
                    half <= 1'b0;
                    s = sb; s[nb] = v; sb <= s;
                    if (nb == 5'd27) begin
                      rep_valid <= 1'b1; rep_status <= (^s) ? 2'd1 : 2'd0; rep_pre <= pre;
                      rep_data <= s[23:0]; rep_vucp <= {s[24], s[25], s[26], s[27]};
                      if (pre != 2'd2 && fidx < 8'd32) begin
                        cs = csb; cs[fidx[4:0]] = s[26]; csb <= cs;
                        if (fidx == 8'd31 && blk) begin rep_cs_valid <= 1'b1; rep_cs <= cs; end
                      end
                      st <= 2'd0;
                    end else nb <= nb + 5'd1;
                  end
                end
          default: st <= 2'd0;
        endcase
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({spdif_in, rep_valid, rep_cs_valid}))
  else $error("SPDIF: X on the line / valids");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> rep_status != 2'd3 && !$isunknown({rep_pre, rep_data, rep_vucp}))
  else $error("SPDIF: bad report");
assert property (@(posedge clk) disable iff (!rst_n) rep_cs_valid |-> rep_valid && rep_status != 2'd2 && rep_pre != 2'd2)
  else $error("SPDIF: channel status without a channel A subframe");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 2'd2 |-> rep_data == 24'h0)
  else $error("SPDIF: data with a violation");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 2'd1);
cover property (@(posedge clk) disable iff (!rst_n) rep_cs_valid);
""",
    smoke="""
int checks = 0;
int fails  = 0;
localparam integer W = 8;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic spdif_in = 1'b0;
wire rep_valid, rep_cs_valid;
wire [1:0] rep_pre, rep_status;
wire [23:0] rep_data;
wire [3:0] rep_vucp;
wire [31:0] rep_cs;

always #5 clk = ~clk;

spdif_model u_dut (.clk(clk), .rst_n(rst_n), .spdif_in(spdif_in), .rep_valid(rep_valid), .rep_pre(rep_pre),
                   .rep_data(rep_data), .rep_vucp(rep_vucp), .rep_status(rep_status),
                   .rep_cs_valid(rep_cs_valid), .rep_cs(rep_cs));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

integer nrep = 0, ncs = 0;
logic [1:0] r_pre [0:255], r_st [0:255];
logic [23:0] r_d [0:255];
logic [3:0] r_v [0:255];
logic [31:0] r_cs;
always @(posedge clk) if (rep_valid) begin
  r_pre[nrep[7:0]] = rep_pre; r_st[nrep[7:0]] = rep_status; r_d[nrep[7:0]] = rep_data; r_v[nrep[7:0]] = rep_vucp;
  nrep = nrep + 1;
  if (rep_cs_valid) begin ncs = ncs + 1; r_cs = rep_cs; end
end

// a run of n UI (plus extra clocks): a transition, then n * W + extra clocks
task automatic run(input integer n, input integer extra = 0);
  spdif_in = ~spdif_in;
  repeat (n * W + extra) @(negedge clk);
endtask
task automatic pre(input integer p);   // 0 B, 1 M, 2 W, 3 illegal
  case (p)
    0: begin run(3); run(1); run(1); run(3); end
    1: begin run(3); run(3); run(1); run(1); end
    2: begin run(3); run(2); run(1); run(2); end
    default: begin run(3); run(1); run(3); run(1); end
  endcase
endtask
// subframe: preamble p, 24-bit data, V U C; parity correct unless bad_p;
// a cell boundary transition dropped before cell drop (-1: none)
// odd = cell replaced by one run of oddn clocks; p0 = clocks of the first preamble run (0: 3 UI)
task automatic sub(input integer p, input logic [23:0] d, input logic v, input logic u, input logic c,
                   input logic bad_p = 0, input integer drop = -1, input integer odd = -1, input integer oddn = 0,
                   input integer p0 = 0);
  logic [27:0] b;
  b = {1'b0, c, u, v, d};
  b[27] = ^b[26:0] ^ bad_p;
  if (p0 != 0) begin
    run(0, p0);
    case (p)
      0: begin run(1); run(1); run(3); end
      1: begin run(3); run(1); run(1); end
      default: begin run(2); run(1); run(2); end
    endcase
  end else pre(p);
  for (int i = 0; i < 28; i++) begin
    if (i == odd) begin run(0, (oddn > 0) ? oddn : -oddn); if (oddn < 0) run(0, -oddn); end
    else if (i == drop) begin
      // no transition at the start of this cell: the previous level goes on
      if (b[i]) begin repeat (W) @(negedge clk); run(1); end else repeat (2 * W) @(negedge clk);
    end else if (b[i]) begin run(1); run(1); end else run(2);
  end
endtask
task automatic prer(input integer a, input integer b, input integer c, input integer d);
  run(a); run(b); run(c); run(d);
  for (int i = 0; i < 28; i++) run(2);
endtask
task automatic stop();
  spdif_in = ~spdif_in;
  repeat (16 * W) @(negedge clk);
endtask

integer r0;
logic [31:0] csw;
initial begin
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0, "no report in reset");
  rst_n = 1;
  repeat (40) @(negedge clk);
  chk(nrep == 0, "no report on an idle line");
  r0 = nrep;
  sub(0, 24'h123456, 0, 0, 1); sub(2, 24'hABCDEF, 0, 0, 1); stop();
  chk(nrep == r0 + 2 && r_pre[r0] == 0 && r_d[r0] == 24'h123456 && r_v[r0] == 4'b0010 && r_st[r0] == 0,
      "B subframe: data, C = 1, parity ok");
  chk(r_pre[r0 + 1] == 2 && r_d[r0 + 1] == 24'hABCDEF && r_st[r0 + 1] == 0, "W subframe");
  r0 = nrep; sub(1, 24'h000000, 1, 0, 0); sub(2, 24'hFFFFFF, 0, 1, 0); stop();
  chk(nrep == r0 + 2 && r_pre[r0] == 1 && r_d[r0] == 0 && r_v[r0] == 4'b1001, "M subframe, all zeros, V = 1");
  chk(r_d[r0 + 1] == 24'hFFFFFF && r_v[r0 + 1] == 4'b0101, "all ones, U = 1 (parity 1)");
  r0 = nrep; sub(1, 24'h00F00F, 0, 0, 0, 1); stop(); chk(nrep == r0 + 1 && r_st[r0] == 1 && r_d[r0] == 24'h00F00F, "parity error: data kept");
  r0 = nrep; sub(1, 24'h5A5A5A, 0, 0, 0, 0, 9); sub(2, 24'h111111, 0, 0, 0); stop();
  chk(nrep == r0 + 2 && r_st[r0] == 2 && r_pre[r0] == 1 && r_d[r0] == 0, "missing transition: violation");
  chk(r_st[r0 + 1] == 0 && r_d[r0 + 1] == 24'h111111, "next subframe received after re-lock");
  r0 = nrep; sub(3, 24'h222222, 0, 0, 0); sub(2, 24'h333333, 0, 0, 0); stop();
  chk(nrep == r0 + 2 && r_st[r0] == 2 && r_pre[r0] == 3 && r_d[r0 + 1] == 24'h333333, "illegal preamble, then W");
  // a subframe cut in the middle: no transition for 7W/2
  r0 = nrep; pre(1); for (int i = 0; i < 10; i++) run(2); stop();
  chk(nrep == r0 + 1 && r_st[r0] == 2, "line stops inside a subframe");
  // windows: 1 UI = W/2 .. 3W/2 - 1, 2 UI up to 5W/2 - 1, 3 UI up to 7W/2 - 1
  r0 = nrep; run(3, 3); run(3, -3); run(1, 3); run(1, -4);
  for (int i = 0; i < 28; i++) if (i % 2) begin run(1, -4); run(1, 3); end else run(2, (i % 4) ? 3 : -4);
  stop();
  chk(nrep == r0 + 1 && r_pre[r0] == 1 && r_st[r0] != 2, "edge jitter at the window limits");
  // channel status: a block of 32 frames from B
  csw = 32'h0200_0004;
  r0 = nrep; ncs = 0;
  for (int f = 0; f < 32; f++) begin sub(f ? 1 : 0, f, 0, 0, csw[f]); sub(2, ~f, 0, 0, ~csw[f]); end
  stop();
  chk(nrep == r0 + 64 && ncs == 1 && r_cs == csw, "channel status word after 32 frames");
  r0 = nrep; ncs = 0;
  for (int f = 0; f < 40; f++) sub(1, f, 0, 0, 1); stop();
  chk(ncs == 0, "no second word without a new B");
  // run windows: 1 UI from W/2 = 4 clocks, 3 UI from 5W/2 = 20, out of range from 7W/2 = 28
  r0 = nrep; sub(1, 24'h0, 0, 0, 0, 0, -1, 5, 3); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2, "a run of 3 clocks is a violation");
  r0 = nrep; sub(1, 24'h0, 0, 0, 0, 0, -1, 5, -3); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2, "two runs of 3 clocks are not a 1 cell");
  r0 = nrep; sub(1, 24'h0, 0, 0, 0, 0, -1, 5, -4); stop(); chk(nrep == r0 + 1 && r_st[r0] == 1, "two runs of 4 clocks are a 1 cell (parity now odd)");
  r0 = nrep; sub(1, 24'h0, 0, 0, 0, 0, -1, 5, 20); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2, "a run of 20 clocks (2.5 UI) in a cell is a violation");
  r0 = nrep; sub(1, 24'h0, 0, 0, 0, 0, -1, 5, 19); stop(); chk(nrep == r0 + 1 && r_st[r0] == 0, "a run of 19 clocks is a 0 cell");
  r0 = nrep; sub(1, 24'h77, 0, 0, 0, 0, -1, -1, 0, 28); sub(2, 24'h88, 0, 0, 0); stop();
  chk(nrep == r0 + 2 && r_st[r0] == 2 && r_pre[r0 + 1] == 2 && r_d[r0 + 1] == 24'h88,
      "a first preamble run of 28 clocks is not one: the hunt locks on the next 3 UI run and fails");
  r0 = nrep; sub(1, 24'h77, 0, 0, 0, 0, -1, -1, 0, 27); stop(); chk(nrep == r0 + 1 && r_d[r0] == 24'h77, "a first preamble run of 27 clocks starts a preamble");
  r0 = nrep; prer(3, 3, 1, 3); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2 && r_pre[r0] == 3, "preamble 3,3,1,3 is illegal");
  r0 = nrep; prer(3, 3, 1, 2); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2 && r_pre[r0] == 3, "preamble 3,3,1,2 is illegal");
  r0 = nrep; prer(3, 1, 3, 3); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2 && r_pre[r0] == 3, "preamble 3,1,3,3 is illegal");
  r0 = nrep; prer(3, 2, 2, 2); stop(); chk(nrep == r0 + 1 && r_st[r0] == 2 && r_pre[r0] == 3, "preamble 3,2,2,2 is illegal");
  // channel A only: the frame counter follows M, not W
  r0 = nrep; ncs = 0;
  for (int f = 0; f < 32; f++) sub(f ? 1 : 0, f, 0, 0, ~csw[f]);
  stop();
  chk(ncs == 1 && r_cs == ~csw, "channel status from 32 channel A subframes without W");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #50000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
