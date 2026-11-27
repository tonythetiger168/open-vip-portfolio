# XGMII (IEEE 802.3 clause 46) PHY-side agent driving a 10G MAC receiver:
# rxd[31:0] / rxc[3:0], four lanes per clock (lane 0 = rxd[7:0]). Frames are
# Start (FB, lane 0), six 55, SFD, the MAC frame and Terminate (FD) in any
# lane, then Idle (07). Error /E/ (FE) inside a frame, a Start outside lane 0,
# another control character inside a frame; link fault signalling with
# Sequence ordered sets (9C in lane 0, 00 00 01 local fault / 00 00 02
# remote fault). tb/top_tb.sv xgmii_model: XGMII front end + the MAC receive
# check of _mii.py; link fault: four sequences of one type, each within 128
# columns of the last, set the fault; 128 columns without one clear it.
from _mii import build_spec

P, p = "XGMII", "xgmii"

FRONT = """
  logic        inf, sfd;
  logic [1:0]  lt_typ, flt;
  logic [2:0]  scnt;
  logic [7:0]  ccnt;
  logic        i_inf, i_sfd, i_pre, i_code, i_end, kc, seq;
  logic [15:0] i_cnt;
  logic [7:0]  b;
  logic [1:0]  styp;
  integer      ln;
  assign local_fault  = (flt == 2'd1);
  assign remote_fault = (flt == 2'd2);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      inf <= 1'b0; sfd <= 1'b0; f_pre <= 1'b0; f_code <= 1'b0; fcnt <= 16'd0; fe_end <= 1'b0;
      lt_typ <= 2'd0; flt <= 2'd0; scnt <= 3'd0; ccnt <= 8'd128;
    end else begin
      // frames, lane by lane
      i_inf = inf; i_sfd = sfd; i_pre = f_pre; i_code = f_code; i_cnt = fcnt; i_end = 1'b0;
      for (ln = 0; ln < 4; ln++) begin
        b = rxd[8*ln +: 8];
        kc = rxc[ln];
        if (!i_inf) begin
          if (kc && b == 8'hFB) begin
            i_inf = 1'b1; i_sfd = 1'b0; i_pre = (ln != 0); i_code = 1'b0; i_cnt = 16'd0;
          end
        end else if (kc && b == 8'hFD) begin
          i_inf = 1'b0; i_end = 1'b1;
          if (!i_sfd) i_pre = 1'b1;
        end else if (kc && b != 8'hFE) begin
          // any other control character ends the frame with an error
          i_inf = 1'b0; i_end = 1'b1; i_code = 1'b1;
          if (!i_sfd) i_pre = 1'b1;
        end else if (kc) i_code = 1'b1;
        else if (!i_sfd) begin
          if (b == 8'hD5) i_sfd = 1'b1;
          else if (b != 8'h55) i_pre = 1'b1;
        end else begin
          if (i_cnt < 16'd2048) fb[i_cnt] <= b;
          i_cnt = i_cnt + 16'd1;
        end
      end
      inf <= i_inf; sfd <= i_sfd; f_pre <= i_pre; f_code <= i_code; fcnt <= i_cnt; fe_end <= i_end;

      // link fault signalling (clause 46.3.4)
      seq  = (rxc == 4'b0001) && (rxd == 32'h0100_009C || rxd == 32'h0200_009C);
      styp = rxd[25:24];
      if (seq) begin
        if (styp == lt_typ && ccnt < 8'd128) begin
          if (scnt >= 3'd3) flt <= styp;
          else scnt <= scnt + 3'd1;
        end else begin
          lt_typ <= styp; scnt <= 3'd1;
        end
        ccnt <= 8'd0;
      end else if (ccnt == 8'd127) begin
        flt <= 2'd0; scnt <= 3'd0; lt_typ <= 2'd0; ccnt <= 8'd128;
      end else if (ccnt < 8'd128) ccnt <= ccnt + 8'd1;
    end
  end
"""

DRV_ITEM = """
bit [7:0] cb[$];
bit kq[$];
@(vif.drv_cb);
repeat (t.gap) @(vif.drv_cb);
t.pre_bad = 0; t.code_err = 0; t.fcols = 0; t.frl = 0; t.frr = 0;
if (t.kind == XGMII_FAULT) begin
  int run = 0;
  bit prev = 0;
  t.bytes.delete(); t.inj = XGMII_X_NONE;
  for (int i = 0; i < t.fn; i++) begin
    bit ty = t.fmix ? (t.ftype ^ i[0]) : t.ftype;     // 0 local, 1 remote
    vif.drv_cb.rxd <= ty ? 32'h0200_009C : 32'h0100_009C; vif.drv_cb.rxc <= 4'b0001;
    @(vif.drv_cb);
    run = (i > 0 && ty == prev) ? run + 1 : 1; prev = ty;
    if (run >= 4) begin if (ty) t.frr = 1; else t.frl = 1; end
  end
  t.fcols = t.fn;
  vif.drv_cb.rxd <= 32'h0707_0707; vif.drv_cb.rxc <= 4'hF;
  repeat (140) @(vif.drv_cb);                          // the fault clears after 128 columns
  return;
end
t.build(cfg.station);
// Start in lane 0 (or later, broken on purpose), preamble, SFD
if (t.inj == XGMII_X_PRE) begin
  repeat (1 + t.seed[9:8] % 3) begin cb.push_back(8'h07); kq.push_back(1); end
  t.pre_bad = 1;
end
cb.push_back(8'hFB); kq.push_back(1);
repeat (6) begin cb.push_back(8'h55); kq.push_back(0); end
if (t.inj != XGMII_X_NOSFD) begin
  cb.push_back(8'hD5); kq.push_back(0);
  foreach (t.bytes[i]) begin cb.push_back(t.bytes[i]); kq.push_back(0); end
end else begin
  int k = -1;
  t.pre_bad = 1;
  cb.push_back(8'h55); kq.push_back(0);
  foreach (t.bytes[i]) if (k < 0 && t.bytes[i] == 8'hD5) k = i;
  foreach (t.bytes[i]) begin cb.push_back(t.bytes[i]); kq.push_back(0); end
  if (k < 0) t.bytes.delete(); else t.bytes = t.bytes[k + 1 : $];
end
if (t.inj == XGMII_X_CODE) begin
  // /E/ replaces a byte: the receiver sees the frame without it
  int ci = t.bytes.size() / 2;
  cb[cb.size() - t.bytes.size() + ci] = 8'hFE; kq[kq.size() - t.bytes.size() + ci] = 1;
  t.bytes.delete(ci);
  t.code_err = 1;
end
cb.push_back(8'hFD); kq.push_back(1);
while (cb.size() % 4) begin cb.push_back(8'h07); kq.push_back(1); end
for (int i = 0; i < cb.size(); i += 4) begin
  vif.drv_cb.rxd <= {cb[i+3], cb[i+2], cb[i+1], cb[i]};
  vif.drv_cb.rxc <= {kq[i+3], kq[i+2], kq[i+1], kq[i]};
  @(vif.drv_cb);
end
vif.drv_cb.rxd <= 32'h0707_0707; vif.drv_cb.rxc <= 4'hF;
repeat (cfg.ifg) @(vif.drv_cb);
"""

MON_RUN = """
bit [7:0] bq[$];
bit inf = 0, sfd = 0, pb = 0, ce = 0, prev = 0;
int run = 0, quiet = 0;
xgmii_transaction pend[$];
xgmii_transaction ft;
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin inf = 0; pend.delete(); ft = null; continue; end
  // DUT results for earlier columns
  if (vif.mon_cb.fr_done) begin
    if (pend.size() == 0) `uvm_error("MON", "XGMII fr_done without a frame")
    else begin
      xgmii_transaction t = pend.pop_front();
      t.status = vif.mon_cb.fr_status; t.len = vif.mon_cb.fr_len; t.etype = vif.mon_cb.fr_etype;
      t.cast = vif.mon_cb.fr_cast; t.vlan = vif.mon_cb.fr_vlan; t.pause = vif.mon_cb.pause_valid;
      t.quanta = t.pause ? vif.mon_cb.pause_quanta : 16'h0;
      publish(t);
    end
  end
  if (ft != null) ft.fseen |= {vif.mon_cb.remote_fault, vif.mon_cb.local_fault};
  else if (vif.mon_cb.remote_fault || vif.mon_cb.local_fault)
    `uvm_error("MON", "XGMII link fault reported without fault sequences")
  // link fault sequences: one item per burst, closed 132 columns after the last one
  if (vif.mon_cb.rxc == 4'b0001 && (vif.mon_cb.rxd == 32'h0100_009C || vif.mon_cb.rxd == 32'h0200_009C)) begin
    bit ty = vif.mon_cb.rxd[25];
    if (ft == null) begin ft = xgmii_transaction::type_id::create("flt"); ft.kind = XGMII_FAULT; end
    run = (ft.fcols > 0 && ty == prev) ? run + 1 : 1; prev = ty;
    ft.fcols++;
    if (run >= 4) begin if (ty) ft.frr = 1; else ft.frl = 1; end
    quiet = 0;
  end else if (ft != null && ++quiet == 132) begin
    ft.fend = {vif.mon_cb.remote_fault, vif.mon_cb.local_fault};
    publish(ft); ft = null;
  end
  // frames, lane by lane
  for (int ln = 0; ln < 4; ln++) begin
    bit [7:0] b = vif.mon_cb.rxd[8*ln +: 8];
    bit k = vif.mon_cb.rxc[ln];
    bit fin = 0;
    if (!inf) begin
      if (k && b == 8'hFB) begin inf = 1; sfd = 0; pb = (ln != 0); ce = 0; bq.delete(); end
    end else if (k && b == 8'hFD) fin = 1;
    else if (k && b != 8'hFE) begin fin = 1; ce = 1; end
    else if (k) ce = 1;
    else if (!sfd) begin if (b == 8'hD5) sfd = 1; else if (b != 8'h55) pb = 1; end
    else bq.push_back(b);
    if (fin) begin
      xgmii_transaction t = xgmii_transaction::type_id::create("t");
      inf = 0; t.kind = XGMII_FRAME; t.bytes = bq; t.pre_bad = pb || !sfd; t.code_err = ce;
      pend.push_back(t);
    end
  end
end
"""

SVA = """
assert property (@(posedge clk) disable iff (!rst_n) !(local_fault && remote_fault))
  else $error("XGMII: local and remote fault at once");
// a fault is only set by a Sequence ordered set
assert property (@(posedge clk) disable iff (!rst_n) $rose(local_fault) |-> $past(rxc == 4'b0001 && rxd == 32'h0100_009C))
  else $error("XGMII: local fault without a local fault sequence");
assert property (@(posedge clk) disable iff (!rst_n) $rose(remote_fault) |-> $past(rxc == 4'b0001 && rxd == 32'h0200_009C))
  else $error("XGMII: remote fault without a remote fault sequence");
// frame result two clocks after the Terminate column
assert property (@(posedge clk) disable iff (!rst_n) fr_done |-> $past(rxc != 4'h0, 2))
  else $error("XGMII: fr_done without a control column");
cover property (@(posedge clk) disable iff (!rst_n) $rose(local_fault));
cover property (@(posedge clk) disable iff (!rst_n) $rose(remote_fault));
cover property (@(posedge clk) disable iff (!rst_n) $fell(local_fault));
"""

SMOKE_BUS = """
// column buffer
logic [7:0] cb [0:2399];
logic       ck [0:2399];
int cn;
task automatic col(input logic [7:0] b, input bit k); cb[cn] = b; ck[cn] = k; cn++; endtask
task automatic flush();
  while (cn % 4) col(8'h07, 1);
  for (int i = 0; i < cn; i += 4) begin
    @(negedge clk); rxd = {cb[i+3], cb[i+2], cb[i+1], cb[i]}; rxc = {ck[i+3], ck[i+2], ck[i+1], ck[i]};
  end
  @(negedge clk); rxd = 32'h0707_0707; rxc = 4'hF;
  cn = 0;
endtask

// Start in lane bad_pre + 1 when bad_pre >= 0; no SFD; /E/ instead of fr[code_at]
// (-2: instead of the SFD, -3: instead of a preamble byte)
task automatic send(input int pre_n, input int bad_pre, input bit nosfd, input int code_at);
  cn = 0;
  if (bad_pre >= 0) repeat (bad_pre + 1) col(8'h07, 1);
  col(8'hFB, 1);
  for (int i = 0; i < 6; i++) if (i == 2 && code_at == -3) col(8'hFE, 1); else col(8'h55, 0);
  if (code_at == -2) col(8'hFE, 1); else col(nosfd ? 8'h55 : 8'hD5, 0);
  for (int i = 0; i < fl; i++) if (i == code_at) col(8'hFE, 1); else col(fr[i], 0);
  col(8'hFD, 1);
  flush();
endtask

task automatic rxs(input logic [2:0] s, input int bad_pre, input bit nosfd, input int code_at, input string msg);
  n0 = ndone;
  send(0, bad_pre, nosfd, code_at);
  idle(4);
  chk(ndone == n0 + 1 && lst == s, $sformatf("%s: status %0d (got %0d, %0d results)", msg, s, lst, ndone - n0));
endtask

task automatic seqs(input int n, input bit remote, input int gap);
  for (int i = 0; i < n; i++) begin
    @(negedge clk); rxd = remote ? 32'h0200_009C : 32'h0100_009C; rxc = 4'b0001;
    if (gap > 0 && i < n - 1) begin @(negedge clk); rxd = 32'h0707_0707; rxc = 4'hF; repeat (gap - 1) @(negedge clk); end
  end
  @(negedge clk); rxd = 32'h0707_0707; rxc = 4'hF;
  #1;
endtask
"""

SMOKE_TESTS = """
  // Terminate in each lane
  for (int n = 46; n < 50; n++) begin mk(ST, 16'h0800, n, 0); rx(0, $sformatf("Terminate in lane %0d", n % 4)); end
  // Start lane, SFD, /E/
  mk(ST, 16'h0800, 46, 0);
  rxs(1, 0, 0, -1, "Start in lane 1");
  rxs(1, 1, 0, -1, "Start in lane 2");
  rxs(1, 2, 0, -1, "Start in lane 3");
  rxs(0, 3, 0, -1, "Start in lane 0 of the next column");
  rxs(1, -1, 1, -1, "no SFD");
  chk(llen == 64 - 45, $sformatf("no SFD: bytes after the first D5 in the data (%0d)", llen));
  rxs(2, -1, 0, 10, "/E/ in the frame");
  chk(llen == 63, "/E/ replaces a byte");
  rxs(2, -1, 0, 0, "/E/ on the first byte");
  rxs(2, -1, 0, 63, "/E/ on the last byte");
  rxs(2, -1, 0, -3, "/E/ in the preamble");
  rxs(1, -1, 0, -2, "/E/ instead of the SFD: no SFD");
  rxs(1, 0, 0, 5, "Start error before code error");
  mk(ST, 16'h0800, 10, 0);
  rxs(2, -1, 0, 5, "code error before runt");
  // control characters inside the frame
  mk(ST, 16'h0800, 46, 0);
  n0 = ndone;
  cn = 0; col(8'hFB, 1); repeat (6) col(8'h55, 0); col(8'hD5, 0);
  for (int i = 0; i < 30; i++) col(fr[i], 0);
  col(8'h07, 1);
  for (int i = 30; i < fl; i++) col(fr[i], 0);
  col(8'hFD, 1); flush(); idle(4);
  chk(ndone == n0 + 1 && lst == 2 && llen == 30, $sformatf("Idle inside a frame ends it with an error (%0d)", llen));
  n0 = ndone;
  cn = 0; col(8'hFB, 1); repeat (6) col(8'h55, 0); col(8'hD5, 0);
  for (int i = 0; i < 20; i++) col(fr[i], 0);
  col(8'h9C, 1); col(8'hFD, 1); flush(); idle(4);
  chk(ndone == n0 + 1 && lst == 2, "Sequence character inside a frame");
  n0 = ndone;
  cn = 0; col(8'hFB, 1); repeat (3) col(8'h55, 0); col(8'h07, 1); col(8'hFD, 1); flush(); idle(4);
  chk(ndone == n0 + 1 && lst == 1, "Idle in the preamble: Start error");
  n0 = ndone;
  cn = 0; col(8'hFB, 1); repeat (3) col(8'h55, 0); col(8'hFD, 1); flush(); idle(4);
  chk(ndone == n0 + 1 && lst == 1 && llen == 0, "Terminate before the SFD: Start error");
  n0 = ndone;
  cn = 0; col(8'h55, 0); col(8'hD5, 0); col(8'hFD, 1); col(8'hFE, 1); for (int i = 0; i < 70; i++) col(8'h11, 0);
  flush(); idle(4);
  chk(ndone == n0, "data, Terminate and /E/ outside a frame are ignored");
  mk(ST, 16'h0800, 46, 0); rx(0, "frame after stray characters");
  // back-to-back: Start in the column after the Terminate
  n0 = ndone;
  cn = 0;
  for (int f = 0; f < 2; f++) begin
    col(8'hFB, 1); repeat (6) col(8'h55, 0); col(8'hD5, 0);
    for (int i = 0; i < fl; i++) col(fr[i], 0);
    col(8'hFD, 1);
    while (cn % 4) col(8'h07, 1);
  end
  flush(); idle(4);
  chk(ndone == n0 + 2 && lst == 0, "two frames with no Idle column between");

  // link fault signalling
  chk(!local_fault && !remote_fault, "no fault after reset");
  seqs(3, 0, 0); idle(2);
  chk(!local_fault, "three local fault sequences: no fault");
  idle(130);
  seqs(4, 0, 0);
  chk(local_fault && !remote_fault, "four local fault sequences: local fault");
  idle(127);
  chk(local_fault, "fault held 127 columns after the last sequence");
  idle(1);
  chk(!local_fault, "fault cleared after 128 columns");
  seqs(4, 1, 0);
  chk(remote_fault && !local_fault, "four remote fault sequences: remote fault");
  seqs(4, 0, 0);
  chk(local_fault && !remote_fault, "four local sequences replace a remote fault");
  idle(140);
  seqs(7, 0, 0); chk(local_fault, "more than four sequences");
  idle(140);
  // alternating types never reach four of one kind
  for (int i = 0; i < 8; i++) seqs(1, i[0], 0);
  chk(!local_fault && !remote_fault, "alternating local / remote: no fault");
  idle(140);
  seqs(3, 0, 0); seqs(1, 1, 0); seqs(3, 0, 0);
  chk(!local_fault && !remote_fault, "a remote sequence restarts the local count");
  idle(140);
  // sequences 127 columns apart still count, 128 apart do not
  seqs(4, 0, 127);
  chk(local_fault, "sequences 127 columns apart");
  idle(140);
  seqs(4, 0, 128);
  chk(!local_fault, "sequences 128 columns apart");
  idle(140);
  // not a fault sequence: other lane-3 code, other control lanes
  for (int i = 0; i < 6; i++) begin @(negedge clk); rxd = 32'h0300_009C; rxc = 4'b0001; end
  for (int i = 0; i < 6; i++) begin @(negedge clk); rxd = 32'h0100_009C; rxc = 4'b0011; end
  for (int i = 0; i < 6; i++) begin @(negedge clk); rxd = 32'h0100_009D; rxc = 4'b0001; end
  for (int i = 0; i < 6; i++) begin @(negedge clk); rxd = 32'h0101_009C; rxc = 4'b0001; end
  @(negedge clk); rxd = 32'h0707_0707; rxc = 4'hF; idle(2);
  chk(!local_fault && !remote_fault, "malformed Sequence ordered sets ignored");
  // frames between sequences count as columns without a fault
  seqs(4, 1, 0);
  mk(ST, 16'h0800, 1000, 0); rx(0, "frame during a remote fault");
  chk(!remote_fault, "fault cleared by frames");
  // reset clears the fault
  seqs(4, 0, 0);
  rst_n = 0; idle(2);
  chk(!local_fault, "reset clears the fault");
  rst_n = 1; idle(2);
  seqs(3, 0, 0);
  chk(!local_fault, "count restarts after reset");
"""

SPEC = build_spec(
    vip="XGMII-UVM-VIP", p=p, P=P,
    desc="XGMII (IEEE 802.3 clause 46) VIP: PHY-side agent driving a 10G MAC receiver with lane-aligned "
         "Start / Terminate, /E/ error control characters and link fault Sequence ordered sets; the MAC "
         "model checks FCS, length limits, the length field, address filtering and PAUSE frames.",
    about="""
The agent plays the PHY on the 32-bit XGMII receive pins (rxd / rxc, lane 0
in rxd[7:0]). An item is a frame or a burst of link fault Sequence ordered
sets. Frames start with /S/ in lane 0, six preamble bytes and the SFD, and
end with /T/ in whichever lane the frame length puts it, padded with /I/.
They are built from knobs (destination: the station, another station,
multicast, broadcast, MAC PAUSE; 802.1Q tag; length or type field; payload
length) and can be broken on purpose: /S/ outside lane 0, no SFD, /E/
replacing a byte, a bad FCS, a runt, an oversize frame or a length field that
does not match the data. Fault bursts send local or remote fault sequences,
of one type or alternating.

The monitor rebuilds frames lane by lane and pairs each with the MAC's
result; the scoreboard runs the IEEE 802.3 receive checks on the observed
bytes and predicts the status, length / type, destination class, VLAN tag and
PAUSE quanta. For fault bursts it predicts local_fault / remote_fault (four
sequences of one type in a row) and that both clear 128 columns later.""",
    ports=[("in", "logic [31:0]", "rxd"), ("in", "logic [3:0]", "rxc")],
    bus_fields=[("bit [3:0]", "fcols", "req", "norand"), ("bit", "frl", "req", "norand"), ("bit", "frr", "req", "norand"),
                ("bit [1:0]", "fseen", "rsp"), ("bit [1:0]", "fend", "rsp"),
                ("bit [3:0]", "fn", "info", "rand"), ("bit", "ftype", "info", "rand"), ("bit", "fmix", "info", "rand")],
    kinds=[("XGMII_FRAME", 12), ("XGMII_FAULT", 2)],
    cfg_extra="int unsigned ifg = 3;   // idle columns after each frame",
    drv_idle="""vif.drv_cb.rxd <= 32'h0707_0707; vif.drv_cb.rxc <= 4'hF;
vif.drv_cb.station <= cfg.station; vif.drv_cb.promisc <= cfg.promisc; vif.drv_cb.mcast_en <= cfg.mcast_en;""",
    drv_item=DRV_ITEM, drv_members="", drv_tasks="",
    mon_run=MON_RUN, mon_tasks="",
    extra_predict="t.fseen = (t.kind == XGMII_FAULT) ? {t.frr, t.frl} : 2'b00;\nt.fend = 2'b00;\n",
    extra_cov="""cp_term  : coverpoint ((tr.bytes.size() + 8 + tr.code_err) % 4) iff (tr.kind == XGMII_FRAME && !tr.pre_bad) { bins lane[] = {[0:3]}; }
cp_fault : coverpoint tr.fseen iff (tr.kind == XGMII_FAULT) { bins none = {0}; bins local_ = {1}; bins remote = {2}; }
""",
    directed="""
for (int n = 46; n < 50; n++) begin
  t = item(); t.kind = XGMII_FRAME; t.inj = XGMII_X_NONE; t.dak = XGMII_D_SELF; t.vtag = 0; t.use_len = 0; t.plen = n; send(t);
end
t = item(); t.kind = XGMII_FAULT; t.fn = 4; t.ftype = 0; t.fmix = 0; send(t);
t = item(); t.kind = XGMII_FAULT; t.fn = 6; t.ftype = 1; t.fmix = 0; send(t);
t = item(); t.kind = XGMII_FAULT; t.fn = 3; t.ftype = 0; t.fmix = 0; send(t);
t = item(); t.kind = XGMII_FAULT; t.fn = 8; t.ftype = 0; t.fmix = 1; send(t);
t = item(); t.kind = XGMII_FAULT; t.fn = 4; t.ftype = 0; t.fmix = 0; send(t);
t = item(); t.kind = XGMII_FAULT; t.fn = 12; t.ftype = 1; t.fmix = 0; send(t);
""",
    model_front=FRONT,
    model_ports=[("out", "logic", "local_fault"), ("out", "logic", "remote_fault")],
    sva=SVA, smoke_bus=SMOKE_BUS, smoke_tests=SMOKE_TESTS,
)
SPEC["constraints"] += "constraint c_flt { fn inside {[1:12]}; }\n"
