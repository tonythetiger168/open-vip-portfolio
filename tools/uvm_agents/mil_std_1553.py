# MIL-STD-1553 remote terminal (tb/top_tb.sv mil_std_1553_model: decoded word
# interface; a command word (sync) addressed to RT 5 is answered with the
# status word {RT, 3'b000, 8'h80} eight clocks later).
SPEC = dict(
    vip="MIL_STD_1553-VIP", p="mil_std_1553", P="MIL-STD-1553", dir="mil_std_1553",
    cfg="bit [4:0] rt_address = 5'h05;   // mil_std_1553_model RT_ADDRESS\nint unsigned resp_window = 16;    // clocks to wait for the status word",
    fields=[
        ("bit", "sync", "req"),              # 1: command word, 0: data word
        ("bit [15:0]", "word", "req"),
        ("bit", "responded", "rsp"),
        ("bit [15:0]", "status", "rsp"),
        ("bit [4:0]", "rt_addr", "rsp"),
    ],
    constraints="""
// command word: RT address [15:11], T/R [10], subaddress [9:5], word count [4:0]
constraint c_rt { sync -> word[15:11] dist { 5'h05 := 3, 5'h1F := 1, [0:4] :/ 1, [6:30] :/ 1 }; }
""",
    drv_desc="one word on the decoded bus interface, then the response window",
    drv_idle="vif.drv_cb.busa_rx_data <= '0; vif.drv_cb.busa_rx_sync <= 1'b0; vif.drv_cb.busa_rx_valid <= 1'b0;",
    drv_item="""
@(vif.drv_cb);
vif.drv_cb.busa_rx_data  <= t.word;
vif.drv_cb.busa_rx_sync  <= t.sync;
vif.drv_cb.busa_rx_valid <= 1'b1;
@(vif.drv_cb);
vif.drv_cb.busa_rx_valid <= 1'b0;
vif.drv_cb.busa_rx_sync  <= 1'b0;
t.responded = 0; t.status = 0;
repeat (cfg.resp_window) begin
  @(vif.drv_cb);
  if (vif.drv_cb.busa_tx_valid === 1'b1 && !t.responded) begin
    t.responded = 1;
    t.status = vif.drv_cb.busa_tx_data;
  end
end
t.rt_addr = vif.drv_cb.rt_addr;
""",
    mon_desc="each received word with the terminal's status word (if any) in the response window",
    mon_run="""
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.busa_tx_valid)
    `uvm_error("MON", "MIL-STD-1553 status word outside a response window")
  if (vif.mon_cb.busa_rx_valid) begin
    mil_std_1553_transaction t = mil_std_1553_transaction::type_id::create("t");
    t.sync = vif.mon_cb.busa_rx_sync;
    t.word = vif.mon_cb.busa_rx_data;
    repeat (cfg.resp_window) begin
      @(vif.mon_cb);
      if (vif.mon_cb.busa_rx_valid) `uvm_error("MON", "MIL-STD-1553 word inside the response window")
      if (vif.mon_cb.busa_tx_valid) begin
        if (t.responded) `uvm_error("MON", "MIL-STD-1553 second status word")
        t.responded = 1;
        t.status = vif.mon_cb.busa_tx_data;
        if (!vif.mon_cb.busa_tx_sync) `uvm_error("MON", "MIL-STD-1553 status word without sync")
      end
    end
    t.rt_addr = vif.mon_cb.rt_addr;
    publish(t);
  end
end
""",
    predict="""
// only command words addressed to this terminal are answered (the model has
// no broadcast handling)
t.rt_addr   = cfg.rt_address;
t.responded = t.sync && (t.word[15:11] == cfg.rt_address);
t.status    = t.responded ? {cfg.rt_address, 3'b000, 8'h80} : 16'h0;
""",
    checks="""
if (t.responded && t.status[15:11] != t.rt_addr) fail(t, "status word carries another RT address");
""",
    coverage="""
cp_kind : coverpoint tr.sync { bins data = {0}; bins command = {1}; }
cp_rt   : coverpoint tr.word[15:11] iff (tr.sync) { bins mine = {5'h05}; bins bcast = {5'h1F}; bins other = default; }
cp_tr   : coverpoint tr.word[10] iff (tr.sync);
cp_resp : coverpoint tr.responded;
""",
    directed="""
t = item(); t.sync = 1; t.word = {5'h05, 1'b1, 5'h01, 5'd4}; send(t);   // transmit command to RT 5
t = item(); t.sync = 1; t.word = {5'h05, 1'b0, 5'h02, 5'd1}; send(t);   // receive command to RT 5
t = item(); t.sync = 0; t.word = 16'h2BAD; send(t);                     // its data word: no response
t = item(); t.sync = 1; t.word = {5'h04, 1'b1, 5'h01, 5'd1}; send(t);   // another terminal
t = item(); t.sync = 1; t.word = {5'h1F, 1'b0, 5'h03, 5'd2}; send(t);   // broadcast
t = item(); t.sync = 0; t.word = {5'h05, 11'h0}; send(t);               // data word with RT 5 bits
""",
)
