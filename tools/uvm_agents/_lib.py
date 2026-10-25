# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared SystemVerilog snippets for the tools/uvm_agents specs."""


def wait_cb(cond, what, cb="vif.drv_cb"):
    """Wait (clocked on ``cb``) until ``cond`` holds; error after
    cfg.timeout_cycles clocks."""
    return """begin
  int unsigned to = 0;
  do begin @({cb}); to++; end while (!({cond}) && to < cfg.timeout_cycles);
  if (!({cond})) `uvm_error("TIMEOUT", $sformatf("{what}: no response within %0d cycles", cfg.timeout_cycles))
end""".format(cond=cond, what=what, cb=cb)


# Ethernet helpers for transactions with a ``bytes`` queue holding one MAC
# frame (destination address .. FCS, after preamble/SFD).
ETH_FUNCS = """
// IEEE 802.3 CRC-32 (reflected 0xEDB88320, init/final xor all ones)
function bit [31:0] crc32(bit [7:0] b[$], int unsigned n);
  bit [31:0] c = 32'hFFFF_FFFF;
  for (int unsigned i = 0; i < n; i++) begin
    c ^= {24'h0, b[i]};
    for (int k = 0; k < 8; k++) c = c[0] ? (c >> 1) ^ 32'hEDB8_8320 : (c >> 1);
  end
  return ~c;
endfunction

// destination/source address, length/type, payload from seed, FCS
function void build_frame(int unsigned payload_len, bit [31:0] seed, bit [15:0] etype);
  bit [31:0] x = seed | 32'h1;
  bit [31:0] fcs;
  bytes.delete();
  for (int i = 0; i < 6; i++) bytes.push_back(8'hFF);                 // broadcast
  for (int i = 0; i < 6; i++) bytes.push_back(i == 0 ? 8'h02 : 8'(seed >> (i * 4)));
  bytes.push_back(etype[15:8]);
  bytes.push_back(etype[7:0]);
  for (int unsigned i = 0; i < payload_len; i++) begin
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    bytes.push_back(x[7:0]);
  end
  fcs = crc32(bytes, bytes.size());
  for (int i = 0; i < 4; i++) bytes.push_back(fcs[i*8 +: 8]);       // LSB first
endfunction

// FCS of a received frame (last four bytes) is correct
function bit fcs_ok();
  bit [31:0] fcs;
  if (bytes.size() < 18) return 0;
  fcs = crc32(bytes, bytes.size() - 4);
  for (int i = 0; i < 4; i++) if (bytes[bytes.size() - 4 + i] != fcs[i*8 +: 8]) return 0;
  return 1;
endfunction
"""


def dram_spec(vip, p, P, dw, rl, sel, sref=False):
    """DRAM-style command/data agent shared by DDR5 / HBM3E / LPDDR6
    (tb/top_tb.sv <p>_model: ACT is ignored, RD/WR when !cs_n && act_n with
    addr[0] = 1 for a read, column = addr[13:1], read data returns with
    rd_valid a fixed number of clocks later). ``sel``: (decl, field, pin)
    selecting the bank / stack / pseudo-channel."""
    key = "{" + ", ".join("t." + f for _, f, _ in sel) + ", t.col}"
    selfields = [(d, f, "req") for d, f, _ in sel]
    fields = [("bit", "write", "req")] + selfields + [
        ("bit [12:0]", "col", "req"),
        ("bit [%d:0]" % (dw - 1), "wdata", "req"),
        ("bit [%d:0]" % (dw - 1), "rdata", "rsp"),
        ("bit [13:0]", "row", "info", "rand"),
        ("int unsigned", "rl", "info"),
    ]
    if sref:
        fields.insert(0, ("bit", "sref", "req"))
        fields.insert(1, ("bit [4:0]", "sref_cycles", "req"))
    keyw = sum(int(d.split("[")[1].split(":")[0]) + 1 if "[" in d else 1 for d, _, _ in sel) + 13
    drive_sel = " ".join("vif.drv_cb.%s <= t.%s;" % (pin, f) for _, f, pin in sel)
    idle_sel = " ".join("vif.drv_cb.%s <= '0;" % pin for _, _, pin in sel)
    mon_sel = "\n".join("t.%s = vif.mon_cb.%s;" % (f, pin) for _, f, pin in sel)
    cmd = """// ACTIVATE (ignored by the model; keeps the command stream realistic)
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b0; vif.drv_cb.act_n <= 1'b0; {sel} vif.drv_cb.addr <= t.row;
// READ (addr[0] = 1) / WRITE (addr[0] = 0) to column addr[13:1]
@(vif.drv_cb);
vif.drv_cb.act_n <= 1'b1;
vif.drv_cb.addr  <= {{t.col, !t.write}};
vif.drv_cb.wr_data <= t.write ? t.wdata : '0;
@(vif.drv_cb);
vif.drv_cb.cs_n <= 1'b1;
vif.drv_cb.wr_data <= '0;
if (!t.write) begin
  int unsigned n = 0;
  do begin @(vif.drv_cb); n++; end while (vif.drv_cb.rd_valid !== 1'b1 && n < cfg.timeout_cycles);
  if (vif.drv_cb.rd_valid !== 1'b1) `uvm_error("TIMEOUT", "{P}: no rd_valid for read")
  t.rdata = vif.drv_cb.rd_data;
  t.rl = n;
end""".format(sel=drive_sel, P=P)
    if sref:
        item = """if (t.sref) begin
  @(vif.drv_cb);
  vif.drv_cb.self_ref <= 1'b1;
  repeat (t.sref_cycles) @(vif.drv_cb);
  vif.drv_cb.self_ref <= 1'b0;
  @(vif.drv_cb);
end else begin
""" + "\n".join("  " + l for l in cmd.splitlines()) + "\nend"
    else:
        item = cmd
    mon = """{p}_transaction pend[$];
int unsigned age[$];
{sref_decl}forever begin
  @(vif.mon_cb);
  foreach (age[i]) age[i]++;
  if (vif.mon_cb.rd_valid) begin
    if (pend.size() == 0) `uvm_error("MON", "{P}: rd_valid without an outstanding read")
    else begin
      {p}_transaction t = pend.pop_front();
      t.rl = age.pop_front();
      t.rdata = vif.mon_cb.rd_data;
      publish(t);
    end
  end
{sref_body}  if ({cmd_cond}!vif.mon_cb.cs_n && vif.mon_cb.act_n) begin
    {p}_transaction t = {p}_transaction::type_id::create("t");
    t.write = !vif.mon_cb.addr[0];
    t.col   = vif.mon_cb.addr[13:1];
{mon_sel}
    if (t.write) begin
      t.wdata = vif.mon_cb.wr_data;
      publish(t);
    end else begin
      pend.push_back(t);
      age.push_back(0);
    end
  end
end""".format(p=p, P=P, mon_sel="\n".join("    " + l for l in mon_sel.splitlines()),
              sref_decl="int unsigned sref_n = 0;\n" if sref else "",
              sref_body="""  if (vif.mon_cb.self_ref) sref_n++;
  else if (sref_n != 0) begin
    {p}_transaction t = {p}_transaction::type_id::create("t");
    t.sref = 1; t.sref_cycles = sref_n; sref_n = 0;
    publish(t);
  end
""".format(p=p) if sref else "",
              cmd_cond="!vif.mon_cb.self_ref && " if sref else "")
    predict = """if ({s}t.write) begin
  mem[{key}] = t.wdata;
  t.rdata = 0;
end else
  t.rdata = mem.exists({key}) ? mem[{key}] : '0;   // the model's array starts at 0""".format(
        key=key, s="!t.sref && " if sref else "")
    if sref:
        predict = "if (t.sref) t.rdata = 0;   // self-refresh keeps the array contents\nelse " + predict
    # The command fields of a self-refresh item are cleared in post_randomize
    # rather than by a constraint: Verilator picks a dist range before solving,
    # so "sref -> col == 0" against the c_col dist is sometimes unsatisfiable.
    sref_cons = "constraint c_sref { sref dist { 0 := 12, 1 := 1 }; sref_cycles inside {[2:20]}; }\n" if sref else ""
    sref_post = """function void post_randomize();
  if (!sref) sref_cycles = 0;   // the monitor reports 0 outside self-refresh
  else begin
    write = 0; wdata = 0; col = 0;%s
  end
endfunction
""" % "".join(" %s = 0;" % f for _, f, _ in sel) if sref else ""
    dir_sref = """// self-refresh between a write and its read-back: contents retained
t = item(); t.write = 1; t.col = 13'h0AA; t.wdata = '1; send(t);
t = item(); t.sref = 1; t.sref_cycles = 12; send(t);
t = item(); t.col = 13'h0AA; send(t);
t = item(); t.sref = 1; t.sref_cycles = 2; send(t);
""" if sref else ""
    first = sel[0][1]
    return dict(
        vip=vip, p=p, P=P, dir=p,
        cfg="int unsigned read_latency = %d;   // clocks from the RD command to rd_valid" % rl,
        fields=fields,
        tr_functions=sref_post,
        constraints=sref_cons + "constraint c_data { !write -> wdata == 0; }\n" +
                    "constraint c_col  { col dist { [0:15] := 2, [16:8190] := 1, 8191 := 1 }; }\n",
        drv_desc="ACT then one RD/WR command; reads wait for rd_valid",
        drv_idle="vif.drv_cb.cs_n <= 1'b1; vif.drv_cb.act_n <= 1'b1; vif.drv_cb.addr <= '0; vif.drv_cb.wr_data <= '0; " + idle_sel +
                 (" vif.drv_cb.self_ref <= 1'b0;" if sref else ""),
        drv_item=item,
        mon_desc="decodes RD/WR commands, pairs reads with rd_valid in order",
        mon_run=mon,
        sb_members="bit [%d:0] mem [bit [%d:0]];   // written locations" % (dw - 1, keyw - 1),
        predict=predict,
        checks="""if ({c}!t.write && t.rl != cfg.read_latency)
  fail(t, $sformatf("read latency %0d clocks, expected %0d", t.rl, cfg.read_latency));""".format(
            c="!t.sref && " if sref else ""),
        coverage="""cp_write : coverpoint tr.write;
cp_{f}  : coverpoint tr.{f};
cp_col   : coverpoint tr.col {{ bins low = {{[0:15]}}; bins mid = {{[16:8190]}}; bins top = {{8191}}; }}
x_wr_{f} : cross cp_write, cp_{f};""".format(f=first) + ("\ncp_sref  : coverpoint tr.sref;" if sref else ""),
        directed="""// each {f}: write then read back; an unwritten location reads 0
for (int b = 0; b < 4; b++) begin
  t = item(); t.write = 1; t.{f} = b; t.col = 13'h10 + b; t.wdata = {{{rep}{{32'hD0D0_0000 | b}}}}; send(t);
  t = item(); t.{f} = b; t.col = 13'h10 + b; send(t);
end
t = item(); t.col = 13'h1234; send(t);
// overwrite, top column, back-to-back writes then reads
t = item(); t.write = 1; t.col = 13'h1FFF; t.wdata = '1; send(t);
t = item(); t.write = 1; t.col = 13'h1FFF; t.wdata = {{{rep}{{32'h0123_4567}}}}; send(t);
t = item(); t.col = 13'h1FFF; send(t);
for (int i = 0; i < 4; i++) begin t = item(); t.write = 1; t.col = i; t.wdata = i + 1; send(t); end
for (int i = 0; i < 4; i++) begin t = item(); t.col = i; send(t); end
""".format(f=first, rep=dw // 32) + dir_sref,
    )


# xorshift32 fill of a queue ``q`` of ``n`` elements of width ``w`` from ``seed``
def fill_fn(q, w, n="n", seed="seed"):
    return """function void fill_{q}(int unsigned {n});
  bit [31:0] x = {seed} | 32'h1;
  {q}.delete();
  for (int unsigned i = 0; i < {n}; i++) begin
    bit [{w1}:0] v;
    for (int k = 0; k < {words}; k++) begin
      x ^= x << 13; x ^= x >> 17; x ^= x << 5;
      v = (v << 32) | {w}'(x);
    end
    {q}.push_back(v);
  end
endfunction""".format(q=q, n=n, seed=seed, w=w, w1=w - 1, words=max(1, (w + 31) // 32))


def eth_spec(vip, p, P, lane, tx, rx, er=None, extra=None):
    """MII-family loopback agent: frame bytes (preamble, SFD, MAC frame) go
    out on ``tx`` = (data, enable[, error]) pins ``lane`` bits per clock, low
    nibble first for 4-bit lanes; the DUT model returns them on ``rx``.
    ``er``: (tx_er, rx_er) pins or None. ``extra``: dict merged into the spec."""
    td, ten = tx[0], tx[1]
    rd, ren = rx[0], rx[1]
    nib = lane == 4
    fields = [
        ("bit [7:0]", "bytes", "req", "q"),      # MAC frame: DA .. FCS (after preamble/SFD)
        ("bit", "preamble_ok", "req", "norand"),
        ("bit [7:0]", "out_bytes", "rsp", "q"),
        ("bit", "out_preamble_ok", "rsp"),
        ("bit [6:0]", "plen", "info", "rand"),
        ("bit [31:0]", "seed", "info", "rand"),
    ]
    if er:
        fields.insert(2, ("bit", "inject_er", "req"))
        fields.insert(5, ("bit", "out_er", "rsp"))
    words = ("for (int i = 0; i < 7; i++) line.push_back(8'h55);\n"
             "line.push_back(8'hD5);\n"
             "foreach (t.bytes[i]) line.push_back(t.bytes[i]);")
    if nib:
        put = """foreach (line[i]) for (int h = 0; h < 2; h++) begin
  vif.drv_cb.{td} <= h ? line[i][7:4] : line[i][3:0];
  vif.drv_cb.{ten} <= 1'b1;
{erput}  @(vif.drv_cb);
end"""
    else:
        put = """foreach (line[i]) begin
  vif.drv_cb.{td} <= line[i];
  vif.drv_cb.{ten} <= 1'b1;
{erput}  @(vif.drv_cb);
end"""
    erput = ("  vif.drv_cb.%s <= t.inject_er && (i == line.size() / 2);\n" % er[0]) if er else ""
    put = put.format(td=td, ten=ten, erput=erput)
    item = """bit [7:0] line[$];
@(vif.drv_cb);
{words}
{put}
vif.drv_cb.{ten} <= 1'b0;
vif.drv_cb.{td} <= '0;
{erclr}repeat (cfg.ifg_clks) @(vif.drv_cb);
""".format(words=words, put=put, ten=ten, td=td,
           erclr=("vif.drv_cb.%s <= 1'b0;\n" % er[0]) if er else "")
    idle = "vif.drv_cb.%s <= '0; vif.drv_cb.%s <= 1'b0;%s" % (td, ten, (" vif.drv_cb.%s <= 1'b0;" % er[0]) if er else "")

    def side(d, en, e, is_out):
        tgt = "out_bytes" if is_out else "bytes"
        pre = "out_preamble_ok" if is_out else "preamble_ok"
        erf = ("out_er" if is_out else "inject_er") if er else None
        return dict(d=d, en=en, e=e, tgt=tgt, pre=pre, erf=erf)
    sides = [side(td, ten, er[0] if er else None, False), side(rd, ren, er[1] if er else None, True)]
    decl = "\n".join("bit [7:0] l{i}[$];\nbit [3:0] lo{i} = 0;\nbit h{i} = 0, a{i} = 0, e{i} = 0;".format(i=i) for i in range(2))
    body = []
    for i, sd in enumerate(sides):
        get = ("if (!h{i}) begin lo{i} = vif.mon_cb.{d}; h{i} = 1; end\n"
               "    else begin l{i}.push_back({{vif.mon_cb.{d}, lo{i}}}); h{i} = 0; end").format(i=i, **sd) if nib else \
              "l{i}.push_back(vif.mon_cb.{d});".format(i=i, **sd)
        erget = ("    if (vif.mon_cb.%s) e%d = 1;\n" % (sd["e"], i)) if er else ""
        fin = ("if (in_q.size() == 0) `uvm_error(\"MON\", \"%s frame received that was never sent\")\n"
               "      else begin\n"
               "        %s_transaction t = in_q.pop_front();\n"
               "        frame(l1, t, 1);\n%s"
               "        publish(t);\n"
               "      end") % (P, p, ("        t.out_er = e1;\n" if er else "")) if i == 1 else \
              ("begin\n"
               "        %s_transaction t = %s_transaction::type_id::create(\"t\");\n"
               "        frame(l0, t, 0);\n%s"
               "        in_q.push_back(t);\n"
               "      end") % (p, p, ("        t.inject_er = e0;\n" if er else ""))
        body.append("""  if (vif.mon_cb.{en}) begin
    a{i} = 1;
{erget}    {get}
  end else if (a{i}) begin
      {fin}
    l{i}.delete(); a{i} = 0; h{i} = 0; e{i} = 0;
  end""".format(i=i, erget=erget, get=get, fin=fin, **sd))
    mon = decl + "\n" + p + "_transaction in_q[$];\nforever begin\n  @(vif.mon_cb);\n" + "\n".join(reversed(body)) + "\nend"
    spec = dict(
        vip=vip, p=p, P=P, dir=p,
        cfg="int unsigned ifg_clks = %d;   // inter-frame gap" % (24 if nib else 12),
        fields=fields,
        constraints="constraint c_len { plen inside {[46:100]}; }\n" +
                    ("constraint c_er { inject_er dist { 0 := 5, 1 := 1 }; }\n" if er else ""),
        tr_functions=ETH_FUNCS + """
function void post_randomize();
  build_frame(plen, seed, 16'(plen));   // IEEE 802.3 length field
  preamble_ok = 1;
endfunction
""",
        drv_rsp=False,
        drv_desc="preamble, SFD and one MAC frame, then the inter-frame gap",
        drv_idle=idle, drv_item=item,
        mon_desc="frames on the transmit pins paired in order with the looped-back receive frames",
        mon_run=mon,
        mon_tasks="""// split a byte stream into the preamble/SFD check and the frame bytes
// (out = 0: transmit side into bytes, 1: receive side into out_bytes)
function void frame(bit [7:0] l[$], %s_transaction t, bit out);
  bit ok = (l.size() >= 8);
  for (int i = 0; i < 8 && i < l.size(); i++) if (l[i] != ((i == 7) ? 8'hD5 : 8'h55)) ok = 0;
  if (out) begin t.out_preamble_ok = ok; t.out_bytes.delete(); end
  else     begin t.preamble_ok = ok;     t.bytes.delete(); end
  for (int i = 8; i < l.size(); i++)
    if (out) t.out_bytes.push_back(l[i]); else t.bytes.push_back(l[i]);
endfunction""" % p,
        predict="t.out_bytes = t.bytes;\nt.out_preamble_ok = t.preamble_ok;" + ("\nt.out_er = t.inject_er;" if er else ""),
        checks="""if (!t.preamble_ok) fail(t, "bad preamble / SFD");
if (!t.fcs_ok()) fail(t, "frame check sequence error");""",
        coverage="""cp_len : coverpoint tr.bytes.size() { bins min_ = {[64:70]}; bins mid = {[71:100]}; bins long_ = {[101:$]}; }""" +
                 ("\ncp_er  : coverpoint tr.inject_er;" if er else ""),
        directed="""t = item(); t.plen = 46;  t.seed = 32'h1; t.post_randomize(); send(t);   // 64-byte minimum frame
t = item(); t.plen = 100; t.seed = 32'h2; t.post_randomize(); send(t);
""" + ("""t = item(); t.plen = 60; t.seed = 32'h3; t.post_randomize(); t.inject_er = 1; send(t);
""" if er else "") + """for (int i = 0; i < 3; i++) begin t = item(); t.plen = 50 + i; t.seed = 32'h10 + i; t.post_randomize(); send(t); end
""",
    )
    if extra:
        spec.update(extra)
    return spec
