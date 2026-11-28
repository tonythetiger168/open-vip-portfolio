# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""MAC receive agents for the MII family (GMII, RGMII, XGMII).

The agent is the PHY: it sends frames (preamble, SFD, MAC frame) on the
receive pins of the bus, plus the bus's own events (GMII / RGMII false
carrier, RGMII in-band link status, XGMII link fault sequences). The DUT
model is a MAC receiver: a bus front end (one per VIP) feeds a common IEEE
802.3 clause 3 / 4 receive check that ends every frame with fr_done and a
status code:

  0 good, 1 preamble / SFD / Start error, 2 code error (rx_er, /E/, a
  control character inside the frame), 3 FCS error, 4 runt (< 64 bytes),
  5 oversize (> 1518, > 1522 with an 802.1Q tag), 6 length field does not
  match the data (or 1501..1535), 7 filtered by the destination address
  (unicast not for the station, multicast while disabled, unless promiscuous)

and reports the length / type, the destination class, the VLAN tag and MAC
PAUSE frames (01-80-C2-00-00-01 or the station address, type 8808, opcode
0001) with their pause quanta. The scoreboard's reference model applies the
same rules to the bytes the monitor saw on the bus.
"""

# ----------------------------------------------------------------- common ---

def defs(p, P):
    return """
localparam bit [47:0] {P}_STATION = 48'h0200_0000_0001;   // DUT station address
localparam bit [47:0] {P}_PAUSE_DA = 48'h0180_C200_0001;

typedef enum bit [1:0] {{{P}_FRAME, {P}_FC, {P}_STATUS, {P}_FAULT}} {p}_kind_e;
typedef enum bit [2:0] {{{P}_X_NONE, {P}_X_PRE, {P}_X_NOSFD, {P}_X_CODE, {P}_X_FCS, {P}_X_RUNT, {P}_X_OVER,
                        {P}_X_LEN}} {p}_inj_e;
typedef enum bit [2:0] {{{P}_D_SELF, {P}_D_OTHER, {P}_D_MCAST, {P}_D_BCAST, {P}_D_PAUSE}} {p}_da_e;

// IEEE 802.3 CRC-32 (reflected 0xEDB88320, init and final xor all ones)
function automatic bit [31:0] {p}_crc32(bit [7:0] b[$], int unsigned n);
  bit [31:0] c = 32'hFFFF_FFFF;
  for (int unsigned i = 0; i < n; i++) begin
    c ^= {{24'h0, b[i]}};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  return ~c;
endfunction

// receive check of one frame (bytes after the SFD): status and reported fields
function automatic void {p}_mac_check(input bit [7:0] b[$], input bit pre_bad, input bit code_err,
                                     input bit [47:0] station, input bit promisc, input bit mcast_en,
                                     output bit [2:0] st, output bit [15:0] et, output bit [1:0] ca,
                                     output bit vl, output bit pz, output bit [15:0] qz);
  int unsigned n = b.size(), pa;
  bit [31:0] c;
  bit [47:0] da;
  bit [15:0] lt;
  bit v;
  st = 0; et = 0; ca = 0; vl = 0; pz = 0; qz = 0;
  if (pre_bad) begin st = 1; return; end
  if (code_err) begin st = 2; return; end
  if (n < 64) begin st = 4; return; end
  v = ({{b[12], b[13]}} == 16'h8100);
  if (n > (v ? 1522 : 1518)) begin st = 5; return; end
  c = {p}_crc32(b, n - 4);
  if ({{b[n-1], b[n-2], b[n-3], b[n-4]}} != c) begin st = 3; return; end
  lt = v ? {{b[16], b[17]}} : {{b[12], b[13]}};
  da = {{b[0], b[1], b[2], b[3], b[4], b[5]}};
  et = lt; vl = v;
  ca = (da == 48'hFFFF_FFFF_FFFF) ? 2'd3 : da[40] ? 2'd2 : 2'd1;
  pa = n - 18 - (v ? 4 : 0);
  if (lt > 1500 && lt < 1536) st = 6;
  else if (lt <= 1500 && (lt > pa || (lt < pa && pa > (v ? 42 : 46)))) st = 6;
  else if (!v && lt == 16'h8808 && {{b[14], b[15]}} == 16'h0001 && (da == {P}_PAUSE_DA || da == station)) begin
    pz = 1; qz = {{b[16], b[17]}};
  end
  else if (!promisc && ((ca == 1 && da != station) || (ca == 2 && !mcast_en))) st = 7;
endfunction
""".format(p=p, P=P)


COMMON_FIELDS = [
    ("KIND", "kind", "req"),
    ("bit [7:0]", "bytes", "req", "q"),       # bytes after the SFD as seen on the bus
    ("bit", "pre_bad", "req", "norand"),      # preamble / SFD / Start error on the bus
    ("bit", "code_err", "req", "norand"),     # error signalled on the bus inside the frame
    ("bit [2:0]", "status", "rsp"),
    ("bit [15:0]", "len", "rsp"),
    ("bit [15:0]", "etype", "rsp"),
    ("bit [1:0]", "cast", "rsp"),             # 1 unicast, 2 multicast, 3 broadcast
    ("bit", "vlan", "rsp"),
    ("bit", "pause", "rsp"),
    ("bit [15:0]", "quanta", "rsp"),
    ("INJ", "inj", "info", "rand"),
    ("DA", "dak", "info", "rand"),
    ("bit", "vtag", "info", "rand"),
    ("bit", "use_len", "info", "rand"),
    ("bit [10:0]", "plen", "info", "rand"),
    ("bit [2:0]", "pre_n", "info", "rand"),   # preamble bytes before the SFD (GMII / RGMII)
    ("bit [15:0]", "pq", "info", "rand"),
    ("bit [31:0]", "seed", "info", "rand"),
    ("bit [3:0]", "gap", "info", "rand"),
]


def fields(p, extra):
    out = []
    for f in COMMON_FIELDS + extra:
        d = {"KIND": p + "_kind_e", "INJ": p + "_inj_e", "DA": p + "_da_e"}.get(f[0], f[0])
        out.append((d,) + tuple(f[1:]))
    return out


def constraints(P, kinds):
    return """
constraint c_kind {{ kind dist {{ {kinds} }}; }}
constraint c_inj  {{ inj dist {{ {P}_X_NONE := 12, [{P}_X_PRE : {P}_X_LEN] :/ 6 }};
                    inj == {P}_X_LEN -> dak != {P}_D_PAUSE; }}
constraint c_da   {{ dak dist {{ {P}_D_SELF := 6, {P}_D_OTHER := 1, {P}_D_MCAST := 1, {P}_D_BCAST := 1, {P}_D_PAUSE := 1 }}; }}
constraint c_len  {{ plen dist {{ [0:45] :/ 2, [46:200] :/ 6, [1400:1500] :/ 1 }}; pre_n inside {{[1:7]}};
                    vtag dist {{ 0 := 3, 1 := 1 }}; gap inside {{[0:4]}}; }}
""".format(P=P, kinds=", ".join("%s := %d" % k for k in kinds))


TR_FUNCS = """
// the MAC frame (DA .. FCS) for the item's knobs; station: the DUT's address
function void build(bit [47:0] station);
  bit [31:0] x = seed | 32'h1, c;
  bit [47:0] da;
  int unsigned n, pad;
  bit [15:0] lt;
  case (dak)
    {P}_D_SELF:  da = station;
    {P}_D_OTHER: da = station ^ 48'h0000_0000_0300;
    {P}_D_MCAST: da = 48'h0100_5E00_0000 | seed[7:0];
    {P}_D_BCAST: da = 48'hFFFF_FFFF_FFFF;
    default:     da = {P}_PAUSE_DA;
  endcase
  bytes.delete();
  for (int i = 5; i >= 0; i--) bytes.push_back(da[8*i +: 8]);
  for (int i = 5; i >= 0; i--) bytes.push_back(8'hA0 + i);
  if (dak == {P}_D_PAUSE) begin
    bytes.push_back(8'h88); bytes.push_back(8'h08); bytes.push_back(8'h00); bytes.push_back(8'h01);
    bytes.push_back(pq[15:8]); bytes.push_back(pq[7:0]);
    repeat (42) bytes.push_back(8'h00);
  end else begin
    int unsigned pl = (inj == {P}_X_OVER) ? 1501 + plen[3:0] : (inj == {P}_X_RUNT) ? plen % 40 : plen;
    if (vtag) begin bytes.push_back(8'h81); bytes.push_back(8'h00); bytes.push_back(seed[15:8]); bytes.push_back(seed[7:0]); end
    lt = (use_len && inj != {P}_X_OVER) ? 16'(pl) : 16'h0800;
    if (inj == {P}_X_LEN) lt = (pl > 46) ? 16'(pl - 1) : 16'(pl + 47);
    bytes.push_back(lt[15:8]); bytes.push_back(lt[7:0]);
    for (int unsigned i = 0; i < pl; i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      bytes.push_back(x[7:0]);
    end
    pad = vtag ? 42 : 46;
    if (inj != {P}_X_RUNT) while (bytes.size() < 14 + 4 * vtag + pad) bytes.push_back(8'h00);
  end
  c = {p}_crc32(bytes, bytes.size());
  if (inj == {P}_X_FCS) c ^= 32'h1 << seed[4:0];
  for (int i = 0; i < 4; i++) bytes.push_back(c[8*i +: 8]);
endfunction
"""

PREDICT = """
bit [2:0] st; bit [15:0] et, qz; bit [1:0] ca; bit vl, pz;
if (t.kind == {P}_FRAME) begin
  {p}_mac_check(t.bytes, t.pre_bad, t.code_err, cfg.station, cfg.promisc, cfg.mcast_en, st, et, ca, vl, pz, qz);
  t.status = st; t.len = t.bytes.size(); t.etype = et; t.cast = ca; t.vlan = vl; t.pause = pz; t.quanta = qz;
end else begin
  t.status = 0; t.len = 0; t.etype = 0; t.cast = 0; t.vlan = 0; t.pause = 0; t.quanta = 0;
end
"""

CHECKS = """
if (t.kind == {P}_FRAME && t.len != t.bytes.size()) fail(t, "reported length differs from the frame on the bus");
if (t.pause && t.status != 0) fail(t, "PAUSE reported on a frame with an error");
"""

COVERAGE = """
cp_kind   : coverpoint tr.kind {{ bins k[] = {{{kinds}}}; }}
cp_status : coverpoint tr.status iff (tr.kind == {P}_FRAME);
cp_cast   : coverpoint tr.cast iff (tr.kind == {P}_FRAME && tr.status inside {{0, 7}}) {{ bins u = {{1}}; bins m = {{2}}; bins b = {{3}}; }}
cp_vlan   : coverpoint tr.vlan iff (tr.kind == {P}_FRAME && tr.status == 0);
cp_pause  : coverpoint tr.pause iff (tr.kind == {P}_FRAME && tr.status == 0);
cp_type   : coverpoint (tr.etype > 1500) iff (tr.kind == {P}_FRAME && tr.status == 0);
cp_len    : coverpoint tr.len iff (tr.kind == {P}_FRAME && tr.status == 0) {{
              bins min_ = {{64}}; bins short_ = {{[65:127]}}; bins mid = {{[128:1023]}}; bins long_ = {{[1024:1517]}};
              bins max_ = {{1518}}; bins tag_max = {{[1519:1522]}}; }}
"""

# Common part of the directed sequence: every status, class and boundary
DIRECTED = """
// good frames: unicast, broadcast, multicast, vtag, PAUSE, minimum and maximum length
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_SELF; t.vtag = 0; t.use_len = 1; t.plen = 46; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_BCAST; t.vtag = 0; t.use_len = 0; t.plen = 1500; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_MCAST; t.vtag = 1; t.use_len = 0; t.plen = 1500; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_SELF; t.vtag = 1; t.use_len = 1; t.plen = 10; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_PAUSE; t.vtag = 0; t.pq = 16'h1234; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_OTHER; t.vtag = 0; t.plen = 80; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_SELF; t.vtag = 0; t.use_len = 0; t.plen = 100; send(t);
t = item(); t.kind = {P}_FRAME; t.inj = {P}_X_NONE; t.dak = {P}_D_SELF; t.vtag = 0; t.use_len = 0; t.plen = 1000; send(t);
// every injected error
for (int i = 1; i < 8; i++) begin
  t = item(); t.kind = {P}_FRAME; t.inj = {p}_inj_e'(i); t.dak = {P}_D_SELF; t.plen = 60 + i; t.use_len = 1; send(t);
end
"""

PAIR = "0"


def build_spec(vip, p, P, desc, about, ports, bus_fields, kinds, cfg_extra, drv_idle, drv_item, drv_members,
               drv_tasks, mon_run, mon_tasks, extra_predict, extra_cov, directed, model_front, model_ports,
               sva, smoke_bus, smoke_tests, timeout=4000, drain=4000):
    f = lambda s: s.format(p=p, P=P)
    spec = dict(
        vip=vip, p=p, P=P, dir=p, family="Networking",
        desc=desc, about=about,
        defs=defs(p, P),
        timeout=timeout,
        ports=[("in", "logic [47:0]", "station"), ("in", "logic", "promisc"), ("in", "logic", "mcast_en")] + ports + [
            ("out", "logic", "fr_done"), ("out", "logic [2:0]", "fr_status"), ("out", "logic [15:0]", "fr_len"),
            ("out", "logic [15:0]", "fr_etype"), ("out", "logic [1:0]", "fr_cast"), ("out", "logic", "fr_vlan"),
            ("out", "logic", "pause_valid"), ("out", "logic [15:0]", "pause_quanta")] + model_ports,
        cfg=f("""bit [47:0] station = {P}_STATION;
bit        promisc = 0;
bit        mcast_en = 1;
""") + cfg_extra,
        fields=fields(p, bus_fields),
        constraints=constraints(P, kinds),
        tr_functions=TR_FUNCS.replace("{P}", P).replace("{p}", p),
        drv_rsp=False,
        drv_desc="one frame or bus event per item on the receive pins, then the inter-frame gap",
        drv_members=drv_members,
        drv_idle=drv_idle,
        drv_item=drv_item,
        drv_tasks=drv_tasks,
        mon_desc="frames and bus events on the receive pins, with the MAC's status and reported fields",
        mon_run=mon_run,
        mon_tasks=mon_tasks,
        predict=f(PREDICT) + extra_predict,
        checks=f(CHECKS),
        coverage=COVERAGE.format(p=p, P=P, kinds=", ".join(k for k, _ in kinds)) + extra_cov,
        directed=f(DIRECTED) + directed,
        drain_ns=drain,
    )
    spec["model"] = model(p, model_ports, ports, model_front)
    spec["sva"] = sva_common() + sva
    spec["smoke"] = smoke(p, ports, model_ports, smoke_bus, smoke_tests)
    return spec


# -------------------------------------------------------------- DUT model ---

MAC_CORE = """
  // MAC receive check, the clock after the front end ends a frame
  logic [31:0] crc;
  logic [47:0] da;
  logic [15:0] lt;
  logic        vl;
  integer      pa, k, j;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      fr_done <= 1'b0; fr_status <= 3'd0; fr_len <= 16'd0; fr_etype <= 16'd0; fr_cast <= 2'd0; fr_vlan <= 1'b0;
      pause_valid <= 1'b0; pause_quanta <= 16'd0;
    end else begin
      fr_done <= 1'b0;
      pause_valid <= 1'b0;
      if (fe_end) begin
        fr_done <= 1'b1; fr_len <= fcnt; fr_etype <= 16'd0; fr_cast <= 2'd0; fr_vlan <= 1'b0; pause_quanta <= 16'd0;
        vl = ({fb[12], fb[13]} == 16'h8100);
        lt = vl ? {fb[16], fb[17]} : {fb[12], fb[13]};
        da = {fb[0], fb[1], fb[2], fb[3], fb[4], fb[5]};
        if (f_pre) fr_status <= 3'd1;
        else if (f_code) fr_status <= 3'd2;
        else if (fcnt < 16'd64) fr_status <= 3'd4;
        else if (fcnt > (vl ? 16'd1522 : 16'd1518)) fr_status <= 3'd5;
        else begin
          crc = 32'hFFFF_FFFF;
          for (k = 0; k < fcnt - 4; k++) begin
            crc = crc ^ {24'h0, fb[k]};
            for (j = 0; j < 8; j++) crc = crc[0] ? ((crc >> 1) ^ 32'hEDB8_8320) : (crc >> 1);
          end
          crc = ~crc;
          if ({fb[fcnt-1], fb[fcnt-2], fb[fcnt-3], fb[fcnt-4]} != crc) fr_status <= 3'd3;
          else begin
            pa = fcnt - 18 - (vl ? 4 : 0);
            fr_etype <= lt; fr_vlan <= vl;
            fr_cast <= (da == 48'hFFFF_FFFF_FFFF) ? 2'd3 : da[40] ? 2'd2 : 2'd1;
            if (lt > 16'd1500 && lt < 16'd1536) fr_status <= 3'd6;
            else if (lt <= 16'd1500 && (lt > pa || (lt < pa && pa > (vl ? 42 : 46)))) fr_status <= 3'd6;
            else if (!vl && lt == 16'h8808 && {fb[14], fb[15]} == 16'h0001 &&
                     (da == 48'h0180_C200_0001 || da == station)) begin
              fr_status <= 3'd0; pause_valid <= 1'b1; pause_quanta <= {fb[16], fb[17]};
            end
            else if (!promisc && ((!da[40] && da != station) || (da[40] && da != 48'hFFFF_FFFF_FFFF && !mcast_en)))
              fr_status <= 3'd7;
            else fr_status <= 3'd0;
          end
        end
      end
    end
  end
"""


def model(p, model_ports, ports, front):
    plist = ["  input  logic        clk", "  input  logic        rst_n"]
    for d, t, n in ports:
        plist.append("  input  %-12s %s" % (t, n))
    plist += ["  input  logic [47:0] station", "  input  logic        promisc", "  input  logic        mcast_en",
              "  output logic        fr_done", "  output logic [2:0]  fr_status", "  output logic [15:0] fr_len",
              "  output logic [15:0] fr_etype", "  output logic [1:0]  fr_cast", "  output logic        fr_vlan",
              "  output logic        pause_valid", "  output logic [15:0] pause_quanta"]
    for d, t, n in model_ports:
        plist.append("  output %-12s %s" % (t, n))
    return """
module {p}_model (
{plist}
);
  // frame buffer filled by the bus front end
  logic [7:0]  fb [0:2047];
  logic [15:0] fcnt;
  logic        fe_end, f_pre, f_code;
{front}
{core}endmodule
""".format(p=p, plist=",\n".join(plist), front=front, core=MAC_CORE)


def sva_common():
    return """
// a frame result is a one-clock pulse; PAUSE only on a good frame
assert property (@(posedge clk) disable iff (!rst_n) fr_done |=> !fr_done)
  else $error("MAC: fr_done longer than one clock");
assert property (@(posedge clk) disable iff (!rst_n) pause_valid |-> fr_done && fr_status == 3'd0)
  else $error("MAC: pause_valid without a good frame");
// a good frame is at least 64 bytes and at most 1522
assert property (@(posedge clk) disable iff (!rst_n) fr_done && fr_status == 3'd0 |-> fr_len >= 16'd64 && fr_len <= 16'd1522)
  else $error("MAC: good frame outside 64..1522 bytes");
assert property (@(posedge clk) disable iff (!rst_n) fr_done && fr_status == 3'd4 |-> fr_len < 16'd64)
  else $error("MAC: runt status on a frame of 64 bytes or more");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({fr_done, fr_status, pause_valid}))
  else $error("MAC: X on frame outputs");
cover property (@(posedge clk) disable iff (!rst_n) pause_valid);
cover property (@(posedge clk) disable iff (!rst_n) fr_done && fr_status == 3'd3);
"""


# ------------------------------------------------------------ smoke TB ------

SMOKE_COMMON = """
int checks = 0;
int fails  = 0;

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// frame under construction: fr[0:fl-1] = DA .. FCS
logic [7:0] fr [0:2199];
int fl;
function automatic logic [31:0] crc32(input int n);
  logic [31:0] c = 32'hFFFF_FFFF;
  for (int i = 0; i < n; i++) begin
    c = c ^ {24'h0, fr[i]};
    for (int k = 0; k < 8; k++) c = c[0] ? ((c >> 1) ^ 32'hEDB8_8320) : (c >> 1);
  end
  return ~c;
endfunction
task automatic addb(input logic [7:0] b); fr[fl] = b; fl++; endtask
task automatic add_fcs();
  logic [31:0] c = crc32(fl);
  for (int i = 0; i < 4; i++) addb(c[8*i +: 8]);
endtask
// DA, SA, [tag,] length / type, n payload bytes, FCS
localparam logic [47:0] ST = 48'h0200_0000_0001;
task automatic mk(input logic [47:0] da, input logic [15:0] lt, input int n, input bit tag);
  fl = 0;
  for (int i = 5; i >= 0; i--) addb(da[8*i +: 8]);
  for (int i = 5; i >= 0; i--) addb(8'hA0 + i);
  if (tag) begin addb(8'h81); addb(8'h00); addb(8'h20); addb(8'h05); end
  addb(lt[15:8]); addb(lt[7:0]);
  for (int i = 0; i < n; i++) addb(8'(i * 7 + 3));
  add_fcs();
endtask
task automatic mk_pause(input logic [47:0] da, input logic [15:0] op, input logic [15:0] q);
  fl = 0;
  for (int i = 5; i >= 0; i--) addb(da[8*i +: 8]);
  for (int i = 5; i >= 0; i--) addb(8'hA0 + i);
  addb(8'h88); addb(8'h08); addb(op[15:8]); addb(op[7:0]); addb(q[15:8]); addb(q[7:0]);
  repeat (42) addb(8'h00);
  add_fcs();
endtask

// frame results
int ndone = 0, npause = 0;
logic [2:0]  lst = 0;
logic [15:0] llen = 0, let_ = 0, lq = 0;
logic [1:0]  lca = 0;
logic        lvl = 0, lpz = 0;
always @(negedge clk) if (fr_done) begin
  ndone++; lst = fr_status; llen = fr_len; let_ = fr_etype; lca = fr_cast; lvl = fr_vlan; lpz = pause_valid;
  if (pause_valid) begin npause++; lq = pause_quanta; end
end

task automatic idle(input int n);
  repeat (n) @(negedge clk);
  #1;
endtask

// send fr with the bus task, expect one result with status s
int n0;
task automatic rx(input logic [2:0] s, input string msg);
  n0 = ndone;
  send(7, -1, 0, -1);
  idle(4);
  chk(ndone == n0 + 1 && lst == s && llen == fl, $sformatf("%s: status %0d (got %0d, len %0d/%0d, %0d results)",
      msg, s, lst, llen, fl, ndone - n0));
endtask
"""

SMOKE_MAC_TESTS = """
  // reset values
  idle(3);
  chk(!fr_done && fr_status == 0 && !pause_valid && !fr_vlan && fr_cast == 0 && fr_len == 0 && fr_etype == 0 &&
      pause_quanta == 0, "reset values");
  rst_n = 1;
  idle(4);

  // good frames and what is reported
  mk(ST, 16'd46, 46, 0); rx(0, "64-byte unicast to the station");
  chk(let_ == 46 && lca == 1 && !lvl && !lpz, "length 46, unicast, untagged");
  mk(48'hFFFF_FFFF_FFFF, 16'h0800, 100, 0); rx(0, "broadcast");
  chk(lca == 3 && let_ == 16'h0800, "broadcast class, type 0800");
  mk(48'h0100_5E00_0001, 16'h86DD, 60, 0); rx(0, "multicast");
  chk(lca == 2, "multicast class");
  mk(ST, 16'h0800, 46, 1); rx(0, "vtag frame");
  chk(lvl && let_ == 16'h0800, "802.1Q tag skipped for the type");
  mk(48'hFFFF_FFFF_FFFE, 16'h0800, 46, 0); rx(0, "multicast all-but-broadcast");
  chk(lca == 2, "FF-FF-FF-FF-FF-FE is multicast, not broadcast");

  // address filter
  mk(ST ^ 48'h1, 16'h0800, 46, 0); rx(7, "unicast for another station");
  mk(ST ^ 48'h0000_8000_0000, 16'h0800, 46, 0); rx(7, "unicast differing in byte 2");
  mk(ST ^ 48'h0200_0000_0000, 16'h0800, 46, 0); rx(7, "unicast differing in byte 0");
  chk(lca == 1 && let_ == 16'h0800, "filtered frame still reports its fields");
  mcast_en = 0;
  mk(48'h0100_5E00_0001, 16'h0800, 46, 0); rx(7, "multicast while disabled");
  mk(48'hFFFF_FFFF_FFFF, 16'h0800, 46, 0); rx(0, "broadcast while multicast is disabled");
  promisc = 1;
  mk(48'h0100_5E00_0001, 16'h0800, 46, 0); rx(0, "promiscuous: multicast");
  mk(ST ^ 48'h1, 16'h0800, 46, 0); rx(0, "promiscuous: other unicast");
  promisc = 0; mcast_en = 1;
  station = 48'h0200_0000_0099;
  mk(48'h0200_0000_0099, 16'h0800, 46, 0); rx(0, "new station address");
  mk(ST, 16'h0800, 46, 0); rx(7, "old station address filtered");
  station = ST;

  // FCS
  mk(ST, 16'h0800, 46, 0); fr[fl - 4] ^= 8'h01; rx(3, "FCS byte 0 wrong");
  mk(ST, 16'h0800, 46, 0); fr[fl - 1] ^= 8'h80; rx(3, "FCS byte 3 wrong");
  mk(ST, 16'h0800, 46, 0); fr[20] ^= 8'h10; rx(3, "payload bit flipped");
  mk(ST, 16'h0800, 46, 0); fr[0] ^= 8'h04; rx(3, "FCS checked before the address");

  // length limits
  mk(ST, 16'h0800, 46, 1); rx(0, "tagged frame before the runt");
  mk(ST, 16'h0800, 45, 0); rx(4, "63-byte runt");
  chk(let_ == 0 && lca == 0 && !lvl, "runt reports no fields");
  mk(ST, 16'h0800, 10, 0); fr[fl - 1] ^= 1; rx(4, "runt checked before the FCS");
  mk(ST, 16'h0800, 1500, 0); rx(0, "1518 bytes");
  mk(ST, 16'h0800, 1501, 0); rx(5, "1519 bytes");
  mk(ST, 16'h0800, 1504, 0); rx(5, "1522 bytes untagged");
  mk(ST, 16'h0800, 1500, 1); rx(0, "1522 bytes vtag");
  mk(ST, 16'h0800, 1501, 1); rx(5, "1523 bytes vtag");
  mk(ST, 16'h0800, 1501, 0); fr[fl - 1] ^= 1; rx(5, "oversize checked before the FCS");
  mk(ST, 16'h0800, 2082, 0); rx(5, "2100-byte jabber: counted past the buffer");

  // length field
  mk(ST, 16'd45, 46, 0); rx(0, "length 45 padded to 46");
  mk(ST, 16'd0, 46, 0); rx(0, "length 0 padded");
  mk(ST, 16'd47, 46, 0); rx(6, "length 47 with 46 bytes");
  mk(ST, 16'd100, 100, 0); rx(0, "length 100 exact");
  mk(ST, 16'd99, 100, 0); rx(6, "length 99 with 100 bytes");
  mk(ST, 16'd101, 100, 0); rx(6, "length 101 with 100 bytes");
  mk(ST, 16'd46, 47, 0); rx(6, "length 46 with 47 bytes");
  mk(ST, 16'd42, 42, 1); rx(0, "vtag length 42 exact");
  mk(ST, 16'd10, 42, 1); rx(0, "vtag length 10 padded to 42");
  mk(ST, 16'd10, 43, 1); rx(6, "vtag length 10 with 43 bytes");
  mk(ST, 16'd43, 42, 1); rx(6, "vtag length 43 with 42 bytes");
  mk(ST, 16'd1500, 1500, 0); rx(0, "length 1500");
  mk(ST, 16'd1500, 1499, 0); rx(6, "length 1500 with 1499 bytes");
  mk(ST, 16'd1501, 100, 0); rx(6, "length / type 1501");
  mk(ST, 16'd1535, 100, 0); rx(6, "length / type 1535");
  mk(ST, 16'd1536, 100, 0); rx(0, "type 0600");
  chk(let_ == 16'd1536, "type 0600 reported");
  mk(ST ^ 48'h1, 16'd47, 46, 0); rx(6, "length error before the address filter");

  // PAUSE
  mk_pause(48'h0180_C200_0001, 16'h0001, 16'hBEEF); rx(0, "PAUSE to 01-80-C2-00-00-01");
  chk(lpz && lq == 16'hBEEF && npause == 1 && let_ == 16'h8808, "pause quanta BEEF");
  mk_pause(ST, 16'h0001, 16'h0010); rx(0, "PAUSE to the station address");
  chk(lpz && lq == 16'h0010, "pause to the station");
  mk_pause(48'h0180_C200_0001, 16'h0002, 16'h0010); rx(0, "MAC control opcode 2");
  chk(!lpz && lca == 2, "opcode 2: not a PAUSE");
  mk_pause(48'h0180_C200_0001, 16'h0101, 16'h0010); rx(0, "MAC control opcode 0101");
  chk(!lpz, "opcode 0101: not a PAUSE");
  mk_pause(48'h0180_C200_0002, 16'h0001, 16'h0010); rx(0, "PAUSE to another multicast");
  chk(!lpz, "PAUSE to 01-80-C2-00-00-02 not honoured");
  mk_pause(48'h0180_C200_0001, 16'h0001, 16'h0010); fr[12] = 8'h88; fr[13] = 8'h09;
  fl = fl - 4; add_fcs(); rx(0, "type 8809");
  chk(!lpz, "type 8809: not a PAUSE");
  mk(48'h0180_C200_0001, 16'h8808, 50, 1); fr[18] = 8'h00; fr[19] = 8'h01; fl = fl - 4; add_fcs();
  rx(0, "vtag MAC control frame");
  chk(!lpz, "vtag: not a PAUSE");
  mk_pause(ST ^ 48'h1, 16'h0001, 16'h0010); rx(7, "PAUSE to another station");
  chk(!lpz && npause == 2, "only two PAUSE frames honoured");
"""


def smoke(p, ports, model_ports, bus, tests):
    decl = []
    for d, t, n in ports + model_ports:
        if d == "in":
            decl.append("%s %s = '0;" % (t.replace("logic", "logic"), n))
        else:
            decl.append("wire %s %s;" % (t.replace("logic", "").strip() or "", n))
    conn = ", ".join(".%s(%s)" % (n, n) for _, _, n in ports + model_ports)
    return """
logic clk = 1'b0;
logic rst_n = 1'b0;
logic [47:0] station = 48'h0200_0000_0001;
logic promisc = 1'b0, mcast_en = 1'b1;
{decl}
wire fr_done, fr_vlan, pause_valid;
wire [2:0] fr_status;
wire [15:0] fr_len, fr_etype, pause_quanta;
wire [1:0] fr_cast;

always #5 clk = ~clk;

{p}_model u_dut (.clk(clk), .rst_n(rst_n), {conn}, .station(station), .promisc(promisc), .mcast_en(mcast_en),
               .fr_done(fr_done), .fr_status(fr_status), .fr_len(fr_len), .fr_etype(fr_etype), .fr_cast(fr_cast),
               .fr_vlan(fr_vlan), .pause_valid(pause_valid), .pause_quanta(pause_quanta));
{common}
{bus}
initial begin
{mac}
{tests}
  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #20000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""".format(p=p, decl="\n".join(decl), conn=conn, common=SMOKE_COMMON, bus=bus, mac=SMOKE_MAC_TESTS, tests=tests)
