# AMBA ACE (AXI Coherency Extensions, ARM IHI 0022 part C) cached manager agent.
#
# The agent is a caching master with 16 lines of 16 bytes (four 32-bit beats,
# lines 0x000-0x0F0 shareable, 0x100-0x1F0 non-shareable). It issues
# ReadNoSnoop, ReadOnce, ReadShared, ReadUnique, CleanUnique (dataless: one R
# transfer), WriteNoSnoop, WriteUnique and WriteBack with RACK / WACK, keeps
# the ACE line states (I, UC, UD, SC, SD) from RRESP[3:2] (IsShared,
# PassDirty), and answers snoops on AC / CR / CD from those states.
# A requested command is made legal for the line's state before it is issued:
#   UC / SC: the clean line is dropped silently first (allowed for clean
#            lines), except CleanUnique from SC
#   UD / SD: WriteBack, except CleanUnique from SD
#   I:       CleanUnique becomes ReadUnique, WriteBack becomes WriteUnique
# ReadUnique / CleanUnique carry a store (word, wdata, wstrb) applied to the
# line once it is unique (state UD). A snoop to a line with a WriteBack in
# progress is answered after the WriteBack completes (the line is then I).
#
# tb/top_tb.sv ace_model is the interconnect with memory and one other
# (modelled) caching master, the "peer", whose line state is I, SC or UD:
#   * reads: ReadShared from a UD peer returns its dirty data with
#     IsShared + PassDirty (peer -> SC); ReadUnique takes the peer's copy
#     (PassDirty if it was dirty, peer -> I); CleanUnique writes a dirty peer
#     line to memory and invalidates it; ReadOnce returns the current data
#   * writes: WriteUnique merges into the peer's dirty data if any (peer -> I);
#     WriteBack writes memory
#   * snoops: when idle (no transaction in progress, no RACK / WACK owed) the
#     peer starts, from an LFSR, ReadOnce, ReadShared, ReadUnique (then
#     modifies the line: every word + 1), CleanInvalid or MakeInvalid (then
#     writes the whole line: ~memory) to a random line, which reaches this
#     master as a snoop; PassDirty data from the master goes to memory
#     (ReadUnique: to the peer)
#   * a read or WriteUnique accepted while a snoop is outstanding is answered
#     after the snoop (snoop first); a WriteBack completes independently
from _lib import wait_cb

C = dict(RD_NOSNOOP=0, RD_ONCE=1, RD_SHARED=2, RD_UNIQUE=3, CLEAN_UNIQUE=4, WR_NOSNOOP=5,
         WR_UNIQUE=6, WR_BACK=7, SN_RD_ONCE=8, SN_RD_SHARED=9, SN_RD_UNIQUE=10, SN_CLEAN_INV=11,
         SN_MAKE_INV=12, BAD=15)

DEFS = "\n".join("localparam bit [3:0] C_%s = 4'd%d;" % (k, v) for k, v in C.items()) + """
// line states
localparam bit [2:0] ST_I = 3'd0, ST_UC = 3'd1, ST_UD = 3'd2, ST_SC = 3'd3, ST_SD = 3'd4;

// command -> AR / AW signals
function automatic bit [3:0] ace_arsnoop(bit [3:0] c);
  case (c)
    C_RD_SHARED:    return 4'b0001;
    C_RD_UNIQUE:    return 4'b0111;
    C_CLEAN_UNIQUE: return 4'b1011;
    default:        return 4'b0000;     // ReadNoSnoop / ReadOnce
  endcase
endfunction
function automatic bit [2:0] ace_awsnoop(bit [3:0] c);
  return (c == C_WR_BACK) ? 3'b011 : 3'b000;   // WriteNoSnoop / WriteUnique 000
endfunction
// AR / AW / AC signals -> command
function automatic bit [3:0] ace_ar_cmd(bit [3:0] snoop, bit [1:0] domain);
  if (domain == 2'b00 || domain == 2'b11) return snoop == 4'b0000 ? C_RD_NOSNOOP : C_BAD;
  case (snoop)
    4'b0000: return C_RD_ONCE;
    4'b0001: return C_RD_SHARED;
    4'b0111: return C_RD_UNIQUE;
    4'b1011: return C_CLEAN_UNIQUE;
    default: return C_BAD;
  endcase
endfunction
function automatic bit [3:0] ace_aw_cmd(bit [2:0] snoop, bit [1:0] domain);
  if (domain == 2'b00 || domain == 2'b11) return snoop == 3'b000 ? C_WR_NOSNOOP : C_BAD;
  case (snoop)
    3'b000:  return C_WR_UNIQUE;
    3'b011:  return C_WR_BACK;
    default: return C_BAD;
  endcase
endfunction
function automatic bit [3:0] ace_ac_cmd(bit [3:0] snoop);
  case (snoop)
    4'b0000: return C_SN_RD_ONCE;
    4'b0001: return C_SN_RD_SHARED;
    4'b0111: return C_SN_RD_UNIQUE;
    4'b1001: return C_SN_CLEAN_INV;
    4'b1101: return C_SN_MAKE_INV;
    default: return C_BAD;
  endcase
endfunction
// initial memory contents: word w of line i
function automatic bit [127:0] ace_init_line(int i);
  bit [127:0] l;
  for (int w = 0; w < 4; w++) l[w*32 +: 32] = {24'hC0FFEE, 4'(i), 4'(w)};
  return l;
endfunction
// the peer's modification after its ReadUnique: every word + 1
function automatic bit [127:0] ace_inc_line(bit [127:0] x);
  bit [127:0] l;
  for (int w = 0; w < 4; w++) l[w*32 +: 32] = x[w*32 +: 32] + 32'd1;
  return l;
endfunction
"""

SPEC = dict(
    vip="ACE-UVM-VIP", p="ace", P="ACE", dir="ace", family="AMBA",
    desc="AMBA ACE cached manager VIP: ReadShared / ReadUnique / CleanUnique / ReadOnce / "
         "WriteUnique / WriteBack and non-snooping reads and writes, RRESP IsShared / PassDirty, "
         "RACK / WACK, snoop channels AC / CR / CD answered from a five-state cache model.",
    about="""
ACE adds hardware coherency to AXI4: a caching master keeps each line in one
of five states (Invalid, UniqueClean, UniqueDirty, SharedClean, SharedDirty),
the interconnect snoops the other caches on the AC channel and they answer on
CR (WasUnique, IsShared, PassDirty, Error, DataTransfer) and CD. This agent is
a caching master: it picks a legal transaction for the state of the line,
updates the state from the response, answers snoops from its cache, and
handles a snoop that crosses its own transaction (read: answered from the
state before the read; WriteBack: answered after it). The DUT model is an
interconnect with memory and a second caching master; the scoreboard keeps
its own memory and peer state, predicts every read's data and RRESP, and
applies every observed snoop and its CR / CD data. Snoop responses are checked
for legality (PassDirty only with DataTransfer, no data for MakeInvalid, no
IsShared after ReadUnique / CleanInvalid) and, from the agent, against the
monitor.""",
    timeout=400,
    ports=[
        ("in", "logic", "arvalid"), ("out", "logic", "arready"), ("in", "logic [31:0]", "araddr"),
        ("in", "logic [7:0]", "arlen"), ("in", "logic [2:0]", "arsize"), ("in", "logic [1:0]", "arburst"),
        ("in", "logic [3:0]", "arsnoop"), ("in", "logic [1:0]", "ardomain"), ("in", "logic [1:0]", "arbar"),
        ("out", "logic", "rvalid"), ("in", "logic", "rready"), ("out", "logic [31:0]", "rdata"),
        ("out", "logic [3:0]", "rresp"), ("out", "logic", "rlast"), ("in", "logic", "rack"),
        ("in", "logic", "awvalid"), ("out", "logic", "awready"), ("in", "logic [31:0]", "awaddr"),
        ("in", "logic [7:0]", "awlen"), ("in", "logic [2:0]", "awsize"), ("in", "logic [1:0]", "awburst"),
        ("in", "logic [2:0]", "awsnoop"), ("in", "logic [1:0]", "awdomain"), ("in", "logic [1:0]", "awbar"),
        ("in", "logic", "wvalid"), ("out", "logic", "wready"), ("in", "logic [31:0]", "wdata"),
        ("in", "logic [3:0]", "wstrb"), ("in", "logic", "wlast"),
        ("out", "logic", "bvalid"), ("in", "logic", "bready"), ("out", "logic [1:0]", "bresp"),
        ("in", "logic", "wack"),
        ("out", "logic", "acvalid"), ("in", "logic", "acready"), ("out", "logic [31:0]", "acaddr"),
        ("out", "logic [3:0]", "acsnoop"), ("out", "logic [2:0]", "acprot"),
        ("in", "logic", "crvalid"), ("out", "logic", "crready"), ("in", "logic [4:0]", "crresp"),
        ("in", "logic", "cdvalid"), ("out", "logic", "cdready"), ("in", "logic [31:0]", "cddata"),
        ("in", "logic", "cdlast"),
    ],
    defs=DEFS,
    cfg="int unsigned ready_pct = 70;   // percent of clocks RREADY / BREADY are high",
    fields=[
        ("bit [3:0]", "cmd", "req"),
        ("bit [31:0]", "addr", "req"),
        ("bit [1:0]", "word", "req"),             # store / WriteUnique word in the line
        ("bit [31:0]", "wdata", "req"),
        ("bit [3:0]", "wstrb", "req"),
        ("bit [127:0]", "wline", "req", "norand"),  # WriteBack data (from the cache)
        ("bit [127:0]", "rline", "rsp"),
        ("bit [3:0]", "rresp", "rsp"),             # RRESP of the last beat
        ("bit [1:0]", "bresp", "rsp"),
        ("bit [4:0]", "crresp", "rsp"),            # snoops: {WasUnique, IsShared, PassDirty, Error, DataTransfer}
        ("bit [127:0]", "cdline", "rsp"),
        ("bit [2:0]", "gap", "info", "rand"),
    ],
    constraints="""
constraint c_cmd  { cmd dist { C_RD_NOSNOOP := 1, C_RD_ONCE := 1, C_RD_SHARED := 4, C_RD_UNIQUE := 3,
                               C_CLEAN_UNIQUE := 3, C_WR_NOSNOOP := 1, C_WR_UNIQUE := 1, C_WR_BACK := 3 }; }
constraint c_addr { addr[3:0] == 0; addr[31:9] == 0;
                    addr[8] == (cmd == C_RD_NOSNOOP || cmd == C_WR_NOSNOOP); }
constraint c_wr   { (cmd == C_WR_NOSNOOP || cmd == C_WR_UNIQUE) -> wstrb != 4'h0; }
constraint c_gap  { gap dist { 0 := 4, [1:7] :/ 2 }; }
""",
    drv_desc="cache controller: legal command for the line state, AR/R + RACK or AW/W/B + WACK, "
             "snoops answered on CR / CD from the cache",
    drv_members="""bit [2:0]   cst [16];      // line states (ST_*)
bit [127:0] cdat [16];     // line data
bit         wb_busy = 0;   // WriteBack in progress to line wb_line
bit [3:0]   wb_line;""",
    drv_idle="""
vif.drv_cb.arvalid <= 1'b0; vif.drv_cb.araddr <= '0; vif.drv_cb.arlen <= '0; vif.drv_cb.arsize <= '0;
vif.drv_cb.arburst <= '0; vif.drv_cb.arsnoop <= '0; vif.drv_cb.ardomain <= '0; vif.drv_cb.arbar <= '0;
vif.drv_cb.rready <= 1'b0; vif.drv_cb.rack <= 1'b0;
vif.drv_cb.awvalid <= 1'b0; vif.drv_cb.awaddr <= '0; vif.drv_cb.awlen <= '0; vif.drv_cb.awsize <= '0;
vif.drv_cb.awburst <= '0; vif.drv_cb.awsnoop <= '0; vif.drv_cb.awdomain <= '0; vif.drv_cb.awbar <= '0;
vif.drv_cb.wvalid <= 1'b0; vif.drv_cb.wdata <= '0; vif.drv_cb.wstrb <= '0; vif.drv_cb.wlast <= 1'b0;
vif.drv_cb.bready <= 1'b0; vif.drv_cb.wack <= 1'b0;
vif.drv_cb.acready <= 1'b0; vif.drv_cb.crvalid <= 1'b0; vif.drv_cb.crresp <= '0;
vif.drv_cb.cdvalid <= 1'b0; vif.drv_cb.cddata <= '0; vif.drv_cb.cdlast <= 1'b0;
for (int i = 0; i < 16; i++) begin cst[i] = ST_I; cdat[i] = '0; end
""",
    # snoop responder: runs beside the transaction driver and does not wait
    # for it, except for a WriteBack to the snooped line
    drv_bg="""
forever begin
  bit [3:0] c, l;
  bit [31:0] a;
  bit [4:0] cr;
  bit [127:0] d;
  bit valid, dirty, uniq;
  vif.drv_cb.acready <= 1'b1;
  do @(vif.drv_cb); while (vif.drv_cb.acvalid !== 1'b1);
  vif.drv_cb.acready <= 1'b0;
  a = vif.drv_cb.acaddr; c = ace_ac_cmd(vif.drv_cb.acsnoop); l = a[7:4];
  while (wb_busy && wb_line == l) @(vif.drv_cb);
  valid = cst[l] != ST_I; dirty = cst[l] == ST_UD || cst[l] == ST_SD; uniq = cst[l] == ST_UC || cst[l] == ST_UD;
  d = cdat[l];
  case (c)
    C_SN_RD_ONCE:   cr = valid ? {uniq, 1'b1, 1'b0, 1'b0, 1'b1} : 5'b0;      // keeps the line
    C_SN_RD_SHARED: begin
                      cr = valid ? {uniq, 1'b1, 1'b0, 1'b0, 1'b1} : 5'b0;    // keeps it, dirty stays here
                      if (cst[l] == ST_UC) cst[l] = ST_SC;
                      if (cst[l] == ST_UD) cst[l] = ST_SD;
                    end
    C_SN_RD_UNIQUE: begin cr = valid ? {uniq, 1'b0, dirty, 1'b0, 1'b1} : 5'b0; cst[l] = ST_I; end
    C_SN_CLEAN_INV: begin cr = {uniq, 1'b0, dirty, 1'b0, dirty}; cst[l] = ST_I; end
    C_SN_MAKE_INV:  begin cr = {uniq, 4'b0}; cst[l] = ST_I; end
    default: begin cr = 5'b00010; `uvm_error("SNOOP", $sformatf("ACE: unsupported ACSNOOP %b", vif.drv_cb.acsnoop)) end
  endcase
  vif.drv_cb.crvalid <= 1'b1; vif.drv_cb.crresp <= cr;
""" + wait_cb("vif.drv_cb.crready === 1'b1", "ACE CRREADY") + """
  vif.drv_cb.crvalid <= 1'b0;
  if (cr[0]) for (int b = 0; b < 4; b++) begin
    vif.drv_cb.cdvalid <= 1'b1; vif.drv_cb.cddata <= d[b*32 +: 32]; vif.drv_cb.cdlast <= (b == 3);
""" + "\n".join("  " + x for x in wait_cb("vif.drv_cb.cdready === 1'b1", "ACE CDREADY").splitlines()) + """
  end
  vif.drv_cb.cdvalid <= 1'b0; vif.drv_cb.cdlast <= 1'b0;
end
""",
    drv_item="""
bit [3:0] l, c;
bit [2:0] s;
repeat (t.gap) @(vif.drv_cb);
l = t.addr[7:4];
c = t.cmd;
if (!t.addr[8]) begin
  // a legal command for the line state
  s = cst[l];
  if ((s == ST_UC || s == ST_SC) && !(c == C_CLEAN_UNIQUE && s == ST_SC)) begin cst[l] = ST_I; s = ST_I; end
  if (s == ST_UD || s == ST_SD) begin
    if (!(c == C_CLEAN_UNIQUE && s == ST_SD)) c = C_WR_BACK;
  end else if (s == ST_I) begin
    if (c == C_CLEAN_UNIQUE) c = C_RD_UNIQUE;
    else if (c == C_WR_BACK) begin c = C_WR_UNIQUE; if (t.wstrb == 0) t.wstrb = 4'hF; end
  end
end
t.cmd = c;
t.rline = 0; t.rresp = 0; t.bresp = 0; t.crresp = 0; t.cdline = 0; t.wline = 0;
if (c <= C_CLEAN_UNIQUE) begin
  bit [127:0] line = 0;
  int unsigned beat = 0, to = 0;
  bit done = 0;
  vif.drv_cb.arvalid <= 1'b1; vif.drv_cb.araddr <= t.addr; vif.drv_cb.arlen <= 8'd3;
  vif.drv_cb.arsize <= 3'd2; vif.drv_cb.arburst <= 2'b01; vif.drv_cb.arsnoop <= ace_arsnoop(c);
  vif.drv_cb.ardomain <= (c == C_RD_NOSNOOP) ? 2'b00 : 2'b01; vif.drv_cb.arbar <= 2'b00;
""" + "\n".join("  " + x for x in wait_cb("vif.drv_cb.arready === 1'b1", "ACE ARREADY").splitlines()) + """
  vif.drv_cb.arvalid <= 1'b0;
  vif.drv_cb.rready <= ($urandom_range(99) < cfg.ready_pct);
  while (!done && to < cfg.timeout_cycles) begin
    @(vif.drv_cb); to++;
    if (vif.drv_cb.rvalid === 1'b1 && vif.drv_cb.rready === 1'b1) begin
      line[beat[1:0]*32 +: 32] = vif.drv_cb.rdata; t.rresp = vif.drv_cb.rresp; beat++;
      done = vif.drv_cb.rlast;
    end
    vif.drv_cb.rready <= !done && ($urandom_range(99) < cfg.ready_pct);
  end
  if (!done) `uvm_error("TIMEOUT", "ACE: no RLAST")
  vif.drv_cb.rready <= 1'b0;
  vif.drv_cb.rack <= 1'b1;            // RACK in the clock after the last R transfer
  @(vif.drv_cb);
  vif.drv_cb.rack <= 1'b0;
  // new line state (a crossing snoop may have changed it since the decision)
  case (c)
    C_RD_SHARED: begin
      cst[l] = t.rresp[3] ? (t.rresp[2] ? ST_SD : ST_SC) : (t.rresp[2] ? ST_UD : ST_UC);
      cdat[l] = line;
    end
    C_RD_UNIQUE: begin cst[l] = t.rresp[2] ? ST_UD : ST_UC; cdat[l] = line; end
    C_CLEAN_UNIQUE: begin
      if (cst[l] == ST_SC) cst[l] = ST_UC;
      else if (cst[l] == ST_SD) cst[l] = ST_UD;
    end
    default: ;
  endcase
  // the store of ReadUnique / CleanUnique, once the line is unique
  if ((c == C_RD_UNIQUE || c == C_CLEAN_UNIQUE) && (cst[l] == ST_UC || cst[l] == ST_UD) && t.wstrb != 0) begin
    for (int b = 0; b < 4; b++) if (t.wstrb[b]) cdat[l][t.word*32 + b*8 +: 8] = t.wdata[b*8 +: 8];
    cst[l] = ST_UD;
  end
  t.rline = (c == C_CLEAN_UNIQUE) ? 128'h0 : line;
  t.word = 0; t.wdata = 0; t.wstrb = 0;
end else begin
  bit [127:0] wl = 0;
  bit [15:0] st = 0;
  if (c == C_WR_BACK) begin
    wb_busy = 1; wb_line = l;
    wl = cdat[l]; st = 16'hFFFF;
  end else begin
    wl[t.word*32 +: 32] = t.wdata; st[t.word*4 +: 4] = t.wstrb;
  end
  vif.drv_cb.awvalid <= 1'b1; vif.drv_cb.awaddr <= t.addr; vif.drv_cb.awlen <= 8'd3;
  vif.drv_cb.awsize <= 3'd2; vif.drv_cb.awburst <= 2'b01; vif.drv_cb.awsnoop <= ace_awsnoop(c);
  vif.drv_cb.awdomain <= (c == C_WR_NOSNOOP) ? 2'b00 : 2'b01; vif.drv_cb.awbar <= 2'b00;
""" + "\n".join("  " + x for x in wait_cb("vif.drv_cb.awready === 1'b1", "ACE AWREADY").splitlines()) + """
  vif.drv_cb.awvalid <= 1'b0;
  for (int b = 0; b < 4; b++) begin
    vif.drv_cb.wvalid <= 1'b1; vif.drv_cb.wdata <= wl[b*32 +: 32]; vif.drv_cb.wstrb <= st[b*4 +: 4];
    vif.drv_cb.wlast <= (b == 3);
""" + "\n".join("    " + x for x in wait_cb("vif.drv_cb.wready === 1'b1", "ACE WREADY").splitlines()) + """
  end
  vif.drv_cb.wvalid <= 1'b0; vif.drv_cb.wlast <= 1'b0;
  begin
    int unsigned to = 0;
    bit done = 0;
    vif.drv_cb.bready <= ($urandom_range(99) < cfg.ready_pct);
    while (!done && to < cfg.timeout_cycles) begin
      @(vif.drv_cb); to++;
      if (vif.drv_cb.bvalid === 1'b1 && vif.drv_cb.bready === 1'b1) begin done = 1; t.bresp = vif.drv_cb.bresp; end
      vif.drv_cb.bready <= !done && ($urandom_range(99) < cfg.ready_pct);
    end
    if (!done) `uvm_error("TIMEOUT", "ACE: no B response")
  end
  vif.drv_cb.bready <= 1'b0;
  vif.drv_cb.wack <= 1'b1;            // WACK in the clock after the B transfer
  @(vif.drv_cb);
  vif.drv_cb.wack <= 1'b0;
  if (c == C_WR_BACK) begin
    cst[l] = ST_I; wb_busy = 0;
    t.wline = wl; t.word = 0; t.wdata = 0; t.wstrb = 0;
  end
end
""",
    mon_desc="AR + R beats and AW + W beats + B rebuilt into transactions; AC + CR + CD into snoops",
    mon_members="""bit [35:0] ar_q[$], aw_q[$], ac_q[$];   // {cmd, addr}
bit [127:0] r_line, w_line, cd_line;
bit [15:0]  w_strb;
int unsigned r_beats = 0, w_beats = 0, cd_beats = 0;
bit cr_have = 0, cd_done = 0;
bit [4:0] cr_v;""",
    mon_run="""
forever begin
  @(vif.mon_cb);
  // ---- snoops: published once CR (and CD, with DataTransfer) are complete
  if (vif.mon_cb.acvalid && vif.mon_cb.acready) ac_q.push_back({ace_ac_cmd(vif.mon_cb.acsnoop), vif.mon_cb.acaddr});
  if (vif.mon_cb.crvalid && vif.mon_cb.crready) begin cr_have = 1; cr_v = vif.mon_cb.crresp; end
  if (vif.mon_cb.cdvalid && vif.mon_cb.cdready) begin
    cd_line[cd_beats[1:0]*32 +: 32] = vif.mon_cb.cddata; cd_beats++;
    if (vif.mon_cb.cdlast) begin
      cd_done = 1;
      if (cd_beats != 4) `uvm_error("MON", $sformatf("ACE: CD transfer of %0d beats, not a full line", cd_beats))
    end
  end
  if (cr_have && (!cr_v[0] || cd_done)) begin
    if (ac_q.size() == 0) `uvm_error("MON", "ACE: snoop response without an AC transfer")
    else begin
      ace_transaction t = ace_transaction::type_id::create("t");
      {t.cmd, t.addr} = ac_q.pop_front();
      t.crresp = cr_v; t.cdline = cr_v[0] ? cd_line : 128'h0;
      publish(t);
    end
    cr_have = 0; cd_done = 0; cd_beats = 0; cd_line = 0;
  end
  // ---- reads
  if (vif.mon_cb.arvalid && vif.mon_cb.arready) begin
    ar_q.push_back({ace_ar_cmd(vif.mon_cb.arsnoop, vif.mon_cb.ardomain), vif.mon_cb.araddr});
    if (vif.mon_cb.arlen != 8'd3 || vif.mon_cb.arsize != 3'd2)
      `uvm_error("MON", "ACE: read is not a full 16-byte line (ARLEN 3, ARSIZE 2)")
  end
  if (vif.mon_cb.rvalid && vif.mon_cb.rready) begin
    r_line[r_beats[1:0]*32 +: 32] = vif.mon_cb.rdata; r_beats++;
    if (vif.mon_cb.rlast) begin
      if (ar_q.size() == 0) `uvm_error("MON", "ACE: R transfer without an AR transfer")
      else begin
        ace_transaction t = ace_transaction::type_id::create("t");
        {t.cmd, t.addr} = ar_q.pop_front();
        if (r_beats != (t.cmd == C_CLEAN_UNIQUE ? 1 : 4))
          `uvm_error("MON", $sformatf("ACE: %0d R beats for command %0d", r_beats, t.cmd))
        t.rline = (t.cmd == C_CLEAN_UNIQUE) ? 128'h0 : r_line;
        t.rresp = vif.mon_cb.rresp;
        publish(t);
      end
      r_beats = 0; r_line = 0;
    end
  end
  // ---- writes: published at the B transfer
  if (vif.mon_cb.awvalid && vif.mon_cb.awready)
    aw_q.push_back({ace_aw_cmd(vif.mon_cb.awsnoop, vif.mon_cb.awdomain), vif.mon_cb.awaddr});
  if (vif.mon_cb.wvalid && vif.mon_cb.wready) begin
    w_line[w_beats[1:0]*32 +: 32] = vif.mon_cb.wdata; w_strb[w_beats[1:0]*4 +: 4] = vif.mon_cb.wstrb; w_beats++;
  end
  if (vif.mon_cb.bvalid && vif.mon_cb.bready) begin
    if (aw_q.size() == 0 || w_beats != 4) `uvm_error("MON", "ACE: B response without AW and four W beats")
    else begin
      ace_transaction t = ace_transaction::type_id::create("t");
      int n = 0;
      {t.cmd, t.addr} = aw_q.pop_front();
      t.bresp = vif.mon_cb.bresp;
      if (t.cmd == C_WR_BACK) begin
        t.wline = w_line;
        if (w_strb != 16'hFFFF) `uvm_error("MON", "ACE: WriteBack without every byte strobe")
      end else begin
        for (int b = 0; b < 4; b++) if (w_strb[b*4 +: 4] != 0) begin
          n++; t.word = b; t.wdata = w_line[b*32 +: 32]; t.wstrb = w_strb[b*4 +: 4];
        end
        if (n != 1) t.wline = w_line;   // the agent writes one word: anything else mismatches
      end
      publish(t);
    end
    w_beats = 0; w_line = 0; w_strb = 0;
  end
end
""",
    pair_skip="t.cmd >= C_SN_RD_ONCE && t.cmd <= C_SN_MAKE_INV",
    sb_members="""bit [127:0] mem [16], nsmem [16], pdat [16];
bit [1:0]   peer [16];   // 0 I, 1 SC, 2 UD
bit         init_done = 0;
function bit [127:0] merge(bit [127:0] base, bit [127:0] d, bit [15:0] st);
  for (int b = 0; b < 16; b++) if (st[b]) base[b*8 +: 8] = d[b*8 +: 8];
  return base;
endfunction""",
    predict="""
bit [3:0] l;
if (!init_done) begin
  for (int i = 0; i < 16; i++) begin mem[i] = ace_init_line(i); nsmem[i] = 0; pdat[i] = 0; peer[i] = 0; end
  init_done = 1;
end
l = t.addr[7:4];
case (t.cmd)
  C_RD_NOSNOOP: begin t.rline = nsmem[l]; t.rresp = 4'b0000; end
  C_RD_ONCE:    begin t.rline = peer[l] == 2 ? pdat[l] : mem[l]; t.rresp = {peer[l] != 0, 3'b000}; end
  C_RD_SHARED:  begin
    if (peer[l] == 2) begin t.rline = pdat[l]; t.rresp = 4'b1100; peer[l] = 1; end
    else begin t.rline = mem[l]; t.rresp = {peer[l] == 1, 3'b000}; end
  end
  C_RD_UNIQUE:  begin
    if (peer[l] == 2) begin t.rline = pdat[l]; t.rresp = 4'b0100; end
    else begin t.rline = mem[l]; t.rresp = 4'b0000; end
    peer[l] = 0;
  end
  C_CLEAN_UNIQUE: begin
    if (peer[l] == 2) mem[l] = pdat[l];
    peer[l] = 0; t.rline = 0; t.rresp = 4'b0000;
  end
  C_WR_NOSNOOP, C_WR_UNIQUE: begin
    bit [127:0] d = 0; bit [15:0] st = 0;
    d[t.word*32 +: 32] = t.wdata; st[t.word*4 +: 4] = t.wstrb;
    if (t.cmd == C_WR_NOSNOOP) nsmem[l] = merge(nsmem[l], d, st);
    else begin
      mem[l] = merge(peer[l] == 2 ? pdat[l] : mem[l], d, st);
      peer[l] = 0;
    end
    t.bresp = 2'b00;
  end
  C_WR_BACK: begin mem[l] = t.wline; t.bresp = 2'b00; end
  // snoops: the response came from the agent; apply it as the peer's transaction
  C_SN_RD_ONCE, C_SN_RD_SHARED, C_SN_CLEAN_INV: begin
    if (t.crresp[2]) mem[l] = t.cdline;
    if (t.cmd == C_SN_RD_SHARED && peer[l] == 0) peer[l] = 1;
    if (t.cmd == C_SN_CLEAN_INV) begin
      if (!t.crresp[2] && peer[l] == 2) mem[l] = pdat[l];
      peer[l] = 0;
    end
  end
  C_SN_RD_UNIQUE: begin pdat[l] = ace_inc_line(t.crresp[0] ? t.cdline : mem[l]); peer[l] = 2; end
  C_SN_MAKE_INV:  begin pdat[l] = ~mem[l]; peer[l] = 2; end
  default: ;
endcase
""",
    checks="""
bit snoop = t.cmd >= C_SN_RD_ONCE && t.cmd <= C_SN_MAKE_INV;
if (t.cmd == C_BAD) fail(t, "unsupported ARSNOOP / AWSNOOP / ACSNOOP encoding");
if (snoop) begin
  if (t.crresp[2] && !t.crresp[0]) fail(t, "CRRESP PassDirty without DataTransfer");
  if (t.crresp[1]) fail(t, "CRRESP Error");
  if (t.cmd == C_SN_MAKE_INV && t.crresp[0]) fail(t, "data transfer for MakeInvalid");
  if ((t.cmd == C_SN_RD_UNIQUE || t.cmd == C_SN_CLEAN_INV || t.cmd == C_SN_MAKE_INV) && t.crresp[3])
    fail(t, "IsShared after an invalidating snoop");
  if (t.cmd == C_SN_RD_ONCE && t.crresp[2]) fail(t, "PassDirty for a ReadOnce snoop (the line stays here)");
end else begin
  if (t.addr[3:0] != 0) fail(t, "address not line aligned");
  if (t.cmd <= C_CLEAN_UNIQUE && t.rresp[1:0] != 2'b00) fail(t, "read error response");
  if (t.cmd == C_RD_UNIQUE && t.rresp[3]) fail(t, "IsShared for ReadUnique");
  if (t.cmd == C_CLEAN_UNIQUE && t.rresp[3:2] != 2'b00) fail(t, "IsShared / PassDirty for CleanUnique");
  if ((t.cmd == C_RD_ONCE || t.cmd == C_RD_NOSNOOP) && t.rresp[2]) fail(t, "PassDirty for a non-caching read");
  if (t.cmd >= C_WR_NOSNOOP && t.cmd <= C_WR_BACK && t.bresp != 2'b00) fail(t, "write error response");
  if ((t.cmd == C_RD_NOSNOOP || t.cmd == C_WR_NOSNOOP) != t.addr[8]) fail(t, "shareability domain does not match the region");
end
""",
    coverage="""
cp_cmd    : coverpoint tr.cmd { bins rns = {C_RD_NOSNOOP}; bins ro = {C_RD_ONCE}; bins rs = {C_RD_SHARED};
                                bins ru = {C_RD_UNIQUE}; bins cu = {C_CLEAN_UNIQUE}; bins wns = {C_WR_NOSNOOP};
                                bins wu = {C_WR_UNIQUE}; bins wb = {C_WR_BACK}; bins s_ro = {C_SN_RD_ONCE};
                                bins s_rs = {C_SN_RD_SHARED}; bins s_ru = {C_SN_RD_UNIQUE};
                                bins s_ci = {C_SN_CLEAN_INV}; bins s_mi = {C_SN_MAKE_INV}; }
cp_rs     : coverpoint tr.rresp[3:2] iff (tr.cmd == C_RD_SHARED) { bins uc = {0}; bins sc = {2}; bins sd = {3}; }
cp_ru     : coverpoint tr.rresp[2] iff (tr.cmd == C_RD_UNIQUE);
cp_ro     : coverpoint tr.rresp[3] iff (tr.cmd == C_RD_ONCE);
cp_snoop  : coverpoint tr.cmd iff (tr.cmd >= C_SN_RD_ONCE && tr.cmd <= C_SN_MAKE_INV)
                       { bins ro = {C_SN_RD_ONCE}; bins rs = {C_SN_RD_SHARED}; bins ru = {C_SN_RD_UNIQUE};
                         bins ci = {C_SN_CLEAN_INV}; bins mi = {C_SN_MAKE_INV}; }
cp_cr     : coverpoint {tr.crresp[2], tr.crresp[0]} iff (tr.cmd >= C_SN_RD_ONCE && tr.cmd <= C_SN_MAKE_INV)
                       { bins none = {2'b00}; bins clean = {2'b01}; bins dirty = {2'b11}; }
cp_wasu   : coverpoint tr.crresp[4] iff (tr.cmd >= C_SN_RD_ONCE && tr.cmd <= C_SN_MAKE_INV);
// legal combinations only: no data for MakeInvalid, no dirty data for ReadOnce / ReadShared here
x_snoop_cr : cross cp_snoop, cp_cr {
  ignore_bins mi_data = binsof(cp_snoop.mi) && (binsof(cp_cr.clean) || binsof(cp_cr.dirty));
  ignore_bins ro_dirty = binsof(cp_snoop.ro) && binsof(cp_cr.dirty);
  ignore_bins rs_dirty = binsof(cp_snoop.rs) && binsof(cp_cr.dirty);
  ignore_bins ci_clean = binsof(cp_snoop.ci) && binsof(cp_cr.clean); }
""",
    directed="""
// line 0: ReadShared, store via CleanUnique / WriteBack; line 1: ReadUnique
// with a store, then a ReadShared request (dirty: becomes WriteBack); line 2:
// ReadOnce / WriteUnique; non-shareable region; then a mix on four lines
t = item(); t.cmd = C_RD_SHARED;    t.addr = 32'h00; send(t);
t = item(); t.cmd = C_CLEAN_UNIQUE; t.addr = 32'h00; t.word = 1; t.wdata = 32'h1111_2222; t.wstrb = 4'hF; send(t);
t = item(); t.cmd = C_WR_BACK;      t.addr = 32'h00; send(t);
t = item(); t.cmd = C_RD_ONCE;      t.addr = 32'h00; send(t);
t = item(); t.cmd = C_RD_UNIQUE;    t.addr = 32'h10; t.word = 3; t.wdata = 32'hAABB_CCDD; t.wstrb = 4'h6; send(t);
t = item(); t.cmd = C_RD_SHARED;    t.addr = 32'h10; send(t);
t = item(); t.cmd = C_RD_SHARED;    t.addr = 32'h10; send(t);
t = item(); t.cmd = C_RD_ONCE;      t.addr = 32'h20; send(t);
t = item(); t.cmd = C_WR_UNIQUE;    t.addr = 32'h20; t.word = 2; t.wdata = 32'h5555_6666; t.wstrb = 4'h9; send(t);
t = item(); t.cmd = C_RD_ONCE;      t.addr = 32'h20; send(t);
t = item(); t.cmd = C_WR_NOSNOOP;   t.addr = 32'h130; t.word = 0; t.wdata = 32'h0BAD_F00D; t.wstrb = 4'hF; send(t);
t = item(); t.cmd = C_RD_NOSNOOP;   t.addr = 32'h130; send(t);
for (int i = 0; i < 48; i++) begin
  t = item();
  t.cmd = (i % 5 == 0) ? C_RD_SHARED : (i % 5 == 1) ? C_CLEAN_UNIQUE : (i % 5 == 2) ? C_RD_UNIQUE :
          (i % 5 == 3) ? C_WR_BACK : C_RD_ONCE;
  t.addr = 32'h40 + 16 * (i % 4); t.word = i % 4; t.wdata = 32'h7000_0000 + i; t.wstrb = 4'hF;
  t.gap = i % 3; send(t);
end
""",
    drain_ns=6000,
    model="""
module ace_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        arvalid,
  output logic        arready,
  input  logic [31:0] araddr,
  input  logic [7:0]  arlen,
  input  logic [2:0]  arsize,
  input  logic [1:0]  arburst,
  input  logic [3:0]  arsnoop,
  input  logic [1:0]  ardomain,
  input  logic [1:0]  arbar,
  output logic        rvalid,
  input  logic        rready,
  output logic [31:0] rdata,
  output logic [3:0]  rresp,
  output logic        rlast,
  input  logic        rack,
  input  logic        awvalid,
  output logic        awready,
  input  logic [31:0] awaddr,
  input  logic [7:0]  awlen,
  input  logic [2:0]  awsize,
  input  logic [1:0]  awburst,
  input  logic [2:0]  awsnoop,
  input  logic [1:0]  awdomain,
  input  logic [1:0]  awbar,
  input  logic        wvalid,
  output logic        wready,
  input  logic [31:0] wdata,
  input  logic [3:0]  wstrb,
  input  logic        wlast,
  output logic        bvalid,
  input  logic        bready,
  output logic [1:0]  bresp,
  input  logic        wack,
  output logic        acvalid,
  input  logic        acready,
  output logic [31:0] acaddr,
  output logic [3:0]  acsnoop,
  output logic [2:0]  acprot,
  input  logic        crvalid,
  output logic        crready,
  input  logic [4:0]  crresp,
  input  logic        cdvalid,
  output logic        cdready,
  input  logic [31:0] cddata,
  input  logic        cdlast
);
  // commands (as in ace_defs_pkg)
  localparam [3:0] RNS = 4'd0, RO = 4'd1, RS = 4'd2, RU = 4'd3, CU = 4'd4, WNS = 4'd5, WU = 4'd6, WB = 4'd7,
                   SRO = 4'd8, SRS = 4'd9, SRU = 4'd10, SCI = 4'd11, SMI = 4'd12, BAD = 4'd15;
  localparam [1:0] P_I = 2'd0, P_SC = 2'd1, P_UD = 2'd2;

  logic [127:0] mem [0:15];
  logic [127:0] nsmem [0:15];
  logic [127:0] pdat [0:15];
  logic [1:0]   peer [0:15];
  logic [15:0]  lfsr;

  // master transaction: 0 idle, 1 read accepted, 2 read data, 3 write data, 4 write done, 5 B
  logic [2:0]   tx;
  logic [3:0]   t_cmd, t_line;
  logic [127:0] t_data, wbuf;
  logic [15:0]  wstb;
  logic [1:0]   t_beat;
  logic [3:0]   t_resp;
  logic [1:0]   t_bresp;
  logic [3:0]   acks;            // RLAST / B transfers not yet acknowledged
  // snoop: 0 idle, 1 AC, 2 waiting for CR / CD
  logic [1:0]   sn;
  logic [3:0]   s_op, s_line;
  logic         cr_got, cd_done;
  logic [4:0]   s_cr;
  logic [127:0] s_cd;
  logic [1:0]   s_cdb;
  logic [3:0]   rd_cmd, wr_cmd;

  always_comb begin
    if (ardomain == 2'b00 || ardomain == 2'b11) rd_cmd = (arsnoop == 4'b0000) ? RNS : BAD;
    else case (arsnoop)
      4'b0000: rd_cmd = RO;
      4'b0001: rd_cmd = RS;
      4'b0111: rd_cmd = RU;
      4'b1011: rd_cmd = CU;
      default: rd_cmd = BAD;
    endcase
    if (awdomain == 2'b00 || awdomain == 2'b11) wr_cmd = (awsnoop == 3'b000) ? WNS : BAD;
    else wr_cmd = (awsnoop == 3'b000) ? WU : (awsnoop == 3'b011) ? WB : BAD;
  end

  assign arready = (tx == 3'd0) && lfsr[0];
  assign awready = (tx == 3'd0) && !arvalid && lfsr[2];
  assign wready  = (tx == 3'd3) && lfsr[4];
  assign rvalid  = (tx == 3'd2);
  assign rdata   = t_data[t_beat*32 +: 32];
  assign rresp   = t_resp;
  assign rlast   = (tx == 3'd2) && (t_cmd == CU || t_beat == 2'd3);
  assign bvalid  = (tx == 3'd5);
  assign bresp   = t_bresp;
  assign acvalid = (sn == 2'd1);
  assign acaddr  = {24'h0, s_line, 4'h0};
  assign acsnoop = (s_op == SRS) ? 4'b0001 : (s_op == SRU) ? 4'b0111 : (s_op == SCI) ? 4'b1001 :
                   (s_op == SMI) ? 4'b1101 : 4'b0000;
  assign acprot  = 3'b000;
  assign crready = (sn == 2'd2) && !cr_got && lfsr[6];
  assign cdready = (sn == 2'd2) && !cd_done && lfsr[8];

  function automatic [127:0] merge(input [127:0] base, input [127:0] d, input [15:0] st);
    merge = base;
    for (int b = 0; b < 16; b++) if (st[b]) merge[b*8 +: 8] = d[b*8 +: 8];
  endfunction
  function automatic [127:0] inc_line(input [127:0] x);
    for (int w = 0; w < 4; w++) inc_line[w*32 +: 32] = x[w*32 +: 32] + 32'd1;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      lfsr <= 16'hACE1;
      tx <= 3'd0; t_cmd <= '0; t_line <= '0; t_data <= '0; wbuf <= '0; wstb <= '0; t_beat <= '0;
      t_resp <= '0; t_bresp <= '0; acks <= '0;
      sn <= 2'd0; s_op <= '0; s_line <= '0; cr_got <= 1'b0; cd_done <= 1'b0; s_cr <= '0; s_cd <= '0; s_cdb <= '0;
      for (int i = 0; i < 16; i++) begin
        for (int w = 0; w < 4; w++) mem[i][w*32 +: 32] <= {24'hC0FFEE, i[3:0], w[3:0]};
        nsmem[i] <= '0; pdat[i] <= '0; peer[i] <= P_I;
      end
    end else begin
      logic [3:0] a_inc, a_dec;
      a_inc = 0; a_dec = 0;
      lfsr <= {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};

      // ---------------- master transactions ----------------
      if (arvalid && arready) begin tx <= 3'd1; t_cmd <= rd_cmd; t_line <= araddr[7:4]; t_beat <= 2'd0; end
      else if (awvalid && awready) begin tx <= 3'd3; t_cmd <= wr_cmd; t_line <= awaddr[7:4]; t_beat <= 2'd0; wstb <= '0; end
      case (tx)
        3'd1: if (sn == 2'd0) begin          // a snoop in progress goes first
          tx <= 3'd2;
          case (t_cmd)
            RNS: begin t_data <= nsmem[t_line]; t_resp <= 4'b0000; end
            RO:  begin t_data <= (peer[t_line] == P_UD) ? pdat[t_line] : mem[t_line];
                       t_resp <= {peer[t_line] != P_I, 3'b000}; end
            RS:  if (peer[t_line] == P_UD) begin t_data <= pdat[t_line]; t_resp <= 4'b1100; peer[t_line] <= P_SC; end
                 else begin t_data <= mem[t_line]; t_resp <= {peer[t_line] == P_SC, 3'b000}; end
            RU:  begin
                   if (peer[t_line] == P_UD) begin t_data <= pdat[t_line]; t_resp <= 4'b0100; end
                   else begin t_data <= mem[t_line]; t_resp <= 4'b0000; end
                   peer[t_line] <= P_I;
                 end
            CU:  begin
                   if (peer[t_line] == P_UD) mem[t_line] <= pdat[t_line];
                   peer[t_line] <= P_I; t_data <= '0; t_resp <= 4'b0000;
                 end
            default: begin t_data <= '0; t_resp <= 4'b0010; end   // SLVERR
          endcase
        end
        3'd2: if (rready) begin
          if (rlast) begin tx <= 3'd0; a_inc = a_inc + 1; end
          else t_beat <= t_beat + 2'd1;
        end
        3'd3: if (wvalid && wready) begin
          wbuf[t_beat*32 +: 32] <= wdata; wstb[t_beat*4 +: 4] <= wstrb; t_beat <= t_beat + 2'd1;
          if (wlast) tx <= 3'd4;
        end
        3'd4: if (t_cmd == WB || sn == 2'd0) begin   // a WriteBack does not wait for a snoop
          tx <= 3'd5; t_bresp <= 2'b00;
          case (t_cmd)
            WNS: nsmem[t_line] <= merge(nsmem[t_line], wbuf, wstb);
            WU:  begin mem[t_line] <= merge((peer[t_line] == P_UD) ? pdat[t_line] : mem[t_line], wbuf, wstb);
                       peer[t_line] <= P_I; end
            WB:  mem[t_line] <= merge(mem[t_line], wbuf, wstb);
            default: t_bresp <= 2'b10;
          endcase
        end
        3'd5: if (bready) begin tx <= 3'd0; a_inc = a_inc + 1; end
        default: ;
      endcase
      if (rack) a_dec = a_dec + 1;
      if (wack) a_dec = a_dec + 1;
      acks <= acks + a_inc - a_dec;

      // ---------------- snoops from the peer ----------------
      case (sn)
        2'd0: if (tx == 3'd0 && acks == 4'd0 && lfsr[7:4] == 4'h0) begin
          logic [3:0] o, l;
          l = lfsr[11:8];
          case (lfsr[14:12])
            3'd0, 3'd7: o = SRO;
            3'd1, 3'd5: o = SRS;
            3'd2, 3'd6: o = SRU;
            3'd3:       o = SCI;
            default:    o = SMI;
          endcase
          if (peer[l] == P_UD && (o == SRS || o == SRU || o == SMI)) o = SCI;   // it already owns the line
          if (peer[l] == P_SC && o == SRS) o = SRO;
          sn <= 2'd1; s_op <= o; s_line <= l;
        end
        2'd1: if (acready) begin sn <= 2'd2; cr_got <= 1'b0; cd_done <= 1'b0; s_cdb <= 2'd0; end
        2'd2: begin
          if (crvalid && crready) begin cr_got <= 1'b1; s_cr <= crresp; end
          if (cdvalid && cdready) begin
            s_cd[s_cdb*32 +: 32] <= cddata; s_cdb <= s_cdb + 2'd1;
            if (cdlast) cd_done <= 1'b1;
          end
          if (cr_got && (!s_cr[0] || cd_done)) begin
            sn <= 2'd0;
            case (s_op)
              SRO: if (s_cr[2]) mem[s_line] <= s_cd;
              SRS: begin
                     if (s_cr[2]) mem[s_line] <= s_cd;
                     if (peer[s_line] == P_I) peer[s_line] <= P_SC;
                   end
              SRU: begin pdat[s_line] <= inc_line(s_cr[0] ? s_cd : mem[s_line]); peer[s_line] <= P_UD; end
              SCI: begin
                     if (s_cr[2]) mem[s_line] <= s_cd;
                     else if (peer[s_line] == P_UD) mem[s_line] <= pdat[s_line];
                     peer[s_line] <= P_I;
                   end
              default: begin pdat[s_line] <= ~mem[s_line]; peer[s_line] <= P_UD; end   // MakeInvalid
            endcase
          end
        end
        default: sn <= 2'd0;
      endcase
    end
  end
endmodule
""",
    sva="""
// transfers counted for the RACK / WACK and response rules
int unsigned n_rl = 0, n_rack = 0, n_b = 0, n_wack = 0, n_ar = 0;
logic [31:0] last_rd;
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) begin n_rl <= 0; n_rack <= 0; n_b <= 0; n_wack <= 0; n_ar <= 0; last_rd <= '0; end
  else begin
    if (arvalid && arready) begin n_ar <= n_ar + 1; last_rd <= araddr; end
    if (rvalid && rready && rlast) n_rl <= n_rl + 1;
    if (rack) n_rack <= n_rack + 1;
    if (bvalid && bready) n_b <= n_b + 1;
    if (wack) n_wack <= n_wack + 1;
  end
assert property (@(posedge clk) !rst_n |-> !rvalid && !bvalid && !acvalid)
  else $error("ACE: VALID high in reset");
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({arready, awready, wready, rvalid, bvalid, acvalid, crready, cdready}))
  else $error("ACE: X on a handshake signal");
// VALID held and payload stable until READY on every channel
assert property (@(posedge clk) disable iff (!rst_n) arvalid && !arready |=> arvalid && $stable({araddr, arlen, arsize, arburst, arsnoop, ardomain, arbar}))
  else $error("ACE: AR changed before ARREADY");
assert property (@(posedge clk) disable iff (!rst_n) awvalid && !awready |=> awvalid && $stable({awaddr, awlen, awsize, awburst, awsnoop, awdomain, awbar}))
  else $error("ACE: AW changed before AWREADY");
assert property (@(posedge clk) disable iff (!rst_n) wvalid && !wready |=> wvalid && $stable({wdata, wstrb, wlast}))
  else $error("ACE: W changed before WREADY");
assert property (@(posedge clk) disable iff (!rst_n) rvalid && !rready |=> rvalid && $stable({rdata, rresp, rlast}))
  else $error("ACE: R changed before RREADY");
assert property (@(posedge clk) disable iff (!rst_n) bvalid && !bready |=> bvalid && $stable(bresp))
  else $error("ACE: B changed before BREADY");
assert property (@(posedge clk) disable iff (!rst_n) acvalid && !acready |=> acvalid && $stable({acaddr, acsnoop, acprot}))
  else $error("ACE: AC changed before ACREADY");
assert property (@(posedge clk) disable iff (!rst_n) crvalid && !crready |=> crvalid && $stable(crresp))
  else $error("ACE: CR changed before CRREADY");
assert property (@(posedge clk) disable iff (!rst_n) cdvalid && !cdready |=> cdvalid && $stable({cddata, cdlast}))
  else $error("ACE: CD changed before CDREADY");
// RACK / WACK only acknowledge completed transfers; CR: PassDirty needs DataTransfer
assert property (@(posedge clk) disable iff (!rst_n) rack |-> n_rl > n_rack)
  else $error("ACE: RACK without an unacknowledged RLAST transfer");
assert property (@(posedge clk) disable iff (!rst_n) wack |-> n_b > n_wack)
  else $error("ACE: WACK without an unacknowledged B transfer");
assert property (@(posedge clk) disable iff (!rst_n) crvalid |-> !(crresp[2] && !crresp[0]))
  else $error("ACE: CRRESP PassDirty without DataTransfer");
// no snoop to a line between its read response and RACK
assert property (@(posedge clk) disable iff (!rst_n) $rose(acvalid) |-> !(n_rl > n_rack && acaddr[31:4] == last_rd[31:4]))
  else $error("ACE: snoop to a line whose read is not yet acknowledged");
// ARBAR / AWBAR: no barriers on this interface
assert property (@(posedge clk) disable iff (!rst_n) (arvalid |-> arbar == 2'b00) and (awvalid |-> awbar == 2'b00))
  else $error("ACE: barrier transaction");
cover property (@(posedge clk) disable iff (!rst_n) acvalid && acready && acsnoop == 4'b0111);
cover property (@(posedge clk) disable iff (!rst_n) crvalid && crready && crresp[2]);
cover property (@(posedge clk) disable iff (!rst_n) rvalid && rready && rlast && rresp[3:2] == 2'b11);
cover property (@(posedge clk) disable iff (!rst_n) acvalid && (arvalid || awvalid));
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic arvalid = 0, rready = 1, rack = 0, awvalid = 0, wvalid = 0, wlast = 0, bready = 1, wack = 0;
logic acready = 0, crvalid = 0, cdvalid = 0, cdlast = 0;
logic [31:0] araddr = 0, awaddr = 0, wdata = 0, cddata = 0;
logic [3:0] arsnoop = 0, wstrb = 0;
logic [2:0] awsnoop = 0;
logic [1:0] ardomain = 0, awdomain = 0;
logic [4:0] crresp = 0;
wire arready, rvalid, rlast, awready, wready, bvalid, acvalid, crready, cdready;
wire [31:0] rdata, acaddr;
wire [3:0] rresp, acsnoop;
wire [1:0] bresp;
wire [2:0] acprot;

always #5 clk = ~clk;

ace_model u_dut (.clk(clk), .rst_n(rst_n), .arvalid(arvalid), .arready(arready), .araddr(araddr),
                 .arlen(8'd3), .arsize(3'd2), .arburst(2'b01), .arsnoop(arsnoop), .ardomain(ardomain),
                 .arbar(2'b00), .rvalid(rvalid), .rready(rready), .rdata(rdata), .rresp(rresp), .rlast(rlast),
                 .rack(rack), .awvalid(awvalid), .awready(awready), .awaddr(awaddr), .awlen(8'd3),
                 .awsize(3'd2), .awburst(2'b01), .awsnoop(awsnoop), .awdomain(awdomain), .awbar(2'b00),
                 .wvalid(wvalid), .wready(wready), .wdata(wdata), .wstrb(wstrb), .wlast(wlast),
                 .bvalid(bvalid), .bready(bready), .bresp(bresp), .wack(wack), .acvalid(acvalid),
                 .acready(acready), .acaddr(acaddr), .acsnoop(acsnoop), .acprot(acprot), .crvalid(crvalid),
                 .crready(crready), .crresp(crresp), .cdvalid(cdvalid), .cdready(cdready), .cddata(cddata),
                 .cdlast(cdlast));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// ---- reference: memory, non-shareable memory, the peer (0 I, 1 SC, 2 UD)
logic [127:0] m_mem [16], m_ns [16], m_pd [16];
logic [1:0]   m_peer [16];
function automatic [127:0] inc_line(input [127:0] x);
  for (int w = 0; w < 4; w++) inc_line[w*32 +: 32] = x[w*32 +: 32] + 32'd1;
endfunction

// ---- snoop responder: no line is cached here unless dirty_mode, then
// every snoop except MakeInvalid is answered with PassDirty data cd_val
bit dirty_mode = 0;
bit wb_busy = 0;      // a WriteBack is in progress: snoops are answered after it
logic [127:0] cd_val = 0;
int n_snoop [16];
int ac_while_ack = 0;
int bad_sel = 0;      // a snoop the peer would not start for its line state
bit late = 0;
int n_late = 0;
initial forever begin
  logic [3:0] op_code, l;
  logic [4:0] r;
  @(negedge clk);
  if (acvalid) begin
    op_code = acsnoop; l = acaddr[7:4];
    acready = 1;
    @(negedge clk);
    acready = 0;
    while (wb_busy) @(negedge clk);
    n_snoop[op_code]++;
    if (late) n_late++;
    if (m_peer[l] == 2 && (op_code == 4'b0001 || op_code == 4'b0111 || op_code == 4'b1101)) bad_sel++;
    if (m_peer[l] == 1 && op_code == 4'b0001) bad_sel++;
    r = (dirty_mode && op_code != 4'b1101) ? 5'b00101 : 5'b00000;
    // the reference applies the snoop now: transactions the model accepts
    // from here on are answered after it
    case (op_code)
      4'b0000: if (r[2]) m_mem[l] = cd_val;
      4'b0001: begin if (r[2]) m_mem[l] = cd_val; if (m_peer[l] == 0) m_peer[l] = 1; end
      4'b0111: begin m_pd[l] = inc_line(r[0] ? cd_val : m_mem[l]); m_peer[l] = 2; end
      4'b1001: begin
                 if (r[2]) m_mem[l] = cd_val; else if (m_peer[l] == 2) m_mem[l] = m_pd[l];
                 m_peer[l] = 0;
               end
      default: begin m_pd[l] = ~m_mem[l]; m_peer[l] = 2; end
    endcase
    crvalid = 1; crresp = r;
    @(posedge clk);
    while (!crready) @(posedge clk);
    @(negedge clk);
    crvalid = 0;
    if (r[0]) for (int b = 0; b < 4; b++) begin
      cdvalid = 1; cddata = cd_val[b*32 +: 32]; cdlast = (b == 3);
      @(posedge clk);
      while (!cdready) @(posedge clk);
      @(negedge clk);
    end
    cdvalid = 0; cdlast = 0;
  end
end

// read: cmd 0 ReadNoSnoop, 1 ReadOnce, 2 ReadShared, 3 ReadUnique, 4 CleanUnique
int beats;
task automatic rd(input int cmd, input logic [31:0] a, input int ack_delay,
                  output logic [127:0] q, output logic [3:0] r);
  int n;
  @(negedge clk);
  arvalid = 1; araddr = a;
  ardomain = (cmd == 0) ? 2'b00 : 2'b01;
  arsnoop = (cmd == 2) ? 4'b0001 : (cmd == 3) ? 4'b0111 : (cmd == 4) ? 4'b1011 : (cmd == 9) ? 4'b0101 : 4'b0000;
  n = 0;
  @(posedge clk);
  while (!arready && n < 100) begin @(posedge clk); n++; end
  @(negedge clk);
  arvalid = 0;
  q = 0; beats = 0; n = 0;
  forever begin
    @(posedge clk);
    if (rvalid && rready) begin
      q[beats[1:0]*32 +: 32] = rdata; r = rresp; beats++;
      if (rlast) break;
    end
    n++;
    if (n > 200) break;
  end
  @(negedge clk);
  repeat (ack_delay) begin @(negedge clk); if (acvalid) ac_while_ack++; end
  rack = 1;
  @(negedge clk);
  rack = 0;
endtask

// write: cmd 5 WriteNoSnoop, 6 WriteUnique, 7 WriteBack
task automatic wr(input int cmd, input logic [31:0] a, input logic [127:0] d, input logic [15:0] st,
                  output logic [1:0] r);
  int n;
  @(negedge clk);
  awvalid = 1; awaddr = a;
  awdomain = (cmd == 5) ? 2'b00 : 2'b01;
  awsnoop = (cmd == 7) ? 3'b011 : (cmd == 9) ? 3'b110 : 3'b000;
  @(posedge clk);
  n = 0;
  while (!awready && n < 100) begin @(posedge clk); n++; end
  @(negedge clk);
  awvalid = 0;
  for (int b = 0; b < 4; b++) begin
    wvalid = 1; wdata = d[b*32 +: 32]; wstrb = st[b*4 +: 4]; wlast = (b == 3);
    @(posedge clk);
    while (!wready) @(posedge clk);
    @(negedge clk);
  end
  wvalid = 0; wlast = 0;
  @(posedge clk);
  while (!bvalid) @(posedge clk);
  r = bresp;
  @(negedge clk);
  wack = 1;
  @(negedge clk);
  wack = 0;
endtask

function automatic [127:0] merge(input [127:0] base, input [127:0] d, input [15:0] st);
  merge = base;
  for (int b = 0; b < 16; b++) if (st[b]) merge[b*8 +: 8] = d[b*8 +: 8];
endfunction

initial begin
  logic [127:0] q, e, d;
  logic [3:0] r, er;
  logic [1:0] br;
  int bad_d, bad_r, bad_n, n_ops;
  for (int i = 0; i < 16; i++) begin
    for (int w = 0; w < 4; w++) m_mem[i][w*32 +: 32] = {24'hC0FFEE, i[3:0], w[3:0]};
    m_ns[i] = 0; m_pd[i] = 0; m_peer[i] = 0; n_snoop[i] = 0;
  end
  repeat (3) @(posedge clk);
  chk(rvalid === 1'b0 && bvalid === 1'b0 && acvalid === 1'b0, "R / B / AC idle in reset");
  rst_n = 1;
  repeat (2) @(posedge clk);

  // non-shareable region: its own memory, not snooped
  rd(0, 32'h150, 0, q, r);
  chk(q === 0 && r === 4'b0000 && beats == 4, "ReadNoSnoop: four beats of 0");
  wr(5, 32'h150, 128'h4444_3333_2222_1111_0000_0000_0000_FFFF, 16'hF0F3, br);
  chk(br === 2'b00, "WriteNoSnoop: OKAY");
  rd(0, 32'h150, 0, q, r);
  chk(q === 128'h4444_3333_0000_0000_0000_0000_0000_FFFF, "WriteNoSnoop byte strobes merged");
  rd(1, 32'h050, 0, q, r);
  chk(q === ((m_peer[5] == 2) ? m_pd[5] : m_mem[5]), "ReadOnce of line 5 returns its current contents");

  // unsupported encodings answer SLVERR
  rd(9, 32'h010, 0, q, r);
  chk(r[1:0] === 2'b10 && q === 0, "unsupported ARSNOOP: SLVERR, no data");
  wr(9, 32'h010, '1, '1, br);
  chk(br === 2'b10, "unsupported AWSNOOP: SLVERR");

  // random coherent traffic against the reference, peer snoops in between
  bad_d = 0; bad_r = 0; bad_n = 0; n_ops = 0;
  for (int i = 0; i < 400; i++) begin
    int cmd, l;
    logic [31:0] x;
    x = $urandom;
    l = x[3:0];
    cmd = 1 + x[10:8] % 7;               // 1..7
    if (i == 150) begin dirty_mode = 1; cd_val = {4{32'hD1D1_0000 | i}}; end
    if (i == 200) dirty_mode = 0;
    if (i == 300) late = 1;
    if (cmd <= 4) begin
      rd(cmd, {l, 4'h0}, x[13:12], q, r);
      // the reference after any snoop the model ordered first
      case (cmd)
        1: begin e = (m_peer[l] == 2) ? m_pd[l] : m_mem[l]; er = {m_peer[l] != 0, 3'b000}; end
        2: if (m_peer[l] == 2) begin e = m_pd[l]; er = 4'b1100; m_peer[l] = 1; end
           else begin e = m_mem[l]; er = {m_peer[l] == 1, 3'b000}; end
        3: begin e = (m_peer[l] == 2) ? m_pd[l] : m_mem[l]; er = {1'b0, m_peer[l] == 2, 2'b00}; m_peer[l] = 0; end
        default: begin if (m_peer[l] == 2) m_mem[l] = m_pd[l]; m_peer[l] = 0; e = 0; er = 0; end
      endcase
      if (cmd != 4 && q !== e) begin bad_d++; if (bad_d < 4) $display("  op %0d line %0d: %h exp %h", cmd, l, q, e); end
      if (r !== er) begin bad_r++; if (bad_r < 4) $display("  op %0d line %0d: rresp %b exp %b", cmd, l, r, er); end
      if (beats != (cmd == 4 ? 1 : 4)) bad_n++;
    end else begin
      d = {$urandom, $urandom, $urandom, $urandom};
      if (cmd == 7) begin
        wb_busy = 1;
        wr(7, {l, 4'h0}, d, 16'hFFFF, br);
        m_mem[l] = d;
        wb_busy = 0;
      end else begin
        logic [15:0] st;
        st = {$urandom} | 16'h1;
        wr(6, {l, 4'h0}, d, st, br);
        m_mem[l] = merge((m_peer[l] == 2) ? m_pd[l] : m_mem[l], d, st);
        m_peer[l] = 0;
      end
      if (br !== 2'b00) bad_r++;
    end
    n_ops++;
  end
  chk(bad_d == 0, $sformatf("read data matches the reference (%0d of %0d wrong)", bad_d, n_ops));
  chk(bad_r == 0, $sformatf("RRESP IsShared / PassDirty and BRESP match the reference (%0d wrong)", bad_r));
  chk(bad_n == 0, "four R beats per read, one for CleanUnique");
  chk(n_snoop[0] > 0 && n_snoop[1] > 0 && n_snoop[7] > 0 && n_snoop[9] > 0 && n_snoop[13] > 0,
      $sformatf("snoops seen: ReadOnce %0d ReadShared %0d ReadUnique %0d CleanInvalid %0d MakeInvalid %0d",
                n_snoop[0], n_snoop[1], n_snoop[7], n_snoop[9], n_snoop[13]));
  chk(ac_while_ack == 0, "no snoop while a RACK is owed");
  chk(n_late > 0, $sformatf("snoops still start late in the run (%0d in the last 100 transactions)", n_late));
  chk(bad_sel == 0, "the peer snoops only with commands its line state allows (no ReadShared / ReadUnique / MakeInvalid for a line it owns dirty, no ReadShared for one it shares)");

  // one transaction at a time: no AR while a write is in progress, no AW
  // while a read is (the requests are withdrawn again: test stimulus only)
  begin
    int acc;
    acc = 0;
    @(negedge clk);
    awvalid = 1; awaddr = 32'h0E0; awdomain = 2'b01; awsnoop = 3'b000;
    @(posedge clk);
    while (!awready) @(posedge clk);
    @(negedge clk);
    awvalid = 0;
    arvalid = 1; araddr = 32'h0F0; ardomain = 2'b01; arsnoop = 4'b0000;
    repeat (8) begin @(posedge clk); if (arready) acc++; @(negedge clk); end
    arvalid = 0;
    chk(acc == 0, "ARREADY low while a write waits for its data");
    for (int b = 0; b < 4; b++) begin
      wvalid = 1; wdata = 32'h0E0E_0000 + b; wstrb = 4'hF; wlast = (b == 3);
      @(posedge clk);
      while (!wready) @(posedge clk);
      @(negedge clk);
    end
    wvalid = 0; wlast = 0;
    m_mem[14] = merge((m_peer[14] == 2) ? m_pd[14] : m_mem[14], 128'h0E0E0003_0E0E0002_0E0E0001_0E0E0000, 16'hFFFF);
    m_peer[14] = 0;
    @(posedge clk);
    while (!bvalid) @(posedge clk);
    @(negedge clk);
    wack = 1; @(negedge clk); wack = 0;
    acc = 0;
    rready = 0;
    arvalid = 1; araddr = 32'h0E0; ardomain = 2'b01; arsnoop = 4'b0000;
    @(posedge clk);
    while (!arready) @(posedge clk);
    @(negedge clk);
    arvalid = 0;
    awvalid = 1; awaddr = 32'h0F0; awsnoop = 3'b000; awdomain = 2'b01;
    repeat (8) begin @(posedge clk); if (awready) acc++; @(negedge clk); end
    awvalid = 0;
    chk(acc == 0, "AWREADY low while a read waits for RREADY");
    rready = 1;
    q = 0; beats = 0;
    forever begin
      @(posedge clk);
      if (rvalid && rready) begin q[beats[1:0]*32 +: 32] = rdata; beats++; if (rlast) break; end
    end
    @(negedge clk);
    rack = 1; @(negedge clk); rack = 0;
    chk(q === ((m_peer[14] == 2) ? m_pd[14] : m_mem[14]), "the WriteUnique of line 14 read back");
  end
  chk(acprot === 3'b000, "ACPROT 0");

  // the final memory contents, line by line through ReadOnce
  begin
    int bad;
    bad = 0;
    repeat (40) @(negedge clk);
    for (int l = 0; l < 16; l++) begin
      rd(1, {l[3:0], 4'h0}, 0, q, r);
      if (q !== ((m_peer[l] == 2) ? m_pd[l] : m_mem[l])) bad++;
    end
    chk(bad == 0, $sformatf("all 16 lines match the reference at the end (%0d wrong)", bad));
  end

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #3000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
