// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// axim_kit_pkg.sv -- self-test of the AXI4 manager-port kit: the manager BFM
// stands in for an IP and the kit's subordinate, monitor and checkers are the
// units under test.
//
//   axim_func_test     legal traffic of every shape (INCR / WRAP / FIXED,
//                      sizes 1/2/4 bytes, sparse strobes, unaligned INCR,
//                      1..256 beats, all 16 IDs, a write and a read in flight
//                      together, random back-pressure and latency, SLVERR and
//                      DECERR regions); every read is checked against a byte
//                      shadow of the memory, every response against the
//                      expected one, and no checker may fire.
//                      Prints SB_PASS checks=<n>.
//   axim_checker_test  one injected violation per rule under the subsystem
//                      contract (INCR, 4-byte beats, <= 16 beats, full
//                      strobes, aligned, windows): every rule must catch its
//                      injection, and legal bursts in between must not trip
//                      anything. Prints SB_PASS checks=<n>.

package axim_kit_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import ssv_pkg::*;

  class axim_kit_env extends uvm_env;
    `uvm_component_utils(axim_kit_env)
    axim_agent      axi;
    ssv_axi_mgr_bfm bfm;
    axim_cfg        cfg;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      virtual axim_if vif;
      if (!uvm_config_db #(virtual axim_if)::get(this, "", "axim_vif", vif))
        `uvm_fatal("NOVIF", "axim_vif not set")
      cfg = axim_cfg::type_id::create("cfg");
      axi = axim_agent::type_id::create("axi", this);
      axi.cfg = cfg;
      bfm = ssv_axi_mgr_bfm::type_id::create("bfm");
      bfm.vif = vif;
    endfunction
  endclass

  class axim_kit_base_test extends uvm_test;
    `uvm_component_utils(axim_kit_base_test)
    axim_kit_env    env;
    virtual axim_if vif;
    int unsigned    checks, fails;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      env = axim_kit_env::type_id::create("env", this);
      void'(uvm_config_db #(virtual axim_if)::get(this, "", "axim_vif", vif));
    endfunction

    function void sb_check(bit ok, string what);
      checks++;
      if (!ok) begin
        fails++;
        `uvm_error("KIT_SB", what)
      end
    endfunction

    task wait_reset();
      env.bfm.init();
      @(posedge vif.aclk);
      while (!vif.aresetn) @(posedge vif.aclk);
      repeat (2) @(posedge vif.aclk);
    endtask

    function void report_phase(uvm_phase phase);
      uvm_report_server rs = uvm_report_server::get_server();
      if (fails == 0 && checks > 0 && rs.get_severity_count(UVM_ERROR) == 0 && rs.get_severity_count(UVM_FATAL) == 0)
        $display("SB_PASS checks=%0d", checks);
      else
        $display("SB_FAIL checks=%0d fails=%0d", checks, fails);
    endfunction
  endclass

  // ------------------------------------------------------------------------
  class axim_func_test extends axim_kit_base_test;
    `uvm_component_utils(axim_func_test)
    bit [7:0] shadow[bit [31:0]];
    int unsigned n_bursts = 400;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function bit [7:0] sh(bit [31:0] a);
      return shadow.exists(a) ? shadow[a] : 8'h00;
    endfunction

    // a random legal burst inside [base, base + span)
    function void pick(bit [31:0] base, bit [31:0] span, output bit [31:0] addr, output bit [7:0] len,
                       output bit [2:0] size, output bit [1:0] burst);
      int unsigned k = $urandom_range(99);
      size  = $urandom_range(2);
      burst = (k < 60) ? AXI_INCR : (k < 85) ? AXI_WRAP : AXI_FIXED;
      case (burst)
        AXI_WRAP:  len = (8'd1 << $urandom_range(1, 4)) - 1;
        AXI_FIXED: len = $urandom_range(15);
        default:   len = ($urandom_range(9) == 0) ? 8'($urandom_range(255)) : 8'($urandom_range(15));
      endcase
      if (burst != AXI_WRAP && $urandom_range(19) == 0) len = 0;
      addr = base + ($urandom_range(span / 2) & ~32'h0);
      if (burst == AXI_WRAP || $urandom_range(1)) addr &= ~((32'd1 << size) - 1);   // INCR / FIXED may be unaligned
      // keep INCR inside its 4 KB page
      if (burst == AXI_INCR) begin
        bit [31:0] last = (addr & ~((32'd1 << size) - 1)) + (int'(len) + 1) * (1 << size) - 1;
        if ((addr >> 12) != (last >> 12)) addr = (last & ~32'hFFF) - (int'(len) + 1) * (1 << size);
        if (addr < base) begin addr = base; len = 0; end
      end
    endfunction

    function void make_beat(axim_txn t, int unsigned n, output bit [31:0] d, output bit [3:0] s);
      bit [3:0] m = t.lane_mask(n);
      d = $urandom();
      s = ($urandom_range(3) == 0) ? (4'($urandom()) & m) : m;
    endfunction

    task do_write(bit [31:0] addr, bit [7:0] len, bit [2:0] size, bit [1:0] burst, bit [3:0] id);
      axim_txn t = new();
      bit [31:0] d[$]; bit [3:0] s[$]; bit [1:0] resp, exp_resp;
      t.addr = addr; t.len = len; t.size = size; t.burst = burst;
      exp_resp = AXI_OKAY;
      for (int unsigned n = 0; n <= len; n++) begin
        bit [31:0] dd; bit [3:0] ss; bit [1:0] r;
        make_beat(t, n, dd, ss);
        d.push_back(dd); s.push_back(ss);
        r = env.cfg.resp_for(t.beat_addr(n), 1);
        if (r > exp_resp) exp_resp = r;
      end
      env.bfm.write(id, addr, len, size, burst, d, s, resp);
      sb_check(resp == exp_resp, $sformatf("write %08h len %0d: BRESP %0d, expected %0d", addr, len, resp, exp_resp));
      // update the shadow beat by beat, as the subordinate commits them
      for (int unsigned n = 0; n <= len; n++) begin
        bit [31:0] ba = t.beat_addr(n);
        if (env.cfg.resp_for(ba, 1) != AXI_OKAY) continue;
        for (int b = 0; b < 4; b++) if (s[n][b]) shadow[{ba[31:2], 2'b00} + b] = d[n][8*b +: 8];
      end
    endtask

    task do_read(bit [31:0] addr, bit [7:0] len, bit [2:0] size, bit [1:0] burst, bit [3:0] id);
      axim_txn t = new();
      bit [31:0] d[$]; bit [1:0] r[$];
      t.addr = addr; t.len = len; t.size = size; t.burst = burst;
      env.bfm.read(id, addr, len, size, burst, d, r);
      sb_check(d.size() == int'(len) + 1, $sformatf("read %08h: %0d beats, expected %0d", addr, d.size(), len + 1));
      foreach (d[n]) begin
        bit [31:0] ba = t.beat_addr(n);
        bit [1:0]  er = env.cfg.resp_for(ba, 0);
        bit [3:0]  m  = t.lane_mask(n);
        sb_check(r[n] == er, $sformatf("read %08h beat %0d: RRESP %0d, expected %0d", addr, n, r[n], er));
        if (er == AXI_OKAY)
          for (int b = 0; b < 4; b++)
            if (m[b])
              sb_check(d[n][8*b +: 8] == sh({ba[31:2], 2'b00} + b),
                    $sformatf("read %08h beat %0d lane %0d: %02h, shadow %02h", addr, n, b,
                              d[n][8*b +: 8], sh({ba[31:2], 2'b00} + b)));
      end
    endtask

    task run_phase(uvm_phase phase);
      phase.raise_objection(this);
      // legal-everything checker configuration
      env.cfg.max_beats = 256; env.cfg.size_mask = 8'h07; env.cfg.burst_mask = 4'h7;
      env.cfg.require_full_strb = 0; env.cfg.require_aligned = 0;
      env.cfg.max_out_rd = 1; env.cfg.max_out_wr = 1;
      env.cfg.add_err_region(32'h0000_3000, 32'h0000_3100, AXI_SLVERR);
      env.cfg.add_err_region(32'h0000_3100, 32'h0000_3200, AXI_DECERR);
      wait_reset();
      // region A [0x0000, 0x2000) written then read back; region B
      // [0x2000, 0x3000) preloaded and read while A is written
      for (int unsigned a = 32'h2000; a < 32'h3000; a += 4) begin
        bit [31:0] w = $urandom();
        env.axi.mem.wr32(a, w);
        for (int b = 0; b < 4; b++) shadow[a + b] = w[8*b +: 8];
      end
      for (int unsigned i = 0; i < n_bursts; i++) begin
        bit [31:0] wa, ra; bit [7:0] wl, rl; bit [2:0] ws, rs; bit [1:0] wb, rb;
        case (i % 4)
          0: env.cfg.set_backpressure(100, 0);
          1: env.cfg.set_backpressure(70, 3);
          2: env.cfg.set_backpressure(40, 8);
          3: env.cfg.set_backpressure(90, 1);
        endcase
        env.bfm.wvalid_gap_pct = (i % 3 == 0) ? 20 : 0;
        env.bfm.bready_pct = (i % 5 == 0) ? 50 : 100;
        env.bfm.rready_pct = (i % 7 == 0) ? 50 : 100;
        pick(32'h0000, 32'h2000, wa, wl, ws, wb);
        pick(32'h2000, 32'h1000, ra, rl, rs, rb);
        if (i % 40 == 7)  begin wa = 32'h0000_2FF0 + 32'h1000; wl = 3; ws = 2; wb = AXI_INCR; end  // SLVERR region
        if (i % 40 == 23) begin ra = 32'h0000_3100; rl = 15; rs = 2; rb = AXI_INCR; end            // DECERR region
        if (i == 11) begin wa = 32'h0000_0FC0; wl = 15; ws = 2; wb = AXI_INCR; end                 // ends on a 4 KB edge
        fork
          do_write(wa, wl, ws, wb, 4'(i));
          do_read(ra, rl, rs, rb, 4'(i + 3));
        join
        if (i % 8 == 0) begin   // read back part of region A
          bit [31:0] a2; bit [7:0] l2; bit [2:0] s2; bit [1:0] b2;
          pick(32'h0000, 32'h2000, a2, l2, s2, b2);
          do_read(a2, l2, s2, b2, 4'(i + 5));
        end
      end
      // read back the whole of region A with 16-beat INCR bursts
      env.cfg.set_backpressure(100, 0);
      for (bit [31:0] a = 0; a < 32'h2000; a += 64) do_read(a, 15, 2, AXI_INCR, 4'h9);
      repeat (20) @(posedge vif.aclk);
      sb_check(env.axi.mon.total_rule_errors() == 0, "monitor rules fired on legal traffic");
      sb_check(vif.chk_errors == 0, "interface checker fired on legal traffic");
      sb_check(env.axi.cov.goal_met(), "coverage goal (rd, wr, 1 and 16 beats, OKAY, error) not met");
      sb_check(env.axi.cov.c_burst.size() == 3, "not every burst type was exercised");
      sb_check(env.axi.cov.c_size.size() == 3, "not every transfer size was exercised");
      sb_check(env.axi.cov.c_id.size() == 16, "not every ID was exercised");
      phase.drop_objection(this);
    endtask
  endclass

  // ------------------------------------------------------------------------
  class axim_checker_test extends axim_kit_base_test;
    `uvm_component_utils(axim_checker_test)
    ssv_expect_catcher catcher;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void start_of_simulation_phase(uvm_phase phase);
      catcher = new("catcher");
      uvm_report_cb::add(null, catcher);
    endfunction

    // a legal 4-beat write + read under the contract: must trip nothing
    task legal(bit [31:0] a);
      bit [31:0] d[$]; bit [3:0] s[$]; bit [1:0] resp; bit [1:0] r[$];
      int unsigned n_before = env.axi.mon.total_rule_errors() + vif.chk_errors;
      for (int i = 0; i < 4; i++) begin d.push_back($urandom()); s.push_back(4'hF); end
      env.bfm.write(4'h1, a, 3, 2, AXI_INCR, d, s, resp);
      env.bfm.read(4'h2, a, 3, 2, AXI_INCR, d, r);
      sb_check(env.axi.mon.total_rule_errors() + vif.chk_errors == n_before,
            $sformatf("legal burst at %08h tripped a checker", a));
    endtask

    task inject(inject_e inj, string rule, bit is_if_rule = 0);
      bit [31:0] d[$]; bit [3:0] s[$]; bit [1:0] resp; bit [1:0] r[$];
      bit [31:0] a = 32'h0000_1000; bit [7:0] len = 3; bit [2:0] size = 2; bit [1:0] burst = AXI_INCR;
      int unsigned before_rule = is_if_rule ? vif.rule_count(rule) : env.axi.mon.rule_count(rule);
      int unsigned before_all  = env.axi.mon.total_rule_errors();
      int unsigned before_if   = vif.chk_errors;
      catcher.ids.delete();
      catcher.ids.push_back(rule);
      if (is_if_rule) catcher.ids.push_back("AXIM_IF_CHECK");
      case (inj)
        INJ_4K:    a = 32'h0000_1FF8;
        INJ_LEN:   len = 16;
        INJ_SIZE:  size = 1;
        INJ_BURST: burst = AXI_WRAP;
        INJ_ALIGN: a = 32'h0000_1004 + 2;
        INJ_WINDOW: a = 32'h0000_8000;
        default: ;
      endcase
      begin
        axim_txn t = new();
        t.addr = a; t.len = len; t.size = size; t.burst = burst;
        for (int i = 0; i <= len; i++) begin
          d.push_back($urandom());
          s.push_back(inj == INJ_STRB ? 4'h3 : t.lane_mask(i));
        end
      end
      if (inj inside {INJ_AW_DROP, INJ_AW_CHANGE, INJ_W_CHANGE}) begin
        if (inj == INJ_W_CHANGE) env.cfg.wready_pct = 0; else env.cfg.awready_pct = 0;
        fork
          env.bfm.write(4'h3, a, len, size, burst, d, s, resp, inj);
          begin repeat (6) @(posedge vif.aclk); env.cfg.set_backpressure(100, 0); end
        join
      end else if (inj == INJ_AR_DROP) begin
        env.cfg.arready_pct = 0;
        fork
          env.bfm.read(4'h4, a, len, size, burst, d, r, inj);
          begin repeat (6) @(posedge vif.aclk); env.cfg.set_backpressure(100, 0); end
        join
      end else
        env.bfm.write(4'h3, a, len, size, burst, d, s, resp, inj);
      repeat (3) @(posedge vif.aclk);
      if (is_if_rule) begin
        sb_check(vif.rule_count(rule) > before_rule, $sformatf("%s did not catch %s", rule, inj.name()));
        sb_check(catcher.count("AXIM_IF_CHECK") > 0, $sformatf("monitor did not report the %s failure", rule));
        sb_check(vif.chk_errors - before_if == vif.rule_count(rule) - before_rule,
              $sformatf("%s also tripped other cycle-level rules", inj.name()));
        catcher.caught.delete();
      end else begin
        sb_check(env.axi.mon.rule_count(rule) > before_rule, $sformatf("%s did not catch %s", rule, inj.name()));
        sb_check(env.axi.mon.total_rule_errors() - before_all == env.axi.mon.rule_count(rule) - before_rule,
              $sformatf("%s also tripped other rules", inj.name()));
        sb_check(vif.chk_errors == before_if, $sformatf("%s tripped the cycle-level checker", inj.name()));
      end
      `uvm_info("KIT_INJ", $sformatf("%s caught by %s", inj.name(), rule), UVM_LOW)
      catcher.ids.delete();
    endtask

    task run_phase(uvm_phase phase);
      phase.raise_objection(this);
      // default axim_cfg = the subsystem contract; plus address windows
      env.cfg.check_windows = 1;
      env.cfg.add_window(32'h0000_0000, 32'h0000_4000, 1, 1, "buffers");
      wait_reset();
      legal(32'h0000_0100);
      inject(INJ_4K,            "TXN_4K");            legal(32'h0000_0200);
      inject(INJ_LEN,           "TXN_LEN");           legal(32'h0000_0300);
      inject(INJ_SIZE,          "TXN_SIZE");          legal(32'h0000_0400);
      inject(INJ_BURST,         "TXN_BURST");         legal(32'h0000_0500);
      inject(INJ_ALIGN,         "TXN_ALIGN");         legal(32'h0000_0600);
      inject(INJ_WLAST_EARLY,   "TXN_WLAST");         legal(32'h0000_0700);
      inject(INJ_WLAST_MISSING, "TXN_WLAST");         legal(32'h0000_0800);
      inject(INJ_STRB,          "TXN_STRB");          legal(32'h0000_0900);
      inject(INJ_WINDOW,        "TXN_WINDOW");        legal(32'h0000_0A00);
      inject(INJ_AW_DROP,       "CHK_STABLE_AW", 1);  legal(32'h0000_0B00);
      inject(INJ_AW_CHANGE,     "CHK_STABLE_AW", 1);  legal(32'h0000_0C00);
      inject(INJ_W_CHANGE,      "CHK_STABLE_W",  1);  legal(32'h0000_0D00);
      inject(INJ_AR_DROP,       "CHK_STABLE_AR", 1);  legal(32'h0000_0E00);
      repeat (10) @(posedge vif.aclk);
      phase.drop_objection(this);
    endtask
  endclass
endpackage
