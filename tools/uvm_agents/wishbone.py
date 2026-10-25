# Wishbone B4 classic-cycle master agent (tb/top_tb.sv wishbone_model:
# 16 x 32-bit registers at ADR[5:2], registered ACK one clock after CYC&STB,
# DAT_O = read data, or the write data echoed on a write).
from _lib import wait_cb

SPEC = dict(
    vip="Wishbone-UVM-VIP", p="wishbone", P="Wishbone", dir="wishbone",
    fields=[
        ("bit", "we", "req"),
        ("bit [31:0]", "adr", "req"),
        ("bit [31:0]", "wdat", "req"),
        ("bit [31:0]", "rdat", "rsp"),
        ("int unsigned", "wait_cycles", "info"),
    ],
    constraints="""
constraint c_adr  { adr[1:0] == 2'b00; adr < 32'h40; }   // 16 word registers
constraint c_wdat { !we -> wdat == 0; }
""",
    drv_desc="classic single-read / single-write cycles, waits for ACK",
    drv_idle="""
vif.drv_cb.wb_cyc_i <= 1'b0;
vif.drv_cb.wb_stb_i <= 1'b0;
vif.drv_cb.wb_we_i  <= 1'b0;
vif.drv_cb.wb_adr_i <= '0;
vif.drv_cb.wb_dat_i <= '0;
""",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.wb_cyc_i <= 1'b1;
vif.drv_cb.wb_stb_i <= 1'b1;
vif.drv_cb.wb_we_i  <= t.we;
vif.drv_cb.wb_adr_i <= t.adr;
vif.drv_cb.wb_dat_i <= t.wdat;
""" + wait_cb("vif.drv_cb.wb_ack_o === 1'b1", "Wishbone ACK") + """
t.rdat = vif.drv_cb.wb_dat_o;
vif.drv_cb.wb_cyc_i <= 1'b0;
vif.drv_cb.wb_stb_i <= 1'b0;
vif.drv_cb.wb_we_i  <= 1'b0;
""",
    mon_desc="one item per ACKed classic cycle",
    mon_run="""
int unsigned waits = 0;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.wb_cyc_i && vif.mon_cb.wb_stb_i) begin
    if (vif.mon_cb.wb_ack_o) begin
      wishbone_transaction t = wishbone_transaction::type_id::create("t");
      t.we   = vif.mon_cb.wb_we_i;
      t.adr  = vif.mon_cb.wb_adr_i;
      t.wdat = t.we ? vif.mon_cb.wb_dat_i : 32'h0;
      t.rdat = vif.mon_cb.wb_dat_o;
      t.wait_cycles = waits;
      waits = 0;
      publish(t);
    end else
      waits++;
  end
end
""",
    sb_members="bit [31:0] regs [16];   // reset value 0",
    predict="""
if (t.we) begin
  regs[t.adr[5:2]] = t.wdat;
  t.rdat = t.wdat;            // the model echoes the write data on DAT_O
end else
  t.rdat = regs[t.adr[5:2]];
""",
    checks="""
if (t.wait_cycles != 1)
  fail(t, $sformatf("ACK after %0d wait states (model registers ACK: expected 1)", t.wait_cycles));
if (t.adr[1:0] != 2'b00)
  fail(t, "unaligned word address");
""",
    coverage="""
cp_we  : coverpoint tr.we;
cp_reg : coverpoint tr.adr[5:2];
x_we_reg : cross cp_we, cp_reg;
""",
    directed="""
// write every register with a distinct pattern, then read all back
for (int i = 0; i < 16; i++) begin
  t = item(); t.we = 1; t.adr = i * 4; t.wdat = 32'hA5A5_0000 | (i * 32'h0101_0101); send(t);
end
for (int i = 0; i < 16; i++) begin
  t = item(); t.we = 0; t.adr = i * 4; send(t);
end
// overwrite, all-ones / all-zeros data, immediate read-after-write
t = item(); t.we = 1; t.adr = 32'h3C; t.wdat = 32'hFFFF_FFFF; send(t);
t = item(); t.we = 0; t.adr = 32'h3C; send(t);
t = item(); t.we = 1; t.adr = 32'h00; t.wdat = 32'h0; send(t);
t = item(); t.we = 0; t.adr = 32'h00; send(t);
""",
)
