# MPEG-2 transport stream (ISO/IEC 13818-1) source VIP on a parallel TSI port
# (the byte-wide transport stream interface between a tuner / demodulator or
# CI module and the TV SoC's demultiplexer).
#
# Agent -> DUT, a byte per clock with ts_valid (gaps allowed): ts_sync marks
# byte 0 of each 188-byte packet, ts_err flags a byte the demodulator could not
# correct. Packet: 0x47, {TEI, PUSI, priority, PID[12:8]}, PID[7:0],
# {scrambling 00, adaptation_field_control, continuity_counter}, adaptation
# field (length, flags with discontinuity_indicator in bit 7, stuffing), payload.
# DUT -> agent: the payload of each accepted packet (out_valid, out_data,
# out_last) and one report per packet (rep_valid, rep_pid, rep_cc, rep_status).
#
# tb/top_tb.sv tsi_model: a demultiplexer with a PID filter of four entries
# (0x0000 PAT, 0x0100, 0x0101, 0x0111). Checks in order:
#   5  packet cut short (no byte for 64 clocks) or sync byte not 0x47: dropped (pid 0)
#   4  transport_error_indicator set or ts_err on any byte: dropped
#   1  PID not in the filter (the null PID 0x1FFF never is): dropped
#   6  adaptation_field_control 00, or adaptation field length out of range
#      (control 10: must be 183; control 11: at most 182): dropped
#   0  control 10 (adaptation field only): accepted, no payload, CC not checked
#   for packets with payload, per PID (first packet, or discontinuity_indicator: any CC):
#   3  CC equal to the last one: duplicate, dropped
#   0  CC = last + 1: payload delivered
#   2  any other CC: discontinuity, payload delivered, CC tracking restarts

TSI_FUNCS = """
function automatic bit [12:0] tsi_pid(int i);
  case (i)
    0: return 13'h0000;
    1: return 13'h0100;
    2: return 13'h0101;
    default: return 13'h0111;
  endcase
endfunction
function automatic int tsi_slot(bit [12:0] pid);   // filter entry, -1 when not filtered
  for (int i = 0; i < 4; i++) if (tsi_pid(i) == pid) return i;
  return -1;
endfunction
"""

SPEC = dict(
    vip="MPEG_TS-UVM-VIP", p="tsi", P="TSI", dir="tsi", family="Video",
    desc="MPEG-2 transport stream source VIP on a parallel TSI port: 188-byte packets with PID, continuity counter, "
         "adaptation fields, TEI / ts_err; demultiplexer model with a PID filter, CC duplicate / discontinuity checks "
         "and payload extraction.",
    about="""
Broadcast TV arrives at the SoC as an MPEG-2 transport stream from the tuner
or a CI module over a byte-wide TSI port. The agent is that source: it keeps
a continuity counter per PID, sends packets with and without adaptation
fields (stuffing, discontinuity indicator), adaptation-only packets, null
packets, PIDs outside the filter, duplicates and CC gaps, and faults (TEI,
ts_err, a wrong sync byte, a packet cut short, illegal adaptation field
lengths), with random ts_valid gaps. The DUT model is the demultiplexer's
input stage; the scoreboard keeps the CC state of every filtered PID and
predicts each report and the extracted payload. The pins match TS_Demux_top
in open-ip-portfolio (ts_valid, ts_sync, ts_data, ts_err).""",
    defs=TSI_FUNCS,
    timeout=2000,
    ports=[
        ("in", "logic", "ts_valid"), ("in", "logic", "ts_sync"), ("in", "logic [7:0]", "ts_data"), ("in", "logic", "ts_err"),
        ("out", "logic", "out_valid"), ("out", "logic [7:0]", "out_data"), ("out", "logic", "out_last"),
        ("out", "logic", "rep_valid"), ("out", "logic [12:0]", "rep_pid"), ("out", "logic [3:0]", "rep_cc"),
        ("out", "logic [2:0]", "rep_status"),
    ],
    fields=[
        ("bit [7:0]", "pkt", "req", "q"),
        ("bit", "terr", "req", "norand"),
        ("bit [12:0]", "rpid", "rsp"),
        ("bit [3:0]", "rcc", "rsp"),
        ("bit [2:0]", "rstatus", "rsp"),
        ("bit [7:0]", "odata", "rsp", "q"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "sel", "info", "rand"),
        ("bit [7:0]", "aflen", "info", "rand"),
        ("bit", "pusi", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [3:0]", "cc", "info"),
    ],
    tr_functions="""
// kind: 0-11 payload in order (control 01 / 11 from aflen[0]), 12 duplicate CC,
// 13 CC gap, 14 CC gap with discontinuity_indicator, 15 PID not filtered, 16 null
// packet, 17 TEI, 18 ts_err, 19 sync byte 0x46, 20 cut after 100 bytes,
// 21 adaptation field only, 22 control 11 with length 183, 23 control 00, 24-31 in order
function void set(int k, int s, bit [7:0] af = 8'h01); kind = k; sel = s; aflen = af; endfunction
function bit [12:0] pid_of();
  if (kind == 15) return 13'h0200 + seed[7:0];
  if (kind == 16) return 13'h1FFF;
  return tsi_pid(sel);
endfunction
function void build(bit [3:0] c);
  bit [31:0] x = seed | 1;
  bit [1:0] afc;
  int L = -1;
  bit [12:0] pid = pid_of();
  cc = c;
  afc = aflen[0] ? 2'b01 : 2'b11;
  if (kind == 21) afc = 2'b10;
  if (kind == 22 || kind == 14) afc = 2'b11;
  if (kind == 23) afc = 2'b00;
  if (afc[1]) L = (kind == 21 || kind == 22) ? 183 : (kind == 14) ? 1 + aflen % 182 : aflen % 183;
  pkt.delete();
  terr = (kind == 18);
  pkt.push_back((kind == 19) ? 8'h46 : 8'h47);
  pkt.push_back({kind == 17, pusi, 1'b0, pid[12:8]});
  pkt.push_back(pid[7:0]);
  pkt.push_back({2'b00, afc, c});
  if (L >= 0) begin
    pkt.push_back(L[7:0]);
    if (L > 0) pkt.push_back({kind == 14, 7'h00});
    while (pkt.size() < 5 + L) pkt.push_back(8'hFF);
  end
  while (pkt.size() < 188) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    pkt.push_back(x[7:0]);
  end
  if (kind == 20) while (pkt.size() > 100) void'(pkt.pop_back());
endfunction
""",
    drv_rsp=True,
    drv_desc="one 188-byte packet per item with ts_sync on byte 0 and random ts_valid gaps, CC from a per-PID counter (duplicates and gaps planted); then the payload and the report",
    drv_members="bit [3:0] nxt [4] = '{0, 0, 0, 0};",
    drv_idle="""
vif.drv_cb.ts_valid <= 1'b0;
vif.drv_cb.ts_sync  <= 1'b0;
vif.drv_cb.ts_data  <= 8'h00;
vif.drv_cb.ts_err   <= 1'b0;
""",
    drv_item="""
bit [3:0] c = nxt[t.sel];
bit [31:0] x = t.seed ^ 32'h9E37_79B9;
int k = 0, ep = 4 + t.seed[6:0];
if (t.kind == 12) c = nxt[t.sel] - 1;
else if (t.kind inside {13, 14}) c = nxt[t.sel] + 1 + t.seed[1:0];
else if (t.kind == 21) c = nxt[t.sel] - 1;
t.build(c);
if (t.kind inside {[0:11], 13, 14, [24:31]}) nxt[t.sel] = c + 1;
@(vif.drv_cb);
foreach (t.pkt[i]) begin
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  if (x[2:0] == 0 && i != 0) begin
    vif.drv_cb.ts_valid <= 1'b0; vif.drv_cb.ts_sync <= 1'b0; vif.drv_cb.ts_err <= 1'b0;
    repeat (1 + x[4:3]) @(vif.drv_cb);
  end
  vif.drv_cb.ts_valid <= 1'b1; vif.drv_cb.ts_sync <= (i == 0); vif.drv_cb.ts_data <= t.pkt[i];
  vif.drv_cb.ts_err <= t.terr && (i == ep);
  @(vif.drv_cb);
end
vif.drv_cb.ts_valid <= 1'b0; vif.drv_cb.ts_sync <= 1'b0; vif.drv_cb.ts_err <= 1'b0;
t.odata.delete();
do begin
  @(vif.drv_cb);
  if (vif.drv_cb.out_valid) t.odata.push_back(vif.drv_cb.out_data);
  k++;
end while (!vif.drv_cb.rep_valid && k < cfg.timeout_cycles);
if (!vif.drv_cb.rep_valid) `uvm_error("DRV", "TSI: no report for a packet")
t.rpid = vif.drv_cb.rep_pid; t.rcc = vif.drv_cb.rep_cc; t.rstatus = vif.drv_cb.rep_status;
repeat (2) @(vif.drv_cb);
""",
    mon_desc="bytes from each ts_sync, the payload and the report that closes the packet",
    mon_run="""
bit [7:0] b[$], o[$];
bit e = 0;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.ts_valid) begin
    if (vif.mon_cb.ts_sync) begin b.delete(); e = 0; end
    b.push_back(vif.mon_cb.ts_data);
    if (vif.mon_cb.ts_err) e = 1;
  end
  if (vif.mon_cb.out_valid) o.push_back(vif.mon_cb.out_data);
  if (vif.mon_cb.rep_valid) begin
    tsi_transaction t = tsi_transaction::type_id::create("t");
    t.pkt = b; t.terr = e; t.odata = o;
    t.rpid = vif.mon_cb.rep_pid; t.rcc = vif.mon_cb.rep_cc; t.rstatus = vif.mon_cb.rep_status;
    publish(t);
    b.delete(); o.delete(); e = 0;
  end
end
""",
    sb_members="""bit [3:0] last [4];
bit       seen [4] = '{0, 0, 0, 0};""",
    predict="""
int n = t.pkt.size(), s, L = 0, p0;
bit [12:0] pid;
bit [1:0] afc;
bit [3:0] c;
bit di = 0;
t.odata.delete();
t.rpid = 0; t.rcc = 0;
if (n != 188 || t.pkt[0] != 8'h47) begin t.rstatus = 5; return; end
pid = {t.pkt[1][4:0], t.pkt[2]};
c = t.pkt[3][3:0]; afc = t.pkt[3][5:4];
t.rpid = pid; t.rcc = c;
if (t.pkt[1][7] || t.terr) begin t.rstatus = 4; return; end
s = tsi_slot(pid);
if (s < 0) begin t.rstatus = 1; return; end
if (afc[1]) begin L = t.pkt[4]; if (L > 0) di = t.pkt[5][7]; end
if (afc == 2'b00 || (afc == 2'b10 && L != 183) || (afc == 2'b11 && L > 182)) begin t.rstatus = 6; return; end
if (afc == 2'b10) begin t.rstatus = 0; return; end
p0 = afc[1] ? 5 + L : 4;
if (!seen[s] || di || c == last[s] + 4'd1) t.rstatus = 0;
else if (c == last[s]) begin t.rstatus = 3; return; end
else t.rstatus = 2;
seen[s] = 1; last[s] = c;
for (int i = p0; i < 188; i++) t.odata.push_back(t.pkt[i]);
""",
    checks="""
if (!(t.rstatus inside {0, 2}) && t.odata.size() != 0) fail(t, "payload delivered for a dropped packet");
if (t.rstatus == 7) fail(t, "reserved status");
if (t.odata.size() > 184) fail(t, "payload longer than 184 bytes");
""",
    coverage="""
cp_status : coverpoint tr.rstatus { bins ok = {0}; bins filtered = {1}; bins gap = {2}; bins dup = {3};
                                    bins tei = {4}; bins sync = {5}; bins af = {6}; }
cp_pid    : coverpoint tr.rpid iff (tr.rstatus inside {0, 2}) { bins pat = {13'h0000}; bins v = {13'h0100};
                                                               bins a = {13'h0101}; bins s = {13'h0111}; }
cp_plen   : coverpoint tr.odata.size() iff (tr.rstatus inside {0, 2}) { bins none = {0}; bins one = {1};
                                                                       bins part = {[2:183]}; bins full = {184}; }
""",
    directed="""
// in-order traffic on every PID, both adaptation forms and their limits, each fault
for (int s = 0; s < 4; s++)
  for (int i = 0; i < 2; i++) begin t = item(); t.set(0, s, 8'h01 + 8'h10 * i); send(t); end
t = item(); t.set(0, 1, 8'h00); t.aflen = 8'h00; send(t);          // control 11, length 0
t = item(); t.set(0, 1, 8'd182); send(t);                          // control 11, length 182: 1 payload byte
t = item(); t.set(12, 1); send(t);
t = item(); t.set(13, 1); send(t);
t = item(); t.set(0, 1); send(t);
t = item(); t.set(14, 2, 8'd9); send(t);
for (int k = 15; k < 24; k++) begin
  t = item(); t.set(k, 3, 8'd41); t.seed = 32'h1F00 + k; send(t);
  t = item(); t.set(0, 3); send(t);
end
for (int i = 0; i < 18; i++) begin t = item(); t.set(0, 0, i); t.seed = i; send(t); end   // CC wraps
""",
    drain_ns=4000,
    model="""
module tsi_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        ts_valid,
  input  logic        ts_sync,
  input  logic [7:0]  ts_data,
  input  logic        ts_err,
  output logic        out_valid,
  output logic [7:0]  out_data,
  output logic        out_last,
  output logic        rep_valid,
  output logic [12:0] rep_pid,
  output logic [3:0]  rep_cc,
  output logic [2:0]  rep_status
);
  function automatic integer slot(input logic [12:0] pid);
    case (pid)
      13'h0000: slot = 0;
      13'h0100: slot = 1;
      13'h0101: slot = 2;
      13'h0111: slot = 3;
      default:  slot = -1;
    endcase
  endfunction

  logic [7:0]  rb [0:187];
  logic [7:0]  cnt, opos;
  logic        go, busy, perr;
  logic [6:0]  idle;
  logic [3:0]  last [0:3];
  logic [3:0]  seen;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cnt <= '0; opos <= '0; go <= 1'b0; busy <= 1'b0; perr <= 1'b0; idle <= '0; seen <= '0;
      for (int i = 0; i < 4; i++) last[i] <= 4'h0;
      out_valid <= 1'b0; out_data <= '0; out_last <= 1'b0;
      rep_valid <= 1'b0; rep_pid <= '0; rep_cc <= '0; rep_status <= '0;
    end else begin
      rep_valid <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
      go <= 1'b0;
      if (ts_valid) begin
        idle <= '0;
        if (ts_sync) begin
          if (cnt != 8'd0) begin rep_valid <= 1'b1; rep_status <= 3'd5; rep_pid <= '0; rep_cc <= '0; end
          rb[0] <= ts_data; cnt <= 8'd1; perr <= ts_err;
        end else if (cnt != 8'd0) begin
          rb[cnt] <= ts_data;
          if (ts_err) perr <= 1'b1;
          if (cnt == 8'd187) begin cnt <= '0; go <= 1'b1; end
          else cnt <= cnt + 8'd1;
        end
      end else if (cnt != 8'd0) begin
        idle <= idle + 7'd1;
        if (idle == 7'd63) begin
          cnt <= '0; rep_valid <= 1'b1; rep_status <= 3'd5; rep_pid <= '0; rep_cc <= '0;
        end
      end
      if (go) begin : packet
        logic [12:0] pid;
        logic [1:0]  afc;
        logic [3:0]  c;
        logic [7:0]  L;
        logic        di, pay;
        logic [2:0]  rs;
        integer      s;
        pid = {rb[1][4:0], rb[2]}; afc = rb[3][5:4]; c = rb[3][3:0];
        L = afc[1] ? rb[4] : 8'd0;
        di = afc[1] && L != 8'd0 && rb[5][7];
        s = slot(pid);
        pay = 1'b0;
        rep_pid <= pid; rep_cc <= c;
        if (rb[0] != 8'h47) begin rs = 3'd5; rep_pid <= '0; rep_cc <= '0; end
        else if (rb[1][7] || perr) rs = 3'd4;
        else if (s < 0) rs = 3'd1;
        else if (afc == 2'b00 || (afc == 2'b10 && L != 8'd183) || (afc == 2'b11 && L > 8'd182)) rs = 3'd6;
        else if (afc == 2'b10) rs = 3'd0;
        else if (!seen[s] || di || c == last[s] + 4'd1) begin rs = 3'd0; pay = 1'b1; end
        else if (c == last[s]) rs = 3'd3;
        else begin rs = 3'd2; pay = 1'b1; end
        rep_status <= rs;
        if (pay) begin
          seen[s] <= 1'b1; last[s] <= c;
          opos <= afc[1] ? 8'd5 + L : 8'd4; busy <= 1'b1;
        end else rep_valid <= 1'b1;
      end
      if (busy) begin
        out_valid <= 1'b1;
        out_data <= rb[opos];
        opos <= opos + 8'd1;
        if (opos == 8'd187) begin out_last <= 1'b1; busy <= 1'b0; rep_valid <= 1'b1; end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({ts_valid, out_valid, rep_valid}))
  else $error("TSI: X on a valid");
assert property (@(posedge clk) disable iff (!rst_n) ts_sync |-> ts_valid)
  else $error("TSI: ts_sync without ts_valid");
assert property (@(posedge clk) disable iff (!rst_n) ts_valid |-> !$isunknown({ts_sync, ts_data, ts_err}))
  else $error("TSI: X on a valid byte");
assert property (@(posedge clk) disable iff (!rst_n) out_last |-> out_valid && rep_valid && rep_status inside {3'd0, 3'd2})
  else $error("TSI: payload end without an accept report");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> rep_status != 3'd7)
  else $error("TSI: reserved status");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd2);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd3);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic ts_valid = 1'b0, ts_sync = 1'b0, ts_err = 1'b0;
logic [7:0] ts_data = 8'h00;
wire out_valid, out_last, rep_valid;
wire [7:0] out_data;
wire [12:0] rep_pid;
wire [3:0] rep_cc;
wire [2:0] rep_status;

always #5 clk = ~clk;

tsi_model u_dut (.clk(clk), .rst_n(rst_n), .ts_valid(ts_valid), .ts_sync(ts_sync), .ts_data(ts_data),
                 .ts_err(ts_err), .out_valid(out_valid), .out_data(out_data), .out_last(out_last),
                 .rep_valid(rep_valid), .rep_pid(rep_pid), .rep_cc(rep_cc), .rep_status(rep_status));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

logic [7:0] pb [0:187];
integer p0;
// packet: pid, cc, afc, adaptation length L (or -1), discontinuity, payload from v0
task automatic build(input logic [12:0] pid, input logic [3:0] cc, input logic [1:0] afc = 2'b01,
                     input integer L = -1, input logic di = 0, input logic [7:0] v0 = 8'h10);
  integer n;
  pb[0] = 8'h47; pb[1] = {3'b010, pid[12:8]}; pb[2] = pid[7:0]; pb[3] = {2'b00, afc, cc};
  n = 4;
  if (L >= 0) begin
    pb[4] = L; n = 5;
    if (L > 0) begin pb[5] = {di, 7'h00}; n = 6; end
    for (int i = 0; i < 188; i++) if (i >= n && i < 5 + L) pb[i] = 8'hFF;
    n = 5 + L;
  end
  p0 = n;
  for (int i = 0; i < 188; i++) if (i >= n) pb[i] = v0 + 8'd7 * i;
endtask

logic [7:0] ob [0:187];
integer on = 0, nrep = 0, nlast = 0, badlast = 0;
logic [12:0] r_pid;
logic [3:0] r_cc;
logic [2:0] r_st;
always @(posedge clk) begin
  if (out_valid) begin ob[on] = out_data; on = on + 1; end
  if (out_last) begin nlast = nlast + 1; if (!out_valid || !rep_valid) badlast = badlast + 1; end
  if (rep_valid && out_valid && !out_last) badlast = badlast + 1;
  if (rep_valid) begin nrep = nrep + 1; r_pid = rep_pid; r_cc = rep_cc; r_st = rep_status; end
end
task automatic send(input integer len = 188, input integer errb = -1, input integer gap = 0);
  integer r0, k;
  r0 = nrep; on = 0;
  for (int i = 0; i < 188; i++)
    if (i < len) begin
      if (gap != 0 && i % gap == 1) begin @(negedge clk); ts_valid = 0; ts_sync = 0; ts_err = 0; @(negedge clk); end
      @(negedge clk); ts_valid = 1; ts_sync = (i == 0); ts_data = pb[i]; ts_err = (i == errb);
    end
  @(negedge clk); ts_valid = 0; ts_sync = 0; ts_err = 0;
  k = 0;
  while (k < 400 && nrep == r0) begin @(negedge clk); k = k + 1; end
  @(negedge clk);
endtask
function automatic logic got(input logic [2:0] st, input logic [12:0] pid, input logic [3:0] cc);
  got = r_st == st && r_pid == pid && r_cc == cc;
endfunction
function automatic logic delivered();
  logic ok;
  ok = (on == 188 - p0);
  for (int i = 0; i < 188; i++) if (i < 188 - p0 && ob[i] !== pb[p0 + i]) ok = 0;
  delivered = ok;
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && out_valid === 1'b0, "nothing out in reset");
  rst_n = 1;
  repeat (30) @(negedge clk);
  chk(nrep == 0 && on == 0 && nlast == 0, "nothing out after reset without input");
  build(13'h0000, 4'd5); send(); chk(got(0, 0, 5) && delivered() && on == 184, "PAT, first packet: any CC, 184 bytes");
  build(13'h0000, 4'd6); send(188, -1, 3); chk(got(0, 0, 6) && delivered(), "CC + 1 with ts_valid gaps");
  build(13'h0100, 4'd0, 2'b11, 0); send(); chk(got(0, 13'h100, 0) && on == 183, "adaptation length 0");
  build(13'h0100, 4'd1, 2'b11, 182); send(); chk(got(0, 13'h100, 1) && on == 1 && delivered(), "adaptation length 182");
  build(13'h0100, 4'd1); send(); chk(got(3, 13'h100, 1) && on == 0, "same CC: duplicate dropped");
  build(13'h0100, 4'd2); send(); chk(got(0, 13'h100, 2) && delivered(), "then CC + 1");
  build(13'h0100, 4'd9); send(); chk(got(2, 13'h100, 9) && delivered(), "CC 9 after 2: discontinuity, delivered");
  build(13'h0100, 4'd10); send(); chk(got(0, 13'h100, 10), "tracking restarted at 9");
  build(13'h0100, 4'd3, 2'b11, 7, 1); send(); chk(got(0, 13'h100, 3) && delivered(), "discontinuity_indicator: any CC");
  build(13'h0100, 4'd3, 2'b11, 7, 0); send(); chk(got(3, 13'h100, 3) && on == 0, "duplicate with an adaptation field (no discontinuity flag)");
  build(13'h0100, 4'd3, 2'b10, 183); send(); chk(got(0, 13'h100, 3) && on == 0, "adaptation only: no payload");
  build(13'h0100, 4'd4, 2'b10, 100); send(); chk(got(6, 13'h100, 4), "control 10 with length 100");
  build(13'h0100, 4'd4, 2'b11, 183); send(); chk(got(6, 13'h100, 4), "control 11 with length 183");
  build(13'h0100, 4'd4, 2'b00); send(); chk(got(6, 13'h100, 4), "control 00");
  build(13'h0101, 4'd0); pb[1][7] = 1; send(); chk(got(4, 13'h101, 0) && on == 0, "TEI set: dropped");
  build(13'h0101, 4'd0); send(188, 77); chk(got(4, 13'h101, 0) && on == 0, "ts_err on byte 77: dropped");
  build(13'h0101, 4'd0); pb[0] = 8'h46; send(); chk(got(5, 0, 0), "sync byte 0x46");
  build(13'h0101, 4'd0); send(100); chk(got(5, 0, 0) && on == 0, "cut after 100 bytes: timeout");
  build(13'h1FFF, 4'd0); send(); chk(got(1, 13'h1FFF, 0) && on == 0, "null packet");
  build(13'h0102, 4'd0); send(); chk(got(1, 13'h102, 0), "PID not filtered");
  build(13'h0101, 4'd0); send(); chk(got(0, 13'h101, 0) && delivered(), "PID 0x101 first packet after the faults");
  build(13'h0111, 4'd15); send(); chk(got(0, 13'h111, 15), "PID 0x111 CC 15");
  build(13'h0111, 4'd0); send(); chk(got(0, 13'h111, 0), "CC wraps 15 -> 0");
  // sync in the middle of a packet: the partial one is reported, the new one received
  build(13'h0000, 4'd7); send(50); chk(got(5, 0, 0), "50-byte packet");
  build(13'h0000, 4'd7); send(); chk(got(0, 0, 7) && delivered(), "PAT CC 7");
  chk(badlast == 0, "out_last only on the last payload byte, with the report");
  chk(nlast == 12, $sformatf("one out_last per delivered packet (%0d)", nlast));
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
