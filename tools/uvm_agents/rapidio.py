# RapidIO packet port (tb/top_tb.sv rapidio_model: in_* words registered onto
# out_* one clock later, start-of-packet and priority carried along).
from _lib import fill_fn

SPEC = dict(
    vip="RapidIO-VIP", p="rapidio", P="RapidIO", dir="rapidio",
    fields=[
        ("bit [2:0]", "prio", "req"),
        ("bit [31:0]", "words", "req", "q"),
        ("bit [2:0]", "out_prio", "rsp"),
        ("bit [31:0]", "out_words", "rsp", "q"),
        ("bit", "out_soc_ok", "rsp"),    # out_soc on the first word only
        ("bit [4:0]", "nwords", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nwords inside {[1:17]}; }   // header + up to 256 bytes / 16 words
constraint c_prio { prio inside {[0:3]}; }      // physical-layer priorities 0..3
""",
    tr_functions=fill_fn("words", 32, "n") + """

function void post_randomize();
  fill_words(nwords);
endfunction
""",
    drv_rsp=False,
    drv_desc="one packet per item: in_soc on the first word, in_valid for every word, then idle",
    drv_idle="""
vif.drv_cb.in_valid <= 1'b0; vif.drv_cb.in_soc <= 1'b0;
vif.drv_cb.in_data <= '0; vif.drv_cb.in_prio <= '0;
""",
    drv_item="""
foreach (t.words[i]) begin
  @(vif.drv_cb);
  vif.drv_cb.in_valid <= 1'b1;
  vif.drv_cb.in_soc   <= (i == 0);
  vif.drv_cb.in_data  <= t.words[i];
  vif.drv_cb.in_prio  <= t.prio;
end
@(vif.drv_cb);
vif.drv_cb.in_valid <= 1'b0;
vif.drv_cb.in_soc   <= 1'b0;
@(vif.drv_cb);
""",
    mon_desc="input packets (in_soc .. idle) paired in order with output packets",
    mon_run="""
rapidio_transaction in_q[$], cur_in, cur_out;
forever begin
  @(vif.mon_cb);
  // egress first: the output side lags by one clock
  if (vif.mon_cb.out_valid) begin
    if (vif.mon_cb.out_soc || cur_out == null) begin
      if (cur_out != null) begin publish(cur_out); cur_out = null; end
      if (in_q.size() == 0) `uvm_error("MON", "RapidIO output word with no input packet")
      else begin
        cur_out = in_q.pop_front();
        cur_out.out_prio = vif.mon_cb.out_prio;
        cur_out.out_soc_ok = vif.mon_cb.out_soc;
      end
    end
    if (cur_out != null) begin
      cur_out.out_words.push_back(vif.mon_cb.out_data);
      if (vif.mon_cb.out_prio != cur_out.out_prio) cur_out.out_soc_ok = 0;
    end
  end else if (cur_out != null) begin
    publish(cur_out);
    cur_out = null;
  end
  if (vif.mon_cb.in_valid) begin
    if (vif.mon_cb.in_soc || cur_in == null) begin
      cur_in = rapidio_transaction::type_id::create("t");
      cur_in.prio = vif.mon_cb.in_prio;
      in_q.push_back(cur_in);
    end
    cur_in.words.push_back(vif.mon_cb.in_data);
  end else
    cur_in = null;
end
""",
    predict="""
t.out_words  = t.words;
t.out_prio   = t.prio;
t.out_soc_ok = 1;
""",
    checks="""
if (t.words.size() == 0) fail(t, "empty packet");
""",
    coverage="""
cp_prio : coverpoint tr.prio { bins p[] = {[0:3]}; }
cp_len  : coverpoint tr.words.size() { bins one = {1}; bins short_ = {[2:8]}; bins long_ = {[9:17]}; }
""",
    directed="""
for (int p = 0; p < 4; p++) begin
  t = item(); t.prio = p; t.seed = 32'h900 + p; t.fill_words(p == 3 ? 17 : p + 1); send(t);
end
t = item(); t.prio = 2; t.words = '{32'h0, 32'hFFFF_FFFF, 32'h8000_0001}; send(t);
""",
)
