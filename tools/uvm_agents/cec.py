# HDMI CEC (HDMI 1.4b Supplement 1) VIP: single-wire open-drain bus, the
# agent is a CEC initiator, the DUT model a follower at logical address 0 (TV).
#
# Line: cec_in = ~(agent_low | cec_oe_low) (wired-AND, idle high). Timing in
# units of 50 us (cfg.cec_u clocks each, model parameter U, default 2):
#   start bit : low 74 (3.7 ms), period 90 (4.5 ms)
#   data bit  : period 48 (2.4 ms); 1 = low 12 (0.6 ms), 0 = low 30 (1.5 ms)
#   block     : 8 data bits MSB first, EOM, ACK. Header block {initiator, destination}.
#   ACK       : the initiator sends 1; a follower addressed directly pulls the
#               line low for 30 (a 0) to acknowledge; a broadcast (destination
#               15) is accepted when nobody pulls the ACK bit low.
# Follower model windows: 1 low [8, 16], 0 low [26, 34], bit period [41, 55],
# start low [70, 78], start period [86, 94]. A bit timing error is answered
# by an error notification (the follower pulls the line low for 72 = 1.5 bit
# periods); then the model waits for 96 of idle line before the next start bit.
# DUT -> agent: each data block of a frame it accepts (out_valid, out_data) and
# one report per frame (rep_valid; rep_status 0 direct frame received, 1
# broadcast received, 2 not addressed (header NACK), 3 bit timing error or
# bit period overrun, 4 start bit error; rep_init, rep_dest, rep_len = data
# blocks received). The agent stops a frame after a NACKed direct block and
# when it sees an error notification (line still low at the end of a bit).

CEC_FUNCS = """
function automatic bit cec_rng(int v, int lo, int hi); return v >= lo && v <= hi; endfunction
"""

SPEC = dict(
    vip="HDMI_CEC-UVM-VIP", p="cec", P="CEC", dir="cec", family="Video",
    desc="HDMI CEC VIP: initiator agent on the open-drain CEC line (start bit, header / data blocks, EOM, ACK), "
         "follower model at logical address 0 with ACK, broadcast, NACK, error notification and timing windows.",
    about="""
CEC is the HDMI control bus: a single open-drain wire shared by every device,
carrying short frames such as Standby, Image View On or Give Physical
Address. The agent is a CEC initiator (a player or set-top box): it sends
polling messages, direct and broadcast frames of up to 15 data blocks,
frames to other devices, frames with timing jitter inside the follower's
windows and faults (a data bit low time between 0 and 1, a short bit period,
a bad start bit, a frame whose last block has no EOM). It reads the ACK bit
like a real initiator and stops after a NACK or an error notification. The
DUT model is the TV (logical address 0); the scoreboard decodes the
initiator's own pulses with an independent segment-level follower and
predicts ACKs, error notifications, delivered blocks and the report. The
pins match HDMI_CEC_top in open-ip-portfolio (cec_in, cec_oe_low).""",
    defs=CEC_FUNCS,
    timeout=20000,
    cfg="""int unsigned cec_u   = 2;    // clocks per 50 us (model parameter U)
int unsigned gap_u   = 336;  // idle units after a frame (7 bit periods)
int unsigned mon_end = 192;  // monitor: idle units that close a frame""",
    interface="""interface cec_if (input logic clk);
  logic rst_n;

  logic       agent_low;    // initiator (this agent) pulls the line low
  logic       cec_oe_low;   // DUT pulls the line low
  logic       cec_in;       // line level (wired-AND)
  logic       out_valid;
  logic [7:0] out_data;
  logic       rep_valid;
  logic [2:0] rep_status;
  logic [3:0] rep_init;
  logic [3:0] rep_dest;
  logic [4:0] rep_len;

  assign cec_in = ~(agent_low | cec_oe_low);

  modport DUT (input clk, rst_n, cec_in, output cec_oe_low, out_valid, out_data, rep_valid, rep_status,
               rep_init, rep_dest, rep_len);
  modport MON (input clk, rst_n, agent_low, cec_oe_low, cec_in, out_valid, out_data, rep_valid, rep_status,
               rep_init, rep_dest, rep_len);

  clocking drv_cb @(posedge clk);
    input rst_n, cec_in, cec_oe_low, out_valid, out_data, rep_valid, rep_status, rep_init, rep_dest, rep_len;
    inout agent_low;
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, agent_low, cec_oe_low, cec_in, out_valid, out_data, rep_valid, rep_status, rep_init,
          rep_dest, rep_len;
  endclocking
endinterface
""",
    ports=[
        ("in", "logic", "cec_in"), ("out", "logic", "cec_oe_low"),
        ("out", "logic", "out_valid"), ("out", "logic [7:0]", "out_data"),
        ("out", "logic", "rep_valid"), ("out", "logic [2:0]", "rep_status"), ("out", "logic [3:0]", "rep_init"),
        ("out", "logic [3:0]", "rep_dest"), ("out", "logic [4:0]", "rep_len"),
    ],
    fields=[
        ("bit [15:0]", "seg", "req", "q"),
        ("bit [4:0]", "nack", "rsp"),
        ("bit", "epulse", "rsp"),
        ("bit [2:0]", "rstatus", "rsp"),
        ("bit [3:0]", "rinit", "rsp"),
        ("bit [3:0]", "rdest", "rsp"),
        ("bit [4:0]", "rlen", "rsp"),
        ("bit [7:0]", "odata", "rsp", "q"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [3:0]", "init", "info", "rand"),
        ("bit [3:0]", "dest", "info", "rand"),
        ("bit [3:0]", "nblk", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-9 direct to the TV, 10-12 broadcast, 13-14 to another device, 15 polling
// (header only), 16 data bit low 20 (between 1 and 0), 17 short bit period (36),
// 18 start low 60, 19 start period 100, 20 last block without EOM, 21-22 jitter,
// 23 long bit period (58), 24-31 direct to the TV
function void set(int k, bit [3:0] d, int n, bit [3:0] i = 4'h4);
  kind = k; dest = d; nblk = n; init = i;
endfunction
function bit [3:0] dest_of();
  if (kind inside {[10:12]}) return 4'hF;
  if (kind inside {13, 14}) return (dest == 4'h0 || dest == 4'hF) ? 4'h3 : dest;
  return 4'h0;
endfunction
// blocks: header, then nblk data blocks (opcode, operands) from the seed
function void blocks(output bit [7:0] b[$]);
  bit [31:0] x = seed | 1;
  b.delete();
  b.push_back({init, dest_of()});
  if (kind != 15)
    for (int i = 0; i < ((nblk == 0) ? 1 : nblk); i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      b.push_back(x[7:0]);
    end
endfunction
// pulse train in clocks (marks = agent low, spaces); u = clocks per 50 us
function void build(int unsigned u);
  bit [31:0] x = seed | 1;
  bit [7:0] b[$];
  int nbit = 0;
  int fbit;
  blocks(b);
  fbit = 1 + seed[11:4] % (10 * b.size() - 1);       // a bit of the frame after the first
  seg.delete();
  seg.push_back(((kind == 18) ? 60 : 74) * u);
  seg.push_back(((kind == 19) ? 26 : 16) * u);
  foreach (b[k])
    for (int i = 0; i < 10; i++) begin
      bit v = (i < 8) ? b[k][7 - i] : (i == 8) ? (k == b.size() - 1 && kind != 20) : 1'b1;
      int lo = (v ? 12 : 30) * u, per = 48 * u;
      nbit++;
      if (kind == 16 && nbit == fbit) lo = 20 * u;
      if (kind == 17 && nbit == fbit) per = 36 * u;
      if (kind == 23 && nbit == fbit) per = 58 * u;
      seg.push_back(lo);
      seg.push_back(per - lo);
    end
  void'(seg.pop_back());                           // the line stays high after the last bit
  if (kind inside {21, 22}) foreach (seg[i]) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    seg[i] = seg[i] + x[2:0] - 3;
  end
endfunction
""",
    drv_rsp=True,
    drv_desc="one CEC frame per item: start bit, blocks of 10 bits; reads the ACK bits, stops after a NACKed direct block or an error notification; t.seg keeps the pulses actually driven",
    drv_idle="vif.drv_cb.agent_low <= 1'b0;",
    drv_item="""
bit [16:0] q[$];
int nseg = 0, bitn = 0;
bit stop = 0;
t.build(cfg.cec_u);
@(vif.drv_cb);
foreach (t.seg[i]) q.push_back(t.seg[i]);
t.seg.delete();
t.odata.delete(); t.nack = 0; t.epulse = 0;
for (int i = 0; i < q.size() && !stop; i += 2) begin
  int lo = q[i], hi = (i + 1 < q.size()) ? q[i + 1] : 0;
  bit sampled = 1;
  vif.drv_cb.agent_low <= 1'b1;
  repeat (lo) begin @(vif.drv_cb); watch(t); end
  vif.drv_cb.agent_low <= 1'b0;
  t.seg.push_back(lo);
  if (i == 0) begin
    repeat (hi) begin @(vif.drv_cb); watch(t); end
    t.seg.push_back(hi);
    continue;
  end
  bitn++;
  for (int c = lo; c < lo + hi; c++) begin
    @(vif.drv_cb); watch(t);
    if (c + 1 == 21 * cfg.cec_u) sampled = vif.drv_cb.cec_in;
  end
  if (hi == 0) break;
  // error notification: the line is still low at the end of the bit
  if (vif.drv_cb.cec_in === 1'b0) begin t.epulse = 1; stop = 1; end
  // NACK of a direct block: stop the frame
  else if (bitn % 10 == 0 && t.dest_of() != 4'hF && sampled) stop = 1;
  if (!stop) t.seg.push_back(hi);
end
repeat (cfg.gap_u * cfg.cec_u) begin @(vif.drv_cb); watch(t); end
""",
    drv_tasks="""
bit oe_q = 0;
int unsigned oe_n = 0;
function void watch(cec_transaction t);
  if (vif.drv_cb.out_valid) t.odata.push_back(vif.drv_cb.out_data);
  if (vif.drv_cb.rep_valid) begin
    t.rstatus = vif.drv_cb.rep_status; t.rinit = vif.drv_cb.rep_init; t.rdest = vif.drv_cb.rep_dest;
    t.rlen = vif.drv_cb.rep_len;
  end
  if (vif.drv_cb.cec_oe_low === 1'b1) oe_n++;
  else if (oe_q) begin if (oe_n <= 40 * cfg.cec_u) t.nack++; else t.epulse = 1; oe_n = 0; end
  oe_q = (vif.drv_cb.cec_oe_low === 1'b1);
endfunction
""",
    mon_desc="the initiator's low pulses (agent_low) from the start bit to cfg.mon_end idle units, the follower's ACK / error pulses (cec_oe_low), delivered blocks and the report",
    mon_run="""
forever begin
  cec_transaction t;
  int unsigned n = 0, nrep = 0, oe_n = 0;
  bit lv = 1'b1, oe_q = 0;
  do @(vif.mon_cb); while (vif.mon_cb.agent_low !== 1'b1);
  t = cec_transaction::type_id::create("t");
  n = 1;
  forever begin
    @(vif.mon_cb);
    if (vif.mon_cb.out_valid) t.odata.push_back(vif.mon_cb.out_data);
    if (vif.mon_cb.rep_valid) begin
      nrep++;
      t.rstatus = vif.mon_cb.rep_status; t.rinit = vif.mon_cb.rep_init; t.rdest = vif.mon_cb.rep_dest;
      t.rlen = vif.mon_cb.rep_len;
    end
    if (vif.mon_cb.cec_oe_low === 1'b1) oe_n++;
    else if (oe_q) begin if (oe_n <= 40 * cfg.cec_u) t.nack++; else t.epulse = 1; oe_n = 0; end
    oe_q = (vif.mon_cb.cec_oe_low === 1'b1);
    if (vif.mon_cb.agent_low === lv) begin
      n++;
      if (lv == 1'b0 && n >= cfg.mon_end * cfg.cec_u && !oe_q) break;
    end else begin
      t.seg.push_back(n);
      lv = vif.mon_cb.agent_low; n = 1;
    end
  end
  if (nrep != 1) `uvm_error("MON", $sformatf("CEC: %0d reports for one frame", nrep))
  publish(t);
end
""",
    predict="""
// follower (logical address 0) run on whole pulses: marks are the initiator's
// lows, a bit's period is its mark plus the following space
int unsigned u = cfg.cec_u, n = t.seg.size();
int b = 0, k = 0;
bit [7:0] sh = 0;
bit eom = 0, ack = 0, done = 0, hdr = 0;
t.odata.delete(); t.nack = 0; t.epulse = 0;
t.rstatus = 4; t.rinit = 0; t.rdest = 0; t.rlen = 0;
if (!cec_rng(t.seg[0], 70 * u, 78 * u) || n < 2 || !cec_rng(t.seg[0] + t.seg[1], 86 * u, 94 * u)) done = 1;
for (int i = 2; i < n && !done; i += 2) begin
  int lo = t.seg[i];
  int per = (i + 1 < n) ? lo + t.seg[i + 1] : 32'h7FFF_FFFF;
  bit v;
  if (b == 9 && ack) begin v = 0; t.nack++; end
  else if (cec_rng(lo, 8 * u, 16 * u)) v = 1;
  else if (cec_rng(lo, 26 * u, 34 * u)) v = 0;
  else begin t.rstatus = 3; t.epulse = 1; done = 1; break; end
  if (b < 8) sh = {sh[6:0], v};
  else if (b == 8) eom = v;
  if (k == 0 && b == 7) begin
    t.rinit = sh[7:4]; t.rdest = sh[3:0]; hdr = 1;
    ack = (sh[3:0] == 4'h0);
  end
  if (b == 9) begin
    if (k == 0 && t.rdest != 4'h0 && t.rdest != 4'hF) begin t.rstatus = 2; done = 1; break; end
    if (k != 0) begin t.odata.push_back(sh); t.rlen++; end
    if (eom) begin t.rstatus = (t.rdest == 4'hF) ? 1 : 0; done = 1; break; end
    k++; b = 0;
  end else b++;
  // period of this bit, measured at the next falling edge (or overrun)
  if (per > 55 * u) begin t.rstatus = 3; done = 1; break; end
  if (per < 41 * u) begin t.rstatus = 3; t.epulse = 1; done = 1; break; end
end
if (!done) t.rstatus = 3;
""",
    checks="""
if (t.rstatus > 4) fail(t, "reserved status");
if (t.rstatus == 2 && t.rlen != 0) fail(t, "blocks delivered for a frame to another device");
if (t.odata.size() != t.rlen) fail(t, "delivered blocks do not match the reported length");
""",
    coverage="""
cp_status : coverpoint tr.rstatus { bins direct = {0}; bins bcast = {1}; bins other = {2}; bins bit_err = {3};
                                    bins start_err = {4}; }
cp_len    : coverpoint tr.rlen iff (tr.rstatus < 2) { bins poll = {0}; bins op = {1}; bins short_f = {[2:4]};
                                                       bins long_f = {[5:15]}; }
cp_epulse : coverpoint tr.epulse;
cp_init   : coverpoint tr.rinit iff (tr.rstatus < 3) { bins tuner = {3}; bins player = {4}; bins other = default; }
""",
    directed="""
// poll, direct frames of every length, broadcast, another device, each fault, jitter
t = item(); t.set(15, 0, 0); send(t);
t = item(); t.set(0, 0, 1); t.seed = 32'h36; send(t);                      // e.g. Standby
for (int n = 2; n <= 15; n += 3) begin t = item(); t.set(0, 0, n); t.seed = n * 977; send(t); end
t = item(); t.set(0, 0, 15, 4'hB); t.seed = 32'hBEEF; send(t);
t = item(); t.set(10, 15, 3); t.seed = 32'h84; send(t);                    // Report Physical Address
t = item(); t.set(10, 15, 1, 4'h3); send(t);
t = item(); t.set(13, 5, 2); send(t);
t = item(); t.set(13, 0, 2); send(t);
for (int s = 0; s < 3; s++) begin
  t = item(); t.set(16, 0, 4); t.seed = 32'h101 * (s + 7); send(t);
  t = item(); t.set(17, 0, 4); t.seed = 32'h202 * (s + 5); send(t);
  t = item(); t.set(23, 0, 4); t.seed = 32'h303 * (s + 3); send(t);
end
t = item(); t.set(18, 0, 2); send(t);
t = item(); t.set(19, 0, 2); send(t);
t = item(); t.set(20, 0, 3); send(t);
t = item(); t.set(0, 0, 2); send(t);
for (int s = 0; s < 4; s++) begin t = item(); t.set(21 + s[0], s[0] ? 15 : 0, 2 + s); t.seed = 32'h55 * (s + 1); send(t); end
""",
    drain_ns=20000,
    model="""
module cec_model #(parameter int U = 2, parameter logic [3:0] LA = 4'h0) (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       cec_in,
  output logic       cec_oe_low,
  output logic       out_valid,
  output logic [7:0] out_data,
  output logic       rep_valid,
  output logic [2:0] rep_status,
  output logic [3:0] rep_init,
  output logic [3:0] rep_dest,
  output logic [4:0] rep_len
);
  localparam logic [2:0] S_IDLE = 3'd0, S_STL = 3'd1, S_STH = 3'd2, S_BL = 3'd3, S_BH = 3'd4,
                         S_ERRP = 3'd5, S_WAIT = 3'd6;
  logic [2:0]  st;
  logic        lv, ack, eom;
  logic [15:0] lcnt, hcnt, dcnt;
  logic [3:0]  b;
  logic [4:0]  k;
  logic [7:0]  sh;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= S_IDLE; lv <= 1'b1; ack <= 1'b0; eom <= 1'b0; lcnt <= '0; hcnt <= '0; dcnt <= '0;
      b <= '0; k <= '0; sh <= '0;
      cec_oe_low <= 1'b0; out_valid <= 1'b0; out_data <= '0;
      rep_valid <= 1'b0; rep_status <= '0; rep_init <= '0; rep_dest <= '0; rep_len <= '0;
    end else begin : step
      logic        x, v, err, ovr, fin;
      logic [2:0]  nst;
      logic [7:0]  s2;
      logic [15:0] per;
      x = cec_in; nst = st; err = 1'b0; ovr = 1'b0; fin = 1'b0; s2 = sh;
      rep_valid <= 1'b0; out_valid <= 1'b0;
      lv <= x;
      // the ACK pulse and the error notification
      if (dcnt != 16'd0) begin
        dcnt <= dcnt - 16'd1;
        if (dcnt == 16'd1) cec_oe_low <= 1'b0;
      end
      if (!x) lcnt <= (lv) ? 16'd1 : lcnt + 16'd1;
      else    hcnt <= (!lv) ? 16'd1 : hcnt + 16'd1;
      case (st)
        S_IDLE: if (!x && lv) begin
                  nst = S_STL; rep_init <= '0; rep_dest <= '0; rep_len <= '0; k <= '0; b <= '0; ack <= 1'b0;
                end
        S_STL:  if (x && !lv) begin
                  if (lcnt >= 70 * U && lcnt <= 78 * U) nst = S_STH;
                  else begin rep_valid <= 1'b1; rep_status <= 3'd4; nst = S_WAIT; end
                end
        S_STH:  if (!x && lv) begin
                  per = lcnt + hcnt;
                  if (per >= 86 * U && per <= 94 * U) nst = S_BL;
                  else begin rep_valid <= 1'b1; rep_status <= 3'd4; nst = S_WAIT; end
                end else if (x && lcnt + hcnt + 16'd1 > 94 * U) begin
                  rep_valid <= 1'b1; rep_status <= 3'd4; nst = S_WAIT;
                end
        S_BL:   if (x && !lv) begin : bit_end
                  if (b == 4'd9 && ack) v = 1'b0;
                  else if (lcnt >= 8 * U && lcnt <= 16 * U) v = 1'b1;
                  else if (lcnt >= 26 * U && lcnt <= 34 * U) v = 1'b0;
                  else begin v = 1'b0; err = 1'b1; end
                  if (!err) begin
                    if (b < 4'd8) s2 = {sh[6:0], v};
                    if (b == 4'd8) eom <= v;
                    sh <= s2;
                    if (k == 5'd0 && b == 4'd7) begin
                      rep_init <= s2[7:4]; rep_dest <= s2[3:0]; ack <= (s2[3:0] == LA);
                    end
                    nst = S_BH;
                    if (b == 4'd9) begin
                      b <= '0;
                      if (k == 5'd0 && rep_dest != LA && rep_dest != 4'hF) begin
                        rep_valid <= 1'b1; rep_status <= 3'd2; nst = S_WAIT;
                      end else begin
                        if (k != 5'd0) begin out_valid <= 1'b1; out_data <= sh; rep_len <= rep_len + 5'd1; end
                        if (eom) begin
                          rep_valid <= 1'b1; rep_status <= (rep_dest == 4'hF) ? 3'd1 : 3'd0; nst = S_WAIT;
                        end
                        k <= k + 5'd1;
                      end
                    end else b <= b + 4'd1;
                  end
                end
        S_BH:   if (!x && lv) begin
                  per = lcnt + hcnt;
                  if (per < 41 * U) err = 1'b1;
                  else if (per > 55 * U) ovr = 1'b1;
                  else begin
                    nst = S_BL;
                    if (b == 4'd9 && ack) begin cec_oe_low <= 1'b1; dcnt <= 30 * U; end
                  end
                end else if (x && lcnt + hcnt + 16'd1 > 55 * U) ovr = 1'b1;
        S_ERRP: if (dcnt == 16'd1) nst = S_WAIT;
        S_WAIT: if (x && lv && hcnt + 16'd1 >= 96 * U) nst = S_IDLE;
        default: nst = S_IDLE;
      endcase
      if (err) begin
        rep_valid <= 1'b1; rep_status <= 3'd3;
        cec_oe_low <= 1'b1; dcnt <= 72 * U; nst = S_ERRP;
      end else if (ovr) begin
        rep_valid <= 1'b1; rep_status <= 3'd3; nst = S_WAIT;
      end
      st <= nst;
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({cec_in, cec_oe_low, rep_valid, out_valid}))
  else $error("CEC: X on the line / valids");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> rep_status <= 3'd4 && !$isunknown({rep_init, rep_dest, rep_len}))
  else $error("CEC: bad report");
assert property (@(posedge clk) disable iff (!rst_n) cec_oe_low |-> !cec_in)
  else $error("CEC: the follower pulls low but the line is high");
assert property (@(posedge clk) disable iff (!rst_n) $rose(cec_oe_low) |-> cec_oe_low [*20])
  else $error("CEC: follower pulse shorter than 0.5 ms");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd1);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_status == 3'd3);
""",
    smoke="""
int checks = 0;
int fails  = 0;
localparam integer U = 2;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic agent_low = 1'b0;
wire cec_oe_low, out_valid, rep_valid;
wire [7:0] out_data;
wire [2:0] rep_status;
wire [3:0] rep_init, rep_dest;
wire [4:0] rep_len;
wire cec_in = ~(agent_low | cec_oe_low);

always #5 clk = ~clk;

cec_model u_dut (.clk(clk), .rst_n(rst_n), .cec_in(cec_in), .cec_oe_low(cec_oe_low), .out_valid(out_valid),
                 .out_data(out_data), .rep_valid(rep_valid), .rep_status(rep_status), .rep_init(rep_init),
                 .rep_dest(rep_dest), .rep_len(rep_len));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

integer nrep = 0, nout = 0, nacks = 0, nerrp = 0, oen = 0;
logic [2:0] r_st;
logic [3:0] r_in, r_de;
logic [4:0] r_ln;
logic [7:0] ob [0:31];
always @(posedge clk) begin
  if (rep_valid) begin nrep = nrep + 1; r_st = rep_status; r_in = rep_init; r_de = rep_dest; r_ln = rep_len; end
  if (out_valid) begin ob[nout] = out_data; nout = nout + 1; end
  if (cec_oe_low) oen = oen + 1;
  else if (oen != 0) begin if (oen <= 40 * U) nacks = nacks + 1; else nerrp = nerrp + 1; oen = 0; end
end

integer r0, sampled, eperr;
// one bit: low lo units, period per units; sampled = line at 1.05 ms
task automatic cbit(input integer lo, input integer per);
  agent_low = 1;
  repeat (lo * U) @(negedge clk);
  agent_low = 0;
  for (int c = lo * U; c < per * U; c++) begin
    @(negedge clk);
    if (c + 1 == 21 * U) sampled = cec_in;
  end
  if (cec_in == 1'b0) eperr = 1;
endtask
task automatic start(input integer lo = 74, input integer per = 90);
  agent_low = 1; repeat (lo * U) @(negedge clk);
  agent_low = 0; repeat ((per - lo) * U) @(negedge clk);
endtask
task automatic idle();
  agent_low = 0; repeat (336 * U) @(negedge clk);
endtask
logic [7:0] fb [0:15];
integer fn;
// frame of fn blocks fb[]; bad = bit index (from 0, after the start bit) with low time badlo
task automatic frame(input integer bad = -1, input integer badlo = 20, input integer badper = 48,
                     input logic noeom = 0);
  integer bi;
  r0 = nrep; nout = 0; nacks = 0; nerrp = 0; eperr = 0; bi = 0;
  start();
  for (int k = 0; k < 16; k++) if (k < fn && eperr == 0) begin
    for (int i = 0; i < 10; i++) if (eperr == 0) begin
      logic v;
      v = (i < 8) ? fb[k][7 - i] : (i == 8) ? (k == fn - 1 && !noeom) : 1'b1;
      if (bi == bad) cbit(badlo, badper); else cbit(v ? 12 : 30, 48);
      bi = bi + 1;
    end
  end
  idle();
endtask
function automatic logic got(input logic [2:0] s, input logic [3:0] i, input logic [3:0] d, input integer n);
  got = (nrep == r0 + 1) && r_st == s && r_in == i && r_de == d && r_ln == n;
endfunction
function automatic logic outs(input integer n);
  logic ok;
  ok = (nout == n);
  for (int j = 0; j < 16; j++) if (j < n && ob[j] !== fb[j + 1]) ok = 0;
  outs = ok;
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0 && cec_oe_low === 1'b0, "nothing out in reset");
  rst_n = 1;
  repeat (4) @(negedge clk);
  fn = 1; fb[0] = 8'h40; frame(); chk(got(0, 4, 0, 0) && nacks == 1, "polling 4 -> 0: ACK, no data");
  fn = 2; fb[1] = 8'h36; frame(); chk(got(0, 4, 0, 1) && outs(1) && nacks == 2, "Standby: header and opcode ACKed");
  fn = 4; fb[0] = 8'h30; fb[1] = 8'h82; fb[2] = 8'h10; fb[3] = 8'h00; frame();
  chk(got(0, 3, 0, 3) && outs(3) && nacks == 4, "Active Source 3 -> 0 with two operands");
  fn = 16; fb[0] = 8'hB0; for (int j = 1; j < 16; j++) fb[j] = 8'h11 * j; frame();
  chk(got(0, 4'hB, 0, 15) && outs(15) && nacks == 16, "15 data blocks");
  fn = 4; fb[0] = 8'h4F; fb[1] = 8'h84; fb[2] = 8'h10; fb[3] = 8'h00; frame();
  chk(got(1, 4, 15, 3) && outs(3) && nacks == 0, "broadcast: accepted without pulling ACK low");
  fn = 1; fb[0] = 8'h45; frame(); chk(got(2, 4, 5, 0) && nout == 0 && nacks == 0, "polling another device: NACK");
  fn = 3; fb[0] = 8'h40; fb[1] = 8'h44; fb[2] = 8'h41; frame(15, 20);
  chk(got(3, 4, 0, 0) && nerrp == 1 && eperr == 1, "data bit low 1.0 ms: error notification");
  frame(25, 30, 36); chk(got(3, 4, 0, 1) && nerrp == 1 && eperr == 1, "bit period 1.8 ms: error notification");
  frame(25, 30, 58); chk(got(3, 4, 0, 1) && nerrp == 0, "bit period 2.9 ms: overrun, no notification");
  fn = 2; fb[1] = 8'h04; frame(-1, 20, 48, 1); chk(got(3, 4, 0, 1) && outs(1) && nerrp == 0, "no EOM: the frame never ends");
  r0 = nrep; start(60, 90); idle(); chk(got(4, 0, 0, 0), "start low 3.0 ms");
  r0 = nrep; start(74, 100); idle(); chk(got(4, 0, 0, 0), "start period 5.0 ms");
  // windows: 1 low 0.4 / 0.8 ms, 0 low 1.3 / 1.7 ms, period 2.05 / 2.75 ms
  r0 = nrep; nout = 0; nacks = 0; eperr = 0; start(70, 86);
  for (int i = 0; i < 8; i++) cbit((8'h40 >> (7 - i)) & 1 ? 8 : 26, 41);
  cbit(30, 55); cbit(16, 55);
  for (int i = 0; i < 8; i++) cbit((8'h9F >> (7 - i)) & 1 ? 16 : 34, 55);
  cbit(8, 41); cbit(12, 48); idle();
  chk(got(0, 4, 0, 1) && nout == 1 && ob[0] == 8'h9F && nacks == 2, "every window edge accepted");
  fn = 2; fb[0] = 8'h40; fb[1] = 8'h8F; frame(); chk(got(0, 4, 0, 1) && outs(1), "frame after the faults");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #50000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
