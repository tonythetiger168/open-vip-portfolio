# I2S audio codec VIP, clock master (the ADC / DAC codec on an IP camera's
# microphone and speaker path, with the SoC's I2S port as the slave).
#
# Agent -> DUT: bclk, lrck (0 = left, 1 = right) and sdin (ADC data), Philips
# I2S timing: lrck and sdin change on the bclk falling edge, the MSB of a
# channel word follows one bclk after the lrck change, words are 16 bits in
# slots of 16, 18, 24 or 32 bclk periods (bits after the LSB are padding).
# bclk runs during an item (cfg.div clocks per period, plus 0, 2 or 8) and
# idles high between items (lrck is low from reset, then stays in the right
# slot between items); each item ends with one extra period so the
# slave can take the last LSB.
# DUT -> agent: sdout (DAC data), sampled on every bclk rising edge.
#
# tb/top_tb.sv i2sc_model is I2S_top of open-ip-portfolio (DW = 16) with a
# loopback client: every received word is written to the same channel's
# transmit register, so each DAC word is the ADC word of the previous frame
# (a slot shorter than 16 bits loses its word, and the older one is sent
# again). The scoreboard steps the slave's receive counter and transmit
# shift register on every bclk period and predicts each sdout bit.

SPEC = dict(
    vip="I2S_Codec-UVM-VIP", p="i2sc", P="I2SC", dir="i2sc", family="Audio",
    desc="I2S audio codec VIP as clock master: bclk / lrck generation, 16-bit ADC words in 16 / 18 / 24 / 32-bit "
         "slots, short slots, bclk rate changes, DAC capture on every bclk rise; I2S_top slave model with a "
         "loopback client, bit-exact sdout prediction.",
    about="""
An IP camera's microphone ADC and speaker DAC usually sit in one codec that
masters the I2S bus. The agent is that codec: it generates bclk and lrck,
sends stereo ADC words in several slot widths, shortens a slot below the
word length, changes the bclk rate between bursts, and samples the SoC's
DAC data on every bclk rising edge. The DUT model is the SoC's I2S slave
port with a loopback client; the scoreboard steps the slave's receive and
transmit logic on every bclk period (with its state kept across bursts) and
predicts every sdout bit, so the one-bclk Philips data delay, the padding
after the LSB and the lost short-slot word are all checked. The pins match
I2S_top in open-ip-portfolio (bclk, lrck, sdin, sdout); the slave needs
`cfg.div` of 8 clocks or more.""",
    timeout=20000,
    cfg="""int unsigned div  = 8;     // clocks per bclk period (even, >= 8 for I2S_top)
int unsigned idle = 64;    // clocks with bclk high between items""",
    ports=[
        ("in", "logic", "bclk"), ("in", "logic", "lrck"), ("in", "logic", "sdin"),
        ("out", "logic", "sdout"),
    ],
    fields=[
        ("bit [1:0]", "rises", "req", "q"),     # {lrck, sdin} at each bclk rise
        ("bit", "dout", "rsp", "q"),            # sdout at each bclk rise
        ("bit [4:0]", "kind", "info", "rand"),
        ("bit [1:0]", "nfr", "info", "rand"),
        ("bit [1:0]", "ssel", "info", "rand"),
        ("bit [1:0]", "dsel", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    tr_functions="""
// kind: 0-23 nfr + 1 stereo frames in slot_of() periods, 24-27 the first left
// slot cut to 8-15 periods, 28-31 the first right slot cut. dsel: bclk
// period cfg.div + 0 / 2 / 8 / 0.
function void set(int k, int frames = 2, int s = 0, bit [31:0] sd = 32'h1); kind = k; nfr = frames - 1; ssel = s; seed = sd; endfunction
function int ones(); int n = 0; foreach (dout[i]) n += dout[i]; return n; endfunction
function int slot_of();
  case (ssel)
    0: return 16;
    1: return 24;
    2: return 32;
    default: return 18;
  endcase
endfunction
function int period(int d);
  return d + ((dsel == 1) ? 2 : (dsel == 2) ? 8 : 0);
endfunction
// lrck / data bit per bclk period; data is the slot bit stream delayed by one period
function void build(ref bit lr [$], ref bit dat [$]);
  bit [31:0] x = seed | 1;
  bit s [$];
  int S = slot_of();
  lr.delete(); dat.delete();
  for (int f = 0; f <= nfr; f++)
    for (int ch = 0; ch < 2; ch++) begin
      int n = S;
      bit [15:0] w;
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      w = x[15:0];
      if (f == 0 && ((kind inside {[24:27]} && ch == 0) || (kind inside {[28:31]} && ch == 1))) n = 8 + x[18:16];
      for (int b = 0; b < n; b++) begin lr.push_back(ch); s.push_back((b < 16) ? w[15 - b] : 1'b0); end
    end
  lr.push_back(1'b1);                       // the extra period carries the last LSB
  dat.push_back(1'b0);
  for (int i = 0; i < s.size(); i++) dat.push_back(s[i]);
endfunction
""",
    drv_rsp=False,
    drv_desc="one burst of bclk periods per item: lrck and sdin set at each falling edge, bclk high for the second half; then bclk idles high for cfg.idle clocks",
    drv_idle="""
vif.drv_cb.bclk <= 1'b1;
vif.drv_cb.lrck <= 1'b0;
vif.drv_cb.sdin <= 1'b0;
""",
    drv_item="""
bit lr [$], dat [$];
int h = t.period(cfg.div) / 2;
t.build(lr, dat);
t.rises.delete();
foreach (lr[i]) t.rises.push_back({lr[i], dat[i]});
@(vif.drv_cb);
foreach (lr[i]) begin
  vif.drv_cb.bclk <= 1'b0; vif.drv_cb.lrck <= lr[i]; vif.drv_cb.sdin <= dat[i];
  repeat (h) @(vif.drv_cb);
  vif.drv_cb.bclk <= 1'b1;
  repeat (h) @(vif.drv_cb);
end
repeat (cfg.idle) @(vif.drv_cb);
""",
    mon_desc="{lrck, sdin} and sdout at every bclk rising edge of a burst; bclk high for more than half of cfg.idle ends it",
    mon_run="""
forever begin
  i2sc_transaction t;
  bit pb;
  int hi = 0;
  pb = vif.mon_cb.bclk;
  while (!(pb === 1'b1 && vif.mon_cb.bclk === 1'b0)) begin pb = vif.mon_cb.bclk; @(vif.mon_cb); end
  t = i2sc_transaction::type_id::create("t");
  forever begin
    pb = vif.mon_cb.bclk;
    @(vif.mon_cb);
    if (pb === 1'b0 && vif.mon_cb.bclk === 1'b1) begin
      t.rises.push_back({vif.mon_cb.lrck, vif.mon_cb.sdin});
      t.dout.push_back(vif.mon_cb.sdout);
    end
    if (vif.mon_cb.bclk === 1'b1) hi++; else hi = 0;
    if (hi > cfg.idle / 2) break;
  end
  publish(t);
end
""",
    sb_members="""// I2S_top state after reset (lrck low from reset on, so the first left
// slot of the first burst has no lrck change before it and is not taken)
bit        lrp = 0, tpend = 0, tch = 0, rpend = 0, rchn = 0, rch = 0;
bit [15:0] tsh = 0, txl = 0, txr = 0;
bit [14:0] rsh = 0;
int        rcnt = 16;""",
    predict="""
t.dout.delete();
foreach (t.rises[i]) begin
  bit lr = t.rises[i][1], sd = t.rises[i][0];
  bit [15:0] w = {rsh, sd};
  // falling edge: load on a pending lrck change, else shift; then the change
  if (tpend) begin tsh = tch ? txr : txl; tpend = 0; end
  else tsh = {tsh[14:0], 1'b0};
  if (lr != lrp) begin tpend = 1; tch = lr; rpend = 1; rchn = lr; end
  lrp = lr;
  t.dout.push_back(tsh[15]);
  // rising edge: take sdin; a complete word goes to the loopback register
  if (rcnt != 16) begin
    rsh = w[14:0];
    if (rcnt == 15) begin if (!rch) txl = w; else txr = w; end
    rcnt++;
  end
  if (rpend) begin rcnt = 0; rch = rchn; rpend = 0; end
end
""",
    checks="""
if (t.rises.size() < 33) fail(t, "burst shorter than one stereo frame");
if (t.rises.size() && t.rises[0][1] !== 1'b0) fail(t, "burst does not start with the left channel");
if (t.rises.size() && t.rises[t.rises.size() - 1][1] !== 1'b1) fail(t, "burst does not end in the right channel");
""",
    coverage="""
cp_len   : coverpoint tr.rises.size() { bins one = {[33:65]}; bins two = {[66:130]}; bins more = {[131:300]}; }
cp_first : coverpoint (tr.dout.size() > 1 ? tr.dout[1] : 1'b0);
cp_ones  : coverpoint (tr.ones() > 0) { bins silent = {0}; bins data = {1}; }
""",
    directed="""
// every slot width, short slots on each channel, bclk rate changes, long bursts
for (int s = 0; s < 4; s++)
  for (int d = 0; d < 3; d++) begin t = item(); t.set(s * 5, 1 + d, s, 32'h100 * s + d + 1); t.dsel = d; send(t); end
for (int k = 24; k < 32; k += 2) begin
  t = item(); t.set(k, 2, k % 4, 32'h4000 + k); send(t);
  t = item(); t.set(0, 2, k % 4, 32'h5000 + k); send(t);
end
t = item(); t.set(1, 4, 2, 32'hBEEF); t.dsel = 2; send(t);
""",
    drain_ns=4000,
    model="""
module i2sc_model #(parameter int DW = 16) (
  input  logic clk,
  input  logic rst_n,
  input  logic bclk,
  input  logic lrck,
  input  logic sdin,
  output logic sdout
);
  localparam int CW = $clog2(DW + 1);
  logic [DW-1:0] tx_left, tx_right;
  logic [DW-1:0] tx_shift;
  logic [DW-2:0] rx_shift;
  logic [CW-1:0] rx_cnt;
  logic          tx_pend, tx_ch, rx_pend, rx_ch_n, rx_ch;
  logic          bclk_s, bclk_d, lrck_s, lrck_d, sdin_s;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      bclk_s <= 1'b0; bclk_d <= 1'b0; lrck_s <= 1'b0; lrck_d <= 1'b0; sdin_s <= 1'b0;
    end else begin
      bclk_s <= bclk; bclk_d <= bclk_s; lrck_s <= lrck; lrck_d <= lrck_s; sdin_s <= sdin;
    end
  end
  wire bclk_rise   =  bclk_s & ~bclk_d;
  wire bclk_fall   = ~bclk_s &  bclk_d;
  wire lrck_change =  lrck_s ^  lrck_d;
  wire [DW-1:0] rx_word = {rx_shift, sdin_s};

  // transmit (I2S_top), loading the loopback registers
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_shift <= '0; tx_pend <= 1'b0; tx_ch <= 1'b0;
    end else begin
      if (bclk_fall) begin
        if (tx_pend) begin
          tx_shift <= tx_ch ? tx_right : tx_left;
          tx_pend  <= 1'b0;
        end else tx_shift <= {tx_shift[DW-2:0], 1'b0};
      end
      if (lrck_change) begin tx_pend <= 1'b1; tx_ch <= lrck_s; end
    end
  end

  // receive (I2S_top); each word written back to the same channel
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_left <= '0; tx_right <= '0; rx_shift <= '0;
      rx_cnt <= CW'(DW); rx_pend <= 1'b0; rx_ch_n <= 1'b0; rx_ch <= 1'b0;
    end else begin
      if (bclk_rise) begin
        if (rx_cnt != CW'(DW)) begin
          rx_shift <= rx_word[DW-2:0];
          rx_cnt   <= rx_cnt + 1'b1;
          if (rx_cnt == CW'(DW - 1)) begin
            if (!rx_ch) tx_left  <= rx_word;
            else        tx_right <= rx_word;
          end
        end
        if (rx_pend) begin rx_cnt <= '0; rx_ch <= rx_ch_n; rx_pend <= 1'b0; end
      end
      if (lrck_change) begin rx_pend <= 1'b1; rx_ch_n <= lrck_s; end
    end
  end

  assign sdout = tx_shift[DW-1];
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({bclk, lrck, sdin, sdout}))
  else $error("I2SC: X on the bus");
assert property (@(posedge clk) disable iff (!rst_n) $changed(lrck) |-> $fell(bclk))
  else $error("I2SC: lrck changed away from a bclk falling edge");
assert property (@(posedge clk) disable iff (!rst_n) $changed(sdin) |-> $fell(bclk))
  else $error("I2SC: sdin changed away from a bclk falling edge");
assert property (@(posedge clk) disable iff (!rst_n) $rose(bclk) |-> $stable(sdout))
  else $error("I2SC: sdout changing at the bclk rising edge");
cover property (@(posedge clk) disable iff (!rst_n) $rose(bclk) && sdout);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic bclk = 1'b1, lrck = 1'b0, sdin = 1'b0;
wire sdout;

always #5 clk = ~clk;

i2sc_model u_dut (.clk(clk), .rst_n(rst_n), .bclk(bclk), .lrck(lrck), .sdin(sdin), .sdout(sdout));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// a burst: frames of (L, R) words in slot periods; slot of channel 0 / 1 of the first frame may be cut
logic [15:0] wl [0:7], wr [0:7];
logic        lb [0:1023], db [0:1023], ob [0:1023];
integer      nb = 0;
task automatic burst(input integer nfr, input integer slot, input integer h = 4, input integer cut0 = 0,
                     input integer cut1 = 0);
  integer n, k;
  nb = 0;
  db[0] = 0;
  for (int f = 0; f < nfr; f++)
    for (int ch = 0; ch < 2; ch++) begin
      n = slot;
      if (f == 0 && ch == 0 && cut0 != 0) n = cut0;
      if (f == 0 && ch == 1 && cut1 != 0) n = cut1;
      for (int b = 0; b < n; b++) begin
        lb[nb] = ch;
        db[nb + 1] = (b < 16) ? ((ch == 0) ? wl[f][15 - b] : wr[f][15 - b]) : 1'b0;
        nb = nb + 1;
      end
    end
  lb[nb] = 1; nb = nb + 1;
  for (int i = 0; i < nb; i++) begin
    @(negedge clk); bclk = 0; lrck = lb[i]; sdin = db[i];
    repeat (h) @(negedge clk);
    bclk = 1;
    repeat (h - 1) @(negedge clk);
    ob[i] = sdout;
  end
  @(negedge clk); sdin = 0;
  repeat (40) @(negedge clk);
endtask
// DAC word of slot j (start period s0): sdout at periods s0 + 1 .. s0 + 16
function automatic logic [15:0] dac(input integer s0);
  logic [15:0] w;
  for (int b = 0; b < 16; b++) w[15 - b] = ob[s0 + 1 + b];
  dac = w;
endfunction
function automatic logic pad_zero(input integer s0, input integer slot);
  logic ok;
  ok = 1;
  for (int b = 16; b < 32; b++) if (b < slot && ob[s0 + 1 + b] !== 1'b0) ok = 0;
  pad_zero = ok;
endfunction

initial begin
  repeat (3) @(posedge clk);
  chk(sdout === 1'b0, "sdout low in reset");
  rst_n = 1;
  repeat (10) @(posedge clk);
  wl[0] = 16'hA55A; wr[0] = 16'h1234; wl[1] = 16'h8001; wr[1] = 16'hFFFF; wl[2] = 16'h0F0F; wr[2] = 16'h7FFE;
  burst(3, 16);
  chk(dac(0) == 16'h0000 && dac(16) == 16'h0000, "first frame: transmit registers still 0");
  chk(dac(32) == 16'h0000 && dac(48) == 16'h1234,
      "lrck low from reset: the first left slot is not taken, the first right one is sent back");
  chk(dac(64) == 16'h8001 && dac(80) == 16'hFFFF, "frame 3 sends frame 2 back");
  wl[0] = 16'h3C3C; wr[0] = 16'hC3C3; wl[1] = 16'h0001; wr[1] = 16'h8000;
  burst(2, 24);
  chk(dac(0) == 16'h0F0F && dac(24) == 16'h7FFE, "frame 3's words come back in the next burst");
  chk(dac(48) == 16'h3C3C && dac(72) == 16'hC3C3, "24-bit slots");
  chk(pad_zero(48, 24) && pad_zero(72, 24), "padding after the LSB is 0");
  wl[0] = 16'hDEAD; wr[0] = 16'hBEEF; wl[1] = 16'h5555; wr[1] = 16'hAAAA;
  burst(2, 32, 8);
  chk(dac(0) == 16'h0001 && dac(32) == 16'h8000 && dac(64) == 16'hDEAD && dac(96) == 16'hBEEF,
      "32-bit slots at a slower bclk");
  chk(pad_zero(64, 32), "16 padding bits");
  wl[0] = 16'h1111; wr[0] = 16'h2222; wl[1] = 16'h3333; wr[1] = 16'h4444;
  burst(2, 16, 4, 10);
  chk(dac(10) == 16'hAAAA && dac(26) == 16'h5555 && dac(42) == 16'h2222,
      "left slot cut to 10 bits: word lost, the older left word is sent again");
  wl[0] = 16'h6666; wr[0] = 16'h7777; wl[1] = 16'h9999; wr[1] = 16'hEEEE;
  burst(2, 18, 4, 0, 12);
  chk(dac(0) == 16'h3333 && dac(30) == 16'h6666 && dac(48) == 16'h4444,
      "right slot cut to 12 bits: the older right word again");
  wl[0] = 16'hFFFF; wr[0] = 16'h0000;
  burst(1, 16, 5);
  chk(dac(0) == 16'h9999 && dac(16) == 16'hEEEE, "odd bclk half-period");
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
