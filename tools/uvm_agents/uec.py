# Ultra Ethernet packet port (tb/top_tb.sv uec_model: one 512-bit beat per
# packet with its length, 64..1518 bytes delivered on rx_* three clocks later,
# anything shorter or longer reported with an rx_err pulse instead).
from _lib import wait_cb, fill_fn

SPEC = dict(
    vip="UEC-VIP", p="uec", P="UEC", dir="uec",
    fields=[
        ("bit [10:0]", "len", "req"),
        ("bit [511:0]", "data", "req", "norand"),
        ("bit", "err", "rsp"),            # rx_err instead of rx_valid
        ("bit [511:0]", "rx_data", "rsp"),
        ("bit [10:0]", "rx_len", "rsp"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { len dist { [64:1518] :/ 8, [0:63] :/ 1, [1519:2047] :/ 1, 64 := 1, 1518 := 1 }; }
""",
    tr_members="bit [511:0] dq[$];",
    tr_functions=fill_fn("dq", 512, "n") + """

function void post_randomize();
  fill_dq(1);
  data = dq[0];
endfunction
""",
    drv_rsp=False,
    drv_desc="one packet beat per item on tx_valid/tx_ready",
    drv_idle="""
vif.drv_cb.tx_valid <= 1'b0; vif.drv_cb.tx_data <= '0; vif.drv_cb.tx_len <= '0;
""",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.tx_valid <= 1'b1;
vif.drv_cb.tx_data  <= t.data;
vif.drv_cb.tx_len   <= t.len;
""" + wait_cb("vif.drv_cb.tx_ready === 1'b1", "UEC tx_ready") + """
vif.drv_cb.tx_valid <= 1'b0;
""",
    mon_desc="transmitted packets paired in order with rx_valid / rx_err",
    mon_run="""
uec_transaction in_q[$];
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rx_valid || vif.mon_cb.rx_err) begin
    if (in_q.size() == 0) `uvm_error("MON", "UEC rx_valid/rx_err with no packet in flight")
    else begin
      uec_transaction t = in_q.pop_front();
      if (vif.mon_cb.rx_valid && vif.mon_cb.rx_err) `uvm_error("MON", "UEC rx_valid and rx_err together")
      t.err     = vif.mon_cb.rx_err;
      t.rx_data = t.err ? '0 : vif.mon_cb.rx_data;
      t.rx_len  = t.err ? '0 : vif.mon_cb.rx_len;
      publish(t);
    end
  end
  if (vif.mon_cb.tx_valid && vif.mon_cb.tx_ready) begin
    uec_transaction t = uec_transaction::type_id::create("t");
    t.data = vif.mon_cb.tx_data;
    t.len  = vif.mon_cb.tx_len;
    in_q.push_back(t);
  end
end
""",
    predict="""
// length policing: 64..1518 bytes delivered unchanged, otherwise rx_err
t.err     = (t.len < 64 || t.len > 1518);
t.rx_data = t.err ? '0 : t.data;
t.rx_len  = t.err ? '0 : t.len;
""",
    checks="""
if (!t.err && (t.rx_len < 64 || t.rx_len > 1518)) fail(t, "out-of-range length delivered");
""",
    coverage="""
cp_len : coverpoint tr.len { bins runt = {[0:63]}; bins min_ = {64}; bins normal = {[65:1517]}; bins max_ = {1518}; bins giant = {[1519:2047]}; }
cp_err : coverpoint tr.err;
""",
    directed="""
int unsigned lens [8] = '{64, 1518, 63, 1519, 0, 2047, 65, 1000};
foreach (lens[i]) begin
  t = item(); t.len = lens[i]; t.seed = 32'h5EED + i; t.fill_dq(1); t.data = t.dq[0]; send(t);
end
""",
)
