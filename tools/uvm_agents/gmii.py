# GMII (IEEE 802.3 clause 35) PHY-side agent driving a MAC receiver: rxd /
# rx_dv / rx_er, one byte per clock. Frames with any preamble length (1..7
# bytes of 55, shrinkage allowed) and SFD, rx_er inside the frame, carrier
# extension (rx_dv 0, rx_er 1, rxd 0F) after it, false carrier (rx_dv 0,
# rx_er 1, rxd 0E). tb/top_tb.sv gmii_model: GMII front end + the MAC
# receive check of _mii.py.
from _mii import build_spec

P, p = "GMII", "gmii"

FRONT = """
  logic inf, sfd, fc_q;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      inf <= 1'b0; sfd <= 1'b0; f_pre <= 1'b0; f_code <= 1'b0; fcnt <= 16'd0; fe_end <= 1'b0;
      false_carrier <= 1'b0; fc_q <= 1'b0;
    end else begin
      fe_end <= 1'b0;
      false_carrier <= 1'b0;
      // false carrier: rx_dv 0, rx_er 1, rxd 0E (one pulse per event)
      fc_q <= !rx_dv && rx_er && rxd == 8'h0E;
      if (!rx_dv && rx_er && rxd == 8'h0E && !fc_q) false_carrier <= 1'b1;
      if (rx_dv) begin
        if (!inf) begin
          inf <= 1'b1; fcnt <= 16'd0; f_code <= rx_er;
          sfd <= (rxd == 8'hD5); f_pre <= (rxd != 8'h55 && rxd != 8'hD5);
        end else begin
          if (rx_er) f_code <= 1'b1;
          if (!sfd) begin
            if (rxd == 8'hD5) sfd <= 1'b1;
            else if (rxd != 8'h55) f_pre <= 1'b1;
          end else begin
            if (fcnt < 16'd2048) fb[fcnt] <= rxd;
            fcnt <= fcnt + 16'd1;
          end
        end
      end else if (inf) begin
        // end of frame (carrier extension after it is ignored)
        inf <= 1'b0; fe_end <= 1'b1;
        if (!sfd) f_pre <= 1'b1;
      end
    end
  end
"""

DRV_ITEM = """
bit [7:0] ln[$];
int ci = -1;
@(vif.drv_cb);
repeat (t.gap) @(vif.drv_cb);
t.pre_bad = 0; t.code_err = 0;
if (t.kind == GMII_FC) begin
  t.bytes.delete(); t.inj = GMII_X_NONE;
  repeat (2 + t.cext) begin
    vif.drv_cb.rxd <= 8'h0E; vif.drv_cb.rx_dv <= 1'b0; vif.drv_cb.rx_er <= 1'b1; @(vif.drv_cb);
  end
  vif.drv_cb.rx_er <= 1'b0; vif.drv_cb.rxd <= 8'h00;
  repeat (cfg.ifg) @(vif.drv_cb);
  return;
end
t.build(cfg.station);
for (int i = 0; i < t.pre_n; i++) ln.push_back(8'h55);
if (t.inj == GMII_X_PRE) begin ln[0] = 8'h5D; t.pre_bad = 1; end
if (t.inj != GMII_X_NOSFD) ln.push_back(8'hD5);
else begin
  // no SFD: the receiver keeps hunting and only stores what follows a D5 in the frame
  int k = -1;
  t.pre_bad = 1;
  foreach (t.bytes[i]) if (k < 0 && t.bytes[i] == 8'hD5) k = i;
  foreach (t.bytes[i]) ln.push_back(t.bytes[i]);
  if (k < 0) t.bytes.delete(); else t.bytes = t.bytes[k + 1 : $];
end
if (t.inj != GMII_X_NOSFD) foreach (t.bytes[i]) ln.push_back(t.bytes[i]);
if (t.inj == GMII_X_CODE) begin ci = t.pre_n + 1 + t.bytes.size() / 2; t.code_err = 1; end
foreach (ln[i]) begin
  vif.drv_cb.rxd <= ln[i]; vif.drv_cb.rx_dv <= 1'b1; vif.drv_cb.rx_er <= (i == ci);
  @(vif.drv_cb);
end
vif.drv_cb.rx_dv <= 1'b0; vif.drv_cb.rx_er <= 1'b0; vif.drv_cb.rxd <= 8'h00;
if (t.cext != 0) begin
  repeat (t.cext) begin vif.drv_cb.rx_er <= 1'b1; vif.drv_cb.rxd <= 8'h0F; @(vif.drv_cb); end
  vif.drv_cb.rx_er <= 1'b0; vif.drv_cb.rxd <= 8'h00;
end
repeat (cfg.ifg) @(vif.drv_cb);
"""

MON_RUN = """
bit [7:0] b[$];
bit inf = 0, sfd = 0, pb = 0, ce = 0, fcq = 0;
gmii_transaction pend[$];
gmii_transaction fct;
forever begin
  bit [7:0] d;
  bit dv, er, fc;
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin inf = 0; fcq = 0; pend.delete(); fct = null; continue; end
  // DUT results for earlier bus activity
  if (fct != null) begin fct.fc_out = vif.mon_cb.false_carrier; publish(fct); fct = null; end
  else if (vif.mon_cb.false_carrier) `uvm_error("MON", "GMII false_carrier without a false carrier on the bus")
  if (vif.mon_cb.fr_done) begin
    if (pend.size() == 0) `uvm_error("MON", "GMII fr_done without a frame")
    else begin
      gmii_transaction t = pend.pop_front();
      t.status = vif.mon_cb.fr_status; t.len = vif.mon_cb.fr_len; t.etype = vif.mon_cb.fr_etype;
      t.cast = vif.mon_cb.fr_cast; t.vlan = vif.mon_cb.fr_vlan; t.pause = vif.mon_cb.pause_valid;
      t.quanta = t.pause ? vif.mon_cb.pause_quanta : 16'h0;
      publish(t);
    end
  end
  // the bus
  d = vif.mon_cb.rxd; dv = vif.mon_cb.rx_dv; er = vif.mon_cb.rx_er;
  if (dv) begin
    fcq = 0;
    if (!inf) begin inf = 1; b.delete(); sfd = (d == 8'hD5); pb = (d != 8'h55 && d != 8'hD5); ce = er; end
    else begin
      if (er) ce = 1;
      if (!sfd) begin if (d == 8'hD5) sfd = 1; else if (d != 8'h55) pb = 1; end
      else b.push_back(d);
    end
  end else begin
    if (inf) begin
      gmii_transaction t = gmii_transaction::type_id::create("t");
      inf = 0; t.kind = GMII_FRAME; t.bytes = b; t.pre_bad = pb || !sfd; t.code_err = ce;
      pend.push_back(t);
    end
    fc = er && d == 8'h0E;
    if (fc && !fcq) begin fct = gmii_transaction::type_id::create("fc"); fct.kind = GMII_FC; end
    fcq = fc;
  end
end
"""

SVA = """
assert property (@(posedge clk) disable iff (!rst_n) false_carrier |=> !false_carrier)
  else $error("GMII: false_carrier longer than one clock");
assert property (@(posedge clk) disable iff (!rst_n) false_carrier |-> $past(!rx_dv && rx_er && rxd == 8'h0E))
  else $error("GMII: false_carrier without 0E / rx_er");
// a frame result follows the end of rx_dv by two clocks
assert property (@(posedge clk) disable iff (!rst_n) fr_done |-> $past(rx_dv, 3) && !$past(rx_dv, 2))
  else $error("GMII: fr_done not two clocks after rx_dv fell");
cover property (@(posedge clk) disable iff (!rst_n) false_carrier);
cover property (@(posedge clk) disable iff (!rst_n) !rx_dv && rx_er && rxd == 8'h0F);
"""

SMOKE_BUS = """
int nfc = 0;
always @(negedge clk) if (false_carrier) nfc++;

// pre_n preamble bytes (index bad_pre sent as 5D), SFD unless nosfd, then fr;
// rx_er on fr[code_at] (-2: on the SFD, -3: on the first preamble byte)
task automatic send(input int pre_n, input int bad_pre, input bit nosfd, input int code_at);
  for (int i = 0; i < pre_n; i++) begin
    @(negedge clk); rx_dv = 1; rxd = (i == bad_pre) ? 8'h5D : 8'h55; rx_er = (i == 0 && code_at == -3);
  end
  if (!nosfd) begin @(negedge clk); rx_dv = 1; rxd = 8'hD5; rx_er = (code_at == -2); end
  for (int i = 0; i < fl; i++) begin @(negedge clk); rx_dv = 1; rxd = fr[i]; rx_er = (i == code_at); end
  @(negedge clk); rx_dv = 0; rx_er = 0; rxd = 0;
endtask

task automatic rxs(input logic [2:0] s, input int pre_n, input int bad_pre, input bit nosfd, input int code_at,
                   input string msg);
  n0 = ndone;
  send(pre_n, bad_pre, nosfd, code_at);
  idle(4);
  chk(ndone == n0 + 1 && lst == s, $sformatf("%s: status %0d (got %0d, %0d results)", msg, s, lst, ndone - n0));
endtask
"""

SMOKE_TESTS = """
  // preamble and SFD
  mk(ST, 16'h0800, 46, 0);
  rxs(0, 1, -1, 0, -1, "one preamble byte");
  chk(llen == 64, "length after a short preamble");
  rxs(0, 0, -1, 0, -1, "SFD without preamble");
  rxs(1, 7, 3, 0, -1, "preamble byte 3 is 5D");
  rxs(1, 7, 0, 0, -1, "first preamble byte is 5D");
  rxs(1, 7, 6, 0, -1, "last preamble byte is 5D");
  rxs(1, 7, -1, 1, -1, "no SFD");
  chk(llen == 64 - 45, $sformatf("no SFD: bytes after the first D5 in the data (%0d)", llen));
  rxs(1, 0, -1, 1, -1, "no preamble and no SFD");
  // rx_er
  mk(ST, 16'h0800, 46, 0);
  rxs(2, 7, -1, 0, 10, "rx_er on byte 10");
  rxs(2, 7, -1, 0, 0, "rx_er on the first byte");
  rxs(2, 7, -1, 0, 63, "rx_er on the last byte");
  rxs(2, 7, -1, 0, -2, "rx_er on the SFD");
  rxs(2, 7, -1, 0, -3, "rx_er on the first preamble byte");
  rxs(1, 7, 2, 0, 5, "preamble error before code error");
  mk(ST, 16'h0800, 10, 0);
  rxs(2, 7, -1, 0, 5, "code error before runt");
  // false carrier and carrier extension
  rx_er = 1; rxd = 8'h0E; idle(3); rx_er = 0; rxd = 0; idle(2);
  chk(nfc == 1 && ndone == n0 + 1, $sformatf("false carrier: one pulse, no frame (%0d)", nfc));
  rx_er = 1; rxd = 8'h0E; idle(1); rx_er = 0; idle(1); rx_er = 1; idle(1); rx_er = 0; rxd = 0; idle(2);
  chk(nfc == 3, $sformatf("two false-carrier events (%0d)", nfc));
  rx_er = 1; rxd = 8'h0F; idle(3); rx_er = 0; rxd = 8'h0E; idle(3); rxd = 0; idle(2);
  chk(nfc == 3, "carrier extension and 0E without rx_er: no false carrier");
  rx_er = 1; rxd = 8'h1E; idle(2); rxd = 8'h0C; idle(2); rx_er = 0; rxd = 0; idle(2);
  chk(nfc == 3, "1E and 0C with rx_er: no false carrier");
  mk(ST, 16'h0800, 46, 0);
  n0 = ndone;
  send(7, -1, 0, -1); rx_er = 1; rxd = 8'h0F; idle(6); rx_er = 0; rxd = 0; idle(3);
  chk(ndone == n0 + 1 && lst == 0 && nfc == 3, "frame followed by carrier extension");
  rx_dv = 1; rx_er = 1; rxd = 8'h0E; idle(1); rx_dv = 0; rx_er = 0; rxd = 0; idle(4);
  chk(nfc == 3 && lst == 1, "0E with rx_dv is data, not false carrier");
  // back-to-back frames, one idle clock apart
  n0 = ndone;
  send(7, -1, 0, -1); send(7, -1, 0, -1); idle(4);
  chk(ndone == n0 + 2 && lst == 0, "two frames one clock apart");
  // reset inside a frame
  n0 = ndone;
  for (int i = 0; i < 20; i++) begin @(negedge clk); rx_dv = 1; rxd = (i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : 8'h33; end
  rst_n = 0; idle(2); rx_dv = 0; rxd = 0; rst_n = 1; idle(2);
  chk(ndone == n0 && !fr_done, "reset drops the frame in progress");
  rx(0, "frame after the reset");
"""

SPEC = build_spec(
    vip="GMII-UVM-VIP", p=p, P=P,
    desc="GMII (IEEE 802.3 clause 35) VIP: PHY-side agent driving a MAC receiver with frames, preamble "
         "shrinkage, rx_er code errors, carrier extension and false carrier; the MAC model checks FCS, "
         "length limits, the length field, address filtering and PAUSE frames.",
    about="""
The agent plays the PHY on the GMII receive pins (rxd / rx_dv / rx_er, one
byte per 125 MHz clock). An item is a frame or a false-carrier event. Frames
are built from knobs (destination: the station, another station, multicast,
broadcast, MAC PAUSE; 802.1Q tag; length or type field; payload length) and
can be broken on purpose: a bad preamble byte, no SFD, rx_er inside the
frame, a bad FCS, a runt, an oversize frame or a length field that does not
match the data. Frames can be followed by carrier extension.

The monitor rebuilds every frame from the pins and pairs it with the MAC's
result; the scoreboard runs the IEEE 802.3 receive checks on the observed
bytes and predicts the status, length / type, destination class, VLAN tag and
PAUSE quanta, and a false_carrier pulse for each false-carrier event.""",
    ports=[("in", "logic [7:0]", "rxd"), ("in", "logic", "rx_dv"), ("in", "logic", "rx_er")],
    bus_fields=[("bit", "fc_out", "rsp"), ("bit [2:0]", "cext", "info", "rand")],
    kinds=[("GMII_FRAME", 12), ("GMII_FC", 1)],
    cfg_extra="int unsigned ifg = 12;   // idle clocks after each item",
    drv_idle="""vif.drv_cb.rxd <= 8'h00; vif.drv_cb.rx_dv <= 1'b0; vif.drv_cb.rx_er <= 1'b0;
vif.drv_cb.station <= cfg.station; vif.drv_cb.promisc <= cfg.promisc; vif.drv_cb.mcast_en <= cfg.mcast_en;""",
    drv_item=DRV_ITEM, drv_members="", drv_tasks="",
    mon_run=MON_RUN, mon_tasks="",
    extra_predict="t.fc_out = (t.kind == GMII_FC);\n",
    extra_cov="cp_fc   : coverpoint tr.fc_out iff (tr.kind == GMII_FC) { bins seen = {1}; }\n",
    directed="""
t = item(); t.kind = GMII_FC; t.cext = 0; send(t);
t = item(); t.kind = GMII_FRAME; t.inj = GMII_X_NONE; t.dak = GMII_D_SELF; t.pre_n = 1; t.cext = 4; send(t);
t = item(); t.kind = GMII_FC; t.cext = 3; send(t);
""",
    model_front=FRONT,
    model_ports=[("out", "logic", "false_carrier")],
    sva=SVA, smoke_bus=SMOKE_BUS, smoke_tests=SMOKE_TESTS,
)
