# CHI request node (tb/top_tb.sv chi_model: REQ accepted with a one-clock
# req_ready pulse, write data accepted with it, then one RSP (resp = 5'b00001)
# held until rsp_ready).
from _lib import wait_cb

SPEC = dict(
    vip="CHI-UVM-VIP", p="chi", P="CHI", dir="chi",
    defs="""
// REQ opcodes used by the agent (CHI-B encodings, low 5 bits)
localparam bit [4:0] CHI_READ_ONCE    = 5'h03;
localparam bit [4:0] CHI_READ_NOSNP   = 5'h04;
localparam bit [4:0] CHI_WRITE_UNIQUE = 5'h19;   // WriteUniqueFull
localparam bit [4:0] CHI_WRITE_NOSNP  = 5'h1D;   // WriteNoSnpFull
function automatic bit chi_is_write(bit [4:0] op);
  return op == CHI_WRITE_UNIQUE || op == CHI_WRITE_NOSNP;
endfunction
""",
    fields=[
        ("bit [4:0]", "opcode", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [63:0]", "data", "req"),
        ("bit", "dat_acc", "rsp"),        # write data accepted (dat_ready with req_ready)
        ("bit [4:0]", "resp", "rsp"),
    ],
    constraints="""
constraint c_op   { opcode inside {CHI_READ_ONCE, CHI_READ_NOSNP, CHI_WRITE_UNIQUE, CHI_WRITE_NOSNP}; }
constraint c_addr { addr[5:0] == 6'h0; }   // cache-line aligned
constraint c_data { !(opcode inside {CHI_WRITE_UNIQUE, CHI_WRITE_NOSNP}) -> data == 0; }
""",
    drv_desc="REQ (+DAT for writes) until req_ready, then accepts the RSP",
    drv_idle="""
vif.drv_cb.req_valid <= 1'b0; vif.drv_cb.req_addr <= '0; vif.drv_cb.req_opcode <= '0;
vif.drv_cb.dat_valid <= 1'b0; vif.drv_cb.dat_data <= '0;
vif.drv_cb.rsp_ready <= 1'b0;
""",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.req_valid  <= 1'b1;
vif.drv_cb.req_addr   <= t.addr;
vif.drv_cb.req_opcode <= t.opcode;
vif.drv_cb.dat_valid  <= chi_is_write(t.opcode);
vif.drv_cb.dat_data   <= t.data;
""" + wait_cb("vif.drv_cb.req_ready === 1'b1", "CHI req_ready") + """
t.dat_acc = (vif.drv_cb.dat_ready === 1'b1);
vif.drv_cb.req_valid <= 1'b0;
vif.drv_cb.dat_valid <= 1'b0;
// the model drops rsp_valid if rsp_ready is already high: accept after valid
""" + wait_cb("vif.drv_cb.rsp_valid === 1'b1", "CHI rsp_valid") + """
vif.drv_cb.rsp_ready <= 1'b1;
@(vif.drv_cb);
t.resp = vif.drv_cb.rsp_resp;
vif.drv_cb.rsp_ready <= 1'b0;
""",
    mon_desc="REQ/DAT handshake, completed by the RSP handshake",
    mon_run="""
chi_transaction t;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.req_valid && vif.mon_cb.req_ready) begin
    if (t != null) `uvm_error("MON", "CHI request accepted with a response outstanding")
    t = chi_transaction::type_id::create("t");
    t.opcode  = vif.mon_cb.req_opcode;
    t.addr    = vif.mon_cb.req_addr;
    t.dat_acc = vif.mon_cb.dat_valid && vif.mon_cb.dat_ready;
    t.data    = vif.mon_cb.dat_valid ? vif.mon_cb.dat_data : 64'h0;
  end
  if (vif.mon_cb.rsp_valid && vif.mon_cb.rsp_ready) begin
    if (t == null) `uvm_error("MON", "CHI response without a request")
    else begin
      t.resp = vif.mon_cb.rsp_resp;
      publish(t);
      t = null;
    end
  end
end
""",
    predict="""
t.dat_acc = chi_is_write(t.opcode);
t.resp    = 5'b00001;   // OK
""",
    checks="""
if (t.resp != 5'b00001) fail(t, "response is not OK");
if (chi_is_write(t.opcode) && !t.dat_acc) fail(t, "write data not accepted with the request");
if (t.addr[5:0] != 0) fail(t, "address not cache-line aligned");
""",
    coverage="""
cp_op : coverpoint tr.opcode { bins rd_once = {CHI_READ_ONCE}; bins rd_nosnp = {CHI_READ_NOSNP};
                               bins wr_unique = {CHI_WRITE_UNIQUE}; bins wr_nosnp = {CHI_WRITE_NOSNP}; }
cp_dat : coverpoint tr.dat_acc;
""",
    directed="""
bit [4:0] ops [4] = '{CHI_READ_ONCE, CHI_READ_NOSNP, CHI_WRITE_UNIQUE, CHI_WRITE_NOSNP};
foreach (ops[i]) begin
  t = item(); t.opcode = ops[i]; t.addr = 32'h1000 + i * 64;
  if (chi_is_write(ops[i])) t.data = 64'hFEED_FACE_0000_0000 | i;
  send(t);
end
t = item(); t.opcode = CHI_WRITE_NOSNP; t.addr = 32'hFFFF_FFC0; t.data = '1; send(t);
t = item(); t.opcode = CHI_READ_NOSNP; t.addr = 32'hFFFF_FFC0; send(t);
""",
)
