# SAE J2716 SENT receiver test agent (tb/top_tb.sv sent_model: the low time
# of each sens_out pulse, 3..18 clocks, is reported as nibble = low - 3 with a
# one-clock nibble_valid at the rising edge; longer pulses are ignored).
SPEC = dict(
    vip="SENT-VIP", p="sent", P="SENT", dir="sent",
    cfg="int unsigned sync_low = 30;   // sync/calibration pulse (ignored by the model)\nint unsigned high_clks = 4;   // high time after every pulse",
    fields=[
        ("bit [3:0]", "nib", "req", "q"),       # status, 6 data nibbles, CRC on the line
        ("bit [3:0]", "dut_nib", "rsp", "q"),   # nibbles reported by the DUT
        ("bit [3:0]", "status", "info", "rand"),
        ("bit [23:0]", "data", "info", "rand"),
    ],
    tr_functions="""
// J2716 4-bit CRC (x^4+x^3+x^2+1, seed 5) over the data nibbles, with the
// recommended extra zero nibble
static function bit [3:0] crc4(bit [3:0] d[$]);
  bit [3:0] tbl [16] = '{0, 13, 7, 10, 14, 3, 9, 4, 1, 12, 6, 11, 15, 2, 8, 5};
  bit [3:0] c = 4'd5;
  foreach (d[i]) c = tbl[c] ^ d[i];
  return tbl[c];
endfunction

function void build();
  bit [3:0] d[$];
  for (int i = 5; i >= 0; i--) d.push_back(data[i*4 +: 4]);
  nib.delete();
  nib.push_back(status);
  foreach (d[i]) nib.push_back(d[i]);
  nib.push_back(crc4(d));
endfunction

function void post_randomize(); build(); endfunction
""",
    drv_rsp=False,
    drv_desc="sync pulse, then status, six data and the CRC nibble as low pulses of nibble + 3 clocks",
    drv_idle="vif.drv_cb.sens_out <= 1'b1;",
    drv_item="""
@(vif.drv_cb);
pulse(cfg.sync_low);
foreach (t.nib[i]) pulse(t.nib[i] + 3);
repeat (8) @(vif.drv_cb);              // pause before the next frame
""",
    drv_tasks="""
task pulse(int unsigned low);
  vif.drv_cb.sens_out <= 1'b0;
  repeat (low) @(vif.drv_cb);
  vif.drv_cb.sens_out <= 1'b1;
  repeat (cfg.high_clks) @(vif.drv_cb);
endtask
""",
    mon_desc="decodes pulse low times on sens_out into frames, with the DUT's nibble reports",
    mon_run="""
sent_transaction t;
int unsigned low = 0;
bit so_d = 1;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.nibble_valid) begin
    if (t == null) `uvm_error("MON", "SENT nibble_valid outside a frame")
    else t.dut_nib.push_back(vif.mon_cb.nibble);
  end
  if (!vif.mon_cb.sens_out) low++;
  else if (!so_d) begin                      // rising edge: end of a pulse
    if (low > 27) begin                      // sync pulse: new frame
      if (t != null) `uvm_error("MON", "SENT frame cut short by a sync pulse")
      t = sent_transaction::type_id::create("t");
    end else if (t != null) t.nib.push_back(low - 3);
    low = 0;
  end
  so_d = vif.mon_cb.sens_out;
  if (t != null && t.nib.size() == 8 && t.dut_nib.size() == 8) begin
    t.status = t.nib[0];
    for (int i = 0; i < 6; i++) t.data[(5 - i) * 4 +: 4] = t.nib[i + 1];
    publish(t);
    t = null;
  end
end
""",
    predict="""
t.dut_nib = t.nib;
""",
    checks="""
bit [3:0] d[$];
if (t.nib.size() != 8) fail(t, "frame is not 8 nibbles");
else begin
  for (int i = 1; i <= 6; i++) d.push_back(t.nib[i]);
  if (sent_transaction::crc4(d) != t.nib[7]) fail(t, "CRC nibble does not match the data");
end
""",
    coverage="""
cp_status : coverpoint tr.status;
cp_d0     : coverpoint tr.data[23:20];
""",
    directed="""
t = item(); t.status = 4'h0; t.data = 24'h000000; t.build(); send(t);
t = item(); t.status = 4'hF; t.data = 24'hFFFFFF; t.build(); send(t);
t = item(); t.status = 4'h5; t.data = 24'h0123AB; t.build(); send(t);
t = item(); t.status = 4'hA; t.data = 24'hFEDCBA; t.build(); send(t);
""",
)
