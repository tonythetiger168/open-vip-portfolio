# AMBA AXI4-Stream transmitter agent (ARM IHI 0051).
# tb/top_tb.sv axi_stream_model: 32-bit receiver (four byte lanes) with TREADY
# from an LFSR. Per packet (TLAST) it reports, one clock after the last
# transfer, the number of data bytes (TKEEP and TSTRB high), the number of
# position bytes (TKEEP high, TSTRB low), the CRC-32 (IEEE 802.3, reflected,
# init and xorout 0xFFFFFFFF) of the data bytes in stream order, the packet's
# TID / TDEST, and an error flag for the reserved TKEEP low / TSTRB high
# combination or a TID / TDEST change inside a packet. Null bytes (TKEEP low)
# are dropped.
# The driver places the packet's bytes on the lanes with random null bytes
# and random TVALID gaps; packets follow each other with no idle clock.
from _lib import wait_cb

SPEC = dict(
    vip="AXI_Stream-UVM-VIP", p="axi_stream", P="AXI4-Stream", dir="axi_stream", family="AMBA",
    desc="AMBA AXI4-Stream transmitter VIP: TVALID / TREADY back-pressure, TKEEP null bytes, "
         "TSTRB position bytes, TLAST packets, TID / TDEST routing fields, back-to-back packets.",
    about="""
AXI4-Stream carries unaddressed data (video lines, network packets, DSP
samples) between IP blocks. The DUT model is a packet receiver that reports a
byte count, a position-byte count and the CRC-32 of each packet's data bytes;
the scoreboard computes the same from the bytes the agent sent, so a dropped,
duplicated, reordered or mis-classified byte shows up as a mismatch. The SVA
checker holds the AXI4-Stream rules: payload stable while TVALID waits for
TREADY, no reserved TKEEP / TSTRB combination, TID / TDEST constant within a
packet.""",
    timeout=200,
    ports=[
        ("in", "logic", "tvalid"), ("out", "logic", "tready"),
        ("in", "logic [31:0]", "tdata"), ("in", "logic [3:0]", "tkeep"), ("in", "logic [3:0]", "tstrb"),
        ("in", "logic", "tlast"), ("in", "logic [3:0]", "tid"), ("in", "logic [3:0]", "tdest"),
        ("out", "logic", "pkt_done"), ("out", "logic [7:0]", "pkt_ndata"), ("out", "logic [7:0]", "pkt_npos"),
        ("out", "logic [31:0]", "pkt_crc"), ("out", "logic [3:0]", "pkt_id"), ("out", "logic [3:0]", "pkt_dest"),
        ("out", "logic", "pkt_err"),
    ],
    cfg="int unsigned null_pct = 15;   // percent of lanes left null inside a packet\n"
        "int unsigned pos_pct  = 10;   // percent of bytes sent as position bytes",
    fields=[
        ("bit [8:0]", "bytes", "req", "q"),        # {position, value}; position bytes carry 0
        ("bit [3:0]", "id", "req"),
        ("bit [3:0]", "dest", "req"),
        ("bit [7:0]", "ndata", "rsp"),
        ("bit [7:0]", "npos", "rsp"),
        ("bit [31:0]", "crc", "rsp"),
        ("bit", "err", "rsp"),
        ("bit [6:0]", "nbytes", "info", "rand"),
        ("bit [1:0]", "gap", "info", "rand"),      # TVALID low clocks between transfers
        ("bit", "sparse", "info", "rand"),         # null lanes inside the packet
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nbytes inside {[1:64]}; gap dist { 0 := 4, [1:3] :/ 1 }; }
""",
    tr_functions="""
// cfg-free fill: about one byte in ten is a position byte
function void fill_bytes(int unsigned n, int unsigned pos_pct = 10);
  bit [31:0] x = seed | 32'h1;
  bytes.delete();
  for (int unsigned i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    if (x[31:24] % 100 < pos_pct) bytes.push_back(9'h100);
    else bytes.push_back({1'b0, x[7:0]});
  end
endfunction

function void post_randomize();
  fill_bytes(nbytes);
endfunction
""",
    drv_rsp=False,
    drv_desc="one packet per item, bytes placed on the four lanes with random null bytes and TVALID gaps",
    drv_idle="""
vif.drv_cb.tvalid <= 1'b0; vif.drv_cb.tdata <= '0; vif.drv_cb.tkeep <= '0; vif.drv_cb.tstrb <= '0;
vif.drv_cb.tlast  <= 1'b0; vif.drv_cb.tid   <= '0; vif.drv_cb.tdest <= '0;
""",
    drv_item="""
int unsigned idx = 0;
while (idx < t.bytes.size()) begin
  bit [31:0] d = 0; bit [3:0] k = 0, s = 0;
  for (int l = 0; l < 4; l++) begin
    if (idx < t.bytes.size() && !(t.sparse && $urandom_range(99) < cfg.null_pct)) begin
      k[l] = 1'b1;
      s[l] = !t.bytes[idx][8];
      d[l*8 +: 8] = t.bytes[idx][7:0];
      idx++;
    end
  end
  vif.drv_cb.tvalid <= 1'b1; vif.drv_cb.tdata <= d; vif.drv_cb.tkeep <= k; vif.drv_cb.tstrb <= s;
  vif.drv_cb.tlast  <= (idx == t.bytes.size()); vif.drv_cb.tid <= t.id; vif.drv_cb.tdest <= t.dest;
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.tready === 1'b1", "AXI4-Stream TREADY").splitlines()) + """
  if (t.gap != 0 && idx < t.bytes.size()) begin
    vif.drv_cb.tvalid <= 1'b0;
    repeat (t.gap) @(vif.drv_cb);
  end
end
vif.drv_cb.tvalid <= 1'b0;
vif.drv_cb.tlast  <= 1'b0;
""",
    mon_desc="transfers (TVALID & TREADY) collected into packets at TLAST, completed by the receiver's packet report",
    mon_members="axi_stream_transaction cur, done_q[$];",
    mon_run="""
forever begin
  @(vif.mon_cb);
  // the report of a packet comes one clock after its TLAST transfer
  if (vif.mon_cb.pkt_done) begin
    if (done_q.size() == 0)
      `uvm_error("MON", "AXI4-Stream: packet report without a TLAST transfer")
    else begin
      axi_stream_transaction t = done_q.pop_front();
      t.ndata = vif.mon_cb.pkt_ndata; t.npos = vif.mon_cb.pkt_npos; t.crc = vif.mon_cb.pkt_crc;
      t.err = vif.mon_cb.pkt_err;
      if (vif.mon_cb.pkt_id != t.id || vif.mon_cb.pkt_dest != t.dest) t.err = 1'b1;
      publish(t);
    end
  end
  if (vif.mon_cb.tvalid && vif.mon_cb.tready) begin
    if (cur == null) begin
      cur = axi_stream_transaction::type_id::create("t");
      cur.id = vif.mon_cb.tid; cur.dest = vif.mon_cb.tdest;
    end
    for (int l = 0; l < 4; l++)
      if (vif.mon_cb.tkeep[l])
        cur.bytes.push_back(vif.mon_cb.tstrb[l] ? {1'b0, vif.mon_cb.tdata[l*8 +: 8]} : 9'h100);
    if (vif.mon_cb.tlast) begin
      done_q.push_back(cur);
      cur = null;
    end
  end
end
""",
    sb_members="""
// CRC-32 (IEEE 802.3), one byte at a time, reflected
function bit [31:0] crc32_byte(bit [31:0] c, bit [7:0] b);
  c ^= b;
  for (int i = 0; i < 8; i++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : c >> 1;
  return c;
endfunction""",
    predict="""
bit [31:0] c = 32'hFFFF_FFFF;
t.ndata = 0; t.npos = 0; t.err = 0;
foreach (t.bytes[i])
  if (t.bytes[i][8]) t.npos++;
  else begin t.ndata++; c = crc32_byte(c, t.bytes[i][7:0]); end
t.crc = ~c;
""",
    checks="""
if (t.bytes.size() == 0) fail(t, "packet with no data or position byte");
if (t.err) fail(t, "receiver flagged a reserved TKEEP / TSTRB combination or a TID / TDEST change");
""",
    coverage="""
cp_len  : coverpoint tr.bytes.size() { bins one = {1}; bins word = {[2:4]}; bins short_ = {[5:16]}; bins long_ = {[17:64]}; }
cp_pos  : coverpoint tr.npos { bins none = {0}; bins some = {[1:$]}; }
cp_tail : coverpoint tr.bytes.size() % 4;
cp_id   : coverpoint tr.id;
cp_dest : coverpoint tr.dest { bins lo = {[0:7]}; bins hi = {[8:15]}; }
x_len_tail : cross cp_len, cp_tail;
""",
    directed="""
// the CRC-32 check string, then every tail length, null-heavy packets,
// position bytes, every TID and back-to-back single-transfer packets
begin
  string cv = "123456789";
  t = item();
  foreach (cv[i]) t.bytes.push_back({1'b0, cv[i]});
  t.id = 4'h1; t.dest = 4'h2; send(t);
end
for (int n = 1; n <= 8; n++) begin t = item(); t.seed = n; t.fill_bytes(n, 0); t.id = n; send(t); end
t = item(); t.seed = 32'h77; t.sparse = 1; t.gap = 2; t.fill_bytes(40); send(t);
t = item(); t.bytes = '{9'h100, 9'h0AA, 9'h100, 9'h100, 9'h055}; t.dest = 4'hF; send(t);
t = item(); t.bytes = '{9'h100}; send(t);                 // position byte only
for (int i = 0; i < 16; i++) begin t = item(); t.seed = 200 + i; t.fill_bytes(1 + i % 4, 0); t.id = i; t.dest = 15 - i; send(t); end
t = item(); t.seed = 32'h99; t.fill_bytes(64); send(t);
""",
    drain_ns=3000,
    model="""
module axi_stream_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        tvalid,
  output logic        tready,
  input  logic [31:0] tdata,
  input  logic [3:0]  tkeep,
  input  logic [3:0]  tstrb,
  input  logic        tlast,
  input  logic [3:0]  tid,
  input  logic [3:0]  tdest,
  output logic        pkt_done,
  output logic [7:0]  pkt_ndata,
  output logic [7:0]  pkt_npos,
  output logic [31:0] pkt_crc,
  output logic [3:0]  pkt_id,
  output logic [3:0]  pkt_dest,
  output logic        pkt_err
);
  logic [7:0]  lfsr;
  logic        in_pkt, err;
  logic [7:0]  nd, np;
  logic [31:0] crc;
  logic [3:0]  cur_id, cur_dest;
  // this transfer folded into the packet state
  logic [7:0]  nd_n, np_n;
  logic [31:0] crc_n;
  logic        err_n;

  assign tready = lfsr[1] | lfsr[3];

  always_comb begin
    nd_n = in_pkt ? nd : 8'd0;
    np_n = in_pkt ? np : 8'd0;
    crc_n = in_pkt ? crc : 32'hFFFF_FFFF;
    err_n = in_pkt ? err : 1'b0;
    if (in_pkt && (tid != cur_id || tdest != cur_dest)) err_n = 1'b1;
    for (int l = 0; l < 4; l++) begin
      if (tkeep[l] && tstrb[l]) begin
        nd_n = nd_n + 8'd1;
        crc_n = crc_n ^ {24'h0, tdata[l*8 +: 8]};
        for (int i = 0; i < 8; i++) crc_n = crc_n[0] ? (crc_n >> 1) ^ 32'hEDB8_8320 : crc_n >> 1;
      end else if (tkeep[l]) np_n = np_n + 8'd1;
      else if (tstrb[l]) err_n = 1'b1;           // reserved: TKEEP low, TSTRB high
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      lfsr <= 8'hC3; in_pkt <= 1'b0; err <= 1'b0; nd <= '0; np <= '0; crc <= '1;
      cur_id <= '0; cur_dest <= '0;
      pkt_done <= 1'b0; pkt_ndata <= '0; pkt_npos <= '0; pkt_crc <= '0; pkt_id <= '0;
      pkt_dest <= '0; pkt_err <= 1'b0;
    end else begin
      lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
      pkt_done <= 1'b0;
      if (tvalid && tready) begin
        if (!in_pkt) begin cur_id <= tid; cur_dest <= tdest; end
        if (tlast) begin
          in_pkt <= 1'b0;
          pkt_done <= 1'b1; pkt_ndata <= nd_n; pkt_npos <= np_n; pkt_crc <= ~crc_n;
          pkt_id <= in_pkt ? cur_id : tid; pkt_dest <= in_pkt ? cur_dest : tdest; pkt_err <= err_n;
        end else begin
          in_pkt <= 1'b1; nd <= nd_n; np <= np_n; crc <= crc_n; err <= err_n;
        end
      end
    end
  end
endmodule
""",
    sva="""
logic in_pkt;
logic [3:0] p_id, p_dest;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin in_pkt <= 1'b0; p_id <= '0; p_dest <= '0; end
  else if (tvalid && tready) begin
    in_pkt <= !tlast;
    if (!in_pkt) begin p_id <= tid; p_dest <= tdest; end
  end
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({tready, pkt_done}))
  else $error("AXI4-Stream: X on TREADY / report");
assert property (@(posedge clk) disable iff (!rst_n) tvalid |-> !$isunknown({tdata & {{8{tkeep[3]}}, {8{tkeep[2]}}, {8{tkeep[1]}}, {8{tkeep[0]}}}, tkeep, tstrb, tlast, tid, tdest}))
  else $error("AXI4-Stream: X on the payload while TVALID");
// once TVALID is high it stays high, payload stable, until TREADY
assert property (@(posedge clk) disable iff (!rst_n) tvalid && !tready |=> tvalid && $stable({tdata, tkeep, tstrb, tlast, tid, tdest}))
  else $error("AXI4-Stream: transfer changed or withdrawn before TREADY");
// TKEEP low with TSTRB high is reserved
assert property (@(posedge clk) disable iff (!rst_n) tvalid |-> (tstrb & ~tkeep) == 4'h0)
  else $error("AXI4-Stream: reserved TKEEP = 0 / TSTRB = 1 combination");
// TID and TDEST do not change inside a packet
assert property (@(posedge clk) disable iff (!rst_n) tvalid && in_pkt |-> tid == p_id && tdest == p_dest)
  else $error("AXI4-Stream: TID / TDEST changed inside a packet");
// a report only follows a TLAST transfer
assert property (@(posedge clk) disable iff (!rst_n) pkt_done |-> $past(tvalid && tready && tlast))
  else $error("AXI4-Stream: packet report without TLAST");
cover property (@(posedge clk) disable iff (!rst_n) tvalid && !tready ##1 tvalid && tready);
cover property (@(posedge clk) disable iff (!rst_n) tvalid && tready && tkeep != 4'hF && !tlast);
cover property (@(posedge clk) disable iff (!rst_n) tvalid && tready && (tkeep & ~tstrb) != 0);
cover property (@(posedge clk) disable iff (!rst_n) tvalid && tready && tlast ##1 tvalid && tready && tlast);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic tvalid = 0, tlast = 0;
logic [31:0] tdata = 0;
logic [3:0] tkeep = 0, tstrb = 0, tid = 0, tdest = 0;
wire tready, pkt_done, pkt_err;
wire [7:0] pkt_ndata, pkt_npos;
wire [31:0] pkt_crc;
wire [3:0] pkt_id, pkt_dest;

always #5 clk = ~clk;

axi_stream_model u_dut (.clk(clk), .rst_n(rst_n), .tvalid(tvalid), .tready(tready), .tdata(tdata),
                        .tkeep(tkeep), .tstrb(tstrb), .tlast(tlast), .tid(tid), .tdest(tdest),
                        .pkt_done(pkt_done), .pkt_ndata(pkt_ndata), .pkt_npos(pkt_npos),
                        .pkt_crc(pkt_crc), .pkt_id(pkt_id), .pkt_dest(pkt_dest), .pkt_err(pkt_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// reports seen (one per packet)
int nrep = 0;
logic [7:0] r_nd, r_np; logic [31:0] r_crc; logic [3:0] r_id, r_dest; logic r_err;
always @(posedge clk) if (pkt_done) begin
  nrep++; r_nd = pkt_ndata; r_np = pkt_npos; r_crc = pkt_crc; r_id = pkt_id; r_dest = pkt_dest; r_err = pkt_err;
end

// one transfer, held until TREADY
int stalls = 0;
task automatic xfer(input logic [31:0] d, input logic [3:0] k, input logic [3:0] s, input logic l,
                    input logic [3:0] id, input logic [3:0] dst);
  int n;
  tvalid = 1; tdata = d; tkeep = k; tstrb = s; tlast = l; tid = id; tdest = dst;
  n = 0;
  @(posedge clk);
  while (!tready && n < 50) begin stalls++; @(posedge clk); n++; end
  #1;
  tvalid = 0; tlast = 0;
endtask

task automatic wait_rep(input int prev);
  int n;
  n = 0;
  while (nrep == prev && n < 20) begin @(posedge clk); n++; end
  #1;
endtask

initial begin
  int b;
  repeat (3) @(posedge clk);
  chk(pkt_done === 1'b0, "no report in reset");
  rst_n = 1;
  repeat (2) @(posedge clk); #1;

  // "123456789" on four lanes: CRC-32 check value 0xCBF43926
  b = nrep;
  xfer(32'h3433_3231, 4'hF, 4'hF, 0, 4'h1, 4'h2);
  xfer(32'h3837_3635, 4'hF, 4'hF, 0, 4'h1, 4'h2);
  xfer(32'h0000_0039, 4'h1, 4'h1, 1, 4'h1, 4'h2);
  wait_rep(b);
  chk(nrep == b + 1, "one report per packet");
  chk(r_crc === 32'hCBF4_3926 && r_nd == 9 && r_np == 0, "CRC-32 of 123456789 = 0xCBF43926, 9 bytes");
  chk(r_id == 4'h1 && r_dest == 4'h2 && r_err === 1'b0, "TID / TDEST reported, no error");

  // the same bytes with null lanes in between and a null transfer
  b = nrep;
  xfer(32'h0032_0031, 4'h5, 4'h5, 0, 4'h3, 4'h4);
  xfer(32'h3300_0000, 4'h8, 4'h8, 0, 4'h3, 4'h4);
  xfer(32'hFFFF_FFFF, 4'h0, 4'h0, 0, 4'h3, 4'h4);
  xfer(32'h3736_3534, 4'hF, 4'hF, 0, 4'h3, 4'h4);
  xfer(32'h0039_3800, 4'h6, 4'h6, 1, 4'h3, 4'h4);
  wait_rep(b);
  chk(r_crc === 32'hCBF4_3926 && r_nd == 9, "null bytes are dropped (same CRC, same count)");
  chk(r_id == 4'h3 && r_dest == 4'h4, "TID / TDEST of the second packet");

  // position bytes: counted, not in the CRC, their data ignored
  b = nrep;
  xfer(32'h33FF_3231, 4'hF, 4'hB, 0, 4'h5, 4'h6);
  xfer(32'h3736_3534, 4'hF, 4'hF, 0, 4'h5, 4'h6);
  xfer(32'hAA39_3800, 4'hF, 4'h6, 1, 4'h5, 4'h6);
  wait_rep(b);
  chk(r_crc === 32'hCBF4_3926 && r_nd == 9 && r_np == 3 && r_err === 1'b0, "three position bytes counted, CRC unchanged");

  // a single-byte packet and a position-only packet
  b = nrep;
  xfer(32'h0000_0061, 4'h1, 4'h1, 1, 4'h7, 4'h8);
  wait_rep(b);
  chk(r_nd == 1 && r_crc === 32'hE8B7_BE43 && r_id == 4'h7 && r_dest == 4'h8, "single byte 'a': CRC 0xE8B7BE43");
  b = nrep;
  xfer(32'h0000_0000, 4'h2, 4'h0, 1, 4'h9, 4'hA);
  wait_rep(b);
  chk(r_nd == 0 && r_np == 1 && r_crc === 32'h0 && r_err === 1'b0, "position byte only: no data, CRC of nothing is 0");

  // reserved TKEEP low / TSTRB high
  b = nrep;
  xfer(32'h0000_3231, 4'h3, 4'h7, 1, 4'h0, 4'h0);
  wait_rep(b);
  chk(r_err === 1'b1 && r_nd == 2, "TKEEP 0 / TSTRB 1 flagged, data bytes still counted");
  // TID change inside a packet, TDEST change inside a packet
  b = nrep;
  xfer(32'h3433_3231, 4'hF, 4'hF, 0, 4'h1, 4'h1);
  xfer(32'h3837_3635, 4'hF, 4'hF, 1, 4'h2, 4'h1);
  wait_rep(b);
  chk(r_err === 1'b1 && r_id == 4'h1, "TID change inside a packet flagged; the first TID reported");
  b = nrep;
  xfer(32'h3433_3231, 4'hF, 4'hF, 0, 4'h1, 4'h1);
  xfer(32'h3837_3635, 4'hF, 4'hF, 1, 4'h1, 4'h3);
  wait_rep(b);
  chk(r_err === 1'b1 && r_dest == 4'h1, "TDEST change inside a packet flagged; the first TDEST reported");
  b = nrep;
  xfer(32'h3433_3231, 4'hF, 4'hF, 1, 4'h2, 4'h3);
  wait_rep(b);
  chk(r_err === 1'b0 && r_nd == 4 && r_crc === 32'h9BE3_E0A3, "error state cleared for the next packet; CRC of 1234");

  // back to back: each single-transfer packet reported on its own
  b = nrep;
  for (int i = 0; i < 8; i++) xfer(32'h0000_0061, 4'h1, 4'h1, 1, i, i);
  repeat (3) @(posedge clk); #1;
  chk(nrep == b + 8, "eight back-to-back packets, eight reports");
  chk(r_crc === 32'hE8B7_BE43 && r_id == 4'h7 && r_nd == 1, "last of them reported correctly");

  // a long packet: 255 bytes (count width), no tail
  b = nrep;
  for (int i = 0; i < 63; i++) xfer(32'h6161_6161, 4'hF, 4'hF, 0, 4'hC, 4'hD);
  xfer(32'h0061_6161, 4'h7, 4'h7, 1, 4'hC, 4'hD);
  wait_rep(b);
  chk(r_nd == 255 && r_err === 1'b0, "255 data bytes counted");

  // TREADY is not always high: the receiver back-pressures
  chk(stalls > 0, $sformatf("TREADY low for %0d clocks of a held transfer", stalls));

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #400000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
