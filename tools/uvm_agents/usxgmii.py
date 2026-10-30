# USXGMII transmit agent (Cisco USXGMII, single port): Ethernet frames on a
# 64-bit XGMII, rate adaptation by replication, IEEE 802.3 clause 49
# 64b/66b encoding and the x^58 + x^39 + 1 self-synchronizing scrambler.
#
# Wires: blk_valid, blk[65:0] (one 66-bit block per clock while valid: blk[1:0]
# sync header 2'b01 data / 2'b10 control, blk[65:2] the scrambled payload,
# payload bit 0 first) and rate[1:0] (0 = 10G, 1 = 5G, 2 = 2.5G, 3 = 1G).
# At a rate below 10G every block is sent R = 1 / 2 / 4 / 10 times; the
# receiver keeps the first copy and checks the others against it.
# Frames start in lane 0: block type 0x78 with the preamble 55 55 55 55 55 55
# and SFD D5, data blocks of 8 bytes, then a terminate block with the last 0..7
# bytes (types 0x87 0x99 0xAA 0xB4 0xCC 0xD2 0xE1 0xFF); idle blocks are type
# 0x1E with 7-bit idle codes 0x00, an error block type 0x1E with /E/ codes.
#
# tb/top_tb.sv usxgmii_model: the receive PCS. It descrambles, keeps one block
# per replication group (taking the rate at the first block of a group),
# decodes and reports each frame one clock after its terminate block: the MAC
# frame length (FCS included), its CRC-32, FCS good (CRC residue 0xDEBB20E3)
# and an error code: 1 invalid sync header, 2 a replica differing from the
# first copy, 4 a control block other than terminate inside a frame (error,
# idle, a second start), 8 preamble / SFD wrong (the frame is still received).
# Error codes 1, 2 and 4 end the frame; the bytes taken before it are
# reported. Outside a frame data blocks, bad headers and replica differences
# are ignored. 100M and 10M (100 and 1000 copies) are not modelled.

USX_FUNCS = """
// IEEE CRC-32 step (reflected, not inverted): residue 0xDEBB20E3 over a frame with its FCS
function automatic bit [31:0] usx_crc32(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction
function automatic int usx_reps(bit [1:0] rate);
  case (rate) 2'd0: return 1; 2'd1: return 2; 2'd2: return 4; default: return 10; endcase
endfunction
// terminate block types for 0..7 bytes
function automatic bit [7:0] usx_term(int n);
  case (n)
    0: return 8'h87; 1: return 8'h99; 2: return 8'hAA; 3: return 8'hB4;
    4: return 8'hCC; 5: return 8'hD2; 6: return 8'hE1; default: return 8'hFF;
  endcase
endfunction
function automatic int usx_term_n(bit [7:0] t);
  case (t)
    8'h87: return 0; 8'h99: return 1; 8'hAA: return 2; 8'hB4: return 3;
    8'hCC: return 4; 8'hD2: return 5; 8'hE1: return 6; 8'hFF: return 7;
    default: return -1;
  endcase
endfunction
"""

SPEC = dict(
    vip="USXGMII-UVM-VIP", p="usxgmii", P="USXGMII", dir="usxgmii", family="Networking",
    desc="USXGMII transmit VIP: 64b/66b blocks (clause 49), self-synchronizing scrambler, rate adaptation by "
         "replication (10G / 5G / 2.5G / 1G), start / data / terminate / idle blocks, FCS, header / replica / control faults.",
    about="""
USXGMII carries one Ethernet port at 10M to 10G over a single 10.3125 Gb/s
SerDes lane: the MAC's XGMII stream is replicated to slow it down, then 64b/66b
encoded and scrambled as in 10GBASE-R. It is the MAC-to-PHY link of multi-gig
copper PHYs. The agent builds that stream from frames; the DUT model is the
receive PCS (descrambler, replication check, block decoder) and reports every
frame. The scoreboard predicts each report from the bytes the monitor's own
descrambler and decoder recovered, and the monitor and driver agree on the
fault the agent planted (an invalid sync header, a replica that differs, an
error block, a wrong preamble), so a descrambler tap, a replication count or
a terminate-lane mistake shows up as a mismatch.""",
    defs=USX_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "blk_valid"), ("in", "logic [65:0]", "blk"), ("in", "logic [1:0]", "rate"),
        ("out", "logic", "rep_valid"), ("out", "logic [7:0]", "rep_len"), ("out", "logic [31:0]", "rep_crc"),
        ("out", "logic", "rep_fcs_ok"), ("out", "logic [3:0]", "rep_err"),
    ],
    fields=[
        ("bit [7:0]", "data", "req", "q"),      # MAC frame with FCS (cut at a fault)
        ("bit [1:0]", "speed", "req"),
        ("bit [2:0]", "fault", "req"),          # 1 bad header, 2 replica differs, 3 error block, 4 bad SFD
        ("bit [3:0]", "fpos", "req"),           # data block of the fault
        ("bit", "bad_fcs", "req"),
        ("bit [7:0]", "rlen", "rsp"),
        ("bit [31:0]", "rcrc", "rsp"),
        ("bit", "fcs_ok", "rsp"),
        ("bit [3:0]", "err", "rsp"),
        ("bit [6:0]", "nbytes", "info", "rand"),
        ("bit [1:0]", "gap", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len   { nbytes >= 8; nbytes <= 80; }
constraint c_speed { speed dist { 0 := 4, 1 := 3, 2 := 3, 3 := 2 }; }
constraint c_fault { fault dist { 0 := 16, 1 := 1, 2 := 1, 3 := 1, 4 := 1 }; bad_fcs dist { 0 := 12, 1 := 1 }; }
""",
    tr_functions="""
// payload from the seed, FCS appended (inverted in bit 0 when bad_fcs);
// a fault falls on a whole data block, a replica fault needs replicas
function void post_randomize();
  bit [31:0] x = seed | 1, c = 32'hFFFF_FFFF;
  data.delete();
  for (int i = 0; i < nbytes; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    data.push_back(x[7:0]);
    c = usx_crc32(c, x[7:0]);
  end
  c = ~c ^ {31'h0, bad_fcs};
  for (int i = 0; i < 4; i++) data.push_back(c[8*i +: 8]);
  if (fault > 4 || (fault == 2 && speed == 0)) fault = 0;
  fpos = (fault inside {1, 2, 3}) ? x[19:16] % (data.size() / 8) : 0;
endfunction
""",
    drv_rsp=False,
    drv_desc="frames as 64b/66b blocks: start with preamble, data, terminate, idle gap; scrambled, each block repeated for the rate; planted header / replica / error-block / preamble faults",
    drv_members="bit [57:0] scr = '0;   // scrambler state (last 58 scrambled bits)",
    drv_idle="""
vif.drv_cb.blk_valid <= 1'b0;
vif.drv_cb.blk       <= '0;
vif.drv_cb.rate      <= '0;
""",
    drv_tasks="""
// scramble one payload and send it R times (copy 1 replaced by alt when given)
task send_blk(bit [1:0] sh, bit [63:0] pl, int reps, bit use_alt = 0, bit [63:0] alt = 0);
  for (int r = 0; r < reps; r++) begin
    bit [63:0] p = (use_alt && r == 1) ? alt : pl, s;
    for (int i = 0; i < 64; i++) begin
      s[i] = p[i] ^ scr[38] ^ scr[57];
      scr = {scr[56:0], s[i]};
    end
    vif.drv_cb.blk_valid <= 1'b1;
    vif.drv_cb.blk <= {s, sh};
    @(vif.drv_cb);
  end
endtask
""",
    drv_item="""
int R = usx_reps(t.speed), nfull = t.data.size() / 8, nd;
bit [63:0] pl;
vif.drv_cb.rate <= t.speed;
// start: type 0x78, preamble, SFD (planted: SFD 0xD4)
send_blk(2'b10, {(t.fault == 4) ? 8'hD4 : 8'hD5, {6{8'h55}}, 8'h78}, R);
nd = nfull;
for (int b = 0; b < nfull; b++) begin
  for (int i = 0; i < 8; i++) pl[8*i +: 8] = t.data[8*b + i];
  if (t.fault == 1 && b == t.fpos) begin send_blk(2'b00, pl, R); nd = b; break; end
  if (t.fault == 3 && b == t.fpos) begin send_blk(2'b10, {{8{7'h1E}}, 8'h1E}, R); nd = b; break; end
  if (t.fault == 2 && b == t.fpos) begin send_blk(2'b01, pl, R, 1, pl ^ 64'h0000_0100_0000_0000); nd = b + 1; break; end
  send_blk(2'b01, pl, R);
end
if (t.fault inside {1, 2, 3}) begin
  // the receiver drops the frame at the fault: what it kept is the request
  while (t.data.size() > 8 * nd) void'(t.data.pop_back());
  t.bad_fcs = 0;
end else begin
  int n = t.data.size() - 8 * nfull;
  pl = '0;
  pl[7:0] = usx_term(n);
  for (int i = 0; i < n; i++) pl[8 + 8*i +: 8] = t.data[8*nfull + i];
  send_blk(2'b10, pl, R);
end
// close a cut frame's remainder with idles; inter-frame gap
repeat (1 + t.gap) send_blk(2'b10, 64'h1E, R);
vif.drv_cb.blk_valid <= 1'b0;
""",
    mon_desc="blocks descrambled by the monitor's own descrambler, one copy per replication group, decoded into frames and faults; completed by the DUT's report",
    mon_members="usxgmii_transaction done_q[$], rep_q[$];",
    mon_run="""
bit [57:0] st = '0;
bit [65:0] ref_b;
int cnt = 0, R = 1;
bit in_f = 0;
usxgmii_transaction cur;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rep_valid) begin
    usxgmii_transaction r = usxgmii_transaction::type_id::create("r");
    r.rlen = vif.mon_cb.rep_len; r.rcrc = vif.mon_cb.rep_crc; r.fcs_ok = vif.mon_cb.rep_fcs_ok; r.err = vif.mon_cb.rep_err;
    rep_q.push_back(r);
  end
  if (vif.mon_cb.blk_valid) begin
    bit [63:0] d;
    bit [65:0] b;
    for (int i = 0; i < 64; i++) begin
      d[i] = vif.mon_cb.blk[2 + i] ^ st[38] ^ st[57];
      st = {st[56:0], vif.mon_cb.blk[2 + i]};
    end
    b = {d, vif.mon_cb.blk[1:0]};
    if (cnt == 0) begin
      R = usx_reps(vif.mon_cb.rate);
      ref_b = b;
      cnt = (R == 1) ? 0 : 1;
      if (b[1:0] == 2'b01) begin
        if (in_f) for (int i = 0; i < 8; i++) cur.data.push_back(d[8*i +: 8]);
      end else if (b[1:0] == 2'b10) begin
        int n = usx_term_n(d[7:0]);
        if (d[7:0] == 8'h78) begin
          if (in_f) `uvm_error("MON", "USXGMII: start inside a frame")
          cur = usxgmii_transaction::type_id::create("t");
          cur.speed = vif.mon_cb.rate;
          if (d[63:8] != {8'hD5, {6{8'h55}}}) cur.fault = 4;
          in_f = 1;
        end else if (in_f && n >= 0) begin
          for (int i = 0; i < n; i++) cur.data.push_back(d[8 + 8*i +: 8]);
          cur.bad_fcs = !fcs_good(cur.data);
          done_q.push_back(cur); in_f = 0;
        end else if (in_f) begin
          cur.fault = 3; cur.fpos = cur.data.size() / 8;
          done_q.push_back(cur); in_f = 0;
        end
      end else if (in_f) begin
        cur.fault = 1; cur.fpos = cur.data.size() / 8;
        done_q.push_back(cur); in_f = 0;
      end
    end else begin
      if (b != ref_b && in_f) begin
        cur.fault = 2; cur.fpos = cur.data.size() / 8 - 1;
        done_q.push_back(cur); in_f = 0;
      end
      cnt = (cnt + 1 == R) ? 0 : cnt + 1;
    end
  end
  while (done_q.size() != 0 && rep_q.size() != 0) begin
    usxgmii_transaction t = done_q.pop_front(), r = rep_q.pop_front();
    t.rlen = r.rlen; t.rcrc = r.rcrc; t.fcs_ok = r.fcs_ok; t.err = r.err;
    publish(t);
  end
end
""",
    mon_tasks="""
function bit fcs_good(bit [7:0] q[$]);
  bit [31:0] c = 32'hFFFF_FFFF;
  foreach (q[i]) c = usx_crc32(c, q[i]);
  return c == 32'hDEBB_20E3;
endfunction
""",
    predict="""
bit [31:0] c = 32'hFFFF_FFFF;
foreach (t.data[i]) c = usx_crc32(c, t.data[i]);
t.rlen = t.data.size();
t.rcrc = ~c;
t.fcs_ok = (c == 32'hDEBB_20E3);
case (t.fault)
  1: t.err = 1;
  2: t.err = 2;
  3: t.err = 4;
  4: t.err = 8;
  default: t.err = 0;
endcase
""",
    checks="""
if (t.fault == 0 && !t.bad_fcs && !t.fcs_ok) fail(t, "good frame reported with a bad FCS");
if (t.fault inside {1, 2, 3} && t.data.size() % 8 != 0) fail(t, "a cut frame not on a block boundary");
""",
    coverage="""
cp_speed : coverpoint tr.speed { bins g10 = {0}; bins g5 = {1}; bins g2_5 = {2}; bins g1 = {3}; }
cp_fault : coverpoint tr.fault { bins none = {0}; bins header = {1}; bins replica = {2}; bins error_blk = {3}; bins sfd = {4}; }
cp_term  : coverpoint (tr.data.size() % 8) iff (tr.fault == 0) { bins t[] = {[0:7]}; }
cp_fcs   : coverpoint tr.bad_fcs iff (tr.fault == 0);
x_speed_fault : cross cp_speed, cp_fault { ignore_bins rep10 = binsof(cp_speed.g10) && binsof(cp_fault.replica); }
""",
    directed="""
// every terminate lane at 10G, every rate, then each planted fault
for (int n = 0; n < 8; n++) begin
  t = item(); t.speed = 0; t.nbytes = 16 + n; t.seed = n + 1; t.post_randomize(); send(t);
end
for (int s = 0; s < 4; s++) begin
  t = item(); t.speed = s; t.nbytes = 60; t.seed = 77 + s; t.post_randomize(); send(t);
end
t = item(); t.speed = 1; t.nbytes = 20; t.seed = 5; t.bad_fcs = 1; t.post_randomize(); send(t);
for (int s = 0; s < 4; s++) begin
  t = item(); t.speed = s; t.nbytes = 40; t.seed = 9 + s; t.fault = 1; t.post_randomize(); t.fpos = 2; send(t);
  t = item(); t.speed = s; t.nbytes = 40; t.seed = 19 + s; t.fault = 3; t.post_randomize(); t.fpos = 0; send(t);
  t = item(); t.speed = s; t.nbytes = 40; t.seed = 29 + s; t.fault = 4; t.post_randomize(); send(t);
  if (s != 0) begin
    t = item(); t.speed = s; t.nbytes = 40; t.seed = 39 + s; t.fault = 2; t.post_randomize(); t.fpos = 3; send(t);
  end
end
""",
    drain_ns=2000,
    model="""
module usxgmii_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        blk_valid,
  input  logic [65:0] blk,
  input  logic [1:0]  rate,
  output logic        rep_valid,
  output logic [7:0]  rep_len,
  output logic [31:0] rep_crc,
  output logic        rep_fcs_ok,
  output logic [3:0]  rep_err
);
  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    logic [31:0] x;
    x = c ^ {24'h0, b};
    for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
    crc32_byte = x;
  endfunction

  logic [57:0] st;            // descrambler: the last 58 received bits
  logic [65:0] ref_b;         // first copy of the current replication group
  logic [3:0]  cnt, reps;
  logic        in_f, pre_bad;
  logic [7:0]  len;
  logic [31:0] crc;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= '0; ref_b <= '0; cnt <= '0; reps <= 4'd1; in_f <= 1'b0; pre_bad <= 1'b0; len <= '0; crc <= '1;
      rep_valid <= 1'b0; rep_len <= '0; rep_crc <= '0; rep_fcs_ok <= 1'b0; rep_err <= '0;
    end else begin
      rep_valid <= 1'b0;
      if (blk_valid) begin : one_block
        logic [57:0] s;
        logic [63:0] d;
        logic [65:0] b;
        logic [31:0] c;
        logic [3:0]  r;
        logic [7:0]  l;
        integer      n;
        s = st;
        for (int i = 0; i < 64; i++) begin
          d[i] = blk[2 + i] ^ s[38] ^ s[57];
          s = {s[56:0], blk[2 + i]};
        end
        st <= s;
        b = {d, blk[1:0]};
        c = crc; l = len;
        if (cnt == 4'd0) begin
          case (rate)
            2'd0: r = 4'd1;
            2'd1: r = 4'd2;
            2'd2: r = 4'd4;
            default: r = 4'd10;
          endcase
          reps <= r;
          ref_b <= b;
          cnt <= (r == 4'd1) ? 4'd0 : 4'd1;
          if (b[1:0] == 2'b01) begin                      // data
            if (in_f) begin
              for (int i = 0; i < 8; i++) c = crc32_byte(c, d[8*i +: 8]);
              crc <= c; len <= l + 8'd8;
            end
          end else if (b[1:0] == 2'b10) begin             // control
            case (d[7:0])
              8'h87: n = 0;  8'h99: n = 1;  8'hAA: n = 2;  8'hB4: n = 3;
              8'hCC: n = 4;  8'hD2: n = 5;  8'hE1: n = 6;  8'hFF: n = 7;
              default: n = -1;
            endcase
            if (d[7:0] == 8'h78) begin
              if (in_f) begin                             // a start inside a frame
                rep_valid <= 1'b1; rep_len <= l; rep_crc <= ~c; rep_fcs_ok <= (c == 32'hDEBB_20E3); rep_err <= 4'd4;
              end
              in_f <= 1'b1; len <= '0; crc <= '1;
              pre_bad <= (d[63:8] != {8'hD5, {6{8'h55}}});
            end else if (in_f && n >= 0) begin            // terminate
              for (int i = 0; i < 7; i++) if (i < n) c = crc32_byte(c, d[8 + 8*i +: 8]);
              l = l + 8'(n);
              in_f <= 1'b0;
              rep_valid <= 1'b1; rep_len <= l; rep_crc <= ~c; rep_fcs_ok <= (c == 32'hDEBB_20E3);
              rep_err <= pre_bad ? 4'd8 : 4'd0;
            end else if (in_f) begin                      // error / idle / other inside a frame
              in_f <= 1'b0;
              rep_valid <= 1'b1; rep_len <= l; rep_crc <= ~c; rep_fcs_ok <= (c == 32'hDEBB_20E3); rep_err <= 4'd4;
            end
          end else if (in_f) begin                        // invalid sync header
            in_f <= 1'b0;
            rep_valid <= 1'b1; rep_len <= l; rep_crc <= ~c; rep_fcs_ok <= (c == 32'hDEBB_20E3); rep_err <= 4'd1;
          end
        end else begin
          if (b != ref_b && in_f) begin                   // a copy differs from the first
            in_f <= 1'b0;
            rep_valid <= 1'b1; rep_len <= l; rep_crc <= ~c; rep_fcs_ok <= (c == 32'hDEBB_20E3); rep_err <= 4'd2;
          end
          cnt <= (cnt + 4'd1 == reps) ? 4'd0 : cnt + 4'd1;
        end
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({blk_valid, rep_valid}))
  else $error("USXGMII: X on block valid / report");
assert property (@(posedge clk) disable iff (!rst_n) blk_valid |-> !$isunknown(blk))
  else $error("USXGMII: X in a valid block");
// a report follows a valid block
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> $past(blk_valid))
  else $error("USXGMII: report without a block");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 0 && rep_fcs_ok);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 2);
cover property (@(posedge clk) disable iff (!rst_n) blk_valid && rate == 2'd3);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic blk_valid = 0;
logic [65:0] blk = 0;
logic [1:0] rate = 0;
wire rep_valid, rep_fcs_ok;
wire [7:0] rep_len;
wire [31:0] rep_crc;
wire [3:0] rep_err;

always #5 clk = ~clk;

usxgmii_model u_dut (.clk(clk), .rst_n(rst_n), .blk_valid(blk_valid), .blk(blk), .rate(rate),
                     .rep_valid(rep_valid), .rep_len(rep_len), .rep_crc(rep_crc), .rep_fcs_ok(rep_fcs_ok),
                     .rep_err(rep_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

function automatic bit [31:0] crc32(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction

int nrep = 0;
logic [7:0] r_len;
logic [31:0] r_crc;
logic r_ok;
logic [3:0] r_err;
always @(posedge clk) if (rep_valid) begin nrep++; r_len = rep_len; r_crc = rep_crc; r_ok = rep_fcs_ok; r_err = rep_err; end

// transmitter: scrambler, replication
logic [57:0] scr = 0;
int reps = 1;
task automatic tx(input logic [1:0] sh, input logic [63:0] pl, input int alt_at = -1, input logic [63:0] alt = 0);
  logic [63:0] p, s;
  for (int r = 0; r < reps; r++) begin
    p = (r == alt_at) ? alt : pl;
    for (int i = 0; i < 64; i++) begin
      s[i] = p[i] ^ scr[38] ^ scr[57];
      scr = {scr[56:0], s[i]};
    end
    @(negedge clk); blk_valid = 1; blk = {s, sh};
  end
endtask
task automatic set_rate(input logic [1:0] r);
  rate = r;
  reps = (r == 0) ? 1 : (r == 1) ? 2 : (r == 2) ? 4 : 10;
endtask
task automatic idle(input int n); for (int i = 0; i < n; i++) tx(2'b10, 64'h1E); endtask
task automatic pause(input int n); @(negedge clk); blk_valid = 0; repeat (n) @(negedge clk); endtask

// a frame of n payload bytes v0, v0+1, ... with its FCS; sfd, bad_fcs
logic [7:0] fr [0:127];
int flen;
logic [31:0] fcrc;
task automatic build(input int n, input logic [7:0] v0, input bit bad_fcs = 0);
  logic [31:0] c;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < n; i++) begin fr[i] = v0 + i; c = crc32(c, fr[i]); end
  c = ~c ^ {31'h0, bad_fcs};
  for (int i = 0; i < 4; i++) fr[n + i] = c[8*i +: 8];
  flen = n + 4;
  fcrc = 32'hFFFF_FFFF;
  for (int i = 0; i < flen; i++) fcrc = crc32(fcrc, fr[i]);
endtask
task automatic start(input logic [7:0] sfd = 8'hD5);
  tx(2'b10, {sfd, {6{8'h55}}, 8'h78});
endtask
task automatic data_blk(input int b, input int alt_at = -1);
  logic [63:0] pl;
  for (int i = 0; i < 8; i++) pl[8*i +: 8] = fr[8*b + i];
  tx(2'b01, pl, alt_at, pl ^ 64'h0000_0000_0001_0000);
endtask
task automatic term_blk(input int from);
  logic [63:0] pl;
  int n;
  n = flen - from;
  pl = 0;
  case (n) 0: pl[7:0] = 8'h87; 1: pl[7:0] = 8'h99; 2: pl[7:0] = 8'hAA; 3: pl[7:0] = 8'hB4;
           4: pl[7:0] = 8'hCC; 5: pl[7:0] = 8'hD2; 6: pl[7:0] = 8'hE1; default: pl[7:0] = 8'hFF; endcase
  for (int i = 0; i < 7; i++) if (i < n) pl[8 + 8*i +: 8] = fr[from + i];
  tx(2'b10, pl);
endtask
task automatic frame(input logic [7:0] sfd = 8'hD5);
  start(sfd);
  for (int b = 0; b < flen / 8; b++) data_blk(b);
  term_blk(8 * (flen / 8));
  idle(1);
endtask
// expected CRC of the first k bytes
function automatic logic [31:0] part(input int k);
  logic [31:0] c;
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < k; i++) c = crc32(c, fr[i]);
  return c;
endfunction

initial begin
  int b;
  logic [31:0] c;
  logic [63:0] z, s;
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0, "no report in reset");
  rst_n = 1;
  repeat (2) @(posedge clk);
  // scrambler reference: from the all-zero state, payload bit 0 = 1 then
  // zeros gives 1 at bits 0, 39, 58 (x^58 + x^39 + 1 taps)
  begin
    logic [57:0] t;
    t = 0; z = 64'h1;
    for (int i = 0; i < 64; i++) begin s[i] = z[i] ^ t[38] ^ t[57]; t = {t[56:0], s[i]}; end
    chk(s[0] && s[39] && s[58] && $countones(s) == 3, $sformatf("scrambler taps (%h)", s));
  end

  set_rate(0); idle(3);
  chk(nrep == 0, "idles: no report");
  // every terminate lane at 10G
  for (int n = 0; n < 8; n++) begin
    b = nrep;
    build(20 + n, 8'h10 * n);
    frame();
    pause(0);
    chk(nrep == b + 1 && r_err == 0 && r_ok === 1'b1 && r_len == flen && r_crc == ~fcrc,
        $sformatf("10G frame of %0d bytes (terminate with %0d)", flen, flen % 8));
  end
  // every rate
  for (int r = 1; r < 4; r++) begin
    set_rate(r);
    b = nrep; build(45, 8'hA0 + r); frame(); pause(0);
    chk(nrep == b + 1 && r_err == 0 && r_ok === 1'b1 && r_len == 49, $sformatf("frame at rate %0d (%0d copies)", r, reps));
  end
  // bad FCS
  set_rate(1);
  b = nrep; build(30, 8'h33, 1); frame(); pause(0);
  chk(nrep == b + 1 && r_err == 0 && r_ok === 1'b0 && r_len == 34, "bad FCS reported");
  // a pause in the block stream (valid low) keeps scrambler and replication in step
  b = nrep; build(26, 8'h44); start(); data_blk(0); pause(5); data_blk(1); data_blk(2); term_blk(24); idle(1); pause(0);
  chk(nrep == b + 1 && r_err == 0 && r_ok === 1'b1, "frame across a pause in valid");

  // planted faults
  set_rate(0);
  b = nrep; build(40, 8'h01); start(); data_blk(0); data_blk(1);
  tx(2'b00, 64'h0); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd1 && r_len == 16 && r_crc == ~part(16), "invalid sync header 00: code 1, 16 bytes kept");
  b = nrep; build(40, 8'h02); start(); data_blk(0); tx(2'b11, 64'h0); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd1 && r_len == 8, "invalid sync header 11: code 1");
  b = nrep; build(40, 8'h03); start(); data_blk(0); tx(2'b10, {{8{7'h1E}}, 8'h1E}); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd4 && r_len == 8, "error block in a frame: code 4");
  b = nrep; build(40, 8'h04); start(); data_blk(0); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd4 && r_len == 8, "idle block in a frame: code 4");
  b = nrep; build(40, 8'h05); start(); data_blk(0); data_blk(1); data_blk(2); start(); pause(1);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd4 && r_len == 24, "second start: the open frame ends with code 4");
  for (int k = 3; k < 5; k++) data_blk(k);
  term_blk(40); idle(1); pause(0);
  chk(nrep == b + 2 && r_err == 0 && r_len == 20 && r_ok === 1'b0, "the new frame runs on (its own bytes)");
  b = nrep; build(24, 8'h06); frame(8'hD4); pause(0);
  chk(nrep == b + 1 && r_err == 4'd8 && r_ok === 1'b1 && r_len == 28, "SFD D4: code 8, frame still received");
  b = nrep; build(24, 8'h07); tx(2'b10, {8'hD5, {5{8'h55}}, 8'h54, 8'h78});
  for (int k = 0; k < 3; k++) data_blk(k); term_blk(24); idle(1); pause(0);
  chk(nrep == b + 1 && r_err == 4'd8, "preamble byte 54: code 8");
  // replica faults
  set_rate(2);
  b = nrep; build(40, 8'h08); start(); data_blk(0); data_blk(1, 2); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd2 && r_len == 16 && r_crc == ~part(16), "third copy differs: code 2 after the block");
  b = nrep; build(40, 8'h09); start(); data_blk(0, 3); idle(2); pause(0);
  chk(nrep == b + 1 && r_ok === 1'b0 && r_err == 4'd2 && r_len == 8, "last copy differs: code 2");
  // outside a frame: stray data, bad headers and differing copies are ignored
  b = nrep;
  tx(2'b01, 64'h1234); tx(2'b00, 64'h0); tx(2'b10, 64'h1E, 1, 64'h11E); tx(2'b10, 64'hFF);
  idle(2); pause(0);
  chk(nrep == b, "outside a frame: data, bad header, differing copy, terminate ignored");
  build(30, 8'h0A); b = nrep; frame(); pause(0);
  chk(nrep == b + 1 && r_err == 0 && r_ok === 1'b1, "clean frame after the faults");
  // rate change between frames
  set_rate(3); build(18, 8'h0B); b = nrep; frame(); pause(0);
  set_rate(0); build(18, 8'h0C); frame(); pause(0);
  chk(nrep == b + 2 && r_err == 0 && r_ok === 1'b1, "1G frame, then 10G frame");

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
