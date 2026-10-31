# SpaceWire link agent (ECSS-E-ST-50-12C): Data-Strobe encoded serial link,
# character level and exchange level. The agent is the link end that sends
# packets and time-codes; the DUT is the receiving node, which sends NULLs
# and flow-control tokens back.
#
# Wires: din / sin (agent to DUT), dout / sout (DUT to agent). D carries the
# bit; S toggles on every bit where D does not, so D xor S changes once per
# bit. Agent bits last cfg.bitclk system clocks, the DUT's 3 clocks.
# Characters: parity bit, data-control flag, then 8 data bits LSB first (data)
# or 2 control bits (sent first, second): FCT 0 0, EOP 0 1, EEP 1 0, ESC 1 1.
# NULL = ESC FCT, time-code = ESC + data character. Odd parity over the
# previous character's data / control bits and the parity bit and flag of
# this one; the first character after a link (re)start has no previous bits.
# Flow control: the agent sends an N-char (data, EOP, EEP) only while it holds
# credit; every FCT from the DUT grants 8.
#
# tb/top_tb.sv spacewire_model: holds its transmitter silent for 40 clocks
# after reset, then sends NULLs; once it has received a NULL it sends an FCT
# whenever the credit it has given is 8 or less (16 at most outstanding). A
# receiver starts at the first bit after 12 quiet clocks. Reports one clock
# after: an EOP / EEP (packet length, CRC-32 of the data, end marker), a
# time-code (value, tick = time value was the previous one + 1, modulo 64), or
# an error (length and CRC of the packet so far, code 1 parity, 2 escape:
# ESC followed by ESC / EOP / EEP, 4 credit: an N-char without credit). An
# error resets the link: transmitter silent for 40 clocks, credit and the
# received-NULL state cleared, the receiver restarts after the line goes
# quiet. The agent sees the silence (12 quiet clocks), drops what it had not
# yet sent, stays silent for 40 clocks and starts again with NULLs.

SPW_FUNCS = """
// IEEE CRC-32 step (reflected), for the packet fingerprint
function automatic bit [31:0] spw_crc32(bit [31:0] c, bit [7:0] b);
  c ^= {24'h0, b};
  for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  return c;
endfunction
// control codes as {second bit, first bit}
localparam bit [1:0] SPW_FCT = 2'b00, SPW_EOP = 2'b10, SPW_EEP = 2'b01, SPW_ESC = 2'b11;
localparam int SPW_QUIET = 12;     // quiet clocks: a receiver restarts / the link is down
localparam int SPW_SILENT = 40;    // clocks a link end stays silent after a link error
"""

SPEC = dict(
    vip="SpaceWire-UVM-VIP", p="spacewire", P="SpaceWire", dir="spacewire", family="Aerospace",
    desc="SpaceWire link VIP (ECSS-E-ST-50-12C): Data-Strobe encoding, character parity, NULL / FCT flow "
         "control with credit, packets ended by EOP / EEP, time-codes, parity / escape / credit errors and link restart.",
    about="""
SpaceWire is the ECSS link and network standard used on board spacecraft
between instruments, mass memory and processors. Each link end sends bits
Data-Strobe encoded, packs them into parity-protected characters, and may send
data only against credit the other end grants with flow-control tokens; a
parity, escape or credit error resets the link, which then restarts with
NULLs. The DUT model is the receiving node of a link: it sends NULLs and FCTs
back, checks every character and reports packets, time-codes and errors. The
agent runs the transmit side and its flow control (it decodes the FCTs coming
back and stops when its credit runs out); the scoreboard predicts each report,
including the cut packet and error code after a planted parity or escape
fault and the time-code tick. The monitor rebuilds packets from the D / S
wires.""",
    defs=SPW_FUNCS,
    timeout=400,
    ports=[
        ("in", "logic", "din"), ("in", "logic", "sin"),
        ("out", "logic", "dout"), ("out", "logic", "sout"),
        ("out", "logic", "rep_valid"), ("out", "logic", "rep_kind"), ("out", "logic [15:0]", "rep_len"),
        ("out", "logic [31:0]", "rep_crc"), ("out", "logic", "rep_eop"), ("out", "logic [2:0]", "rep_err"),
        ("out", "logic [7:0]", "rep_tc"), ("out", "logic", "rep_tick"),
    ],
    cfg="int unsigned bitclk = 2;   // system clocks per transmitted bit",
    fields=[
        ("bit", "kind", "req"),                 # 0 packet, 1 time-code
        ("bit [7:0]", "data", "req", "q"),
        ("bit", "eep", "req"),                  # end the packet with EEP
        ("bit [7:0]", "tc", "req"),
        ("bit [1:0]", "fault", "req"),          # 1 parity error on data[fpos], 2 ESC + EOP before data[fpos]
        ("bit [5:0]", "fpos", "req"),
        ("bit [15:0]", "rlen", "rsp"),
        ("bit [31:0]", "rcrc", "rsp"),
        ("bit", "reop", "rsp"),
        ("bit [2:0]", "err", "rsp"),
        ("bit [7:0]", "rtc", "rsp"),
        ("bit", "tick", "rsp"),
        ("bit [5:0]", "nbytes", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_kind  { kind dist { 0 := 8, 1 := 2 }; }
constraint c_len   { nbytes dist { 0 := 1, [1:8] :/ 6, [9:40] :/ 4 }; }
constraint c_fault { fault dist { 0 := 14, 1 := 1, 2 := 1 }; eep dist { 0 := 6, 1 := 1 }; }
""",
    tr_functions="""
// packet data from the seed; a time-code carries no packet fields and a
// packet no time-code, and a fault falls inside the data
function void post_randomize();
  bit [31:0] x = seed | 1;
  data.delete();
  for (int i = 0; i < nbytes; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    data.push_back(x[7:0]);
  end
  if (kind) begin data.delete(); eep = 0; fault = 0; end
  else tc = 0;
  if (data.size() == 0 || fault == 3) fault = 0;
  fpos = (fault != 0) ? x[15:8] % data.size() : 0;
endfunction
""",
    drv_rsp=False,
    drv_desc="link transmitter: Data-Strobe bits, characters with parity, NULLs when idle, N-chars only against the credit from received FCTs, time-codes; drops its queue and restarts the link when the DUT goes silent",
    drv_members="""
// link state, kept by the background process
int unsigned credit = 0;          // N-chars granted by FCTs and not yet sent
bit [10:0] txq[$];                // {no credit needed, parity flip, control, value}
bit [7:0]  tcq[$];                // time-codes to send
bit [9:0]  pend[$];               // characters to send next: {parity flip, control, value}
int unsigned cur_n = 0;           // bits of the current character still to send
int unsigned sil = SPW_SILENT;    // clocks of silence left (link start / restart)
int unsigned resets = 0;          // link restarts seen""",
    drv_idle="""
vif.drv_cb.din <= 1'b0;
vif.drv_cb.sin <= 1'b0;
""",
    drv_bg="""
bit d_p = 0, s_p = 0, rx_on = 0, rxf = 0, rx_esc = 0;
bit d_o = 0, s_o = 0, tx_par = 0;
int unsigned quiet = 0, rnb = 0, tb = 0;
bit [7:0] rsh = 0;
bit [9:0] cur = 0;
forever begin
  bit d, s, ev;
  @(vif.drv_cb);
  // receiver: FCTs grant credit; the DUT going quiet is a link reset
  d = vif.drv_cb.dout; s = vif.drv_cb.sout;
  ev = (d != d_p) ^ (s != s_p);
  if (d != d_p && s != s_p) quiet = 0;
  d_p = d; s_p = s;
  if (ev) begin
    if (!rx_on && quiet >= SPW_QUIET) begin rx_on = 1; rnb = 0; rx_esc = 0; end
    quiet = 0;
    if (rx_on) begin
      if (rnb == 1) rxf = d;
      if (rnb >= 2) rsh = {d, rsh[7:1]};
      rnb++;
      if (rnb >= 4 && rnb == (rxf ? 4 : 10)) begin
        if (rxf) begin
          if (rsh[7:6] == SPW_FCT && !rx_esc) credit += 8;
          rx_esc = (rsh[7:6] == SPW_ESC);
        end else rx_esc = 0;
        rnb = 0;
      end
    end
  end else if (quiet < 1000) quiet++;
  if (rx_on && quiet == SPW_QUIET) begin
    rx_on = 0; credit = 0; txq.delete(); pend.delete(); cur_n = 0; sil = SPW_SILENT; resets++;
  end
  // transmitter
  if (sil != 0) begin
    sil--; d_o = 0; s_o = 0; tx_par = 0; tb = 0;
  end else begin
    if (tb == 0) begin
      bit b;
      if (cur_n == 0) begin
        bit [9:0] c;
        if (pend.size() == 0) begin
          if (tcq.size() != 0) begin
            pend.push_back({1'b0, 1'b1, 8'(SPW_ESC)});
            pend.push_back({1'b0, 1'b0, tcq.pop_front()});
          end else if (txq.size() != 0 && (txq[0][10] || credit != 0)) begin
            bit [10:0] q = txq.pop_front();
            if (!q[10]) credit--;
            pend.push_back(q[9:0]);
          end else begin
            pend.push_back({1'b0, 1'b1, 8'(SPW_ESC)});
            pend.push_back({1'b0, 1'b1, 8'(SPW_FCT)});
          end
        end
        c = pend.pop_front();
        if (c[8]) begin                     // control: P, 1, first bit, second bit
          cur = {6'b0, c[1], c[0], 1'b1, tx_par ^ c[9]};
          cur_n = 4;
          tx_par = c[1] ^ c[0];
        end else begin                      // data: P, 0, 8 bits LSB first
          cur = {c[7:0], 1'b0, !tx_par ^ c[9]};
          cur_n = 10;
          tx_par = ^c[7:0];
        end
      end
      b = cur[0];
      cur = cur >> 1;
      cur_n--;
      if (b == d_o) s_o = !s_o;
      d_o = b;
    end
    tb = (tb + 1 == cfg.bitclk) ? 0 : tb + 1;
  end
  vif.drv_cb.din <= d_o;
  vif.drv_cb.sin <= s_o;
end
""",
    drv_item="""
int unsigned r0 = resets, n = 0;
if (t.kind) tcq.push_back(t.tc);
else begin
  foreach (t.data[i]) begin
    if (t.fault == 2 && i == t.fpos) begin
      txq.push_back({1'b1, 1'b0, 1'b1, 8'(SPW_ESC)});
      txq.push_back({1'b1, 1'b0, 1'b1, 8'(SPW_EOP)});
    end
    txq.push_back({1'b0, t.fault == 1 && i == t.fpos, 1'b0, t.data[i]});
  end
  txq.push_back({1'b0, 1'b0, 1'b1, 8'(t.eep ? SPW_EEP : SPW_EOP)});
end
if (t.fault != 0) begin
  // the link goes down at the fault: the DUT only saw the data before it
  while (resets == r0 && n < 40 * cfg.timeout_cycles) begin @(vif.drv_cb); n++; end
  if (resets == r0) `uvm_error("DRV", "SpaceWire: no link reset after a planted fault")
  while (t.data.size() > t.fpos) void'(t.data.pop_back());
  t.eep = 0;
end else begin
  while ((txq.size() != 0 || tcq.size() != 0 || pend.size() != 0 || cur_n != 0) && n < 40 * cfg.timeout_cycles) begin
    @(vif.drv_cb); n++;
  end
  if (n >= 40 * cfg.timeout_cycles) `uvm_error("TIMEOUT", "SpaceWire: characters not sent (no credit?)")
  if (resets != r0) `uvm_error("DRV", "SpaceWire: link reset without a fault")
end
""",
    mon_desc="characters decoded from the D / S wires: packets up to EOP / EEP, time-codes, parity and escape faults; completed by the DUT's report",
    mon_members="spacewire_transaction done_q[$], rep_q[$];",
    mon_run="""
bit d_p = 0, s_p = 0, on = 0, f = 0, p = 0, par = 0, esc = 0;
int unsigned quiet = 0, nb = 0;
bit [7:0] sh = 0;
bit [7:0] data[$];
forever begin
  @(vif.mon_cb);
  if (vif.mon_cb.rep_valid) begin
    spacewire_transaction r = spacewire_transaction::type_id::create("r");
    r.rlen = vif.mon_cb.rep_len; r.rcrc = vif.mon_cb.rep_crc; r.reop = vif.mon_cb.rep_eop;
    r.err = vif.mon_cb.rep_err; r.rtc = vif.mon_cb.rep_tc; r.tick = vif.mon_cb.rep_tick;
    rep_q.push_back(r);
  end
  if ((vif.mon_cb.din != d_p) && (vif.mon_cb.sin != s_p)) quiet = 0;   // lines dropped
  else if ((vif.mon_cb.din != d_p) || (vif.mon_cb.sin != s_p)) begin
    bit d = vif.mon_cb.din;
    if (!on && quiet >= SPW_QUIET) begin on = 1; nb = 0; par = 0; esc = 0; data.delete(); end
    quiet = 0;
    if (on) begin
      if (nb == 0) p = d;
      else if (nb == 1) begin
        f = d;
        if ((p ^ d ^ par) != 1'b1) begin item(data, 0, 1); on = 0; end
      end else sh = {d, sh[7:1]};
      if (on) nb++;
      if (on && nb >= 4 && nb == (f ? 4 : 10)) begin
        nb = 0;
        if (f) begin
          bit [1:0] c = sh[7:6];
          par = c[1] ^ c[0];
          if (esc) begin
            esc = 0;
            if (c != SPW_FCT) begin item(data, 0, 2); on = 0; end
          end else if (c == SPW_ESC) esc = 1;
          else if (c != SPW_FCT) begin item(data, c == SPW_EEP, 0); data.delete(); end
        end else begin
          par = ^sh;
          if (esc) begin esc = 0; tc_item(sh); end
          else data.push_back(sh);
        end
      end
    end
  end else if (quiet < 1000) quiet++;
  d_p = vif.mon_cb.din; s_p = vif.mon_cb.sin;
  while (done_q.size() != 0 && rep_q.size() != 0) begin
    spacewire_transaction t = done_q.pop_front(), r = rep_q.pop_front();
    t.rlen = r.rlen; t.rcrc = r.rcrc; t.reop = r.reop; t.err = r.err; t.rtc = r.rtc; t.tick = r.tick;
    publish(t);
  end
end
""",
    mon_tasks="""
function void item(bit [7:0] data[$], bit eep, bit [1:0] fault);
  spacewire_transaction t = spacewire_transaction::type_id::create("t");
  t.kind = 0; t.eep = eep; t.fault = fault;
  foreach (data[i]) t.data.push_back(data[i]);
  t.fpos = (fault != 0) ? data.size() : 0;
  done_q.push_back(t);
endfunction
function void tc_item(bit [7:0] v);
  spacewire_transaction t = spacewire_transaction::type_id::create("t");
  t.kind = 1; t.tc = v;
  done_q.push_back(t);
endfunction
""",
    sb_members="bit [5:0] last_tc = 0;",
    predict="""
bit [31:0] c = 32'hFFFF_FFFF;
t.rlen = 0; t.rcrc = 0; t.reop = 0; t.err = 0; t.rtc = 0; t.tick = 0;
if (t.kind) begin
  t.rtc = t.tc;
  t.tick = (t.tc[5:0] == 6'(last_tc + 1));
  last_tc = t.tc[5:0];
end else begin
  foreach (t.data[i]) c = spw_crc32(c, t.data[i]);
  t.rlen = t.data.size(); t.rcrc = ~c;
  if (t.fault != 0) t.err = (t.fault == 1) ? 3'd1 : 3'd2;
  else t.reop = !t.eep;
end
""",
    checks="""
if (t.err == 4) fail(t, "credit error: the agent sent an N-char without credit");
if (!t.kind && t.fault == 0 && t.err != 0) fail(t, "DUT reported an error on a clean packet");
""",
    coverage="""
cp_kind  : coverpoint tr.kind;
cp_len   : coverpoint tr.data.size() { bins empty = {0}; bins short_ = {[1:8]}; bins credit1 = {[9:16]}; bins long_ = {[17:$]}; }
cp_end   : coverpoint {tr.fault != 0, tr.eep} iff (!tr.kind) { bins eop = {2'b00}; bins eep = {2'b01}; bins cut = {2'b10}; }
cp_fault : coverpoint tr.fault { bins none = {0}; bins parity = {1}; bins escape = {2}; }
cp_tick  : coverpoint tr.tick iff (tr.kind);
cp_flags : coverpoint tr.tc[7:6] iff (tr.kind);
x_len_fault : cross cp_len, cp_fault { ignore_bins empty_fault = binsof(cp_len.empty) && !binsof(cp_fault.none); }
""",
    directed="""
// the CRC-32 check string, an empty packet, EEP, then packets longer than
// one and two FCTs of credit
begin
  string cv = "123456789";
  t = item(); foreach (cv[i]) t.data.push_back(cv[i]); send(t);
end
t = item(); send(t);
t = item(); t.eep = 1; t.data = '{8'hDE, 8'hAD}; send(t);
t = item(); for (int i = 0; i < 12; i++) t.data.push_back(8'(i)); send(t);
t = item(); for (int i = 0; i < 40; i++) t.data.push_back(8'(255 - i)); send(t);
// time-codes: in sequence (tick), a jump (no tick), the wrap 63 -> 0, flags
t = item(); t.kind = 1; t.tc = 8'h01; send(t);
t = item(); t.kind = 1; t.tc = 8'h02; send(t);
t = item(); t.kind = 1; t.tc = 8'h09; send(t);
t = item(); t.kind = 1; t.tc = 8'h3F; send(t);
t = item(); t.kind = 1; t.tc = 8'h00; send(t);
t = item(); t.kind = 1; t.tc = 8'hC1; send(t);
// planted faults: the link resets, the packet is cut, the next one is fine
t = item(); t.data = '{8'h11, 8'h22, 8'h33, 8'h44}; t.fault = 1; t.fpos = 2; send(t);
t = item(); t.data = '{8'h55, 8'h66}; send(t);
t = item(); t.data = '{8'h77, 8'h88, 8'h99}; t.fault = 2; t.fpos = 1; send(t);
t = item(); t.kind = 1; t.tc = 8'h01; send(t);
t = item(); t.data = '{8'hAB}; t.fault = 1; t.fpos = 0; send(t);
t = item(); for (int i = 0; i < 20; i++) t.data.push_back(8'(i * 3)); t.eep = 1; send(t);
t = item(); for (int i = 0; i < 20; i++) t.data.push_back(8'(i * 5)); t.fault = 2; t.fpos = 17; send(t);
t = item(); t.data = '{8'h01}; send(t);
""",
    drain_ns=3000,
    model="""
module spacewire_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        din,
  input  logic        sin,
  output logic        dout,
  output logic        sout,
  output logic        rep_valid,
  output logic        rep_kind,
  output logic [15:0] rep_len,
  output logic [31:0] rep_crc,
  output logic        rep_eop,
  output logic [2:0]  rep_err,
  output logic [7:0]  rep_tc,
  output logic        rep_tick
);
  localparam int TXB = 3, QUIET = 12, SILENT = 40;

  function automatic logic [31:0] crc32_byte(input logic [31:0] c, input logic [7:0] b);
    logic [31:0] x;
    x = c ^ {24'h0, b};
    for (int k = 0; k < 8; k++) x = x[0] ? (x >> 1) ^ 32'hEDB8_8320 : (x >> 1);
    crc32_byte = x;
  endfunction

  // receiver
  logic        d_p, s_p, rx_on, p, f, par, esc, got_null;
  logic [5:0]  quiet;
  logic [3:0]  nb;
  logic [7:0]  sh;
  logic [4:0]  outst;          // credit given and not yet used
  logic [15:0] len;
  logic [31:0] crc;
  logic [5:0]  last_tc;
  // transmitter
  logic [5:0]  err_t;          // silent clocks left
  logic [1:0]  tb;
  logic [9:0]  tx_sh;
  logic [3:0]  tx_n;
  logic        tx_par, tx_fct_next;

  // a bit: exactly one of D and S changes (both at once is a link end
  // dropping its lines, not a bit)
  wire ev = (din != d_p) ^ (sin != s_p);
  wire drop = (din != d_p) && (sin != s_p);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      d_p <= 1'b0; s_p <= 1'b0; rx_on <= 1'b0; p <= 1'b0; f <= 1'b0; par <= 1'b0; esc <= 1'b0; got_null <= 1'b0;
      quiet <= '0; nb <= '0; sh <= '0; outst <= '0; len <= '0; crc <= '1; last_tc <= '0;
      err_t <= 6'(SILENT); tb <= '0; tx_sh <= '0; tx_n <= '0; tx_par <= 1'b0; tx_fct_next <= 1'b0;
      dout <= 1'b0; sout <= 1'b0;
      rep_valid <= 1'b0; rep_kind <= 1'b0; rep_len <= '0; rep_crc <= '0; rep_eop <= 1'b0;
      rep_err <= '0; rep_tc <= '0; rep_tick <= 1'b0;
    end else begin : run
      logic [2:0] e;
      logic       use_credit, give_credit;
      e = 3'd0; use_credit = 1'b0; give_credit = 1'b0;
      d_p <= din; s_p <= sin;
      quiet <= (ev || drop) ? 6'd0 : (quiet == 6'd63 ? quiet : quiet + 6'd1);
      rep_valid <= 1'b0;

      // ---- receiver
      if (err_t != 0) rx_on <= 1'b0;
      else if (ev && !rx_on) begin
        if (quiet >= 6'(QUIET)) begin            // first bit after quiet: a parity bit
          rx_on <= 1'b1; p <= din; nb <= 4'd1; par <= 1'b0; esc <= 1'b0;
        end
      end else if (ev && rx_on) begin
        if (nb == 4'd0) begin p <= din; nb <= 4'd1; end
        else if (nb == 4'd1) begin
          f <= din; nb <= 4'd2;
          if ((p ^ din ^ par) != 1'b1) e = 3'd1;  // odd parity
        end else if (nb == (f ? 4'd3 : 4'd9)) begin : char_done
          logic [7:0] v;
          logic [1:0] c;
          v = {din, sh[7:1]};
          c = {din, sh[7]};
          nb <= 4'd0;
          if (f) begin
            par <= c[1] ^ c[0];
            if (esc) begin
              esc <= 1'b0;
              if (c == 2'b00) got_null <= 1'b1;     // NULL
              else e = 3'd2;                         // ESC + ESC / EOP / EEP
            end else if (c == 2'b11) esc <= 1'b1;
            else if (c != 2'b00) begin               // EOP / EEP
              if (outst == 0) e = 3'd4;
              else begin
                use_credit = 1'b1;
                rep_valid <= 1'b1; rep_kind <= 1'b0; rep_len <= len; rep_crc <= ~crc;
                rep_eop <= (c == 2'b10); rep_err <= 3'd0; rep_tc <= '0; rep_tick <= 1'b0;
                len <= '0; crc <= '1;
              end
            end
          end else begin
            par <= ^v;
            if (esc) begin                           // time-code
              esc <= 1'b0;
              rep_valid <= 1'b1; rep_kind <= 1'b1; rep_len <= '0; rep_crc <= '0; rep_eop <= 1'b0;
              rep_err <= 3'd0; rep_tc <= v; rep_tick <= (v[5:0] == last_tc + 6'd1);
              last_tc <= v[5:0];
            end else if (outst == 0) e = 3'd4;
            else begin
              use_credit = 1'b1;
              len <= len + 16'd1; crc <= crc32_byte(crc, v);
            end
          end
        end else begin
          sh <= {din, sh[7:1]};
          nb <= nb + 4'd1;
        end
      end

      // ---- transmitter: NULLs, FCTs while credit given <= 8
      if (err_t != 0) begin
        err_t <= err_t - 6'd1;
        dout <= 1'b0; sout <= 1'b0; tb <= '0; tx_n <= '0; tx_par <= 1'b0; tx_fct_next <= 1'b0;
      end else begin
        tb <= (tb == 2'(TXB - 1)) ? 2'd0 : tb + 2'd1;
        if (tb == 2'd0) begin : tx_bit
          logic [9:0] v;
          logic [3:0] n;
          v = tx_sh; n = tx_n;
          if (n == 4'd0) begin
            if (tx_fct_next || (got_null && outst <= 5'd8)) begin
              v = {6'b0, 2'b00, 1'b1, tx_par};       // FCT
              if (!tx_fct_next) give_credit = 1'b1;
              tx_fct_next <= 1'b0;
            end else begin
              v = {6'b0, 2'b11, 1'b1, tx_par};       // ESC (of a NULL)
              tx_fct_next <= 1'b1;
            end
            tx_par <= 1'b0;
            n = 4'd4;
          end
          if (v[0] == dout) sout <= !sout;
          dout <= v[0];
          tx_sh <= v >> 1;
          tx_n <= n - 4'd1;
        end
      end

      // credit: +8 for an FCT sent (not the FCT of a NULL), -1 per N-char
      outst <= outst + (give_credit ? 5'd8 : 5'd0) - (use_credit ? 5'd1 : 5'd0);

      // ---- an error resets the link
      if (e != 3'd0) begin
        rep_valid <= 1'b1; rep_kind <= 1'b0; rep_len <= len; rep_crc <= ~crc; rep_eop <= 1'b0;
        rep_err <= e; rep_tc <= '0; rep_tick <= 1'b0;
        len <= '0; crc <= '1; rx_on <= 1'b0; esc <= 1'b0; got_null <= 1'b0; outst <= '0;
        err_t <= 6'(SILENT); dout <= 1'b0; sout <= 1'b0; tx_n <= '0; tx_par <= 1'b0; tx_fct_next <= 1'b0;
      end
    end
  end
endmodule
""",
    sva="""
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({dout, sout, rep_valid}))
  else $error("SpaceWire: X on D / S out or report");
// Data-Strobe: one of D and S changes per bit, never both
assert property (@(posedge clk) disable iff (!rst_n) !($changed(dout) && $changed(sout) && (dout || sout)))
  else $error("SpaceWire: D and S changed together");
// a report never comes while the line in is quiet for long
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_kind);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 3'd1);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && rep_err == 3'd2);
cover property (@(posedge clk) disable iff (!rst_n) rep_valid && !rep_kind && rep_err == 0 && !rep_eop);
""",
    smoke="""
int checks = 0;
int fails  = 0;
// the DUT is silent 40 clocks (first bit on the 41st); silent(11) after a
// bit gives the receiver exactly the 12 quiet clocks it needs
localparam int SILENT_CLKS = 41, QUIET_MIN = 11;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic din = 0, sin = 0;
wire dout, sout, rep_valid, rep_kind, rep_eop, rep_tick;
wire [15:0] rep_len;
wire [31:0] rep_crc;
wire [2:0] rep_err;
wire [7:0] rep_tc;

always #5 clk = ~clk;

spacewire_model u_dut (.clk(clk), .rst_n(rst_n), .din(din), .sin(sin), .dout(dout), .sout(sout),
                       .rep_valid(rep_valid), .rep_kind(rep_kind), .rep_len(rep_len), .rep_crc(rep_crc),
                       .rep_eop(rep_eop), .rep_err(rep_err), .rep_tc(rep_tc), .rep_tick(rep_tick));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// reports
int nrep = 0;
logic r_kind, r_eop, r_tick;
logic [15:0] r_len;
logic [31:0] r_crc;
logic [2:0] r_err;
logic [7:0] r_tc;
always @(posedge clk) if (rep_valid) begin
  nrep++; r_kind = rep_kind; r_len = rep_len; r_crc = rep_crc; r_eop = rep_eop; r_err = rep_err;
  r_tc = rep_tc; r_tick = rep_tick;
end

// the DUT's transmitter, decoded: NULLs, FCTs, parity, D / S rule, quiet time
int n_null = 0, n_fct = 0, n_other = 0, tx_par_err = 0, ds_both = 0, quiet_max = 0;
int quiet = 0, rnb = 0;
logic rd_p = 0, rs_p = 0, r_on = 0, r_f = 0, r_p = 0, r_par = 0, r_esc = 0, par_pend = 0;
logic [7:0] r_sh = 0;
always @(posedge clk) if (rst_n) begin
  if (dout !== rd_p && sout !== rs_p) begin
    if (dout !== 1'b0 || sout !== 1'b0) ds_both++;   // only dropping both lines is allowed
    quiet = 0;
  end else if (dout !== rd_p || sout !== rs_p) begin
    if (!r_on && quiet >= 12) begin r_on = 1; rnb = 0; r_par = 0; r_esc = 0; end
    quiet = 0;
    if (r_on) begin
      if (rnb == 0) r_p = dout;
      else if (rnb == 1) begin
        r_f = dout;
        // counted once the character goes on: a lone bit before the DUT went
        // quiet is its lines dropping, not a character
        par_pend = ((r_p ^ dout ^ r_par) !== 1'b1);
      end else begin
        if (rnb == 2 && par_pend) tx_par_err++;
        r_sh = {dout, r_sh[7:1]};
      end
      rnb++;
      if (rnb >= 4 && rnb == (r_f ? 4 : 10)) begin
        rnb = 0;
        if (r_f) begin
          r_par = r_sh[7] ^ r_sh[6];
          if (r_sh[7:6] == 2'b11) r_esc = 1;
          else begin
            if (r_sh[7:6] == 2'b00) begin if (r_esc) n_null++; else n_fct++; end
            else n_other++;
            r_esc = 0;
          end
        end else begin r_par = ^r_sh; n_other++; r_esc = 0; end
      end
    end
  end else begin
    quiet++;
    if (quiet > quiet_max) quiet_max = quiet;
    if (quiet == 12) begin r_on = 0; par_pend = 0; end
  end
  rd_p = dout; rs_p = sout;
end

// DUT bit period, silence after reset, lines during an error
int cyc = 0, last_ev = -1, per_min = 99, per_max = 0, first_ev = -1, err_glitch = 0;
logic measure = 1'b1;              // bit periods until the first link error
always @(posedge clk) if (rst_n) begin
  cyc++;
  if (rep_valid && rep_err != 0) measure = 0;
  if (measure && ((dout !== rd_q) ^ (sout !== rs_q))) begin
    if (first_ev < 0) first_ev = cyc;
    if (last_ev >= 0) begin
      if (cyc - last_ev < per_min) per_min = cyc - last_ev;
      if (cyc - last_ev > per_max) per_max = cyc - last_ev;
    end
    last_ev = cyc;
  end else if (dout === 1'b0 && sout === 1'b0) last_ev = -1;
  if (rep_valid && rep_err != 0 && (dout || sout)) err_glitch++;
  rd_q = dout; rs_q = sout;
end
logic rd_q = 0, rs_q = 0;

// the agent side: bits of 2 clocks
logic tx_par = 0;
int sent = 0;                      // N-chars sent since the link started
task automatic w(input int n); repeat (n) @(posedge clk); #1; endtask
task automatic bitx(input logic b);
  if (b == din) sin = !sin;
  din = b;
  w(2);
endtask
task automatic ctrl(input logic [1:0] c, input logic flip = 0);   // c = {second, first}
  bitx(tx_par ^ flip); bitx(1); bitx(c[0]); bitx(c[1]);
  tx_par = c[1] ^ c[0];
endtask
task automatic dat(input logic [7:0] v, input logic flip = 0);
  bitx(!tx_par ^ flip); bitx(0);
  for (int i = 0; i < 8; i++) bitx(v[i]);
  tx_par = ^v;
endtask
task automatic null_c; ctrl(2'b11); ctrl(2'b00); endtask
task automatic silent(input int n); din = 0; sin = 0; tx_par = 0; w(n); endtask
// an N-char, waiting with NULLs for credit
task automatic nchar(input bit is_ctrl, input logic [7:0] v);
  int k;
  k = 0;
  while (n_fct * 8 - sent <= 0 && k < 200) begin null_c(); k++; end
  if (is_ctrl) ctrl(v[1:0]); else dat(v);
  sent++;
endtask
// start the link: quiet, then NULLs until the first FCT
task automatic link_up;
  int k;
  n_fct = 0;
  silent(40);
  chk(n_fct == 0, "no FCT after a link reset before a NULL arrives");
  sent = 0; k = 0;
  while (n_fct == 0 && k < 50) begin null_c(); k++; end
  null_c(); null_c();
endtask
task automatic wait_rep(input int prev);
  int k;
  k = 0;
  while (nrep == prev && k < 100) begin @(posedge clk); k++; end
  #1;
endtask

initial begin
  int b, f0, q0;
  string s9 = "123456789";
  logic [31:0] c;
  repeat (3) @(posedge clk);
  chk(dout === 1'b0 && sout === 1'b0 && rep_valid === 1'b0, "lines low and no report during reset");
  rst_n = 1;
  w(30);
  chk(dout === 1'b0 && sout === 1'b0 && n_null == 0, "transmitter silent after reset");
  w(400);
  chk(n_null > 5 && n_fct == 0 && n_other == 0, $sformatf("NULLs only until a NULL is received (%0d NULLs, %0d FCTs)", n_null, n_fct));
  chk(nrep == 0, "no report while the line in is quiet");
  chk(first_ev == SILENT_CLKS, $sformatf("first bit out %0d clocks after reset", first_ev));

  // link start: one NULL brings two FCTs (16 N-chars of credit)
  silent(2);
  null_c(); null_c();
  w(120);
  chk(n_fct == 2, $sformatf("two FCTs after the first NULL (%0d)", n_fct));
  sent = 0;

  // a packet of 9 data bytes and EOP
  b = nrep;
  for (int i = 0; i < 9; i++) nchar(0, s9[i]);
  nchar(1, 2'b10);
  wait_rep(b);
  chk(nrep == b + 1 && r_kind == 0 && r_err == 0 && r_eop === 1'b1 && r_len == 9 && r_crc == 32'hCBF4_3926,
      $sformatf("packet: 9 bytes, CRC-32 0xCBF43926, EOP (%0d %h %0d)", r_len, r_crc, r_err));
  null_c(); null_c(); null_c(); w(60);
  chk(n_fct == 3, $sformatf("one more FCT once 8 N-chars were used (%0d)", n_fct));
  chk(n_fct * 8 - sent == 14, "credit back up: 24 given, 10 used");

  // EEP, an empty packet, a packet longer than the credit
  b = nrep; nchar(0, 8'hDE); nchar(0, 8'hAD); nchar(1, 2'b01); wait_rep(b);
  chk(r_len == 2 && r_eop === 1'b0 && r_err == 0, "packet ended by EEP");
  b = nrep; nchar(1, 2'b10); wait_rep(b);
  chk(nrep == b + 1 && r_len == 0 && r_crc == 32'h0 && r_eop === 1'b1, "empty packet");
  b = nrep; c = 32'hFFFF_FFFF;
  for (int i = 0; i < 30; i++) begin
    nchar(0, 8'(i * 7));
    c ^= {24'h0, 8'(i * 7)};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  nchar(1, 2'b10); wait_rep(b);
  chk(nrep == b + 1 && r_len == 30 && r_crc == ~c && r_err == 0, "30-byte packet across several FCTs");
  // an FCT from this side is accepted and ignored
  ctrl(2'b00);
  b = nrep; nchar(0, 8'h42); nchar(1, 2'b10); wait_rep(b);
  chk(r_len == 1 && r_err == 0, "FCT received from the agent ignored");

  // time-codes
  b = nrep; ctrl(2'b11); dat(8'h01); wait_rep(b);
  chk(nrep == b + 1 && r_kind === 1'b1 && r_tc == 8'h01 && r_tick === 1'b1, "time-code 1 after 0: tick");
  b = nrep; ctrl(2'b11); dat(8'h05); wait_rep(b);
  chk(r_kind === 1'b1 && r_tc == 8'h05 && r_tick === 1'b0 && r_eop === 1'b0 && r_err == 0,
      "time-code 5 after 1: no tick, no packet fields");
  b = nrep; ctrl(2'b11); dat(8'hC6); wait_rep(b);
  chk(r_tc == 8'hC6 && r_tick === 1'b1 && r_len == 0, "time-code 6 with flags: tick, flags kept");
  ctrl(2'b11); dat(8'h3F); b = nrep; ctrl(2'b11); dat(8'h00); wait_rep(b);
  chk(r_tc == 8'h00 && r_tick === 1'b1, "time-code 63 -> 0 wraps: tick");
  chk(n_fct * 8 - sent >= 8, "time-codes and NULLs use no credit");

  // parity error in a packet: reported with the bytes before it, link reset
  b = nrep; nchar(0, 8'h41); nchar(0, 8'h42);
  dat(8'h43, 1);
  dat(8'h44); dat(8'h45);
  wait_rep(b);
  c = 32'hFFFF_FFFF;
  for (int i = 0; i < 2; i++) begin
    c ^= {24'h0, 8'(8'h41 + i)};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  chk(nrep == b + 1 && r_err == 3'd1 && r_len == 2 && r_crc == ~c && r_eop === 1'b0,
      $sformatf("parity error: code 1, the 2 bytes before it (%0d %0d)", r_err, r_len));
  q0 = quiet_max;
  silent(60);
  chk(quiet_max >= 36, $sformatf("transmitter silent after the error (%0d quiet clocks)", quiet_max));
  chk(nrep == b + 1, "the characters after the error were ignored");
  f0 = n_null;
  link_up();
  chk(n_fct == 2, $sformatf("link restarts: two FCTs after NULLs (%0d)", n_fct));
  b = nrep; nchar(0, 8'h55); nchar(1, 2'b10); wait_rep(b);
  chk(r_err == 0 && r_len == 1, "packet after the restart");

  // escape errors: ESC EOP, ESC ESC, ESC EEP
  b = nrep; nchar(0, 8'h77); ctrl(2'b11); ctrl(2'b10); wait_rep(b);
  chk(nrep == b + 1 && r_err == 3'd2 && r_len == 1, "ESC + EOP: escape error");
  // keep sending through the DUT's silence: it must not start on a running
  // stream, only after quiet
  b = nrep;
  repeat (8) null_c();
  chk(nrep == b, "no restart on a stream that never went quiet");
  silent(QUIET_MIN);
  n_fct = 0; null_c(); null_c(); null_c(); null_c(); w(40);
  chk(n_fct >= 1, "receiver starts after the minimum quiet time");
  sent = 0; w(40);
  b = nrep; ctrl(2'b11); ctrl(2'b11); wait_rep(b);
  chk(nrep == b + 1 && r_err == 3'd2 && r_len == 0, "ESC + ESC: escape error");
  link_up();
  b = nrep; ctrl(2'b11); ctrl(2'b01); wait_rep(b);
  chk(nrep == b + 1 && r_err == 3'd2, "ESC + EEP: escape error");
  // both lines dropping at once is activity, not quiet: no start right after it
  din = 1; sin = 1; w(50);
  n_fct = 0; din = 0; sin = 0; tx_par = 0; w(2);
  null_c(); null_c(); null_c(); w(30);
  chk(n_fct == 0, "no start on a bit right after both lines dropped");

  // credit error: a data character before any FCT
  silent(40);
  b = nrep; dat(8'h99); wait_rep(b);
  chk(nrep == b + 1 && r_err == 3'd4, "N-char without credit: credit error");
  link_up();
  b = nrep; nchar(0, 8'h01); nchar(1, 2'b10); wait_rep(b);
  chk(r_err == 0, "clean packet at the end");

  chk(tx_par_err == 0, "the DUT's characters have odd parity");
  chk(per_min == 3 && per_max == 3, $sformatf("DUT bits last 3 clocks (%0d..%0d)", per_min, per_max));
  chk(err_glitch == 0, "lines low from the clock of an error report");
  chk(ds_both == 0, "D and S out never change together");
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #4000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
