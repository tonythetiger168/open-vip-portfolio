# DFI 5.0 (DDR PHY Interface) agent on the memory-controller side, frequency
# ratio 1:1, one rank, DDR4-style command encoding:
#   ACT: cs_n=0 act_n=0, row on address        RD: ras_n cas_n we_n = 1 0 1
#   WR: 1 0 0      PRE: 0 1 0 (address[10] = 1: all banks)      REF: 0 0 1
#   RD / WR: column on address[9:0], address[10] = auto-precharge
# Write data: dfi_wrdata_en for DFI_BL cycles, starting DFI_TPHY_WRLAT cycles
# after WR; dfi_wrdata / dfi_wrdata_mask DFI_TPHY_WRDATA (1) cycle after each
# enable cycle. Read data: dfi_rddata_en for DFI_BL cycles starting
# DFI_TRDDATA_EN cycles after RD; the PHY returns dfi_rddata_valid +
# dfi_rddata a fixed number of cycles later.
# Handshakes: dfi_init_start / dfi_init_complete (also a frequency change,
# dfi_frequency), dfi_ctrlupd_req / ack (MC-initiated, tctrlupd_min..max
# cycles), dfi_phyupd_req / ack (PHY-initiated; the testbench input
# tb_phyupd stands for the PHY's own need), dfi_lp_ctrl_req / dfi_lp_ack with
# dfi_lp_wakeup. The controller must not issue commands before init
# completes or while a ctrlupd / phyupd / lp ack is high.
#
# tb/top_tb.sv dfi_model: PHY + DRAM. It tracks open banks and rows, checks
# tRCD / tRP / tRAS / tRFC, bank state, the data-enable windows and the
# handshakes, flags the first error of a cycle on dfi_error with a code on
# dfi_error_info (1 timing, 2 bank state, 3 wrdata_en, 4 rddata_en,
# 5 command while busy, 6 handshake), drops a command in error, stores write
# data with byte masks and returns read data. Its memory holds 8 rows x 64
# columns per bank: higher row and column bits are ignored (the reference
# model does the same). One write and one read burst may be outstanding.

DEFS = """
localparam int DFI_BL           = 4;    // data cycles per RD / WR (BL8)
localparam int DFI_TPHY_WRLAT   = 3;    // WR to dfi_wrdata_en
localparam int DFI_TPHY_WRDATA  = 1;    // dfi_wrdata_en to dfi_wrdata
localparam int DFI_TRDDATA_EN   = 3;    // RD to dfi_rddata_en
localparam int DFI_TRCD = 4, DFI_TRP = 4, DFI_TRAS = 8, DFI_TRFC = 12;
localparam int DFI_TINIT        = 10;   // dfi_init_start to dfi_init_complete
localparam int DFI_TCTRLUPD_MIN = 4, DFI_TCTRLUPD_MAX = 24;
localparam int DFI_TPHYUPD_RESP = 12;   // the controller must ack a PHY update within this
localparam int DFI_TLP_RESP     = 3;

typedef enum bit [3:0] {K_INIT, K_ACT, K_RD, K_WR, K_PRE, K_PREA, K_REF, K_CTRLUPD, K_PHYUPD, K_LP} dfi_kind_e;

// dfi_error_info codes
localparam bit [2:0] DFI_E_TIMING = 3'd1, DFI_E_BANK = 3'd2, DFI_E_WRDATA = 3'd3,
                     DFI_E_RDDATA = 3'd4, DFI_E_BUSY = 3'd5, DFI_E_HSHAKE = 3'd6;

// DUT model memory index: bank, row[2:0], column[5:0]
function automatic bit [11:0] dfi_idx(bit [2:0] b, bit [13:0] r, bit [9:0] c);
  return {b, r[2:0], c[5:0]};
endfunction

function automatic bit [11:0] dfi_beat(bit [11:0] base, int unsigned k);
  bit [5:0] c = base[5:0] + k;
  return {base[11:6], c};
endfunction

function automatic bit [31:0] dfi_merge(bit [31:0] old, bit [31:0] d, bit [3:0] m);
  for (int i = 0; i < 4; i++) if (!m[i]) old[8*i +: 8] = d[8*i +: 8];
  return old;
endfunction
"""

SPEC = dict(
    vip="DFI-VIP", p="dfi", P="DFI", dir="dfi", family="Memory",
    desc="DFI 5.0 (DDR PHY Interface) VIP on the memory-controller side: DDR4-style command channel, "
         "dfi_wrdata_en / dfi_rddata_en timing (tphy_wrlat, tphy_wrdata, trddata_en), byte masks, "
         "init and frequency change, controller update, PHY update and low-power handshakes, with a PHY + DRAM "
         "model that checks tRCD / tRP / tRAS / tRFC and bank state.",
    about="""
DFI is the interface between a DDR memory controller and its PHY. The agent
plays the controller: it issues ACT / RD / WR / PRE / PREA / REF (with
auto-precharge), drives the write-data enable and data with byte masks,
drives the read-data enable and collects the returned data, and runs the
init / frequency change, ctrlupd, phyupd and lp handshakes. Each item can be
off-spec on purpose (a command inside tRCD / tRP / tRAS / tRFC, a closed or
open bank, a data enable one cycle early or late or a beat short or long, a
controller update outside tctrlupd_min..max, a late or early-dropped PHY
update acknowledge, a command while an update or low-power ack is high).
The monitor rebuilds items from the pins with its own cycle count; the
scoreboard's reference model predicts every error code, the read data and
the handshake responses.

The model runs at a 1:1 frequency ratio with one rank and fixed timing
parameters (`DFI_*` in `dfi_defs.sv`); its memory keeps 8 rows x 64 columns
per bank.""",
    defs=DEFS,
    timeout=200,
    ports=[
        ("in", "logic", "init_start"), ("in", "logic [4:0]", "frequency"), ("in", "logic", "cke"),
        ("in", "logic", "cs_n"), ("in", "logic", "act_n"), ("in", "logic", "ras_n"), ("in", "logic", "cas_n"),
        ("in", "logic", "we_n"), ("in", "logic [2:0]", "bank"), ("in", "logic [13:0]", "address"),
        ("in", "logic", "wrdata_en"), ("in", "logic [31:0]", "wrdata"), ("in", "logic [3:0]", "wrdata_mask"),
        ("in", "logic", "rddata_en"), ("in", "logic", "ctrlupd_req"), ("in", "logic", "phyupd_ack"),
        ("in", "logic", "lp_ctrl_req"), ("in", "logic [3:0]", "lp_wakeup"), ("in", "logic", "tb_phyupd"),
        ("out", "logic", "init_complete"), ("out", "logic [4:0]", "freq"), ("out", "logic [31:0]", "rddata"),
        ("out", "logic", "rddata_valid"), ("out", "logic", "ctrlupd_ack"), ("out", "logic", "phyupd_req"),
        ("out", "logic [1:0]", "phyupd_type"), ("out", "logic", "lp_ack"), ("out", "logic", "error"),
        ("out", "logic [2:0]", "error_info"),
    ],
    cfg="int unsigned tail_cycles = 8;   // idle cycles after the last data beat of a RD / WR",
    fields=[
        ("dfi_kind_e", "kind", "req"),
        ("bit [2:0]", "bank", "req"),
        ("bit [13:0]", "row", "req"),       # ACT
        ("bit [9:0]", "col", "req"),        # RD / WR
        ("bit", "ap", "req"),               # RD / WR auto-precharge
        ("bit [3:0]", "lat", "req"),        # RD / WR: command to first data enable
        ("bit [3:0]", "beats", "req"),      # RD / WR: data enable cycles
        ("bit [31:0]", "wdata", "req", "q"),
        ("bit [3:0]", "wmask", "req", "q"),
        ("bit [4:0]", "fsel", "req"),       # INIT: dfi_frequency
        ("bit [5:0]", "len", "req"),        # CTRLUPD / LP: request cycles
        ("bit [3:0]", "wakeup", "req"),     # LP
        ("bit [4:0]", "resp", "req"),       # PHYUPD: cycles before the ack
        ("bit", "early", "req"),            # PHYUPD: drop the ack during the update
        ("bit", "intrude", "req"),          # CTRLUPD / LP: a REF while acked
        ("bit [7:0]", "err", "rsp"),        # bit k: error code k seen
        ("bit [31:0]", "rdata", "rsp", "q"),
        ("bit", "acked", "rsp"),            # init complete / ctrlupd / lp ack seen
        ("bit [1:0]", "ptype", "rsp"),      # PHYUPD: dfi_phyupd_type
        ("bit [4:0]", "freq_o", "rsp"),     # INIT: frequency after the init
        ("bit [5:0]", "lat_o", "rsp"),      # INIT: start to complete; LP: request end to ack end
        ("bit [3:0]", "gap", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
        ("int unsigned", "cyc", "info"),    # monitor: cycle of the command / start
    ],
    constraints="""
constraint c_kind { kind dist { K_ACT := 5, K_RD := 4, K_WR := 4, K_PRE := 3, K_PREA := 1, K_REF := 1,
                                K_CTRLUPD := 1, K_PHYUPD := 1, K_LP := 1, K_INIT := 1 }; }
constraint c_addr { bank dist { [0:1] := 3, [2:7] := 1 }; row[13:3] dist { 0 := 3, [1:2047] := 1 };
                    col[9:6] dist { 0 := 3, [1:15] := 1 }; ap dist { 0 := 3, 1 := 1 }; }
// RD and WR share the nominal latency (DFI_TPHY_WRLAT == DFI_TRDDATA_EN)
constraint c_data { lat dist { 3 := 12, 2 := 1, 4 := 1 }; beats dist { 4 := 12, 3 := 1, 5 := 1 }; }
constraint c_hs   { len inside {[1:30]}; len dist { [DFI_TCTRLUPD_MIN:DFI_TCTRLUPD_MAX] := 8, [1:3] := 1, [25:30] := 1 };
                    resp dist { [0:DFI_TPHYUPD_RESP - 1] := 8, [DFI_TPHYUPD_RESP:20] := 1 };
                    early dist { 0 := 8, 1 := 1 }; intrude dist { 0 := 6, 1 := 1 };
                    intrude -> (len >= 8 && wakeup != 0); fsel inside {[0:3]}; }
constraint c_gap  { gap dist { 0 := 1, [1:3] := 2, [4:9] := 4 }; }
""",
    tr_functions="""
// clear the fields the kind does not use and build the write data
function void post_randomize();
  bit [31:0] x = seed | 1;
  if (kind != K_ACT) row = 0;
  if (!(kind inside {K_RD, K_WR})) begin col = 0; ap = 0; lat = 0; beats = 0; end
  if (kind inside {K_PREA, K_REF, K_INIT, K_CTRLUPD, K_PHYUPD, K_LP}) bank = 0;
  if (kind != K_INIT) fsel = 0;
  if (!(kind inside {K_CTRLUPD, K_LP})) begin len = 0; intrude = 0; end
  if (kind != K_LP) wakeup = 0;
  if (kind != K_PHYUPD) begin resp = 0; early = 0; end
  wdata.delete(); wmask.delete();
  if (kind == K_WR)
    for (int i = 0; i < beats; i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      wdata.push_back(x);
      wmask.push_back((x[31:28] == 4'hF) ? x[3:0] : 4'h0);
    end
endfunction
""",
    drv_rsp=False,
    drv_desc="idle cycles, then one command with its data window, or one handshake",
    drv_idle="""
vif.drv_cb.init_start <= 1'b0; vif.drv_cb.frequency <= '0; vif.drv_cb.cke <= 1'b1;
vif.drv_cb.cs_n <= 1'b1; vif.drv_cb.act_n <= 1'b1; vif.drv_cb.ras_n <= 1'b1; vif.drv_cb.cas_n <= 1'b1;
vif.drv_cb.we_n <= 1'b1; vif.drv_cb.bank <= '0; vif.drv_cb.address <= '0;
vif.drv_cb.wrdata_en <= 1'b0; vif.drv_cb.wrdata <= '0; vif.drv_cb.wrdata_mask <= '0; vif.drv_cb.rddata_en <= 1'b0;
vif.drv_cb.ctrlupd_req <= 1'b0; vif.drv_cb.phyupd_ack <= 1'b0; vif.drv_cb.lp_ctrl_req <= 1'b0;
vif.drv_cb.lp_wakeup <= '0; vif.drv_cb.tb_phyupd <= 1'b0;
""",
    drv_item="""
repeat (t.gap) @(vif.drv_cb);
case (t.kind)
  K_INIT: begin
    int unsigned w = 0;
    vif.drv_cb.init_start <= 1'b1; vif.drv_cb.frequency <= t.fsel;
    repeat (2) @(vif.drv_cb);          // a frequency change drops init_complete first
    while (vif.drv_cb.init_complete !== 1'b1 && w < 64) begin @(vif.drv_cb); w++; end
    @(vif.drv_cb);
    vif.drv_cb.init_start <= 1'b0;
    @(vif.drv_cb);
  end
  K_CTRLUPD: begin
    for (int i = 0; i < t.len; i++) begin
      vif.drv_cb.ctrlupd_req <= 1'b1;
      if (t.intrude && i == 2) command(3'b001, 1'b1, 3'd0, 14'h0);
      @(vif.drv_cb);
      nop();
    end
    vif.drv_cb.ctrlupd_req <= 1'b0;
    repeat (2) @(vif.drv_cb);
  end
  K_PHYUPD: begin
    int unsigned w = 0;
    vif.drv_cb.tb_phyupd <= 1'b1; @(vif.drv_cb); vif.drv_cb.tb_phyupd <= 1'b0;
    while (vif.drv_cb.phyupd_req !== 1'b1 && w < 16) begin @(vif.drv_cb); w++; end
    repeat (t.resp) @(vif.drv_cb);
    vif.drv_cb.phyupd_ack <= 1'b1;
    @(vif.drv_cb);
    if (t.early) begin vif.drv_cb.phyupd_ack <= 1'b0; @(vif.drv_cb); end
    w = 0;
    while (vif.drv_cb.phyupd_req !== 1'b0 && w < 32) begin @(vif.drv_cb); w++; end
    vif.drv_cb.phyupd_ack <= 1'b0;
    repeat (2) @(vif.drv_cb);
  end
  K_LP: begin
    int unsigned w = 0;
    bit done = 0;
    vif.drv_cb.lp_wakeup <= t.wakeup;
    for (int i = 0; i < t.len; i++) begin
      vif.drv_cb.lp_ctrl_req <= 1'b1;
      if (t.intrude && !done && i < t.len - 1 && vif.drv_cb.lp_ack === 1'b1) begin
        command(3'b001, 1'b1, 3'd0, 14'h0); done = 1;
      end
      @(vif.drv_cb);
      nop();
    end
    vif.drv_cb.lp_ctrl_req <= 1'b0;
    @(vif.drv_cb);
    while (vif.drv_cb.lp_ack !== 1'b0 && w < 32) begin @(vif.drv_cb); w++; end
    @(vif.drv_cb);
  end
  default: begin
    bit [13:0] a;
    case (t.kind)
      K_ACT:  begin a = t.row; end
      K_RD, K_WR: a = {3'b0, t.ap, t.col};
      K_PREA: a = 14'h400;
      default: a = 14'h0;
    endcase
    case (t.kind)
      K_ACT:  command(3'b111, 1'b0, t.bank, a);
      K_RD:   command(3'b101, 1'b1, t.bank, a);
      K_WR:   command(3'b100, 1'b1, t.bank, a);
      K_PRE, K_PREA: command(3'b010, 1'b1, t.bank, a);
      default: command(3'b001, 1'b1, t.bank, a);   // REF
    endcase
    // cycle i after the command: data enable at lat .. lat + beats - 1,
    // write data one cycle after each enable
    if (t.kind inside {K_RD, K_WR}) begin
      for (int i = 0; i < t.lat + t.beats + 1 + cfg.tail_cycles; i++) begin
        @(vif.drv_cb);
        if (i == 0) nop();
        if (t.kind == K_WR) begin
          vif.drv_cb.wrdata_en <= (i + 1 >= t.lat && i + 1 < t.lat + t.beats);
          if (i >= t.lat && i < t.lat + t.beats) begin
            vif.drv_cb.wrdata <= t.wdata[i - t.lat]; vif.drv_cb.wrdata_mask <= t.wmask[i - t.lat];
          end else begin
            vif.drv_cb.wrdata <= '0; vif.drv_cb.wrdata_mask <= '0;
          end
        end else
          vif.drv_cb.rddata_en <= (i + 1 >= t.lat && i + 1 < t.lat + t.beats);
      end
    end else begin
      @(vif.drv_cb);
      nop();
    end
  end
endcase
""",
    drv_tasks="""
// drive one command for the next clock (ras_n cas_n we_n, act_n)
task command(bit [2:0] rcw, bit act_n, bit [2:0] b, bit [13:0] a);
  vif.drv_cb.cs_n <= 1'b0; vif.drv_cb.act_n <= act_n;
  vif.drv_cb.ras_n <= rcw[2]; vif.drv_cb.cas_n <= rcw[1]; vif.drv_cb.we_n <= rcw[0];
  vif.drv_cb.bank <= b; vif.drv_cb.address <= a;
endtask

task nop();
  vif.drv_cb.cs_n <= 1'b1; vif.drv_cb.act_n <= 1'b1;
  vif.drv_cb.ras_n <= 1'b1; vif.drv_cb.cas_n <= 1'b1; vif.drv_cb.we_n <= 1'b1;
endtask
""",
    mon_desc="commands with their data windows and the handshakes, with the error codes seen while each item is active",
    mon_run="""
dfi_transaction cur;
int unsigned cyc = 0, age = 0, r_cyc = 0, f_cyc = 0;
bit done = 0, wen_q = 0, is_q = 0, cu_q = 0, lp_q = 0, tbp_q = 0, req_seen = 0, ack_seen = 0, req_low = 0;
forever begin
  bit cmd, in_win, start;
  @(vif.mon_cb);
  if (vif.mon_cb.rst_n !== 1'b1) begin cur = null; cyc = 0; continue; end
  cyc++;
  cmd = vif.mon_cb.cke && !vif.mon_cb.cs_n;
  in_win = cur != null && (cur.kind inside {K_CTRLUPD, K_LP}) && !done;
  // 1. the current item: errors, data, handshake progress
  if (cur != null) begin
    age++;
    if (vif.mon_cb.error) cur.err |= 8'h1 << vif.mon_cb.error_info;
    if (done) begin publish(cur); cur = null; end
  end
  if (cur != null) begin
    case (cur.kind)
      K_WR: begin
        if (vif.mon_cb.wrdata_en) begin if (cur.beats == 0) cur.lat = cyc - cur.cyc; cur.beats++; end
        if (wen_q) begin cur.wdata.push_back(vif.mon_cb.wrdata); cur.wmask.push_back(vif.mon_cb.wrdata_mask); end
        if (age >= 18) done = 1;
      end
      K_RD: begin
        if (vif.mon_cb.rddata_en) begin if (cur.beats == 0) cur.lat = cyc - cur.cyc; cur.beats++; end
        if (vif.mon_cb.rddata_valid) cur.rdata.push_back(vif.mon_cb.rddata);
        if (age >= 18) done = 1;
      end
      K_INIT: begin
        if (vif.mon_cb.init_complete && !cur.acked) begin cur.acked = 1; cur.lat_o = cyc - cur.cyc; end
        cur.freq_o = vif.mon_cb.freq;
        if (!vif.mon_cb.init_start) done = 1;
      end
      K_CTRLUPD: begin
        if (vif.mon_cb.ctrlupd_ack) cur.acked = 1;
        if (vif.mon_cb.ctrlupd_req) begin cur.len++; if (cmd) cur.intrude = 1; end
        else done = 1;
      end
      K_PHYUPD: begin
        if (vif.mon_cb.phyupd_req && !req_seen) begin req_seen = 1; r_cyc = cyc; cur.ptype = vif.mon_cb.phyupd_type; end
        if (vif.mon_cb.phyupd_ack && !ack_seen) begin ack_seen = 1; cur.resp = cyc - r_cyc - 1; end
        if (ack_seen && !vif.mon_cb.phyupd_ack && vif.mon_cb.phyupd_req) cur.early = 1;
        if (req_seen && !vif.mon_cb.phyupd_req && !vif.mon_cb.phyupd_ack) done = 1;
        if (age >= 64) done = 1;
      end
      K_LP: begin
        if (vif.mon_cb.lp_ack) cur.acked = 1;
        if (vif.mon_cb.lp_ctrl_req && !req_low) begin cur.len++; if (cmd) cur.intrude = 1; end
        else if (!req_low) begin req_low = 1; f_cyc = cyc; end
        if (req_low && !vif.mon_cb.lp_ack) begin
          if (cur.acked) cur.lat_o = cyc - f_cyc;
          done = 1;
        end
      end
      default: if (age >= 2) done = 1;
    endcase
  end
  // 2. a new item starts
  start = (cmd && !in_win) || (vif.mon_cb.init_start && !is_q) || (vif.mon_cb.ctrlupd_req && !cu_q) ||
          (vif.mon_cb.lp_ctrl_req && !lp_q) || (vif.mon_cb.tb_phyupd && !tbp_q);
  if (start) begin
    if (cur != null) publish(cur);
    cur = dfi_transaction::type_id::create("t");
    cur.cyc = cyc; age = 0; done = 0; req_seen = 0; ack_seen = 0; req_low = 0;
    if (cmd && !in_win) begin
      bit [2:0] rcw = {vif.mon_cb.ras_n, vif.mon_cb.cas_n, vif.mon_cb.we_n};
      cur.bank = vif.mon_cb.bank;
      if (!vif.mon_cb.act_n) begin cur.kind = K_ACT; cur.row = vif.mon_cb.address; end
      else if (rcw == 3'b101 || rcw == 3'b100) begin
        cur.kind = (rcw == 3'b101) ? K_RD : K_WR;
        cur.col = vif.mon_cb.address[9:0]; cur.ap = vif.mon_cb.address[10];
      end else if (rcw == 3'b010) begin
        cur.kind = vif.mon_cb.address[10] ? K_PREA : K_PRE;
        if (cur.kind == K_PREA) cur.bank = 0;
      end else begin cur.kind = K_REF; cur.bank = 0; end
    end else if (vif.mon_cb.init_start && !is_q) begin cur.kind = K_INIT; cur.fsel = vif.mon_cb.frequency; end
    else if (vif.mon_cb.ctrlupd_req && !cu_q) begin cur.kind = K_CTRLUPD; cur.len = 1; end
    else if (vif.mon_cb.lp_ctrl_req && !lp_q) begin cur.kind = K_LP; cur.len = 1; cur.wakeup = vif.mon_cb.lp_wakeup; end
    else cur.kind = K_PHYUPD;
  end
  wen_q = vif.mon_cb.wrdata_en;
  is_q = vif.mon_cb.init_start; cu_q = vif.mon_cb.ctrlupd_req; lp_q = vif.mon_cb.lp_ctrl_req;
  tbp_q = vif.mon_cb.tb_phyupd;
end
""",
    sb_members="""bit [31:0] mem [bit [11:0]];
bit       open_b [8];
bit [13:0] row_q [8];
int       act_c [8] = '{default: 0};
int       pre_c [8] = '{default: -1000};
int       ref_c = -1000;
bit       init_done = 0;
bit [1:0] pu_type = 0;

function bit [31:0] rd_mem(bit [11:0] i);
  return mem.exists(i) ? mem[i] : (32'h5A5A_0000 | i);
endfunction""",
    predict="""
int c = t.cyc;
bit [2:0] ce = 0;
bit acc = 0;
t.err = 0; t.rdata.delete(); t.acked = 0; t.ptype = 0; t.freq_o = 0; t.lat_o = 0;
case (t.kind)
  K_INIT: begin
    if (open_b.or() != 0) t.err[DFI_E_BANK] = 1;
    init_done = 1; t.acked = 1; t.freq_o = t.fsel; t.lat_o = DFI_TINIT;
  end
  K_CTRLUPD: begin
    t.acked = 1;
    if (t.len < DFI_TCTRLUPD_MIN || t.len > DFI_TCTRLUPD_MAX) t.err[DFI_E_HSHAKE] = 1;
    if (t.intrude) t.err[DFI_E_BUSY] = 1;
  end
  K_PHYUPD: begin
    t.ptype = pu_type; pu_type++;
    if (t.resp >= DFI_TPHYUPD_RESP || t.early) t.err[DFI_E_HSHAKE] = 1;
  end
  K_LP: begin
    t.acked = (t.wakeup != 0) && (t.len > DFI_TLP_RESP);
    if (t.acked) t.lat_o = t.wakeup + 1;
    if (t.intrude && t.acked) t.err[DFI_E_BUSY] = 1;
  end
  default: begin
    if (!init_done) ce = DFI_E_BUSY;
    else case (t.kind)
      K_ACT:
        if (open_b[t.bank]) ce = DFI_E_BANK;
        else if (c - pre_c[t.bank] < DFI_TRP || c - ref_c < DFI_TRFC) ce = DFI_E_TIMING;
        else begin open_b[t.bank] = 1; row_q[t.bank] = t.row; act_c[t.bank] = c; end
      K_RD, K_WR:
        if (!open_b[t.bank]) ce = DFI_E_BANK;
        else if (c - act_c[t.bank] < DFI_TRCD) ce = DFI_E_TIMING;
        else acc = 1;
      K_PRE:
        if (open_b[t.bank]) begin
          if (c - act_c[t.bank] < DFI_TRAS) ce = DFI_E_TIMING;
          else begin open_b[t.bank] = 0; pre_c[t.bank] = c; end
        end
      K_PREA: begin
        foreach (open_b[i]) if (open_b[i] && c - act_c[i] < DFI_TRAS) ce = DFI_E_TIMING;
        if (ce == 0) foreach (open_b[i]) if (open_b[i]) begin open_b[i] = 0; pre_c[i] = c; end
      end
      default:                                       // REF
        if (open_b.or() != 0) ce = DFI_E_BANK;
        else begin
          foreach (pre_c[i]) if (c - pre_c[i] < DFI_TRP) ce = DFI_E_TIMING;
          if (c - ref_c < DFI_TRFC) ce = DFI_E_TIMING;
          if (ce == 0) ref_c = c;
        end
    endcase
    if (ce != 0) t.err[ce] = 1;
    if (t.kind inside {K_RD, K_WR}) begin
      int nom = (t.kind == K_WR) ? DFI_TPHY_WRLAT : DFI_TRDDATA_EN;
      bit [11:0] base = dfi_idx(t.bank, row_q[t.bank], t.col);
      if (acc ? (t.lat != nom || t.beats != DFI_BL) : (t.beats != 0))
        t.err[(t.kind == K_WR) ? DFI_E_WRDATA : DFI_E_RDDATA] = 1;
      if (acc) begin
        // beats inside the expected window move data
        for (int j = 0; j < t.beats; j++) begin
          int k = t.lat + j - nom;
          if (k >= 0 && k < DFI_BL) begin
            bit [11:0] i = dfi_beat(base, k);
            if (t.kind == K_WR) mem[i] = dfi_merge(rd_mem(i), t.wdata[j], t.wmask[j]);
            else t.rdata.push_back(rd_mem(i));
          end
        end
        if (t.ap) begin open_b[t.bank] = 0; pre_c[t.bank] = c + DFI_BL; end
      end
    end
  end
endcase
""",
    checks="""
if (t.kind == K_WR && t.wdata.size() != t.beats) fail(t, "write data beats do not match the enable cycles");
if (t.kind == K_RD && t.rdata.size() > t.beats) fail(t, "more read data than read enables");
if (t.err[0] || t.err[7]) fail(t, "unknown dfi_error_info code");
""",
    coverage="""
cp_kind  : coverpoint tr.kind;
cp_bank  : coverpoint tr.bank iff (tr.kind inside {K_ACT, K_RD, K_WR, K_PRE});
cp_ap    : coverpoint tr.ap iff (tr.kind inside {K_RD, K_WR});
cp_wlat  : coverpoint tr.lat iff (tr.kind == K_WR) { bins early = {2}; bins nom = {3}; bins late = {4}; }
cp_rlat  : coverpoint tr.lat iff (tr.kind == K_RD) { bins early = {2}; bins nom = {3}; bins late = {4}; }
cp_beats : coverpoint tr.beats iff (tr.kind inside {K_RD, K_WR}) { bins short_ = {3}; bins bl = {4}; bins long_ = {5}; }
cp_e_tim : coverpoint tr.err[1];
cp_e_bank: coverpoint tr.err[2];
cp_e_wr  : coverpoint tr.err[3];
cp_e_rd  : coverpoint tr.err[4];
cp_e_busy: coverpoint tr.err[5];
cp_e_hs  : coverpoint tr.err[6];
cp_cu    : coverpoint tr.len iff (tr.kind == K_CTRLUPD) { bins short_ = {[1:3]}; bins ok = {[4:24]}; bins long_ = {[25:63]}; }
cp_pu    : coverpoint tr.resp iff (tr.kind == K_PHYUPD) { bins ok = {[0:11]}; bins late = {[12:31]}; }
cp_ptype : coverpoint tr.ptype iff (tr.kind == K_PHYUPD);
cp_lp    : coverpoint tr.acked iff (tr.kind == K_LP);
cp_fsel  : coverpoint tr.fsel iff (tr.kind == K_INIT) { bins f[] = {[0:3]}; }
cp_cmd   : coverpoint tr.kind { bins c[] = {K_ACT, K_RD, K_WR, K_PRE, K_PREA, K_REF}; }
cp_bad   : coverpoint tr.err { bins ok = {0}; bins bad = {[1:255]}; }
x_cmd_bad: cross cp_cmd, cp_bad;
""",
    seq_members="bit inited = 0;",
    seq_before="""
if (!inited) begin
  dfi_transaction i0 = dfi_transaction::type_id::create("init");
  i0.kind = K_INIT; i0.gap = 2;
  start_item(i0); finish_item(i0);
  inited = 1;
end""",
    directed="""
// a command before init is refused
t = item(); t.kind = K_ACT; t.bank = 1; t.row = 5; t.gap = 3; send(t);
t = item(); t.kind = K_INIT; t.fsel = 2; send(t);
// write, read back and close every bank, with and without auto-precharge
for (int b = 0; b < 8; b++) begin
  t = item(); t.kind = K_ACT; t.bank = b; t.row = 14'h10 + b; t.gap = 2; send(t);
  t = item(); t.kind = K_WR; t.bank = b; t.col = 8 * b; t.lat = DFI_TPHY_WRLAT; t.beats = DFI_BL;
  t.seed = 100 + b; t.gap = 4; t.post_randomize(); send(t);
  t = item(); t.kind = K_RD; t.bank = b; t.col = 8 * b; t.ap = b[0]; t.lat = DFI_TRDDATA_EN; t.beats = DFI_BL;
  t.gap = 1; t.post_randomize(); send(t);
  if (!b[0]) begin t = item(); t.kind = K_PRE; t.bank = b; t.gap = 1; send(t); end
end
// masked write, column wrap inside the row, read back
t = item(); t.kind = K_ACT; t.bank = 2; t.row = 3; t.gap = 5; send(t);
t = item(); t.kind = K_WR; t.bank = 2; t.col = 62; t.lat = DFI_TPHY_WRLAT; t.beats = DFI_BL; t.seed = 7;
t.gap = 4; t.post_randomize(); t.wmask[1] = 4'b0101; t.wmask[2] = 4'hF; send(t);
t = item(); t.kind = K_RD; t.bank = 2; t.col = 62; t.lat = DFI_TRDDATA_EN; t.beats = DFI_BL; t.post_randomize(); send(t);
// data enable one cycle early / late, one beat short / long
for (int k = 0; k < 4; k++) begin
  t = item(); t.kind = K_WR; t.bank = 2; t.col = 4 * k; t.lat = DFI_TPHY_WRLAT + (k == 1) - (k == 0);
  t.beats = DFI_BL + (k == 3) - (k == 2); t.seed = 20 + k; t.post_randomize(); send(t);
  t = item(); t.kind = K_RD; t.bank = 2; t.col = 4 * k; t.lat = DFI_TRDDATA_EN + (k == 1) - (k == 0);
  t.beats = DFI_BL + (k == 3) - (k == 2); t.post_randomize(); send(t);
end
// timing and bank-state violations
t = item(); t.kind = K_PRE; t.bank = 2; send(t);
t = item(); t.kind = K_ACT; t.bank = 2; t.row = 9; send(t);                   // inside tRP
t = item(); t.kind = K_ACT; t.bank = 2; t.row = 9; t.gap = 4; send(t);
t = item(); t.kind = K_RD; t.bank = 2; t.lat = DFI_TRDDATA_EN; t.beats = DFI_BL; t.post_randomize(); send(t);   // inside tRCD
t = item(); t.kind = K_ACT; t.bank = 2; t.row = 9; send(t);                   // bank already open
t = item(); t.kind = K_PRE; t.bank = 2; send(t);                              // inside tRAS (RD tail counts)
t = item(); t.kind = K_RD; t.bank = 5; t.lat = DFI_TRDDATA_EN; t.beats = DFI_BL; t.post_randomize(); send(t);   // closed bank
t = item(); t.kind = K_REF; send(t);                                          // bank 2 open
t = item(); t.kind = K_PREA; t.gap = 9; send(t);
t = item(); t.kind = K_REF; t.gap = 4; send(t);
t = item(); t.kind = K_ACT; t.bank = 0; t.row = 1; send(t);                   // inside tRFC
t = item(); t.kind = K_REF; t.gap = 9; send(t);                               // inside tRFC of the last REF
// handshakes
t = item(); t.kind = K_CTRLUPD; t.len = 6; t.gap = 9; send(t);
t = item(); t.kind = K_CTRLUPD; t.len = 2; send(t);
t = item(); t.kind = K_CTRLUPD; t.len = 26; send(t);
t = item(); t.kind = K_CTRLUPD; t.len = 8; t.intrude = 1; send(t);
for (int k = 0; k < 5; k++) begin
  t = item(); t.kind = K_PHYUPD; t.resp = (k == 3) ? DFI_TPHYUPD_RESP : 2 * k; t.early = (k == 4); send(t);
end
t = item(); t.kind = K_LP; t.len = 6; t.wakeup = 3; send(t);
t = item(); t.kind = K_LP; t.len = 6; t.wakeup = 0; send(t);                  // declined
t = item(); t.kind = K_LP; t.len = 2; t.wakeup = 5; send(t);                  // withdrawn before the ack
t = item(); t.kind = K_LP; t.len = 10; t.wakeup = 1; t.intrude = 1; send(t);
// frequency change with a bank open, then with all banks closed
t = item(); t.kind = K_ACT; t.bank = 6; t.row = 2; t.gap = 9; send(t);
t = item(); t.kind = K_INIT; t.fsel = 1; send(t);
t = item(); t.kind = K_PREA; t.gap = 9; send(t);
t = item(); t.kind = K_INIT; t.fsel = 3; t.gap = 5; send(t);
""",
    drain_ns=1000,
)

SPEC["model"] = """
module dfi_model (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        init_start,
  input  logic [4:0]  frequency,
  input  logic        cke,
  input  logic        cs_n,
  input  logic        act_n,
  input  logic        ras_n,
  input  logic        cas_n,
  input  logic        we_n,
  input  logic [2:0]  bank,
  input  logic [13:0] address,
  input  logic        wrdata_en,
  input  logic [31:0] wrdata,
  input  logic [3:0]  wrdata_mask,
  input  logic        rddata_en,
  input  logic        ctrlupd_req,
  input  logic        phyupd_ack,
  input  logic        lp_ctrl_req,
  input  logic [3:0]  lp_wakeup,
  input  logic        tb_phyupd,
  output logic        init_complete,
  output logic [4:0]  freq,
  output logic [31:0] rddata,
  output logic        rddata_valid,
  output logic        ctrlupd_ack,
  output logic        phyupd_req,
  output logic [1:0]  phyupd_type,
  output logic        lp_ack,
  output logic        error,
  output logic [2:0]  error_info
);
  localparam int BL = 4, WRLAT = 3, RDEN = 3, TRCD = 4, TRP = 4, TRAS = 8, TRFC = 12, TINIT = 10;
  localparam int CU_MIN = 4, CU_MAX = 24, PU_RESP = 12, PU_BUSY = 4, LP_RESP = 3;

  logic [31:0] mem [0:4095];
  logic [31:0] cyc, ref_c;
  logic [31:0] act_c [0:7];
  logic [31:0] pre_c [0:7];
  logic [7:0]  open_b;
  logic [13:0] row_q [0:7];
  logic [7:0]  wexp, wst, rexp, rst_m;   // expected data-enable windows (bit 0: this cycle), window starts
  logic [11:0] wbase_n, wbase, rbase_n, rbase;
  logic [1:0]  wbeat, rbeat;
  logic        wcap;
  logic [11:0] wcap_i;
  logic [3:0]  vld_sr;
  logic [31:0] dat_sr [0:3];
  logic        init_q, tbp_q, lp_q;
  logic [4:0]  icnt, freq_n, pu_cnt;
  logic [5:0]  cu_len;
  logic [1:0]  pu_st, pu_type, lp_st;
  logic [3:0]  lp_cnt;

  initial for (int i = 0; i < 4096; i++) mem[i] = 32'h5A5A_0000 | i;

  function automatic logic [11:0] f_idx(input logic [2:0] b, input logic [13:0] r, input logic [9:0] c);
    f_idx = {b, r[2:0], c[5:0]};
  endfunction
  function automatic logic [11:0] f_beat(input logic [11:0] base, input logic [1:0] k);
    f_beat = {base[11:6], base[5:0] + {4'b0, k}};
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cyc <= '0; ref_c <= 32'hFFFF_FF00; open_b <= '0;
      for (int i = 0; i < 8; i++) begin act_c[i] <= '0; pre_c[i] <= 32'hFFFF_FF00; row_q[i] <= '0; end
      wexp <= '0; wst <= '0; rexp <= '0; rst_m <= '0;
      wbase_n <= '0; wbase <= '0; rbase_n <= '0; rbase <= '0; wbeat <= '0; rbeat <= '0;
      wcap <= 1'b0; wcap_i <= '0; vld_sr <= '0;
      for (int i = 0; i < 4; i++) dat_sr[i] <= '0;
      init_q <= 1'b0; tbp_q <= 1'b0; lp_q <= 1'b0; icnt <= '0; freq_n <= '0; pu_cnt <= '0; cu_len <= '0;
      pu_st <= '0; pu_type <= '0; lp_st <= '0; lp_cnt <= '0;
      init_complete <= 1'b0; freq <= '0; rddata <= '0; rddata_valid <= 1'b0; ctrlupd_ack <= 1'b0;
      phyupd_req <= 1'b0; phyupd_type <= '0; lp_ack <= 1'b0; error <= 1'b0; error_info <= '0;
    end else begin : step
      logic [2:0]  e, ce, de;          // handshake, command and data errors of this cycle
      logic [7:0]  wx, wsx, rx, rsx;
      logic [11:0] wi, ri;
      e = 3'd0; ce = 3'd0; de = 3'd0;
      cyc <= cyc + 32'd1;
      error <= 1'b0;
      wx = wexp >> 1; wsx = wst >> 1; rx = rexp >> 1; rsx = rst_m >> 1;

      // initialisation / frequency change
      init_q <= init_start;
      if (init_start && !init_q) begin
        if (open_b != 8'h0) e = 3'd2;
        init_complete <= 1'b0; icnt <= TINIT - 1; freq_n <= frequency;
      end else if (icnt != 5'd0) begin
        icnt <= icnt - 5'd1;
        if (icnt == 5'd1) begin init_complete <= 1'b1; freq <= freq_n; end
      end

      // controller update: ack while requested, tctrlupd_min .. max cycles
      if (ctrlupd_req) begin
        ctrlupd_ack <= 1'b1;
        if (cu_len != 6'd63) cu_len <= cu_len + 6'd1;
      end else begin
        ctrlupd_ack <= 1'b0; cu_len <= '0;
        if (cu_len != 6'd0 && (cu_len < CU_MIN || cu_len > CU_MAX)) e = 3'd6;
      end

      // PHY update, started by tb_phyupd (the PHY's own need for one)
      tbp_q <= tb_phyupd;
      case (pu_st)
        2'd0:
          if (tb_phyupd && !tbp_q) begin
            pu_st <= 2'd1; phyupd_req <= 1'b1; phyupd_type <= pu_type; pu_type <= pu_type + 2'd1; pu_cnt <= '0;
          end
        2'd1:
          if (phyupd_ack) begin pu_st <= 2'd2; pu_cnt <= '0; end
          else begin
            if (pu_cnt != 5'd31) pu_cnt <= pu_cnt + 5'd1;
            if (pu_cnt == PU_RESP) e = 3'd6;          // no ack within tphyupd_resp
          end
        2'd2:
          if (!phyupd_ack) begin e = 3'd6; pu_st <= 2'd0; phyupd_req <= 1'b0; end   // ack dropped during the update
          else begin
            pu_cnt <= pu_cnt + 5'd1;
            if (pu_cnt == PU_BUSY - 1) begin phyupd_req <= 1'b0; pu_st <= 2'd3; end
          end
        default:
          if (!phyupd_ack) pu_st <= 2'd0;
      endcase

      // low power: ack tlp_resp cycles after the request (declined when
      // lp_wakeup is 0), dropped lp_wakeup cycles after the request ends
      lp_q <= lp_ctrl_req;
      case (lp_st)
        2'd0:
          if (lp_ctrl_req && !lp_q && lp_wakeup != 4'd0) begin lp_st <= 2'd1; lp_cnt <= LP_RESP - 1; end
        2'd1:
          if (!lp_ctrl_req) lp_st <= 2'd0;
          else if (lp_cnt == 4'd0) begin lp_ack <= 1'b1; lp_st <= 2'd2; end
          else lp_cnt <= lp_cnt - 4'd1;
        2'd2:
          if (!lp_ctrl_req) begin lp_st <= 2'd3; lp_cnt <= lp_wakeup; end
        default:
          if (lp_cnt <= 4'd1) begin lp_ack <= 1'b0; lp_st <= 2'd0; end
          else lp_cnt <= lp_cnt - 4'd1;
      endcase

      // command channel
      if (cke && !cs_n) begin
        if (!init_complete || ctrlupd_ack || phyupd_ack || lp_ack) ce = 3'd5;
        else if (!act_n) begin                                     // ACT
          if (open_b[bank]) ce = 3'd2;
          else if ($signed(cyc - pre_c[bank]) < TRP || $signed(cyc - ref_c) < TRFC) ce = 3'd1;
          else begin open_b[bank] <= 1'b1; row_q[bank] <= address; act_c[bank] <= cyc; end
        end else if (ras_n && !cas_n) begin                        // RD (we_n 1) / WR (we_n 0)
          if (!open_b[bank]) ce = 3'd2;
          else if ($signed(cyc - act_c[bank]) < TRCD) ce = 3'd1;
          else begin
            if (we_n) begin
              rx = rx | (8'hF << (RDEN - 1)); rsx = rsx | (8'h1 << (RDEN - 1));
              rbase_n <= f_idx(bank, row_q[bank], address[9:0]);
            end else begin
              wx = wx | (8'hF << (WRLAT - 1)); wsx = wsx | (8'h1 << (WRLAT - 1));
              wbase_n <= f_idx(bank, row_q[bank], address[9:0]);
            end
            if (address[10]) begin open_b[bank] <= 1'b0; pre_c[bank] <= cyc + BL; end   // auto-precharge
          end
        end else if (!ras_n && cas_n && !we_n) begin               // PRE / PREA
          if (address[10]) begin
            for (int i = 0; i < 8; i++) if (open_b[i] && $signed(cyc - act_c[i]) < TRAS) ce = 3'd1;
            if (ce == 3'd0)
              for (int i = 0; i < 8; i++) if (open_b[i]) begin open_b[i] <= 1'b0; pre_c[i] <= cyc; end
          end else if (open_b[bank]) begin
            if ($signed(cyc - act_c[bank]) < TRAS) ce = 3'd1;
            else begin open_b[bank] <= 1'b0; pre_c[bank] <= cyc; end
          end
        end else if (!ras_n && !cas_n && we_n) begin               // REF
          if (open_b != 8'h0) ce = 3'd2;
          else begin
            for (int i = 0; i < 8; i++) if ($signed(cyc - pre_c[i]) < TRP) ce = 3'd1;
            if ($signed(cyc - ref_c) < TRFC) ce = 3'd1;
            if (ce == 3'd0) ref_c <= cyc;
          end
        end
      end

      // write data: enable exactly in the window, data one cycle later
      if (wrdata_en != wexp[0]) de = 3'd3;
      wi = f_beat(wbase, wbeat);
      if (wexp[0]) begin
        if (wst[0]) begin wi = wbase_n; wbase <= wbase_n; wbeat <= 2'd1; end
        else wbeat <= wbeat + 2'd1;
      end
      wcap <= wrdata_en && wexp[0];
      wcap_i <= wi;
      if (wcap)
        mem[wcap_i] <= {wrdata_mask[3] ? mem[wcap_i][31:24] : wrdata[31:24],
                        wrdata_mask[2] ? mem[wcap_i][23:16] : wrdata[23:16],
                        wrdata_mask[1] ? mem[wcap_i][15:8]  : wrdata[15:8],
                        wrdata_mask[0] ? mem[wcap_i][7:0]   : wrdata[7:0]};

      // read data: enable exactly in the window, valid data registered four cycles later
      if (rddata_en != rexp[0] && de == 3'd0) de = 3'd4;
      ri = f_beat(rbase, rbeat);
      if (rexp[0]) begin
        if (rst_m[0]) begin ri = rbase_n; rbase <= rbase_n; rbeat <= 2'd1; end
        else rbeat <= rbeat + 2'd1;
      end
      vld_sr <= {vld_sr[2:0], rddata_en && rexp[0]};
      dat_sr[0] <= mem[ri];
      for (int i = 1; i < 4; i++) dat_sr[i] <= dat_sr[i - 1];
      rddata_valid <= vld_sr[3];
      rddata <= vld_sr[3] ? dat_sr[3] : 32'h0;

      wexp <= wx; wst <= wsx; rexp <= rx; rst_m <= rsx;
      if (e == 3'd0) e = ce;
      if (e == 3'd0) e = de;
      if (e != 3'd0) begin error <= 1'b1; error_info <= e; end
    end
  end
endmodule
"""

SPEC["sva"] = """
// outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n)
                 !$isunknown({init_complete, rddata_valid, ctrlupd_ack, phyupd_req, lp_ack, error, error_info}))
  else $error("DFI: X on outputs");
// an error always carries a code
assert property (@(posedge clk) disable iff (!rst_n) error |-> error_info != 3'd0)
  else $error("DFI: dfi_error without dfi_error_info");
// init completes only while the controller requests it
assert property (@(posedge clk) disable iff (!rst_n) $rose(init_complete) |-> init_start)
  else $error("DFI: dfi_init_complete without dfi_init_start");
// the PHY acks a controller update only while it is requested
assert property (@(posedge clk) disable iff (!rst_n) ctrlupd_ack |-> $past(ctrlupd_req))
  else $error("DFI: dfi_ctrlupd_ack without a request");
// low-power ack only after a request
assert property (@(posedge clk) disable iff (!rst_n) $rose(lp_ack) |-> lp_ctrl_req)
  else $error("DFI: dfi_lp_ack without dfi_lp_ctrl_req");
// the controller acks a PHY update only while it is requested
assert property (@(posedge clk) disable iff (!rst_n) $rose(phyupd_ack) |-> phyupd_req)
  else $error("DFI: dfi_phyupd_ack without dfi_phyupd_req");
// a command while an update or low-power ack is high is flagged
assert property (@(posedge clk) disable iff (!rst_n)
                 cke && !cs_n && (ctrlupd_ack || phyupd_ack || lp_ack) |=> error && error_info == 3'd5)
  else $error("DFI: command during an update / low power not flagged");
cover property (@(posedge clk) disable iff (!rst_n) rddata_valid);
cover property (@(posedge clk) disable iff (!rst_n) error && error_info == 3'd1);
cover property (@(posedge clk) disable iff (!rst_n) $fell(lp_ack));
"""

SPEC["smoke"] = """
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic init_start = 1'b0, cke = 1'b1, cs_n = 1'b1, act_n = 1'b1, ras_n = 1'b1, cas_n = 1'b1, we_n = 1'b1;
logic [4:0] frequency = '0;
logic [2:0] bank = '0;
logic [13:0] address = '0;
logic wrdata_en = 1'b0, rddata_en = 1'b0, ctrlupd_req = 1'b0, phyupd_ack = 1'b0, lp_ctrl_req = 1'b0, tb_phyupd = 1'b0;
logic [31:0] wrdata = '0;
logic [3:0] wrdata_mask = '0, lp_wakeup = '0;
wire init_complete, rddata_valid, ctrlupd_ack, phyupd_req, lp_ack, error;
wire [4:0] freq;
wire [31:0] rddata;
wire [1:0] phyupd_type;
wire [2:0] error_info;

always #5 clk = ~clk;

dfi_model u_dut (.clk(clk), .rst_n(rst_n), .init_start(init_start), .frequency(frequency), .cke(cke), .cs_n(cs_n),
                 .act_n(act_n), .ras_n(ras_n), .cas_n(cas_n), .we_n(we_n), .bank(bank), .address(address),
                 .wrdata_en(wrdata_en), .wrdata(wrdata), .wrdata_mask(wrdata_mask), .rddata_en(rddata_en),
                 .ctrlupd_req(ctrlupd_req), .phyupd_ack(phyupd_ack), .lp_ctrl_req(lp_ctrl_req), .lp_wakeup(lp_wakeup),
                 .tb_phyupd(tb_phyupd), .init_complete(init_complete), .freq(freq), .rddata(rddata),
                 .rddata_valid(rddata_valid), .ctrlupd_ack(ctrlupd_ack), .phyupd_req(phyupd_req),
                 .phyupd_type(phyupd_type), .lp_ack(lp_ack), .error(error), .error_info(error_info));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

// error codes seen since the last clear (bit k: code k)
logic [7:0] errs = '0;
int nerr = 0;
always @(negedge clk) if (error) begin errs = errs | (8'h1 << error_info); nerr++; end

// read data returned since the last clear
logic [31:0] rd [0:15];
int nrd = 0, t_rd = -1, tcyc = 0;
always @(posedge clk) tcyc++;
always @(negedge clk) begin
  if (rddata_valid && nrd < 16) begin rd[nrd] = rddata; nrd++; if (t_rd < 0) t_rd = tcyc; end
end

// tasks return 1 ns after a falling edge, after the monitors above ran
task automatic idle(input int n);
  repeat (n) @(negedge clk);
  #1;
endtask

// one command, sampled on the next rising edge; returns one cycle later
int t_cmd;
task automatic cmd(input logic [2:0] rcw, input logic an, input logic [2:0] b, input logic [13:0] a);
  @(negedge clk); cs_n = 0; act_n = an; {ras_n, cas_n, we_n} = rcw; bank = b; address = a; t_cmd = tcyc;
  @(negedge clk); cs_n = 1; act_n = 1; {ras_n, cas_n, we_n} = 3'b111;
  #1;
endtask

task automatic act(input logic [2:0] b, input logic [13:0] r); cmd(3'b111, 1'b0, b, r); endtask
task automatic pre(input logic [2:0] b, input logic all); cmd(3'b010, 1'b1, b, all ? 14'h400 : 14'h0); endtask
task automatic refr(); cmd(3'b001, 1'b1, 3'd0, 14'h0); endtask

// WR / RD with the data enable at cycle lat after the command for n cycles
logic [31:0] wd [0:7];
logic [3:0]  wm [0:7];
task automatic wr(input logic [2:0] b, input logic [9:0] c, input logic ap, input int lat, input int n);
  cmd(3'b100, 1'b1, b, {3'b0, ap, c});
  for (int k = 1; k < lat + n + 8; k++) begin
    wrdata_en = (k >= lat && k < lat + n);
    if (k - 1 >= lat && k - 1 < lat + n) begin wrdata = wd[k - 1 - lat]; wrdata_mask = wm[k - 1 - lat]; end
    else begin wrdata = '0; wrdata_mask = '0; end
    @(negedge clk);
  end
  wrdata_en = 0;
  #1;
endtask
task automatic rdc(input logic [2:0] b, input logic [9:0] c, input logic ap, input int lat, input int n);
  nrd = 0; t_rd = -1;
  cmd(3'b101, 1'b1, b, {3'b0, ap, c});
  for (int k = 1; k < lat + n + 10; k++) begin
    rddata_en = (k >= lat && k < lat + n);
    @(negedge clk);
  end
  rddata_en = 0;
  #1;
endtask

function automatic logic [31:0] pat(input logic [2:0] b, input logic [2:0] r, input logic [5:0] c);
  pat = 32'h5A5A_0000 | {b, r, c};
endfunction

int t0, k0;

initial begin
  repeat (3) @(posedge clk);
  chk(!init_complete && !rddata_valid && !ctrlupd_ack && !phyupd_req && !lp_ack && !error && error_info == 3'd0 &&
      freq == 5'd0 && rddata == 32'h0 && phyupd_type == 2'd0, "outputs clear in reset");
  @(negedge clk); rst_n = 1;

  // before init
  errs = 0; act(3'd1, 14'h5); idle(1);
  chk(errs == 8'h20, $sformatf("command before init: busy error (%02h)", errs));
  // init at frequency 2
  @(negedge clk); init_start = 1; frequency = 5'd2; t0 = tcyc;
  while (!init_complete && tcyc - t0 < 40) @(negedge clk);
  chk(tcyc - t0 == 10, $sformatf("init complete 10 cycles after init start (%0d)", tcyc - t0));
  chk(freq == 5'd2, "frequency taken at init");
  @(negedge clk); init_start = 0; idle(2);

  // write, read back
  errs = 0;
  act(3'd0, 14'h10); idle(3);
  for (int i = 0; i < 4; i++) begin wd[i] = 32'h1111_0000 * (i + 1) + i; wm[i] = 4'h0; end
  wr(3'd0, 10'd0, 1'b0, 3, 4);
  rdc(3'd0, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h0, $sformatf("legal ACT / WR / RD: no error (%02h)", errs));
  chk(nrd == 4 && rd[0] == wd[0] && rd[1] == wd[1] && rd[2] == wd[2] && rd[3] == wd[3], "read returns the written burst");
  chk(t_rd - t_cmd == 8, $sformatf("first read beat 8 cycles after RD (%0d)", t_rd - t_cmd));
  rdc(3'd0, 10'd8, 1'b0, 3, 4);
  chk(nrd == 4 && rd[0] == pat(0, 0, 8) && rd[3] == pat(0, 0, 11), "unwritten columns read the default pattern");
  // byte masks and the column wrap inside the row
  for (int i = 0; i < 4; i++) begin wd[i] = 32'hA0B0_C0D0 + i; wm[i] = 4'h0; end
  wm[1] = 4'b0101;
  wr(3'd0, 10'd62, 1'b0, 3, 4);
  rdc(3'd0, 10'd62, 1'b0, 3, 4);
  chk(rd[0] == wd[0] && rd[1] == {wd[1][31:24], 8'h5A, wd[1][15:8], 8'h3F} && rd[2] == wd[2], "byte masks keep masked bytes");
  rdc(3'd0, 10'd0, 1'b0, 3, 4);
  chk(rd[0] == wd[2] && rd[1] == wd[3] && rd[2] == 32'h3333_0002, "burst wraps inside the 64-column row");
  // rows alias above bit 2
  act(3'd3, 14'h8); idle(3);
  rdc(3'd3, 10'd5, 1'b0, 3, 4);
  chk(errs == 8'h0 && rd[0] == pat(3, 0, 5), "row 8 reads the row-0 location");

  // timing boundaries: tRCD, tRAS, tRP, tRFC
  errs = 0; act(3'd1, 14'h1); idle(1); rdc(3'd1, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h12, $sformatf("RD 3 cycles after ACT: tRCD error, read enable error (%02h)", errs));
  errs = 0; act(3'd2, 14'h1); idle(2); rdc(3'd2, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h0 && nrd == 4, "RD 4 cycles after ACT accepted");
  errs = 0; act(3'd4, 14'h1); idle(5); pre(3'd4, 1'b0);
  chk(errs == 8'h02, $sformatf("PRE 7 cycles after ACT: tRAS error (%02h)", errs));
  errs = 0; pre(3'd4, 1'b0);
  chk(errs == 8'h0, "PRE 8 cycles after ACT accepted");
  errs = 0; idle(1); act(3'd4, 14'h2);
  chk(errs == 8'h02, $sformatf("ACT 3 cycles after PRE: tRP error (%02h)", errs));
  errs = 0; act(3'd4, 14'h2);
  chk(errs == 8'h0, "ACT 5 cycles after PRE accepted");
  pre(3'd3, 1'b0); idle(2); errs = 0; act(3'd3, 14'h8);
  chk(errs == 8'h0, "ACT 4 cycles after PRE accepted");
  // NOP and other commands (MRS) with cs_n low change nothing
  errs = 0; cmd(3'b111, 1'b1, 3'd3, 14'h0); cmd(3'b000, 1'b1, 3'd3, 14'h0); cmd(3'b110, 1'b1, 3'd3, 14'h0);
  idle(2); rdc(3'd3, 10'd5, 1'b0, 3, 4);
  chk(errs == 8'h0 && nrd == 4, "NOP / MRS / ZQ commands ignored, bank still open");
  // bank state
  errs = 0; act(3'd4, 14'h2);
  chk(errs == 8'h04, "ACT to an open bank: bank error");
  errs = 0; rdc(3'd5, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h14 && nrd == 0, $sformatf("RD to a closed bank: bank error, no data (%02h)", errs));
  errs = 0; refr();
  chk(errs == 8'h04, "REF with banks open: bank error");
  errs = 0; pre(3'd6, 1'b0);
  chk(errs == 8'h0, "PRE of a closed bank is a no-op");
  idle(8);
  errs = 0; act(3'd5, 14'h1); pre(3'd0, 1'b1);
  chk(errs == 8'h02, "PREA with a bank inside tRAS: timing error");
  idle(3); rdc(3'd0, 10'd0, 1'b0, 3, 4);
  chk(nrd == 4, "rejected PREA closes nothing");
  idle(4);
  errs = 0; pre(3'd0, 1'b1);
  chk(errs == 8'h0, "PREA closes all banks");
  errs = 0; rdc(3'd2, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h14, "bank closed by PREA");
  errs = 0; refr();
  chk(errs == 8'h0, "REF with all banks closed");
  idle(9); errs = 0; act(3'd0, 14'h1);
  chk(errs == 8'h02, "ACT 11 cycles after REF: tRFC error");
  errs = 0; act(3'd0, 14'h1);
  chk(errs == 8'h0, "ACT 12 cycles after REF accepted");
  idle(8); pre(3'd0, 1'b0); idle(1);
  errs = 0; refr();
  chk(errs == 8'h02, $sformatf("REF 3 cycles after PRE: tRP error (%02h)", errs));
  errs = 0; refr();
  chk(errs == 8'h0, "REF 5 cycles after PRE accepted");
  idle(8); errs = 0; refr();
  chk(errs == 8'h02, "REF 10 cycles after REF: tRFC error");
  errs = 0; refr();
  chk(errs == 8'h0, "REF 12 cycles after REF accepted");
  // auto-precharge
  idle(12); act(3'd1, 14'h3); idle(3);
  errs = 0; rdc(3'd1, 10'd0, 1'b1, 3, 4);
  chk(errs == 8'h0 && nrd == 4, "RD with auto-precharge");
  errs = 0; rdc(3'd1, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h14, "auto-precharge closed the bank");
  act(3'd1, 14'h3); idle(3);
  errs = 0; wr(3'd1, 10'd4, 1'b1, 3, 4); act(3'd1, 14'h3);
  chk(errs == 8'h0, "WR with auto-precharge, ACT after the burst and tRP");
  idle(3); pre(3'd1, 1'b0); idle(4);
  act(3'd1, 14'h3); idle(3);
  errs = 0; cmd(3'b100, 1'b1, 3'd1, 14'h400); act(3'd1, 14'h3);
  chk(errs == 8'h02, $sformatf("ACT right after WR with auto-precharge: tRP error (%02h)", errs));
  idle(12);
  // auto-precharge starts tRP after the burst: ACT 7 cycles after RD-AP is early, 8 is in time
  act(3'd1, 14'h3); idle(3);
  cmd(3'b101, 1'b1, 3'd1, 14'h400); idle(5); errs = 0; act(3'd1, 14'h3);
  chk(errs[2:1] == 2'b01, $sformatf("ACT 7 cycles after RD with auto-precharge: tRP error (%02h)", errs));
  idle(12); act(3'd1, 14'h3); idle(3);
  cmd(3'b101, 1'b1, 3'd1, 14'h400); idle(6); errs = 0; act(3'd1, 14'h3);
  chk(errs[2:1] == 2'b00, $sformatf("ACT 8 cycles after RD with auto-precharge accepted (%02h)", errs));
  idle(8); pre(3'd1, 1'b0); idle(12);

  // data enable windows
  act(3'd2, 14'h4); idle(3);
  for (int i = 0; i < 6; i++) begin wd[i] = 32'hC0DE_0000 + i; wm[i] = 4'h0; end
  errs = 0; wr(3'd2, 10'd0, 1'b0, 2, 4);
  chk(errs == 8'h08, "write enable one cycle early: wrdata error");
  rdc(3'd2, 10'd0, 1'b0, 3, 4);
  chk(rd[0] == wd[1] && rd[2] == wd[3] && rd[3] == pat(2, 4, 3), "early write: beats inside the window are written");
  errs = 0; wr(3'd2, 10'd8, 1'b0, 4, 4);
  chk(errs == 8'h08, "write enable one cycle late");
  errs = 0; wr(3'd2, 10'd8, 1'b0, 3, 3);
  chk(errs == 8'h08, "write burst one beat short");
  errs = 0; wr(3'd2, 10'd8, 1'b0, 3, 5);
  chk(errs == 8'h08, "write burst one beat long");
  errs = 0; rdc(3'd2, 10'd8, 1'b0, 2, 4);
  chk(errs == 8'h10 && nrd == 3, $sformatf("read enable one cycle early: rddata error, 3 beats (%0d)", nrd));
  errs = 0; rdc(3'd2, 10'd8, 1'b0, 4, 4);
  chk(errs == 8'h10 && nrd == 3, "read enable one cycle late: 3 beats");
  errs = 0; rdc(3'd2, 10'd8, 1'b0, 3, 5);
  chk(errs == 8'h10 && nrd == 4, "read enable one beat long: 4 beats");
  errs = 0; wr(3'd7, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h0C, "WR to a closed bank: bank and wrdata errors");
  // clock disabled: commands ignored
  cke = 0; errs = 0; act(3'd7, 14'h1); cke = 1; idle(4);
  rdc(3'd7, 10'd0, 1'b0, 3, 4);
  chk(errs == 8'h14, "ACT with cke low ignored");

  // controller update
  pre(3'd0, 1'b1); idle(4);
  @(negedge clk); ctrlupd_req = 1; @(negedge clk);
  chk(ctrlupd_ack, "ctrlupd_ack one cycle after the request");
  errs = 0; act(3'd0, 14'h1);
  chk(errs == 8'h20, "command during ctrlupd_ack: busy error");
  idle(1); ctrlupd_req = 0; idle(1);
  chk(!ctrlupd_ack && errs == 8'h20, "4-cycle update ends without a handshake error");
  for (int n = 3; n <= 25; n += 22) begin
    errs = 0; ctrlupd_req = 1; idle(n); ctrlupd_req = 0; idle(2);
    chk(errs == 8'h40, $sformatf("%0d-cycle update: handshake error", n));
    errs = 0; ctrlupd_req = 1; idle(n == 3 ? 4 : 24); ctrlupd_req = 0; idle(2);
    chk(errs == 8'h0, $sformatf("%0d-cycle update accepted", n == 3 ? 4 : 24));
  end

  // a very long update saturates the cycle counter: still one error at the end
  nerr = 0; errs = 0; ctrlupd_req = 1; idle(70); ctrlupd_req = 0; idle(2);
  chk(errs == 8'h40 && nerr == 1, $sformatf("70-cycle update: one handshake error (%0d)", nerr));

  // PHY update
  for (int k = 0; k < 3; k++) begin
    errs = 0;
    @(negedge clk); tb_phyupd = 1; @(negedge clk); tb_phyupd = 0;
    chk(phyupd_req && phyupd_type == k, $sformatf("PHY update request %0d with type %0d", k, phyupd_type));
    idle(11 + k); phyupd_ack = 1;
    @(negedge clk);
    t0 = tcyc; while (phyupd_req && tcyc - t0 < 20) @(negedge clk);
    chk(tcyc - t0 == 4, $sformatf("PHY update takes 4 cycles after the ack (%0d)", tcyc - t0));
    phyupd_ack = 0; idle(2);
    chk(errs == (k == 2 ? 8'h40 : 8'h0), $sformatf("ack %0d cycles after the request: %s", 12 + k, k == 2 ? "late" : "in time"));
  end
  // an ack 40 cycles late: one error
  nerr = 0; errs = 0;
  @(negedge clk); tb_phyupd = 1; @(negedge clk); tb_phyupd = 0;
  idle(40); phyupd_ack = 1; idle(6); phyupd_ack = 0; idle(2);
  chk(errs == 8'h40 && nerr == 1 && !phyupd_req, $sformatf("ack 40 cycles late: one handshake error (%0d)", nerr));
  errs = 0;
  @(negedge clk); tb_phyupd = 1; @(negedge clk); tb_phyupd = 0;
  idle(2); phyupd_ack = 1; @(negedge clk);
  errs = 0; act(3'd0, 14'h1);
  chk(errs == 8'h20, "command during phyupd_ack: busy error");
  phyupd_ack = 0; idle(2);
  chk(errs == 8'h60 && !phyupd_req, "ack dropped during the update: handshake error, request withdrawn");

  // low power
  lp_wakeup = 3; @(negedge clk); lp_ctrl_req = 1; idle(3);
  chk(!lp_ack, "no lp_ack before tlp_resp");
  @(negedge clk);
  chk(lp_ack, "lp_ack four cycles after the request");
  errs = 0; act(3'd0, 14'h1);
  chk(errs == 8'h20, "command during lp_ack: busy error");
  lp_ctrl_req = 0; t0 = tcyc;
  @(negedge clk); while (lp_ack && tcyc - t0 < 20) @(negedge clk);
  chk(tcyc - t0 == 4, $sformatf("lp_ack drops lp_wakeup + 1 cycles after the request (%0d)", tcyc - t0));
  lp_wakeup = 0; lp_ctrl_req = 1; idle(8); lp_ctrl_req = 0; idle(2);
  chk(!lp_ack, "lp_wakeup 0: request declined");
  lp_wakeup = 2; lp_ctrl_req = 1; idle(3); lp_ctrl_req = 0; idle(6);
  chk(!lp_ack, "request withdrawn before the ack: no ack");
  lp_ctrl_req = 1; idle(5); lp_ctrl_req = 0; @(negedge clk);
  chk(lp_ack, "ack held while waking up");
  idle(2);
  chk(!lp_ack, "lp_wakeup 2: ack dropped 3 cycles after the request");

  // frequency change
  act(3'd6, 14'h1); idle(2);
  errs = 0; @(negedge clk); init_start = 1; frequency = 5'd1; @(negedge clk);
  chk(!init_complete, "frequency change: init_complete drops");
  while (!init_complete) @(negedge clk);
  @(negedge clk); init_start = 0;
  chk(errs == 8'h04 && freq == 5'd1, "frequency change with a bank open: bank error, new frequency");

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #2000000;
  $display("FUNC_FAIL timeout");
  $finish;
end
"""
