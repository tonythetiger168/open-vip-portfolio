# 1-Wire bus master (tb/top_tb.sv onewire_model: a low of 8 or more clocks is
# a reset and is answered by a presence pulse; the model has no ROM or data
# path, so read slots return the master's own bits).
SPEC = dict(
    vip="OneWire-UVM-VIP", p="onewire", P="1-Wire", dir="onewire",
    cfg="""int unsigned reset_low  = 10;  // reset pulse (model detects >= 8; >= 17 re-triggers it)
int unsigned presence_win = 16; // clocks after the reset pulse to look for presence
int unsigned slot_clks  = 10;  // time slot
int unsigned low0_clks  = 4;   // write-0 low time (< 8: not a reset)
int unsigned low1_clks  = 1;   // write-1 / read low time
int unsigned sample_clk = 3;   // master samples the line this many clocks into the slot""",
    fields=[
        ("bit", "is_reset", "req"),       # 1: reset/presence, 0: one byte of time slots
        ("bit [7:0]", "wdata", "req"),
        ("bit", "presence", "rsp"),
        ("bit [7:0]", "rdata", "rsp"),    # line value at the sampling point of each slot
    ],
    constraints="""
constraint c_kind { is_reset dist { 0 := 4, 1 := 1 }; is_reset -> wdata == 0; }
""",
    drv_desc="reset/presence detect, or eight write/read time slots (LSB first)",
    drv_idle="vif.drv_cb.dq_oe <= 1'b0; vif.drv_cb.dq_o <= 1'b1;",
    drv_item="""
@(vif.drv_cb);
if (t.is_reset) begin
  vif.drv_cb.dq_oe <= 1'b1; vif.drv_cb.dq_o <= 1'b0;
  repeat (cfg.reset_low) @(vif.drv_cb);
  vif.drv_cb.dq_oe <= 1'b0;
  t.presence = 0;
  repeat (cfg.presence_win) begin
    @(vif.drv_cb);
    if (vif.drv_cb.dq === 1'b0) t.presence = 1;
  end
  repeat (4) @(vif.drv_cb);
end else begin
  for (int i = 0; i < 8; i++) begin
    int unsigned low = t.wdata[i] ? cfg.low1_clks : cfg.low0_clks;
    vif.drv_cb.dq_oe <= 1'b1; vif.drv_cb.dq_o <= 1'b0;
    for (int c = 0; c < cfg.slot_clks; c++) begin
      @(vif.drv_cb);
      if (c + 1 == low) vif.drv_cb.dq_oe <= 1'b0;
      if (c == cfg.sample_clk) t.rdata[i] = (vif.drv_cb.dq !== 1'b0);
    end
  end
end
""",
    mon_desc="master low pulses on dq: resets (with presence) and byte-wise time slots",
    mon_run="""
int unsigned nbit = 0;
bit [7:0] wb = 0, rb = 0;
forever begin
  @(vif.mon_cb);
  if (master_low()) begin                  // first clock of a master low pulse
    int unsigned low = 1, c = 0;
    bit rv = 1, released = 0;
    // measure the low time; the line is sampled sample_clk clocks in
    while (!released || c < cfg.sample_clk) begin
      @(vif.mon_cb); c++;
      if (c == cfg.sample_clk) rv = (vif.mon_cb.dq !== 1'b0);
      if (!released) begin
        if (master_low()) low++; else released = 1;
      end
      if (released && low >= 8) break;
      if (c > 10 * cfg.slot_clks) break;
    end
    if (low >= 8) begin                    // reset: look for the presence pulse
      onewire_transaction t = onewire_transaction::type_id::create("t");
      if (nbit != 0) `uvm_error("MON", "1-Wire reset inside a byte")
      nbit = 0;
      t.is_reset = 1;
      for (int i = 0; i < cfg.presence_win; i++) begin
        if (i != 0) @(vif.mon_cb);
        if (vif.mon_cb.dq === 1'b0 && !master_low()) t.presence = 1;
      end
      publish(t);
    end else begin                         // time slot: short low writes 1 (or reads)
      wb[nbit] = (low < cfg.low0_clks);
      rb[nbit] = rv;
      nbit++;
      if (nbit == 8) begin
        onewire_transaction t = onewire_transaction::type_id::create("t");
        t.wdata = wb; t.rdata = rb;
        publish(t);
        nbit = 0;
      end
    end
  end
end
""",
    mon_tasks="""
function bit master_low();
  return vif.mon_cb.dq_oe === 1'b1 && vif.mon_cb.dq_o === 1'b0;
endfunction
""",
    predict="""
// no slave answers data slots: the line carries the master's bits
t.rdata = t.is_reset ? 8'h0 : t.wdata;
t.presence = t.is_reset;
""",
    checks="""
if (t.is_reset && !t.presence) fail(t, "no presence pulse after reset");
""",
    coverage="""
cp_kind : coverpoint tr.is_reset { bins reset = {1}; bins data = {0}; }
cp_data : coverpoint tr.wdata iff (!tr.is_reset) { bins zero = {8'h00}; bins ones = {8'hFF}; bins other = default; }
""",
    directed="""
t = item(); t.is_reset = 1; send(t);
t = item(); t.wdata = 8'hCC; send(t);   // Skip ROM
t = item(); t.wdata = 8'h44; send(t);   // Convert T
t = item(); t.is_reset = 1; send(t);
t = item(); t.wdata = 8'h33; send(t);   // Read ROM
t = item(); t.wdata = 8'hFF; send(t);   // read slots
t = item(); t.wdata = 8'h00; send(t);
t = item(); t.is_reset = 1; send(t);
""",
)
# SVA: Verilator has no strong(); the bounded response reads the same weak
SPEC["patches"] = {"onewire/sva/onewire_compliance_checker.sv": [(
    "$rose(presence) |-> strong(##[1:16] !presence))",
    "$rose(presence) |-> ##[1:16] !presence)")]}
