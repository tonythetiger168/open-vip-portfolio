# IO-Link (SDCI) UART character agent (tb/top_tb.sv io_link_model: 8N1
# characters of BIT_CLKS = 4 clocks per bit; a character on rx is reported on
# rx_data/rx_valid, tx_req makes the model send tx_data on tx and pulse tx_cnf).
SPEC = dict(
    vip="IO_Link-VIP", p="io_link", P="IO-Link", dir="io_link",
    cfg="int unsigned bit_clks = 4;   // io_link_model BIT_CLKS",
    fields=[
        ("bit", "dut_tx", "req"),          # 0: agent sends a character on rx, 1: tx_req, DUT sends on tx
        ("bit [7:0]", "data", "req"),
        ("bit [7:0]", "rx_data", "rsp"),   # dut_tx=0: rx_data reported by the DUT; 1: character decoded from tx
        ("bit", "cnf", "rsp"),             # tx_cnf after the DUT's character
        ("bit", "framing_ok", "rsp"),      # start bit low and stop bit high on the line
    ],
    drv_rsp=False,
    drv_desc="UART character on rx (start, 8 data LSB first, stop), or a tx_req for the DUT to send",
    drv_idle="vif.drv_cb.rx <= 1'b1; vif.drv_cb.tx_req <= 1'b0; vif.drv_cb.tx_data <= '0;",
    drv_item="""
@(vif.drv_cb);
if (!t.dut_tx) begin
  send_bit(1'b0);
  for (int i = 0; i < 8; i++) send_bit(t.data[i]);
  send_bit(1'b1);
  send_bit(1'b1);                       // one idle bit time
end else begin
  vif.drv_cb.tx_req  <= 1'b1;
  vif.drv_cb.tx_data <= t.data;
  @(vif.drv_cb);
  vif.drv_cb.tx_req  <= 1'b0;
  begin
    int unsigned to = 0;
    do begin @(vif.drv_cb); to++; end while (vif.drv_cb.tx_cnf !== 1'b1 && to < cfg.timeout_cycles);
    if (vif.drv_cb.tx_cnf !== 1'b1) `uvm_error("TIMEOUT", "IO-Link: no tx_cnf")
  end
  // idle for two bit times: the monitor watches tx for 12 bit times from
  // the start bit, so an earlier tx_req would be missed
  repeat (2 * cfg.bit_clks) @(vif.drv_cb);
end
""",
    drv_tasks="""
task send_bit(bit b);
  vif.drv_cb.rx <= b;
  repeat (cfg.bit_clks) @(vif.drv_cb);
endtask
""",
    mon_desc="decodes characters on rx and tx (mid-bit sampling) with rx_valid / tx_cnf",
    mon_run="""
fork
  forever begin                          // agent -> DUT on rx
    @(vif.mon_cb);
    if (vif.mon_cb.rx === 1'b0) begin
      io_link_transaction t = io_link_transaction::type_id::create("t");
      bit got = 0;
      t.dut_tx = 0;
      decode_char(0, t, got);
      if (!got) `uvm_error("MON", "IO-Link: character on rx not reported by rx_valid")
      publish(t);
    end
  end
  forever begin                          // DUT -> agent on tx
    @(vif.mon_cb);
    if (vif.mon_cb.tx_req === 1'b1) begin
      io_link_transaction t = io_link_transaction::type_id::create("t");
      bit got = 0;
      int unsigned to = 0;
      t.dut_tx = 1;
      t.data = vif.mon_cb.tx_data;
      do begin @(vif.mon_cb); to++; end while (vif.mon_cb.tx !== 1'b0 && to < 8);
      if (vif.mon_cb.tx !== 1'b0) `uvm_error("MON", "IO-Link: tx_req without a start bit on tx")
      decode_char(1, t, got);
      publish(t);
    end
  end
join
""",
    mon_tasks="""
// called on the first clock of the start bit; samples each bit in its middle
// and watches rx_valid (line rx) or tx_cnf (line tx) until the stop bit ends
task decode_char(bit line_tx, io_link_transaction t, output bit got);
  int unsigned n = cfg.bit_clks;
  bit v;
  got = 0;
  t.framing_ok = 1;
  for (int c = 1; c < 10 * n + (line_tx ? 2 * n : 0); c++) begin
    @(vif.mon_cb);
    v = line_tx ? vif.mon_cb.tx : vif.mon_cb.rx;
    if (c == n / 2 && v != 1'b0) t.framing_ok = 0;                  // start bit
    if (c % n == n / 2 && c / n >= 1 && c / n <= 8) begin
      if (line_tx) t.rx_data[c / n - 1] = v; else t.data[c / n - 1] = v;
    end
    if (c == 9 * n + n / 2 && v != 1'b1) t.framing_ok = 0;          // stop bit
    if (!line_tx && vif.mon_cb.rx_valid) begin got = 1; t.rx_data = vif.mon_cb.rx_data; end
    if (line_tx && vif.mon_cb.tx_cnf) begin got = 1; t.cnf = 1; end
  end
endtask
""",
    predict="""
t.rx_data = t.data;      // both directions carry the character unchanged
t.cnf = t.dut_tx;
t.framing_ok = 1;
""",
    checks="""
if (!t.framing_ok) fail(t, "UART framing error (start/stop bit)");
""",
    coverage="""
cp_dir  : coverpoint tr.dut_tx { bins to_dut = {0}; bins from_dut = {1}; }
cp_data : coverpoint tr.data { bins zero = {8'h00}; bins ones = {8'hFF}; bins other = default; }
x_dir_data : cross cp_dir, cp_data;
""",
    directed="""
bit [7:0] chars [5] = '{8'h00, 8'hFF, 8'h55, 8'hA5, 8'h81};
foreach (chars[i]) begin
  t = item(); t.dut_tx = 0; t.data = chars[i]; send(t);
  t = item(); t.dut_tx = 1; t.data = chars[i]; send(t);
end
""",
)

# SVA: the line idles high, so tx resets to 1, not 0
SPEC["patches"] = {"io_link/sva/io_link_compliance_checker.sv": [(
    "disable iff (1'b0) !rst_n |-> tx == '0)",
    "disable iff (1'b0) !rst_n |=> tx == 1'b1)   // idle high in reset")]}
