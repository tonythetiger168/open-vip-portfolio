# UCIe die-to-die flit stream (tb/top_tb.sv ucie_model: 8-deep FIFO,
# tready = not full, rvalid/rdata/rlast from the FIFO head, pop on
# rvalid && rready).
from _lib import wait_cb, fill_fn

SPEC = dict(
    vip="UCIe-VIP", p="ucie", P="UCIe", dir="ucie",
    cfg="int unsigned rready_pct = 60;   // receiver ready probability (back-pressure fills the FIFO)",
    fields=[
        ("bit [63:0]", "flits", "req", "q"),
        ("bit [63:0]", "out_flits", "rsp", "q"),
        ("bit [4:0]", "nflits", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nflits inside {[1:20]}; }
""",
    tr_functions=fill_fn("flits", 64, "nf") + """

function void post_randomize();
  fill_flits(nflits);
endfunction
""",
    drv_rsp=False,
    drv_desc="flits on tvalid/tready (tlast on the last), random rready on the receive side",
    drv_idle="""
vif.drv_cb.tvalid <= 1'b0; vif.drv_cb.tdata <= '0; vif.drv_cb.tlast <= 1'b0;
vif.drv_cb.rready <= 1'b0;
""",
    drv_bg="""
forever begin
  @(vif.drv_cb);
  vif.drv_cb.rready <= ($urandom_range(99) < cfg.rready_pct);
end
""",
    drv_item="""
@(vif.drv_cb);
foreach (t.flits[i]) begin
  vif.drv_cb.tvalid <= 1'b1;
  vif.drv_cb.tdata  <= t.flits[i];
  vif.drv_cb.tlast  <= (i == t.flits.size() - 1);
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.tready === 1'b1", "UCIe tready").splitlines()) + """
end
vif.drv_cb.tvalid <= 1'b0;
vif.drv_cb.tlast  <= 1'b0;
""",
    mon_desc="transmit messages (tlast) paired in order with received messages (rlast)",
    mon_run="""
ucie_transaction in_q[$], cur_in, cur_out;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.tvalid && vif.mon_cb.tready) begin
    if (cur_in == null) begin
      cur_in = ucie_transaction::type_id::create("t");
      in_q.push_back(cur_in);   // queued at its first flit: the FIFO may drain it early
    end
    cur_in.flits.push_back(vif.mon_cb.tdata);
    if (vif.mon_cb.tlast) cur_in = null;
  end
  if (vif.mon_cb.rvalid && vif.mon_cb.rready) begin
    if (cur_out == null) begin
      if (in_q.size() == 0) begin
        `uvm_error("MON", "UCIe flit received that was never sent")
        continue;
      end
      cur_out = in_q.pop_front();
    end
    cur_out.out_flits.push_back(vif.mon_cb.rdata);
    if (vif.mon_cb.rlast) begin publish(cur_out); cur_out = null; end
  end
end
""",
    predict="""
t.out_flits = t.flits;
""",
    checks="""
if (t.flits.size() == 0) fail(t, "empty message");
""",
    coverage="""
cp_len : coverpoint tr.flits.size() { bins one = {1}; bins fits = {[2:8]}; bins overflows = {[9:20]}; }
""",
    directed="""
t = item(); t.seed = 32'h11; t.fill_flits(1); send(t);
t = item(); t.seed = 32'h12; t.fill_flits(8); send(t);    // exactly the FIFO depth
t = item(); t.seed = 32'h13; t.fill_flits(20); send(t);   // longer than the FIFO: tready back-pressure
t = item(); t.flits = '{64'h0, 64'hFFFF_FFFF_FFFF_FFFF, 64'h8000_0000_0000_0001}; send(t);
""",
)
# SVA: tready = FIFO not full, so it is high (empty FIFO) in reset
SPEC["patches"] = {"ucie/sva/ucie_compliance_checker.sv": [(
    "disable iff (1'b0) !rst_n |-> tready == '0)",
    "disable iff (1'b0) !rst_n |-> tready == 1'b1)   // empty FIFO in reset")]}
