# 10BASE-T1S PLCA node agent (IEEE 802.3cg, clause 148 Physical Layer
# Collision Avoidance), at the MII side of the PLCA reconciliation sublayer.
# tb/top_tb.sv t1s_plca_model: the multidrop segment with the coordinator
# (node 0, sends the BEACON) and the other nodes 0..7 except the agent's
# LOCAL_ID 3, which transmit at random in their own transmit opportunities.
# Every node counts transmit opportunities (TO) the same way: after the
# BEACON the current ID is 0; a TO ends one clock after the carrier of the
# frame sent in it falls, or after TO_TIMER clocks without a carrier; after
# the TO of node 7 the coordinator sends the next BEACON.
# The model reports each frame of the agent one clock after TX_EN falls: the
# TO it started in, whether the FCS residue is right, and an error flag for a
# start outside the agent's TO, a second frame in one TO, or a frame over a
# carrier (collision).
from _lib import wait_cb

N_NODES, LOCAL_ID, TO_TIMER, BEACON = 8, 3, 8, 4

PLCA_STEP = """
// one clock of the PLCA transmit-opportunity counter (same rule as the
// segment model): act = a carrier on the segment this clock
if (beacon) begin cur = 0; tmr = 0; busy = 0; synced = 1; end
else if (act) busy = 1;
else if (busy) begin cur++; tmr = 0; busy = 0; end
else if (tmr == {to} - 1) begin cur++; tmr = 0; end
else tmr++;
""".format(to=TO_TIMER)

SPEC = dict(
    vip="T1S_PLCA-UVM-VIP", p="t1s_plca", P="10BASE-T1S PLCA", dir="t1s_plca", family="Automotive",
    desc="IEEE 802.3cg 10BASE-T1S PLCA node VIP: BEACON synchronisation, transmit-opportunity counting, "
         "TO_TIMER yield, one frame per opportunity, FCS, collision-free multidrop access.",
    about="""
10BASE-T1S is the 10 Mb/s single-pair multidrop Ethernet of automotive zone
architectures. PLCA (clause 148) replaces CSMA/CD collisions with a round of
transmit opportunities: the coordinator sends a BEACON, then nodes 0..N-1 get
one opportunity each, in ID order, which they use for a frame or let expire
after TO_TIMER bit times. The agent is node 3: it synchronises on the BEACON,
counts the opportunities the same way every node does, and sends each frame in
its own opportunity only. The DUT model is the rest of the segment (the
coordinator and six nodes sending at random) and checks every frame of the
agent: the opportunity it started in, the FCS, and that it never overlapped
another carrier.""",
    timeout=400,
    ports=[
        ("in", "logic", "tx_en"), ("in", "logic [3:0]", "txd"),
        ("out", "logic", "beacon"), ("out", "logic", "crs"),
        ("out", "logic", "rep_valid"), ("out", "logic [3:0]", "rep_slot"), ("out", "logic", "rep_ok"),
        ("out", "logic", "rep_err"),
    ],
    cfg="int unsigned local_id = {lid};   // PLCA node ID of the agent\n"
        "int unsigned nodes    = {n};     // node count (PLCA nodes)".format(lid=LOCAL_ID, n=N_NODES),
    fields=[
        ("bit [7:0]", "bytes", "req", "q"),        # payload; the driver appends the FCS
        ("bit [3:0]", "slot", "rsp"),
        ("bit", "ok", "rsp"),
        ("bit", "err", "rsp"),
        ("bit [5:0]", "nbytes", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nbytes inside {[1:40]}; }
""",
    tr_functions="""
function void fill_bytes(int unsigned n);
  bit [31:0] x = seed | 32'h1;
  bytes.delete();
  for (int unsigned i = 0; i < n; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    bytes.push_back(x[7:0]);
  end
endfunction

function void post_randomize();
  fill_bytes(nbytes);
endfunction

// IEEE 802.3 CRC-32 of the payload (reflected, init / final xor all ones)
function bit [31:0] fcs();
  bit [31:0] c = 32'hFFFF_FFFF;
  foreach (bytes[i]) begin
    c ^= {24'h0, bytes[i]};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  return ~c;
endfunction
""",
    drv_rsp=False,
    drv_desc="tracks the PLCA transmit opportunities from the BEACON and the carrier, sends one frame "
             "(payload + FCS, low nibble first) in each opportunity of its own node ID",
    drv_members="""
// PLCA state, updated every clock by the background process
int unsigned cur, tmr;
bit busy, synced, my_tx, used;""",
    drv_bg="""
forever begin
  bit beacon, act;
  @(vif.drv_cb);
  beacon = vif.drv_cb.beacon === 1'b1;
  act = vif.drv_cb.crs === 1'b1 || my_tx;
""" + "\n".join("  " + l for l in PLCA_STEP.strip().splitlines()) + """
  if (tmr == 0 && !busy) used = 0;     // a new opportunity
end
""",
    drv_idle="""
vif.drv_cb.tx_en <= 1'b0; vif.drv_cb.txd <= '0;
""",
    drv_item="""
bit [7:0] fr[$];
bit [31:0] f = t.fcs();
fr = t.bytes;
for (int i = 0; i < 4; i++) fr.push_back(f[i*8 +: 8]);
// wait for an unused opportunity of this node with room to start before
// TO_TIMER runs out (the driver's state is updated at the same clock edge)
begin
  int unsigned to = 0;
  do begin @(vif.drv_cb); #0; to++; end
  while (!(synced && cur == cfg.local_id && !busy && !used && tmr <= {to} - 3 && vif.drv_cb.crs !== 1'b1)
         && to < cfg.timeout_cycles * 4);
  if (to >= cfg.timeout_cycles * 4) `uvm_error("TIMEOUT", "PLCA: no transmit opportunity of this node")
end
used = 1;
my_tx = 1;
foreach (fr[i]) begin
  vif.drv_cb.tx_en <= 1'b1; vif.drv_cb.txd <= fr[i][3:0];
  @(vif.drv_cb);
  vif.drv_cb.txd <= fr[i][7:4];
  @(vif.drv_cb);
end
vif.drv_cb.tx_en <= 1'b0; vif.drv_cb.txd <= '0;
@(vif.drv_cb);
my_tx = 0;
""".format(to=TO_TIMER),
    mon_desc="nibbles while TX_EN collected into a frame, completed by the segment's report",
    mon_members="t1s_plca_transaction cur; bit [3:0] nib[$]; bit [7:0] done_q[$][$];",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rep_valid) begin
    t1s_plca_transaction t = t1s_plca_transaction::type_id::create("t");
    if (done_q.size() == 0) `uvm_error("MON", "PLCA: frame report without a frame")
    else begin
      bit [7:0] b[$] = done_q.pop_front();
      // the last four bytes are the FCS
      for (int i = 0; i + 4 < b.size(); i++) t.bytes.push_back(b[i]);
    end
    t.slot = vif.mon_cb.rep_slot; t.ok = vif.mon_cb.rep_ok; t.err = vif.mon_cb.rep_err;
    publish(t);
  end
  if (vif.mon_cb.tx_en === 1'b1) nib.push_back(vif.mon_cb.txd);
  else if (nib.size() != 0) begin
    bit [7:0] b[$];
    for (int i = 0; i + 1 < nib.size(); i += 2) b.push_back({nib[i + 1], nib[i]});
    if (nib.size() % 2) `uvm_error("MON", "PLCA: odd number of nibbles")
    done_q.push_back(b);
    nib.delete();
  end
end
""",
    predict="""
t.slot = {lid}; t.ok = 1; t.err = 0;
""".format(lid=LOCAL_ID),
    checks="""
if (t.err) fail(t, "frame started outside this node's transmit opportunity or over a carrier");
if (!t.ok) fail(t, "segment saw a bad FCS");
""",
    coverage="""
cp_len  : coverpoint tr.bytes.size() { bins one = {1}; bins short_ = {[2:8]}; bins mid = {[9:24]}; bins long_ = {[25:40]}; }
cp_b0   : coverpoint tr.bytes[0] { bins zero = {0}; bins ff = {8'hFF}; bins other = default; }
cp_slot : coverpoint tr.slot { bins mine = {3}; }
""",
    directed="""
// one byte, the CRC check string, all-zero and all-ones payloads, then a run
// of frames that need one PLCA cycle each
t = item(); t.bytes = '{8'h00}; send(t);
begin
  string cv = "123456789";
  t = item();
  foreach (cv[i]) t.bytes.push_back(cv[i]);
  send(t);
end
t = item(); repeat (16) t.bytes.push_back(8'h00); send(t);
t = item(); repeat (16) t.bytes.push_back(8'hFF); send(t);
for (int i = 0; i < 6; i++) begin t = item(); t.seed = 50 + i; t.fill_bytes(1 + 7 * i); send(t); end
""",
    drain_ns=6000,
    model="""
module t1s_plca_model #(
  parameter int N = {n}, LOCAL = {lid}, TO_TIMER = {to}, BEACON = {bc}
)(
  input  logic       clk,
  input  logic       rst_n,
  input  logic       tx_en,
  input  logic [3:0] txd,
  output logic       beacon,
  output logic       crs,
  output logic       rep_valid,
  output logic [3:0] rep_slot,
  output logic       rep_ok,
  output logic       rep_err
);
  logic [3:0]  cur, tmr, bcnt, olen;
  logic        busy, o_tx, tx_d, lo, err;
  logic [7:0]  lfsr, sh;
  logic [3:0]  slot;
  logic [31:0] crc;
  logic        act;

  assign beacon = bcnt != 0;
  assign crs    = beacon || o_tx;
  assign act    = tx_en || o_tx;

  function automatic logic [31:0] crc_nib(input logic [31:0] c, input logic [3:0] d);
    c = c ^ {{28'h0, d}};
    for (int i = 0; i < 4; i++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : c >> 1;
    return c;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cur <= '0; tmr <= '0; bcnt <= 4'(BEACON); busy <= 1'b0; o_tx <= 1'b0; olen <= '0;
      lfsr <= 8'h5A; tx_d <= 1'b0; lo <= 1'b0; err <= 1'b0; sh <= '0;
      slot <= '0; crc <= '1;
      rep_valid <= 1'b0; rep_slot <= '0; rep_ok <= 1'b0; rep_err <= 1'b0;
    end else begin
      lfsr <= {{lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]}};
      rep_valid <= 1'b0;
      tx_d <= tx_en;
      // ---- transmit-opportunity counter
      if (bcnt != 0) begin
        bcnt <= bcnt - 4'd1;
        if (bcnt == 4'd1) begin cur <= '0; tmr <= '0; busy <= 1'b0; end
      end else if (act) busy <= 1'b1;
      else if (busy || tmr == 4'(TO_TIMER - 1)) begin
        tmr <= '0; busy <= 1'b0;
        if (cur == 4'(N - 1)) bcnt <= 4'(BEACON);
        else cur <= cur + 4'd1;
      end else tmr <= tmr + 4'd1;
      // ---- the other nodes: a frame of 3..10 clocks, decided in the
      // opportunity's second clock
      if (o_tx) begin
        if (olen == 4'd1) o_tx <= 1'b0;
        olen <= olen - 4'd1;
      end else if (bcnt == 0 && cur != 4'(LOCAL) && tmr == 4'd1 && !busy && lfsr[0] ^ lfsr[6]) begin
        o_tx <= 1'b1; olen <= 4'd3 + {{1'b0, lfsr[3:1]}};
      end
      // ---- the agent's frames
      if (tx_en) begin
        if (!tx_d) begin                              // start of frame
          slot <= cur; lo <= 1'b1; crc <= crc_nib(32'hFFFF_FFFF, txd);
          // a second frame in the same opportunity cannot happen: the
          // opportunity ends the clock its frame's carrier falls
          err <= bcnt != 0 || cur != 4'(LOCAL) || busy || o_tx;
        end else begin
          lo <= ~lo; crc <= crc_nib(crc, txd);
          if (o_tx) err <= 1'b1;                      // collision
        end
      end else if (tx_d) begin                        // end of frame: report
        rep_valid <= 1'b1; rep_slot <= slot; rep_err <= err;
        rep_ok <= !lo && crc == 32'hDEBB_20E3;        // whole bytes, CRC-32 residue
      end
    end
  end
endmodule
""".format(n=N_NODES, lid=LOCAL_ID, to=TO_TIMER, bc=BEACON),
    sva="""
logic tx_d;
always_ff @(posedge clk or negedge rst_n) if (!rst_n) tx_d <= 1'b0; else tx_d <= tx_en;
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({{tx_en, beacon, crs, rep_valid}}))
  else $error("PLCA: X on TX_EN / BEACON / CRS / report");
assert property (@(posedge clk) disable iff (!rst_n) tx_en |-> !$isunknown(txd))
  else $error("PLCA: X on TXD while TX_EN");
// a frame never starts during the BEACON or over another node's carrier
assert property (@(posedge clk) disable iff (!rst_n) $rose(tx_en) |-> !crs)
  else $error("PLCA: frame started over a carrier");
// the BEACON lasts {bc} clocks
assert property (@(posedge clk) disable iff (!rst_n) $rose(beacon) |-> beacon [*{bc}] ##1 !beacon)
  else $error("PLCA: BEACON length");
// a report follows the end of each frame, one clock later
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> $past(tx_d && !tx_en))
  else $error("PLCA: report without the end of a frame");
assert property (@(posedge clk) disable iff (!rst_n) $fell(tx_en) |=> rep_valid)
  else $error("PLCA: frame not reported");
cover property (@(posedge clk) disable iff (!rst_n) crs && !beacon ##[1:$] $rose(tx_en));
cover property (@(posedge clk) disable iff (!rst_n) $fell(tx_en) ##[1:40] beacon);
""".format(bc=BEACON),
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic tx_en = 0;
logic [3:0] txd = 0;
wire beacon, crs, rep_valid, rep_ok, rep_err;
wire [3:0] rep_slot;

always #5 clk = ~clk;

t1s_plca_model u_dut (.clk(clk), .rst_n(rst_n), .tx_en(tx_en), .txd(txd), .beacon(beacon), .crs(crs),
                      .rep_valid(rep_valid), .rep_slot(rep_slot), .rep_ok(rep_ok), .rep_err(rep_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// the PLCA counter as every node runs it (clause 148), mirrored from the
// reset values on: compared with the segment's BEACON every clock, and the
// other nodes may only start in their own opportunity's third clock
int cur = 0, tmr = 0, bcnt = 4;
bit busy = 0, synced = 0;
int n_beacon = 0, n_other = 0, n_yield = 0, beacon_len = 0, max_beacon_len = 0;
int n_bmis = 0, n_obad = 0, olen = 0, olen_min = 99, olen_max = 0;
bit crs_d = 0;
always @(posedge clk) if (rst_n) begin
  bit act;
  act = (crs && !beacon) || tx_en;
  if (bcnt != 0) begin
    if (bcnt == 1) begin cur = 0; tmr = 0; busy = 0; synced = 1; end
    bcnt--;
  end else if (act) busy = 1;
  else if (busy || tmr == 8 - 1) begin
    if (!busy) n_yield++;
    tmr = 0; busy = 0;
    if (cur == 8 - 1) bcnt = 4;
    else cur++;
  end else tmr++;
  #1;
  if (beacon !== (bcnt != 0)) n_bmis++;
  if (beacon) begin
    if (beacon_len == 0) n_beacon++;
    beacon_len++;
    if (beacon_len > max_beacon_len) max_beacon_len = beacon_len;
  end else beacon_len = 0;
  if (crs && !beacon) begin
    if (!crs_d) begin
      n_other++;
      if (cur == 3 || tmr != 2) n_obad++;
    end
    olen++;
  end else if (olen != 0) begin
    if (olen < olen_min) olen_min = olen;
    if (olen > olen_max) olen_max = olen;
    olen = 0;
  end
  crs_d = crs && !beacon;
end

int nrep = 0;
logic r_ok, r_err; logic [3:0] r_slot;
always @(posedge clk) if (rep_valid) begin nrep++; r_ok = rep_ok; r_err = rep_err; r_slot = rep_slot; end

// CRC-32 with the FCS appended
bit [7:0] fr[$];
task automatic make(input string s, input bit bad);
  bit [31:0] c = 32'hFFFF_FFFF;
  fr.delete();
  foreach (s[i]) begin
    fr.push_back(s[i]);
    c ^= {24'h0, s[i]};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  c = ~c ^ {31'h0, bad};
  for (int i = 0; i < 4; i++) fr.push_back(c[i*8 +: 8]);
endtask
// wait until this node's counter says ID == id, no carrier, room left
task automatic wait_to(input int id);
  int n = 0;
  do begin @(posedge clk); #1; n++; end
  while (!(synced && cur == id && !busy && tmr <= """ + str(TO_TIMER - 3) + """ && !crs) && n < 2000);
endtask
task automatic send(input bit odd = 0);
  foreach (fr[i]) begin
    tx_en = 1; txd = fr[i][3:0]; @(posedge clk); #1;
    txd = fr[i][7:4]; @(posedge clk); #1;
  end
  if (odd) begin txd = 4'h5; @(posedge clk); #1; end
  tx_en = 0; txd = 0;
endtask
task automatic wait_rep(input int prev);
  int n = 0;
  while (nrep == prev && n < 10) begin @(posedge clk); n++; end
  #1;
endtask

initial begin
  int b;
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0, "no report in reset");
  rst_n = 1;
  #1;
  chk(beacon === 1'b1 && crs === 1'b1, "the coordinator starts with a BEACON, carrier on");
  repeat (400) @(posedge clk); #1;
  chk(nrep == 0, "no report without a frame");
  chk(n_beacon >= 3, $sformatf("BEACONs repeat (%0d in 400 clocks)", n_beacon));
  chk(n_bmis == 0, $sformatf("BEACON exactly when the clause 148 counter ends a cycle (%0d clocks differ)", n_bmis));
  chk(n_obad == 0, "other nodes start only in their own opportunity, never in node 3's");
  chk(olen_min >= 3 && olen_max <= 10, $sformatf("other nodes' frames %0d..%0d clocks", olen_min, olen_max));
  chk(max_beacon_len == """ + str(BEACON) + """, $sformatf("BEACON lasts %0d clocks", max_beacon_len));
  chk(n_other > 0 && n_yield > 0, "other nodes send frames, unused opportunities expire");

  // a frame in this node's opportunity
  make("123456789", 0); wait_to(""" + str(LOCAL_ID) + """); b = nrep; send(); wait_rep(b);
  chk(nrep == b + 1 && r_ok === 1'b1 && r_err === 1'b0 && r_slot == """ + str(LOCAL_ID) + """, "frame in its own opportunity: FCS good, no error, slot 3");
  // a second frame in the same opportunity
  b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b1, "second frame in the same opportunity flagged");
  // a frame in another node's opportunity
  wait_to(5); b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b1 && r_slot == 5, "frame in node 5's opportunity flagged");
  // the next cycle: allowed again
  make("a", 0); wait_to(""" + str(LOCAL_ID) + """); b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b0 && r_ok === 1'b1, "the next cycle's opportunity: accepted");
  // bad FCS, odd nibble count
  make("hello", 1); wait_to(""" + str(LOCAL_ID) + """); b = nrep; send(); wait_rep(b);
  chk(r_ok === 1'b0 && r_err === 1'b0, "bad FCS reported");
  make("hello", 0); wait_to(""" + str(LOCAL_ID) + """); b = nrep; send(1); wait_rep(b);
  chk(r_ok === 1'b0, "odd nibble count reported");
  // during a BEACON
  make("x", 0);
  do begin @(posedge clk); #1; end while (!beacon);
  b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b1, "frame during the BEACON flagged");
  // over another node's carrier
  do begin @(posedge clk); #1; end while (!(crs && !beacon));
  b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b1, "frame over another node's carrier flagged");
  // a long frame in its own opportunity holds the opportunity open
  make("the quick brown fox jumps over the lazy dog", 0);
  wait_to(""" + str(LOCAL_ID) + """); b = nrep; send(); wait_rep(b);
  chk(r_err === 1'b0 && r_ok === 1'b1, "long frame: the opportunity lasts until the carrier falls");
  chk(cur == """ + str(LOCAL_ID + 1) + """ || beacon, "the next opportunity starts after the frame");

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
