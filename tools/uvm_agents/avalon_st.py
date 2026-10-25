# Avalon-ST source + sink (tb/top_tb.sv avalon_st_model: registered stage
# with a one-beat skid buffer, readyLatency 0 on both sides: asi_ready high
# out of reset, every accepted beat appears on aso_* one clock later and is
# held while aso_ready is low; asi_ready drops while the skid buffer is full).
from _lib import wait_cb, fill_fn

SPEC = dict(
    vip="Avalon_ST-UVM-VIP", p="avalon_st", P="Avalon-ST", dir="avalon_st",
    cfg="int unsigned aso_ready_pct = 70;   // sink ready probability (back-pressure)",
    fields=[
        ("bit [31:0]", "data", "req", "q"),       # packet beats into asi_*
        ("bit [31:0]", "out_data", "rsp", "q"),   # packet beats seen on aso_*
        ("bit", "out_framing_ok", "rsp"),        # SOP on the first beat only, EOP on the last only
        ("bit [3:0]", "nbeats", "info", "rand"),
        ("bit [1:0]", "gap", "info", "rand"),     # idle clocks between beats
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_len { nbeats inside {[1:12]}; gap dist { 0 := 3, [1:3] :/ 1 }; }
""",
    tr_functions=fill_fn("data", 32, "nb") + """

function void post_randomize();
  fill_data(nbeats);
endfunction
""",
    drv_rsp=False,
    drv_desc="one packet per item, beat by beat on asi_valid/asi_ready; random aso_ready",
    drv_idle="""
vif.drv_cb.asi_valid <= 1'b0; vif.drv_cb.asi_data <= '0;
vif.drv_cb.asi_startofpacket <= 1'b0; vif.drv_cb.asi_endofpacket <= 1'b0;
vif.drv_cb.aso_ready <= 1'b1;
""",
    drv_bg="""
forever begin
  @(vif.drv_cb);
  vif.drv_cb.aso_ready <= ($urandom_range(99) < cfg.aso_ready_pct);
end
""",
    drv_item="""
@(vif.drv_cb);
foreach (t.data[i]) begin
  vif.drv_cb.asi_valid <= 1'b1;
  vif.drv_cb.asi_data  <= t.data[i];
  vif.drv_cb.asi_startofpacket <= (i == 0);
  vif.drv_cb.asi_endofpacket   <= (i == t.data.size() - 1);
""" + "\n".join("  " + l for l in wait_cb("vif.drv_cb.asi_ready === 1'b1", "Avalon-ST asi_ready").splitlines()) + """
  if (t.gap != 0 && i != t.data.size() - 1) begin
    vif.drv_cb.asi_valid <= 1'b0;
    repeat (t.gap - 1) @(vif.drv_cb);
    @(vif.drv_cb);
  end
end
vif.drv_cb.asi_valid <= 1'b0;
vif.drv_cb.asi_startofpacket <= 1'b0;
vif.drv_cb.asi_endofpacket   <= 1'b0;
""",
    mon_desc="input packets from asi_*, paired in order with output packets on aso_*",
    mon_run="""
// in_q holds input packets in arrival order (including the one still being
// received: the registered output starts one clock after its first beat)
avalon_st_transaction in_q[$], cur_in, cur_out;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.asi_valid && vif.mon_cb.asi_ready) begin
    if (vif.mon_cb.asi_startofpacket || cur_in == null) begin
      cur_in = avalon_st_transaction::type_id::create("t");
      in_q.push_back(cur_in);
    end
    cur_in.data.push_back(vif.mon_cb.asi_data);
    if (vif.mon_cb.asi_endofpacket) cur_in = null;
  end
  if (vif.mon_cb.aso_valid && vif.mon_cb.aso_ready) begin
    if (cur_out == null) begin
      if (in_q.size() == 0) begin
        `uvm_error("MON", "Avalon-ST output beat with no input packet pending")
        continue;
      end
      cur_out = in_q.pop_front();
      cur_out.out_framing_ok = vif.mon_cb.aso_startofpacket;
    end else if (vif.mon_cb.aso_startofpacket) cur_out.out_framing_ok = 0;
    cur_out.out_data.push_back(vif.mon_cb.aso_data);
    if (vif.mon_cb.aso_endofpacket) begin
      if (cur_out.out_data.size() != cur_out.data.size()) cur_out.out_framing_ok = 0;
      publish(cur_out);
      cur_out = null;
    end
  end
end
""",
    predict="""
t.out_data = t.data;
t.out_framing_ok = 1;
""",
    checks="""
if (t.data.size() == 0) fail(t, "empty packet");
""",
    coverage="""
cp_len : coverpoint tr.data.size() { bins single = {1}; bins short_ = {[2:4]}; bins long_ = {[5:12]}; }
""",
    directed="""
t = item(); t.seed = 32'h1; t.fill_data(1); send(t);                // single-beat packet (SOP+EOP)
t = item(); t.seed = 32'h2; t.fill_data(12); send(t);               // long packet, back-to-back beats
t = item(); t.seed = 32'h3; t.gap = 3; t.fill_data(5); send(t);     // idle clocks inside the packet
t = item(); t.data = '{32'h0, 32'hFFFF_FFFF}; send(t);
for (int i = 0; i < 4; i++) begin t = item(); t.seed = 100 + i; t.fill_data(2); send(t); end
""",
)

# SVA: "SOP inside packet" fired on a legal back-to-back packet (EOP beat
# followed by the next SOP); track the packet state from accepted beats.
SPEC["patches"] = {"avalon_st/sva/avalon_st_compliance_checker.sv": [(
    "  assert property (@(posedge clk) disable iff (!rst_n) aso_valid && !aso_startofpacket |=> !aso_startofpacket || !aso_valid || $fell(aso_valid))\n",
    "  logic in_pkt;\n"
    "  always_ff @(posedge clk or negedge rst_n)\n"
    "    if (!rst_n) in_pkt <= 1'b0;\n"
    "    else if (aso_valid && aso_ready) in_pkt <= !aso_endofpacket;\n"
    "  assert property (@(posedge clk) disable iff (!rst_n) aso_valid && aso_ready && in_pkt |-> !aso_startofpacket)\n")]}
