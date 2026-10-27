# Avalon-MM host (tb/top_tb.sv avalon_mm_model: 64 x 32-bit words at
# address[7:2]; waitrequest is high on the first clock of each command, and
# the command completes on the clock where waitrequest is low, as in the
# Avalon-MM specification; read data returns with readdatavalid two clocks
# after the transfer). Until 2026-10-27 the model took the command on the
# clock its registered waitrequest was HIGH; fixed in the model and here.
from _lib import wait_cb

SPEC = dict(
    vip="Avalon_MM-UVM-VIP", p="avalon_mm", P="Avalon-MM", dir="avalon_mm",
    fields=[
        ("bit", "write", "req"),
        ("bit [7:0]", "address", "req"),
        ("bit [31:0]", "writedata", "req"),
        ("bit [31:0]", "readdata", "rsp"),
        ("bit [1:0]", "response", "rsp"),
    ],
    constraints="""
constraint c_addr { address[1:0] == 2'b00; }
constraint c_data { !write -> writedata == 0; }
""",
    drv_desc="single read / write, held until the clock where waitrequest is low",
    drv_idle="""
vif.drv_cb.av_write <= 1'b0; vif.drv_cb.av_read <= 1'b0;
vif.drv_cb.av_address <= '0; vif.drv_cb.av_writedata <= '0;
""",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.av_address   <= t.address;
vif.drv_cb.av_writedata <= t.writedata;
vif.drv_cb.av_write     <= t.write;
vif.drv_cb.av_read      <= !t.write;
""" + wait_cb("vif.drv_cb.av_waitrequest === 1'b0", "Avalon-MM command accept") + """
vif.drv_cb.av_write <= 1'b0;
vif.drv_cb.av_read  <= 1'b0;
t.response = 2'b00;
if (!t.write) begin
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.av_readdatavalid === 1'b1", "Avalon-MM readdatavalid").splitlines()) + """
  t.readdata = vif.drv_cb.av_readdata;
  t.response = vif.drv_cb.av_response;
end
""",
    mon_desc="transfer on each clock with read/write high and waitrequest low, reads completed by readdatavalid",
    mon_run="""
avalon_mm_transaction rd;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.av_readdatavalid) begin
    if (rd == null) `uvm_error("MON", "Avalon-MM readdatavalid without an outstanding read")
    else begin
      rd.readdata = vif.mon_cb.av_readdata;
      rd.response = vif.mon_cb.av_response;
      publish(rd);
      rd = null;
    end
  end
  if ((vif.mon_cb.av_write || vif.mon_cb.av_read) && !vif.mon_cb.av_waitrequest) begin
    avalon_mm_transaction t = avalon_mm_transaction::type_id::create("t");
    t.write     = vif.mon_cb.av_write;
    t.address   = vif.mon_cb.av_address;
    t.writedata = t.write ? vif.mon_cb.av_writedata : 32'h0;
    if (t.write) publish(t);
    else if (rd != null) `uvm_error("MON", "Avalon-MM read issued with a read outstanding")
    else rd = t;
  end
end
""",
    sb_members="bit [31:0] mem [64];   // reset value 0",
    predict="""
t.response = 2'b00;
if (t.write) begin
  mem[t.address[7:2]] = t.writedata;
  t.readdata = 0;
end else
  t.readdata = mem[t.address[7:2]];
""",
    checks="""
if (t.response != 2'b00) fail(t, "non-OKAY response");
if (t.address[1:0] != 2'b00) fail(t, "address not word aligned");
""",
    coverage="""
cp_write : coverpoint tr.write;
cp_word  : coverpoint tr.address[7:2] { bins low = {[0:15]}; bins mid = {[16:47]}; bins high = {[48:63]}; }
x_rw     : cross cp_write, cp_word;
""",
    directed="""
for (int i = 0; i < 64; i += 7) begin
  t = item(); t.write = 1; t.address = i * 4; t.writedata = 32'h5A00_0000 | i; send(t);
  t = item(); t.write = 0; t.address = i * 4; send(t);
end
t = item(); t.write = 0; t.address = 8'h04; send(t);              // never written: 0
t = item(); t.write = 1; t.address = 8'hFC; t.writedata = '1; send(t);
t = item(); t.write = 1; t.address = 8'hFC; t.writedata = 32'h1; send(t);
t = item(); t.write = 0; t.address = 8'hFC; send(t);
""",
    ral=dict(
        n_regs=64,
        desc="avalon_mm_model memory, 64 x 32-bit words at address[7:2], reset 0",
        reg2bus="""
t.write     = (rw.kind == UVM_WRITE);
t.address   = rw.addr[7:0];
t.writedata = t.write ? rw.data[31:0] : 32'h0;
""",
        bus2reg="""
rw.kind   = t.write ? UVM_WRITE : UVM_READ;
rw.addr   = t.address;
rw.data   = t.write ? t.writedata : t.readdata;
rw.status = (t.response == 2'b00) ? UVM_IS_OK : UVM_NOT_OK;
""",
    ),
)
