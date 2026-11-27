# RGMII (Reduced GMII v2.0) PHY-side agent driving a MAC receiver: rxd[3:0]
# and rx_ctl on both clock edges. Rising edge: rxd = byte[3:0], rx_ctl =
# RX_DV; falling edge: rxd = byte[7:4], rx_ctl = RX_DV xor RX_ER. Between
# frames (RX_DV = RX_ER = 0) rxd carries the in-band status {duplex,
# speed[1:0], link} on both edges. False carrier: RX_DV 0, RX_ER 1, byte 0E.
# tb/top_tb.sv rgmii_model: RGMII front end + the MAC receive check of _mii.py.
from _mii import build_spec

P, p = "RGMII", "rgmii"

FRONT = """
  // rising edge: low nibble and RX_DV; falling edge: high nibble and RX_DV ^ RX_ER
  logic [3:0] lo;
  logic       dv_r, inf, sfd, fc_q;
  logic [7:0] rb;
  logic       rer;
  assign rb  = {rxd, lo};
  assign rer = rx_ctl ^ dv_r;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin lo <= 4'h0; dv_r <= 1'b0; end
    else begin lo <= rxd; dv_r <= rx_ctl; end
  end
  always_ff @(negedge clk or negedge rst_n) begin
    if (!rst_n) begin
      inf <= 1'b0; sfd <= 1'b0; f_pre <= 1'b0; f_code <= 1'b0; fcnt <= 16'd0; fe_end <= 1'b0;
      false_carrier <= 1'b0; fc_q <= 1'b0; link_up <= 1'b0; speed <= 2'd0; duplex <= 1'b0;
    end else begin
      fe_end <= 1'b0;
      false_carrier <= 1'b0;
      fc_q <= !dv_r && rer && rb == 8'h0E;
      if (!dv_r && rer && rb == 8'h0E && !fc_q) false_carrier <= 1'b1;
      // in-band status: the same nibble on both edges between frames
      if (!dv_r && !rer && rxd == lo) begin link_up <= lo[0]; speed <= lo[2:1]; duplex <= lo[3]; end
      if (dv_r) begin
        if (!inf) begin
          inf <= 1'b1; fcnt <= 16'd0; f_code <= rer;
          sfd <= (rb == 8'hD5); f_pre <= (rb != 8'h55 && rb != 8'hD5);
        end else begin
          if (rer) f_code <= 1'b1;
          if (!sfd) begin
            if (rb == 8'hD5) sfd <= 1'b1;
            else if (rb != 8'h55) f_pre <= 1'b1;
          end else begin
            if (fcnt < 16'd2048) fb[fcnt] <= rb;
            fcnt <= fcnt + 16'd1;
          end
        end
      end else if (inf) begin
        inf <= 1'b0; fe_end <= 1'b1;
        if (!sfd) f_pre <= 1'b1;
      end
    end
  end
"""

# rxd / rx_ctl change on both edges, so the driver writes them directly
# (nonblocking, right after each edge) instead of through a clocking block.
INTERFACE = """interface rgmii_if (input logic clk);
  logic rst_n;

  logic [47:0] station;
  logic        promisc;
  logic        mcast_en;
  logic [3:0]  rxd;
  logic        rx_ctl;
  logic        fr_done;
  logic [2:0]  fr_status;
  logic [15:0] fr_len;
  logic [15:0] fr_etype;
  logic [1:0]  fr_cast;
  logic        fr_vlan;
  logic        pause_valid;
  logic [15:0] pause_quanta;
  logic        false_carrier;
  logic        link_up;
  logic [1:0]  speed;
  logic        duplex;

  clocking drv_cb @(posedge clk);
    input rst_n, fr_done, fr_status, fr_len, fr_etype, fr_cast, fr_vlan, pause_valid, pause_quanta,
          false_carrier, link_up, speed, duplex;
    inout station, promisc, mcast_en;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, station, promisc, mcast_en, rxd, rx_ctl, fr_done, fr_status, fr_len, fr_etype, fr_cast, fr_vlan,
          pause_valid, pause_quanta, false_carrier, link_up, speed, duplex;
  endclocking
endinterface
"""

DRV_ITEM = """
bit [7:0] ln[$];
int ci = -1;
@(vif.drv_cb);
repeat (t.gap) idle_byte();
t.pre_bad = 0; t.code_err = 0;
if (t.kind != RGMII_STATUS) t.st_nib = 0;
if (t.kind == RGMII_FC) begin
  t.bytes.delete(); t.inj = RGMII_X_NONE;
  repeat (2 + t.gap) put_byte(8'h0E, 1'b0, 1'b1);
  repeat (cfg.ifg) idle_byte();
  return;
end
if (t.kind == RGMII_STATUS) begin
  t.bytes.delete(); t.inj = RGMII_X_NONE;
  if (t.st_nib == cur_st) t.st_nib = t.st_nib ^ 4'h1;   // always a change
  cur_st = t.st_nib;
  repeat (8 + cfg.ifg) idle_byte();
  return;
end
t.build(cfg.station);
for (int i = 0; i < t.pre_n; i++) ln.push_back(8'h55);
if (t.inj == RGMII_X_PRE) begin ln[0] = 8'h5D; t.pre_bad = 1; end
if (t.inj != RGMII_X_NOSFD) begin
  ln.push_back(8'hD5);
  foreach (t.bytes[i]) ln.push_back(t.bytes[i]);
end else begin
  int k = -1;
  t.pre_bad = 1;
  foreach (t.bytes[i]) if (k < 0 && t.bytes[i] == 8'hD5) k = i;
  foreach (t.bytes[i]) ln.push_back(t.bytes[i]);
  if (k < 0) t.bytes.delete(); else t.bytes = t.bytes[k + 1 : $];
end
if (t.inj == RGMII_X_CODE) begin ci = t.pre_n + 1 + t.bytes.size() / 2; t.code_err = 1; end
foreach (ln[i]) put_byte(ln[i], 1'b1, i == ci);
repeat (cfg.ifg) idle_byte();
"""

DRV_TASKS = """
// one byte: low nibble for the next rising edge, high nibble for the falling edge after it
task put_byte(bit [7:0] b, bit dv, bit er);
  @(negedge vif.clk);
  vif.rxd <= b[3:0]; vif.rx_ctl <= dv;
  @(posedge vif.clk);
  vif.rxd <= b[7:4]; vif.rx_ctl <= dv ^ er;
endtask

task idle_byte();
  put_byte({cur_st, cur_st}, 1'b0, 1'b0);
endtask
"""

MON_RUN = """
bit [7:0] b[$];
bit inf = 0, sfd = 0, pb = 0, ce = 0, fcq = 0;
bit [3:0] cur = 0;
int st_wait = 0;
rgmii_transaction pend[$];
rgmii_transaction fct, stt;
forever begin
  bit [3:0] lo;
  bit [7:0] d;
  bit dv, er, fc;
  @(posedge vif.clk);
  if (vif.rst_n !== 1'b1) begin inf = 0; fcq = 0; cur = 0; pend.delete(); fct = null; stt = null; continue; end
  // DUT results (values from before this edge)
  if (fct != null) begin fct.fc_out = vif.false_carrier; publish(fct); fct = null; end
  else if (vif.false_carrier) `uvm_error("MON", "RGMII false_carrier without a false carrier on the bus")
  if (stt != null && --st_wait == 0) begin
    stt.st_out = {vif.duplex, vif.speed, vif.link_up}; publish(stt); stt = null;
  end
  if (vif.fr_done) begin
    if (pend.size() == 0) `uvm_error("MON", "RGMII fr_done without a frame")
    else begin
      rgmii_transaction t = pend.pop_front();
      t.status = vif.fr_status; t.len = vif.fr_len; t.etype = vif.fr_etype;
      t.cast = vif.fr_cast; t.vlan = vif.fr_vlan; t.pause = vif.pause_valid;
      t.quanta = t.pause ? vif.pause_quanta : 16'h0;
      publish(t);
    end
  end
  // the bus: low nibble and RX_DV now, high nibble and RX_DV ^ RX_ER on the falling edge
  lo = vif.rxd; dv = vif.rx_ctl;
  @(negedge vif.clk);
  d = {vif.rxd, lo}; er = vif.rx_ctl ^ dv;
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
      rgmii_transaction t = rgmii_transaction::type_id::create("t");
      inf = 0; t.kind = RGMII_FRAME; t.bytes = b; t.pre_bad = pb || !sfd; t.code_err = ce;
      pend.push_back(t);
    end
    fc = er && d == 8'h0E;
    if (fc && !fcq) begin fct = rgmii_transaction::type_id::create("fc"); fct.kind = RGMII_FC; end
    fcq = fc;
    if (!er && d[7:4] == d[3:0] && d[3:0] != cur && stt == null) begin
      cur = d[3:0];
      stt = rgmii_transaction::type_id::create("st"); stt.kind = RGMII_STATUS; stt.st_nib = cur; st_wait = 2;
    end
  end
end
"""

SVA = """
assert property (@(posedge clk) disable iff (!rst_n) false_carrier |=> !false_carrier)
  else $error("RGMII: false_carrier longer than one clock");
assert property (@(posedge clk) disable iff (!rst_n) speed != 2'd3)
  else $error("RGMII: reserved in-band speed 11");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({link_up, speed, duplex, false_carrier}))
  else $error("RGMII: X on status outputs");
cover property (@(posedge clk) disable iff (!rst_n) $rose(link_up));
cover property (@(posedge clk) disable iff (!rst_n) speed == 2'd2 && duplex);
cover property (@(posedge clk) disable iff (!rst_n) false_carrier);
"""

SMOKE_BUS = """
int nfc = 0;
always @(negedge clk) if (false_carrier) nfc++;
logic [3:0] st_nib = 4'h0;

// one byte: low nibble before the rising edge, high nibble before the falling edge
task automatic put(input logic [7:0] b, input bit dv, input bit er);
  @(negedge clk); #1 rxd = b[3:0]; rx_ctl = dv;
  @(posedge clk); #1 rxd = b[7:4]; rx_ctl = dv ^ er;
endtask
task automatic put_idle(input int n);
  repeat (n) put({st_nib, st_nib}, 1'b0, 1'b0);
endtask

// pre_n preamble bytes (index bad_pre sent as 5D), SFD unless nosfd, then fr;
// RX_ER on fr[code_at] (-2: on the SFD, -3: on the first preamble byte)
task automatic send(input int pre_n, input int bad_pre, input bit nosfd, input int code_at);
  for (int i = 0; i < pre_n; i++) put((i == bad_pre) ? 8'h5D : 8'h55, 1'b1, i == 0 && code_at == -3);
  if (!nosfd) put(8'hD5, 1'b1, code_at == -2);
  for (int i = 0; i < fl; i++) put(fr[i], 1'b1, i == code_at);
  put_idle(1);
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
  // nibble order: a frame with the nibbles of every byte swapped fails the FCS
  mk(ST, 16'h0800, 46, 0);
  for (int i = 0; i < fl; i++) fr[i] = {fr[i][3:0], fr[i][7:4]};
  rxs(3, 7, -1, 0, -1, "swapped nibbles fail the FCS");
  mk(ST, 16'h0800, 46, 0);
  // RX_ER (RX_DV ^ RX_ER on the falling edge)
  rxs(2, 7, -1, 0, 10, "RX_ER on byte 10");
  rxs(2, 7, -1, 0, 0, "RX_ER on the first byte");
  rxs(2, 7, -1, 0, 63, "RX_ER on the last byte");
  rxs(2, 7, -1, 0, -2, "RX_ER on the SFD");
  rxs(2, 7, -1, 0, -3, "RX_ER on the first preamble byte");
  rxs(1, 7, 2, 0, 5, "preamble error before code error");
  mk(ST, 16'h0800, 10, 0);
  rxs(2, 7, -1, 0, 5, "code error before runt");

  // in-band status
  chk(!link_up && speed == 0 && !duplex, "status 0 after reset");
  st_nib = 4'hD; put_idle(3); idle(2);
  chk(link_up && speed == 2'd2 && duplex, "link up, 1000 Mb/s, full duplex");
  st_nib = 4'h3; put_idle(3); idle(2);
  chk(link_up && speed == 2'd1 && !duplex, "link up, 100 Mb/s, half duplex");
  st_nib = 4'h8; put_idle(3); idle(2);
  chk(!link_up && speed == 2'd0 && duplex, "link down, 10 Mb/s, full duplex");
  st_nib = 4'h5; put_idle(3); idle(2);
  chk(link_up && speed == 2'd2 && !duplex, "link up, 1000 Mb/s, half duplex");
  put({4'h5, 4'h3}, 1'b0, 1'b0); put({4'h5, 4'h5}, 1'b0, 1'b0); idle(2);
  chk(link_up && speed == 2'd2 && !duplex, "nibbles differing between edges: status not taken");
  put({4'hF, 4'hF}, 1'b0, 1'b1); put_idle(1); idle(2);
  chk(speed == 2'd2 && !duplex, "RX_ER between frames: not status");
  st_nib = 4'hD; put_idle(3);
  mk(ST, 16'h0800, 46, 0); rx(0, "frame with the link up");
  chk(link_up && speed == 2'd2 && duplex, "status kept across a frame (preamble 55 is data)");
  repeat (7) put(8'h55, 1'b1, 1'b0);
  chk(link_up && speed == 2'd2 && duplex, "preamble bytes with equal nibbles are not status");
  put(8'hD5, 1'b1, 1'b0); put(8'h11, 1'b1, 1'b1); put_idle(2); idle(4);
  chk(lst == 2 && duplex, "RX_ER byte with equal nibbles inside a frame is not status");

  // false carrier
  n0 = ndone;
  repeat (3) put(8'h0E, 1'b0, 1'b1);
  put_idle(2); idle(2);
  chk(nfc == 1 && ndone == n0, $sformatf("false carrier: one pulse, no frame (%0d)", nfc));
  put(8'h0E, 1'b0, 1'b1); put_idle(1); put(8'h0E, 1'b0, 1'b1); put_idle(2); idle(2);
  chk(nfc == 3, $sformatf("two false-carrier events (%0d)", nfc));
  put(8'h0E, 1'b0, 1'b1); put({4'h0, 4'hE}, 1'b0, 1'b0); put(8'h0E, 1'b0, 1'b1); put_idle(2); idle(2);
  chk(nfc == 5, $sformatf("0E without RX_ER separates two events (%0d)", nfc));
  put(8'h0F, 1'b0, 1'b1); put(8'h1E, 1'b0, 1'b1); put(8'hE0, 1'b0, 1'b1); put({4'h0, 4'hE}, 1'b0, 1'b0); put_idle(2); idle(2);
  chk(nfc == 5, "0F, 1E, E0 with RX_ER, 0E without: no false carrier");
  put(8'h0E, 1'b1, 1'b1); put_idle(2); idle(4);
  chk(nfc == 5 && lst == 1, "0E with RX_DV is data, not false carrier");

  // back-to-back frames, one idle byte apart
  mk(ST, 16'h0800, 46, 0);
  n0 = ndone;
  send(7, -1, 0, -1); send(7, -1, 0, -1); idle(4);
  chk(ndone == n0 + 2 && lst == 0, "two frames one byte apart");
  // reset inside a frame
  n0 = ndone;
  for (int i = 0; i < 20; i++) put((i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : 8'h33, 1'b1, 1'b0);
  rst_n = 0; idle(2);
  chk(!link_up && speed == 0 && !duplex && !fr_done, "reset clears the status and drops the frame");
  rx_ctl = 0; rxd = 0; st_nib = 0; @(posedge clk); #1 rst_n = 1; idle(2);
  chk(ndone == n0, "no result for the dropped frame");
  rx(0, "frame after the reset");
"""

SPEC = build_spec(
    vip="RGMII-UVM-VIP", p=p, P=P,
    desc="RGMII v2.0 VIP: PHY-side agent driving a MAC receiver on both clock edges (data nibbles, "
         "RX_DV / RX_DV^RX_ER on rx_ctl), in-band link / speed / duplex status and false carrier; the MAC "
         "model checks FCS, length limits, the length field, address filtering and PAUSE frames.",
    about="""
The agent plays the PHY on the RGMII receive pins: the low nibble of each
byte with RX_DV before the rising edge, the high nibble with RX_DV xor RX_ER
before the falling edge. An item is a frame, a false-carrier event or an
in-band status change (link, speed, duplex sent on rxd between frames).
Frames are built from knobs (destination: the station, another station,
multicast, broadcast, MAC PAUSE; 802.1Q tag; length or type field; payload
length) and can be broken on purpose: a bad preamble byte, no SFD, RX_ER
inside the frame, a bad FCS, a runt, an oversize frame or a length field
that does not match the data.

The monitor samples both edges, rebuilds every frame and pairs it with the
MAC's result; the scoreboard runs the IEEE 802.3 receive checks on the
observed bytes and predicts the status, length / type, destination class,
VLAN tag and PAUSE quanta, the false_carrier pulse and the decoded in-band
status.""",
    ports=[("in", "logic [3:0]", "rxd"), ("in", "logic", "rx_ctl")],
    bus_fields=[("bit", "fc_out", "rsp"), ("bit [3:0]", "st_nib", "req"), ("bit [3:0]", "st_out", "rsp")],
    kinds=[("RGMII_FRAME", 12), ("RGMII_FC", 1), ("RGMII_STATUS", 1)],
    cfg_extra="int unsigned ifg = 12;   // idle bytes after each item",
    drv_idle="""vif.rxd <= cur_st; vif.rx_ctl <= 1'b0;
vif.drv_cb.station <= cfg.station; vif.drv_cb.promisc <= cfg.promisc; vif.drv_cb.mcast_en <= cfg.mcast_en;""",
    drv_item=DRV_ITEM, drv_members="bit [3:0] cur_st = 4'h0;   // in-band status sent between frames",
    drv_tasks=DRV_TASKS,
    mon_run=MON_RUN, mon_tasks="",
    extra_predict="t.fc_out = (t.kind == RGMII_FC);\nt.st_out = (t.kind == RGMII_STATUS) ? t.st_nib : 4'h0;\n",
    extra_cov="""cp_fc    : coverpoint tr.fc_out iff (tr.kind == RGMII_FC) { bins seen = {1}; }
cp_speed : coverpoint tr.st_out[2:1] iff (tr.kind == RGMII_STATUS) { bins s10 = {0}; bins s100 = {1}; bins s1000 = {2}; }
cp_link  : coverpoint tr.st_out[0] iff (tr.kind == RGMII_STATUS);
cp_dup   : coverpoint tr.st_out[3] iff (tr.kind == RGMII_STATUS);
""",
    directed="""
t = item(); t.kind = RGMII_STATUS; t.st_nib = 4'hD; send(t);
t = item(); t.kind = RGMII_STATUS; t.st_nib = 4'h3; send(t);
t = item(); t.kind = RGMII_STATUS; t.st_nib = 4'h0; send(t);
t = item(); t.kind = RGMII_STATUS; t.st_nib = 4'h9; send(t);
t = item(); t.kind = RGMII_FC; send(t);
t = item(); t.kind = RGMII_FRAME; t.inj = RGMII_X_NONE; t.dak = RGMII_D_SELF; t.pre_n = 1; send(t);
""",
    model_front=FRONT,
    model_ports=[("out", "logic", "false_carrier"), ("out", "logic", "link_up"), ("out", "logic [1:0]", "speed"),
                 ("out", "logic", "duplex")],
    sva=SVA, smoke_bus=SMOKE_BUS, smoke_tests=SMOKE_TESTS,
)
SPEC["interface"] = INTERFACE
SPEC["constraints"] += "constraint c_st { st_nib[2:1] != 2'd3; }\n"
