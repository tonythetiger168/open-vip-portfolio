# Scale-up Ethernet transport (SUE / ESUN style) VIP: reliable, in-order
# delivery per virtual channel between accelerators over Ethernet with
# packet sequence numbers and ACK / NACK (go-back-N). The frame layout and
# codes are this VIP's own; they follow the shape of the SUE transport
# (sequence numbers per VC, ACK of the last in-order packet, NACK of the
# expected one, retransmission from it), not its bit encoding.
#
# Agent -> DUT, a byte per clock (in_valid, in_data, in_last):
#   DA, SA, EtherType 0x88B5, SUE header {version 1 | opcode 0 (data)},
#   {VC[1:0], 6'h0}, destination XPU ID[15:0], PSN[15:0], payload length[15:0],
#   payload (1..64 bytes), CRC-32 over header and payload (IEEE, LSB first).
# DUT -> agent: the delivered payload (out_valid, out_data, out_last) and one
# report per frame (rep_valid, rep_type: 0 ACK, 1 NACK, 2 dropped; rep_vc,
# rep_psn, rep_reason).
#
# tb/top_tb.sv sue_model: the receiving XPU 0x0042 with an expected PSN per
# VC (0 after reset). Checks in order:
#   reason 5  shorter than an empty frame, EtherType, version or opcode wrong: dropped
#   reason 3  CRC wrong: NACK of the header VC's expected PSN
#   reason 6  length field not the payload size (or 0 / over 64): dropped
#   reason 4  another destination: dropped
#   reason 0  PSN = expected: delivered, ACK(PSN), expected + 1
#   reason 1  PSN behind (expected - PSN mod 2^16 in 1..32768): ACK(expected - 1)
#   reason 2  PSN ahead: NACK(expected), dropped
# Credit-based flow control is not modelled.

SUE_FUNCS = """
localparam bit [15:0] SUE_ETYPE = 16'h88B5;
localparam bit [15:0] SUE_XPU   = 16'h0042;
function automatic bit [31:0] sue_crc32(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction
"""

SPEC = dict(
    vip="SUE-UVM-VIP", p="sue", P="SUE", dir="sue", family="AI Interconnect",
    desc="Scale-up Ethernet transport VIP (SUE / ESUN style): data frames with VC, destination XPU, PSN and CRC; "
         "receiver model with in-order delivery per VC, ACK / NACK (go-back-N), duplicates, gaps and drops.",
    about="""
Scale-up Ethernet (Broadcom's SUE, the OCP ESUN work) carries accelerator
memory traffic over Ethernet with a thin reliable transport: each virtual
channel numbers its packets, the receiver delivers them in order,
acknowledges the last good one and NACKs a gap so the sender goes back and
retransmits. The agent is the sending XPU: it keeps a PSN per VC, plants
gaps, duplicates, CRC errors and header faults, and on a gap keeps its own
PSN so the next frame is the retransmission. The DUT model is the receiving
XPU; the scoreboard keeps the expected PSN of every VC and predicts each
ACK, NACK, drop and delivered payload. Frame encodings are this VIP's own.""",
    defs=SUE_FUNCS,
    timeout=1000,
    ports=[
        ("in", "logic", "in_valid"), ("in", "logic [7:0]", "in_data"), ("in", "logic", "in_last"),
        ("out", "logic", "out_valid"), ("out", "logic [7:0]", "out_data"), ("out", "logic", "out_last"),
        ("out", "logic", "rep_valid"), ("out", "logic [1:0]", "rep_type"), ("out", "logic [1:0]", "rep_vc"),
        ("out", "logic [15:0]", "rep_psn"), ("out", "logic [2:0]", "rep_reason"),
    ],
    fields=[
        ("bit [7:0]", "frame", "req", "q"),
        ("bit [1:0]", "rtype", "rsp"),
        ("bit [1:0]", "rvc", "rsp"),
        ("bit [15:0]", "rpsn", "rsp"),
        ("bit [2:0]", "reason", "rsp"),
        ("bit [7:0]", "odata", "rsp", "q"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "vc", "info", "rand"),
        ("bit [5:0]", "len_r", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [15:0]", "psn", "info"),
    ],
    tr_functions="""
// kind: 0-17 in order, 18-19 duplicate, 20-21 gap, 22 CRC, 23 destination, 24 version, 25 opcode,
// 26 EtherType, 27 length field, 28 runt, 29-31 in order
function void set(int k, bit [1:0] v, int n); kind = k; vc = v; len_r = n - 1; endfunction
function void build(bit [15:0] p);
  bit [31:0] x = seed | 1, c = 32'hFFFF_FFFF;
  bit [15:0] n = len_r + 1;
  psn = p;
  frame.delete();
  for (int i = 0; i < 6; i++) frame.push_back(8'h02 + i);
  for (int i = 0; i < 6; i++) frame.push_back(8'h12 + i);
  frame.push_back((kind == 26) ? 8'h08 : SUE_ETYPE[15:8]); frame.push_back((kind == 26) ? 8'h00 : SUE_ETYPE[7:0]);
  frame.push_back({(kind == 24) ? 4'h2 : 4'h1, (kind == 25) ? 4'h1 : 4'h0});
  frame.push_back({vc, 6'h0});
  frame.push_back((kind == 23) ? 8'h00 : SUE_XPU[15:8]); frame.push_back((kind == 23) ? 8'h43 : SUE_XPU[7:0]);
  frame.push_back(p[15:8]); frame.push_back(p[7:0]);
  frame.push_back(8'h00); frame.push_back((kind == 27) ? 8'(n + 1) : n[7:0]);
  for (int i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    frame.push_back(x[7:0]);
  end
  for (int i = 14; i < frame.size(); i++) c = sue_crc32(c, frame[i]);
  c = ~c;
  if (kind == 22) c[17] = ~c[17];
  for (int i = 0; i < 4; i++) frame.push_back(c[8*i +: 8]);
  if (kind == 28) while (frame.size() > 20) void'(frame.pop_back());
endfunction
""",
    drv_rsp=True,
    drv_desc="one frame per item with the PSN from the driver's per-VC counter (planted duplicate / gap PSNs leave the counter, so the next frame is the retransmission); then the delivered payload and the report",
    drv_members="bit [15:0] nxt [4] = '{0, 0, 0, 0};",
    drv_idle="""
vif.drv_cb.in_valid <= 1'b0;
vif.drv_cb.in_data  <= 8'h00;
vif.drv_cb.in_last  <= 1'b0;
""",
    drv_item="""
bit [15:0] p = nxt[t.vc];
int k = 0;
if (t.kind inside {18, 19}) p = nxt[t.vc] - 1 - t.seed[2:0];
else if (t.kind inside {20, 21}) p = nxt[t.vc] + 1 + t.seed[2:0];
else if (!(t.kind inside {[22:28]})) nxt[t.vc]++;
t.build(p);
foreach (t.frame[i]) begin
  vif.drv_cb.in_valid <= 1'b1; vif.drv_cb.in_data <= t.frame[i]; vif.drv_cb.in_last <= (i == t.frame.size() - 1);
  @(vif.drv_cb);
end
vif.drv_cb.in_valid <= 1'b0; vif.drv_cb.in_last <= 1'b0;
t.odata.delete();
do begin
  @(vif.drv_cb);
  if (vif.drv_cb.out_valid) t.odata.push_back(vif.drv_cb.out_data);
  k++;
end while (!vif.drv_cb.rep_valid && k < cfg.timeout_cycles);
if (!vif.drv_cb.rep_valid) `uvm_error("DRV", "SUE: no report for a frame")
t.rtype = vif.drv_cb.rep_type; t.rvc = vif.drv_cb.rep_vc; t.rpsn = vif.drv_cb.rep_psn; t.reason = vif.drv_cb.rep_reason;
repeat (2) @(vif.drv_cb);
""",
    mon_desc="frames into the receiver, then the delivered payload and the report that close each one",
    mon_run="""
bit [7:0] b[$], o[$];
bit [7:0] frames[$][$];
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.in_valid) begin
    b.push_back(vif.mon_cb.in_data);
    if (vif.mon_cb.in_last) begin frames.push_back(b); b.delete(); end
  end
  if (vif.mon_cb.out_valid) o.push_back(vif.mon_cb.out_data);
  if (vif.mon_cb.rep_valid) begin
    if (frames.size() == 0) `uvm_error("MON", "SUE: report without a frame")
    else begin
      sue_transaction t = sue_transaction::type_id::create("t");
      t.frame = frames.pop_front();
      t.odata = o;
      t.rtype = vif.mon_cb.rep_type; t.rvc = vif.mon_cb.rep_vc; t.rpsn = vif.mon_cb.rep_psn; t.reason = vif.mon_cb.rep_reason;
      publish(t);
    end
    o.delete();
  end
end
""",
    sb_members="bit [15:0] exp_psn [4] = '{0, 0, 0, 0};",
    predict="""
int n = t.frame.size(), len;
bit [31:0] c = 32'hFFFF_FFFF;
bit [15:0] p, d;
bit [1:0] v;
t.odata.delete();
t.rtype = 2; t.rvc = 0; t.rpsn = 0;
if (n < 26 || {t.frame[12], t.frame[13]} != SUE_ETYPE || t.frame[14] != 8'h10) t.reason = 5;
else begin
  v = t.frame[15][7:6];
  for (int i = 14; i < n; i++) c = sue_crc32(c, t.frame[i]);
  len = {t.frame[20], t.frame[21]};
  p = {t.frame[18], t.frame[19]};
  if (c != 32'hDEBB_20E3) begin t.reason = 3; t.rtype = 1; t.rvc = v; t.rpsn = exp_psn[v]; end
  else if (len != n - 26 || len == 0 || len > 64) t.reason = 6;
  else if ({t.frame[16], t.frame[17]} != SUE_XPU) t.reason = 4;
  else begin
    t.rvc = v;
    d = exp_psn[v] - p;
    if (p == exp_psn[v]) begin
      t.reason = 0; t.rtype = 0; t.rpsn = p;
      for (int i = 0; i < len; i++) t.odata.push_back(t.frame[22 + i]);
      exp_psn[v]++;
    end else if (d >= 1 && d <= 16'h8000) begin t.reason = 1; t.rtype = 0; t.rpsn = exp_psn[v] - 1; end
    else begin t.reason = 2; t.rtype = 1; t.rpsn = exp_psn[v]; end
  end
end
""",
    checks="""
if (t.reason != 0 && t.odata.size() != 0) fail(t, "payload delivered for a frame that was not in order");
""",
    coverage="""
cp_reason : coverpoint tr.reason { bins in_order = {0}; bins duplicate = {1}; bins gap = {2}; bins crc = {3};
                                     bins dest = {4}; bins header = {5}; bins length = {6}; }
cp_vc : coverpoint tr.rvc iff (tr.reason == 0);
cp_len : coverpoint tr.odata.size() iff (tr.reason == 0) { bins one = {1}; bins short_p = {[2:16]}; bins long_p = {[17:64]}; }
""",
    directed="""
// in order on every VC, a duplicate, a gap and its retransmission, each fault
for (int v = 0; v < 4; v++)
  for (int i = 0; i < 2; i++) begin t = item(); t.set(0, v, 1 + 21 * i + v); send(t); end
t = item(); t.set(18, 1, 8); send(t);
t = item(); t.set(20, 1, 8); send(t);
t = item(); t.set(0, 1, 64); send(t);
for (int k = 22; k < 29; k++) begin
  t = item(); t.set(k, 2, 10); send(t);
  t = item(); t.set(0, 2, 10); send(t);
end
""",
    drain_ns=2000,
    model="""
module sue_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        in_valid,
  input  logic [7:0]  in_data,
  input  logic        in_last,
  output logic        out_valid,
  output logic [7:0]  out_data,
  output logic        out_last,
  output logic        rep_valid,
  output logic [1:0]  rep_type,
  output logic [1:0]  rep_vc,
  output logic [15:0] rep_psn,
  output logic [2:0]  rep_reason
);
  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    logic [31:0] x;
    x = c ^ {24'h0, b};
    for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
    crc32_byte = x;
  endfunction

  logic [7:0]  rb [0:127];
  logic [7:0]  nrb, olen, opos;
  logic        go, busy;
  logic [15:0] expp [0:3];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nrb <= '0; olen <= '0; opos <= '0; go <= 1'b0; busy <= 1'b0;
      for (int i = 0; i < 4; i++) expp[i] <= 16'h0;
      out_valid <= 1'b0; out_data <= '0; out_last <= 1'b0;
      rep_valid <= 1'b0; rep_type <= '0; rep_vc <= '0; rep_psn <= '0; rep_reason <= '0;
    end else begin
      rep_valid <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
      go <= in_valid && in_last;
      if (in_valid) begin
        if (nrb < 8'd128) rb[nrb[6:0]] <= in_data;
        nrb <= nrb + 8'd1;
      end
      if (go) begin : receive
        logic [31:0] c;
        logic [15:0] p, d, len, e;
        logic [1:0]  v, ty;
        logic [2:0]  rs;
        logic [15:0] rp;
        integer      n;
        n = nrb;
        nrb <= '0;
        ty = 2'd2; rp = 16'h0; v = rb[15][7:6];
        e = expp[v];
        if (n < 26 || {rb[12], rb[13]} != 16'h88B5 || rb[14] != 8'h10) begin rs = 3'd5; v = 2'd0; end
        else begin
          c = 32'hFFFF_FFFF;
          for (int i = 14; i < 128; i++) if (i < n) c = crc32_byte(c, rb[i]);
          len = {rb[20], rb[21]};
          p = {rb[18], rb[19]};
          if (c != 32'hDEBB_20E3) begin rs = 3'd3; ty = 2'd1; rp = e; end
          else if (len != n - 26 || len == 16'd0 || len > 16'd64) begin rs = 3'd6; v = 2'd0; end
          else if ({rb[16], rb[17]} != 16'h0042) begin rs = 3'd4; v = 2'd0; end
          else begin
            d = e - p;
            if (p == e) begin
              rs = 3'd0; ty = 2'd0; rp = p;
              expp[v] <= e + 16'd1;
              olen <= len[7:0]; opos <= '0; busy <= 1'b1;
            end else if (d >= 16'd1 && d <= 16'h8000) begin rs = 3'd1; ty = 2'd0; rp = e - 16'd1; end
            else begin rs = 3'd2; ty = 2'd1; rp = e; end
          end
        end
        rep_type <= ty; rep_vc <= v; rep_psn <= rp; rep_reason <= rs;
        if (rs != 3'd0) rep_valid <= 1'b1;
      end
      if (busy) begin
        out_valid <= 1'b1;
        out_data <= rb[22 + opos];
        opos <= opos + 8'd1;
        if (opos == olen - 8'd1) begin out_last <= 1'b1; busy <= 1'b0; rep_valid <= 1'b1; end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({in_valid, out_valid, rep_valid}))
  else $error("SUE: X on a valid");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> !$isunknown({rep_type, rep_vc, rep_psn, rep_reason}))
  else $error("SUE: X in a report");
assert property (@(posedge clk) disable iff (!rst_n) out_last |-> rep_valid && rep_type == 2'd0 && rep_reason == 3'd0)
  else $error("SUE: delivered payload without an in-order ACK");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_type == 2'd1);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_reason == 3'd1);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic in_valid = 1'b0, in_last = 1'b0;
logic [7:0] in_data = 8'h00;
wire out_valid, out_last, rep_valid;
wire [7:0] out_data;
wire [1:0] rep_type, rep_vc;
wire [15:0] rep_psn;
wire [2:0] rep_reason;

always #5 clk = ~clk;

sue_model u_dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data), .in_last(in_last),
                 .out_valid(out_valid), .out_data(out_data), .out_last(out_last), .rep_valid(rep_valid),
                 .rep_type(rep_type), .rep_vc(rep_vc), .rep_psn(rep_psn), .rep_reason(rep_reason));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic logic [31:0] crc32(input logic [31:0] c, input logic [7:0] b);
  logic [31:0] x;
  x = c ^ {24'h0, b};
  for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
  crc32 = x;
endfunction

logic [7:0] fb [0:127];
integer fn;
// data frame: vc, psn, n payload bytes from v0; dest; then the CRC
task automatic build(input integer vc, input logic [15:0] psn, input integer n, input logic [7:0] v0,
                     input logic [15:0] dest = 16'h0042);
  logic [31:0] c;
  for (int i = 0; i < 128; i++) fb[i] = 8'h00;
  for (int i = 0; i < 12; i++) fb[i] = 8'hA0 + i;
  fb[12] = 8'h88; fb[13] = 8'hB5; fb[14] = 8'h10; fb[15] = {vc[1:0], 6'h0};
  fb[16] = dest[15:8]; fb[17] = dest[7:0]; fb[18] = psn[15:8]; fb[19] = psn[7:0]; fb[20] = 8'h00; fb[21] = n;
  for (int i = 0; i < n; i++) fb[22 + i] = v0 + 8'd29 * i;
  fn = 22 + n;
  c = 32'hFFFF_FFFF;
  for (int i = 14; i < 128; i++) if (i < fn) c = crc32(c, fb[i]);
  c = ~c;
  fb[fn] = c[7:0]; fb[fn + 1] = c[15:8]; fb[fn + 2] = c[23:16]; fb[fn + 3] = c[31:24];
  fn = fn + 4;
endtask
task automatic recrc();
  logic [31:0] c;
  c = 32'hFFFF_FFFF;
  for (int i = 14; i < 128; i++) if (i < fn - 4) c = crc32(c, fb[i]);
  c = ~c;
  fb[fn - 4] = c[7:0]; fb[fn - 3] = c[15:8]; fb[fn - 2] = c[23:16]; fb[fn - 1] = c[31:24];
endtask

logic [7:0] ob [0:127];
integer on = 0, nrep = 0, nlast = 0;
logic [1:0] r_ty, r_vc;
logic [15:0] r_psn;
logic [2:0] r_rs;
always @(posedge clk) begin
  if (out_valid) begin ob[on] = out_data; on = on + 1; if (out_last) nlast = nlast + 1; end
  if (rep_valid) begin nrep = nrep + 1; r_ty = rep_type; r_vc = rep_vc; r_psn = rep_psn; r_rs = rep_reason; end
end
task automatic send();
  integer r0, k;
  r0 = nrep; on = 0;
  for (int i = 0; i < 128; i++)
    if (i < fn) begin @(negedge clk); in_valid = 1; in_data = fb[i]; in_last = (i == fn - 1); end
  @(negedge clk); in_valid = 0; in_last = 0;
  k = 0;
  while (k < 200 && nrep == r0) begin @(negedge clk); k = k + 1; end
  @(negedge clk);
endtask
function automatic logic got(input logic [1:0] ty, input logic [1:0] vc, input logic [15:0] psn, input logic [2:0] rs);
  got = r_ty == ty && r_vc == vc && r_psn == psn && r_rs == rs;
endfunction
function automatic logic delivered(input integer n);
  logic ok;
  ok = (on == n);
  for (int i = 0; i < 128; i++) if (i < n && ob[i] !== fb[22 + i]) ok = 0;
  delivered = ok;
endfunction

initial begin
  integer r;
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && out_valid === 1'b0 && out_last === 1'b0, "nothing out in reset");
  rst_n = 1;
  repeat (4) @(negedge clk);
  chk(nrep == 0, "no report without a frame");

  build(0, 0, 1, 8'h11); send(); chk(got(0, 0, 0, 0) && delivered(1), "VC 0 PSN 0, 1 byte: ACK 0, delivered");
  build(0, 1, 64, 8'h12); send(); chk(got(0, 0, 1, 0) && delivered(64), "VC 0 PSN 1, 64 bytes");
  build(3, 0, 17, 8'h13); send(); chk(got(0, 3, 0, 0) && delivered(17), "VC 3 has its own PSN");
  build(2, 0, 5, 8'h14); send(); chk(got(0, 2, 0, 0) && delivered(5), "VC 2 PSN 0");
  build(1, 0, 9, 8'h15); send(); chk(got(0, 1, 0, 0) && delivered(9), "VC 1 PSN 0");
  // duplicate, gap, retransmission
  build(0, 1, 8, 8'h16); send(); chk(got(0, 0, 1, 1) && on == 0, "VC 0 PSN 1 again: duplicate, ACK 1, not delivered");
  build(0, 0, 8, 8'h17); send(); chk(got(0, 0, 1, 1), "VC 0 PSN 0: duplicate, ACK of the last (1)");
  build(0, 3, 8, 8'h18); send(); chk(got(1, 0, 2, 2) && on == 0, "VC 0 PSN 3 where 2 is due: NACK 2, dropped");
  build(0, 2, 8, 8'h19); send(); chk(got(0, 0, 2, 0) && delivered(8), "retransmitted PSN 2: delivered");
  build(0, 3, 8, 8'h1A); send(); chk(got(0, 0, 3, 0) && delivered(8), "then PSN 3");
  build(0, 16'h8003, 8, 8'h1B); send(); chk(got(1, 0, 4, 2), "PSN 0x8003 (32767 ahead): gap, NACK 4");
  build(0, 16'h8004, 8, 8'h1C); send(); chk(got(0, 0, 3, 1), "PSN 0x8004 (32768 behind): duplicate, ACK 3");
  // faults
  build(1, 1, 10, 8'h20); fb[25] = fb[25] ^ 8'h04; send(); chk(got(1, 1, 1, 3) && on == 0, "payload bit flipped: CRC NACK of VC 1's 1");
  build(1, 1, 10, 8'h21); fb[fn - 1] = fb[fn - 1] ^ 8'h80; send(); chk(got(1, 1, 1, 3), "CRC bit flipped");
  build(2, 1, 10, 8'h22, 16'h0043); send(); chk(got(2, 0, 0, 4) && on == 0, "XPU 0x0043: dropped");
  build(2, 1, 10, 8'h23); fb[14] = 8'h20; recrc(); send(); chk(got(2, 0, 0, 5), "version 2: dropped");
  build(2, 1, 10, 8'h24); fb[14] = 8'h11; recrc(); send(); chk(got(2, 0, 0, 5), "opcode 1: dropped");
  build(2, 1, 10, 8'h25); fb[12] = 8'h08; fb[13] = 8'h00; send(); chk(got(2, 0, 0, 5), "EtherType 0x0800: dropped");
  build(2, 1, 10, 8'h26); fb[21] = 8'd11; recrc(); send(); chk(got(2, 0, 0, 6), "length field 11 for 10 bytes: dropped");
  build(2, 1, 10, 8'h27); fb[21] = 8'd9; recrc(); send(); chk(got(2, 0, 0, 6), "length field 9 for 10 bytes: dropped");
  build(2, 1, 0, 8'h28); send(); chk(got(2, 0, 0, 6), "empty payload: dropped");
  build(2, 1, 65, 8'h29); send(); chk(got(2, 0, 0, 6), "65-byte payload: dropped");
  build(2, 1, 10, 8'h2A); fn = 25; send(); chk(got(2, 0, 0, 5), "25-byte runt: dropped");
  build(2, 1, 10, 8'h2B); send(); chk(got(0, 2, 1, 0) && delivered(10), "VC 2 PSN 1 after the drops");
  build(1, 1, 10, 8'h2C); send(); chk(got(0, 1, 1, 0) && delivered(10), "VC 1 PSN 1 after its CRC NACKs");
  build(3, 1, 3, 8'h2D); send(); chk(got(0, 3, 1, 0) && delivered(3), "VC 3 untouched");
  // a long in-order run on VC 3
  for (int i = 2; i < 6; i++) begin build(3, i, 2, 8'h30 + i); send(); end
  r = 1;
  for (int i = 6; i < 70; i++) begin build(3, i, 1, i); send(); if (!got(0, 3, i, 0)) r = 0; end
  chk(r == 1, "VC 3 PSN 6..69 in order");
  chk(nlast == 78, $sformatf("one last-byte strobe per delivered frame (%0d)", nlast));

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
