# OpenHW Group OBI (Open Bus Interface) v1.6 manager agent.
# tb/top_tb.sv obi_model: subordinate with 256 x 32-bit words at addr[9:2]
# (0x000-0x3FF), an error response (err = 1, no write) above, byte enables on
# writes, a grant pattern from an LFSR (about one stall in four) and up to four
# outstanding transactions answered in order through a response FIFO.
# The driver issues A-phase requests back to back (pipelined, without waiting
# for the response); a background process drives rready with random
# back-pressure; the monitor pairs R-phase responses with A-phase requests in
# order.

SPEC = dict(
    vip="OBI-UVM-VIP", p="obi", P="OBI", dir="obi", family="RISC-V / Interconnect",
    desc="OpenHW Group OBI 1.6 manager VIP: pipelined A channel (req/gnt), in-order R channel "
         "(rvalid/rready) with back-pressure, byte enables, error responses and transaction IDs.",
    about="""
OBI is the bus of the OpenHW CORE-V cores (CV32E40P, CV32E40X, CVA6 instruction /
data ports). The DUT model is a memory subordinate; the scoreboard keeps its own
copy of the memory (byte-enable merges, error region) and predicts every
response. The protocol rules checked by the SVA are the OBI 1.6 handshake rules:
an A-phase request may not be retracted or changed until granted, an R-phase
response is held until accepted, and the subordinate never answers more
transactions than were granted.""",
    timeout=200,
    ports=[
        ("in", "logic", "req"), ("out", "logic", "gnt"),
        ("in", "logic [31:0]", "addr"), ("in", "logic", "we"), ("in", "logic [3:0]", "be"),
        ("in", "logic [31:0]", "wdata"), ("in", "logic [3:0]", "aid"),
        ("out", "logic", "rvalid"), ("in", "logic", "rready"),
        ("out", "logic [31:0]", "rdata"), ("out", "logic", "err"), ("out", "logic [3:0]", "rid"),
    ],
    cfg="int unsigned rready_pct = 70;   // percent of clocks rready is high",
    fields=[
        ("bit", "we", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [3:0]", "be", "req"),
        ("bit [31:0]", "wdata", "req"),
        ("bit [3:0]", "aid", "req"),
        ("bit [31:0]", "rdata", "rsp"),
        ("bit", "err", "rsp"),
        ("bit [3:0]", "rid", "rsp"),
        ("bit [2:0]", "gap", "info", "rand"),          # idle clocks before the request
        ("bit", "oob", "info", "rand"),                # address in the error region
        ("int unsigned", "gnt_wait", "info"),          # clocks req waited for gnt
    ],
    constraints="""
// one request in ten goes to the error region 0x400-0xFFC (a dist over the
// address ranges would make Verilator pick a value before the alignment)
constraint c_addr { addr[1:0] == 2'b00; addr[31:12] == 0;
                    oob dist { 0 := 9, 1 := 1 };
                    oob -> addr[11:10] != 2'b00; !oob -> addr[11:10] == 2'b00; }
constraint c_be   { be != 4'h0; !we -> be == 4'hF; }
constraint c_wd   { !we -> wdata == 0; }
constraint c_gap  { gap dist { 0 := 6, [1:7] :/ 2 }; }
""",
    drv_rsp=False,
    drv_desc="A-phase requests, back to back, without waiting for the response; random rready",
    drv_idle="""
vif.drv_cb.req   <= 1'b0;
vif.drv_cb.addr  <= '0;
vif.drv_cb.we    <= 1'b0;
vif.drv_cb.be    <= '0;
vif.drv_cb.wdata <= '0;
vif.drv_cb.aid   <= '0;
vif.drv_cb.rready <= 1'b0;
""",
    drv_bg="""
forever begin
  @(vif.drv_cb);
  vif.drv_cb.rready <= ($urandom_range(99) < cfg.rready_pct);
end
""",
    drv_item="""
repeat (t.gap) @(vif.drv_cb);
vif.drv_cb.req   <= 1'b1;
vif.drv_cb.addr  <= t.addr;
vif.drv_cb.we    <= t.we;
vif.drv_cb.be    <= t.be;
vif.drv_cb.wdata <= t.wdata;
vif.drv_cb.aid   <= t.aid;
begin
  int unsigned to = 0;
  // the request is accepted on the clock gnt is sampled high with req
  do begin @(vif.drv_cb); to++; end while (vif.drv_cb.gnt !== 1'b1 && to < cfg.timeout_cycles);
  if (vif.drv_cb.gnt !== 1'b1) `uvm_error("TIMEOUT", "OBI: no gnt")
  t.gnt_wait = to - 1;
end
vif.drv_cb.req <= 1'b0;
""",
    mon_desc="A-phase handshakes (req & gnt) queued, completed by R-phase handshakes (rvalid & rready) in order",
    mon_members="obi_transaction pend[$];",
    mon_run="""
int unsigned waits = 0;
forever begin
  @(vif.mon_cb);
  // R phase first: a response can complete in the clock after its grant
  if (vif.mon_cb.rvalid && vif.mon_cb.rready) begin
    if (pend.size() == 0)
      `uvm_error("MON", "OBI: response without an outstanding request")
    else begin
      obi_transaction t = pend.pop_front();
      t.rdata = vif.mon_cb.rdata;
      t.err   = vif.mon_cb.err;
      t.rid   = vif.mon_cb.rid;
      publish(t);
    end
  end
  if (vif.mon_cb.req) begin
    if (vif.mon_cb.gnt) begin
      obi_transaction t = obi_transaction::type_id::create("t");
      t.we    = vif.mon_cb.we;
      t.addr  = vif.mon_cb.addr;
      t.be    = vif.mon_cb.be;
      t.wdata = t.we ? vif.mon_cb.wdata : 32'h0;
      t.aid   = vif.mon_cb.aid;
      t.gnt_wait = waits;
      waits = 0;
      pend.push_back(t);
    end else
      waits++;
  end
end
""",
    sb_members="bit [31:0] mem [256];   // reset value 0",
    predict="""
t.rid = t.aid;
if (t.addr >= 32'h400) begin
  t.err = 1'b1;
  t.rdata = 32'h0;
end else begin
  t.err = 1'b0;
  if (t.we) begin
    for (int b = 0; b < 4; b++)
      if (t.be[b]) mem[t.addr[9:2]][b*8 +: 8] = t.wdata[b*8 +: 8];
    t.rdata = 32'h0;
  end else
    t.rdata = mem[t.addr[9:2]];
end
""",
    checks="""
if (t.rid != t.aid) fail(t, "rid does not match the in-order request's aid");
if (t.addr[1:0] != 2'b00) fail(t, "unaligned word address");
if (t.we && t.be == 4'h0) fail(t, "write with no byte enabled");
if (t.gnt_wait > 16) fail(t, $sformatf("request waited %0d clocks for gnt", t.gnt_wait));
""",
    coverage="""
cp_we   : coverpoint tr.we;
cp_be   : coverpoint tr.be { bins full = {4'hF}; bins byte_[] = {4'h1, 4'h2, 4'h4, 4'h8};
                             bins half[] = {4'h3, 4'hC}; bins other = default; }
cp_err  : coverpoint tr.err;
cp_wait : coverpoint tr.gnt_wait { bins zero = {0}; bins one = {1}; bins more = {[2:$]}; }
x_we_err : cross cp_we, cp_err;
x_we_be  : cross cp_we, cp_be;
""",
    directed="""
// fill a few words with byte-lane writes and read them back
for (int i = 0; i < 4; i++) begin
  t = item(); t.we = 1; t.addr = 32'h10; t.be = 4'h1 << i; t.wdata = 32'h11 << (8 * i) | 32'hEEEE_EEEE; t.aid = i; send(t);
end
t = item(); t.we = 0; t.addr = 32'h10; t.be = 4'hF; t.aid = 4; send(t);
t = item(); t.we = 1; t.addr = 32'h3FC; t.be = 4'hF; t.wdata = 32'hDEAD_BEEF; t.aid = 5; send(t);
t = item(); t.we = 1; t.addr = 32'h3FC; t.be = 4'h6; t.wdata = 32'h00AA_5500; t.aid = 6; send(t);
t = item(); t.we = 0; t.addr = 32'h3FC; t.be = 4'hF; t.aid = 7; send(t);
// error region: the write must not land anywhere, the read returns err
t = item(); t.we = 1; t.addr = 32'h400; t.be = 4'hF; t.wdata = 32'h1234_5678; t.aid = 8; send(t);
t = item(); t.we = 0; t.addr = 32'h400; t.be = 4'hF; t.aid = 9; send(t);
t = item(); t.we = 0; t.addr = 32'h0;   t.be = 4'hF; t.aid = 10; send(t);
// back-to-back burst: eight requests with no gap keep four outstanding
for (int i = 0; i < 8; i++) begin
  t = item(); t.we = i[0]; t.addr = 32'h100 + 4 * (i / 2); t.be = 4'hF; t.wdata = t.we ? 32'hC0DE_0000 + i : 0; t.aid = i; send(t);
end
""",
    drain_ns=3000,
    model="""
module obi_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        req,
  output logic        gnt,
  input  logic [31:0] addr,
  input  logic        we,
  input  logic [3:0]  be,
  input  logic [31:0] wdata,
  input  logic [3:0]  aid,
  output logic        rvalid,
  input  logic        rready,
  output logic [31:0] rdata,
  output logic        err,
  output logic [3:0]  rid
);
  logic [31:0] mem [0:255];
  // response FIFO: {err, rid, rdata}
  logic [36:0] fifo [0:3];
  logic [1:0]  wp, rp;
  logic [2:0]  cnt;
  logic [7:0]  lfsr;
  logic        stall, push, pop;

  assign stall  = (lfsr[1:0] == 2'b00);              // about one clock in four
  assign gnt    = req && !stall && (cnt < 3'd4 || pop);
  assign push   = req && gnt;
  assign rvalid = (cnt != 3'd0);
  assign pop    = rvalid && rready;
  assign {err, rid, rdata} = rvalid ? fifo[rp] : 37'h0;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wp <= '0; rp <= '0; cnt <= '0;
      lfsr <= 8'hA5;
      for (int i = 0; i < 256; i++) mem[i] <= 32'h0;
      for (int i = 0; i < 4; i++) fifo[i] <= '0;
    end else begin
      lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
      if (push) begin
        if (addr >= 32'h400)
          fifo[wp] <= {1'b1, aid, 32'h0};
        else if (we) begin
          for (int b = 0; b < 4; b++)
            if (be[b]) mem[addr[9:2]][b*8 +: 8] <= wdata[b*8 +: 8];
          fifo[wp] <= {1'b0, aid, 32'h0};
        end else
          fifo[wp] <= {1'b0, aid, mem[addr[9:2]]};
        wp <= wp + 2'd1;
      end
      if (pop) rp <= rp + 2'd1;
      cnt <= cnt + {2'b0, push} - {2'b0, pop};
    end
  end
endmodule
""",
    sva="""
// no X on the subordinate outputs out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({gnt, rvalid}))
  else $error("OBI: X on gnt/rvalid");
assert property (@(posedge clk) disable iff (!rst_n) rvalid |-> !$isunknown({rdata, err, rid}))
  else $error("OBI: X on the R channel while rvalid");
// A phase: a request is not retracted and its signals are stable until granted
assert property (@(posedge clk) disable iff (!rst_n) req && !gnt |=> req)
  else $error("OBI: req retracted before gnt");
assert property (@(posedge clk) disable iff (!rst_n) req && !gnt |=> $stable({addr, we, be, wdata, aid}))
  else $error("OBI: A-phase signals changed before gnt");
// R phase: a response is held until accepted
assert property (@(posedge clk) disable iff (!rst_n) rvalid && !rready |=> rvalid && $stable({rdata, err, rid}))
  else $error("OBI: R-phase response dropped or changed before rready");
// gnt only answers a request
assert property (@(posedge clk) disable iff (!rst_n) gnt |-> req)
  else $error("OBI: gnt without req");
cover property (@(posedge clk) disable iff (!rst_n) req && !gnt ##1 req && gnt);
cover property (@(posedge clk) disable iff (!rst_n) rvalid && !rready ##1 rvalid && rready);
cover property (@(posedge clk) disable iff (!rst_n) rvalid && err);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic req = 0, we = 0, rready = 1;
logic [31:0] addr = 0, wdata = 0;
logic [3:0] be = 0, aid = 0;
wire gnt, rvalid, err;
wire [31:0] rdata;
wire [3:0] rid;

always #5 clk = ~clk;

obi_model u_dut (.clk(clk), .rst_n(rst_n), .req(req), .gnt(gnt), .addr(addr), .we(we), .be(be),
                 .wdata(wdata), .aid(aid), .rvalid(rvalid), .rready(rready), .rdata(rdata),
                 .err(err), .rid(rid));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// one transfer: A phase until gnt, then wait for the response
task automatic xfer(input logic w, input logic [31:0] a, input logic [3:0] b, input logic [31:0] d,
                    input logic [3:0] id, output logic [31:0] q, output logic e);
  int n;
  @(negedge clk);
  req = 1; we = w; addr = a; be = b; wdata = d; aid = id;
  n = 0;
  while (!gnt && n < 50) begin @(negedge clk); n++; end
  chk(gnt === 1'b1, "request granted");
  @(negedge clk);
  req = 0;
  n = 0;
  while (!rvalid && n < 50) begin @(negedge clk); n++; end
  chk(rvalid === 1'b1, "response returned");
  chk(rid === id, "rid echoes aid");
  q = rdata; e = err;
  @(posedge clk); #1;
endtask

initial begin
  logic [31:0] q; logic e;
  repeat (3) @(posedge clk);
  chk(gnt === 1'b0 && rvalid === 1'b0, "idle out of reset");
  rst_n = 1;
  repeat (2) @(posedge clk);

  xfer(0, 32'h0, 4'hF, 0, 4'h7, q, e);
  chk(q === 32'h0 && e === 1'b0, "word 0 reads 0 after reset");
  xfer(0, 32'h3FC, 4'hF, 0, 4'h8, q, e);
  chk(q === 32'h0 && e === 1'b0, "last word (0x3FC) reads 0 after reset, in range");
  xfer(0, 32'h400, 4'hF, 0, 4'h9, q, e);
  chk(e === 1'b1, "0x400 is the first out-of-range address");
  xfer(1, 32'h20, 4'hF, 32'hCAFE_F00D, 4'h1, q, e);
  chk(e === 1'b0, "write in range: no error");
  xfer(0, 32'h20, 4'hF, 0, 4'h2, q, e);
  chk(q === 32'hCAFE_F00D && e === 1'b0, "read back full word");
  xfer(1, 32'h20, 4'h2, 32'h0000_AB00, 4'h3, q, e);
  xfer(0, 32'h20, 4'hF, 0, 4'h4, q, e);
  chk(q === 32'hCAFE_AB0D, "byte-enable merge on lane 1");
  xfer(1, 32'h800, 4'hF, 32'h1, 4'h5, q, e);
  chk(e === 1'b1, "write above 0x3FF: error response");
  xfer(0, 32'h800, 4'hF, 0, 4'h6, q, e);
  chk(e === 1'b1 && q === 32'h0, "read above 0x3FF: error response, rdata 0");

  // back-pressure: hold rready low, four requests fill the FIFO, the fifth waits
  begin : bp
    int granted = 0;
    @(negedge clk); rready = 0;
    req = 1; we = 0; addr = 32'h20; be = 4'hF;
    repeat (20) begin #1; if (gnt) granted++; @(negedge clk); end   // gnt half a clock before each edge
    chk(granted == 4, "four outstanding requests, then no gnt while the FIFO is full");
    chk(rvalid === 1'b1 && rdata === 32'hCAFE_AB0D, "response held while rready is low");
    rready = 1;
    repeat (10) @(negedge clk);
    req = 0;
    repeat (10) @(negedge clk);
    chk(rvalid === 1'b0, "FIFO drains when rready returns");
  end

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #200000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
