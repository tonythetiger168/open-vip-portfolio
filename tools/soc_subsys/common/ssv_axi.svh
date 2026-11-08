// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_axi.svh -- verification of an IP's AXI4 manager port ("m_" pins):
//
//   axim_txn          one burst as seen on the bus (address phase, every beat,
//                     response, timestamps)
//   axim_cfg          rules the IP promises (max beats, sizes, burst types,
//                     outstanding limits, address windows) and the
//                     subordinate's behaviour (back-pressure, latency, error
//                     regions)
//   axim_subordinate  memory-backed responder: accepts any legal AXI4
//                     traffic (INCR / WRAP / FIXED, narrow, sparse strobes,
//                     write data before or after its address, several
//                     transactions in flight), random READY back-pressure and
//                     response latency, SLVERR / DECERR regions
//   axim_monitor      rebuilds each burst and checks the transaction rules:
//                     TXN_SIZE, TXN_BURST, TXN_LEN, TXN_4K, TXN_ALIGN,
//                     TXN_WLAST, TXN_STRB, TXN_OUTSTANDING, TXN_WINDOW,
//                     TXN_RESP_ID, TXN_RLAST; also turns the interface's
//                     cycle-level checker failures into UVM errors
//   axim_coverage     functional coverage counters (length, size, burst,
//                     response, ID, outstanding depth, back-pressure)
//   axim_agent        subordinate + monitor + coverage
//
// Rule failures are reported with `uvm_error(<rule>, ...); a negative test
// can count them with axim_monitor::rule_count(<rule>).

typedef enum bit [1:0] {AXI_FIXED = 2'b00, AXI_INCR = 2'b01, AXI_WRAP = 2'b10} axim_burst_e;
typedef enum bit [1:0] {AXI_OKAY = 2'b00, AXI_EXOKAY = 2'b01, AXI_SLVERR = 2'b10, AXI_DECERR = 2'b11} axim_resp_e;

class axim_txn extends uvm_sequence_item;
  `uvm_object_utils(axim_txn)
  bit          write;
  bit [3:0]    id;
  bit [31:0]   addr;
  bit [7:0]    len;      // beats - 1
  bit [2:0]    size;     // bytes per beat = 1 << size
  bit [1:0]    burst;
  bit [2:0]    prot;
  bit [31:0]   data[$];
  bit [3:0]    strb[$];
  bit [1:0]    resp[$];  // one per beat (reads) or one (writes)
  time         t_addr, t_done;
  longint unsigned c_addr, c_done;   // clock counts at the address handshake and at completion

  function new(string name = "axim_txn");
    super.new(name);
  endfunction

  function int unsigned beats();
    return int'(len) + 1;
  endfunction

  function int unsigned nbytes();
    return beats() << size;
  endfunction

  // AXI4 A3.4.1: address of beat n (byte address, low bits as on the bus)
  function bit [31:0] beat_addr(int unsigned n);
    bit [31:0] nb = 32'd1 << size;
    bit [31:0] aligned = (addr / nb) * nb;
    if (burst == AXI_FIXED) return addr;
    if (burst == AXI_WRAP) begin
      bit [31:0] wb = nb * beats();
      bit [31:0] lo = (addr / wb) * wb;
      return lo + ((aligned - lo + n * nb) % wb);
    end
    return (n == 0) ? addr : aligned + n * nb;
  endfunction

  // the byte lanes that beat n may use
  function bit [3:0] lane_mask(int unsigned n);
    bit [31:0] a  = beat_addr(n);
    int unsigned nb = 1 << size;
    int unsigned lo = a[1:0];
    int unsigned hi = (a[1:0] & ~(nb - 1)) + nb - 1;   // last lane of the aligned transfer
    bit [3:0] m = 0;
    for (int unsigned b = lo; b <= hi && b < 4; b++) m[b] = 1'b1;
    return m;
  endfunction

  function bit [1:0] worst_resp();
    bit [1:0] w = AXI_OKAY;
    foreach (resp[i]) if (resp[i] > w) w = resp[i];
    return w;
  endfunction

  virtual function string convert2string();
    return $sformatf("%s id=%0d addr=%08h len=%0d size=%0d burst=%0d resp=%0d beats=%0d",
                     write ? "AW" : "AR", id, addr, len, size, burst, worst_resp(), data.size());
  endfunction

  virtual function void do_copy(uvm_object rhs);
    axim_txn r;
    super.do_copy(rhs);
    $cast(r, rhs);
    write = r.write; id = r.id; addr = r.addr; len = r.len; size = r.size; burst = r.burst;
    prot = r.prot; data = r.data; strb = r.strb; resp = r.resp; t_addr = r.t_addr; t_done = r.t_done;
    c_addr = r.c_addr; c_done = r.c_done;
  endfunction
endclass

// an address window [lo, hi) with what is allowed there
class axim_window extends uvm_object;
  `uvm_object_utils(axim_window)
  bit [31:0] lo, hi;
  bit        rd_ok, wr_ok;
  string     tag;
  function new(string name = "axim_window");
    super.new(name);
  endfunction
endclass

class axim_err_region extends uvm_object;
  `uvm_object_utils(axim_err_region)
  bit [31:0] lo, hi;
  bit [1:0]  resp = AXI_SLVERR;
  bit        on_read = 1, on_write = 1;
  function new(string name = "axim_err_region");
    super.new(name);
  endfunction
endclass

class axim_cfg extends uvm_object;
  `uvm_object_utils(axim_cfg)
  // ---- what the manager (the IP) promises; defaults: the subsystem contract
  int unsigned max_beats      = 16;     // TXN_LEN
  bit [7:0]    size_mask      = 8'h04;  // TXN_SIZE: bit s set = size s allowed (default 4 bytes only)
  bit [3:0]    burst_mask     = 4'h2;   // TXN_BURST: bit b set = burst type b allowed (default INCR only)
  bit          require_full_strb = 1;   // TXN_STRB: every write beat strobes all its lanes
  bit          require_aligned   = 1;   // TXN_ALIGN: address aligned to the transfer size
  int unsigned max_out_rd     = 1;      // TXN_OUTSTANDING
  int unsigned max_out_wr     = 1;
  bit          check_windows  = 0;      // TXN_WINDOW: every byte inside a window that allows it
  int          expect_id      = -1;     // TXN_ID: AWID / ARID the IP uses (-1: any)
  int          expect_rd_id   = -1;     // TXN_ID for reads only, when it differs (-1: expect_id)
  axim_window  windows[$];
  // ---- subordinate behaviour
  int unsigned awready_pct = 100, wready_pct = 100, arready_pct = 100;  // READY high per clock, %
  int unsigned bvalid_lat_max = 0, rvalid_lat_max = 0;                  // extra clocks before a response
  int unsigned rbeat_gap_pct = 0;                                        // chance of an idle clock between R beats
  axim_err_region err_regions[$];
  int unsigned resp_timeout = 20000;    // clocks a started burst may take to complete
  // ---- reporting
  string       master_name = "ip";      // LAT lines: "LAT <master> <slave> <R|W> <cycles>"
  string       slave_name  = "mem";
  bit          print_lat   = 1;

  function new(string name = "axim_cfg");
    super.new(name);
  endfunction

  function void set_backpressure(int unsigned pct, int unsigned lat);
    awready_pct = pct; wready_pct = pct; arready_pct = pct;
    bvalid_lat_max = lat; rvalid_lat_max = lat;
    rbeat_gap_pct = (pct >= 100) ? 0 : (100 - pct) / 2;
  endfunction

  function void add_window(bit [31:0] lo, bit [31:0] hi, bit rd_ok, bit wr_ok, string tag = "");
    axim_window w = axim_window::type_id::create("win");
    w.lo = lo; w.hi = hi; w.rd_ok = rd_ok; w.wr_ok = wr_ok; w.tag = tag;
    windows.push_back(w);
  endfunction

  function void clear_windows();
    windows.delete();
  endfunction

  function void add_err_region(bit [31:0] lo, bit [31:0] hi, bit [1:0] resp = AXI_SLVERR,
                               bit on_read = 1, bit on_write = 1);
    axim_err_region e = axim_err_region::type_id::create("err");
    e.lo = lo; e.hi = hi; e.resp = resp; e.on_read = on_read; e.on_write = on_write;
    err_regions.push_back(e);
  endfunction

  function bit [1:0] resp_for(bit [31:0] a, bit write);
    foreach (err_regions[i])
      if (a >= err_regions[i].lo && a < err_regions[i].hi &&
          (write ? err_regions[i].on_write : err_regions[i].on_read))
        return err_regions[i].resp;
    return AXI_OKAY;
  endfunction

  function bit in_window(bit [31:0] a, bit write);
    foreach (windows[i])
      if (a >= windows[i].lo && a < windows[i].hi && (write ? windows[i].wr_ok : windows[i].rd_ok))
        return 1;
    return 0;
  endfunction
endclass

function automatic bit axim_pct(int unsigned pct);
  return (pct >= 100) ? 1'b1 : ($urandom_range(99) < pct);
endfunction

// ----------------------------------------------------------------------------
// Subordinate (responder). One cycle-based process: sample every handshake on
// the rising edge, update the queues, drive the next values on the falling
// edge. Writes commit to memory when both the address and all beats are in,
// in address order (AXI4 has no write interleaving); B responses go out in
// that order after a random latency. Reads are served in address order, one
// burst at a time, beat by beat.
class axim_subordinate extends uvm_component;
  `uvm_component_utils(axim_subordinate)
  virtual axim_if vif;
  axim_cfg cfg;
  ssv_mem  mem;

  typedef struct { bit [3:0] id; bit [31:0] addr; bit [7:0] len; bit [2:0] size; bit [1:0] burst; } addr_t;
  typedef struct { bit [3:0] id; bit [1:0] resp; int unsigned wait_clk; } bresp_t;
  addr_t       aw_q[$], ar_q[$];
  bit [31:0]   wd_q[$];
  bit [3:0]    ws_q[$];
  bresp_t      b_q[$];
  // read burst being returned
  bit          rd_act;
  addr_t       rd_cur;
  int unsigned rd_beat, rd_wait;
  int unsigned n_wr, n_rd;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    if (!uvm_config_db #(virtual axim_if)::get(this, "", "axim_vif", vif))
      `uvm_fatal("NOVIF", "axim_subordinate: axim_vif not set")
  endfunction

  function void idle_outputs();
    vif.awready = 0; vif.wready = 0; vif.arready = 0;
    vif.bvalid = 0; vif.bid = 0; vif.bresp = 0;
    vif.rvalid = 0; vif.rid = 0; vif.rdata = 0; vif.rresp = 0; vif.rlast = 0;
  endfunction

  function void flush();
    aw_q.delete(); ar_q.delete(); wd_q.delete(); ws_q.delete(); b_q.delete();
    rd_act = 0;
  endfunction

  static function bit [31:0] beat_addr(addr_t a, int unsigned n);
    axim_txn t = new();
    t.addr = a.addr; t.len = a.len; t.size = a.size; t.burst = a.burst;
    return t.beat_addr(n);
  endfunction

  function void commit_write(addr_t a);
    bit [1:0] worst = AXI_OKAY;
    bresp_t b;
    for (int unsigned n = 0; n <= a.len; n++) begin
      bit [31:0] ba = beat_addr(a, n);
      bit [31:0] d  = wd_q.pop_front();
      bit [3:0]  s  = ws_q.pop_front();
      bit [1:0]  r  = cfg.resp_for(ba, 1);
      if (r > worst) worst = r;
      if (r == AXI_OKAY) mem.bus_wr32({ba[31:2], 2'b00}, d, s);   // errored beats leave memory alone
    end
    b.id = a.id; b.resp = worst;
    b.wait_clk = (cfg.bvalid_lat_max == 0) ? 0 : $urandom_range(cfg.bvalid_lat_max);
    b_q.push_back(b);
    n_wr++;
  endfunction

  task run_phase(uvm_phase phase);
    idle_outputs();
    forever begin
      @(posedge vif.aclk);
      if (!vif.aresetn) begin
        flush();
        @(negedge vif.aclk);
        idle_outputs();
        continue;
      end
      // ---- handshakes at this edge
      if (vif.awvalid && vif.awready)
        aw_q.push_back('{vif.awid, vif.awaddr, vif.awlen, vif.awsize, vif.awburst});
      if (vif.wvalid && vif.wready) begin
        wd_q.push_back(vif.wdata);
        ws_q.push_back(vif.wstrb);
      end
      if (vif.arvalid && vif.arready)
        ar_q.push_back('{vif.arid, vif.araddr, vif.arlen, vif.arsize, vif.arburst});
      if (vif.bvalid && vif.bready) void'(b_q.pop_front());
      if (vif.rvalid && vif.rready) begin
        if (vif.rlast) rd_act = 0;
        else begin
          rd_beat++;
          rd_wait = (cfg.rbeat_gap_pct != 0 && axim_pct(cfg.rbeat_gap_pct)) ? 1 : 0;
        end
      end
      // ---- commit complete writes
      while (aw_q.size() > 0 && wd_q.size() >= int'(aw_q[0].len) + 1)
        commit_write(aw_q.pop_front());
      // ---- start the next read burst
      if (!rd_act && ar_q.size() > 0) begin
        rd_cur  = ar_q.pop_front();
        rd_act  = 1;
        rd_beat = 0;
        rd_wait = (cfg.rvalid_lat_max == 0) ? 0 : $urandom_range(cfg.rvalid_lat_max);
        n_rd++;
      end
      // ---- drive
      @(negedge vif.aclk);
      vif.awready = axim_pct(cfg.awready_pct);
      vif.wready  = axim_pct(cfg.wready_pct);
      vif.arready = axim_pct(cfg.arready_pct);
      if (b_q.size() > 0 && b_q[0].wait_clk > 0) begin
        b_q[0].wait_clk--;
        vif.bvalid = 0; vif.bid = 0; vif.bresp = 0;
      end else if (b_q.size() > 0) begin
        vif.bvalid = 1; vif.bid = b_q[0].id; vif.bresp = b_q[0].resp;
      end else begin
        vif.bvalid = 0; vif.bid = 0; vif.bresp = 0;
      end
      if (rd_act && rd_wait > 0) begin
        rd_wait--;
        vif.rvalid = 0; vif.rid = 0; vif.rdata = 0; vif.rresp = 0; vif.rlast = 0;
      end else if (rd_act) begin
        bit [31:0] ba = beat_addr(rd_cur, rd_beat);
        bit [1:0]  r  = cfg.resp_for(ba, 0);
        vif.rvalid = 1;
        vif.rid    = rd_cur.id;
        vif.rdata  = (r == AXI_OKAY) ? mem.rd32({ba[31:2], 2'b00}) : 32'h0;
        vif.rresp  = r;
        vif.rlast  = (rd_beat == rd_cur.len);
      end else begin
        vif.rvalid = 0; vif.rid = 0; vif.rdata = 0; vif.rresp = 0; vif.rlast = 0;
      end
    end
  endtask
endclass

// ----------------------------------------------------------------------------
class axim_monitor extends uvm_monitor;
  `uvm_component_utils(axim_monitor)
  virtual axim_if vif;
  axim_cfg cfg;
  uvm_analysis_port #(axim_txn) ap;     // completed bursts (writes after B, reads after RLAST)
  axim_txn aw_pend[$];                  // addresses without all their W beats yet
  axim_txn wb_pend[$];                  // all beats in, waiting for B
  axim_txn ar_pend[$];                  // waiting for R beats (in order)
  bit [31:0] w_early_d[$];              // W beats that came before their address
  bit [3:0]  w_early_s[$];
  bit        w_early_l[$];
  int unsigned rule_errors[string];
  int unsigned n_wr, n_rd, if_errors_seen;
  int unsigned max_seen_rd, max_seen_wr;
  axim_txn   completed[$];              // every burst seen since the last clear (scoreboards read it)

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    if (!uvm_config_db #(virtual axim_if)::get(this, "", "axim_vif", vif))
      `uvm_fatal("NOVIF", "axim_monitor: axim_vif not set")
  endfunction

  function void fail(string rule, string msg);
    if (rule_errors.exists(rule)) rule_errors[rule]++; else rule_errors[rule] = 1;
    `uvm_error(rule, msg)
  endfunction

  function int unsigned rule_count(string rule);
    return rule_errors.exists(rule) ? rule_errors[rule] : 0;
  endfunction

  function int unsigned total_rule_errors();
    int unsigned n = 0;
    foreach (rule_errors[r]) n += rule_errors[r];
    return n;
  endfunction

  // address-phase rules
  function void check_addr(axim_txn t);
    string ch = t.write ? "AW" : "AR";
    bit [31:0] last;
    begin
      int eid = (!t.write && cfg.expect_rd_id >= 0) ? cfg.expect_rd_id : cfg.expect_id;
      if (eid >= 0 && t.id != eid)
        fail("TXN_ID", $sformatf("%s id %0d, the IP uses id %0d", ch, t.id, eid));
    end
    if (!cfg.size_mask[t.size])
      fail("TXN_SIZE", $sformatf("%s size %0d (%0d bytes) not allowed: %s", ch, t.size, 1 << t.size, t.convert2string()));
    if (t.size > 2)
      fail("TXN_SIZE", $sformatf("%s size %0d wider than the 32-bit bus", ch, t.size));
    if (t.burst == 2'b11 || !cfg.burst_mask[t.burst])
      fail("TXN_BURST", $sformatf("%s burst type %0d not allowed", ch, t.burst));
    if (t.beats() > cfg.max_beats)
      fail("TXN_LEN", $sformatf("%s %0d beats, the IP promises at most %0d", ch, t.beats(), cfg.max_beats));
    if (t.burst == AXI_WRAP && !(t.len inside {8'd1, 8'd3, 8'd7, 8'd15}))
      fail("TXN_LEN", $sformatf("%s WRAP burst of %0d beats (2, 4, 8 or 16 only)", ch, t.beats()));
    if (t.burst == AXI_FIXED && t.beats() > 16)
      fail("TXN_LEN", $sformatf("%s FIXED burst of %0d beats (16 at most)", ch, t.beats()));
    if ((cfg.require_aligned || t.burst == AXI_WRAP) && (t.addr & ((32'd1 << t.size) - 1)) != 0)
      fail("TXN_ALIGN", $sformatf("%s address %08h not aligned to %0d bytes", ch, t.addr, 1 << t.size));
    if (t.burst == AXI_INCR) begin
      last = t.beat_addr(t.len) | ((32'd1 << t.size) - 1);
      if ((t.addr >> 12) != (last >> 12))
        fail("TXN_4K", $sformatf("%s INCR burst %08h..%08h crosses a 4 KB boundary", ch, t.addr, last));
    end
    if (cfg.check_windows)
      for (int unsigned n = 0; n < t.beats(); n++) begin
        bit [31:0] a = t.beat_addr(n);
        if (!cfg.in_window(a, t.write) || !cfg.in_window((a | ((32'd1 << t.size) - 1)), t.write)) begin
          fail("TXN_WINDOW", $sformatf("%s beat %0d at %08h is outside every %s window", ch, n, a,
                                       t.write ? "write" : "read"));
          break;
        end
      end
  endfunction

  function void add_wbeat(axim_txn t, bit [31:0] d, bit [3:0] s, bit last);
    int unsigned n = t.data.size();
    bit [3:0] m = t.lane_mask(n);
    t.data.push_back(d);
    t.strb.push_back(s);
    if ((s & ~m) != 0)
      fail("TXN_STRB", $sformatf("W beat %0d of %08h strobes lanes %b outside its transfer (%b)", n, t.addr, s, m));
    else if (cfg.require_full_strb && s != m)
      fail("TXN_STRB", $sformatf("W beat %0d of %08h strobe %b, the IP promises full words (%b)", n, t.addr, s, m));
    if (last != (n == t.len))
      fail("TXN_WLAST", $sformatf("WLAST=%0d on beat %0d of a %0d-beat burst at %08h", last, n, t.beats(), t.addr));
  endfunction

  longint unsigned cyc;

  function void finish(axim_txn t);
    t.t_done = $time;
    t.c_done = cyc;
    if (cfg.print_lat)
      $display("LAT %s %s %s %0d", cfg.master_name, cfg.slave_name, t.write ? "W" : "R", t.c_done - t.c_addr);
    completed.push_back(t);
    ap.write(t);
  endfunction

  function void clear();
    completed.delete();
  endfunction

  function void flush();
    aw_pend.delete(); wb_pend.delete(); ar_pend.delete();
    w_early_d.delete(); w_early_s.delete(); w_early_l.delete();
  endfunction

  task run_phase(uvm_phase phase);
    forever begin
      @(posedge vif.aclk);
      cyc++;
      if (vif.chk_errors != if_errors_seen) begin
        fail("AXIM_IF_CHECK", $sformatf("%0d new cycle-level failure(s), last: %s",
                                        vif.chk_errors - if_errors_seen, vif.chk_last));
        if_errors_seen = vif.chk_errors;
      end
      if (!vif.aresetn) begin
        flush();
        continue;
      end
      if (vif.awvalid && vif.awready) begin
        axim_txn t = axim_txn::type_id::create("aw");
        t.write = 1; t.id = vif.awid; t.addr = vif.awaddr; t.len = vif.awlen;
        t.size = vif.awsize; t.burst = vif.awburst; t.prot = vif.awprot; t.t_addr = $time; t.c_addr = cyc;
        check_addr(t);
        while (w_early_d.size() > 0 && t.data.size() < t.beats())
          add_wbeat(t, w_early_d.pop_front(), w_early_s.pop_front(), w_early_l.pop_front());
        if (t.data.size() == t.beats()) wb_pend.push_back(t); else aw_pend.push_back(t);
        if (aw_pend.size() + wb_pend.size() > cfg.max_out_wr)
          fail("TXN_OUTSTANDING", $sformatf("%0d writes outstanding, the IP promises at most %0d",
                                            aw_pend.size() + wb_pend.size(), cfg.max_out_wr));
        if (aw_pend.size() + wb_pend.size() > max_seen_wr) max_seen_wr = aw_pend.size() + wb_pend.size();
      end
      if (vif.wvalid && vif.wready) begin
        if (aw_pend.size() > 0) begin
          add_wbeat(aw_pend[0], vif.wdata, vif.wstrb, vif.wlast);
          if (aw_pend[0].data.size() == aw_pend[0].beats()) wb_pend.push_back(aw_pend.pop_front());
        end else begin
          w_early_d.push_back(vif.wdata); w_early_s.push_back(vif.wstrb); w_early_l.push_back(vif.wlast);
          if (w_early_d.size() > 16 * (cfg.max_out_wr + 1))
            fail("TXN_WLAST", $sformatf("%0d W beats without a write address", w_early_d.size()));
        end
      end
      if (vif.bvalid && vif.bready) begin
        int k = -1;
        foreach (wb_pend[i]) if (wb_pend[i].id == vif.bid) begin k = i; break; end
        if (k < 0)
          fail("TXN_RESP_ID", $sformatf("B id=%0d with no write of that ID whose data is complete", vif.bid));
        else begin
          axim_txn t = wb_pend[k];
          wb_pend.delete(k);
          t.resp.push_back(vif.bresp);
          n_wr++;
          finish(t);
        end
      end
      if (vif.arvalid && vif.arready) begin
        axim_txn t = axim_txn::type_id::create("ar");
        t.write = 0; t.id = vif.arid; t.addr = vif.araddr; t.len = vif.arlen;
        t.size = vif.arsize; t.burst = vif.arburst; t.prot = vif.arprot; t.t_addr = $time; t.c_addr = cyc;
        check_addr(t);
        ar_pend.push_back(t);
        if (ar_pend.size() > cfg.max_out_rd)
          fail("TXN_OUTSTANDING", $sformatf("%0d reads outstanding, the IP promises at most %0d",
                                            ar_pend.size(), cfg.max_out_rd));
        if (ar_pend.size() > max_seen_rd) max_seen_rd = ar_pend.size();
      end
      if (vif.rvalid && vif.rready) begin
        int k = -1;
        foreach (ar_pend[i]) if (ar_pend[i].id == vif.rid) begin k = i; break; end
        if (k < 0)
          fail("TXN_RESP_ID", $sformatf("R id=%0d with no read of that ID outstanding", vif.rid));
        else begin
          axim_txn t = ar_pend[k];
          t.data.push_back(vif.rdata);
          t.resp.push_back(vif.rresp);
          if (vif.rlast != (t.data.size() == t.beats()))
            fail("TXN_RLAST", $sformatf("RLAST=%0d on beat %0d of a %0d-beat read at %08h",
                                        vif.rlast, t.data.size() - 1, t.beats(), t.addr));
          if (vif.rlast || t.data.size() == t.beats()) begin
            ar_pend.delete(k);
            n_rd++;
            finish(t);
          end
        end
      end
    end
  endtask

  // a burst still in flight at the end of the test never completed
  function void check_phase(uvm_phase phase);
    if (aw_pend.size() + wb_pend.size() + ar_pend.size() != 0)
      fail("TXN_HANG", $sformatf("%0d write and %0d read bursts never completed",
                                 aw_pend.size() + wb_pend.size(), ar_pend.size()));
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("AXIM_MON", $sformatf("%0d writes, %0d reads, max outstanding wr=%0d rd=%0d, rule errors=%0d",
                                    n_wr, n_rd, max_seen_wr, max_seen_rd, total_rule_errors()), UVM_LOW)
  endfunction
endclass

// ----------------------------------------------------------------------------
// Functional coverage as plain counters (Verilator 5.052 does not sample
// covergroups); report_phase prints one AXIM_COV line per bin family and
// `goal_met()` says whether every bin of the subsystem contract was hit.
class axim_coverage extends uvm_subscriber #(axim_txn);
  `uvm_component_utils(axim_coverage)
  int unsigned c_dir[2];          // 0 read, 1 write
  int unsigned c_len[int];        // beats
  int unsigned c_size[int];
  int unsigned c_burst[int];
  int unsigned c_resp[int];
  int unsigned c_id[int];
  int unsigned c_4k_edge;         // a burst ending on the last word of a 4 KB page

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  static function void bump(ref int unsigned a[int], input int k);
    if (a.exists(k)) a[k]++; else a[k] = 1;
  endfunction

  function void write(axim_txn t);
    c_dir[t.write]++;
    bump(c_len, t.beats());
    bump(c_size, t.size);
    bump(c_burst, t.burst);
    bump(c_resp, t.worst_resp());
    bump(c_id, t.id);
    if (((t.beat_addr(t.len) + (1 << t.size)) & 32'hFFF) == 0) c_4k_edge++;
  endfunction

  static function string fmt(int unsigned a[int]);
    string s = "";
    foreach (a[k]) s = {s, $sformatf(" %0d:%0d", k, a[k])};
    return s;
  endfunction

  // bins the subsystem contract asks for: reads and writes, a 1-beat and a
  // 16-beat burst, an OKAY and an error response
  function bit goal_met(bit need_rd = 1, bit need_wr = 1, bit need_err = 1);
    if (need_rd && c_dir[0] == 0) return 0;
    if (need_wr && c_dir[1] == 0) return 0;
    if (!c_len.exists(1) || !c_len.exists(16)) return 0;
    if (!c_resp.exists(AXI_OKAY)) return 0;
    if (need_err && !c_resp.exists(AXI_SLVERR) && !c_resp.exists(AXI_DECERR)) return 0;
    return 1;
  endfunction

  static function int unsigned hits(int unsigned a[int], int k);
    return a.exists(k) ? a[k] : 0;
  endfunction

  // one "FCOV <group> <point> <bin> <hits>" line per bin, 0-hit bins included
  // (the SoC-tb-regress-builder coverage merge reads these)
  function void print_fcov(string group);
    int unsigned big = 0;
    string bn[4] = '{"FIXED", "INCR", "WRAP", "RSVD"};
    string rn[4] = '{"OKAY", "EXOKAY", "SLVERR", "DECERR"};
    $display("FCOV %s dir RD %0d", group, c_dir[0]);
    $display("FCOV %s dir WR %0d", group, c_dir[1]);
    for (int b = 1; b <= 16; b++) $display("FCOV %s beats %0d %0d", group, b, hits(c_len, b));
    foreach (c_len[k]) if (k > 16) big += c_len[k];
    $display("FCOV %s beats 17_256 %0d", group, big);
    for (int z = 0; z <= 2; z++) $display("FCOV %s size %0dB %0d", group, 1 << z, hits(c_size, z));
    for (int b = 0; b <= 2; b++) $display("FCOV %s burst %s %0d", group, bn[b], hits(c_burst, b));
    for (int r = 0; r <= 3; r++) $display("FCOV %s resp %s %0d", group, rn[r], hits(c_resp, r));
    for (int i = 0; i < 16; i++) $display("FCOV %s id %0d %0d", group, i, hits(c_id, i));
    $display("FCOV %s page_end 4k_edge %0d", group, c_4k_edge);
  endfunction

  string fcov_group = "axim";

  function void report_phase(uvm_phase phase);
    print_fcov(fcov_group);
    `uvm_info("AXIM_COV", $sformatf("dir rd:%0d wr:%0d | beats%s | size%s | burst%s | resp%s | id%s | 4k_edge:%0d",
                                    c_dir[0], c_dir[1], fmt(c_len), fmt(c_size), fmt(c_burst),
                                    fmt(c_resp), fmt(c_id), c_4k_edge), UVM_LOW)
  endfunction
endclass

class axim_agent extends uvm_agent;
  `uvm_component_utils(axim_agent)
  axim_cfg         cfg;
  ssv_mem          mem;
  axim_subordinate sub;
  axim_monitor     mon;
  axim_coverage    cov;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    if (cfg == null && !uvm_config_db #(axim_cfg)::get(this, "", "axim_cfg", cfg))
      cfg = axim_cfg::type_id::create("cfg");
    if (mem == null) mem = ssv_mem::type_id::create("mem");
    sub = axim_subordinate::type_id::create("sub", this);
    mon = axim_monitor::type_id::create("mon", this);
    cov = axim_coverage::type_id::create("cov", this);
    sub.cfg = cfg; sub.mem = mem;
    mon.cfg = cfg;
  endfunction

  function void connect_phase(uvm_phase phase);
    mon.ap.connect(cov.analysis_export);
  endfunction
endclass
