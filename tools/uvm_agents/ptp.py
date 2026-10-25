# PTP timestamp unit (tb/top_tb.sv ptp_model: clock_time += 8 ns every clock,
# event_i rising edge latched into event_ts, egress_req latched into
# egress_ts, each reported with a one-clock *_valid).
SPEC = dict(
    vip="PTP-VIP", p="ptp", P="PTP", dir="ptp",
    cfg="int unsigned clock_step_ns = 8;   // ptp_model CLOCK_STEP_NS",
    fields=[
        ("bit", "egress", "req"),            # 0: event_i edge, 1: egress_req
        ("bit", "valid", "rsp"),             # *_valid the clock after the request
        ("bit [63:0]", "ts_delta", "rsp"),   # timestamp - clock_time when the request was sampled
        ("bit [2:0]", "width", "info", "rand"),
        ("bit [63:0]", "ts", "info"),
    ],
    constraints="""
constraint c_width { width inside {[1:6]}; }
""",
    drv_rsp=False,
    drv_desc="an event_i pulse of width clocks, or a one-clock egress_req",
    drv_idle="vif.drv_cb.event_i <= 1'b0; vif.drv_cb.egress_req <= 1'b0;",
    drv_item="""
@(vif.drv_cb);
if (!t.egress) begin
  vif.drv_cb.event_i <= 1'b1;
  repeat (t.width) @(vif.drv_cb);
  vif.drv_cb.event_i <= 1'b0;
end else begin
  vif.drv_cb.egress_req <= 1'b1;
  @(vif.drv_cb);
  vif.drv_cb.egress_req <= 1'b0;
end
repeat (3) @(vif.drv_cb);
""",
    mon_desc="timestamps checked against the free-running clock_time",
    mon_run="""
ptp_transaction ev, eg;
bit [63:0] ev_ref, eg_ref, last_time;
bit ev_d = 0, have_time = 0;
forever begin
  @(vif.mon_cb);
  if (have_time && vif.mon_cb.clock_time != last_time + cfg.clock_step_ns)
    `uvm_error("MON", $sformatf("PTP clock_time stepped from %0d to %0d", last_time, vif.mon_cb.clock_time))
  last_time = vif.mon_cb.clock_time; have_time = 1;
  if (ev != null) begin
    ev.valid = vif.mon_cb.event_valid; ev.ts = vif.mon_cb.event_ts;
    ev.ts_delta = vif.mon_cb.event_ts - ev_ref;
    publish(ev); ev = null;
  end
  if (eg != null) begin
    eg.valid = vif.mon_cb.egress_valid; eg.ts = vif.mon_cb.egress_ts;
    eg.ts_delta = vif.mon_cb.egress_ts - eg_ref;
    publish(eg); eg = null;
  end
  if (vif.mon_cb.event_i && !ev_d) begin
    ev = ptp_transaction::type_id::create("ev");
    ev.egress = 0; ev_ref = vif.mon_cb.clock_time;
  end
  if (vif.mon_cb.egress_req) begin
    eg = ptp_transaction::type_id::create("eg");
    eg.egress = 1; eg_ref = vif.mon_cb.clock_time;
  end
  ev_d = vif.mon_cb.event_i;
end
""",
    predict="""
// the model latches clock_time on the clock it samples the request
t.valid = 1;
t.ts_delta = 0;
""",
    checks="""
if (t.ts[2:0] != 0) fail(t, "timestamp not a multiple of the 8 ns clock step");
""",
    coverage="""
cp_kind : coverpoint tr.egress { bins event_ = {0}; bins egress = {1}; }
""",
    directed="""
t = item(); t.egress = 0; t.width = 1; send(t);
t = item(); t.egress = 0; t.width = 6; send(t);   // long pulse: one timestamp
t = item(); t.egress = 1; send(t);
t = item(); t.egress = 1; send(t);
t = item(); t.egress = 0; t.width = 2; send(t);
""",
)
