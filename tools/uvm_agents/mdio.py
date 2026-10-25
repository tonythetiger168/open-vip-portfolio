# IEEE 802.3 clause 22 MDIO station management (MDC = clk / 2).
#
# tb/top_tb.sv mdio_model is a clause 22 PHY at address 5: after a preamble of
# 32 or more ones it answers a read of PHYAD 5 (any REGAD) with TA = Z, 0 and
# the 16 bits of phy_status; writes and other addresses get no response, and
# mdio_status mirrors phy_status one clock later. MDIO is sampled on MDC
# rising edges by both sides.
#
# The original interface gave the station no way to drive MDIO; it now has
# mdio_o / mdio_oe and a pull-up on mdio (a tri1 net: Verilator lets a
# (weak0, weak1) assign override the PHY's strong 0).
SPEC = dict(
    vip="MDIO-UVM-VIP", p="mdio", P="MDIO", dir="mdio",
    interface="""interface mdio_if (input logic clk);
  logic rst_n;

  logic mdc;
  logic mdio_o;          // station management entity output
  logic mdio_oe;
  tri1  mdio;            // shared, pulled up when nobody drives it
  logic [15:0] phy_status;
  logic [15:0] mdio_status;

  assign mdio = mdio_oe ? mdio_o : 1'bz;

  modport DUT (input clk, rst_n, mdc, phy_status, output mdio_status, inout mdio);
  modport DRV (input clk, rst_n, mdio_status, mdio, output mdc, mdio_o, mdio_oe, phy_status);
  modport MON (input clk, rst_n, mdc, mdio, mdio_o, mdio_oe, phy_status, mdio_status);

  clocking drv_cb @(posedge clk);
    input rst_n, mdio, mdio_status;
    inout mdc, mdio_o, mdio_oe, phy_status;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, mdc, mdio, mdio_o, mdio_oe, phy_status, mdio_status;
  endclocking
endinterface
""",
    cfg="bit [4:0] phy_addr = 5'h05;   // mdio_model PHY_ADDR",
    fields=[
        ("bit", "read", "req"),
        ("bit [4:0]", "phyad", "req"),
        ("bit [4:0]", "regad", "req"),
        ("bit [15:0]", "wdata", "req"),
        ("bit [15:0]", "phy_status", "req"),   # value on the phy_status pins during the frame
        ("bit [15:0]", "rdata", "rsp"),
        ("bit", "ta_ack", "rsp"),              # PHY drove the second turnaround bit low
        ("bit [15:0]", "mdio_status", "rsp"),
        ("bit [1:0]", "ta", "info"),           # turnaround bits as seen on the bus
    ],
    constraints="""
constraint c_data { read -> wdata == 0; }
constraint c_phy  { phyad dist { 5'h05 := 3, [0:4] :/ 1, [6:31] :/ 1 }; }
""",
    drv_members="bit sampled;   // MDIO at the last MDC rising edge",
    drv_desc="preamble, ST, OP, PHYAD, REGAD, TA, DATA; MDIO set while MDC is low",
    drv_idle="vif.drv_cb.mdc <= 1'b0; vif.drv_cb.mdio_oe <= 1'b0; vif.drv_cb.mdio_o <= 1'b1; vif.drv_cb.phy_status <= '0;",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.phy_status <= t.phy_status;
repeat (32) mdc_bit(1'b1, 1'b1);               // preamble
mdc_bit(1'b1, 1'b0); mdc_bit(1'b1, 1'b1);      // ST = 01
mdc_bit(1'b1, t.read); mdc_bit(1'b1, !t.read); // OP: 10 read, 01 write
for (int i = 4; i >= 0; i--) mdc_bit(1'b1, t.phyad[i]);
for (int i = 4; i >= 0; i--) mdc_bit(1'b1, t.regad[i]);
if (t.read) begin
  mdc_bit(1'b0, 1'b1);                         // TA: Z
  mdc_bit(1'b0, 1'b1); t.ta_ack = !sampled;    // TA: 0 from the PHY
  for (int i = 15; i >= 0; i--) begin mdc_bit(1'b0, 1'b1); t.rdata[i] = sampled; end
end else begin
  mdc_bit(1'b1, 1'b1); mdc_bit(1'b1, 1'b0);    // TA = 10
  for (int i = 15; i >= 0; i--) mdc_bit(1'b1, t.wdata[i]);
  t.ta_ack = 0;
  t.rdata = 0;
end
vif.drv_cb.mdio_oe <= 1'b0;
repeat (2) @(vif.drv_cb);
t.mdio_status = vif.drv_cb.mdio_status;
""",
    drv_tasks="""
// one MDC period: MDC low with MDIO set up, then MDC high (the PHY samples
// on the rising edge, the station samples a PHY-driven bit there too)
task mdc_bit(bit drive, bit b);
  vif.drv_cb.mdc <= 1'b0;
  vif.drv_cb.mdio_oe <= drive;
  vif.drv_cb.mdio_o <= b;
  @(vif.drv_cb);
  vif.drv_cb.mdc <= 1'b1;
  @(vif.drv_cb);
  sampled = vif.drv_cb.mdio;
endtask
""",
    mon_desc="decodes clause 22 frames from MDIO sampled on MDC rising edges",
    mon_run="""
bit [63:0] sh = 0;
int unsigned ones = 0, n = 0;
bit mdc_d = 0, in_frame = 0;
mdio_transaction t;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.mdc && !mdc_d) begin           // MDC rising edge: one bit
    bit b = (vif.mon_cb.mdio !== 1'b0);
    if (!in_frame) begin
      // ST (01) after at least 32 preamble ones
      if (ones >= 32 && b == 1'b0) begin in_frame = 1; n = 1; sh = 0; end
      ones = b ? ones + 1 : 0;
    end else begin
      sh = {sh[62:0], b};
      n++;
      if (n == 32) begin                        // ST OP PHYAD REGAD TA DATA
        t = mdio_transaction::type_id::create("t");
        if (sh[30] != 1'b1) `uvm_error("MON", "MDIO start code is not 01")
        t.read  = (sh[29:28] == 2'b10);
        if (sh[29:28] != 2'b10 && sh[29:28] != 2'b01) `uvm_error("MON", "MDIO OP code is not read/write")
        t.phyad = sh[27:23];
        t.regad = sh[22:18];
        t.ta    = sh[17:16];
        t.ta_ack = t.read && (sh[16] == 1'b0);
        if (t.read) t.rdata = sh[15:0]; else t.wdata = sh[15:0];
        t.phy_status = vif.mon_cb.phy_status;
        in_frame = 0; ones = 0;
        repeat (3) @(vif.mon_cb);
        t.mdio_status = vif.mon_cb.mdio_status;
        publish(t);
      end
    end
  end
  mdc_d = vif.mon_cb.mdc;
end
""",
    predict="""
// the PHY at address 5 answers reads with phy_status; any other read sees
// the pulled-up bus and no turnaround zero
t.ta_ack = t.read && t.phyad == cfg.phy_addr;
t.rdata  = t.ta_ack ? t.phy_status : (t.read ? 16'hFFFF : 16'h0);
t.mdio_status = t.phy_status;      // registered mirror
""",
    checks="""
if (!t.read && t.ta != 2'b10) fail(t, "write frame turnaround is not 10");
if (t.read && t.ta_ack && t.ta != 2'b10) fail(t, "read turnaround is not Z, 0");
""",
    coverage="""
cp_op  : coverpoint tr.read { bins write = {0}; bins read = {1}; }
cp_reg : coverpoint tr.regad { bins bmcr = {0}; bins bmsr = {1}; bins id = {[2:3]}; bins other = default; }
cp_phy : coverpoint tr.phyad { bins five = {5}; bins other = default; }
""",
    directed="""
t = item(); t.read = 0; t.phyad = 5; t.regad = 0; t.wdata = 16'h1200; t.phy_status = 16'h7849; send(t);
t = item(); t.read = 1; t.phyad = 5; t.regad = 1; t.phy_status = 16'h796D; send(t);
t = item(); t.read = 1; t.phyad = 5; t.regad = 2; t.phy_status = 16'hFFFF; send(t);
t = item(); t.read = 0; t.phyad = 0; t.regad = 31; t.wdata = 16'hFFFF; t.phy_status = 16'h0; send(t);
t = item(); t.read = 1; t.phyad = 31; t.regad = 3; t.phy_status = 16'hABCD; send(t);
""",
)
