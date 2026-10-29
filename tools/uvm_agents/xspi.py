# JEDEC JESD251 xSPI (Profile 1.0, 8D-8D-8D octal DDR) host agent.
# tb/top_tb.sv xspi_model: 64 Kbit NOR flash (8 KiB, two 4 KiB sectors,
# 256-byte pages, erased = 0xFF) behind an 8D-8D-8D command interface.
#
# Wires: cs_n, ck, the host and device halves of the DQ[7:0] bus (dq_m with
# dq_m_oe, dq_s with dq_s_oe) and the read data strobe ds. One DDR beat per
# system clock: the host toggles ck on every beat; the device samples DQ
# on every ck edge and toggles ds with every byte it drives.
#
# Transfer: opcode, inverted opcode (command extension), 4 address bytes MSB
# first (all commands but WREN / WRDI), then for reads XSPI_DUMMY dummy beats
# and data, for Page Program data bytes. A command takes effect at CS# rise.
#   0x06 WREN   0x04 WRDI   0x05 RDSR (status {6'b0, WEL, WIP} on every beat)
#   0x9F RDID (ID bytes 0x5A 0x81 0x1A repeating)   0xEE 8D READ (address
#   increments, wraps at 8 KiB)   0x12 PAGE PROGRAM (needs WEL; bytes AND
#   into the array, address wraps inside the 256-byte page; WIP while busy)
#   0x21 SECTOR ERASE 4 KiB (needs WEL)
# A wrong command extension, an unknown opcode, or any command but RDSR while
# WIP is set is ignored; PP / SE without WEL are ignored; WEL clears when a
# program or erase ends and on WRDI. The sequences poll RDSR after PP / SE
# until WIP clears (as a host must), so the scoreboard needs no busy timing:
# it accepts a WIP of 1 only while a program / erase it predicted is pending.

SPEC = dict(
    vip="xSPI-UVM-VIP", p="xspi", P="xSPI", dir="xspi", family="Memory / Flash",
    desc="JEDEC JESD251 xSPI Profile 1.0 host VIP (8D-8D-8D octal DDR): command + inverted extension, "
         "4-byte address, read latency, data strobe, NOR program / erase with WEL / WIP status.",
    about="""
xSPI (octal DDR serial NOR, JESD251) is the boot and XIP flash interface of
current MCUs and SoCs. The DUT model is an 8 KiB NOR array; the scoreboard keeps
its own copy (NOR program can only clear bits, erase sets 0xFF, page wrap,
write-enable latch) and predicts every read, status and ID byte. The monitor
rebuilds each transfer from the wires: the host beats from DQ, the device bytes
from the DS strobe edges. The DQ bus is modelled as its host-driven and
device-driven halves so the model needs no tristate.""",
    defs="""
localparam int XSPI_DUMMY = 16;        // dummy beats before read data (8 clock cycles, DDR)
localparam int XSPI_MEM   = 8192;      // array size in bytes
""",
    timeout=400,
    ports=[
        ("in", "logic", "cs_n"), ("in", "logic", "ck"),
        ("in", "logic [7:0]", "dq_m"), ("in", "logic", "dq_m_oe"),
        ("out", "logic [7:0]", "dq_s"), ("out", "logic", "dq_s_oe"), ("out", "logic", "ds"),
    ],
    fields=[
        ("bit [7:0]", "opcode", "req"),
        ("bit", "bad_ext", "req"),            # command extension not the inverted opcode
        ("bit [31:0]", "addr", "req"),
        ("bit [7:0]", "wdata", "req", "q"),   # Page Program data
        ("bit [7:0]", "nread", "req"),        # data beats clocked after the dummy beats
        ("bit [7:0]", "rdata", "rsp", "q"),   # bytes the device drove (DS edges)
        ("bit [5:0]", "len", "info", "rand"), # Page Program length - 1
        ("bit [31:0]", "seed", "info", "rand"),
    ],
    constraints="""
constraint c_op   { opcode dist { 8'h06 := 3, 8'h04 := 1, 8'h05 := 2, 8'h9F := 1, 8'hEE := 4,
                                  8'h12 := 3, 8'h21 := 1, 8'hAB := 1 }; }
constraint c_ext  { bad_ext dist { 0 := 15, 1 := 1 }; }
constraint c_addr { addr[31:13] == 0;
                    (opcode inside {8'h06, 8'h04, 8'h05, 8'h9F, 8'hAB}) -> addr == 0; }
constraint c_nrd  { (opcode == 8'hEE) -> nread inside {[1:48]};
                    (opcode == 8'h05) -> nread == 2;
                    (opcode == 8'h9F) -> nread inside {[3:6]};
                    !(opcode inside {8'hEE, 8'h05, 8'h9F}) -> nread == 0; }
""",
    tr_functions="""
function bit has_addr(); return !(opcode inside {8'h06, 8'h04}); endfunction
function bit is_read(); return opcode inside {8'h05, 8'h9F, 8'hEE}; endfunction

// Page Program data from len / seed (no queue constraint for the solver)
function void post_randomize();
  bit [31:0] x = seed | 1;
  wdata.delete();
  if (opcode == 8'h12)
    for (int i = 0; i <= len; i++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      wdata.push_back(x[7:0]);
    end
endfunction
""",
    drv_rsp=True,
    drv_desc="one 8D-8D-8D transfer per item: command, extension, address, dummy and data beats; device bytes taken on DS edges",
    drv_idle="""
vif.drv_cb.cs_n    <= 1'b1;
vif.drv_cb.ck      <= 1'b0;
vif.drv_cb.dq_m    <= '0;
vif.drv_cb.dq_m_oe <= 1'b0;
""",
    drv_tasks="""
// one beat: toggle CK, drive (oe) or release DQ
task beat(bit oe, bit [7:0] d);
  vif.drv_cb.ck      <= !vif.drv_cb.ck;
  vif.drv_cb.dq_m_oe <= oe;
  vif.drv_cb.dq_m    <= oe ? d : 8'h0;
  @(vif.drv_cb);
endtask
""",
    drv_item="""
bit [7:0] hb[$];
bit ds_p;
hb.push_back(t.opcode);
hb.push_back(~t.opcode ^ {7'h0, t.bad_ext});
if (t.has_addr()) for (int i = 3; i >= 0; i--) hb.push_back(t.addr[8*i +: 8]);
foreach (t.wdata[i]) hb.push_back(t.wdata[i]);
t.rdata.delete();
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b0;
@(vif.drv_cb);
foreach (hb[i]) beat(1'b1, hb[i]);
if (t.is_read()) begin
  ds_p = vif.drv_cb.ds;
  for (int i = 0; i < XSPI_DUMMY + t.nread; i++) begin
    beat(1'b0, 8'h0);
    if (vif.drv_cb.ds != ds_p) t.rdata.push_back(vif.drv_cb.dq_s);
    ds_p = vif.drv_cb.ds;
  end
  // the device answers a beat on the following clock: collect the last
  // bytes with CS# still low and CK stopped
  repeat (3) begin
    @(vif.drv_cb);
    if (vif.drv_cb.ds != ds_p) t.rdata.push_back(vif.drv_cb.dq_s);
    ds_p = vif.drv_cb.ds;
  end
end
vif.drv_cb.dq_m_oe <= 1'b0;
vif.drv_cb.cs_n <= 1'b1;
repeat (2) @(vif.drv_cb);
""",
    mon_desc="transfers between CS# fall and rise: host bytes on CK edges with dq_m_oe, device bytes on DS edges",
    mon_run="""
bit [7:0] hb[$], db[$];
int unsigned rbeats = 0;
bit ck_p = 0, ds_p = 0, cs_p = 1;
forever begin
  @(vif.mon_cb);
  if (!vif.mon_cb.cs_n) begin
    if (cs_p) begin hb.delete(); db.delete(); rbeats = 0; end
    if (vif.mon_cb.ck != ck_p) begin
      if (vif.mon_cb.dq_m_oe) hb.push_back(vif.mon_cb.dq_m);
      else rbeats++;
    end
  end
  if (vif.mon_cb.ds != ds_p) begin
    if (!vif.mon_cb.dq_s_oe) `uvm_error("MON", "xSPI: DS edge without the device driving DQ")
    db.push_back(vif.mon_cb.dq_s);
  end
  if (vif.mon_cb.cs_n && !cs_p) build(hb, db, rbeats);
  ck_p = vif.mon_cb.ck; ds_p = vif.mon_cb.ds; cs_p = vif.mon_cb.cs_n;
end
""",
    mon_tasks="""
function void build(bit [7:0] hb[$], bit [7:0] db[$], int unsigned rbeats);
  xspi_transaction t = xspi_transaction::type_id::create("t");
  int n = 2;
  if (hb.size() < 2) begin
    `uvm_error("MON", $sformatf("xSPI: transfer with %0d command beats", hb.size()))
    return;
  end
  t.opcode  = hb[0];
  t.bad_ext = (hb[1] != ~hb[0]);
  if (t.has_addr()) begin
    for (int i = 0; i < 4; i++) t.addr = {t.addr[23:0], hb[2 + i]};
    n = 6;
  end
  for (int i = n; i < hb.size(); i++) t.wdata.push_back(hb[i]);
  t.nread = (rbeats > XSPI_DUMMY) ? rbeats - XSPI_DUMMY : 0;
  foreach (db[i]) t.rdata.push_back(db[i]);
  publish(t);
endfunction
""",
    sb_members="""bit [7:0] mem [XSPI_MEM];
bit wel = 0, pending = 0, erased = 0;""",
    predict="""
// independent NOR flash model (no timing: WIP comes from the observed status)
bit ok = !t.bad_ext && t.opcode inside {8'h06, 8'h04, 8'h05, 8'h9F, 8'hEE, 8'h12, 8'h21};
bit [7:0] obs[$] = t.rdata;
t.rdata.delete();
if (!erased) begin foreach (mem[i]) mem[i] = 8'hFF; erased = 1; end   // blank part
if (ok && pending && t.opcode != 8'h05) ok = 0;          // busy: only RDSR
if (ok) case (t.opcode)
  8'h06: wel = 1;
  8'h04: wel = 0;
  8'h05: begin
    // WIP is timing: accept 1 only while a program / erase is pending
    bit wip = (obs.size() > 0) ? obs[0][0] : 1'b0;
    if (wip && !pending) wip = 0;
    if (!wip && pending) begin pending = 0; wel = 0; end
    repeat (t.nread) t.rdata.push_back({6'h0, wel, wip});
  end
  8'h9F: for (int i = 0; i < t.nread; i++) t.rdata.push_back(i % 3 == 0 ? 8'h5A : i % 3 == 1 ? 8'h81 : 8'h1A);
  8'hEE: for (int i = 0; i < t.nread; i++) t.rdata.push_back(mem[(t.addr + i) % XSPI_MEM]);
  8'h12: if (wel && t.wdata.size() > 0) begin
    foreach (t.wdata[i]) begin
      int a = {t.addr[12:8], 8'(t.addr[7:0] + i)};
      mem[a] &= t.wdata[i];
    end
    pending = 1;
  end
  8'h21: if (wel) begin
    for (int i = 0; i < 4096; i++) mem[{t.addr[12], 12'(i)}] = 8'hFF;
    pending = 1;
  end
endcase
""",
    checks="""
if (t.is_read() && !t.bad_ext && t.rdata.size() != t.nread)
  fail(t, $sformatf("device drove %0d bytes for %0d read beats", t.rdata.size(), t.nread));
if (t.bad_ext && t.rdata.size() != 0) fail(t, "device answered a command with a wrong extension");
if (t.has_addr() && t.addr >= XSPI_MEM && t.opcode inside {8'hEE, 8'h12, 8'h21})
  fail(t, "address beyond the array");
""",
    coverage="""
cp_op   : coverpoint tr.opcode { bins wren = {8'h06}; bins wrdi = {8'h04}; bins rdsr = {8'h05};
                                 bins rdid = {8'h9F}; bins rd = {8'hEE}; bins pp = {8'h12};
                                 bins se = {8'h21}; bins unknown = default; }
cp_ext  : coverpoint tr.bad_ext;
cp_wrap : coverpoint (tr.opcode == 8'h12 && tr.addr[7:0] + tr.wdata.size() > 256) { bins wrap = {1}; }
cp_rlen : coverpoint tr.nread { bins none = {0}; bins short_ = {[1:4]}; bins long_ = {[5:$]}; }
x_op_ext : cross cp_op, cp_ext;
""",
    seq_tasks="""
// poll RDSR until the program / erase ends (WIP = 0)
task wait_ready();
  xspi_transaction s;
  int n = 0;
  do begin
    s = xspi_transaction::type_id::create("rdsr");
    s.opcode = 8'h05; s.nread = 2;
    start_item(s); finish_item(s);
    n++;
  end while (s.rdata.size() > 0 && s.rdata[0][0] && n < 50);
endtask
""",
    seq_post="if (!req.bad_ext && req.opcode inside {8'h12, 8'h21}) wait_ready();",
    directed="""
// ID, status, erased array
t = item(); t.opcode = 8'h9F; t.nread = 6; send(t);
t = item(); t.opcode = 8'h05; t.nread = 2; send(t);
t = item(); t.opcode = 8'hEE; t.addr = 32'h100; t.nread = 8; send(t);
// program without WEL is ignored
t = item(); t.opcode = 8'h12; t.addr = 32'h100; t.wdata = '{8'h00, 8'h11}; send(t);
t = item(); t.opcode = 8'hEE; t.addr = 32'h100; t.nread = 2; send(t);
// WREN, program across the page end (wraps to the page start), poll, read
t = item(); t.opcode = 8'h06; send(t);
t = item(); t.opcode = 8'h05; t.nread = 2; send(t);
t = item(); t.opcode = 8'h12; t.addr = 32'h1FC; t.wdata = '{8'hA1, 8'hA2, 8'hA3, 8'hA4, 8'hA5, 8'hA6}; send(t);
wait_ready();
t = item(); t.opcode = 8'hEE; t.addr = 32'h1F8; t.nread = 8; send(t);
t = item(); t.opcode = 8'hEE; t.addr = 32'h100; t.nread = 4; send(t);
// NOR: a second program only clears bits
t = item(); t.opcode = 8'h06; send(t);
t = item(); t.opcode = 8'h12; t.addr = 32'h1FC; t.wdata = '{8'h0F}; send(t);
wait_ready();
t = item(); t.opcode = 8'hEE; t.addr = 32'h1FC; t.nread = 1; send(t);
// wrong extension and unknown opcode are ignored; WRDI blocks a program
t = item(); t.opcode = 8'h06; t.bad_ext = 1; send(t);
t = item(); t.opcode = 8'h05; t.nread = 2; send(t);
t = item(); t.opcode = 8'hAB; send(t);
t = item(); t.opcode = 8'h06; send(t);
t = item(); t.opcode = 8'h04; send(t);
t = item(); t.opcode = 8'h12; t.addr = 32'h0; t.wdata = '{8'h00}; send(t);
t = item(); t.opcode = 8'hEE; t.addr = 32'h0; t.nread = 1; send(t);
// sector erase of the upper sector, then read across the sector boundary and the array wrap
t = item(); t.opcode = 8'h06; send(t);
t = item(); t.opcode = 8'h12; t.addr = 32'h1FFE; t.wdata = '{8'h12, 8'h34}; send(t);
wait_ready();
t = item(); t.opcode = 8'hEE; t.addr = 32'h1FFE; t.nread = 4; send(t);
t = item(); t.opcode = 8'h06; send(t);
t = item(); t.opcode = 8'h21; t.addr = 32'h1000; send(t);
wait_ready();
t = item(); t.opcode = 8'hEE; t.addr = 32'h0FFC; t.nread = 8; send(t);
t = item(); t.opcode = 8'hEE; t.addr = 32'h1FFE; t.nread = 4; send(t);
""",
    drain_ns=1000,
    model="""
module xspi_model (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       cs_n,
  input  logic       ck,
  input  logic [7:0] dq_m,
  input  logic       dq_m_oe,
  output logic [7:0] dq_s,
  output logic       dq_s_oe,
  output logic       ds
);
  localparam int DUMMY = 16;
  logic [7:0]  mem [0:8191];
  logic [7:0]  pbuf [0:255];
  logic [255:0] pmask;
  logic [7:0]  op;
  logic        ext_ok, wel, cs_p, ck_p, rd;
  logic [31:0] addr, paddr;    // transfer address, program / erase address
  logic [8:0]  nb;            // host beats (command, extension, address, data)
  logic [7:0]  dcnt, rcnt;    // dummy beats, read beats
  logic [7:0]  busy;          // WIP countdown
  logic [1:0]  pend;          // 1 = program, 2 = erase after busy

  wire wip  = (busy != 0);
  wire edge_ = !cs_n && (ck != ck_p);
  wire addr_cmd = !(op == 8'h06 || op == 8'h04);

  function automatic logic [7:0] rd_byte(input logic [7:0] o, input logic [31:0] a, input logic [7:0] i);
    case (o)
      8'h05: rd_byte = {6'h0, wel, wip};
      8'h9F: rd_byte = (i % 3 == 0) ? 8'h5A : (i % 3 == 1) ? 8'h81 : 8'h1A;
      default: rd_byte = mem[(a + i) & 32'h1FFF];
    endcase
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < 8192; i++) mem[i] <= 8'hFF;
      for (int i = 0; i < 256; i++) pbuf[i] <= 8'hFF;
      pmask <= '0; paddr <= '0; op <= '0; ext_ok <= 1'b0; wel <= 1'b0; cs_p <= 1'b1; ck_p <= 1'b0; rd <= 1'b0;
      addr <= '0; nb <= '0; dcnt <= '0; rcnt <= '0; busy <= '0; pend <= '0;
      dq_s <= '0; dq_s_oe <= 1'b0; ds <= 1'b0;
    end else begin
      cs_p <= cs_n; ck_p <= ck;
      if (busy != 0) begin
        busy <= busy - 8'd1;
        if (busy == 8'd1) begin
          wel <= 1'b0;
          if (pend == 2'd1) begin
            for (int i = 0; i < 256; i++)
              if (pmask[i]) mem[{paddr[12:8], 8'(i)}] <= mem[{paddr[12:8], 8'(i)}] & pbuf[i];
          end else if (pend == 2'd2)
            for (int i = 0; i < 4096; i++) mem[{paddr[12], 12'(i)}] <= 8'hFF;
          pend <= '0;
          pmask <= '0;
        end
      end
      if (!cs_n && cs_p) begin                     // CS# fall: new transfer
        nb <= '0; dcnt <= '0; rcnt <= '0; rd <= 1'b0;
        if (!wip) pmask <= '0;                     // keep a pending program's data
      end
      if (edge_ && dq_m_oe) begin                  // host beat
        nb <= nb + 9'd1;
        if (nb == 9'd0) op <= dq_m;
        else if (nb == 9'd1) ext_ok <= (dq_m == ~op);
        else if (nb < 9'd6 && addr_cmd) addr <= {addr[23:0], dq_m};
        else if (op == 8'h12 && ext_ok && wel && !wip) begin
          logic [7:0] col;
          col = addr[7:0] + 8'(nb - 9'd6);
          pbuf[col] <= pmask[col] ? (pbuf[col] & dq_m) : dq_m;
          pmask[col] <= 1'b1;
        end
      end else if (edge_ && !dq_m_oe) begin        // dummy / read beat
        if (ext_ok && (op == 8'h05 || ((op == 8'h9F || op == 8'hEE) && !wip))) begin
          if (dcnt < DUMMY[7:0]) dcnt <= dcnt + 8'd1;
          else begin
            dq_s <= rd_byte(op, addr, rcnt);
            dq_s_oe <= 1'b1;
            ds <= !ds;
            rcnt <= rcnt + 8'd1;
          end
        end
      end
      if (cs_n) dq_s_oe <= 1'b0;
      if (cs_n && !cs_p && ext_ok) begin           // CS# rise: execute
        if (op == 8'h06 && !wip) wel <= 1'b1;
        else if (op == 8'h04 && !wip) wel <= 1'b0;
        else if (op == 8'h12 && wel && !wip && nb > 9'd6) begin busy <= 8'd60; pend <= 2'd1; paddr <= addr; end
        else if (op == 8'h21 && wel && !wip && nb >= 9'd6) begin busy <= 8'd120; pend <= 2'd2; paddr <= addr; end
      end
    end
  end
endmodule
""",
    sva="""
// device outputs never X out of reset
assert property (@(posedge clk) disable iff (!rst_n) !$isunknown({dq_s_oe, ds}))
  else $error("xSPI: X on device outputs");
// the device drives DQ only while selected, and never while the host drives it
assert property (@(posedge clk) disable iff (!rst_n) dq_s_oe |-> !$past(cs_n))
  else $error("xSPI: device drives DQ while deselected");
assert property (@(posedge clk) disable iff (!rst_n) !(dq_s_oe && dq_m_oe))
  else $error("xSPI: DQ driven by host and device at once");
// a DS edge comes with valid data and only in a selected transfer
assert property (@(posedge clk) disable iff (!rst_n) $changed(ds) |-> dq_s_oe && !$isunknown(dq_s))
  else $error("xSPI: DS edge without valid read data");
// CK only toggles while selected
assert property (@(posedge clk) disable iff (!rst_n) cs_n && $past(cs_n) |-> $stable(ck))
  else $error("xSPI: CK toggles while CS# is high");
cover property (@(posedge clk) disable iff (!rst_n) $changed(ds));
cover property (@(posedge clk) disable iff (!rst_n) $rose(cs_n));
""",
    smoke="""
int checks = 0;
int fails  = 0;

logic clk = 1'b0;
logic rst_n = 1'b0;
logic cs_n = 1, ck = 0, dq_m_oe = 0;
logic [7:0] dq_m = 0;
wire [7:0] dq_s;
wire dq_s_oe, ds;

always #5 clk = ~clk;

xspi_model u_dut (.clk(clk), .rst_n(rst_n), .cs_n(cs_n), .ck(ck), .dq_m(dq_m), .dq_m_oe(dq_m_oe),
                  .dq_s(dq_s), .dq_s_oe(dq_s_oe), .ds(ds));

task automatic chk(input bit ok, input string msg);
  checks++;
  if (!ok) begin fails++; $display("  [FAIL] %s", msg); end
endtask

task automatic bt(input logic oe, input logic [7:0] d);
  @(negedge clk); ck = !ck; dq_m_oe = oe; dq_m = d;
endtask

// command [+ address] [+ data] [+ dummy and n read bytes]; returns read bytes
logic [7:0] rbuf [0:15];
task automatic xfer(input logic [7:0] op, input logic hasaddr, input logic [31:0] a,
                    input int nw, input logic [7:0] w0, input int nr);
  logic dsp;
  int k;
  @(negedge clk); cs_n = 0;
  bt(1, op); bt(1, ~op);
  if (hasaddr) for (int i = 3; i >= 0; i--) bt(1, a[8*i +: 8]);
  for (int i = 0; i < nw; i++) bt(1, w0 + 8'(i));
  k = 0; dsp = ds;
  if (nr > 0) for (int i = 0; i < 16 + nr + 2; i++) begin
    if (i < 16 + nr) bt(0, 0); else @(negedge clk);
    if (ds != dsp && k < 16) begin rbuf[k] = dq_s; k++; end
    dsp = ds;
  end
  @(negedge clk); dq_m_oe = 0; cs_n = 1;
  repeat (2) @(negedge clk);
endtask

task automatic wait_ready;
  int n = 0;
  do begin xfer(8'h05, 1, 0, 0, 0, 1); n++; end while (rbuf[0][0] && n < 20);
  chk(rbuf[0][0] === 1'b0, "WIP clears");
endtask

initial begin
  repeat (3) @(posedge clk);
  chk(dq_s_oe === 1'b0, "DQ released in reset");
  rst_n = 1;
  repeat (3) @(posedge clk);

  xfer(8'h9F, 1, 0, 0, 0, 7);
  chk(rbuf[0] === 8'h5A && rbuf[1] === 8'h81 && rbuf[2] === 8'h1A, "RDID");
  chk(rbuf[3] === 8'h5A && rbuf[4] === 8'h81 && rbuf[5] === 8'h1A && rbuf[6] === 8'h5A, "RDID repeats every 3 bytes");
  xfer(8'hEE, 1, 32'h40, 0, 0, 2);
  chk(rbuf[0] === 8'hFF && rbuf[1] === 8'hFF, "erased array reads 0xFF");
  xfer(8'h12, 1, 32'h40, 2, 8'h10, 0);                    // no WEL
  xfer(8'hEE, 1, 32'h40, 0, 0, 1);
  chk(rbuf[0] === 8'hFF, "program without WEL ignored");
  xfer(8'h06, 0, 0, 0, 0, 0);
  xfer(8'h05, 1, 0, 0, 0, 1);
  chk(rbuf[0] === 8'h02, "WREN sets WEL");
  xfer(8'h12, 1, 32'h40, 3, 8'h10, 0);
  xfer(8'h05, 1, 0, 0, 0, 1);
  chk(rbuf[0] === 8'h03, "WIP and WEL while programming");
  wait_ready();
  xfer(8'h05, 1, 0, 0, 0, 1);
  chk(rbuf[0] === 8'h00, "WEL cleared after program");
  xfer(8'hEE, 1, 32'h40, 0, 0, 4);
  chk(rbuf[0] === 8'h10 && rbuf[1] === 8'h11 && rbuf[2] === 8'h12 && rbuf[3] === 8'hFF, "programmed bytes read back");
  xfer(8'hEE, 1, 32'h3F, 0, 0, 2);
  chk(rbuf[0] === 8'hFF && rbuf[1] === 8'h10, "read from another address");
  // a program issued while busy is ignored (data and mask untouched)
  xfer(8'h06, 0, 0, 0, 0, 0);
  xfer(8'h12, 1, 32'h48, 2, 8'hF0, 0);
  xfer(8'h12, 1, 32'h48, 2, 8'h00, 0);
  wait_ready();
  xfer(8'hEE, 1, 32'h48, 0, 0, 2);
  chk(rbuf[0] === 8'hF0 && rbuf[1] === 8'hF1, "program while WIP ignored");
  // WRDI clears WEL: the following program does nothing
  xfer(8'h06, 0, 0, 0, 0, 0);
  xfer(8'h04, 0, 0, 0, 0, 0);
  xfer(8'h05, 1, 0, 0, 0, 1);
  chk(rbuf[0] === 8'h00, "WRDI clears WEL");
  xfer(8'h12, 1, 32'h50, 1, 8'h00, 0);
  xfer(8'hEE, 1, 32'h50, 0, 0, 1);
  chk(rbuf[0] === 8'hFF, "program after WRDI ignored");
  xfer(8'h06, 0, 0, 0, 0, 0);
  xfer(8'h21, 1, 32'h0, 0, 0, 0);
  wait_ready();
  xfer(8'hEE, 1, 32'h40, 0, 0, 1);
  chk(rbuf[0] === 8'hFF, "sector erase");
  // wrong extension: no response
  @(negedge clk); cs_n = 0; bt(1, 8'h9F); bt(1, 8'h9F);
  for (int i = 0; i < 4; i++) bt(1, 0);
  begin
    logic dsp; dsp = ds;
    repeat (20) bt(0, 0);
    chk(ds === dsp && dq_s_oe === 1'b0, "wrong command extension ignored");
  end
  @(negedge clk); cs_n = 1;

  if (fails == 0) $display("FUNC_PASS checks=%0d", checks);
  else            $display("FUNC_FAIL checks=%0d fails=%0d", checks, fails);
  $finish;
end

initial begin
  #500000;
  $display("FUNC_FAIL timeout");
  $finish;
end
""",
)
