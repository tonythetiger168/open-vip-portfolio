# SGMII / 1000BASE-X PCS transmit agent (IEEE 802.3 Clause 36 8b/10b PCS,
# Cisco SGMII configuration ordered sets).
# tb/top_tb.sv sgmii_model: the PCS transmit path. GMII (txd, tx_en, tx_er) in,
# one 10-bit code group per clock out on tbi ({a,b,c,d,e,i,f,g,h,j}, a = bit 9,
# a sent first). It sends IDLE ordered sets (/K28.5/ + /D16.2/, or /D5.6/
# when the running disparity is positive), replaces the first preamble byte
# with /S/ (start of packet, even position only: a frame that starts at an
# odd position loses one preamble byte), encodes tx_er as /V/, ends a frame
# with /T/ /R/ (+ /R/ to reach an even position), and while cfg_tx is high
# sends /C1/ /C2/ configuration ordered sets with the SGMII config word.
# The monitor is an independent 8b/10b decoder: it checks running disparity
# and code validity, comma alignment, the /T/R/R/ and /I1/ /I2/ rules, and
# rebuilds the GMII frames and the configuration words.
from _lib import ETH_FUNCS

ENC = """
// IEEE 802.3 Clause 36 8b/10b encoder: d = HGFEDCBA, returns {abcdei, fghj};
// rd: running disparity (1 = positive) before / after the code group
function automatic bit [9:0] enc8b10b(bit [7:0] d, bit k, ref bit rd);
  // 5b/6b (EDCBA -> abcdei) and 3b/4b (HGF -> fghj) for RD-
  bit [5:0] t6[32] = '{6'b100111, 6'b011101, 6'b101101, 6'b110001, 6'b110101, 6'b101001, 6'b011001, 6'b111000,
                       6'b111001, 6'b100101, 6'b010101, 6'b110100, 6'b001101, 6'b101100, 6'b011100, 6'b010111,
                       6'b011011, 6'b100011, 6'b010011, 6'b110010, 6'b001011, 6'b101010, 6'b011010, 6'b111010,
                       6'b110011, 6'b100110, 6'b010110, 6'b110110, 6'b001110, 6'b101110, 6'b011110, 6'b101011};
  bit [3:0] t4[8] = '{4'b1011, 4'b1001, 4'b0101, 4'b1100, 4'b1101, 4'b1010, 4'b0110, 4'b1110};
  bit [5:0] c6;
  bit [3:0] c4;
  bit r = k ? 1'b0 : rd;           // a K code is built for RD- and complemented for RD+
  int x = d[4:0], y = d[7:5];
  c6 = (x == 28 && k) ? 6'b001111 : t6[x];
  if (r && ($countones(c6) != 3 || c6 == 6'b111000)) c6 = ~c6;
  if ($countones(c6) != 3) r = !r;
  if (y == 7 && (k || (!r && (x == 17 || x == 18 || x == 20)) || (r && (x == 11 || x == 13 || x == 14))))
    c4 = 4'b0111;                  // A7
  else
    c4 = t4[y];
  if (r && ($countones(c4) != 2 || c4 == 4'b1100)) c4 = ~c4;
  enc8b10b = {c6, c4};
  if (k && rd) enc8b10b = ~enc8b10b;
  if ($countones(enc8b10b) > 5) rd = 1'b1;
  else if ($countones(enc8b10b) < 5) rd = 1'b0;
endfunction
"""

SPEC = dict(
    vip="SGMII-UVM-VIP", p="sgmii", P="SGMII", dir="sgmii", family="Networking",
    desc="SGMII / 1000BASE-X PCS VIP (IEEE 802.3 Clause 36): GMII frames in, 8b/10b code groups out; "
         "independent 8b/10b decoder with running-disparity, comma-alignment, /S/ /T/ /R/ /V/ and "
         "/I1/ /I2/ checks, plus SGMII /C1/ /C2/ configuration ordered sets.",
    about="""
SGMII is the MAC to PHY link of most Ethernet PHYs and FPGA designs at 10/100/1000
Mb/s; its PCS is the 1000BASE-X 8b/10b PCS. The monitor decodes the code-group
stream on its own (lookup built from its own encoder), so a wrong table entry or
disparity rule in the PCS shows up as a code or disparity error, and rebuilds
the GMII frame (FCS checked) and the SGMII configuration word (link, duplex,
speed). Speed adaptation (10/100 byte replication) sits above the PCS and is
not modelled.""",
    defs="""
// SGMII configuration word (PHY to MAC): [15] link, [14] ack, [12] duplex,
// [11:10] speed (10 = 1000, 01 = 100, 00 = 10 Mb/s), [0] = 1
localparam bit [9:0] K28_5_RDN = 10'b0011111010;
""",
    timeout=200,
    ports=[
        ("in", "logic [7:0]", "txd"), ("in", "logic", "tx_en"), ("in", "logic", "tx_er"),
        ("in", "logic", "cfg_tx"), ("in", "logic [15:0]", "cfg_word"),
        ("out", "logic [9:0]", "tbi"),
    ],
    fields=[
        ("bit", "is_cfg", "req"),
        ("bit [7:0]", "bytes", "req", "q"),     # MAC frame (DA .. FCS) after the SFD
        ("int", "er_pos", "req", "norand"),     # byte sent with tx_er (/V/), -1 = none
        ("bit [15:0]", "cfg_word", "req", "norand"),
        ("bit [7:0]", "code_errs", "rsp"),      # invalid code groups / disparity errors
        ("bit [10:0]", "plen", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("bit [2:0]", "cfg_sets", "info", "rand"),
        ("bit", "inj_er", "info", "rand"),
        ("int unsigned", "pre_len", "info"),    # preamble bytes after /S/
        ("bit", "t_odd", "info"),               # /T/ at an odd position
        ("int unsigned", "n_r", "info"),        # /R/ code groups after /T/
    ],
    constraints="""
constraint c_kind { is_cfg dist { 0 := 4, 1 := 1 }; inj_er dist { 0 := 5, 1 := 1 }; }
constraint c_len  { plen inside {[46:160]}; cfg_sets inside {[2:6]}; }
""",
    tr_functions=ETH_FUNCS + """
function void post_randomize();
  bytes.delete();
  er_pos = -1;
  cfg_word = 16'h0;
  if (is_cfg)
    cfg_word = {seed[15], 1'b0, 1'b0, seed[12:10] == 3'b111 ? 3'b110 : seed[12:10], 9'h0, 1'b1};
  else begin
    build_frame(plen, seed, 16'h0800);
    if (inj_er) er_pos = seed % bytes.size();
  end
endfunction
""",
    drv_rsp=False,
    drv_desc="GMII frames (7 preamble bytes, SFD, frame, tx_er on one byte) or a run of configuration ordered sets",
    drv_idle="""
vif.drv_cb.txd      <= 8'h0;
vif.drv_cb.tx_en    <= 1'b0;
vif.drv_cb.tx_er    <= 1'b0;
vif.drv_cb.cfg_tx   <= 1'b0;
vif.drv_cb.cfg_word <= 16'h0;
""",
    drv_item="""
@(vif.drv_cb);
if (t.is_cfg) begin
  vif.drv_cb.cfg_word <= t.cfg_word;
  vif.drv_cb.cfg_tx   <= 1'b1;
  repeat (4 * t.cfg_sets) @(vif.drv_cb);
  vif.drv_cb.cfg_tx   <= 1'b0;
  repeat (12) @(vif.drv_cb);
end else begin
  for (int i = 0; i < 8 + t.bytes.size(); i++) begin
    vif.drv_cb.tx_en <= 1'b1;
    vif.drv_cb.txd   <= (i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : t.bytes[i - 8];
    vif.drv_cb.tx_er <= (i >= 8 && i - 8 == t.er_pos);
    @(vif.drv_cb);
  end
  vif.drv_cb.tx_en <= 1'b0;
  vif.drv_cb.tx_er <= 1'b0;
  vif.drv_cb.txd   <= 8'h0;
  repeat (12) @(vif.drv_cb);                // inter-packet gap
  if (t.er_pos >= 0) t.bytes[t.er_pos] = 8'h00;   // the line carries /V/, not the byte
end
""",
    mon_desc="independent 8b/10b decoder (disparity and code checks), ordered-set parser, frames and configuration words",
    mon_members="""bit [9:0] dec_code[$];        // code groups for RD- and RD+
bit [8:0] dec_val[$];         // {K, byte}
bit       dec_rd[$];          // RD the code is legal for

function void init_tables();
  // decode table from the encoder: 256 data + 12 control codes, both disparities
  for (int k = 0; k < 2; k++)
    for (int v = 0; v < 256; v++) begin
      bit [7:0] d = v;
      if (k && !(d inside {8'h1C, 8'h3C, 8'h5C, 8'h7C, 8'h9C, 8'hBC, 8'hDC, 8'hFC,
                           8'hF7, 8'hFB, 8'hFD, 8'hFE})) continue;
      for (int r = 0; r < 2; r++) begin
        bit rr = r;
        dec_code.push_back(enc8b10b(d, k, rr));
        dec_val.push_back({k[0], d});
        dec_rd.push_back(r);
      end
    end
endfunction

// decode with the current running disparity; ok = 0 for an invalid code or a
// code of the wrong disparity
function void decode(bit [9:0] c, ref bit rd, output bit [8:0] v, output bit ok);
  ok = 0;
  foreach (dec_code[i])
    if (dec_code[i] == c && dec_rd[i] == rd) begin v = dec_val[i]; ok = 1; break; end
  if ($countones(c) > 5) rd = 1'b1;
  else if ($countones(c) < 5) rd = 1'b0;
endfunction""",
    mon_run="""
// stream positions are counted from the first comma (K28.5 = even position)
typedef enum {M_IDLE, M_PKT, M_R, M_CFG} st_e;
st_e st = M_IDLE;
bit rd = 0, synced = 0, even = 1, rd_set = 0;
bit [8:0] v, prev = 0;
int unsigned cpos = 0, nerr = 0, cfg_n = 0;
bit [7:0] pk[$];
bit [15:0] cw = 0, cur_cw = 0;
bit cfg_open = 0;
int erp = -1;
sgmii_transaction t;
init_tables();
forever begin
  bit ok;
  bit [9:0] c;
  bit rd_in;
  @(vif.mon_cb);
  c = vif.mon_cb.tbi;
  rd_in = rd;
  if (!synced) begin
    if (c == K28_5_RDN) begin synced = 1; rd = 0; even = 1; end
    else if (c == ~K28_5_RDN) begin synced = 1; rd = 1; even = 1; end
    else continue;
  end
  decode(c, rd, v, ok);
  if (!ok) begin
    nerr++;
    `uvm_error("MON", $sformatf("SGMII: invalid code group / disparity error %b (RD%s)", c, rd_in ? "+" : "-"))
  end
  if (v == 9'h1BC && !even) `uvm_error("MON", "SGMII: comma at an odd position")
  case (st)
    M_IDLE: begin
      if (v == 9'h1FB) begin                          // /S/
        if (!even) `uvm_error("MON", "SGMII: /S/ at an odd position")
        if (cfg_open) begin flush_cfg(cur_cw, nerr); cfg_open = 0; end
        pk.delete(); erp = -1; st = M_PKT;
      end else if (prev == 9'h1BC && !even) begin    // second code of an ordered set
        if (v == 9'h0B5 || v == 9'h042) begin         // /C1/ /C2/: config word follows
          st = M_CFG; cpos = 0;
        end else if (v == 9'h0C5 || v == 9'h050) begin   // /I1/ D5.6, /I2/ D16.2
          if (cfg_open) begin flush_cfg(cur_cw, nerr); cfg_open = 0; end
          // /I1/ follows a positive RD at the ordered set, i.e. a negative
          // RD after its K28.5
          if (rd_set && ((v == 9'h0C5) == rd_in))
            `uvm_error("MON", $sformatf("SGMII: %s with RD%s at the ordered set", v == 9'h0C5 ? "/I1/" : "/I2/", rd_in ? "+" : "-"))
        end else
          `uvm_error("MON", $sformatf("SGMII: K28.5 followed by %h", v))
      end
    end
    M_PKT: begin
      if (v == 9'h1FD) begin                          // /T/
        t = sgmii_transaction::type_id::create("t");
        t.t_odd = !even; t.n_r = 0; t.er_pos = -1;
        frame(t, pk, erp);
        st = M_R;
      end else if (v == 9'h1FE) begin pk.push_back(8'h00); if (erp < 0) erp = pk.size() - 1; end   // /V/
      else if (v[8]) `uvm_error("MON", $sformatf("SGMII: control code %h inside a packet", v))
      else pk.push_back(v[7:0]);
    end
    M_R: begin
      if (v == 9'h1F7) t.n_r++;                       // /R/
      else begin
        t.code_errs = nerr; nerr = 0;
        publish(t);
        st = M_IDLE;
        if (v != 9'h1BC) `uvm_error("MON", $sformatf("SGMII: %h after /T/ /R/ instead of an idle", v))
        if (!even) `uvm_error("MON", "SGMII: idle after /R/ at an odd position")
      end
    end
    M_CFG: begin
      cw[8*cpos +: 8] = v[7:0];
      cpos++;
      if (cpos == 2) begin
        if (cfg_open && cw != cur_cw) flush_cfg(cur_cw, nerr);
        cur_cw = cw; cfg_open = 1;
        st = M_IDLE;
      end
    end
  endcase
  // the disparity check of /I1/ / /I2/ needs a known RD at the ordered set
  if (v == 9'h1BC && even) rd_set = 1;
  prev = v;
  even = !even;
end
""",
    mon_tasks="""
// preamble (0x55 ...) and SFD (0xD5) stripped; /V/ position kept
function void frame(sgmii_transaction t, bit [7:0] pk[$], int erp);
  int i = 0;
  while (i < pk.size() && pk[i] == 8'h55) i++;
  t.pre_len = i;
  if (i >= pk.size() || pk[i] != 8'hD5) `uvm_error("MON", "SGMII: no SFD after the preamble")
  for (int j = i + 1; j < pk.size(); j++) t.bytes.push_back(pk[j]);
  t.er_pos = (erp > i) ? erp - i - 1 : -1;
  t.is_cfg = 0;
endfunction

function void flush_cfg(bit [15:0] w, ref int unsigned nerr);
  sgmii_transaction c = sgmii_transaction::type_id::create("cfg");
  c.is_cfg = 1; c.cfg_word = w; c.er_pos = -1; c.code_errs = nerr; nerr = 0;
  publish(c);
endfunction
""",
    tr_members="",
    predict="""
// the PCS passes the frame and the configuration word through unchanged;
// a byte sent with tx_er arrives as /V/ (no data)
t.code_errs = 0;
""",
    checks="""
if (!t.is_cfg) begin
  if (!(t.pre_len inside {5, 6})) fail(t, $sformatf("%0d preamble bytes after /S/ (6, or 5 after alignment)", t.pre_len));
  if (t.n_r != (t.t_odd ? 2 : 1)) fail(t, $sformatf("/T/ at %s position followed by %0d /R/", t.t_odd ? "an odd" : "an even", t.n_r));
  if (t.er_pos < 0 && !t.fcs_ok()) fail(t, "frame FCS wrong");
end else if (!t.cfg_word[0]) fail(t, "SGMII config word bit 0 must be 1");
""",
    coverage="""
cp_kind  : coverpoint tr.is_cfg;
cp_err   : coverpoint (tr.er_pos >= 0);
cp_todd  : coverpoint tr.t_odd iff (!tr.is_cfg);
cp_pre   : coverpoint tr.pre_len iff (!tr.is_cfg) { bins aligned = {6}; bins shrunk = {5}; }
cp_speed : coverpoint tr.cfg_word[11:10] iff (tr.is_cfg) { bins s10 = {0}; bins s100 = {1}; bins s1000 = {2}; }
cp_link  : coverpoint tr.cfg_word[15] iff (tr.is_cfg);
""",
    directed="""
// minimum and odd-length frames (/T/ on both positions), a /V/ error, config words
t = item(); t.plen = 46; t.seed = 32'h1; t.build_frame(46, 32'h1, 16'h0800); t.er_pos = -1; send(t);
t = item(); t.plen = 47; t.seed = 32'h2; t.build_frame(47, 32'h2, 16'h0800); t.er_pos = -1; send(t);
t = item(); t.plen = 64; t.seed = 32'h3; t.build_frame(64, 32'h3, 16'h86DD); t.er_pos = 20; send(t);
t = item(); t.is_cfg = 1; t.cfg_word = 16'h9801; t.cfg_sets = 4; t.er_pos = -1; send(t);   // link, full duplex, 1000
t = item(); t.is_cfg = 1; t.cfg_word = 16'h9401; t.cfg_sets = 3; t.er_pos = -1; send(t);   // 100 Mb/s
t = item(); t.is_cfg = 1; t.cfg_word = 16'h0001; t.cfg_sets = 3; t.er_pos = -1; send(t);   // link down
t = item(); t.plen = 100; t.seed = 32'hABCD; t.build_frame(100, 32'hABCD, 16'h0800); t.er_pos = -1; send(t);
// all data byte values through the encoder (both disparities across frames)
t = item(); t.bytes.delete(); for (int i = 0; i < 256; i++) t.bytes.push_back(i); add_fcs(t); t.er_pos = -1; send(t);
t = item(); t.bytes.delete(); for (int i = 255; i >= 0; i--) t.bytes.push_back(i); t.bytes.push_back(8'h00); add_fcs(t); t.er_pos = -1; send(t);
""",
    seq_tasks="""
function void add_fcs(sgmii_transaction t);
  bit [31:0] f = t.crc32(t.bytes, t.bytes.size());
  for (int i = 0; i < 4; i++) t.bytes.push_back(f[i*8 +: 8]);
endfunction
""",
    drain_ns=1000,
    model="""
module sgmii_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic [7:0]  txd,
  input  logic        tx_en,
  input  logic        tx_er,
  input  logic        cfg_tx,
  input  logic [15:0] cfg_word,
  output logic [9:0]  tbi
);
  typedef enum logic [2:0] {S_IDLE, S_IDLE2, S_DATA, S_R, S_R2, S_CFG} st_t;
  st_t        st;
  logic       rd, even, i1, c2;
  logic [1:0] cn;
  logic [15:0] cw;

  // 5b/6b and 3b/4b sub-blocks for RD- (abcdei / fghj)
  function automatic logic [5:0] sb6(input logic [4:0] x);
    case (x)
      5'd0: sb6 = 6'b100111;  5'd1: sb6 = 6'b011101;  5'd2: sb6 = 6'b101101;  5'd3: sb6 = 6'b110001;
      5'd4: sb6 = 6'b110101;  5'd5: sb6 = 6'b101001;  5'd6: sb6 = 6'b011001;  5'd7: sb6 = 6'b111000;
      5'd8: sb6 = 6'b111001;  5'd9: sb6 = 6'b100101;  5'd10: sb6 = 6'b010101; 5'd11: sb6 = 6'b110100;
      5'd12: sb6 = 6'b001101; 5'd13: sb6 = 6'b101100; 5'd14: sb6 = 6'b011100; 5'd15: sb6 = 6'b010111;
      5'd16: sb6 = 6'b011011; 5'd17: sb6 = 6'b100011; 5'd18: sb6 = 6'b010011; 5'd19: sb6 = 6'b110010;
      5'd20: sb6 = 6'b001011; 5'd21: sb6 = 6'b101010; 5'd22: sb6 = 6'b011010; 5'd23: sb6 = 6'b111010;
      5'd24: sb6 = 6'b110011; 5'd25: sb6 = 6'b100110; 5'd26: sb6 = 6'b010110; 5'd27: sb6 = 6'b110110;
      5'd28: sb6 = 6'b001110; 5'd29: sb6 = 6'b101110; 5'd30: sb6 = 6'b011110; default: sb6 = 6'b101011;
    endcase
  endfunction
  function automatic logic [3:0] sb4(input logic [2:0] y);
    case (y)
      3'd0: sb4 = 4'b1011; 3'd1: sb4 = 4'b1001; 3'd2: sb4 = 4'b0101; 3'd3: sb4 = 4'b1100;
      3'd4: sb4 = 4'b1101; 3'd5: sb4 = 4'b1010; 3'd6: sb4 = 4'b0110; default: sb4 = 4'b1110;
    endcase
  endfunction
  function automatic logic [3:0] ones6(input logic [5:0] v); ones6 = v[0]+v[1]+v[2]+v[3]+v[4]+v[5]; endfunction
  function automatic logic [3:0] ones4(input logic [3:0] v); ones4 = v[0]+v[1]+v[2]+v[3]; endfunction

  // {rd_out, code}
  function automatic logic [10:0] encode(input logic [7:0] d, input logic k, input logic rdi);
    logic [5:0] a6; logic [3:0] a4; logic r; logic [9:0] c;
    r  = k ? 1'b0 : rdi;
    a6 = (k && d[4:0] == 5'd28) ? 6'b001111 : sb6(d[4:0]);
    if (r && (ones6(a6) != 4'd3 || a6 == 6'b111000)) a6 = ~a6;
    if (ones6(a6) != 4'd3) r = ~r;
    if (d[7:5] == 3'd7 && (k || (!r && (d[4:0] == 5'd17 || d[4:0] == 5'd18 || d[4:0] == 5'd20))
                           || (r && (d[4:0] == 5'd11 || d[4:0] == 5'd13 || d[4:0] == 5'd14))))
      a4 = 4'b0111;
    else
      a4 = sb4(d[7:5]);
    if (r && (ones4(a4) != 4'd2 || a4 == 4'b1100)) a4 = ~a4;
    if (ones4(a4) != 4'd2) r = ~r;
    c = {a6, a4};
    if (k && rdi) begin c = ~c; r = ~r; end
    encode = {r, c};
  endfunction

  localparam logic [7:0] K28_5 = 8'hBC, K27_7 = 8'hFB, K29_7 = 8'hFD, K23_7 = 8'hF7, K30_7 = 8'hFE;
  localparam logic [7:0] D16_2 = 8'h50, D5_6 = 8'hC5, D21_5 = 8'hB5, D2_2 = 8'h42;

  logic [7:0] sym;
  logic       symk;
  st_t        nst;
  always_comb begin
    sym = K28_5; symk = 1'b1; nst = st;
    case (st)
      S_IDLE:
        if (cfg_tx) begin sym = K28_5; symk = 1'b1; nst = S_CFG; end
        else if (tx_en) begin sym = K27_7; symk = 1'b1; nst = S_DATA; end
        else begin sym = K28_5; symk = 1'b1; nst = S_IDLE2; end
      S_IDLE2: begin sym = i1 ? D5_6 : D16_2; symk = 1'b0; nst = S_IDLE; end
      S_DATA:
        if (tx_en) begin sym = tx_er ? K30_7 : txd; symk = tx_er; nst = S_DATA; end
        else begin sym = K29_7; symk = 1'b1; nst = S_R; end
      S_R:  begin sym = K23_7; symk = 1'b1; if (even) nst = S_R2; else nst = S_IDLE; end
      S_R2: begin sym = K23_7; symk = 1'b1; nst = S_IDLE; end
      default: begin                               // S_CFG: /C1/ or /C2/ after K28.5
        symk = 1'b0;
        case (cn)
          2'd0: sym = c2 ? D2_2 : D21_5;
          2'd1: sym = cw[7:0];
          default: sym = cw[15:8];
        endcase
        if (cn == 2'd2) nst = S_IDLE; else nst = S_CFG;
      end
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      // the reset code group is the K28.5 (RD-) of an /I2/ at position 0;
      // it leaves the disparity positive and D16.2 follows
      st <= S_IDLE2; rd <= 1'b1; even <= 1'b0; i1 <= 1'b0; c2 <= 1'b0; cn <= '0; cw <= '0;
      tbi <= 10'b0011111010;
    end else begin
      logic [10:0] e;
      e = encode(sym, symk, rd);
      tbi <= e[9:0];
      rd  <= e[10];
      even <= !even;
      st <= nst;
      if (st == S_IDLE && !cfg_tx && !tx_en) i1 <= rd;     // /I1/ corrects a positive RD
      if (st == S_IDLE && cfg_tx) begin cn <= '0; cw <= cfg_word; end
      if (st == S_CFG) begin
        cn <= cn + 2'd1;
        if (cn == 2'd2) c2 <= !c2;
      end
    end
  end
endmodule
""",
    sva="""
// code groups are never X and always have 4, 5 or 6 ones
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(tbi))
  else $error("SGMII: X on tbi");
assert property (@(posedge clk) disable iff (!rst_n) $countones(tbi) inside {4, 5, 6})
  else $error("SGMII: code group with %0d ones", $countones(tbi));
// running disparity alternates: two consecutive unbalanced code groups have
// opposite disparity
assert property (@(posedge clk) disable iff (!rst_n)
                 $countones(tbi) != 5 ##1 $countones(tbi) != 5 |-> ($countones(tbi) > 5) != ($countones($past(tbi)) > 5))
  else $error("SGMII: running disparity violated");
cover property (@(posedge clk) disable iff (!rst_n) tbi == 10'b1101101000);   // /S/ RD-
cover property (@(posedge clk) disable iff (!rst_n) tx_en && tx_er);
cover property (@(posedge clk) disable iff (!rst_n) cfg_tx);
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic [7:0] txd = 0;
logic tx_en = 0, tx_er = 0, cfg_tx = 0;
logic [15:0] cfg_word = 0;
wire [9:0] tbi;

always #5 clk = ~clk;

sgmii_model u_dut (.clk(clk), .rst_n(rst_n), .txd(txd), .tx_en(tx_en), .tx_er(tx_er), .cfg_tx(cfg_tx),
                   .cfg_word(cfg_word), .tbi(tbi));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

logic [9:0] hist [0:4095];
int n = 0;
logic [15:0] cwh [0:4095];
always @(posedge clk) if (rst_n) begin hist[n % 4096] <= tbi; cwh[n % 4096] <= cfg_word; n <= n + 1; end

// Reference 8b/10b data encoder written from the IEEE 802.3 Clause 36
// tables (Table 36-1a..e): explicit RD- and RD+ columns, independent of the
// model's complement-based encoder. rd = 1 means RD+. Returns {rd', code}.
logic [5:0] t6n [0:31] = '{6'b100111, 6'b011101, 6'b101101, 6'b110001, 6'b110101, 6'b101001, 6'b011001, 6'b111000,
                            6'b111001, 6'b100101, 6'b010101, 6'b110100, 6'b001101, 6'b101100, 6'b011100, 6'b010111,
                            6'b011011, 6'b100011, 6'b010011, 6'b110010, 6'b001011, 6'b101010, 6'b011010, 6'b111010,
                            6'b110011, 6'b100110, 6'b010110, 6'b110110, 6'b001110, 6'b101110, 6'b011110, 6'b101011};
logic [5:0] t6p [0:31] = '{6'b011000, 6'b100010, 6'b010010, 6'b110001, 6'b001010, 6'b101001, 6'b011001, 6'b000111,
                            6'b000110, 6'b100101, 6'b010101, 6'b110100, 6'b001101, 6'b101100, 6'b011100, 6'b101000,
                            6'b100100, 6'b100011, 6'b010011, 6'b110010, 6'b001011, 6'b101010, 6'b011010, 6'b000101,
                            6'b001100, 6'b100110, 6'b010110, 6'b001001, 6'b001110, 6'b010001, 6'b100001, 6'b010100};
logic [3:0] t4n [0:8] = '{4'b1011, 4'b1001, 4'b0101, 4'b1100, 4'b1101, 4'b1010, 4'b0110, 4'b1110, 4'b0111};
logic [3:0] t4p [0:8] = '{4'b0100, 4'b1001, 4'b0101, 4'b0011, 4'b0010, 4'b1010, 4'b0110, 4'b0001, 4'b1000};
int a7_hits = 0;
function automatic logic [10:0] ref_enc(input logic [7:0] d, input logic rd);
  logic [5:0] c6; logic [3:0] c4; logic r; int y;
  c6 = rd ? t6p[d[4:0]] : t6n[d[4:0]];
  r  = ($countones(c6) == 3) ? rd : !rd;
  y  = d[7:5];
  if (y == 7 && ((!r && d[4:0] inside {5'd17, 5'd18, 5'd20}) || (r && d[4:0] inside {5'd11, 5'd13, 5'd14}))) begin
    y = 8; a7_hits++;
  end
  c4 = r ? t4p[y] : t4n[y];
  if ($countones(c4) != 2) r = !r;
  return {r, c6, c4};
endfunction
// data code group -> byte (-1 if not a valid data code group)
function automatic int ref_dec(input logic [9:0] c);
  logic [10:0] e;
  for (int v = 0; v < 256; v++) for (int r = 0; r < 2; r++) begin
    e = ref_enc(v[7:0], r[0]);
    if (e[9:0] == c) return v;
  end
  return -1;
endfunction

// index of the first code group equal to c at or after position from
function automatic int find(input logic [9:0] c, input int from);
  for (int i = from; i < n; i++) if (hist[i] == c) return i;
  return -1;
endfunction

initial begin
  int s, t, r, s0;
  repeat (3) @(posedge clk);
  rst_n = 1;
  repeat (10) @(negedge clk);
  // idle from RD-: K28.5 (RD-) then D16.2 (RD+), repeating; positions are
  // counted from this first comma (even)
  s0 = find(10'b0011111010, 1);
  chk(s0 >= 0 && hist[s0 + 1] == 10'b1001000101, "/I2/ idle ordered set");
  chk(hist[s0 + 2] == hist[s0] && hist[s0 + 3] == hist[s0 + 1], "idle repeats with RD- at every ordered set");
  // a short frame: 7 x 0x55, SFD, 4 bytes
  for (int i = 0; i < 12; i++) begin
    @(negedge clk); tx_en = 1; txd = (i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : 8'hA0 + i;
  end
  @(negedge clk); tx_en = 0;
  repeat (12) @(negedge clk);
  s = find(10'b1101101000, 0);
  chk(s >= 0 && (s - s0) % 2 == 0, "/S/ (K27.7 RD-) at an even position");
  chk(hist[s + 1] == 10'b1010100101, "preamble 0x55 = D21.2");
  t = find(10'b1011101000, s);
  if (t < 0) t = find(10'b0100010111, s);
  chk(t > s, "/T/ (K29.7) after the frame");
  r = t + 1;
  chk(hist[r] == 10'b1110101000 || hist[r] == 10'b0001010111, "/R/ (K23.7) after /T/");
  if ((t - s0) % 2 == 1) begin chk(hist[r + 1] == hist[r] || hist[r + 1] == ~hist[r], "second /R/ when /T/ is odd"); r++; end
  chk((r + 1 - s0) % 2 == 0 && (hist[r + 1] == 10'b0011111010 || hist[r + 1] == 10'b1100000101), "idle comma at an even position after /R/");
  // tx_er inside a frame becomes /V/ (K30.7)
  for (int i = 0; i < 10; i++) begin
    @(negedge clk); tx_en = 1; tx_er = (i == 9); txd = (i < 7) ? 8'h55 : 8'hD5;
  end
  @(negedge clk); tx_en = 0; tx_er = 0;
  repeat (12) @(negedge clk);
  chk(find(10'b0111101000, r) > 0 || find(10'b1000010111, r) > 0, "/V/ (K30.7) for tx_er");
  // configuration ordered sets: K28.5, D21.5, then the word
  @(negedge clk); cfg_word = 16'h9801; cfg_tx = 1;
  repeat (16) @(negedge clk);
  cfg_tx = 0;
  repeat (8) @(negedge clk);
  s = find(10'b1010101010, r);
  chk(s > 0 && (hist[s - 1] == 10'b0011111010 || hist[s - 1] == 10'b1100000101), "/C1/ = K28.5 D21.5");
  begin
    int c2a, c2b;
    c2a = find(10'b1011010101, r); c2b = find(10'b0100100101, r);
    chk((c2a < 0 || c2a > s) && (c2b < 0 || c2b > s), "the first configuration ordered set after reset is /C1/");
  end
  chk(hist[s + 1] == 10'b0111010100 || hist[s + 1] == 10'b1000101011, "config word low byte 0x01 = D1.0");
  chk(find(10'b1011010101, s) > 0 || find(10'b0100100101, s) > 0, "/C2/ = K28.5 D2.2");

  // every byte value through the data path, compared code group by code
  // group with the table encoder (both running disparities: the stream is
  // sent twice with an odd-disparity byte between)
  begin : all_bytes
    logic [10:0] e; logic rd; int bad = 0, s1, j;
    a7_hits = 0;
    for (int i = 0; i < 8 + 513; i++) begin
      @(negedge clk); tx_en = 1;
      txd = (i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : (i < 264) ? 8'(i - 8) : (i == 264) ? 8'h00 : 8'(i - 265);
    end
    @(negedge clk); tx_en = 0;
    repeat (12) @(negedge clk);
    s1 = find(10'b1101101000, s);
    // the preamble is shortened when /S/ waits for an even position; data
    // starts after the SFD (D21.6). Preamble and SFD are balanced, so RD- holds.
    j = s1 + 1;
    while (j < s1 + 10 && ref_dec(hist[j]) != 8'hD5) j++;
    rd = 1'b0;
    for (int i = 0; i < 513; i++) begin
      e = ref_enc((i < 256) ? 8'(i) : (i == 256) ? 8'h00 : 8'(i - 257), rd);
      if (hist[j + 1 + i] !== e[9:0]) begin
        if (bad < 4) $display("  byte %0d: got %b exp %b", i, hist[j + 1 + i], e[9:0]);
        bad++;
      end
      rd = e[10];
    end
    chk(s1 > 0 && bad == 0, $sformatf("all 256 data bytes match the Clause 36 tables (%0d mismatches)", bad));
    chk(a7_hits >= 6, "alternate D.x.A7 encodings exercised");
    s = s1;
  end
  // /T/ on both even and odd positions: the extra /R/ is K23.7 too
  for (int len = 9; len <= 10; len++) begin
    for (int i = 0; i < len; i++) begin
      @(negedge clk); tx_en = 1; txd = (i < 7) ? 8'h55 : (i == 7) ? 8'hD5 : 8'h3C;
    end
    @(negedge clk); tx_en = 0;
    repeat (8) @(negedge clk);
  end
  begin : rr
    int nr = 0, odd = 0;
    for (int i = s + 1; i < n - 2; i++)
      if (hist[i] == 10'b1011101000 || hist[i] == 10'b0100010111) begin
        chk(hist[i + 1] == 10'b1110101000 || hist[i + 1] == 10'b0001010111, "/R/ after /T/");
        if ((i - s0) % 2 == 1) begin
          odd++;
          chk(hist[i + 2] == 10'b1110101000 || hist[i + 2] == 10'b0001010111, "second /R/ (K23.7) when /T/ is odd");
        end
        nr++;
      end
    chk(nr >= 3 && odd >= 1, "/T/ seen at both parities");
  end
  // after every comma of an idle ordered set: /I1/ (D5.6) follows K28.5 RD+,
  // /I2/ (D16.2 RD+) follows K28.5 RD-
  begin : idle
    int bad = 0, n1 = 0;
    for (int i = 0; i < n - 1; i++) begin
      if (hist[i] == 10'b1100000101 && ref_dec(hist[i + 1]) == 8'hC5) n1++;
      else if (hist[i] == 10'b1100000101 && !(ref_dec(hist[i + 1]) inside {8'hB5, 8'h42})) bad++;
      if (hist[i] == 10'b0011111010 && !(hist[i + 1] inside {10'b1001000101, 10'b1010101010, 10'b0100100101})) bad++;
    end
    chk(bad == 0 && n1 > 0, $sformatf("/I1/ and /I2/ chosen by the comma disparity (%0d bad)", bad));
  end
  // reset state: the first code group is D16.2 RD+ of an /I2/, then K28.5 RD-
  chk((hist[0] == 10'b0011111010 && hist[1] == 10'b1001000101) || (hist[0] == 10'b1001000101 && hist[1] == 10'b0011111010),
      "first code groups after reset: K28.5 RD- then D16.2 RD+");
  // configuration with a word that changes every clock: each /C/ carries the
  // word sampled with its K28.5, and /C1/ comes first
  begin : cfgw
    int c0, bad = 0, nc = 0, alt = 0, prev = -1;
    c0 = n;
    @(negedge clk); cfg_tx = 1;
    repeat (40) begin cfg_word = $urandom; @(negedge clk); end
    cfg_tx = 0;
    repeat (8) @(negedge clk);
    for (int i = c0; i < n - 3; i++)
      if ((hist[i] == 10'b0011111010 || hist[i] == 10'b1100000101) && ref_dec(hist[i + 1]) inside {8'hB5, 8'h42}) begin
        if (prev >= 0 && ref_dec(hist[i + 1]) == prev) alt++;
        prev = ref_dec(hist[i + 1]);
        nc++;
        if (ref_dec(hist[i + 2]) != cwh[i - 1][7:0] || ref_dec(hist[i + 3]) != cwh[i - 1][15:8]) bad++;
      end
    chk(nc >= 8 && bad == 0, $sformatf("config word sampled with its comma (%0d of %0d bad)", bad, nc));
    chk(alt == 0, "/C1/ and /C2/ alternate");
  end

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #200000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
SPEC["defs"] += ENC
