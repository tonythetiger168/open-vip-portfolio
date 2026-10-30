# AMBA AXI4-Lite manager agent (ARM IHI 0022, AXI4-Lite chapter).
# tb/top_tb.sv axi4_lite_model: subordinate with 256 x 32-bit words at
# addr[9:2] (0x000-0x3FF); writes to 0x3C0-0x3FF need AWPROT[0] = 1
# (privileged), otherwise SLVERR and no write; 0x400-0x7FF answer SLVERR,
# 0x800 and above DECERR (reads return 0). AWREADY / WREADY / ARREADY come
# from an LFSR, AW and W are accepted in either order and the write is done
# once both are in; one write and one read outstanding (AWREADY / WREADY
# stay low while B is pending, ARREADY while R is pending).
# The driver issues AW and W in the order and with the skew of the item;
# a background process drives BREADY / RREADY with random back-pressure;
# the monitor pairs AW + W with B and AR with R.

SPEC = dict(
    vip="AXI4_Lite-UVM-VIP", p="axi4_lite", P="AXI4-Lite", dir="axi4_lite", family="AMBA",
    desc="AMBA AXI4-Lite manager VIP: five independent channels (AW/W/B, AR/R), AW and W in "
         "either order with skew, byte strobes, AxPROT, OKAY / SLVERR / DECERR responses, "
         "random READY and BREADY / RREADY back-pressure.",
    about="""
AXI4-Lite is the register-access subset of AXI4 (single 32-bit beats, no IDs,
no bursts, no exclusive access) used by most peripheral and control ports.
The DUT model is a memory subordinate with a privileged region and two error
regions; the scoreboard keeps its own copy of the memory and predicts every
response. The SVA checker holds the AXI handshake rules on all five channels
(VALID held and payload stable until READY, no response before its request,
no EXOKAY on AXI4-Lite, VALID low in reset).""",
    timeout=200,
    ports=[
        ("in", "logic", "awvalid"), ("out", "logic", "awready"),
        ("in", "logic [31:0]", "awaddr"), ("in", "logic [2:0]", "awprot"),
        ("in", "logic", "wvalid"), ("out", "logic", "wready"),
        ("in", "logic [31:0]", "wdata"), ("in", "logic [3:0]", "wstrb"),
        ("out", "logic", "bvalid"), ("in", "logic", "bready"), ("out", "logic [1:0]", "bresp"),
        ("in", "logic", "arvalid"), ("out", "logic", "arready"),
        ("in", "logic [31:0]", "araddr"), ("in", "logic [2:0]", "arprot"),
        ("out", "logic", "rvalid"), ("in", "logic", "rready"),
        ("out", "logic [31:0]", "rdata"), ("out", "logic [1:0]", "rresp"),
    ],
    defs="""
localparam bit [1:0] AXIL_OKAY = 2'b00, AXIL_EXOKAY = 2'b01, AXIL_SLVERR = 2'b10, AXIL_DECERR = 2'b11;
""",
    cfg="int unsigned ready_pct = 70;   // percent of clocks BREADY / RREADY are high",
    fields=[
        ("bit", "we", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [2:0]", "prot", "req"),
        ("bit [31:0]", "wdata", "req"),
        ("bit [3:0]", "wstrb", "req"),
        ("bit [31:0]", "rdata", "rsp"),
        ("bit [1:0]", "resp", "rsp"),
        ("bit [2:0]", "gap", "info", "rand"),          # idle clocks before the transfer
        ("bit [1:0]", "order", "info", "rand"),        # 0 AW+W together, 1 AW first, 2 W first
        ("bit [1:0]", "skew", "info", "rand"),         # clocks between the two
        ("bit [1:0]", "region", "info", "rand"),       # 0 memory, 1 privileged, 2 SLVERR, 3 DECERR
    ],
    constraints="""
// the region is chosen first (a dist over address ranges would make
// the simulator pick a value before the alignment)
constraint c_region { region dist { 0 := 6, 1 := 2, 2 := 1, 3 := 1 }; }
constraint c_addr   { addr[1:0] == 2'b00; addr[31:12] == 0;
                      region == 0 -> addr < 32'h3C0;
                      region == 1 -> addr inside {[32'h3C0:32'h3FC]};
                      region == 2 -> addr inside {[32'h400:32'h7FC]};
                      region == 3 -> addr >= 32'h800; }
constraint c_wr     { we -> wstrb != 4'h0; !we -> (wstrb == 4'h0 && wdata == 0); }
constraint c_order  { order != 2'd3; !we -> (order == 0 && skew == 0); }
constraint c_gap    { gap dist { 0 := 6, [1:7] :/ 2 }; }
""",
    drv_desc="AW and W in the item's order and skew, each held until READY, then B; AR then R",
    drv_idle="""
vif.drv_cb.awvalid <= 1'b0; vif.drv_cb.awaddr <= '0; vif.drv_cb.awprot <= '0;
vif.drv_cb.wvalid  <= 1'b0; vif.drv_cb.wdata  <= '0; vif.drv_cb.wstrb  <= '0;
vif.drv_cb.arvalid <= 1'b0; vif.drv_cb.araddr <= '0; vif.drv_cb.arprot <= '0;
vif.drv_cb.bready  <= 1'b0; vif.drv_cb.rready <= 1'b0;
""",
    drv_bg="""
forever begin
  @(vif.drv_cb);
  vif.drv_cb.bready <= ($urandom_range(99) < cfg.ready_pct);
  vif.drv_cb.rready <= ($urandom_range(99) < cfg.ready_pct);
end
""",
    drv_item="""
repeat (t.gap) @(vif.drv_cb);
if (t.we) begin
  bit aw_on = 0, w_on = 0, aw_done = 0, w_done = 0;
  int unsigned to = 0;
  // AW first (order 1), W first (order 2) or both together; the other
  // channel follows skew clocks later
  if (t.order != 2) begin
    vif.drv_cb.awvalid <= 1'b1; vif.drv_cb.awaddr <= t.addr; vif.drv_cb.awprot <= t.prot; aw_on = 1;
  end
  if (t.order != 1) begin
    vif.drv_cb.wvalid <= 1'b1; vif.drv_cb.wdata <= t.wdata; vif.drv_cb.wstrb <= t.wstrb; w_on = 1;
  end
  while (!(aw_done && w_done) && to < cfg.timeout_cycles) begin
    @(vif.drv_cb); to++;
    if (aw_on && vif.drv_cb.awready === 1'b1) begin aw_on = 0; aw_done = 1; vif.drv_cb.awvalid <= 1'b0; end
    if (w_on  && vif.drv_cb.wready  === 1'b1) begin w_on  = 0; w_done  = 1; vif.drv_cb.wvalid  <= 1'b0; end
    if (!aw_on && !aw_done && to >= t.skew) begin
      vif.drv_cb.awvalid <= 1'b1; vif.drv_cb.awaddr <= t.addr; vif.drv_cb.awprot <= t.prot; aw_on = 1;
    end
    if (!w_on && !w_done && to >= t.skew) begin
      vif.drv_cb.wvalid <= 1'b1; vif.drv_cb.wdata <= t.wdata; vif.drv_cb.wstrb <= t.wstrb; w_on = 1;
    end
  end
  if (!(aw_done && w_done)) `uvm_error("TIMEOUT", "AXI4-Lite: AWREADY / WREADY not seen")
""" + """  begin
    int unsigned tb = 0;
    do begin @(vif.drv_cb); tb++; end
    while (!(vif.drv_cb.bvalid === 1'b1 && vif.drv_cb.bready === 1'b1) && tb < cfg.timeout_cycles);
    if (vif.drv_cb.bvalid !== 1'b1) `uvm_error("TIMEOUT", "AXI4-Lite: no B response")
    t.resp = vif.drv_cb.bresp;
    t.rdata = 32'h0;
  end
end else begin
  int unsigned to = 0;
  vif.drv_cb.arvalid <= 1'b1; vif.drv_cb.araddr <= t.addr; vif.drv_cb.arprot <= t.prot;
  do begin @(vif.drv_cb); to++; end while (vif.drv_cb.arready !== 1'b1 && to < cfg.timeout_cycles);
  if (vif.drv_cb.arready !== 1'b1) `uvm_error("TIMEOUT", "AXI4-Lite: no ARREADY")
  vif.drv_cb.arvalid <= 1'b0;
  to = 0;
  do begin @(vif.drv_cb); to++; end
  while (!(vif.drv_cb.rvalid === 1'b1 && vif.drv_cb.rready === 1'b1) && to < cfg.timeout_cycles);
  if (vif.drv_cb.rvalid !== 1'b1) `uvm_error("TIMEOUT", "AXI4-Lite: no R response")
  t.rdata = vif.drv_cb.rdata;
  t.resp  = vif.drv_cb.rresp;
end
""",
    mon_desc="AW and W handshakes queued separately and completed by B; AR completed by R",
    mon_members="bit [34:0] aw_q[$];   // {awprot, awaddr}\nbit [35:0] w_q[$];    // {wstrb, wdata}\nbit [34:0] ar_q[$];",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.awvalid && vif.mon_cb.awready) aw_q.push_back({vif.mon_cb.awprot, vif.mon_cb.awaddr});
  if (vif.mon_cb.wvalid  && vif.mon_cb.wready)  w_q.push_back({vif.mon_cb.wstrb, vif.mon_cb.wdata});
  if (vif.mon_cb.arvalid && vif.mon_cb.arready) ar_q.push_back({vif.mon_cb.arprot, vif.mon_cb.araddr});
  if (vif.mon_cb.bvalid && vif.mon_cb.bready) begin
    if (aw_q.size() == 0 || w_q.size() == 0)
      `uvm_error("MON", "AXI4-Lite: B response before both AW and W handshakes")
    else begin
      axi4_lite_transaction t = axi4_lite_transaction::type_id::create("t");
      bit [34:0] a = aw_q.pop_front();
      bit [35:0] w = w_q.pop_front();
      t.we = 1; {t.prot, t.addr} = a; {t.wstrb, t.wdata} = w;
      t.resp = vif.mon_cb.bresp; t.rdata = 32'h0;
      publish(t);
    end
  end
  if (vif.mon_cb.rvalid && vif.mon_cb.rready) begin
    if (ar_q.size() == 0)
      `uvm_error("MON", "AXI4-Lite: R response without an AR handshake")
    else begin
      axi4_lite_transaction t = axi4_lite_transaction::type_id::create("t");
      bit [34:0] a = ar_q.pop_front();
      t.we = 0; {t.prot, t.addr} = a; t.wstrb = 0; t.wdata = 0;
      t.rdata = vif.mon_cb.rdata; t.resp = vif.mon_cb.rresp;
      publish(t);
    end
  end
end
""",
    sb_members="bit [31:0] mem [256];   // reset value 0",
    predict="""
t.rdata = 32'h0;
if (t.addr >= 32'h800)      t.resp = AXIL_DECERR;
else if (t.addr >= 32'h400) t.resp = AXIL_SLVERR;
else if (t.we && t.addr >= 32'h3C0 && !t.prot[0]) t.resp = AXIL_SLVERR;
else begin
  t.resp = AXIL_OKAY;
  if (t.we) begin
    for (int b = 0; b < 4; b++)
      if (t.wstrb[b]) mem[t.addr[9:2]][b*8 +: 8] = t.wdata[b*8 +: 8];
  end else
    t.rdata = mem[t.addr[9:2]];
end
""",
    checks="""
if (t.resp == AXIL_EXOKAY) fail(t, "EXOKAY response on AXI4-Lite (no exclusive access)");
if (t.resp != AXIL_OKAY && t.rdata != 0) fail(t, "error response with read data");
if (!t.we && t.wstrb != 0) fail(t, "read decoded with write strobes");
""",
    coverage="""
cp_we     : coverpoint tr.we;
cp_resp   : coverpoint tr.resp { bins okay = {AXIL_OKAY}; bins slverr = {AXIL_SLVERR}; bins decerr = {AXIL_DECERR};
                                 illegal_bins exokay = {AXIL_EXOKAY}; }
cp_strb   : coverpoint tr.wstrb iff (tr.we) { bins full = {4'hF}; bins byte_[] = {4'h1, 4'h2, 4'h4, 4'h8};
                                              bins half[] = {4'h3, 4'hC}; bins other = default; }
cp_priv   : coverpoint tr.prot[0];
cp_region : coverpoint tr.addr[11:6] { bins mem = {[0:14]}; bins priv = {15}; bins slverr = {[16:31]}; bins decerr = {[32:63]}; }
x_we_resp : cross cp_we, cp_resp;
x_priv    : cross cp_we, cp_priv, cp_region;
""",
    directed="""
// AW and W together, AW first, W first, with and without skew
for (int i = 0; i < 6; i++) begin
  t = item(); t.we = 1; t.addr = 32'h40 + 4 * i; t.wdata = 32'hA000_0000 | i; t.wstrb = 4'hF;
  t.order = i % 3; t.skew = i / 3 * 3; send(t);
end
for (int i = 0; i < 6; i++) begin t = item(); t.addr = 32'h40 + 4 * i; send(t); end
// byte lanes, half words
for (int b = 0; b < 4; b++) begin
  t = item(); t.we = 1; t.addr = 32'h80; t.wdata = 32'h1122_3344; t.wstrb = 4'h1 << b; t.order = b % 3; send(t);
end
t = item(); t.we = 1; t.addr = 32'h84; t.wdata = 32'hFFFF_FFFF; t.wstrb = 4'h3; send(t);
t = item(); t.we = 1; t.addr = 32'h84; t.wdata = 32'h5555_AAAA; t.wstrb = 4'hC; send(t);
t = item(); t.addr = 32'h80; send(t);
t = item(); t.addr = 32'h84; send(t);
// privileged region: unprivileged write refused, privileged write done
t = item(); t.we = 1; t.addr = 32'h3C0; t.wdata = 32'h1111_1111; t.wstrb = 4'hF; t.prot = 3'b000; send(t);
t = item(); t.addr = 32'h3C0; send(t);
t = item(); t.we = 1; t.addr = 32'h3FC; t.wdata = 32'h2222_2222; t.wstrb = 4'hF; t.prot = 3'b001; send(t);
t = item(); t.addr = 32'h3FC; t.prot = 3'b010; send(t);
t = item(); t.we = 1; t.addr = 32'h3BC; t.wdata = 32'h3333_3333; t.wstrb = 4'hF; t.prot = 3'b110; send(t);
t = item(); t.addr = 32'h3BC; send(t);
// error regions: no write lands, reads return 0
t = item(); t.we = 1; t.addr = 32'h400; t.wdata = 32'hDEAD_BEEF; t.wstrb = 4'hF; t.prot = 3'b001; send(t);
t = item(); t.addr = 32'h7FC; send(t);
t = item(); t.we = 1; t.addr = 32'h800; t.wdata = 32'hDEAD_BEEF; t.wstrb = 4'hF; t.order = 2; send(t);
t = item(); t.addr = 32'hFFC; send(t);
t = item(); t.addr = 32'h0; send(t);
// back to back, no gaps
for (int i = 0; i < 8; i++) begin
  t = item(); t.we = !i[0]; t.addr = 32'h100 + 4 * (i / 2); t.wstrb = t.we ? 4'hF : 4'h0;
  t.wdata = t.we ? 32'hC0DE_0000 + i : 0; send(t);
end
""",
    drain_ns=3000,
    model="""
module axi4_lite_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        awvalid,
  output logic        awready,
  input  logic [31:0] awaddr,
  input  logic [2:0]  awprot,
  input  logic        wvalid,
  output logic        wready,
  input  logic [31:0] wdata,
  input  logic [3:0]  wstrb,
  output logic        bvalid,
  input  logic        bready,
  output logic [1:0]  bresp,
  input  logic        arvalid,
  output logic        arready,
  input  logic [31:0] araddr,
  input  logic [2:0]  arprot,
  output logic        rvalid,
  input  logic        rready,
  output logic [31:0] rdata,
  output logic [1:0]  rresp
);
  logic [31:0] mem [0:255];
  logic        aw_full, w_full;
  logic [31:0] aw_a, w_d;
  logic [2:0]  aw_p;
  logic [3:0]  w_s;
  logic [7:0]  lfsr;
  logic [1:0]  wr_resp, rd_resp;

  // READY from the LFSR; no new write while B is pending, no read while R is
  assign awready = !aw_full && !bvalid && lfsr[0];
  assign wready  = !w_full  && !bvalid && lfsr[2];
  assign arready = !rvalid && lfsr[4];

  assign wr_resp = (aw_a >= 32'h800) ? 2'b11 :
                   (aw_a >= 32'h400) ? 2'b10 :
                   (aw_a >= 32'h3C0 && !aw_p[0]) ? 2'b10 : 2'b00;
  assign rd_resp = (araddr >= 32'h800) ? 2'b11 : (araddr >= 32'h400) ? 2'b10 : 2'b00;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      aw_full <= 1'b0; w_full <= 1'b0; aw_a <= '0; aw_p <= '0; w_d <= '0; w_s <= '0;
      bvalid <= 1'b0; bresp <= 2'b00; rvalid <= 1'b0; rdata <= '0; rresp <= 2'b00;
      lfsr <= 8'h5B;
      for (int i = 0; i < 256; i++) mem[i] <= 32'h0;
    end else begin
      lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};
      if (awvalid && awready) begin aw_full <= 1'b1; aw_a <= awaddr; aw_p <= awprot; end
      if (wvalid && wready) begin w_full <= 1'b1; w_d <= wdata; w_s <= wstrb; end
      // the write is done once both AW and W are in
      if (aw_full && w_full && !bvalid) begin
        if (wr_resp == 2'b00)
          for (int b = 0; b < 4; b++)
            if (w_s[b]) mem[aw_a[9:2]][b*8 +: 8] <= w_d[b*8 +: 8];
        bvalid <= 1'b1; bresp <= wr_resp;
        aw_full <= 1'b0; w_full <= 1'b0;
      end
      if (bvalid && bready) bvalid <= 1'b0;
      if (arvalid && arready) begin
        rvalid <= 1'b1; rresp <= rd_resp;
        rdata <= (rd_resp == 2'b00) ? mem[araddr[9:2]] : 32'h0;
      end
      if (rvalid && rready) rvalid <= 1'b0;
    end
  end
endmodule
""",
    sva="""
// outstanding counts: a response only answers an accepted request
int unsigned n_aw = 0, n_w = 0, n_b = 0, n_ar = 0, n_r = 0;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin n_aw <= 0; n_w <= 0; n_b <= 0; n_ar <= 0; n_r <= 0; end
  else begin
    if (awvalid && awready) n_aw <= n_aw + 1;
    if (wvalid && wready)   n_w  <= n_w + 1;
    if (bvalid && bready)   n_b  <= n_b + 1;
    if (arvalid && arready) n_ar <= n_ar + 1;
    if (rvalid && rready)   n_r  <= n_r + 1;
  end
// subordinate VALID low in reset, no X out of reset
assert property (@(posedge clk) !rst_n |-> !bvalid && !rvalid)
  else $error("AXI4-Lite: BVALID / RVALID high in reset");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({awready, wready, arready, bvalid, rvalid}))
  else $error("AXI4-Lite: X on READY / VALID");
assert property (@(posedge clk) disable iff (!rst_n) bvalid |-> !$isunknown(bresp))
  else $error("AXI4-Lite: X on BRESP");
assert property (@(posedge clk) disable iff (!rst_n) rvalid |-> !$isunknown({rdata, rresp}))
  else $error("AXI4-Lite: X on the R channel");
// VALID held and payload stable until READY, on every channel
assert property (@(posedge clk) disable iff (!rst_n) awvalid && !awready |=> awvalid && $stable({awaddr, awprot}))
  else $error("AXI4-Lite: AW changed before AWREADY");
assert property (@(posedge clk) disable iff (!rst_n) wvalid && !wready |=> wvalid && $stable({wdata, wstrb}))
  else $error("AXI4-Lite: W changed before WREADY");
assert property (@(posedge clk) disable iff (!rst_n) arvalid && !arready |=> arvalid && $stable({araddr, arprot}))
  else $error("AXI4-Lite: AR changed before ARREADY");
assert property (@(posedge clk) disable iff (!rst_n) bvalid && !bready |=> bvalid && $stable(bresp))
  else $error("AXI4-Lite: B changed before BREADY");
assert property (@(posedge clk) disable iff (!rst_n) rvalid && !rready |=> rvalid && $stable({rdata, rresp}))
  else $error("AXI4-Lite: R changed before RREADY");
// a write response needs both the address and the data accepted
assert property (@(posedge clk) disable iff (!rst_n) bvalid |-> n_aw > n_b && n_w > n_b)
  else $error("AXI4-Lite: BVALID before AW and W were both accepted");
assert property (@(posedge clk) disable iff (!rst_n) rvalid |-> n_ar > n_r)
  else $error("AXI4-Lite: RVALID without an accepted AR");
assert property (@(posedge clk) disable iff (!rst_n) (bvalid |-> bresp != 2'b01) and (rvalid |-> rresp != 2'b01))
  else $error("AXI4-Lite: EXOKAY response");
cover property (@(posedge clk) disable iff (!rst_n) wvalid && wready && !awvalid && n_aw == n_b);
cover property (@(posedge clk) disable iff (!rst_n) awvalid && !awready ##1 awvalid && awready);
cover property (@(posedge clk) disable iff (!rst_n) bvalid && !bready ##1 bvalid && bready);
cover property (@(posedge clk) disable iff (!rst_n) rvalid && rresp == 2'b11);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic awvalid = 0, wvalid = 0, arvalid = 0, bready = 1, rready = 1;
logic [31:0] awaddr = 0, wdata = 0, araddr = 0;
logic [2:0] awprot = 0, arprot = 0;
logic [3:0] wstrb = 0;
wire awready, wready, arready, bvalid, rvalid;
wire [1:0] bresp, rresp;
wire [31:0] rdata;

always #5 clk = ~clk;

axi4_lite_model u_dut (.clk(clk), .rst_n(rst_n), .awvalid(awvalid), .awready(awready), .awaddr(awaddr),
                       .awprot(awprot), .wvalid(wvalid), .wready(wready), .wdata(wdata), .wstrb(wstrb),
                       .bvalid(bvalid), .bready(bready), .bresp(bresp), .arvalid(arvalid),
                       .arready(arready), .araddr(araddr), .arprot(arprot), .rvalid(rvalid),
                       .rready(rready), .rdata(rdata), .rresp(rresp));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// write: order 0 AW + W together, 1 AW first (W after skew clocks), 2 W first
task automatic wr(input logic [31:0] a, input logic [31:0] d, input logic [3:0] s, input logic [2:0] p,
                  input int order, input int skew, output logic [1:0] r);
  int n;
  bit aw_done, w_done;
  aw_done = 0; w_done = 0;
  @(negedge clk);
  if (order != 2) begin awvalid = 1; awaddr = a; awprot = p; end
  if (order != 1) begin wvalid = 1; wdata = d; wstrb = s; end
  n = 0;
  while (!(aw_done && w_done) && n < 100) begin
    @(posedge clk);
    if (awvalid && awready) aw_done = 1;
    if (wvalid && wready) w_done = 1;
    @(negedge clk); n++;
    if (aw_done) awvalid = 0;
    if (w_done) wvalid = 0;
    if (!aw_done && !awvalid && n >= skew) begin awvalid = 1; awaddr = a; awprot = p; end
    if (!w_done && !wvalid && n >= skew) begin wvalid = 1; wdata = d; wstrb = s; end
  end
  chk(aw_done && w_done, "AW and W accepted");
  n = 0;
  while (!bvalid && n < 50) begin @(negedge clk); n++; end
  chk(bvalid === 1'b1, "B response returned");
  r = bresp;
  @(posedge clk); #1;
endtask

task automatic rd(input logic [31:0] a, input logic [2:0] p, output logic [31:0] q, output logic [1:0] r);
  int n;
  @(negedge clk);
  arvalid = 1; araddr = a; arprot = p;
  n = 0;
  while (!arready && n < 50) begin @(negedge clk); n++; end
  chk(arready === 1'b1, "AR accepted");
  @(negedge clk);
  arvalid = 0;
  n = 0;
  while (!rvalid && n < 50) begin @(negedge clk); n++; end
  chk(rvalid === 1'b1, "R response returned");
  q = rdata; r = rresp;
  @(posedge clk); #1;
endtask

initial begin
  logic [31:0] q; logic [1:0] r;
  repeat (3) @(posedge clk);
  chk(bvalid === 1'b0 && rvalid === 1'b0, "BVALID / RVALID low in reset");
  rst_n = 1;
  repeat (2) @(posedge clk);
  begin : idle
    int spur = 0;
    repeat (20) begin @(negedge clk); if (bvalid || rvalid) spur++; end
    chk(spur == 0, "no response while the bus is idle (READY high without VALID)");
  end

  rd(32'h0, 3'b000, q, r);
  chk(q === 32'h0 && r === 2'b00, "word 0 reads 0 after reset, OKAY");
  rd(32'h3FC, 3'b000, q, r);
  chk(q === 32'h0 && r === 2'b00, "0x3FC: last word, OKAY");
  rd(32'h400, 3'b000, q, r);
  chk(r === 2'b10 && q === 32'h0, "0x400: first SLVERR address, rdata 0");
  rd(32'h7FC, 3'b000, q, r);
  chk(r === 2'b10, "0x7FC: last SLVERR address");
  rd(32'h800, 3'b000, q, r);
  chk(r === 2'b11 && q === 32'h0, "0x800: DECERR, rdata 0");

  // AW + W in each order
  wr(32'h20, 32'hCAFE_F00D, 4'hF, 3'b000, 0, 0, r);
  chk(r === 2'b00, "write AW + W together: OKAY");
  rd(32'h20, 3'b000, q, r);
  chk(q === 32'hCAFE_F00D, "read back full word");
  wr(32'h24, 32'h1234_5678, 4'hF, 3'b000, 1, 3, r);
  rd(32'h24, 3'b000, q, r);
  chk(q === 32'h1234_5678 && r === 2'b00, "AW first, W 3 clocks later");
  wr(32'h28, 32'h8765_4321, 4'hF, 3'b000, 2, 3, r);
  rd(32'h28, 3'b000, q, r);
  chk(q === 32'h8765_4321 && r === 2'b00, "W first, AW 3 clocks later");
  wr(32'h20, 32'h0000_AB00, 4'h2, 3'b000, 0, 0, r);
  rd(32'h20, 3'b000, q, r);
  chk(q === 32'hCAFE_AB0D, "byte strobe merge on lane 1");
  wr(32'h20, 32'h7700_0000, 4'h8, 3'b000, 0, 0, r);
  wr(32'h20, 32'h0000_0011, 4'h1, 3'b000, 2, 1, r);
  rd(32'h20, 3'b000, q, r);
  chk(q === 32'h77FE_AB11, "byte strobe merge on lanes 3 and 0");
  wr(32'h2C, 32'hFFFF_FFFF, 4'h0, 3'b000, 0, 0, r);
  rd(32'h2C, 3'b000, q, r);
  chk(q === 32'h0 && r === 2'b00, "write with no strobe: OKAY, nothing written");

  // privileged region 0x3C0-0x3FF
  wr(32'h3C0, 32'h1111_1111, 4'hF, 3'b000, 0, 0, r);
  chk(r === 2'b10, "unprivileged write to 0x3C0: SLVERR");
  rd(32'h3C0, 3'b000, q, r);
  chk(q === 32'h0 && r === 2'b00, "unprivileged write did not land; reads are not restricted");
  wr(32'h3C0, 32'h2222_2222, 4'hF, 3'b001, 0, 0, r);
  chk(r === 2'b00, "privileged write to 0x3C0: OKAY");
  rd(32'h3C0, 3'b000, q, r);
  chk(q === 32'h2222_2222, "privileged write landed");
  wr(32'h3BC, 32'h3333_3333, 4'hF, 3'b110, 0, 0, r);
  rd(32'h3BC, 3'b000, q, r);
  chk(r === 2'b00 && q === 32'h3333_3333, "0x3BC is below the privileged region");
  wr(32'h3FC, 32'h4444_4444, 4'hF, 3'b110, 0, 0, r);
  chk(r === 2'b10, "0x3FC is in the privileged region (AWPROT[0] = 0, others set)");

  // error regions: no write lands anywhere
  wr(32'h400, 32'hDEAD_BEEF, 4'hF, 3'b001, 0, 0, r);
  chk(r === 2'b10, "write to 0x400: SLVERR");
  wr(32'h800, 32'hDEAD_BEEF, 4'hF, 3'b001, 1, 1, r);
  chk(r === 2'b11, "write to 0x800: DECERR");
  wr(32'h7FC, 32'hDEAD_BEEF, 4'hF, 3'b001, 0, 0, r);
  chk(r === 2'b10, "write to 0x7FC: SLVERR");
  rd(32'h0, 3'b000, q, r);
  chk(q === 32'h0, "error writes did not alias onto word 0");
  rd(32'h3FC, 3'b000, q, r);
  chk(q === 32'h0, "error writes did not alias onto word 0xFF");

  // B held under back-pressure, no new AW / W while it is pending
  begin : bp
    int acc = 0, accw = 0, held = 0;
    @(negedge clk); bready = 0;
    awvalid = 1; awaddr = 32'h30; awprot = 0; wvalid = 1; wdata = 32'h5A5A_5A5A; wstrb = 4'hF;
    repeat (24) begin
      @(posedge clk);
      if (awvalid && awready) acc++;
      if (wvalid && wready) accw++;
      if (bvalid && bresp === 2'b00) held++;
      @(negedge clk);
      if (acc > 0) awvalid = 0;
      if (accw > 0) wvalid = 0;
    end
    chk(acc == 1 && accw == 1, "one AW and one W accepted");
    chk(awready === 1'b0 && wready === 1'b0, "AWREADY / WREADY low while B is pending");
    chk(held >= 8 && bvalid === 1'b1, "B held while BREADY is low");
    bready = 1;
    @(negedge clk);
    @(negedge clk);
    chk(bvalid === 1'b0, "B dropped after BREADY");
  end

  // one AW (or W) held at a time: a second AW offered while the first waits
  // for its W is not accepted until the write is done (same for W first)
  begin : one_aw
    int naw = 0, nw = 0;
    @(negedge clk);
    awvalid = 1; awaddr = 32'h50; awprot = 0;
    repeat (12) begin
      @(posedge clk);
      if (awvalid && awready) naw++;
      @(negedge clk);
      if (naw == 1) awaddr = 32'h54;               // the next AW, pipelined
    end
    chk(naw == 1, "second AW not accepted while the first waits for W");
    wvalid = 1; wdata = 32'h0000_5050; wstrb = 4'hF;
    repeat (12) begin
      @(posedge clk);
      if (awvalid && awready) naw++;
      if (wvalid && wready) nw++;
      @(negedge clk);
      if (naw == 2) awvalid = 0;
      if (nw == 1) wdata = 32'h0000_5454;
      if (nw == 2) wvalid = 0;
    end
    chk(naw == 2 && nw == 2, "both writes completed in order");
    awvalid = 0; wvalid = 0;
    repeat (4) @(negedge clk);
    rd(32'h50, 3'b000, q, r);
    chk(q === 32'h0000_5050, "first AW took the first W");
    rd(32'h54, 3'b000, q, r);
    chk(q === 32'h0000_5454, "second AW took the second W");
    // W first: a second W waits for the first write
    @(negedge clk);
    wvalid = 1; wdata = 32'h0000_6060; wstrb = 4'hF; nw = 0; naw = 0;
    repeat (12) begin
      @(posedge clk);
      if (wvalid && wready) nw++;
      @(negedge clk);
      if (nw == 1) wdata = 32'h0000_6464;
    end
    chk(nw == 1, "second W not accepted while the first waits for AW");
    awvalid = 1; awaddr = 32'h60;
    repeat (12) begin
      @(posedge clk);
      if (awvalid && awready) naw++;
      if (wvalid && wready) nw++;
      @(negedge clk);
      if (naw == 1) awaddr = 32'h64;
      if (naw == 2) awvalid = 0;
      if (nw == 2) wvalid = 0;
    end
    awvalid = 0; wvalid = 0;
    repeat (4) @(negedge clk);
    rd(32'h60, 3'b000, q, r);
    chk(q === 32'h0000_6060, "W-first: first W to the first AW");
    rd(32'h64, 3'b000, q, r);
    chk(q === 32'h0000_6464, "W-first: second W to the second AW");
  end

  // R held under back-pressure, no new AR while it is pending
  begin : rbp
    int acc = 0;
    @(negedge clk); rready = 0;
    arvalid = 1; araddr = 32'h30;
    repeat (12) begin
      @(posedge clk);
      if (arvalid && arready) acc++;
      @(negedge clk);
    end
    chk(acc == 1, "one AR accepted while R is pending");
    chk(rvalid === 1'b1 && rdata === 32'h5A5A_5A5A, "R held while RREADY is low");
    arvalid = 0; rready = 1;
    repeat (2) @(negedge clk);
    chk(rvalid === 1'b0, "R dropped after RREADY");
  end

  // the whole array is addressable
  begin : fill
    int bad = 0;
    for (int i = 0; i < 256; i += 17) wr(i * 4, 32'h0BAD_0000 + i, 4'hF, 3'b001, i % 3, i % 4, r);
    for (int i = 0; i < 256; i += 17) begin rd(i * 4, 3'b000, q, r); if (q !== 32'h0BAD_0000 + i) bad++; end
    chk(bad == 0, "every 17th word written and read back");
  end

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
