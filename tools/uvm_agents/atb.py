# ATB trace source (tb/top_tb.sv atb_model: at_ready pulses one clock after
# at_valid, at_afready answers at_afvalid unless at_flush was high the
# clock before).
from _lib import wait_cb

SPEC = dict(
    vip="ATB-UVM-VIP", p="atb", P="ATB", dir="atb",
    fields=[
        ("bit", "flush", "req"),          # 0: trace data beat, 1: AFVALID/AFREADY flush handshake
        ("bit [31:0]", "data", "req"),
        ("int unsigned", "waits", "rsp"),  # clocks VALID was held before READY
    ],
    constraints="""
constraint c_kind { flush dist { 0 := 6, 1 := 1 }; flush -> data == 0; }
""",
    drv_rsp=False,
    drv_desc="one trace beat (VALID/READY) or one flush handshake (AFVALID/AFREADY)",
    drv_idle="""
vif.drv_cb.at_valid <= 1'b0; vif.drv_cb.at_data <= '0;
vif.drv_cb.at_afvalid <= 1'b0; vif.drv_cb.at_flush <= 1'b0;
""",
    drv_item="""
@(vif.drv_cb);
if (!t.flush) begin
  vif.drv_cb.at_valid <= 1'b1;
  vif.drv_cb.at_data  <= t.data;
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.at_ready === 1'b1", "ATB READY").splitlines()) + """
  vif.drv_cb.at_valid <= 1'b0;
end else begin
  vif.drv_cb.at_afvalid <= 1'b1;
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.at_afready === 1'b1", "ATB AFREADY").splitlines()) + """
  vif.drv_cb.at_afvalid <= 1'b0;
end
""",
    mon_desc="one item per accepted beat or flush handshake",
    mon_run="""
int unsigned dw = 0, fw = 0;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.at_valid) begin
    if (vif.mon_cb.at_ready) begin
      atb_transaction t = atb_transaction::type_id::create("t");
      t.flush = 0; t.data = vif.mon_cb.at_data; t.waits = dw; dw = 0;
      publish(t);
    end else dw++;
  end
  if (vif.mon_cb.at_afvalid) begin
    if (vif.mon_cb.at_afready) begin
      atb_transaction t = atb_transaction::type_id::create("t");
      t.flush = 1; t.data = 0; t.waits = fw; fw = 0;
      publish(t);
    end else fw++;
  end
end
""",
    predict="""
t.waits = 1;   // the model registers READY / AFREADY: one wait state
""",
    checks="""
if (t.flush && t.data != 0) fail(t, "flush handshake carrying data");
""",
    coverage="""
cp_kind : coverpoint tr.flush { bins beat = {0}; bins flush = {1}; }
cp_data : coverpoint tr.data { bins zero = {0}; bins ones = {32'hFFFF_FFFF}; bins other = default; }
""",
    directed="""
t = item(); t.data = 32'h0; send(t);
t = item(); t.data = 32'hFFFF_FFFF; send(t);
for (int i = 0; i < 8; i++) begin t = item(); t.data = 32'h1 << (i * 4); send(t); end
t = item(); t.flush = 1; send(t);
t = item(); t.data = 32'hCAFE_F00D; send(t);
t = item(); t.flush = 1; send(t);
t = item(); t.flush = 1; send(t);
""",
)
