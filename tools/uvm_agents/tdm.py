# TDM audio transmitter agent (multi-channel serial audio, DSP / TDM mode B:
# FSYNC high for the first bit of the frame, data MSB first, no delay), as
# used between SoCs and multi-channel codecs / amplifiers and microphone
# arrays. The bus clock is the system clock (BCLK); frames are TDM8 with
# 16-bit slots (128 BCLK per frame).
# tb/top_tb.sv tdm_model: the receiver. It starts a frame at FSYNC, collects
# the 8 slots and reports one clock after the last bit: the 8 slot values and
# an error flag for an FSYNC anywhere but the first bit of a frame (too wide
# or early). An FSYNC inside a frame restarts the frame (the old one is
# reported with the error flag and the bits it had). After a complete frame
# with no FSYNC on the next bit the receiver waits idle.

NSLOT, W = 8, 16
FB = NSLOT * W

SPEC = dict(
    vip="TDM-UVM-VIP", p="tdm", P="TDM audio", dir="tdm", family="Audio",
    desc="TDM multi-channel audio transmitter VIP (TDM8, 16-bit slots, DSP mode B framing): FSYNC "
         "alignment, MSB-first slots, back-to-back frames, idle gaps and framing faults.",
    about="""
TDM carries many audio channels on one data line: after each frame sync pulse
the transmitter sends one fixed-width slot per channel, MSB first. Codecs,
smart amplifiers and microphone arrays use it in place of several I2S lines.
The DUT model is a TDM8 receiver that rebuilds every slot of a frame and flags
a frame sync in the wrong place; the scoreboard predicts the slots and the flag
from the frame the agent sent, so a slot shifted by one bit, a swapped channel
or a lost frame shows up as a mismatch.""",
    timeout=400,
    ports=[
        ("in", "logic", "fsync"), ("in", "logic", "sd"),
        ("out", "logic", "rep_valid"), ("out", "logic [%d:0]" % (FB - 1), "rep_slots"), ("out", "logic", "rep_err"),
    ],
    fields=[
        ("bit [15:0]", "slot", "req", "q"),
        ("bit", "bad_sync", "req"),            # FSYNC held for two clocks (framing fault)
        ("bit [15:0]", "rslot", "rsp", "q"),
        ("bit", "err", "rsp"),
        ("bit [2:0]", "gap", "info", "rand"),  # idle clocks before the frame (0 = back to back)
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [3:0]", "kind", "info", "rand"),
    ],
    constraints="""
constraint c_gap { gap dist { 0 := 6, [1:7] :/ 2 }; kind dist { 0 := 12, [1:15] :/ 4 }; }
""",
    tr_functions="""
function void post_randomize();
  bit [31:0] x = seed | 32'h1;
  slot.delete();
  for (int i = 0; i < %d; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    case (kind)
      1: slot.push_back(16'h8000);               // full-scale negative
      2: slot.push_back(16'h7FFF);               // full-scale positive
      3: slot.push_back(16'(i));                 // channel number
      default: slot.push_back(x[15:0]);
    endcase
  end
  bad_sync = (kind == 15);
endfunction
""" % NSLOT,
    drv_rsp=False,
    drv_desc="FSYNC on the first bit of each frame, the 8 slots MSB first, optional idle clocks before a frame",
    drv_idle="""
vif.drv_cb.fsync <= 1'b0; vif.drv_cb.sd <= 1'b0;
""",
    drv_item="""
repeat (t.gap) begin vif.drv_cb.fsync <= 1'b0; vif.drv_cb.sd <= 1'b0; @(vif.drv_cb); end
for (int s = 0; s < %d; s++)
  for (int b = %d; b >= 0; b--) begin
    int n = s * %d + (%d - b);
    vif.drv_cb.fsync <= (n == 0) || (n == 1 && t.bad_sync);
    vif.drv_cb.sd <= t.slot[s][b];
    @(vif.drv_cb);
  end
vif.drv_cb.fsync <= 1'b0; vif.drv_cb.sd <= 1'b0;
""" % (NSLOT, W - 1, W, W - 1),
    mon_desc="frames rebuilt from FSYNC and SD, completed by the receiver's report",
    mon_members="tdm_transaction cur; int unsigned nbit; tdm_transaction done_q[$];",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rep_valid) begin
    if (done_q.size() == 0) `uvm_error("MON", "TDM: frame report without a frame")
    else begin
      tdm_transaction t = done_q.pop_front();
      for (int s = 0; s < %d; s++) t.rslot.push_back(vif.mon_cb.rep_slots[%d - 1 - s*%d -: %d]);
      t.err = vif.mon_cb.rep_err;
      publish(t);
    end
  end
  if (vif.mon_cb.fsync && !(cur != null && nbit == 1)) begin
    if (cur != null) `uvm_error("MON", $sformatf("TDM: FSYNC after %%0d bits of a frame", nbit))
    cur = tdm_transaction::type_id::create("t");
    nbit = 0;
  end else if (vif.mon_cb.fsync && cur != null && nbit == 1) cur.bad_sync = 1;
  if (cur != null) begin
    if (nbit %% %d == 0) cur.slot.push_back(0);
    cur.slot[nbit / %d][%d - nbit %% %d] = vif.mon_cb.sd;
    nbit++;
    if (nbit == %d) begin done_q.push_back(cur); cur = null; end
  end
end
""" % (NSLOT, FB, W, W, W, W, W - 1, W, FB),
    predict="""
t.rslot = t.slot;
t.err = t.bad_sync;
""",
    checks="""
if (t.slot.size() != %d) fail(t, "frame without %d slots");
""" % (NSLOT, NSLOT),
    coverage="""
cp_gap  : coverpoint tr.gap { bins b2b = {0}; bins gap = {[1:7]}; }
cp_s0   : coverpoint tr.slot[0] { bins neg_fs = {16'h8000}; bins pos_fs = {16'h7FFF}; bins zero = {0}; bins other = default; }
cp_s7   : coverpoint tr.slot[7] { bins neg = {[16'h8000:16'hFFFF]}; bins pos = {[16'h0001:16'h7FFF]}; bins zero = {0}; }
cp_err  : coverpoint tr.err;
x_gap_err : cross cp_gap, cp_err;
""",
    directed="""
// channel numbers, full scale both ways, alternating bits, one channel only,
// frames back to back and after a gap, then framing faults
t = item(); t.gap = 0; for (int i = 0; i < 8; i++) t.slot.push_back(16'(i)); send(t);
t = item(); t.gap = 0; repeat (8) t.slot.push_back(16'h8000); send(t);
t = item(); t.gap = 0; repeat (8) t.slot.push_back(16'h7FFF); send(t);
t = item(); t.gap = 3; repeat (8) t.slot.push_back(16'hAAAA); send(t);
t = item(); t.gap = 0; repeat (8) t.slot.push_back(16'h5555); send(t);
t = item(); t.gap = 1; for (int i = 0; i < 8; i++) t.slot.push_back(i == 5 ? 16'hFFFF : 16'h0000); send(t);
t = item(); t.gap = 0; t.bad_sync = 1; for (int i = 0; i < 8; i++) t.slot.push_back(16'h1111 * i); send(t);
t = item(); t.gap = 0; for (int i = 0; i < 8; i++) t.slot.push_back(16'h0101 << i); send(t);
t = item(); t.gap = 7; t.bad_sync = 1; repeat (8) t.slot.push_back(16'h0001); send(t);
""",
    drain_ns=4000,
    model="""
module tdm_model (
  input  logic          clk,
  input  logic          rst_n,
  input  logic          fsync,
  input  logic          sd,
  output logic          rep_valid,
  output logic [%(top)d:0] rep_slots,
  output logic          rep_err
);
  logic [%(top)d:0] sh;
  logic [7:0]   nbit;
  logic         active, err;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sh <= '0; nbit <= '0; active <= 1'b0; err <= 1'b0;
      rep_valid <= 1'b0; rep_slots <= '0; rep_err <= 1'b0;
    end else begin
      rep_valid <= 1'b0;
      if (fsync && !(active && nbit == 8'd1)) begin
        // a new frame; one still open is reported as broken
        if (active) begin
          rep_valid <= 1'b1; rep_slots <= sh << (%(fb)d - nbit); rep_err <= 1'b1;
        end
        active <= 1'b1; nbit <= 8'd1; err <= 1'b0; sh <= {{%(top)d{1'b0}}, sd};
      end else if (active) begin
        if (fsync) err <= 1'b1;                     // FSYNC on the second bit: too wide
        sh <= {sh[%(top1)d:0], sd};
        nbit <= nbit + 8'd1;
        if (nbit == 8'd%(last)d) begin
          active <= 1'b0;
          rep_valid <= 1'b1; rep_slots <= {sh[%(top1)d:0], sd}; rep_err <= err | fsync;
        end
      end
    end
  end
endmodule
""" % dict(top=FB - 1, top1=FB - 2, fb=FB, last=FB - 1),
    sva="""
logic [7:0] n;
logic act;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin n <= '0; act <= 1'b0; end
  else if (fsync && !(act && n == 8'd1)) begin act <= 1'b1; n <= 8'd1; end
  else if (act) begin n <= n + 8'd1; if (n == 8'd%(last)d) act <= 1'b0; end
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({fsync, sd, rep_valid}))
  else $error("TDM: X on FSYNC / SD / report");
// the receiver reports a framing fault for an FSYNC in the wrong place
// (the tests plant some on purpose, so these are not assertions)
cover property (@(posedge clk) disable iff (!rst_n) fsync ##1 fsync);
cover property (@(posedge clk) disable iff (!rst_n) act && n > 8'd1 && fsync);
// a wide FSYNC is reported as an error with the frame
assert property (@(posedge clk) disable iff (!rst_n) act && n == 8'd1 && fsync |-> ##[1:128] rep_valid && rep_err)
  else $error("TDM: wide FSYNC not reported");
// a frame is reported one clock after its last bit
assert property (@(posedge clk) disable iff (!rst_n) act && n == 8'd%(last)d && !fsync |=> rep_valid)
  else $error("TDM: complete frame not reported");
cover property (@(posedge clk) disable iff (!rst_n) act && n == 8'd%(last)d ##1 fsync);
cover property (@(posedge clk) disable iff (!rst_n) act && n == 8'd%(last)d ##1 !fsync);
""" % dict(last=FB - 1),
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic fsync = 0, sd = 0;
wire rep_valid, rep_err;
wire [%(top)d:0] rep_slots;

always #5 clk = ~clk;

tdm_model u_dut (.clk(clk), .rst_n(rst_n), .fsync(fsync), .sd(sd), .rep_valid(rep_valid),
                 .rep_slots(rep_slots), .rep_err(rep_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %%s", msg); end
endtask

int nrep = 0;
logic [%(top)d:0] r_slots; logic r_err;
logic [%(top)d:0] p_slots; logic p_err;   // the report before the last
always @(posedge clk) if (rep_valid) begin
  nrep++; p_slots = r_slots; p_err = r_err; r_slots = rep_slots; r_err = rep_err;
end

logic [%(top)d:0] f;
// one frame: FSYNC at bit 0 (and bit 1 when wide), stop after n bits
task automatic frame(input logic [%(top)d:0] v, input int n = %(fb)d, input bit wide = 0);
  for (int i = 0; i < n; i++) begin
    fsync = (i == 0) || (i == 1 && wide); sd = v[%(top)d - i];
    @(posedge clk); #1;
  end
  fsync = 0; sd = 0;
endtask
task automatic idle(input int n); fsync = 0; sd = 0; repeat (n) @(posedge clk); #1; endtask

initial begin
  int b;
  repeat (3) @(posedge clk);
  chk(nrep == 0, "no report during reset");
  rst_n = 1;
  idle(%(fb)d + 20);
  chk(nrep == 0, "no frame open after reset");
  // channels 0..7 in slots 0..7
  for (int i = 0; i < 8; i++) f[%(top)d - 16*i -: 16] = 16'(i);
  b = nrep; frame(f); idle(2);
  chk(nrep == b + 1 && r_slots == f && r_err === 1'b0, "TDM8 frame: slot i = i, no error");
  // two frames back to back, no idle clock
  b = nrep;
  frame({8{16'h8000}});
  chk(nrep == b, "report only after the frame's last bit");
  frame({8{16'h7FFF}}); idle(2);
  chk(nrep == b + 2 && r_slots == {8{16'h7FFF}} && r_err === 1'b0, "back-to-back frames: both reported");
  // MSB first, bit order inside a slot
  f = '0; f[%(top)d] = 1'b1;
  b = nrep; frame(f); idle(2);
  chk(r_slots[%(top)d -: 16] == 16'h8000 && r_slots[%(top1)d - 15 -: 16] == 16'h0, "first bit after FSYNC is the MSB of slot 0");
  f = '0; f[0] = 1'b1;
  b = nrep; frame(f); idle(2);
  chk(r_slots[15:0] == 16'h0001 && r_err === 1'b0, "last bit is the LSB of slot 7");
  // wide FSYNC
  b = nrep; frame({8{16'h1234}}, %(fb)d, 1); idle(2);
  chk(nrep == b + 1 && r_err === 1'b1 && r_slots == {8{16'h1234}}, "FSYNC two clocks wide: framing error, data kept");
  // early FSYNC: the open frame reported broken, the new one fine
  b = nrep; frame({8{16'hAAAA}}, 40); frame({8{16'h5555}}); idle(2);
  chk(nrep == b + 2, "early FSYNC: two reports");
  chk(p_err === 1'b1 && p_slots == ({8{16'hAAAA}} & ~({%(fb)d{1'b1}} >> 40)),
      "the cut frame: framing error, its 40 bits MSB-aligned");
  chk(r_err === 1'b0 && r_slots == {8{16'h5555}}, "the restarted frame is clean");
  // an idle gap of any length between frames
  b = nrep; frame({8{16'h0F0F}}); idle(1); frame({8{16'hF0F0}}); idle(37); frame({8{16'h00FF}}); idle(2);
  chk(nrep == b + 3 && r_slots == {8{16'h00FF}}, "frames after idle gaps");
  // nothing without FSYNC
  b = nrep; sd = 1; idle(300);
  chk(nrep == b, "no frame without FSYNC");

  if (fails == 0) $display("FUNC_PASS checks=%%0d", checks);
  else            $display("FUNC_FAIL checks=%%0d fails=%%0d", checks, fails);
  $finish;
end

initial begin
  #400000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""" % dict(top=FB - 1, top1=FB - 2, fb=FB),
)
