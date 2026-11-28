# Avalon-MM host agent (Intel Avalon Interface Specifications, Avalon-MM):
# pipelined reads with variable latency, burst reads and writes (burstcount
# 1..8, sequential word addresses), per-beat byteenable, a wait-state pattern
# on waitrequest, and the response signal on read beats and on
# writeresponsevalid.
#
# tb/top_tb.sv avalon_mm_model (agent):
#   * byte address[11:0]; 0x000-0x3FF is 256 x 32-bit words of memory,
#     0x400-0x7FF answers SLVERR (2'b10) and 0x800-0xFFF DECODEERROR (2'b11);
#     a burst decides each beat by its own address (base + 4 * beat, 12 bits).
#   * waitrequest: an LFSR stalls about one clock in four, and a command waits
#     while four responses are already queued (maximumPendingReadTransactions
#     = 4, write responses included). The first beat of a write burst also
#     waits while read responses are queued, so a read always returns the
#     memory as of its own command.
#   * responses are returned in command order: one readdatavalid beat per
#     burst beat (gaps from the LFSR), one writeresponsevalid per write burst
#     carrying the first non-OKAY beat response. burstcount 0 is taken as 1.
from _lib import wait_cb

SPEC = dict(
    vip="Avalon_MM-UVM-VIP", p="avalon_mm", P="Avalon-MM", dir="avalon_mm", family="Interconnect",
    desc="Intel Avalon-MM host VIP: pipelined variable-latency reads, read / write bursts with per-beat "
         "byteenable, waitrequest wait states, response codes on read data and write responses.",
    about="""
The DUT model is a memory agent with an error region (SLVERR) and an undecoded
region (DECODEERROR). It holds up to four responses pending, inserts wait states
from an LFSR and returns read beats with gaps. The scoreboard keeps its own copy
of the memory, applies byte enables beat by beat and predicts every read beat and
write response. The SVA checks the Avalon-MM host rules: command signals held
while waitrequest is high, burstcount within maxBurstSize, no read while a write
burst is in progress, and the agent's response signals.""",
    timeout=200,
    ports=[
        ("in", "logic [11:0]", "av_address"), ("in", "logic [3:0]", "av_burstcount"),
        ("in", "logic [3:0]", "av_byteenable"), ("in", "logic", "av_read"), ("in", "logic", "av_write"),
        ("in", "logic [31:0]", "av_writedata"), ("out", "logic", "av_waitrequest"),
        ("out", "logic [31:0]", "av_readdata"), ("out", "logic", "av_readdatavalid"),
        ("out", "logic [1:0]", "av_response"), ("out", "logic", "av_writeresponsevalid"),
    ],
    cfg="int unsigned max_beats = 8;   // maxBurstSize",
    fields=[
        ("bit", "write", "req"),
        ("bit [11:0]", "address", "req"),
        ("bit [3:0]", "burstcount", "req"),
        ("bit [31:0]", "pbe", "req"),          # byteenable of beat i at [4i+3:4i] (writes)
        ("bit [255:0]", "wdata", "req"),       # beat i at [32i+31:32i]
        ("bit [255:0]", "rdata", "rsp"),
        ("bit [15:0]", "resp", "rsp"),         # read: beat i at [2i+1:2i]; write: [1:0]
        ("bit [2:0]", "gap", "info", "rand"),  # idle clocks before the command
        ("bit [7:0]", "bgap", "info", "rand"), # write: an idle clock before beat i when bit i is set
        ("bit [1:0]", "region", "info", "rand"),
        ("int unsigned", "wait_cyc", "info"),  # waitrequest clocks of the first beat
        ("int unsigned", "npend", "info"),     # responses pending when the command was accepted
        ("bit", "pipe", "info", "rand"),       # driver: go on without waiting for the response
        ("bit", "done", "info"),               # driver: response collected
    ],
    constraints="""
// region 0: memory, 1: SLVERR, 2: DECODEERROR, 3: a burst that runs from memory into the SLVERR region
constraint c_addr { address[1:0] == 2'b00;
                    region dist { 0 := 6, 1 := 1, 2 := 1, 3 := 2 };
                    region == 0 -> address[11:10] == 2'b00;
                    region == 1 -> address[11:10] == 2'b01;
                    region == 2 -> address[11] == 1'b1;
                    region == 3 -> address[11:5] == 7'h1F && address[4:2] >= 3'd5; }
constraint c_bc   { burstcount inside {[1:8]};
                    region == 3 -> burstcount >= 4; }
constraint c_wd   { !write -> wdata == 0 && pbe == 0 && bgap == 0; }
constraint c_gap  { gap dist { 0 := 6, [1:7] :/ 2 }; }
constraint c_pipe { pipe dist { 1 := 4, 0 := 1 }; }
""",
    drv_rsp=False,
    drv_desc="pipelined commands (an item with pipe = 0, e.g. from the register layer, waits for its response); "
             "write bursts beat by beat, with optional idle clocks",
    drv_members="""avalon_mm_transaction dq[$];   // accepted commands, in order, waiting for their response
int unsigned dbeat = 0;""",
    drv_bg="""
forever begin
  @(vif.drv_cb);
  if (vif.drv_cb.av_readdatavalid === 1'b1 && dq.size() != 0) begin
    dq[0].rdata[32 * dbeat +: 32] = vif.drv_cb.av_readdata;
    dq[0].resp[2 * dbeat +: 2] = vif.drv_cb.av_response;
    if (++dbeat >= dq[0].burstcount) begin dq[0].done = 1; void'(dq.pop_front()); dbeat = 0; end
  end
  if (vif.drv_cb.av_writeresponsevalid === 1'b1 && dq.size() != 0) begin
    dq[0].resp = {14'h0, vif.drv_cb.av_response}; dq[0].done = 1; void'(dq.pop_front());
  end
end""",
    drv_idle="""
vif.drv_cb.av_read <= 1'b0; vif.drv_cb.av_write <= 1'b0; vif.drv_cb.av_address <= '0;
vif.drv_cb.av_burstcount <= 4'd1; vif.drv_cb.av_byteenable <= 4'hF; vif.drv_cb.av_writedata <= '0;
""",
    drv_item="""
// beats past the burst carry nothing (the monitor sees only real beats)
for (int i = 0; i < 8; i++)
  if (!t.write || i >= t.burstcount) begin t.wdata[32 * i +: 32] = 0; t.pbe[4 * i +: 4] = 0; t.bgap[i] = 0; end
t.bgap[0] = 0;
repeat (t.gap) @(vif.drv_cb);
for (int i = 0; i < (t.write ? t.burstcount : 1); i++) begin
  if (t.bgap[i]) begin vif.drv_cb.av_write <= 1'b0; @(vif.drv_cb); end
  vif.drv_cb.av_read <= !t.write; vif.drv_cb.av_write <= t.write;
  vif.drv_cb.av_address <= t.address; vif.drv_cb.av_burstcount <= t.burstcount;
  vif.drv_cb.av_byteenable <= t.write ? t.pbe[4 * i +: 4] : 4'hF;
  vif.drv_cb.av_writedata <= t.wdata[32 * i +: 32];
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.av_waitrequest === 1'b0", "Avalon-MM command accept").splitlines()) + """
end
vif.drv_cb.av_read <= 1'b0; vif.drv_cb.av_write <= 1'b0;
t.done = 0; t.rdata = 0; t.resp = 0;
dq.push_back(t);
if (!t.pipe) begin
  int unsigned to = 0;
  while (!t.done && to < cfg.timeout_cycles) begin @(vif.drv_cb); to++; end
  if (!t.done) `uvm_error("TIMEOUT", "Avalon-MM: no response")
end
""",
    mon_desc="commands taken on read/write without waitrequest (write bursts beat by beat), completed in command order "
             "by readdatavalid beats or writeresponsevalid",
    mon_members="avalon_mm_transaction pend[$];   // accepted commands waiting for their response",
    mon_run="""
avalon_mm_transaction wr;          // write burst being collected
int unsigned wbeat = 0, rbeat = 0, waits = 0;
bit idle_in_burst = 0;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin pend.delete(); wr = null; wbeat = 0; rbeat = 0; waits = 0; continue; end
  // responses first: a response never answers a command of the same clock
  if (vif.mon_cb.av_readdatavalid) begin
    if (pend.size() == 0 || pend[0].write) `uvm_error("MON", "Avalon-MM readdatavalid without a pending read")
    else begin
      pend[0].rdata[32 * rbeat +: 32] = vif.mon_cb.av_readdata;
      pend[0].resp[2 * rbeat +: 2] = vif.mon_cb.av_response;
      if (++rbeat == (pend[0].burstcount == 0 ? 1 : pend[0].burstcount)) begin publish(pend.pop_front()); rbeat = 0; end
    end
  end
  if (vif.mon_cb.av_writeresponsevalid) begin
    if (pend.size() == 0 || !pend[0].write) `uvm_error("MON", "Avalon-MM writeresponsevalid without a pending write")
    else begin pend[0].resp = {14'h0, vif.mon_cb.av_response}; publish(pend.pop_front()); end
  end
  if (wr != null && !vif.mon_cb.av_write) idle_in_burst = 1;
  if (vif.mon_cb.av_read || vif.mon_cb.av_write) begin
    if (vif.mon_cb.av_waitrequest) waits++;
    else if (vif.mon_cb.av_read) begin
      avalon_mm_transaction t = avalon_mm_transaction::type_id::create("t");
      t.write = 0; t.address = vif.mon_cb.av_address; t.burstcount = vif.mon_cb.av_burstcount;
      t.wait_cyc = waits; t.npend = pend.size(); waits = 0;
      pend.push_back(t);
    end else begin
      if (wr == null) begin
        wr = avalon_mm_transaction::type_id::create("t");
        wr.write = 1; wr.address = vif.mon_cb.av_address; wr.burstcount = vif.mon_cb.av_burstcount;
        wr.wait_cyc = waits; wr.npend = pend.size(); wbeat = 0;
      end
      waits = 0;
      wr.bgap[wbeat] = idle_in_burst; idle_in_burst = 0;
      wr.wdata[32 * wbeat +: 32] = vif.mon_cb.av_writedata;
      wr.pbe[4 * wbeat +: 4] = vif.mon_cb.av_byteenable;
      if (++wbeat == (wr.burstcount == 0 ? 1 : wr.burstcount)) begin pend.push_back(wr); wr = null; end
    end
  end
end
""",
    sb_members="""bit [31:0] mem [256];   // reset value 0
function bit [1:0] code(bit [11:0] a);
  return a[11] ? 2'b11 : a[10] ? 2'b10 : 2'b00;
endfunction""",
    predict="""
begin
  int unsigned n = (t.burstcount == 0) ? 1 : t.burstcount;
  bit [1:0] w = 2'b00;
  t.rdata = 0;
  if (t.write) t.resp = 0;
  for (int unsigned i = 0; i < n; i++) begin
    bit [11:0] a = t.address + 12'(4 * i);
    if (t.write) begin
      if (code(a) != 2'b00) begin if (w == 2'b00) w = code(a); end
      else for (int b = 0; b < 4; b++) if (t.pbe[4 * i + b]) mem[a[9:2]][8 * b +: 8] = t.wdata[32 * i + 8 * b +: 8];
    end else begin
      t.resp[2 * i +: 2] = code(a);
      t.rdata[32 * i +: 32] = (code(a) == 2'b00) ? mem[a[9:2]] : 32'h0;
    end
  end
  if (t.write) t.resp = {14'h0, w};
  else for (int unsigned i = n; i < 8; i++) t.resp[2 * i +: 2] = 2'b00;
end
""",
    checks="""
if (t.address[1:0] != 2'b00) fail(t, "address not word aligned");
if (t.burstcount == 0 || t.burstcount > cfg.max_beats) fail(t, $sformatf("burstcount %0d outside 1..%0d", t.burstcount, cfg.max_beats));
if (t.npend > 3) fail(t, $sformatf("%0d responses pending when a command was taken, the agent allows 4 in all", t.npend));
if (t.wait_cyc > 80) fail(t, $sformatf("command waited %0d clocks", t.wait_cyc));
""",
    coverage="""
cp_write  : coverpoint tr.write;
cp_bc     : coverpoint tr.burstcount { bins one = {1}; bins short_ = {[2:4]}; bins long_ = {[5:7]}; bins max = {8}; }
cp_region : coverpoint tr.address[11:10] { bins mem = {0}; bins slverr = {1}; bins decerr = {[2:3]}; }
cp_rresp  : coverpoint tr.resp[1:0] iff (!tr.write) { bins okay = {0}; bins slverr = {2}; bins decerr = {3}; }
cp_wresp  : coverpoint tr.resp[1:0] iff (tr.write) { bins okay = {0}; bins slverr = {2}; bins decerr = {3}; }
cp_cross  : coverpoint (tr.address[11:10] == 0 && tr.address[9:2] + tr.burstcount > 256) { bins straddle = {1}; }
cp_be     : coverpoint tr.pbe[3:0] iff (tr.write) { bins full = {4'hF}; bins none = {4'h0}; bins part = {[4'h1:4'hE]}; }
cp_bgap   : coverpoint (tr.bgap != 0) iff (tr.write && tr.burstcount > 1) { bins gaps = {1}; bins none = {0}; }
cp_pend   : coverpoint tr.npend { bins none = {0}; bins one = {1}; bins two = {2}; bins three = {3}; }
cp_wait   : coverpoint tr.wait_cyc { bins zero = {0}; bins one = {1}; bins more = {[2:$]}; }
x_rw_bc   : cross cp_write, cp_bc;
x_rw_reg  : cross cp_write, cp_region;
""",
    directed="""
// single beats, then bursts of every length, read back
for (int i = 0; i < 8; i++) begin
  t = item(); t.write = 1; t.address = 12'h40 * i; t.burstcount = i + 1; t.region = 0; t.gap = 0;
  for (int b = 0; b < 8; b++) t.wdata[32 * b +: 32] = 32'hA000_0000 | (i << 8) | b;
  t.pbe = '1; t.bgap = (i == 7) ? 8'b1010_1010 : 8'h0; send(t);
end
for (int i = 0; i < 8; i++) begin
  t = item(); t.write = 0; t.address = 12'h40 * i; t.burstcount = 8 - i; t.region = 0; t.gap = 0; send(t);
end
// byte enables beat by beat, and a write with none
t = item(); t.write = 1; t.address = 12'h200; t.burstcount = 4; t.region = 0; t.pbe = 32'h0000_8421; t.wdata = '1; send(t);
t = item(); t.write = 1; t.address = 12'h200; t.burstcount = 1; t.region = 0; t.pbe = 32'h0; t.wdata = 32'h1234; send(t);
t = item(); t.write = 0; t.address = 12'h200; t.burstcount = 4; t.region = 0; send(t);
// error regions, a burst running out of memory, the address wrap at 0xFFC
t = item(); t.write = 1; t.address = 12'h3F0; t.burstcount = 8; t.region = 3; t.pbe = '1; t.wdata = '1; send(t);
t = item(); t.write = 0; t.address = 12'h3F0; t.burstcount = 8; t.region = 3; send(t);
t = item(); t.write = 0; t.address = 12'h7F8; t.burstcount = 4; t.region = 1; send(t);
t = item(); t.write = 1; t.address = 12'h7FC; t.burstcount = 2; t.region = 1; t.pbe = '1; send(t);
t = item(); t.write = 0; t.address = 12'hFF8; t.burstcount = 4; t.region = 2; send(t);
t = item(); t.write = 1; t.address = 12'hFFC; t.burstcount = 2; t.region = 2; t.pbe = '1; t.wdata = '1; send(t);
t = item(); t.write = 0; t.address = 12'h000; t.burstcount = 1; t.region = 0; send(t);
// eight back-to-back reads fill the pending-response limit
for (int i = 0; i < 8; i++) begin t = item(); t.pipe = 1; t.write = 0; t.address = 12'h20 * i; t.burstcount = 1 + i % 3; t.region = 0; t.gap = 0; send(t); end
""",
    drain_ns=3000,
    model="""
module avalon_mm_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic [11:0] av_address,
  input  logic [3:0]  av_burstcount,
  input  logic [3:0]  av_byteenable,
  input  logic        av_read,
  input  logic        av_write,
  input  logic [31:0] av_writedata,
  output logic        av_waitrequest,
  output logic [31:0] av_readdata,
  output logic        av_readdatavalid,
  output logic [1:0]  av_response,
  output logic        av_writeresponsevalid
);
  logic [31:0] mem [0:255];
  // pending responses, in command order: {write, beats - 1, base address, write response}
  logic        q_wr  [0:3];
  logic [2:0]  q_n   [0:3];
  logic [11:0] q_a   [0:3];
  logic [1:0]  q_rsp [0:3];
  logic [1:0]  wp, rp;
  logic [2:0]  cnt, nrd;             // pending responses, pending reads
  logic [2:0]  beat;                 // read beat being returned
  logic [7:0]  lfsr;
  logic        wact;                 // a write burst is in progress
  logic [2:0]  wbeat, wlast;
  logic [11:0] wbase;
  logic [1:0]  wrsp;
  logic [11:0] wa, ra;
  logic        stall, acc_rd, acc_wr, wdone, give, last;

  function automatic logic [1:0] code(input logic [11:0] a);
    code = a[11] ? 2'b11 : a[10] ? 2'b10 : 2'b00;
  endfunction

  assign stall  = (lfsr[1:0] == 2'b00);
  // a new command waits while four responses are queued; a write burst starts only with no read pending
  assign av_waitrequest = rst_n && (av_read || av_write) &&
                          (stall || (cnt == 3'd4 && (av_read || !wact)) || (av_write && !wact && nrd != 3'd0));
  assign acc_rd = av_read && !av_write && !wact && !av_waitrequest;
  assign acc_wr = av_write && !av_waitrequest;
  assign wa     = (wact ? wbase : av_address) + {7'h0, (wact ? wbeat : 3'd0), 2'b00};
  assign wdone  = acc_wr && ((wact ? wbeat : 3'd0) == (wact ? wlast : (av_burstcount == 4'd0 ? 3'd0 : 3'(av_burstcount - 4'd1))));
  // response side: the head of the queue, a read beat when the LFSR allows (bit 3)
  assign give   = (cnt != 3'd0) && (q_wr[rp] || !lfsr[3]);
  assign ra     = q_a[rp] + {7'h0, beat, 2'b00};
  assign last   = q_wr[rp] || beat == q_n[rp];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 256; i++) mem[i] <= 32'h0;
      for (int i = 0; i < 4; i++) begin q_wr[i] <= 1'b0; q_n[i] <= 3'd0; q_a[i] <= 12'h0; q_rsp[i] <= 2'b00; end
      wp <= 2'd0; rp <= 2'd0; cnt <= 3'd0; nrd <= 3'd0; beat <= 3'd0; lfsr <= 8'h5B;
      wact <= 1'b0; wbeat <= 3'd0; wlast <= 3'd0; wbase <= 12'h0; wrsp <= 2'b00;
      av_readdata <= 32'h0; av_readdatavalid <= 1'b0; av_response <= 2'b00; av_writeresponsevalid <= 1'b0;
    end else begin
      lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
      av_readdatavalid <= 1'b0; av_writeresponsevalid <= 1'b0; av_response <= 2'b00; av_readdata <= 32'h0;
      // ---- write beats: memory updated beat by beat, the response queued after the last one
      if (acc_wr) begin
        if (code(wa) == 2'b00) begin
          for (int b = 0; b < 4; b++) if (av_byteenable[b]) mem[wa[9:2]][8 * b +: 8] <= av_writedata[8 * b +: 8];
        end
        if (!wact) begin
          wbase <= av_address; wlast <= (av_burstcount == 4'd0) ? 3'd0 : 3'(av_burstcount - 4'd1);
        end
        if (wdone) begin
          q_wr[wp] <= 1'b1; q_n[wp] <= 3'd0; q_a[wp] <= 12'h0;
          q_rsp[wp] <= ((wact ? wrsp : 2'b00) != 2'b00) ? wrsp : code(wa);
          wp <= wp + 2'd1; wact <= 1'b0; wbeat <= 3'd0; wrsp <= 2'b00;
        end else begin
          wact <= 1'b1; wbeat <= (wact ? wbeat : 3'd0) + 3'd1;
          if ((wact ? wrsp : 2'b00) == 2'b00) wrsp <= code(wa);
        end
      end
      // ---- read command queued
      if (acc_rd) begin
        q_wr[wp] <= 1'b0; q_n[wp] <= (av_burstcount == 4'd0) ? 3'd0 : 3'(av_burstcount - 4'd1); q_a[wp] <= av_address;
        q_rsp[wp] <= 2'b00; wp <= wp + 2'd1;
      end
      // ---- responses, in command order
      if (give) begin
        if (q_wr[rp]) begin
          av_writeresponsevalid <= 1'b1; av_response <= q_rsp[rp];
        end else begin
          av_readdatavalid <= 1'b1; av_response <= code(ra);
          av_readdata <= (code(ra) == 2'b00) ? mem[ra[9:2]] : 32'h0;
        end
        if (last) begin rp <= rp + 2'd1; beat <= 3'd0; end
        else beat <= beat + 3'd1;
      end
      cnt <= cnt + {2'b0, acc_rd || wdone} - {2'b0, give && last};
      nrd <= nrd + {2'b0, acc_rd} - {2'b0, give && last && !q_wr[rp]};
    end
  end
endmodule
""",
    sva="""
logic in_wr;            // a write burst has started and not finished
logic [3:0] wleft;
always @(posedge clk or negedge rst_n)
  if (!rst_n) begin in_wr <= 1'b0; wleft <= 4'd0; end
  else if (av_write && !av_waitrequest) begin
    if (!in_wr) begin in_wr <= (av_burstcount > 4'd1); wleft <= av_burstcount - 4'd2; end
    else if (wleft == 4'd0) in_wr <= 1'b0;
    else wleft <= wleft - 4'd1;
  end
// no X on the agent's outputs out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({av_waitrequest, av_readdatavalid, av_writeresponsevalid}))
  else $error("Avalon-MM: X on waitrequest / readdatavalid / writeresponsevalid");
assert property (@(posedge clk) disable iff (!rst_n) av_readdatavalid |-> !$isunknown({av_readdata, av_response}))
  else $error("Avalon-MM: X on readdata / response with readdatavalid");
// host rules
assert property (@(posedge clk) disable iff (!rst_n) !(av_read && av_write))
  else $error("Avalon-MM: read and write in the same clock");
assert property (@(posedge clk) disable iff (!rst_n) (av_read || av_write) |-> av_burstcount inside {[1:8]})
  else $error("Avalon-MM: burstcount outside 1..maxBurstSize");
assert property (@(posedge clk) disable iff (!rst_n) (av_read || av_write) && av_waitrequest |=>
                 $stable({av_read, av_write, av_address, av_burstcount, av_byteenable, av_writedata}))
  else $error("Avalon-MM: command changed while waitrequest was high");
assert property (@(posedge clk) disable iff (!rst_n) in_wr |-> !av_read)
  else $error("Avalon-MM: read during a write burst");
// agent rules
assert property (@(posedge clk) disable iff (!rst_n) !(av_readdatavalid && av_writeresponsevalid))
  else $error("Avalon-MM: readdatavalid and writeresponsevalid together");
assert property (@(posedge clk) disable iff (!rst_n) (av_readdatavalid || av_writeresponsevalid) |-> av_response != 2'b01)
  else $error("Avalon-MM: reserved response 2'b01");
cover property (@(posedge clk) disable iff (!rst_n) av_read && av_waitrequest ##1 av_read && !av_waitrequest);
cover property (@(posedge clk) disable iff (!rst_n) av_writeresponsevalid && av_response == 2'b10);
cover property (@(posedge clk) disable iff (!rst_n) av_read && !av_waitrequest && av_burstcount == 4'd8);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic [11:0] av_address = 0;
logic [3:0]  av_burstcount = 1, av_byteenable = 4'hF;
logic        av_read = 0, av_write = 0;
logic [31:0] av_writedata = 0;
wire         av_waitrequest, av_readdatavalid, av_writeresponsevalid;
wire  [31:0] av_readdata;
wire  [1:0]  av_response;

always #5 clk = ~clk;

avalon_mm_model u_dut (.clk(clk), .rst_n(rst_n), .av_address(av_address), .av_burstcount(av_burstcount),
                       .av_byteenable(av_byteenable), .av_read(av_read), .av_write(av_write),
                       .av_writedata(av_writedata), .av_waitrequest(av_waitrequest), .av_readdata(av_readdata),
                       .av_readdatavalid(av_readdatavalid), .av_response(av_response),
                       .av_writeresponsevalid(av_writeresponsevalid));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// response log, filled at every posedge
logic [31:0] r_data [0:255];
logic [1:0]  r_rsp  [0:255];
logic        r_wr   [0:255];
int nr = 0, nwait = 0, nacc = 0;
always @(posedge clk) begin
  if (av_readdatavalid || av_writeresponsevalid) begin
    r_data[nr % 256] = av_readdata; r_rsp[nr % 256] = av_response; r_wr[nr % 256] = av_writeresponsevalid; nr++;
  end
  if ((av_read || av_write) && av_waitrequest) nwait++;
  if ((av_read || av_write) && !av_waitrequest) nacc++;
end

// hold the current command until a clock without waitrequest
task automatic beat_go();
  bit w;
  do begin @(posedge clk); w = av_waitrequest; @(negedge clk); end while (w);   // waitrequest as sampled by the edge
endtask
task automatic idle(input int n); repeat (n) @(negedge clk); endtask

task automatic wr(input logic [11:0] a, input logic [3:0] bc, input logic [31:0] be, input logic [255:0] d,
                  input logic [7:0] gaps);
  int n = (bc == 0) ? 1 : bc;
  for (int i = 0; i < n; i++) begin
    if (gaps[i]) begin av_write = 0; idle(1); end
    av_write = 1; av_address = a; av_burstcount = bc; av_byteenable = be[4 * i +: 4]; av_writedata = d[32 * i +: 32];
    beat_go();
  end
  av_write = 0;
endtask
task automatic rd(input logic [11:0] a, input logic [3:0] bc);
  av_read = 1; av_address = a; av_burstcount = bc; av_byteenable = 4'hF;
  beat_go();
  av_read = 0;
endtask
// wait until k responses have arrived since r0
int r0;
task automatic resp(input int k);
  int t = 0;
  while (nr < r0 + k && t < 200) begin @(negedge clk); t++; end
  chk(nr >= r0 + k, $sformatf("%0d responses arrived", k));
endtask

initial begin
  idle(3);
  chk(!av_waitrequest && !av_readdatavalid && !av_writeresponsevalid && av_response == 0, "idle in reset");
  av_read = 1; #1; chk(!av_waitrequest, "no waitrequest in reset"); av_read = 0;
  @(negedge clk); rst_n = 1; idle(2);
  chk(!av_waitrequest, "no waitrequest without a command");

  // single write, read back
  r0 = nr; wr(12'h010, 1, 32'hF, 256'hCAFE_F00D, 0); resp(1);
  chk(r_wr[r0 % 256] && r_rsp[r0 % 256] == 2'b00, "write response OKAY");
  r0 = nr; rd(12'h010, 1); resp(1);
  chk(!r_wr[r0 % 256] && r_data[r0 % 256] == 32'hCAFE_F00D && r_rsp[r0 % 256] == 2'b00, "read back the word");
  r0 = nr; rd(12'h014, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h0, "neighbour word still 0");
  // byte lanes
  r0 = nr; wr(12'h010, 1, 32'h2, 256'h0000_AB00, 0); wr(12'h010, 1, 32'h8, 256'h7700_0000, 0);
  wr(12'h010, 1, 32'h0, 256'hFFFF_FFFF, 0); resp(3);
  r0 = nr; rd(12'h010, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h77FE_AB0D, $sformatf("byte-enable merge, no-byte write ignored (%h)", r_data[r0 % 256]));
  r0 = nr; wr(12'h020, 1, 32'h1, 256'h0000_0011, 0); wr(12'h020, 1, 32'h4, 256'h0022_0000, 0); resp(2);
  r0 = nr; rd(12'h020, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h0022_0011, "lanes 0 and 2");

  // write burst of 8 with idle clocks between beats, read burst of 8
  r0 = nr;
  wr(12'h100, 8, 32'hFFFF_FFFF, {32'h88, 32'h77, 32'h66, 32'h55, 32'h44, 32'h33, 32'h22, 32'h11}, 8'b1001_0110);
  resp(1);
  chk(nr == r0 + 1 && r_wr[r0 % 256] && r_rsp[r0 % 256] == 0, "one write response for the 8-beat burst");
  r0 = nr; rd(12'h100, 8); resp(8);
  begin
    bit ok = 1;
    for (int i = 0; i < 8; i++) if (r_data[(r0 + i) % 256] != 32'h11 * (i + 1) || r_wr[(r0 + i) % 256]) ok = 0;
    chk(ok, "8 read beats, sequential words");
  end
  r0 = nr; rd(12'h108, 3); resp(3);
  chk(r_data[r0 % 256] == 32'h33 && r_data[(r0 + 2) % 256] == 32'h55, "3-beat burst from the middle");
  r0 = nr; rd(12'h11C, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h88, "last word of the burst");
  r0 = nr; rd(12'h120, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h0, "word after the burst untouched");
  // burst byte enables beat by beat
  r0 = nr; wr(12'h180, 4, 32'h0000_8421, {4{32'hFFFF_FFFF}}, 0); resp(1);
  r0 = nr; rd(12'h180, 4); resp(4);
  chk(r_data[r0 % 256] == 32'h0000_00FF && r_data[(r0 + 1) % 256] == 32'h0000_FF00 &&
      r_data[(r0 + 2) % 256] == 32'h00FF_0000 && r_data[(r0 + 3) % 256] == 32'hFF00_0000, "per-beat byteenable");
  // burstcount 0 is one beat
  r0 = nr; wr(12'h1C0, 0, 32'hF, 256'h5A5A, 0); resp(1);
  chk(r_wr[r0 % 256], "burstcount 0 write: one beat, one response");
  r0 = nr; rd(12'h1C0, 0); resp(1); idle(5);
  chk(nr == r0 + 1 && r_data[r0 % 256] == 32'h5A5A, "burstcount 0 read: one beat");
  // last word, error regions
  r0 = nr; wr(12'h3FC, 1, 32'hF, 256'h1357, 0); rd(12'h3FC, 1); resp(2);
  chk(r_rsp[r0 % 256] == 2'b00 && r_data[(r0 + 1) % 256] == 32'h1357 && r_rsp[(r0 + 1) % 256] == 2'b00, "0x3FC is memory");
  r0 = nr; rd(12'h400, 1); rd(12'h7FC, 1); rd(12'h800, 1); rd(12'hFFC, 1); resp(4);
  chk(r_rsp[r0 % 256] == 2'b10 && r_rsp[(r0 + 1) % 256] == 2'b10 && r_data[r0 % 256] == 0, "0x400..0x7FF: SLVERR, data 0");
  chk(r_rsp[(r0 + 2) % 256] == 2'b11 && r_rsp[(r0 + 3) % 256] == 2'b11, "0x800..0xFFF: DECODEERROR");
  r0 = nr; wr(12'h400, 1, 32'hF, 256'h1, 0); wr(12'h800, 1, 32'hF, 256'h1, 0); resp(2);
  chk(r_rsp[r0 % 256] == 2'b10 && r_rsp[(r0 + 1) % 256] == 2'b11, "write responses SLVERR / DECODEERROR");
  r0 = nr; rd(12'h000, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h0, "an error-region write lands nowhere (0x400 does not alias 0x000)");
  // bursts across region boundaries: each beat by its own address
  r0 = nr; wr(12'h3F8, 4, 32'hFFFF, {32'h4, 32'h3, 32'h2, 32'h1}, 0); resp(1);
  chk(r_rsp[r0 % 256] == 2'b10, "write burst into SLVERR: first error response");
  r0 = nr; rd(12'h3F8, 4); resp(4);
  chk(r_data[r0 % 256] == 32'h1 && r_data[(r0 + 1) % 256] == 32'h2 && r_rsp[(r0 + 1) % 256] == 2'b00 &&
      r_rsp[(r0 + 2) % 256] == 2'b10 && r_rsp[(r0 + 3) % 256] == 2'b10 && r_data[(r0 + 2) % 256] == 0,
      "read burst into SLVERR: in-range beats OKAY, the rest SLVERR");
  r0 = nr; wr(12'h7FC, 2, 32'hFF, 256'h0, 0); rd(12'h7FC, 2); resp(3);
  chk(r_rsp[r0 % 256] == 2'b10 && r_rsp[(r0 + 1) % 256] == 2'b10 && r_rsp[(r0 + 2) % 256] == 2'b11,
      "SLVERR beat then DECODEERROR beat");
  r0 = nr; wr(12'h7F8, 4, 32'hFFFF, 256'h0, 0); resp(1);
  chk(r_rsp[r0 % 256] == 2'b10, "SLVERR, SLVERR, DECODEERROR, DECODEERROR: the first error is reported");
  r0 = nr; wr(12'hFFC, 2, 32'hFF, {32'hBEEF, 32'h0}, 0); resp(1);
  chk(r_rsp[r0 % 256] == 2'b11, "write wrapping 0xFFC -> 0x000: first beat DECODEERROR");
  r0 = nr; rd(12'h000, 1); resp(1);
  chk(r_data[r0 % 256] == 32'hBEEF, "the wrapped beat lands at 0x000");

  // pipelined reads: four pending, a fifth waits until the first burst has returned all its beats
  begin : pipe
    int acc = 0, t = 0, early = 0;
    r0 = nr;
    av_read = 1; av_address = 12'h100; av_burstcount = 8;
    while (acc < 5 && t < 300) begin
      #4; if (!av_waitrequest) begin acc++; if (acc == 5) early = (nr < r0 + 7); end
      @(negedge clk); t++;
    end
    av_read = 0;
    chk(acc == 5 && !early, $sformatf("a fifth read waits for the first burst (%0d, %0d)", acc, nr - r0));
    resp(40);
    idle(5);
    chk(nr == r0 + 40, "five bursts of 8 beats");
  end
  idle(10);

  // a write waits while reads are pending
  r0 = nr;
  av_read = 1; av_address = 12'h100; av_burstcount = 8; beat_go(); av_read = 0;
  av_write = 1; av_address = 12'h104; av_burstcount = 1; av_byteenable = 4'hF; av_writedata = 32'hDEAD;
  #1; chk(av_waitrequest, "write waits while a read is pending");
  beat_go(); av_write = 0;
  chk(nr == r0 + 8, $sformatf("the write is accepted only after the 8 read beats (%0d)", nr - r0));
  resp(9);
  chk(r_wr[(r0 + 8) % 256] && r_data[(r0 + 1) % 256] == 32'h22, "read returned the old word");
  r0 = nr; rd(12'h104, 1); resp(1);
  chk(r_data[r0 % 256] == 32'hDEAD, "the write landed after the read");
  // the LFSR wait-state pattern (about one clock in four) plus the full-queue waits of the pipelined reads
  chk(nwait == 54 && nacc == 61, $sformatf("wait states %0d for %0d accepted beats", nwait, nacc));

  // reset in the middle of a burst
  av_write = 1; av_address = 12'h300; av_burstcount = 4; av_writedata = 32'h1; beat_go();
  av_write = 0; rd(12'h300, 1);
  @(negedge clk); rst_n = 0; idle(2);
  chk(!av_readdatavalid && !av_writeresponsevalid && !av_waitrequest, "reset clears the responses");
  rst_n = 1; idle(2);
  r0 = nr; rd(12'h300, 1); resp(1);
  chk(r_data[r0 % 256] == 32'h0, "reset clears the memory");
  r0 = nr; wr(12'h304, 2, 32'hFF, {32'h2, 32'h1}, 0); resp(1);
  chk(r_wr[r0 % 256] && r_rsp[r0 % 256] == 0, "a new burst after reset starts at beat 0");
  r0 = nr; rd(12'h304, 2); resp(2);
  chk(r_data[r0 % 256] == 32'h1 && r_data[(r0 + 1) % 256] == 32'h2, "burst after reset at the right words");

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
        n_regs=64,
        desc="avalon_mm_model memory words 0..63 (byte address 0x000-0x0FC), reset 0",
        reg2bus="""
t.write      = (rw.kind == UVM_WRITE);
t.address    = rw.addr[11:0];
t.burstcount = 1;
t.pbe        = t.write ? 32'hF : 32'h0;
t.wdata      = t.write ? {224'h0, rw.data[31:0]} : 256'h0;
""",
        bus2reg="""
rw.kind   = t.write ? UVM_WRITE : UVM_READ;
rw.addr   = t.address;
rw.data   = t.write ? t.wdata[31:0] : t.rdata[31:0];
rw.status = (t.resp[1:0] == 2'b00) ? UVM_IS_OK : UVM_NOT_OK;
""",
    ),
)
