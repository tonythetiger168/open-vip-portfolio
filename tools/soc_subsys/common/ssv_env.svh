// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_env.svh -- environment and base test shared by every subsystem VIP.
//
//   ssv_env        APB4 agent + RAL (register model, adapter, explicit
//                  predictor fed by the APB monitor) + AXI4 manager-port
//                  agent (subordinate, memory, monitor, coverage)
//   ssv_base_test  builds the env around the register model the IP's base
//                  test returns from make_regmodel(), and gives the
//                  subsystem tests their helpers: register access by name,
//                  IRQ waits, memory back door, checks with a pass/fail
//                  count, and the RAL test body (run_ral). report_phase
//                  prints "SB_PASS checks=<n>" (functional tests) or
//                  "RAL_PASS checks=<n>" (register tests) when nothing failed.

class ssv_env extends uvm_env;
  `uvm_component_utils(ssv_env)
  ssv_apb_agent                     apb;
  axim_agent                        axi;
  uvm_reg_block                     regmodel;
  ssv_apb_reg_adapter               adapter;
  uvm_reg_predictor #(ssv_apb_item) pred;
  axim_cfg                          axi_cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    apb = ssv_apb_agent::type_id::create("apb", this);
    axi = axim_agent::type_id::create("axi", this);
    if (axi_cfg == null) axi_cfg = axim_cfg::type_id::create("axi_cfg");
    axi.cfg = axi_cfg;
    adapter = ssv_apb_reg_adapter::type_id::create("adapter");
    pred = uvm_reg_predictor #(ssv_apb_item)::type_id::create("pred", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    regmodel.default_map.set_sequencer(apb.sqr, adapter);
    regmodel.default_map.set_auto_predict(0);
    pred.map     = regmodel.default_map;
    pred.adapter = adapter;
    apb.mon.ap.connect(pred.bus_in);
  endfunction
endclass

class ssv_base_test extends uvm_test;
  `uvm_component_utils(ssv_base_test)
  ssv_env            env;
  uvm_reg_block      rm;
  virtual ssv_apb_if apb_vif;
  virtual axim_if    axi_vif;
  int unsigned       checks, fails;
  bit                is_ral_test;
  string             ip_name = "ip";
  int unsigned       irq_timeout = 200000;   // clocks

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // the IP's base test returns its register block (built, not locked)
  virtual function uvm_reg_block make_regmodel();
    `uvm_fatal("NO_RAL", "make_regmodel() not overridden")
    return null;
  endfunction

  // the IP's base test sets its AXI4 contract here (expected IDs, limits)
  virtual function void configure_axi(axim_cfg c);
  endfunction

  function void build_phase(uvm_phase phase);
    if (!uvm_config_db #(virtual ssv_apb_if)::get(this, "", "apb_vif", apb_vif))
      `uvm_fatal("NOVIF", "apb_vif not set")
    if (!uvm_config_db #(virtual axim_if)::get(this, "", "axim_vif", axi_vif))
      `uvm_fatal("NOVIF", "axim_vif not set")
    rm = make_regmodel();
    rm.lock_model();
    env = ssv_env::type_id::create("env", this);
    env.regmodel = rm;
    env.axi_cfg = axim_cfg::type_id::create("axi_cfg");
    env.axi_cfg.master_name = ip_name;
    configure_axi(env.axi_cfg);
  endfunction

  // ---------------------------------------------------------------- checks
  function void sb_check(bit ok, string what);
    checks++;
    if (!ok) begin
      fails++;
      `uvm_error("SB_CHECK", what)
    end
  endfunction

  function void check_eq(bit [31:0] got, bit [31:0] exp, string what);
    sb_check(got == exp, $sformatf("%s: got %08h, expected %08h", what, got, exp));
  endfunction

  // ---------------------------------------------------------------- registers
  function uvm_reg r(string name);
    uvm_reg x = rm.get_reg_by_name(name);
    if (x == null) `uvm_fatal("NO_REG", {ip_name, " has no register ", name})
    return x;
  endfunction

  task wr(string name, bit [31:0] v);
    uvm_status_e st;
    r(name).write(st, v);
    sb_check(st == UVM_IS_OK, {"write ", name, " not OK"});
  endtask

  task rd(string name, output bit [31:0] v);
    uvm_status_e st;
    uvm_reg_data_t d;
    r(name).read(st, d);
    sb_check(st == UVM_IS_OK, {"read ", name, " not OK"});
    v = d[31:0];
  endtask

  // a field value by register and field name
  task rd_field(string reg_name, string field, output bit [31:0] v);
    bit [31:0] w;
    uvm_reg_field f;
    rd(reg_name, w);
    f = r(reg_name).get_field_by_name(field);
    if (f == null) `uvm_fatal("NO_FIELD", {reg_name, " has no field ", field})
    v = (w >> f.get_lsb_pos()) & ((64'd1 << f.get_n_bits()) - 1);
  endtask

  // write several fields of one register in a single APB write
  task wr_fields(string reg_name, string names[$], bit [31:0] vals[$]);
    uvm_status_e st;
    uvm_reg x = r(reg_name);
    foreach (names[i]) begin
      uvm_reg_field f = x.get_field_by_name(names[i]);
      if (f == null) `uvm_fatal("NO_FIELD", {reg_name, " has no field ", names[i]})
      f.set(vals[i]);
    end
    x.update(st, UVM_FRONTDOOR);
    sb_check(st == UVM_IS_OK, {"write ", reg_name, " not OK"});
  endtask

  task raw(bit write, bit [11:0] addr, inout bit [31:0] data, output bit slverr, input bit [3:0] strb = 4'hF);
    ssv_apb_rw_seq s = ssv_apb_rw_seq::type_id::create("raw");
    s.write = write; s.addr = addr; s.data = data; s.strb = strb;
    s.start(env.apb.sqr);
    data = s.data; slverr = s.slverr;
  endtask

  // IRQ index by name (IRQ_STATUS field order = the spec's irq order)
  function int irq_bit(string name);
    uvm_reg_field f = r("IRQ_STATUS").get_field_by_name(name);
    if (f == null) `uvm_fatal("NO_IRQ", {ip_name, " has no interrupt ", name})
    return f.get_lsb_pos();
  endfunction

  // wait until the irq pin is high, then return IRQ_STATUS
  task wait_irq(output bit [31:0] status, input string what = "");
    int unsigned n = 0;
    while (apb_vif.irq !== 1'b1) begin
      @(posedge apb_vif.pclk);
      if (++n > irq_timeout) begin
        sb_check(0, $sformatf("no interrupt within %0d clocks %s", irq_timeout, what));
        break;
      end
    end
    rd("IRQ_STATUS", status);
  endtask

  task clear_irq(bit [31:0] bits);
    wr("IRQ_STATUS", bits);
  endtask

  task clocks(int unsigned n);
    repeat (n) @(posedge apb_vif.pclk);
  endtask

  task wait_reset();
    @(posedge apb_vif.pclk);
    while (!apb_vif.presetn) @(posedge apb_vif.pclk);
    clocks(2);
  endtask

  // ---------------------------------------------------------------- memory
  function ssv_mem mem();
    return env.axi.mem;
  endfunction

  function void fill_random(bit [31:0] base, int unsigned words, ref bit [31:0] w[$]);
    w.delete();
    for (int unsigned i = 0; i < words; i++) w.push_back($urandom());
    mem().load_words(base, w);
  endfunction

  function void check_words(bit [31:0] base, const ref bit [31:0] exp[$], input string what);
    int unsigned bad = 0;
    foreach (exp[i]) begin
      bit [31:0] g = mem().rd32(base + 4 * i);
      checks++;
      if (g != exp[i]) begin
        fails++;
        bad++;
        if (bad <= 8)
          `uvm_error("SB_DATA", $sformatf("%s word %0d @%08h: got %08h, expected %08h",
                                          what, i, base + 4 * i, g, exp[i]))
      end
    end
    if (bad > 8) `uvm_error("SB_DATA", $sformatf("%s: %0d words differ", what, bad))
  endfunction

  // ------------------------------------------------------- single-job IPs
  // The job IPs built on open-ip-portfolio's soc_ss_axi_engine share
  // SRC_ADDR / DST_ADDR / LEN (32-bit words) / CMD.start / STATUS.{busy,err}
  // and the DONE / ERR interrupts. job_input() gives the words the IP will
  // read (0 where the kit's subordinate answers with an error);
  // run_job() programs and starts a job, waits for DONE and checks the
  // interrupts, STATUS, the output words (words whose write gets an error
  // keep their old value), and that the IP read exactly `in_words` words
  // inside the source (`n_rd`, default LEN) and wrote exactly `exp.size()`
  // words inside the destination (address windows). SRC_ADDR / DST_ADDR are
  // written when the IP has them; IP-specific registers are written before.
  function void job_input(bit [31:0] src, int unsigned len, ref bit [31:0] in[$], output bit err);
    in.delete(); err = 0;
    for (int unsigned i = 0; i < len; i++)
      if (env.axi_cfg.resp_for(src + 4 * i, 0) != AXI_OKAY) begin in.push_back(0); err = 1; end
      else in.push_back(mem().rd32(src + 4 * i));
  endfunction

  bit [31:0] job_irq_status;   // IRQ_STATUS seen by the last run_job (before it cleared it)

  task run_job(string tag, bit [31:0] src, bit [31:0] dst, int unsigned len, bit [31:0] exp[$],
               bit exp_err, input int n_rd = -1);
    int unsigned in_words = (n_rd < 0) ? len : n_rd;
    bit [31:0] st, v, want[$];
    int unsigned rw = 0, ww = 0;
    foreach (exp[i]) begin
      if (env.axi_cfg.resp_for(dst + 4 * i, 1) != AXI_OKAY) begin
        exp_err = 1;
        want.push_back(mem().rd32(dst + 4 * i));
      end else want.push_back(exp[i]);
    end
    if (rm.get_reg_by_name("SRC_ADDR") != null) wr("SRC_ADDR", src);
    if (rm.get_reg_by_name("DST_ADDR") != null) wr("DST_ADDR", dst);
    wr("LEN", len);
    env.axi_cfg.clear_windows();
    if (in_words != 0) env.axi_cfg.add_window(src, src + 4 * in_words, 1, 0, "src");
    if (exp.size() != 0) env.axi_cfg.add_window(dst, dst + 4 * exp.size(), 0, 1, "dst");
    env.axi_cfg.check_windows = 1;
    env.axi.mon.clear();
    mem().clear_written();
    wr("IRQ_ENABLE", (32'h1 << irq_bit("DONE")) | (32'h1 << irq_bit("ERR")));
    wr("CMD", 32'h1);
    wait_irq(st, tag);
    job_irq_status = st;
    sb_check(st[irq_bit("DONE")], {tag, ": DONE not set"});
    sb_check(st[irq_bit("ERR")] == exp_err, $sformatf("%s: ERR=%0d, expected %0d", tag, st[irq_bit("ERR")], exp_err));
    clear_irq(st);
    clocks(4);
    rd_field("STATUS", "busy", v);
    sb_check(v == 0, {tag, ": STATUS.busy after DONE"});
    rd_field("STATUS", "err", v);
    sb_check(v == exp_err, {tag, ": STATUS.err"});
    check_words(dst, want, tag);
    sb_check(mem().written_outside(dst, dst + 4 * exp.size()) == 0, {tag, ": bytes written outside the destination"});
    foreach (env.axi.mon.completed[i])
      if (env.axi.mon.completed[i].write) ww += env.axi.mon.completed[i].beats();
      else rw += env.axi.mon.completed[i].beats();
    sb_check(rw == in_words, $sformatf("%s: %0d words read, expected %0d", tag, rw, in_words));
    sb_check(ww == exp.size(), $sformatf("%s: %0d words written, expected %0d", tag, ww, exp.size()));
    env.axi_cfg.check_windows = 0;
  endtask

  function void backpressure(int unsigned i);
    case (i % 4)
      0: env.axi_cfg.set_backpressure(100, 0);
      1: env.axi_cfg.set_backpressure(60, 4);
      2: env.axi_cfg.set_backpressure(30, 10);
      3: env.axi_cfg.set_backpressure(90, 1);
    endcase
  endfunction

  // a word address in [lo, lo + span) with room for `words`; one time in
  // four a few words below a 4 KB boundary
  function bit [31:0] rand_addr(bit [31:0] lo, bit [31:0] span, int unsigned words);
    if ($urandom_range(3) == 0)
      return lo + ((($urandom_range((span >> 12) - 2) + 1) << 12) - 4 * $urandom_range(1, 20));
    return lo + (($urandom_range((span - 4 * words - 4) / 4)) * 4);
  endfunction

  // ---------------------------------------------------------------- RAL test
  task run_ral();
    uvm_status_e st;
    uvm_reg regs[$];
    uvm_reg_hw_reset_seq hw;
    uvm_reg_bit_bash_seq bb;
    bit [31:0] d; bit e;
    is_ral_test = 1;
    hw = uvm_reg_hw_reset_seq::type_id::create("hw");
    hw.model = rm;
    hw.start(null);
    checks += 1;
    bb = uvm_reg_bit_bash_seq::type_id::create("bb");
    bb.model = rm;
    bb.start(null);
    checks += 1;
    // every register that the tests may touch: random value, mirror check
    rm.get_registers(regs);
    foreach (regs[i]) begin
      uvm_reg_data_t v;
      if (uvm_resource_db #(bit)::get_by_name({"REG::", regs[i].get_full_name()}, "NO_REG_TESTS", 0) != null)
        continue;
      if (regs[i].get_rights() != "RW") continue;
      if (regs[i].get_name() == "IRQ_ENABLE") continue;
      v = {$urandom(), $urandom()};
      regs[i].write(st, v);
      sb_check(st == UVM_IS_OK, {"write ", regs[i].get_name()});
      regs[i].mirror(st, UVM_CHECK);
      sb_check(st == UVM_IS_OK, {"mirror ", regs[i].get_name()});
      regs[i].write(st, regs[i].get_reset());
    end
    // decode errors: one word past the map, and a misaligned access
    begin
      bit [11:0] past = 12'(regs.size() * 4);
      d = 32'h0; raw(0, past, d, e);
      sb_check(e, $sformatf("read of unmapped 0x%03h did not raise PSLVERR", past));
      d = 32'hFFFF_FFFF; raw(1, past, d, e);
      sb_check(e, $sformatf("write of unmapped 0x%03h did not raise PSLVERR", past));
      d = 32'h0; raw(0, 12'h012, d, e);
      sb_check(e, "misaligned read 0x012 did not raise PSLVERR");
      d = 32'h0; raw(0, 12'hFFC, d, e);
      sb_check(e, "read of 0xFFC did not raise PSLVERR");
    end
  endtask

  function void report_phase(uvm_phase phase);
    uvm_report_server rs = uvm_report_server::get_server();
    string tag = is_ral_test ? "RAL" : "SB";
    if (fails == 0 && checks > 0 && rs.get_severity_count(UVM_ERROR) == 0 && rs.get_severity_count(UVM_FATAL) == 0)
      $display("%s_PASS checks=%0d", tag, checks);
    else
      $display("%s_FAIL checks=%0d fails=%0d", tag, checks, fails);
  endfunction
endclass
