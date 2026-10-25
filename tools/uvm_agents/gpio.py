# GPIO pin agent (tb/top_tb.sv gpio_model: gpio_out / gpio_oen register
# gpio_in / gpio_dir one clock later).
SPEC = dict(
    vip="GPIO-UVM-VIP", p="gpio", P="GPIO", dir="gpio",
    cfg="bit [15:0] pins = 16'h0;   // {gpio_in, gpio_dir} currently driven (kept by the driver)",
    fields=[
        ("bit [7:0]", "gin", "req"),
        ("bit [7:0]", "dir", "req"),
        ("bit [7:0]", "gout", "rsp"),
        ("bit [7:0]", "oen", "rsp"),
        ("bit [2:0]", "hold", "info", "rand"),   # clocks the pins stay at this value
    ],
    constraints="""
constraint c_hold { hold inside {[2:6]}; }
""",
    seq_members="bit [15:0] cur;",
    seq_before="cur = (cfg != null) ? cfg.pins : 16'h0;",
    # the monitor reports pin changes, so every item must change a pin
    rand_with="{gin, dir} != local::cur;",
    drv_desc="applies one gpio_in/gpio_dir value, samples the registered outputs",
    drv_idle="vif.drv_cb.gpio_in <= '0; vif.drv_cb.gpio_dir <= '0;",
    drv_item="""
if ({t.gin, t.dir} == cfg.pins)
  `uvm_error("GPIO", "item does not change any pin: the monitor cannot see it")
@(vif.drv_cb);
vif.drv_cb.gpio_in  <= t.gin;
vif.drv_cb.gpio_dir <= t.dir;
cfg.pins = {t.gin, t.dir};
@(vif.drv_cb);          // the model registers the new value
@(vif.drv_cb);
t.gout = vif.drv_cb.gpio_out;
t.oen  = vif.drv_cb.gpio_oen;
repeat ((t.hold > 2) ? t.hold - 2 : 0) @(vif.drv_cb);
""",
    mon_desc="one item per input change, outputs sampled one clock later",
    mon_run="""
bit [7:0] pin = 0, pdir = 0;
gpio_transaction t;
forever begin
  @(vif.mon_cb);
  if (t != null) begin
    t.gout = vif.mon_cb.gpio_out;
    t.oen  = vif.mon_cb.gpio_oen;
    publish(t);
    t = null;
  end
  if (vif.mon_cb.gpio_in != pin || vif.mon_cb.gpio_dir != pdir) begin
    pin = vif.mon_cb.gpio_in; pdir = vif.mon_cb.gpio_dir;
    t = gpio_transaction::type_id::create("t");
    t.gin = pin; t.dir = pdir;
  end
end
""",
    predict="""
t.gout = t.gin;   // input pins appear on gpio_out
t.oen  = t.dir;   // direction drives the output enables
""",
    checks="""
// nothing beyond the reference model: every pin value is legal
""",
    coverage="""
cp_dir : coverpoint tr.dir { bins all_in = {8'h00}; bins all_out = {8'hFF}; bins mixed = default; }
cp_in  : coverpoint tr.gin { bins zero = {8'h00}; bins ones = {8'hFF}; bins other = default; }
""",
    directed="""
// walking one on each pin in both directions, then all-ones / all-zeros
for (int i = 0; i < 8; i++) begin t = item(); t.gin = 8'h1 << i; t.dir = 8'h00; t.hold = 3; send(t); end
for (int i = 0; i < 8; i++) begin t = item(); t.gin = 8'h1 << i; t.dir = 8'h1 << i; t.hold = 2; send(t); end
t = item(); t.gin = 8'hFF; t.dir = 8'hFF; t.hold = 4; send(t);
t = item(); t.gin = 8'h00; t.dir = 8'hFF; t.hold = 2; send(t);
t = item(); t.gin = 8'hA5; t.dir = 8'h5A; t.hold = 6; send(t);
""",
)
