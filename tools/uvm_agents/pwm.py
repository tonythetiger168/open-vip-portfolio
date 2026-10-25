# PWM generator control agent (tb/top_tb.sv pwm_model: counter 0..period-1,
# pwm_out = cnt < duty while enabled, pwm_oe = enable, both registered).
SPEC = dict(
    vip="PWM-UVM-VIP", p="pwm", P="PWM", dir="pwm",
    fields=[
        ("bit [15:0]", "period", "req"),
        ("bit [15:0]", "duty", "req"),
        ("bit [2:0]", "periods", "req"),       # PWM periods the setting runs for
        ("bit [15:0]", "high_cnt", "rsp"),     # clocks pwm_out was high
        ("bit", "oe_ok", "rsp"),               # pwm_oe high for the whole run
    ],
    constraints="""
constraint c_cfg { period inside {[1:40]}; duty dist { 0 := 1, [1:40] :/ 6, [41:48] :/ 1 }; periods inside {[1:3]}; }
""",
    drv_desc="enable for periods x period clocks with the item's setting, then disable",
    drv_idle="vif.drv_cb.enable <= 1'b0; vif.drv_cb.period <= '0; vif.drv_cb.duty <= '0;",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.period <= t.period;
vif.drv_cb.duty   <= t.duty;
vif.drv_cb.enable <= 1'b1;
repeat (t.periods * t.period) @(vif.drv_cb);
vif.drv_cb.enable <= 1'b0;
repeat (2) @(vif.drv_cb);   // counter back to 0 before the next setting
""",
    drv_rsp=False,
    mon_desc="measures pwm_out over each enable window",
    mon_run="""
pwm_transaction t;
bit en_d = 0;
int unsigned len = 0;
forever begin
  @(vif.mon_cb);
  if (t != null) begin
    // outputs registered from the clocks enable was high
    len++;
    if (vif.mon_cb.pwm_out) t.high_cnt++;
    if (!vif.mon_cb.pwm_oe) t.oe_ok = 0;
    if (!vif.mon_cb.enable) begin
      t.periods = (t.period != 0) ? len / t.period : 0;
      if (t.period == 0 || len % t.period != 0)
        `uvm_error("MON", $sformatf("PWM enable window of %0d clocks is not whole periods", len))
      publish(t);
      t = null;
    end
  end
  if (vif.mon_cb.enable && !en_d) begin
    t = pwm_transaction::type_id::create("t");
    t.period = vif.mon_cb.period;
    t.duty   = vif.mon_cb.duty;
    t.oe_ok  = 1;
    len = 0;
  end
  en_d = vif.mon_cb.enable;
end
""",
    predict="""
// counter starts at 0 when enabled: high for min(duty, period) clocks a period
t.high_cnt = t.periods * ((t.duty < t.period) ? t.duty : t.period);
t.oe_ok = 1;
""",
    checks="""
if (t.period == 0) fail(t, "enabled with a zero period");
""",
    coverage="""
cp_duty : coverpoint (tr.duty == 0 ? 0 : tr.duty < tr.period ? 1 : tr.duty == tr.period ? 2 : 3)
  { bins off = {0}; bins partial = {1}; bins full = {2}; bins over = {3}; }
cp_per  : coverpoint tr.period { bins one = {1}; bins short_ = {[2:8]}; bins long_ = {[9:40]}; }
""",
    directed="""
t = item(); t.period = 10; t.duty = 0;  t.periods = 2; send(t);   // 0 %
t = item(); t.period = 10; t.duty = 5;  t.periods = 3; send(t);   // 50 %
t = item(); t.period = 10; t.duty = 10; t.periods = 1; send(t);   // 100 %
t = item(); t.period = 10; t.duty = 15; t.periods = 2; send(t);   // duty above period
t = item(); t.period = 1;  t.duty = 1;  t.periods = 3; send(t);
t = item(); t.period = 1;  t.duty = 0;  t.periods = 2; send(t);
t = item(); t.period = 40; t.duty = 1;  t.periods = 1; send(t);
""",
)
