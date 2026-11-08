# Consumer IR remote control VIP: NEC (incl. extended address and repeat
# codes) and Philips RC5 (incl. the RC5X 7-bit command), on the demodulated,
# active-low output of an IR receiver module (ir_in = 0 during a carrier
# burst, "mark"; 1 during a "space"). The 38 / 36 kHz carrier is not modelled.
#
# Agent -> DUT: ir_in. Timing in clocks (cfg.nec_t / cfg.rc5_h, model
# parameters T / H): NEC unit T = 562.5 us (default 8 clocks), RC5 half bit
# H = 889 us (default 14 clocks).
#   NEC frame : mark 16T, space 8T, 32 bits LSB first (addr, ~addr or the
#               high address byte, cmd, ~cmd), stop mark T. Bit = mark T, then
#               space T (0) or 3T (1).
#   NEC repeat: mark 16T, space 4T, stop mark T.
#   RC5       : 14 Manchester bits MSB first, S1 S2 T A4..A0 C5..C0; a 1 is
#               space then mark, a 0 mark then space. S2 = 0 is RC5X: cmd[6] = 1.
# DUT -> agent: one report per frame (rep_valid; rep_proto 0 NEC, 1 NEC repeat,
# 2 RC5; rep_addr, rep_cmd, rep_toggle; rep_err 0 ok, 1 NEC ~cmd check failed,
# 2 timing / framing error).
#
# tb/top_tb.sv ir_model: measures every mark / space in clocks and accepts
#   unit [T/2, 3T/2], NEC 1-space [2T, 4T], leader mark [12T, 20T], leader
#   space [6T, 10T], repeat space [3T, 5T]; RC5 half [H/2, 3H/2], full
#   (3H/2, 5H/2], a space over 5H/2 ends an RC5 frame. A first mark up to 5H/2
#   starts RC5. After a report (or an error) the model waits for 20T of space
#   before it accepts the next frame. NEC: addr == ~addr_inv gives an 8-bit
#   address, otherwise the 16-bit extended address; a repeat reports the last
#   good NEC address and command (0 after reset).

IR_FUNCS = """
// NEC / RC5 segment decoder shared by the scoreboard (independent of the
// cycle-level DUT model). seg: alternating mark, space, ..., ending with a mark;
// the space after the last mark is idle.
function automatic bit ir_in_rng(int v, int lo, int hi); return v >= lo && v <= hi; endfunction
"""

SPEC = dict(
    vip="IR_Remote-UVM-VIP", p="ir", P="IR", dir="ir", family="Consumer / TV",
    desc="Consumer IR remote VIP: NEC (extended address, repeat codes) and RC5 / RC5X frames on the demodulated "
         "active-low IR receiver output; decoder model with tolerance windows and timing / check errors.",
    about="""
A TV or set-top box decodes the remote control from a demodulating IR receiver
module, so the SoC sees a single active-low pin. The agent is the remote: it
sends NEC frames (8-bit and extended 16-bit address), NEC repeat codes,
RC5 and RC5X frames with the toggle bit, frames with timing jitter inside the
receiver's tolerance, and faults (a broken ~cmd byte, a stretched space, a
stretched RC5 half bit, a missing stop mark, an unknown leader). The DUT model
is the receiver; the scoreboard decodes the same pulse train with its own
segment-level decoder and predicts every report. Times are in clocks
(`cfg.nec_t`, `cfg.rc5_h`); set them to the IP's prescaled tick to drive real
RTL.""",
    defs=IR_FUNCS,
    timeout=4000,
    cfg="""int unsigned nec_t  = 8;    // NEC unit (562.5 us) in clocks, model parameter T
int unsigned rc5_h  = 14;   // RC5 half bit (889 us) in clocks, model parameter H
int unsigned gap    = 200;  // idle space after each frame (model re-arms after 20T)
int unsigned mon_end = 180; // monitor: a space this long closes a frame""",
    ports=[
        ("in", "logic", "ir_in"),
        ("out", "logic", "rep_valid"), ("out", "logic [1:0]", "rep_proto"), ("out", "logic [15:0]", "rep_addr"),
        ("out", "logic [7:0]", "rep_cmd"), ("out", "logic", "rep_toggle"), ("out", "logic [1:0]", "rep_err"),
    ],
    fields=[
        ("bit [15:0]", "seg", "req", "q"),
        ("bit [1:0]", "rproto", "rsp"),
        ("bit [15:0]", "raddr", "rsp"),
        ("bit [7:0]", "rcmd", "rsp"),
        ("bit", "rtog", "rsp"),
        ("bit [1:0]", "rerr", "rsp"),
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [7:0]", "addr", "info", "rand"),
        ("bit [7:0]", "addr_hi", "info", "rand"),
        ("bit [7:0]", "cmd", "info", "rand"),
        ("bit", "tog", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-9 NEC, 10-11 NEC extended address, 12-13 NEC repeat, 14 NEC ~cmd wrong,
// 15 NEC stretched space, 16-21 RC5, 22-23 RC5X (S2 = 0), 24 RC5 stretched half bit,
// 25 NEC with jitter, 26 RC5 with jitter, 27 unknown leader mark, 28 NEC without
// the stop mark, 29-31 NEC
function void set(int k, bit [7:0] a, bit [7:0] c, bit tg = 0, bit [7:0] ah = 0);
  kind = k; addr = a; cmd = c; tog = tg; addr_hi = ah;
endfunction
function bit is_rc5(); return kind inside {[16:24], 26}; endfunction
function void build(int unsigned T, int unsigned H);
  bit [31:0] x = seed | 1;
  bit [31:0] w;
  bit [13:0] r;
  bit lv [$];
  seg.delete();
  if (!is_rc5()) begin
    if (kind == 27) begin seg.push_back(6 * T); return; end
    seg.push_back(16 * T);
    if (kind inside {12, 13}) begin seg.push_back(4 * T); seg.push_back(T); return; end
    seg.push_back(8 * T);
    w = {(kind == 14) ? cmd : ~cmd, cmd, (kind inside {10, 11}) ? addr_hi : ~addr, addr};
    for (int i = 0; i < 32; i++) begin
      seg.push_back(T);
      seg.push_back(w[i] ? 3 * T : T);
    end
    if (kind == 15) seg[3 + 2 * cmd[4:0]] = 5 * T;
    if (kind == 28) void'(seg.pop_back()); else seg.push_back(T);
    if (kind == 25) foreach (seg[i]) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      seg[i] = seg[i] + x[1:0] - 2 + ((seg[i] > T) ? 0 : 1);
    end
  end else begin
    r = {1'b1, !(kind inside {22, 23}), tog, addr[4:0], cmd[5:0]};
    lv.push_back(1);                          // invisible first half of S1
    for (int i = 13; i >= 0; i--) begin
      if (i != 13) lv.push_back(r[i] ? 1'b1 : 1'b0);
      lv.push_back(r[i] ? 1'b0 : 1'b1);
    end
    // run lengths of the levels after the leading space; drop the trailing space
    while (lv.size() && lv[lv.size() - 1] == 1'b1) void'(lv.pop_back());
    begin
      int n = 0; bit cur = 0;
      for (int i = 1; i < lv.size(); i++) begin
        if (n != 0 && lv[i] != cur) begin seg.push_back(n * H); n = 0; end
        cur = lv[i]; n++;
      end
      seg.push_back(n * H);
    end
    if (kind == 24) seg[2 * cmd[1:0]] = 3 * H;
    if (kind == 26) foreach (seg[i]) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      seg[i] = seg[i] + x[1:0] - 2;
    end
  end
endfunction
""",
    drv_rsp=True,
    drv_desc="one NEC / RC5 pulse train per item (marks drive ir_in low), then cfg.gap clocks of idle; the report seen anywhere in the item is its response",
    drv_idle="vif.drv_cb.ir_in <= 1'b1;",
    drv_item="""
bit got = 0;
t.build(cfg.nec_t, cfg.rc5_h);
@(vif.drv_cb);
foreach (t.seg[i]) begin
  vif.drv_cb.ir_in <= (i % 2) ? 1'b1 : 1'b0;
  repeat (t.seg[i]) begin
    @(vif.drv_cb);
    if (vif.drv_cb.rep_valid) begin got = 1; capture(t); end
  end
end
vif.drv_cb.ir_in <= 1'b1;
repeat (cfg.gap) begin
  @(vif.drv_cb);
  if (vif.drv_cb.rep_valid) begin got = 1; capture(t); end
end
if (!got) `uvm_error("DRV", "IR: no report for a frame")
""",
    drv_tasks="""
function void capture(ir_transaction t);
  t.rproto = vif.drv_cb.rep_proto; t.raddr = vif.drv_cb.rep_addr; t.rcmd = vif.drv_cb.rep_cmd;
  t.rtog = vif.drv_cb.rep_toggle; t.rerr = vif.drv_cb.rep_err;
endfunction
""",
    mon_desc="marks and spaces on ir_in from the first mark to cfg.mon_end clocks of space, with the report the receiver gave for them",
    mon_run="""
forever begin
  ir_transaction t;
  int unsigned n = 0, nrep = 0;
  bit lv = 1'b0;
  do @(vif.mon_cb); while (vif.mon_cb.ir_in !== 1'b0);
  t = ir_transaction::type_id::create("t");
  n = 1;
  forever begin
    @(vif.mon_cb);
    if (vif.mon_cb.rep_valid) begin
      nrep++;
      t.rproto = vif.mon_cb.rep_proto; t.raddr = vif.mon_cb.rep_addr; t.rcmd = vif.mon_cb.rep_cmd;
      t.rtog = vif.mon_cb.rep_toggle; t.rerr = vif.mon_cb.rep_err;
    end
    if (vif.mon_cb.ir_in === lv) begin
      n++;
      if (lv == 1'b1 && n >= cfg.mon_end) break;
    end else begin
      t.seg.push_back(n);
      lv = vif.mon_cb.ir_in; n = 1;
    end
  end
  if (nrep != 1) `uvm_error("MON", $sformatf("IR: %0d reports for one frame", nrep))
  publish(t);
end
""",
    sb_members="""bit [15:0] last_addr = 0;
bit [7:0]  last_cmd = 0;""",
    predict="""
// state machine of the receiver, run on whole segments
int unsigned T = cfg.nec_t, H = cfg.rc5_h, n = t.seg.size();
int st = 0;            // 0 leader mark, 1 leader space, 2 bit mark, 3 bit space, 4 stop mark, 5 RC5
bit rpt = 0, done = 0;
int nb = 0, nh = 0;
bit [31:0] sh = 0;
bit hv [28];
t.rproto = 0; t.raddr = 0; t.rcmd = 0; t.rtog = 0; t.rerr = 2;
hv[0] = 1; nh = 1;
for (int i = 0; i <= n && !done; i++) begin
  bit mark = (i % 2) == 0;
  int v = (i < n) ? t.seg[i] : 32'h7FFF_FFFF;   // the last space is idle
  if (mark) begin
    case (st)
      0: if (ir_in_rng(v, 12 * T, 20 * T)) st = 1;
         else if (v <= 5 * H / 2 && v >= H / 2) begin
           int k = (v <= 3 * H / 2) ? 1 : 2;
           for (int j = 0; j < k; j++) hv[nh++] = 0;
           st = 5; t.rproto = 2;
         end else done = 1;
      2: if (ir_in_rng(v, T / 2, 3 * T / 2)) st = 3; else done = 1;
      4: begin
           if (ir_in_rng(v, T / 2, 3 * T / 2)) begin
             if (rpt) begin t.rproto = 1; t.raddr = last_addr; t.rcmd = last_cmd; t.rerr = 0; end
             else begin
               t.raddr = (sh[15:8] == ~sh[7:0]) ? {8'h00, sh[7:0]} : sh[15:0];
               t.rcmd = sh[23:16];
               if (sh[31:24] == ~sh[23:16]) begin t.rerr = 0; last_addr = t.raddr; last_cmd = t.rcmd; end
               else t.rerr = 1;
             end
           end
           done = 1;
         end
      5: begin
           int k = (v >= H / 2 && v <= 3 * H / 2) ? 1 : (v > 3 * H / 2 && v <= 5 * H / 2) ? 2 : 0;
           if (k == 0 || nh + k > 28) done = 1;
           else for (int j = 0; j < k; j++) hv[nh++] = 0;
         end
      default: done = 1;
    endcase
  end else begin
    case (st)
      1: if (ir_in_rng(v, 6 * T, 10 * T)) begin st = 2; nb = 0; end
         else if (ir_in_rng(v, 3 * T, 5 * T)) begin st = 4; rpt = 1; end
         else done = 1;
      3: if (ir_in_rng(v, T / 2, 3 * T / 2) || ir_in_rng(v, 2 * T, 4 * T)) begin
           sh[nb] = (v >= 2 * T);
           nb++;
           st = (nb == 32) ? 4 : 2;
         end else done = 1;
      5: if (v > 5 * H / 2) begin
           bit [13:0] r;
           bit ok = 1;
           if (nh == 27) hv[nh++] = 1;
           if (nh != 28) ok = 0;
           for (int b = 0; b < 14 && ok; b++) begin
             if (hv[2 * b] == hv[2 * b + 1]) ok = 0;
             r[13 - b] = hv[2 * b];
           end
           if (ok) begin
             t.rerr = 0; t.rtog = r[11]; t.raddr = {11'h0, r[10:6]}; t.rcmd = {1'b0, !r[12], r[5:0]};
           end
           done = 1;
         end else begin
           int k = (v >= H / 2 && v <= 3 * H / 2) ? 1 : (v > 3 * H / 2) ? 2 : 0;
           if (k == 0 || nh + k > 28) done = 1;
           else for (int j = 0; j < k; j++) hv[nh++] = 1;
         end
      default: done = 1;
    endcase
  end
end
""",
    checks="""
if (t.rerr == 3) fail(t, "reserved error code");
if (t.rproto == 2 && t.rerr == 0 && t.raddr[15:5] != 0) fail(t, "RC5 address wider than 5 bits");
if (t.rproto == 3) fail(t, "reserved protocol code");
""",
    coverage="""
cp_proto : coverpoint tr.rproto iff (tr.rerr == 0) { bins nec = {0}; bins repeat_c = {1}; bins rc5 = {2}; }
cp_err   : coverpoint tr.rerr { bins ok = {0}; bins cmd_check = {1}; bins timing = {2}; }
cp_ext   : coverpoint (tr.raddr[15:8] != 0) iff (tr.rproto == 0 && tr.rerr == 0) { bins std = {0}; bins ext = {1}; }
cp_rc5x  : coverpoint tr.rcmd[6] iff (tr.rproto == 2 && tr.rerr == 0) { bins rc5 = {0}; bins rc5x = {1}; }
cp_tog   : coverpoint tr.rtog iff (tr.rproto == 2 && tr.rerr == 0);
""",
    directed="""
// repeat before any frame, NEC, extended, repeat, every fault, RC5 / RC5X with both toggles
t = item(); t.set(12, 0, 0); send(t);
t = item(); t.set(0, 8'h04, 8'h08); send(t);
t = item(); t.set(0, 8'h00, 8'hFF); send(t);
t = item(); t.set(10, 8'h34, 8'h12, 0, 8'h12); send(t);
t = item(); t.set(12, 0, 0); send(t);
t = item(); t.set(14, 8'h04, 8'h55); send(t);
t = item(); t.set(13, 0, 0); send(t);
for (int c = 0; c < 4; c++) begin t = item(); t.set(15, 8'h04, 8'h20 + c * 7); send(t); end
t = item(); t.set(28, 8'h04, 8'h01); send(t);
t = item(); t.set(27, 0, 0); send(t);
t = item(); t.set(16, 5'h00, 6'h0C, 0); send(t);
t = item(); t.set(16, 5'h00, 6'h0C, 1); send(t);
t = item(); t.set(16, 5'h1F, 6'h3F, 1); send(t);
t = item(); t.set(16, 5'h15, 6'h2A, 0); send(t);
t = item(); t.set(22, 5'h05, 6'h01, 1); send(t);
for (int c = 0; c < 4; c++) begin t = item(); t.set(24, 5'h03, c); send(t); end
for (int s = 0; s < 4; s++) begin
  t = item(); t.set(25, 8'h40 + s, 8'h10 + s); t.seed = 32'h1234 * (s + 1); send(t);
  t = item(); t.set(26, 5'h0A + s, 6'h11 + s, s[0]); t.seed = 32'h4321 * (s + 1); send(t);
end
""",
    drain_ns=4000,
    model="""
module ir_model #(parameter int T = 8, parameter int H = 14) (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        ir_in,
  output logic        rep_valid,
  output logic [1:0]  rep_proto,
  output logic [15:0] rep_addr,
  output logic [7:0]  rep_cmd,
  output logic        rep_toggle,
  output logic [1:0]  rep_err
);
  localparam int GAP = 20 * T;
  localparam logic [2:0] S_IDLE = 3'd0, S_LM = 3'd1, S_LS = 3'd2, S_BM = 3'd3, S_BS = 3'd4,
                         S_STOP = 3'd5, S_RC5 = 3'd6, S_WAIT = 3'd7;
  logic [2:0]  st;
  logic        lv, rpt;
  logic [15:0] cnt;
  logic [31:0] sh;
  logic [5:0]  nb, nh;
  logic [27:0] hv;
  logic [15:0] last_addr;
  logic [7:0]  last_cmd;

  function automatic logic rng(input logic [15:0] v, input integer lo, input integer hi);
    rng = (v >= lo) && (v <= hi);
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st <= S_IDLE; lv <= 1'b1; rpt <= 1'b0; cnt <= 16'd0; sh <= '0; nb <= '0; nh <= '0; hv <= '0;
      last_addr <= '0; last_cmd <= '0;
      rep_valid <= 1'b0; rep_proto <= '0; rep_addr <= '0; rep_cmd <= '0; rep_toggle <= 1'b0; rep_err <= '0;
    end else begin : step
      logic [15:0] v;
      logic        fin, err;
      logic [1:0]  k;
      logic [2:0]  nst;
      logic [27:0] h;
      logic [5:0]  m;
      logic [13:0] r;
      logic        ok;
      rep_valid <= 1'b0;
      fin = 1'b0; err = 1'b0; nst = st; h = hv; m = nh;
      v = cnt;
      if (ir_in == lv) begin
        // segment continues: only a space can time out
        cnt <= (cnt == 16'hFFFF) ? cnt : cnt + 16'd1;
        v = cnt + 16'd1;
        if (lv) begin
          case (st)
            S_LS:   if (v > 10 * T) err = 1'b1;
            S_BS:   if (v > 4 * T) err = 1'b1;
            S_RC5:  if (v > 5 * H / 2) begin
                      if (m == 6'd27) begin h[27] = 1'b1; m = 6'd28; end
                      ok = (m == 6'd28);
                      for (int b = 0; b < 14; b++) begin
                        if (h[2 * b] == h[2 * b + 1]) ok = 1'b0;
                        r[13 - b] = h[2 * b];
                      end
                      if (ok) begin
                        rep_valid <= 1'b1; rep_proto <= 2'd2; rep_err <= 2'd0; rep_toggle <= r[11];
                        rep_addr <= {11'h0, r[10:6]}; rep_cmd <= {1'b0, ~r[12], r[5:0]};
                        nst = S_WAIT;
                      end else err = 1'b1;
                    end
            S_WAIT: if (v >= GAP) nst = S_IDLE;
            default: ;
          endcase
        end
      end else begin
        // edge: the segment of level lv and length cnt has ended
        cnt <= 16'd1;
        lv <= ir_in;
        if (!lv) begin                       // a mark ended
          case (st)
            S_LM: if (rng(v, 12 * T, 20 * T)) nst = S_LS;
                  else if (rng(v, H / 2, 5 * H / 2)) begin
                    h = '0; h[0] = 1'b1; m = 6'd1;
                    if (v > 3 * H / 2) m = 6'd3; else m = 6'd2;
                    nst = S_RC5; rep_proto <= 2'd2;
                  end else err = 1'b1;
            S_BM: if (rng(v, T / 2, 3 * T / 2)) nst = S_BS; else err = 1'b1;
            S_STOP: if (rng(v, T / 2, 3 * T / 2)) begin
                      rep_valid <= 1'b1; rep_toggle <= 1'b0;
                      if (rpt) begin
                        rep_proto <= 2'd1; rep_addr <= last_addr; rep_cmd <= last_cmd; rep_err <= 2'd0;
                      end else begin
                        rep_proto <= 2'd0;
                        rep_addr <= (sh[15:8] == ~sh[7:0]) ? {8'h00, sh[7:0]} : sh[15:0];
                        rep_cmd <= sh[23:16];
                        if (sh[31:24] == ~sh[23:16]) begin
                          rep_err <= 2'd0;
                          last_addr <= (sh[15:8] == ~sh[7:0]) ? {8'h00, sh[7:0]} : sh[15:0];
                          last_cmd <= sh[23:16];
                        end else rep_err <= 2'd1;
                      end
                      nst = S_WAIT;
                    end else err = 1'b1;
            S_RC5: begin
                     k = rng(v, H / 2, 3 * H / 2) ? 2'd1 : rng(v, 3 * H / 2 + 1, 5 * H / 2) ? 2'd2 : 2'd0;
                     if (k == 2'd0 || m + k > 28) err = 1'b1;
                     else begin
                       h[m] = 1'b0; if (k == 2'd2) h[m + 1] = 1'b0;
                       m = m + k;
                     end
                   end
            default: ;
          endcase
        end else begin                       // a space ended
          case (st)
            S_IDLE: begin nst = S_LM; rpt <= 1'b0; rep_proto <= 2'd0; end
            S_LS: if (rng(v, 6 * T, 10 * T)) begin nst = S_BM; nb <= '0; end
                  else if (rng(v, 3 * T, 5 * T)) begin nst = S_STOP; rpt <= 1'b1; end
                  else err = 1'b1;
            S_BS: if (rng(v, T / 2, 3 * T / 2) || rng(v, 2 * T, 4 * T)) begin
                    sh[nb[4:0]] <= (v >= 2 * T);
                    nb <= nb + 6'd1;
                    nst = (nb == 6'd31) ? S_STOP : S_BM;
                  end else err = 1'b1;
            S_RC5: begin
                     k = rng(v, H / 2, 3 * H / 2) ? 2'd1 : rng(v, 3 * H / 2 + 1, 5 * H / 2) ? 2'd2 : 2'd0;
                     if (k == 2'd0 || m + k > 28) err = 1'b1;
                     else begin
                       h[m] = 1'b1; if (k == 2'd2) h[m + 1] = 1'b1;
                       m = m + k;
                     end
                   end
            S_WAIT: ;                         // a mark while re-arming: keep waiting
            default: ;
          endcase
        end
      end
      if (err) begin
        rep_valid <= 1'b1; rep_err <= 2'd2; rep_addr <= '0; rep_cmd <= '0; rep_toggle <= 1'b0;
        nst = S_WAIT;
      end
      hv <= h; nh <= m;
      st <= nst;
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({ir_in, rep_valid}))
  else $error("IR: X on ir_in / rep_valid");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> !$isunknown({rep_proto, rep_addr, rep_cmd, rep_toggle, rep_err}))
  else $error("IR: X in a report");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |-> rep_err != 2'd3 && rep_proto != 2'd3)
  else $error("IR: reserved report code");
assert property (@(posedge clk) disable iff (!rst_n) rep_valid |=> !rep_valid)
  else $error("IR: two reports back to back");
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_proto == 2'd1);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_proto == 2'd2 && rep_err == 2'd0);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 2'd2);
""",
    smoke="""
int checks = 0;
int fails  = 0;
localparam integer T = 8, H = 14;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic ir_in = 1'b1;
wire rep_valid, rep_toggle;
wire [1:0] rep_proto, rep_err;
wire [15:0] rep_addr;
wire [7:0] rep_cmd;

always #5 clk = ~clk;

ir_model u_dut (.clk(clk), .rst_n(rst_n), .ir_in(ir_in), .rep_valid(rep_valid), .rep_proto(rep_proto),
                .rep_addr(rep_addr), .rep_cmd(rep_cmd), .rep_toggle(rep_toggle), .rep_err(rep_err));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

integer nrep = 0;
logic [1:0] r_pr, r_er;
logic [15:0] r_ad;
logic [7:0] r_cm;
logic r_tg;
always @(posedge clk) if (rep_valid) begin
  nrep = nrep + 1; r_pr = rep_proto; r_ad = rep_addr; r_cm = rep_cmd; r_tg = rep_toggle; r_er = rep_err;
end

integer r0;
task automatic lvl(input logic l, input integer n);
  ir_in = l;
  repeat (n) @(negedge clk);
endtask
task automatic idle();
  lvl(1, 200);
endtask
task automatic nec(input logic [31:0] w, input integer stretch_bit = -1, input logic stop = 1);
  r0 = nrep;
  lvl(0, 16 * T); lvl(1, 8 * T);
  for (int i = 0; i < 32; i++) begin
    lvl(0, T);
    lvl(1, (i == stretch_bit) ? 5 * T : (w[i] ? 3 * T : T));
  end
  if (stop) lvl(0, T);
  idle();
endtask
task automatic nec_rpt();
  r0 = nrep;
  lvl(0, 16 * T); lvl(1, 4 * T); lvl(0, T); idle();
endtask
// RC5: bits MSB first, half bits of H clocks (1 = space then mark); an extra
// clock count for half bit number long_h stretches it
task automatic rc5(input logic [13:0] r, input integer long_h = -1);
  integer hn;
  r0 = nrep; hn = 0;
  for (int i = 13; i >= 0; i--) begin
    if (i != 13) begin ir_in = r[i] ? 1'b1 : 1'b0; repeat ((hn == long_h) ? 3 * H : H) @(negedge clk); end
    hn = hn + 1;
    ir_in = r[i] ? 1'b0 : 1'b1; repeat ((hn == long_h) ? 3 * H : H) @(negedge clk);
    hn = hn + 1;
  end
  idle();
endtask
function automatic logic got(input logic [1:0] pr, input logic [15:0] ad, input logic [7:0] cm,
                             input logic tg, input logic [1:0] er);
  got = (nrep == r0 + 1) && r_pr == pr && r_ad == ad && r_cm == cm && r_tg == tg && r_er == er;
endfunction
function automatic logic [31:0] w8(input logic [7:0] a, input logic [7:0] c);
  w8 = {~c, c, ~a, a};
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(rep_valid === 1'b0, "no report in reset");
  rst_n = 1;
  repeat (4) @(negedge clk);
  nec_rpt(); chk(got(1, 0, 0, 0, 0), "repeat before any frame: last address/command 0");
  nec(w8(8'h04, 8'h08)); chk(got(0, 16'h0004, 8'h08, 0, 0), "NEC 0x04 / 0x08");
  nec(w8(8'h00, 8'hFF)); chk(got(0, 16'h0000, 8'hFF, 0, 0), "NEC 0x00 / 0xFF");
  nec_rpt(); chk(got(1, 16'h0000, 8'hFF, 0, 0), "repeat: last frame's address and command");
  nec({~8'h12, 8'h12, 8'h12, 8'h34}); chk(got(0, 16'h1234, 8'h12, 0, 0), "extended NEC address 0x1234");
  nec({8'h55, 8'h12, ~8'h04, 8'h04}); chk(got(0, 16'h0004, 8'h12, 0, 1), "~cmd wrong: check error");
  nec_rpt(); chk(got(1, 16'h1234, 8'h12, 0, 0), "repeat ignores the failed frame");
  nec(w8(8'h04, 8'h33), 7); chk(got(0, 0, 0, 0, 2), "5T space in bit 7: timing error");
  nec(w8(8'h04, 8'h33), -1, 0); chk(got(0, 0, 0, 0, 2), "no stop mark: timing error");
  r0 = nrep; lvl(0, 6 * T); idle(); chk(got(0, 0, 0, 0, 2), "6T leader: unknown frame");
  r0 = nrep; lvl(0, 16 * T); lvl(1, 12 * T); lvl(0, T); idle(); chk(got(0, 0, 0, 0, 2), "12T leader space");
  nec(w8(8'h77, 8'h66)); chk(got(0, 16'h0077, 8'h66, 0, 0), "NEC after the faults");
  rc5({1'b1, 1'b1, 1'b0, 5'h00, 6'h0C}); chk(got(2, 0, 8'h0C, 0, 0), "RC5 TV standby, toggle 0");
  rc5({1'b1, 1'b1, 1'b1, 5'h00, 6'h0C}); chk(got(2, 0, 8'h0C, 1, 0), "RC5 toggle 1");
  rc5({1'b1, 1'b1, 1'b1, 5'h1F, 6'h3F}); chk(got(2, 16'h001F, 8'h3F, 1, 0), "RC5 all ones");
  rc5({1'b1, 1'b1, 1'b0, 5'h15, 6'h2A}); chk(got(2, 16'h0015, 8'h2A, 0, 0), "RC5 alternating bits");
  rc5({1'b1, 1'b1, 1'b0, 5'h00, 6'h00}); chk(got(2, 0, 0, 0, 0), "RC5 zeros (ends on a space)");
  rc5({1'b1, 1'b0, 1'b1, 5'h05, 6'h01}); chk(got(2, 16'h0005, 8'h41, 1, 0), "RC5X: S2 = 0 sets cmd bit 6");
  rc5({1'b1, 1'b1, 1'b0, 5'h03, 6'h12}, 9); chk(got(2, 0, 0, 0, 2), "RC5 half bit 3H: error");
  // tolerance: every segment 1 clock long / short
  r0 = nrep; lvl(0, 16 * T + 1); lvl(1, 8 * T - 1);
  for (int i = 0; i < 32; i++) begin lvl(0, T - 1); lvl(1, (w8(8'hA5, 8'h5A) >> i) & 1 ? 3 * T + 1 : T + 1); end
  lvl(0, T + 1); idle(); chk(got(0, 16'h00A5, 8'h5A, 0, 0), "NEC with jitter inside the windows");
  nec_rpt(); chk(got(1, 16'h00A5, 8'h5A, 0, 0), "repeat after the jittered frame");
  // a mark while re-arming is ignored
  r0 = nrep; lvl(0, 16 * T); lvl(1, 4 * T); lvl(0, T); lvl(1, 50); lvl(0, 3); lvl(1, 50); lvl(0, 40); idle();
  chk(got(1, 16'h00A5, 8'h5A, 0, 0), "marks while re-arming (under 20T of space) are ignored");
  r0 = nrep; lvl(0, 3); idle(); chk(got(0, 0, 0, 0, 2), "3-clock glitch once armed: error");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #20000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
