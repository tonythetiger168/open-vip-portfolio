# XGMII 32-bit (4-lane) transmit agent (tb/top_tb.sv xgmii_model: txd/txc
# looped back onto rxd/rxc one clock later). Frames are Start (FB, lane 0),
# six preamble bytes, SFD, the MAC frame and Terminate (FD), padded with Idle
# (07); an injected error replaces one frame byte with the Error control FE.
from _lib import ETH_FUNCS

def side(i, d, c, is_out):
    return """  for (int ln = 0; ln < 4; ln++) begin
    bit [7:0] b = vif.mon_cb.{d}[ln*8 +: 8];
    bit k = vif.mon_cb.{c}[ln];
    if (!f{i}) begin
      if (k && b == 8'hFB) begin f{i} = 1; l{i}.delete(); e{i} = 0; end
    end else if (k && b == 8'hFD) begin
      f{i} = 0;
{fin}
    end else begin
      if (k) e{i} = 1;
      l{i}.push_back(b);
    end
  end""".format(i=i, d=d, c=c, fin=("""      if (in_q.size() == 0) `uvm_error("MON", "XGMII frame received that was never sent")
      else begin
        xgmii_transaction t = in_q.pop_front();
        frame(l1, t, 1); t.out_err = e1;
        publish(t);
      end""" if is_out else """      begin
        xgmii_transaction t = xgmii_transaction::type_id::create("t");
        frame(l0, t, 0); t.inject_err = e0;
        in_q.push_back(t);
      end"""))

SPEC = dict(
    vip="XGMII-UVM-VIP", p="xgmii", P="XGMII", dir="xgmii",
    cfg="int unsigned ifg_cols = 3;   // idle columns after each frame",
    fields=[
        ("bit [7:0]", "bytes", "req", "q"),
        ("bit", "preamble_ok", "req", "norand"),
        ("bit", "inject_err", "req"),
        ("bit [7:0]", "out_bytes", "rsp", "q"),
        ("bit", "out_preamble_ok", "rsp"),
        ("bit", "out_err", "rsp"),
        ("bit [6:0]", "plen", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="constraint c_len { plen inside {[46:100]}; inject_err dist { 0 := 5, 1 := 1 }; }",
    tr_functions=ETH_FUNCS + """
function void post_randomize();
  build_frame(plen, seed, 16'(plen));
  preamble_ok = 1;
  if (inject_err) bytes[bytes.size() / 2] = 8'hFE;   // sent as the Error control character
endfunction
""",
    drv_rsp=False,
    drv_desc="Start, preamble, SFD, frame, Terminate and Idle, four lanes per clock",
    drv_idle="vif.drv_cb.txd <= 32'h0707_0707; vif.drv_cb.txc <= 4'hF;",
    drv_item="""
bit [7:0] b[$];
bit k[$];
@(vif.drv_cb);
b.push_back(8'hFB); k.push_back(1);
for (int i = 0; i < 6; i++) begin b.push_back(8'h55); k.push_back(0); end
b.push_back(8'hD5); k.push_back(0);
foreach (t.bytes[i]) begin
  b.push_back(t.bytes[i]);
  k.push_back(t.inject_err && i == t.bytes.size() / 2);
end
b.push_back(8'hFD); k.push_back(1);
while (b.size() % 4) begin b.push_back(8'h07); k.push_back(1); end
for (int i = 0; i < b.size(); i += 4) begin
  vif.drv_cb.txd <= {b[i+3], b[i+2], b[i+1], b[i]};
  vif.drv_cb.txc <= {k[i+3], k[i+2], k[i+1], k[i]};
  @(vif.drv_cb);
end
vif.drv_cb.txd <= 32'h0707_0707;
vif.drv_cb.txc <= 4'hF;
repeat (cfg.ifg_cols) @(vif.drv_cb);
""",
    mon_desc="frames between Start and Terminate on txd/txc, paired with rxd/rxc",
    mon_run="bit [7:0] l0[$], l1[$];\nbit f0 = 0, f1 = 0, e0 = 0, e1 = 0;\nxgmii_transaction in_q[$];\n"
            "forever begin\n  @(vif.mon_cb);\n" + side(1, "rxd", "rxc", True) + "\n" + side(0, "txd", "txc", False) + "\nend",
    mon_tasks="""// strip and check the preamble (six 55 + SFD after Start)
function void frame(bit [7:0] l[$], xgmii_transaction t, bit out);
  bit ok = (l.size() >= 7);
  for (int i = 0; i < 7 && i < l.size(); i++) if (l[i] != ((i == 6) ? 8'hD5 : 8'h55)) ok = 0;
  if (out) begin t.out_preamble_ok = ok; t.out_bytes.delete(); end
  else     begin t.preamble_ok = ok;     t.bytes.delete(); end
  for (int i = 7; i < l.size(); i++)
    if (out) t.out_bytes.push_back(l[i]); else t.bytes.push_back(l[i]);
endfunction""",
    predict="t.out_bytes = t.bytes;\nt.out_preamble_ok = t.preamble_ok;\nt.out_err = t.inject_err;",
    checks="""if (!t.preamble_ok) fail(t, "bad preamble / SFD");
if (!t.inject_err && !t.fcs_ok()) fail(t, "frame check sequence error");""",
    coverage="""cp_len : coverpoint tr.bytes.size() { bins min_ = {[64:70]}; bins mid = {[71:100]}; bins long_ = {[101:$]}; }
cp_err : coverpoint tr.inject_err;
cp_end : coverpoint tr.bytes.size() % 4;   // lane of the Terminate character""",
    directed="""for (int n = 46; n < 50; n++) begin    // Terminate in each lane
  t = item(); t.plen = n; t.seed = n; t.post_randomize(); send(t);
end
t = item(); t.plen = 100; t.seed = 32'h77; t.post_randomize(); send(t);
t = item(); t.plen = 60; t.seed = 32'h78; t.inject_err = 1; t.post_randomize(); send(t);
""",
)

# SVA: on the first clock after reset rxd still holds its reset value while
# $past(txd) is the idle pattern; the loopback check starts one clock later
SPEC["patches"] = {"xgmii/sva/xgmii_compliance_checker.sv": [(
    "disable iff (!rst_n) rxd == $past(txd))",
    "disable iff (!rst_n) $past(rst_n) |-> rxd == $past(txd))")]}
