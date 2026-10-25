# CAN / CAN FD bit-stream node (tb/top_tb.sv can_fd_model: one bit per clock
# on rx; six or more consecutive dominant (0) bits raise a one-clock
# stuff_err and bump error_cnt; tx echoes rx two clocks late on every fourth
# clock and is recessive (1) otherwise).
SPEC = dict(
    vip="CAN_FD-UVM-VIP", p="can_fd", P="CAN-FD", dir="can_fd",
    cfg="int unsigned idle_bits = 11;   // recessive bits before each frame (intermission + idle)",
    fields=[
        ("bit", "bits", "req", "q"),            # line bits: SOF, stuffed payload [, error], to the last dominant bit
        ("bit [7:0]", "stuff_errs", "rsp"),    # stuff_err pulses during the frame
        ("bit [3:0]", "error_cnt", "rsp"),     # error counter after the frame
        ("bit [7:0]", "loop_errs", "rsp"),     # clocks where tx was dominant but rx two clocks earlier was not
        # frame content the bits are built from (the monitor recovers it with
        # unstuff(); trailing recessive payload bits are idle on the line)
        ("bit [31:0]", "payload", "info", "rand"),
        ("bit [5:0]", "nbits", "info", "rand"),
        ("bit", "inject_err", "info", "rand"),  # append seven dominant bits (stuff violation)
    ],
    constraints="""
constraint c_len { nbits inside {[1:32]}; inject_err dist { 0 := 4, 1 := 1 }; }
""",
    tr_functions="""
// SOF, payload LSB first with a complement bit stuffed after five equal bits,
// optional stuff violation; trailing recessive bits are idle, not frame
function void build();
  bit last = 1'b0;
  int run = 1;
  bits.delete();
  bits.push_back(1'b0);                       // start of frame
  for (int i = 0; i < nbits; i++) begin
    bit b = payload[i];
    if (run == 5) begin                       // stuff bit
      bits.push_back(!last); last = !last; run = 1;
    end
    bits.push_back(b);
    if (b == last) run++; else begin last = b; run = 1; end
  end
  if (run == 5) bits.push_back(!last);
  if (inject_err) repeat (7) bits.push_back(1'b0);
  while (bits.size() > 1 && bits[bits.size() - 1] == 1'b1) void'(bits.pop_back());
endfunction

function void post_randomize(); build(); endfunction
""",
    drv_rsp=False,
    drv_desc="idle recessive bits, then the frame's line bits one per clock",
    drv_idle="vif.drv_cb.rx <= 1'b1;",
    drv_item="""
@(vif.drv_cb);
repeat (cfg.idle_bits) begin vif.drv_cb.rx <= 1'b1; @(vif.drv_cb); end
foreach (t.bits[i]) begin vif.drv_cb.rx <= t.bits[i]; @(vif.drv_cb); end
vif.drv_cb.rx <= 1'b1;
""",
    mon_desc="frames from SOF (after 8 idle bits) to 8 recessive bits; stuff errors and tx loopback checked",
    mon_run="""
can_fd_transaction t;
int unsigned ones = 0;
bit rx_h1 = 1, rx_h2 = 1;      // rx one and two clocks ago
bit [7:0] lerr = 0;
forever begin
  bit rx;
  @(vif.mon_cb);
  rx = vif.mon_cb.rx;
  if (vif.mon_cb.tx == 1'b0 && rx_h2 != 1'b0) lerr++;
  rx_h2 = rx_h1; rx_h1 = rx;
  if (t == null) begin
    if (rx == 1'b0 && ones >= 8) begin
      t = can_fd_transaction::type_id::create("t");
      t.bits.push_back(1'b0);
      lerr = 0;
    end
    ones = rx ? ones + 1 : 0;
  end else begin
    t.bits.push_back(rx);
    ones = rx ? ones + 1 : 0;
    if (vif.mon_cb.stuff_err) t.stuff_errs++;
    if (ones == 8) begin
      while (t.bits.size() > 1 && t.bits[t.bits.size() - 1] == 1'b1) void'(t.bits.pop_back());
      t.error_cnt = vif.mon_cb.error_cnt;
      t.loop_errs = lerr;
      t.unstuff();
      publish(t);
      t = null;
    end
  end
end
""",
    tr_members="",
    sb_members="bit [3:0] errors = 0;",
    predict="""
// a run of L >= 6 dominant bits gives one stuff_err (plus one per 16 more:
// the model's run counter is four bits wide)
int unsigned run = 0;
t.stuff_errs = 0;
for (int i = 0; i <= t.bits.size(); i++) begin
  if (i < t.bits.size() && t.bits[i] == 1'b0) run++;
  else begin
    if (run >= 6) t.stuff_errs += 1 + (run - 6) / 16;
    run = 0;
  end
end
errors += t.stuff_errs;
t.error_cnt = errors;
t.loop_errs = 0;
""",
    checks="""
if (t.loop_errs != 0) fail(t, $sformatf("%0d tx samples do not echo rx", t.loop_errs));
if (t.bits.size() == 0 || t.bits[0] != 1'b0) fail(t, "frame does not start with a dominant SOF");
""",
    coverage="""
cp_err  : coverpoint tr.inject_err;
cp_len  : coverpoint tr.nbits { bins short_ = {[1:8]}; bins mid = {[9:24]}; bins long_ = {[25:32]}; }
cp_serr : coverpoint tr.stuff_errs { bins none = {0}; bins one = {1}; bins more = {[2:$]}; }
""",
    directed="""
t = item(); t.payload = 32'h0;         t.nbits = 32; t.build(); send(t);   // maximum stuffing
t = item(); t.payload = 32'hFFFF_FFFF; t.nbits = 32; t.build(); send(t);
t = item(); t.payload = 32'h5555_5555; t.nbits = 32; t.build(); send(t);   // no stuffing
t = item(); t.payload = 32'h0000_00F0; t.nbits = 12; t.inject_err = 1; t.build(); send(t);
t = item(); t.payload = 32'h1;         t.nbits = 1;  t.inject_err = 1; t.build(); send(t);
t = item(); t.payload = 32'hA5;        t.nbits = 8;  t.build(); send(t);
""",
)
# the monitor rebuilds payload/nbits/inject_err from the line bits
SPEC["tr_functions"] += """
// inverse of build(): recover payload, nbits and the stuff violation from bits
function void unstuff();
  bit last = 1'b0;
  int run = 1, zeros = 0;
  payload = 0; nbits = 0; inject_err = 0;
  // a trailing run of seven dominant bits that follows the payload is the
  // injected violation
  for (int i = bits.size() - 1; i >= 0 && bits[i] == 1'b0; i--) zeros++;
  for (int i = 1; i < bits.size() - ((zeros >= 7) ? 7 : 0); i++) begin
    if (run == 5) begin                       // drop the stuff bit
      last = bits[i]; run = 1;
      continue;
    end
    if (nbits < 32) payload[nbits] = bits[i];
    nbits++;
    if (bits[i] == last) run++; else begin last = bits[i]; run = 1; end
  end
  inject_err = (zeros >= 7);
endfunction
"""
# SVA: tx resets to recessive (1), not 0
SPEC["patches"] = {"can_fd/sva/can_fd_compliance_checker.sv": [(
    "disable iff (1'b0) !rst_n |-> tx == '0)",
    "disable iff (1'b0) !rst_n |=> tx == 1'b1)   // recessive in reset"),
    # the model passes rx through once every 4 clocks (dly == 3); the other
    # three are IFS-recessive, so a dominant tx is followed by 3 recessive ones
    ("disable iff (!rst_n) 1'b1 |-> tx == 1'b1)",
     "disable iff (!rst_n) !tx |=> tx[*3])")]}
