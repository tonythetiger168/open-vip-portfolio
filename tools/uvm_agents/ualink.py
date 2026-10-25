# UALink transaction-layer requester (tb/top_tb.sv ualink_model: 64 x 64-bit
# words at addr[8:3], opcode 4 = read, 5 = write, anything else answers
# status 1; one request outstanding, response held until rsp_ready).
from _lib import wait_cb

SPEC = dict(
    vip="UALink-VIP", p="ualink", P="UALink", dir="ualink",
    defs="""
localparam bit [3:0] UAL_OP_RD = 4'd4, UAL_OP_WR = 4'd5;
""",
    fields=[
        ("bit [3:0]", "opcode", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [63:0]", "wdata", "req"),
        ("bit [1:0]", "status", "rsp"),
        ("bit [63:0]", "rdata", "rsp"),
        ("bit [1:0]", "rsp_wait", "info", "rand"),   # clocks rsp_ready is held low
    ],
    constraints="""
constraint c_op   { opcode dist { UAL_OP_RD := 4, UAL_OP_WR := 4, [0:3] :/ 1, [6:15] :/ 1 }; }
constraint c_addr { addr[2:0] == 3'b000; addr < 32'h200; }
constraint c_data { opcode != UAL_OP_WR -> wdata == 0; }
""",
    drv_desc="request until req_ready, response accepted after rsp_wait clocks of back-pressure",
    drv_idle="""
vif.drv_cb.req_valid <= 1'b0; vif.drv_cb.req_opcode <= '0;
vif.drv_cb.req_addr <= '0; vif.drv_cb.req_wdata <= '0;
vif.drv_cb.rsp_ready <= 1'b1;
""",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.req_valid  <= 1'b1;
vif.drv_cb.req_opcode <= t.opcode;
vif.drv_cb.req_addr   <= t.addr;
vif.drv_cb.req_wdata  <= t.wdata;
vif.drv_cb.rsp_ready  <= (t.rsp_wait == 0);
""" + wait_cb("vif.drv_cb.req_ready === 1'b1", "UALink req_ready") + """
vif.drv_cb.req_valid <= 1'b0;
if (t.rsp_wait != 0) begin
  repeat (t.rsp_wait) @(vif.drv_cb);
  vif.drv_cb.rsp_ready <= 1'b1;
end
""" + wait_cb("vif.drv_cb.rsp_valid === 1'b1 && vif.drv_cb.rsp_ready === 1'b1", "UALink response") + """
t.status = vif.drv_cb.rsp_status;
t.rdata  = vif.drv_cb.rsp_rdata;
""",
    mon_desc="request handshake, completed by the response handshake",
    mon_run="""
ualink_transaction t;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rsp_valid && vif.mon_cb.rsp_ready) begin
    if (t == null) `uvm_error("MON", "UALink response without a request")
    else begin
      t.status = vif.mon_cb.rsp_status;
      t.rdata  = vif.mon_cb.rsp_rdata;
      publish(t);
      t = null;
    end
  end
  if (vif.mon_cb.req_valid && vif.mon_cb.req_ready) begin
    if (t != null) `uvm_error("MON", "UALink second request while one is outstanding")
    t = ualink_transaction::type_id::create("t");
    t.opcode = vif.mon_cb.req_opcode;
    t.addr   = vif.mon_cb.req_addr;
    t.wdata  = vif.mon_cb.req_opcode == UAL_OP_WR ? vif.mon_cb.req_wdata : 64'h0;
  end
end
""",
    sb_members="bit [63:0] mem [64];   // cleared by reset",
    predict="""
t.rdata = 0;
case (t.opcode)
  UAL_OP_RD: begin t.status = 0; t.rdata = mem[t.addr[8:3]]; end
  UAL_OP_WR: begin t.status = 0; mem[t.addr[8:3]] = t.wdata; end
  default:   t.status = 1;   // unsupported opcode
endcase
""",
    checks="""
if ((t.opcode == UAL_OP_RD || t.opcode == UAL_OP_WR) && t.status != 0) fail(t, "error status for a supported opcode");
if (t.opcode != UAL_OP_RD && t.rdata != 0) fail(t, "read data on a non-read response");
""",
    coverage="""
cp_op     : coverpoint tr.opcode { bins rd = {UAL_OP_RD}; bins wr = {UAL_OP_WR}; bins bad = default; }
cp_status : coverpoint tr.status { bins ok = {0}; bins err = {1}; }
cp_word   : coverpoint tr.addr[8:3] { bins first = {0}; bins last = {63}; bins mid = {[1:62]}; }
""",
    directed="""
for (int i = 0; i < 64; i += 9) begin
  t = item(); t.opcode = UAL_OP_WR; t.addr = i * 8; t.wdata = {32'hA11C_E000 | i, 32'h0BAD_C0DE}; send(t);
  t = item(); t.opcode = UAL_OP_RD; t.addr = i * 8; t.rsp_wait = 3; send(t);
end
t = item(); t.opcode = UAL_OP_RD; t.addr = 32'h1F8; send(t);   // unwritten: 0
t = item(); t.opcode = 4'd0; t.addr = 32'h8; send(t);           // unsupported opcodes
t = item(); t.opcode = 4'd15; t.addr = 32'h10; t.rsp_wait = 2; send(t);
t = item(); t.opcode = UAL_OP_WR; t.addr = 32'h1F8; t.wdata = '1; send(t);
t = item(); t.opcode = UAL_OP_RD; t.addr = 32'h1F8; send(t);
""",
)
# SVA: the model is ready for a request in reset (req_ready resets to 1)
# and a response held under back-pressure (rsp_valid && !rsp_ready) keeps its
# status, so the error-status check applies from its handshake on
SPEC["patches"] = {"ualink/sva/ualink_compliance_checker.sv": [
    ("disable iff (1'b0) !rst_n |-> req_ready == '0)",
     "disable iff (1'b0) !rst_n |-> req_ready == 1'b1)   // ready in reset"),
    ("rsp_status == 2'd1 |=> !rsp_valid || rsp_status == 2'd0)",
     "rsp_status == 2'd1 && rsp_valid && rsp_ready |=> !rsp_valid || rsp_status == 2'd0)")]}
