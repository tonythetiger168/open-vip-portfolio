# ACE-Lite write master (tb/top_tb.sv ace_lite_model: AW/W ready pulse one
# clock after VALID, 16 x 64-bit entries at AWADDR[6:3] with byte strobes,
# OKAY write response on B once AW and W have completed).
from _lib import wait_cb

SPEC = dict(
    vip="ACE_Lite-UVM-VIP", p="ace_lite", P="ACE-Lite", dir="ace_lite",
    defs="""
// AWBAR: 2'b00 normal access, 2'b01 memory barrier, 2'b11 synchronisation barrier
localparam bit [1:0] ACE_BAR_NORMAL = 2'b00, ACE_BAR_MEMORY = 2'b01, ACE_BAR_SYNC = 2'b11;
""",
    fields=[
        ("bit [31:0]", "awaddr", "req"),
        ("bit [1:0]", "awbar", "req"),
        ("bit [63:0]", "wdata", "req"),
        ("bit [7:0]", "wstrb", "req"),
        ("bit [1:0]", "bresp", "rsp"),
    ],
    constraints="""
constraint c_addr { awaddr[2:0] == 3'b000; awaddr < 32'h80; }
constraint c_bar  { awbar dist { ACE_BAR_NORMAL := 8, ACE_BAR_MEMORY := 1, ACE_BAR_SYNC := 1 }; }
// barrier transactions carry no data (all strobes low, address 0)
constraint c_barrier { awbar != ACE_BAR_NORMAL -> (wstrb == 8'h00 && wdata == 0 && awaddr == 0);
                       awbar == ACE_BAR_NORMAL -> wstrb != 8'h00; }
""",
    drv_desc="AW and W issued together, held until each READY, then B with BREADY",
    drv_idle="""
vif.drv_cb.awvalid <= 1'b0; vif.drv_cb.awbar <= '0; vif.drv_cb.awaddr <= '0;
vif.drv_cb.wvalid  <= 1'b0; vif.drv_cb.wdata <= '0;  vif.drv_cb.wstrb  <= '0;
vif.drv_cb.bready  <= 1'b0;
""",
    drv_item="""
bit aw_done = 0, w_done = 0;
int unsigned to = 0;
@(vif.drv_cb);
vif.drv_cb.awvalid <= 1'b1; vif.drv_cb.awaddr <= t.awaddr; vif.drv_cb.awbar <= t.awbar;
vif.drv_cb.wvalid  <= 1'b1; vif.drv_cb.wdata  <= t.wdata;  vif.drv_cb.wstrb <= t.wstrb;
vif.drv_cb.bready  <= 1'b1;
while (!(aw_done && w_done) && to < cfg.timeout_cycles) begin
  @(vif.drv_cb); to++;
  if (!aw_done && vif.drv_cb.awready === 1'b1) begin aw_done = 1; vif.drv_cb.awvalid <= 1'b0; end
  if (!w_done  && vif.drv_cb.wready  === 1'b1) begin w_done  = 1; vif.drv_cb.wvalid  <= 1'b0; end
end
if (!(aw_done && w_done)) `uvm_error("TIMEOUT", "ACE-Lite AWREADY/WREADY not seen")
""" + wait_cb("vif.drv_cb.bvalid === 1'b1", "ACE-Lite BVALID") + """
t.bresp = vif.drv_cb.bresp;
vif.drv_cb.bready <= 1'b0;
""",
    mon_desc="AW and W handshakes, completed by the B handshake",
    mon_run="""
ace_lite_transaction t;
bit have_aw = 0, have_w = 0;
forever begin
  @(vif.mon_cb);
  if (!have_aw && vif.mon_cb.awvalid && vif.mon_cb.awready) begin
    if (t == null) t = ace_lite_transaction::type_id::create("t");
    t.awaddr = vif.mon_cb.awaddr; t.awbar = vif.mon_cb.awbar; have_aw = 1;
  end
  if (!have_w && vif.mon_cb.wvalid && vif.mon_cb.wready) begin
    if (t == null) t = ace_lite_transaction::type_id::create("t");
    t.wdata = vif.mon_cb.wdata; t.wstrb = vif.mon_cb.wstrb; have_w = 1;
  end
  if (vif.mon_cb.bvalid && vif.mon_cb.bready) begin
    if (!(have_aw && have_w))
      `uvm_error("MON", "ACE-Lite B response before both AW and W handshakes")
    else begin
      t.bresp = vif.mon_cb.bresp;
      publish(t);
    end
    t = null; have_aw = 0; have_w = 0;
  end
end
""",
    sb_members="bit [63:0] mem [16];   // write-only port: kept for debug, not observable",
    predict="""
if (t.awbar == ACE_BAR_NORMAL)
  for (int i = 0; i < 8; i++) if (t.wstrb[i]) mem[t.awaddr[6:3]][i*8 +: 8] = t.wdata[i*8 +: 8];
t.bresp = 2'b00;   // OKAY
""",
    checks="""
if (t.bresp != 2'b00) fail(t, "non-OKAY write response");
if (t.awbar != ACE_BAR_NORMAL && t.wstrb != 8'h00) fail(t, "barrier transaction with write strobes");
if (t.awaddr[2:0] != 3'b000) fail(t, "AWADDR not 64-bit aligned");
""",
    coverage="""
cp_bar  : coverpoint tr.awbar { bins normal = {ACE_BAR_NORMAL}; bins mem = {ACE_BAR_MEMORY}; bins sync = {ACE_BAR_SYNC}; }
cp_strb : coverpoint tr.wstrb { bins none = {8'h00}; bins full = {8'hFF}; bins partial = default; }
cp_idx  : coverpoint tr.awaddr[6:3];
""",
    directed="""
// full-word writes to every entry, byte-lane writes, both barrier types
for (int i = 0; i < 16; i++) begin
  t = item(); t.awaddr = i * 8; t.wdata = {2{32'hC0DE_0000 | i}}; t.wstrb = 8'hFF; send(t);
end
for (int b = 0; b < 8; b++) begin
  t = item(); t.awaddr = 32'h40; t.wdata = 64'h1122_3344_5566_7788; t.wstrb = 8'h1 << b; send(t);
end
t = item(); t.awbar = ACE_BAR_MEMORY; send(t);
t = item(); t.awbar = ACE_BAR_SYNC; send(t);
t = item(); t.awaddr = 32'h78; t.wdata = '1; t.wstrb = 8'hF0; send(t);
""",
)
