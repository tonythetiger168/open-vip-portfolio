#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""gen_uvm_agents.py [VIP ...] -- (re)generate the UVM layer of the 29
template-built VIPs from tools/uvm_agents/<prefix>.py.

These VIPs shipped a placeholder agent (monitor sampled every clock, driver
ignored the handshakes, scoreboard compared sequence tags only). Each spec in
tools/uvm_agents/ describes one protocol: the transaction fields, how the
driver runs one item against the DUT model in tb/top_tb.sv, how the monitor
rebuilds items from the pins, and a reference model the scoreboard predicts
the DUT response with. This script renders the per-VIP files from a common
skeleton so the 29 agents share one architecture:

  driver   -> drv.ap : item as driven, with the response the driver saw
  monitor  -> mon.ap : item rebuilt from the bus (request + DUT response)
  scoreboard: predict(copy of the monitor item) == monitor item  (DUT check)
              driver item == monitor item, in order               (agent check)
  <prefix>_func_test : directed + random traffic, prints SB_PASS checks=<n>

Files written under $VIPS_DIR/<VIP> (default build/vips): <p>/<p>_defs.sv,
_transaction/_config/_driver/_monitor/_agent/_sequences/_checker/_coverage.svh,
env/<p>_env.sv, tests/<p>_tests.sv (and the interface when a spec replaces
it). Repack with tools/pack_vips.sh afterwards.
"""
import os, sys, glob, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIPS = os.environ.get("VIPS_DIR", os.path.join(ROOT, "build", "vips"))
SPECS = os.path.join(ROOT, "tools", "uvm_agents")
sys.path.insert(0, SPECS)   # specs import _lib (shared SV snippets)

LICENSE = """// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
"""


def ind(text, n):
    """Indent every non-empty line of ``text`` by ``n`` spaces."""
    pad = " " * n
    return "\n".join(pad + l if l.strip() else "" for l in text.strip("\n").splitlines())


def header(fname, desc):
    return LICENSE + "\n// %s -- %s\n\n" % (fname, desc)


# ---------------------------------------------------------------- fields ----
# Spec fields: (decl, name, role[, flags]) where role is
#   req  : request, driven by the agent (rand unless queue or flags has "norand")
#   rsp  : DUT response (filled by driver/monitor/predictor), compared
#   info : bookkeeping, copied but never compared
# flags: "q" = queue of ``decl`` elements, "norand" = not randomised,
#        "rand" = randomised although not a request field (e.g. gaps, seeds).

def fields(spec):
    out = []
    for f in spec["fields"]:
        decl, name, role = f[:3]
        flags = f[3] if len(f) > 3 else ""
        out.append(dict(decl=decl, name=name, role=role, q="q" in flags,
                        rand=((role == "req" or "rand" in flags) and "q" not in flags and "norand" not in flags)))
    return out


def gen_transaction(s):
    p, F = s["p"], fields(s)
    decl = []
    for role, title in (("req", "request (driven by the agent)"),
                        ("rsp", "response (returned by the DUT)"),
                        ("info", "bookkeeping (not compared)")):
        grp = [f for f in F if f["role"] == role]
        if not grp:
            continue
        decl.append("// " + title)
        for f in grp:
            decl.append("%s%s %s%s;" % ("rand " if f["rand"] else "", f["decl"], f["name"],
                                       "[$]" if f["q"] else ""))
    decl.append("int unsigned tag;   // sequence number (driver/monitor order)")
    copy = "\n".join("%s = rhs_.%s;" % (f["name"], f["name"]) for f in F)

    def eq(sel):
        lines = []
        for f in sel:
            n = f["name"]
            if f["q"]:
                lines.append("if (%s.size() != rhs_.%s.size()) return 0;" % (n, n))
                lines.append("foreach (%s[i]) if (%s[i] != rhs_.%s[i]) return 0;" % (n, n, n))
            else:
                lines.append("if (%s != rhs_.%s) return 0;" % (n, n))
        return "\n".join(lines) or "// no fields"
    req = [f for f in F if f["role"] == "req"]
    cmp_all = [f for f in F if f["role"] in ("req", "rsp")]
    fmt, args = [], []
    for f in F:
        if f["role"] == "info":
            continue
        if f["q"]:
            fmt.append(f["name"] + "=%s")
            args.append("qstr_%s()" % f["name"])
        else:
            fmt.append(f["name"] + "=0x%0h")
            args.append(f["name"])
    qfuncs = []
    for f in F:
        if f["q"]:
            qfuncs.append("""function string qstr_{n}();
  string s = $sformatf("[%0d]{{", {n}.size());
  foreach ({n}[i]) begin
    if (i == 8) begin s = {{s, " ..."}}; break; end
    s = {{s, $sformatf(" %0h", {n}[i])}};
  end
  return {{s, " }}"}};
endfunction""".format(n=f["name"]))
    body = """class {p}_transaction extends uvm_sequence_item;
  `uvm_object_utils({p}_transaction)

{decl}
{members}
{constraints}
  function new(string name = "{p}_transaction"); super.new(name); endfunction

{functions}
  function void do_copy(uvm_object rhs);
    {p}_transaction rhs_;
    if (!$cast(rhs_, rhs)) `uvm_fatal("COPY", "cast failed")
    super.do_copy(rhs);
{copy}
    tag = rhs_.tag;
  endfunction

  // request and response fields
  function bit do_compare(uvm_object rhs, uvm_comparer comparer);
    {p}_transaction rhs_;
    if (!$cast(rhs_, rhs)) return 0;
{eq_all}
    return 1;
  endfunction

  // request fields only (driver view vs monitor view when the driver does
  // not see the DUT response)
  function bit req_equal({p}_transaction rhs_);
{eq_req}
    return 1;
  endfunction

{qfuncs}
  function string convert2string();
    return $sformatf("{P}{{tag=%0d {fmt}}}", tag, {args});
  endfunction
endclass
""".format(p=p, P=s["P"], decl=ind("\n".join(decl), 2),
           members=("\n" + ind(s.get("tr_members", ""), 2) + "\n") if s.get("tr_members") else "",
           constraints=("\n" + ind(s.get("constraints", ""), 2) + "\n") if s.get("constraints") else "",
           functions=(ind(s.get("tr_functions", ""), 2) + "\n") if s.get("tr_functions") else "",
           copy=ind(copy, 4), eq_all=ind(eq(cmp_all), 4), eq_req=ind(eq(req), 4),
           qfuncs=(ind("\n\n".join(qfuncs), 2) + "\n") if qfuncs else "",
           fmt=" ".join(fmt), args=", ".join(args))
    return header(p + "_transaction.svh", s["P"] + " transaction") + body


def gen_defs(s):
    p = s["p"]
    return header(p + "_defs.sv", s["P"] + " shared type definitions") + """package {p}_defs_pkg;

  typedef enum bit [1:0] {{{U}_OK, {U}_ERR}} {p}_status_e;
{defs}
endpackage
""".format(p=p, U=p.upper(), defs=("\n" + ind(s["defs"], 2) + "\n") if s.get("defs") else "")


def gen_config(s):
    p = s["p"]
    return header(p + "_config.svh", s["P"] + " agent configuration") + """class {p}_config extends uvm_object;
  `uvm_object_utils({p}_config)
  uvm_active_passive_enum is_active = UVM_ACTIVE;
  bit coverage_enable = 1;
  bit checks_enable   = 1;
  int unsigned num_items      = 32;     // random items per base sequence
  int unsigned timeout_cycles = {timeout};   // handshake / response watchdog
{extra}
  function new(string name = "{p}_config"); super.new(name); endfunction
endclass
""".format(p=p, timeout=s.get("timeout", 1000), extra=ind(s.get("cfg", ""), 2))


def gen_driver(s):
    p = s["p"]
    return header(p + "_driver.svh", s["P"] + " driver: " + s.get("drv_desc", "drives one item per protocol transfer")) + """class {p}_driver extends uvm_driver #({p}_transaction);
  `uvm_component_utils({p}_driver)

  uvm_analysis_port #({p}_transaction) ap;  // items as driven (+ response seen)
  int unsigned item_cnt = 0;

  virtual {p}_if vif;
  {p}_config cfg;
{members}
  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual {p}_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "{p}: virtual interface not set")
    if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg))
      cfg = {p}_config::type_id::create("cfg");
  endfunction

  task run_phase(uvm_phase phase);
    {p}_transaction rsp_item;
    drive_idle();
    wait (vif.rst_n === 1'b1);
    repeat (4) @(vif.drv_cb);
{bg}
    forever begin
      seq_item_port.get_next_item(req);
      req.tag = item_cnt++;
      `uvm_info("DRV", {{"drive: ", req.convert2string()}}, UVM_HIGH)
      drive_item(req);
      $cast(rsp_item, req.clone());
      ap.write(rsp_item);
      seq_item_port.item_done();
    end
  endtask

  // bus idle / reset values
  task drive_idle();
{idle}
  endtask

  task drive_item({p}_transaction t);
{item}
  endtask
{tasks}
endclass
""".format(p=p, members=("\n" + ind(s.get("drv_members", ""), 2) + "\n") if s.get("drv_members") else "",
           bg=("    fork\n" + ind(s["drv_bg"], 6) + "\n    join_none") if s.get("drv_bg") else "",
           idle=ind(s["drv_idle"], 4), item=ind(s["drv_item"], 4),
           tasks=("\n" + ind(s.get("drv_tasks", ""), 2)) if s.get("drv_tasks") else "")


def gen_monitor(s):
    p = s["p"]
    return header(p + "_monitor.svh", s["P"] + " monitor: " + s.get("mon_desc", "rebuilds items from the bus")) + """class {p}_monitor extends uvm_monitor;
  `uvm_component_utils({p}_monitor)

  virtual {p}_if vif;
  uvm_analysis_port #({p}_transaction) ap;
  {p}_config cfg;
  int unsigned n_obs = 0;
{members}
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap = new("ap", this);
    if (!uvm_config_db#(virtual {p}_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "{p}: virtual interface not set")
    if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg))
      cfg = {p}_config::type_id::create("cfg");
  endfunction

  task run_phase(uvm_phase phase);
    wait (vif.rst_n === 1'b1);
    begin
{run}
    end
  endtask

  function void publish({p}_transaction t);
    t.tag = n_obs++;
    `uvm_info("MON", {{"observed: ", t.convert2string()}}, UVM_HIGH)
    ap.write(t);
  endfunction
{tasks}
endclass
""".format(p=p, members=("\n" + ind(s.get("mon_members", ""), 2) + "\n") if s.get("mon_members") else "",
           run=ind(s["mon_run"], 6),
           tasks=("\n" + ind(s.get("mon_tasks", ""), 2)) if s.get("mon_tasks") else "")


def gen_agent(s):
    p = s["p"]
    return header(p + "_agent.svh", s["P"] + " agent") + """class {p}_agent extends uvm_agent;
  `uvm_component_utils({p}_agent)

  {p}_sequencer sqr;
  {p}_driver    drv;
  {p}_monitor   mon;
  {p}_config    cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg)) begin
      cfg = {p}_config::type_id::create("cfg");
      uvm_config_db#({p}_config)::set(this, "*", "cfg", cfg);
    end
    is_active = cfg.is_active;
    mon = {p}_monitor::type_id::create("mon", this);
    if (is_active == UVM_ACTIVE) begin
      sqr = {p}_sequencer::type_id::create("sqr", this);
      drv = {p}_driver   ::type_id::create("drv", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (is_active == UVM_ACTIVE)
      drv.seq_item_port.connect(sqr.seq_item_export);
  endfunction
endclass
""".format(p=p)


def gen_sequences(s):
    p = s["p"]
    return header(p + "_sequences.svh", s["P"] + " sequences") + """// Random traffic: cfg.num_items constrained-random items.
class {p}_base_sequence extends uvm_sequence #({p}_transaction);
  `uvm_object_utils({p}_base_sequence)
  {p}_config cfg;
{members}
  function new(string name = "{p}_base_sequence"); super.new(name); endfunction

  task body();
    int n = (cfg != null) ? cfg.num_items : 32;
    repeat (n) begin
{before}
      req = {p}_transaction::type_id::create("req");
      start_item(req);
      if (!req.randomize(){rand_with})
        `uvm_error("RANDFAIL", "{p}_transaction randomize() failed")
{after}
      finish_item(req);{post}
    end
  endtask
{tasks}endclass

// Directed traffic: every transfer type and the corner cases of the DUT model.
class {p}_directed_sequence extends uvm_sequence #({p}_transaction);
  `uvm_object_utils({p}_directed_sequence)
  {p}_config cfg;

  function new(string name = "{p}_directed_sequence"); super.new(name); endfunction

  // new item with every field at its default (no randomize() needed)
  function {p}_transaction item();
    item = {p}_transaction::type_id::create("req");
  endfunction

  task send({p}_transaction t);
    start_item(t);
    finish_item(t);
  endtask

  task body();
    {p}_transaction t;
{directed}
  endtask
{tasks}endclass
""".format(p=p, members=("\n" + ind(s.get("seq_members", ""), 2) + "\n") if s.get("seq_members") else "",
           rand_with=(" with {%s}" % s["rand_with"]) if s.get("rand_with") else "",
           before=ind(s.get("seq_before", ""), 6),
           after=ind(s.get("seq_after", ""), 6), directed=ind(s["directed"], 4),
           post=("\n" + ind(s["seq_post"], 6)) if s.get("seq_post") else "",
           tasks=("\n" + ind(s["seq_tasks"], 2) + "\n") if s.get("seq_tasks") else "")


def gen_checker(s):
    p = s["p"]
    return header(p + "_checker.svh", s["P"] + " protocol checker on monitored items") + """class {p}_checker extends uvm_component;
  `uvm_component_utils({p}_checker)
  uvm_analysis_imp #({p}_transaction, {p}_checker) imp;
  int unsigned n_checked = 0, n_violations = 0;
  {p}_config cfg;
{members}
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    imp = new("imp", this);
    if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg))
      cfg = {p}_config::type_id::create("cfg");
  endfunction

  function void fail({p}_transaction t, string msg);
    n_violations++;
    `uvm_error("CHK", $sformatf("{P}: %s: %s", msg, t.convert2string()))
  endfunction

  function void write({p}_transaction t);
    if (!cfg.checks_enable) return;
    n_checked++;
    begin
{checks}
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("CHK", $sformatf("{P} checker: n_checked=%0d n_violations=%0d",
              n_checked, n_violations), UVM_LOW)
  endfunction
endclass
""".format(p=p, P=s["P"], members=("\n" + ind(s.get("chk_members", ""), 2) + "\n") if s.get("chk_members") else "",
           checks=ind(s["checks"], 6))


def gen_coverage(s):
    p = s["p"]
    return header(p + "_coverage.svh", s["P"] + " functional coverage") + """class {p}_coverage extends uvm_subscriber #({p}_transaction);
  `uvm_component_utils({p}_coverage)
  {p}_config cfg;
  {p}_transaction tr;

  covergroup {p}_cg;
{cps}
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    {p}_cg = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg))
      cfg = {p}_config::type_id::create("cfg");
  endfunction

  function void write({p}_transaction t);
    if (!cfg.coverage_enable) return;
    tr = t;
    {p}_cg.sample();
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("COV", $sformatf("{P} coverage: %0.1f%%", {p}_cg.get_inst_coverage()), UVM_LOW)
  endfunction
endclass
""".format(p=p, P=s["P"], cps=ind(s["coverage"], 4))


def gen_env(s):
    p = s["p"]
    drv_rsp = s.get("drv_rsp", True)
    ral = s.get("ral")
    return header(p + "_env.sv", s["P"] + " environment: reference-model scoreboard, checker, coverage") + """package {p}_env_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import common_pkg::*;
  import {p}_defs_pkg::*;
  import {p}_pkg::*;

  `uvm_analysis_imp_decl(_exp)
  `uvm_analysis_imp_decl(_obs)
{ral_classes}
  // Scoreboard. Every monitored item is checked against a reference model of
  // the DUT (predict() fills the expected response from the request fields);
  // in an active agent the driver's items are also matched in order against
  // the monitor's, so a transfer the DUT never completed, or one the
  // monitor decoded differently from how it was driven, is reported.
  class {p}_scoreboard extends uvm_scoreboard;
    `uvm_component_utils({p}_scoreboard)
    uvm_analysis_imp_exp #({p}_transaction, {p}_scoreboard) exp_ap;
    uvm_analysis_imp_obs #({p}_transaction, {p}_scoreboard) obs_ap;

    {p}_config cfg;
    {p}_transaction exp_q[$], obs_q[$];
    int unsigned n_checks = 0, n_matches = 0, n_mismatches = 0;
    bit active = 1;
{members}
    function new(string name, uvm_component parent);
      super.new(name, parent);
      exp_ap = new("exp_ap", this);
      obs_ap = new("obs_ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#({p}_config)::get(this, "", "cfg", cfg))
        cfg = {p}_config::type_id::create("cfg");
      active = (cfg.is_active == UVM_ACTIVE);
    endfunction

    // reference model: expected DUT response for request t (updates state)
    function void predict({p}_transaction t);
{predict}
    endfunction

    function void write_exp({p}_transaction t);
      exp_q.push_back(t);
      pair();
    endfunction

    function void write_obs({p}_transaction t);
      {p}_transaction p;
      $cast(p, t.clone());
      predict(p);
      n_checks++;
      if (p.compare(t)) n_matches++;
      else begin
        n_mismatches++;
        `uvm_error("SB", $sformatf("DUT response mismatch\\n  expected: %s\\n  observed: %s",
                   p.convert2string(), t.convert2string()))
      end
      if (active{skip}) begin
        obs_q.push_back(t);
        pair();
      end
    endfunction

    function void pair();
      while (exp_q.size() && obs_q.size()) begin
        {p}_transaction e = exp_q.pop_front();
        {p}_transaction o = obs_q.pop_front();
        n_checks++;
        if ({agree}) n_matches++;
        else begin
          n_mismatches++;
          `uvm_error("SB", $sformatf("driver/monitor disagree\\n  driven:   %s\\n  observed: %s",
                     e.convert2string(), o.convert2string()))
        end
      end
    endfunction

    function void check_phase(uvm_phase phase);
      if (exp_q.size() || obs_q.size())
        `uvm_error("SB", $sformatf("%0d driven / %0d observed items left unmatched at end of test",
                   exp_q.size(), obs_q.size()))
    endfunction

    function void report_phase(uvm_phase phase);
      `uvm_info("SB", $sformatf("{p} scoreboard: n_checks=%0d n_matches=%0d n_mismatches=%0d",
                n_checks, n_matches, n_mismatches), UVM_LOW)
    endfunction
  endclass

  class {p}_env extends uvm_env;
    `uvm_component_utils({p}_env)
    {p}_agent      agt;
    {p}_scoreboard sb;
    {p}_checker    chk;
    {p}_coverage   cov;
{ral_members}
    function new(string name, uvm_component parent); super.new(name, parent); endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      agt = {p}_agent     ::type_id::create("agt", this);
      sb  = {p}_scoreboard::type_id::create("sb",  this);
      chk = {p}_checker   ::type_id::create("chk", this);
      cov = {p}_coverage  ::type_id::create("cov", this);{ral_build}
    endfunction

    function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);
      if (agt.is_active == UVM_ACTIVE)
        agt.drv.ap.connect(sb.exp_ap);
      agt.mon.ap.connect(sb.obs_ap);
      agt.mon.ap.connect(chk.imp);
      agt.mon.ap.connect(cov.analysis_export);{ral_connect}
    endfunction
  endclass
endpackage
""".format(p=p, members=("\n" + ind(s.get("sb_members", ""), 4) + "\n") if s.get("sb_members") else "",
           predict=ind(s["predict"], 6),
           skip=(" && !(%s)" % s["pair_skip"]) if s.get("pair_skip") else "", agree="e.compare(o)" if drv_rsp else "e.req_equal(o)",
           ral_classes=gen_ral_classes(s) if ral else "",
           ral_members=RAL_MEMBERS.format(p=p) if ral else "",
           ral_build=RAL_BUILD.format(p=p) if ral else "",
           ral_connect=RAL_CONNECT if ral else "")


# ------------------------------------------------------------------- RAL ----
# A spec with ``ral=dict(n_regs=, reg2bus=, bus2reg=, desc=)`` gets a UVM
# register model of the DUT model's register file (n_regs 32-bit RW
# registers at byte address 4*i, reset 0), a reg adapter for its transaction,
# an explicit predictor fed by the monitor, and <p>_ral_test.

RAL_MEMBERS = """
    // UVM RAL: register model of the DUT model, frontdoor through the agent,
    // mirror kept by an explicit predictor fed by the monitor
    {p}_reg_block                         regmodel;
    {p}_reg_adapter                       reg_adapter;
    uvm_reg_predictor #({p}_transaction)  reg_predictor;
"""

RAL_BUILD = """
      regmodel = {p}_reg_block::type_id::create("regmodel");
      regmodel.configure(null, "");
      regmodel.build();
      regmodel.lock_model();
      reg_adapter   = {p}_reg_adapter::type_id::create("reg_adapter");
      reg_predictor = uvm_reg_predictor#({p}_transaction)::type_id::create("reg_predictor", this);"""

RAL_CONNECT = """
      regmodel.default_map.set_sequencer(agt.sqr, reg_adapter);
      regmodel.default_map.set_auto_predict(0);
      reg_predictor.map     = regmodel.default_map;
      reg_predictor.adapter = reg_adapter;
      agt.mon.ap.connect(reg_predictor.bus_in);"""


def gen_ral_classes(s):
    p, r = s["p"], s["ral"]
    return """
  // ---- UVM RAL model: {desc}
  class {p}_data_reg extends uvm_reg;
    `uvm_object_utils({p}_data_reg)
    rand uvm_reg_field DATA;
    function new(string name = "{p}_data_reg"); super.new(name, 32, UVM_NO_COVERAGE); endfunction
    virtual function void build();
      DATA = uvm_reg_field::type_id::create("DATA");
      //            parent size lsb access volatile reset has_reset rand individually_accessible
      DATA.configure(this, 32,  0,  "RW",  0,       32'h0, 1,        1,   1);
    endfunction
  endclass

  class {p}_reg_block extends uvm_reg_block;
    `uvm_object_utils({p}_reg_block)
    localparam int N_REGS = {n};
    rand {p}_data_reg REG[N_REGS];
    uvm_reg_map       map;
    function new(string name = "{p}_reg_block"); super.new(name, UVM_NO_COVERAGE); endfunction
    virtual function void build();
      map = create_map("map", 'h0, 4, UVM_LITTLE_ENDIAN, 1);
      default_map = map;
      foreach (REG[i]) begin
        REG[i] = {p}_data_reg::type_id::create($sformatf("REG%0d", i));
        REG[i].configure(this, null, "");
        REG[i].build();
        map.add_reg(REG[i], i * 4, "RW");
      end
    endfunction
  endclass

  // register access <-> {P} transaction (the driver fills the read data
  // into the request item, so no separate response is needed)
  class {p}_reg_adapter extends uvm_reg_adapter;
    `uvm_object_utils({p}_reg_adapter)
    function new(string name = "{p}_reg_adapter");
      super.new(name);
      supports_byte_enable = 0;
      provides_responses   = 0;
    endfunction
    virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
      {p}_transaction t = {p}_transaction::type_id::create("t");
{reg2bus}
      return t;
    endfunction
    virtual function void bus2reg(uvm_sequence_item bus_item, ref uvm_reg_bus_op rw);
      {p}_transaction t;
      if (!$cast(t, bus_item)) begin
        `uvm_fatal("RAL", "bus2reg: not a {p}_transaction")
        return;
      end
{bus2reg}
    endfunction
  endclass
""".format(p=p, P=s["P"], n=r["n_regs"], desc=r["desc"], reg2bus=ind(r["reg2bus"], 6),
           bus2reg=ind(r["bus2reg"], 6))


RAL_TEST = """
  // UVM RAL on the DUT model's register file (env regmodel):
  //   1. uvm_reg_hw_reset_seq  -- every register reads its reset value
  //   2. uvm_reg_bit_bash_seq  -- every bit of every register writes 0/1 and reads back
  //   3. pseudo-random write + mirror(UVM_CHECK) + read on every register
  // The scoreboard checks the same traffic against the reference model.
  // Uses no randomize(). Prints "RAL_PASS checks=<n>" when nothing was reported.
  class {p}_ral_test extends {p}_base_test;
    `uvm_component_utils({p}_ral_test)
    int unsigned checks;
    function new(string name, uvm_component parent); super.new(name, parent); endfunction

    task stimulus();
      uvm_reg_hw_reset_seq rst_seq;
      uvm_reg_bit_bash_seq bb_seq;
      uvm_status_e         status;
      uvm_reg_data_t       val, exp;
      {p}_reg_block        rm = env.regmodel;
      bit [31:0]           x = 32'h1357_9BDF;

      rst_seq = uvm_reg_hw_reset_seq::type_id::create("rst_seq");
      rst_seq.model = rm;
      rst_seq.start(null);
      checks += rm.N_REGS;

      bb_seq = uvm_reg_bit_bash_seq::type_id::create("bb_seq");
      bb_seq.model = rm;
      bb_seq.start(null);
      checks += rm.N_REGS * 32;

      foreach (rm.REG[i]) begin
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        rm.REG[i].write(status, x);
        if (status != UVM_IS_OK) `uvm_error("RAL", $sformatf("REG%0d write status %s", i, status.name()))
      end
      foreach (rm.REG[i]) begin
        exp = rm.REG[i].get_mirrored_value();
        rm.REG[i].mirror(status, UVM_CHECK);
        rm.REG[i].read(status, val);
        if (status != UVM_IS_OK || val != exp)
          `uvm_error("RAL", $sformatf("REG%0d read 0x%08h status %s, expected 0x%08h",
                     i, val, status.name(), exp))
        checks += 2;
      end
    endtask

    function void report_phase(uvm_phase phase);
      uvm_report_server rs = uvm_report_server::get_server();
      super.report_phase(phase);
      if (rs.get_severity_count(UVM_ERROR) + rs.get_severity_count(UVM_FATAL) == 0)
        $display("RAL_PASS checks=%0d", checks);
      else
        $display("RAL_FAIL errors=%0d", rs.get_severity_count(UVM_ERROR));
    endfunction
  endclass
"""


def gen_tests(s):
    p = s["p"]
    return header(p + "_tests.sv", s["P"] + " tests") + """package {p}_test_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import common_pkg::*;
  import {p}_defs_pkg::*;
  import {p}_pkg::*;
  import {p}_env_pkg::*;

  // constrained-random traffic (cfg.num_items items)
  class {p}_base_test extends uvm_test;
    `uvm_component_utils({p}_base_test)
    {p}_env env;
    {p}_config cfg;

    function new(string name, uvm_component parent); super.new(name, parent); endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      cfg = {p}_config::type_id::create("cfg");
      uvm_config_db#({p}_config)::set(this, "*", "cfg", cfg);
      env = {p}_env::type_id::create("env", this);
    endfunction

    virtual task stimulus();
      {p}_base_sequence seq = {p}_base_sequence::type_id::create("seq");
      seq.cfg = cfg;
      seq.start(env.agt.sqr);
    endtask

    task run_phase(uvm_phase phase);
      phase.raise_objection(this);
      stimulus();
      #({drain}ns);   // let the monitor see the last DUT response
      phase.drop_objection(this);
    endtask

    // pass criteria: scoreboard checked traffic and nothing was reported
    function void report_phase(uvm_phase phase);
      uvm_report_server rs = uvm_report_server::get_server();
      super.report_phase(phase);
      if (env.sb.n_checks == 0)
        `uvm_error("TEST", "scoreboard checked no traffic")
      else if (rs.get_severity_count(UVM_ERROR) == 0 && rs.get_severity_count(UVM_FATAL) == 0)
        $display("SB_PASS checks=%0d", env.sb.n_checks);
    endfunction
  endclass

  // directed corner cases, then random traffic; the test run on Verilator
  // by tools/run_uvm_tests.py
  class {p}_func_test extends {p}_base_test;
    `uvm_component_utils({p}_func_test)

    function new(string name, uvm_component parent); super.new(name, parent); endfunction

    task stimulus();
      {p}_directed_sequence dseq = {p}_directed_sequence::type_id::create("dseq");
      dseq.cfg = cfg;
      dseq.start(env.agt.sqr);
      super.stimulus();
    endtask
  endclass
{ral_test}endpackage
""".format(p=p, drain=s.get("drain_ns", 2000), ral_test=RAL_TEST.format(p=p) if s.get("ral") else "")


# ------------------------------------------------------------- scaffold ----
# Specs of VIPs that were created by this generator (rather than rewritten
# from a template zip) also carry the static part of the tree:
#   ports : [(dir, decl, name)] DUT pins, dir "in" (driven by the agent) or
#           "out" (driven by the DUT model); rst_n and clk are implicit
#   model : the DUT model module <p>_model (plain ports named as in ports)
#   sva   : body of <p>_compliance_checker (inputs: clk, rst_n, every port)
#   smoke : body of tb/smoke_func_tb.sv inside `ifdef VIP_SMOKE_FLATTENED
#   desc, family, about : README text
# ``pair_skip`` (any spec): expression on a monitored item ``t`` that the
# driver does not publish (e.g. a snoop the DUT starts); such items are still
# predicted and checked but not matched against the driver's items.
# and optionally ``interface`` (replaces the interface rendered from ports)
# and ``top_wires`` (extra lines in top_tb, e.g. open-drain bus resolution).

def port_decl(decl, name):
    return "%s %s" % (decl, name)


def gen_interface(s):
    p, ports = s["p"], s["ports"]
    sig = "\n".join("  %s;" % port_decl(d.replace("bit", "logic"), n) for _, d, n in ports)
    ins = [n for d, _, n in ports if d == "in"]
    outs = [n for d, _, n in ports if d == "out"]
    allp = [n for _, _, n in ports]
    return header(p + "_if.sv", s["P"] + " interface") + """interface {p}_if (input logic clk);
  logic rst_n;

{sig}

  modport DUT (input clk, rst_n{ins_m}{outs_m});
  modport MON (input clk, rst_n, {allp});

  clocking drv_cb @(posedge clk);
    input rst_n{outs_cb};
    inout {ins};   // driven by the agent, sampled back
  endclocking

  clocking mon_cb @(posedge clk);
    input rst_n, {allp};
  endclocking
endinterface
""".format(p=p, sig=sig, ins=", ".join(ins), allp=", ".join(allp),
           ins_m="".join(", input " + n for n in ins), outs_m="".join(", output " + n for n in outs),
           outs_cb="".join(", " + n for n in outs))


def gen_top(s):
    p, P, ports = s["p"], s["P"], s["ports"]
    guard = s["vip"].upper().replace("-", "_") + "_TB_SV"
    conn = ",\n    ".join(".%s(vif.%s)" % (n, n) for _, _, n in ports)
    return header("top_tb.sv", P + " testbench top with a functional " + P + " DUT model") + """`ifndef {g}
`define {g}
`include "uvm_macros.svh"
import uvm_pkg::*;
import common_pkg::*;
import {p}_defs_pkg::*;
import {p}_pkg::*;
import {p}_env_pkg::*;
import {p}_test_pkg::*;

module top_tb;
  logic clk = 0;
  always #5ns clk = ~clk;

  {p}_if vif(clk);

  initial begin
    vif.rst_n = 0;
    #100ns;
    vif.rst_n = 1;
  end
{wires}
  // DUT model: plain ports (flattened by smoke/flatten.py for L1b)
  {p}_model u_dut (
    .clk(vif.clk), .rst_n(vif.rst_n),
    {conn}
  );

  // Concurrent protocol checks
  {p}_compliance_checker u_chk (
    .clk(vif.clk), .rst_n(vif.rst_n),
    {conn}
  );

  initial begin
    uvm_config_db#(virtual {p}_if)::set(null, "*", "vif", vif);
    run_test();
  end
endmodule

{model}
`endif
""".format(g=guard, p=p, conn=conn, model=s["model"].strip("\n"),
           wires=("\n" + ind(s["top_wires"], 2) + "\n") if s.get("top_wires") else "")


def gen_sva(s):
    p, P = s["p"], s["P"]
    ports = ", ".join("input %s %s" % (d.replace("bit", "logic"), n)
                      for _, d, n in s["ports"])
    return header(p + "_compliance_checker.sv", P + " concurrent assertion checks (bindable)") + \
        "module {p}_compliance_checker\n  (input logic clk, input logic rst_n, {ports});\n\n{body}\nendmodule\n".format(
            p=p, ports=ports, body=ind(s["sva"], 2))


def gen_smoke(s):
    p, P = s["p"], s["P"]
    return ("// SPDX-License-Identifier: Apache-2.0\n"
            "// Copyright 2026 VIP Portfolio Contributors\n"
            "// Functional smoke testbench (%s DUT model)\n`timescale 1ns/1ps\n//\n"
            "// Self-checking directed test of the flattened %s_model; prints FUNC_PASS/FUNC_FAIL.\n\n"
            "module smoke_func_tb;\n`ifdef VIP_SMOKE_FLATTENED\n%s\n`endif\nendmodule\n") % (P, p, ind(s["smoke"], 2))


def gen_pkg(s):
    p, P = s["p"], s["P"]
    inc = "\n".join('  `include "%s_%s.svh"' % (p, x) for x in
                    ("transaction", "config", "sequencer", "driver", "monitor", "agent",
                     "sequences", "checker", "coverage"))
    return header(p + "_pkg.sv", P + " UVM VIP package") + """package {p}_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  import {p}_defs_pkg::*;
  export {p}_defs_pkg::*;

{inc}
endpackage
""".format(p=p, inc=inc)


def gen_sequencer(s):
    p, P = s["p"], s["P"]
    return header(p + "_sequencer.svh", P + " sequencer") + """class {p}_sequencer extends uvm_sequencer #({p}_transaction);
  `uvm_component_utils({p}_sequencer)
  function new(string name = "{p}_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass
""".format(p=p)


COMMON_PKG = header("common_pkg.sv", "shared typedefs") + """package common_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  typedef enum bit [1:0] {VIP_OK, VIP_WARN, VIP_ERROR, VIP_FATAL} vip_status_e;

  class vip_config extends uvm_object;
    `uvm_object_utils(vip_config)
    int unsigned seed = 32'hC0FFEE;
    bit coverage_enable = 1;
    function new(string name = "vip_config"); super.new(name); endfunction
  endclass
endpackage
"""


def gen_readme(s):
    p, P, v = s["p"], s["P"], s["vip"]
    return """# {P} UVM VIP ({v})

{desc}

{about}

## Structure

- `{d}/` -- VIP core: interface, agent (driver/monitor/sequencer), sequences,
  protocol checker, functional coverage, `sva/{p}_compliance_checker.sv` SVA checks
- `common/` -- shared package
- `env/` -- environment: scoreboard with a reference model of the DUT (checks
  every monitored transfer; in an active agent also matches the driver's items
  against the monitor's), protocol checker, functional coverage
- `tests/` -- `{p}_base_test` (constrained-random), `{p}_func_test` (directed +
  random)
- `tb/top_tb.sv` -- UVM testbench top + behavioural {P} DUT model `{p}_model` (plain
  ports; flattened by `smoke/flatten.py` for the open-toolchain L1b smoke gate)
- `tb/smoke_func_tb.sv` -- self-checking directed test of the DUT model

The UVM layer, interface, testbench top and SVA are generated by
`tools/gen_uvm_agents.py` from `tools/uvm_agents/{p}.py` in the portfolio repo.

## Quality gates

- L1a elaboration: `python3 tools/elab_scan.py vips/{v}` -> `ELAB_ERRORS=0`
- L1b smoke: `bash smoke/run_smoke.sh {v}` -> `SMOKE_PASS`
- L1c functional: `python3 tools/run_func_tests.py {v}` -> `FUNC_PASS`
- L1d UVM (Verilator + uvm-core): `python3 tools/run_uvm_tests.py {v}` -> `UVM_PASS`

## License

Apache-2.0 (SPDX-License-Identifier: Apache-2.0).
""".format(P=P, v=v, p=p, d=s["dir"], desc=s["desc"], about=s.get("about", "").strip())


def scaffold(s, root):
    """Static files of a generator-created VIP (spec has ``model``)."""
    p, d = s["p"], s["dir"]
    out = {
        "README.md": gen_readme(s),
        "common/common_pkg.sv": COMMON_PKG,
        "%s/%s_pkg.sv" % (d, p): gen_pkg(s),
        "%s/%s_sequencer.svh" % (d, p): gen_sequencer(s),
        "%s/sva/%s_compliance_checker.sv" % (d, p): gen_sva(s),
        "tb/top_tb.sv": gen_top(s),
        "tb/smoke_func_tb.sv": gen_smoke(s),
    }
    if not s.get("interface"):
        out["%s/%s_if.sv" % (d, p)] = gen_interface(s)
    for rel, text in out.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    for sub in ("env", "tests"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    return len(out)


def load_spec(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SPEC


def generate(s, root):
    p = s["p"]
    out = {
        "%s/%s_defs.sv" % (s["dir"], p): gen_defs(s),
        "%s/%s_transaction.svh" % (s["dir"], p): gen_transaction(s),
        "%s/%s_config.svh" % (s["dir"], p): gen_config(s),
        "%s/%s_driver.svh" % (s["dir"], p): gen_driver(s),
        "%s/%s_monitor.svh" % (s["dir"], p): gen_monitor(s),
        "%s/%s_agent.svh" % (s["dir"], p): gen_agent(s),
        "%s/%s_sequences.svh" % (s["dir"], p): gen_sequences(s),
        "%s/%s_checker.svh" % (s["dir"], p): gen_checker(s),
        "%s/%s_coverage.svh" % (s["dir"], p): gen_coverage(s),
        "env/%s_env.sv" % p: gen_env(s),
        "tests/%s_tests.sv" % p: gen_tests(s),
    }
    if s.get("interface"):
        out["%s/%s_if.sv" % (s["dir"], p)] = header(p + "_if.sv", s["P"] + " interface") + s["interface"].lstrip("\n")
    for rel, text in out.items():
        path = os.path.join(root, rel)
        if not os.path.isdir(os.path.dirname(path)):
            raise SystemExit("ERROR: %s: no directory for %s" % (s["vip"], rel))
        with open(path, "w") as f:
            f.write(text)
    return len(out)


def patch_files(s, root):
    """Spec ``patches``: {relative path: [(old, new), ...]} applied to files
    the generator does not own (SVA checkers that never ran on a simulator
    before). Idempotent: a pair whose ``new`` text is present is skipped."""
    for rel, pairs in s.get("patches", {}).items():
        path = os.path.join(root, rel)
        txt = open(path).read()
        for old, new in pairs:
            if new in txt:
                continue
            if old not in txt:
                raise SystemExit("ERROR: %s: patch target not found in %s: %r" % (s["vip"], rel, old[:60]))
            txt = txt.replace(old, new)
        with open(path, "w") as f:
            f.write(txt)


def patch_readme(s, root):
    """Describe the generated UVM layer and the L1d gate in the VIP README
    (idempotent)."""
    path = os.path.join(root, "README.md")
    if not os.path.exists(path):
        return
    txt = open(path).read()
    p = s["p"]
    txt = txt.replace("- `env/` -- environment with end-to-end scoreboard",
                      "- `env/` -- environment: scoreboard with a reference model of the DUT (checks\n"
                      "  every monitored transfer; in an active agent also matches the driver's items\n"
                      "  against the monitor's), protocol checker, functional coverage")
    old = "- `tests/` -- `%s_base_test`" % p
    if old in txt and "%s_func_test" % p not in txt:
        txt = txt.replace(old, "- `tests/` -- `%s_base_test` (constrained-random), `%s_func_test` (directed +\n"
                               "  random)" % (p, p))
    gate = "- L1d UVM (Verilator + uvm-core): `python3 tools/run_uvm_tests.py %s` -> `UVM_PASS`" % s["vip"]
    if gate not in txt:
        lines = txt.splitlines()
        for i, l in enumerate(lines):
            if l.startswith("- L1b smoke:"):
                lines.insert(i + 1, gate)
                break
        txt = "\n".join(lines) + "\n"
    with open(path, "w") as f:
        f.write(txt)


def all_specs():
    return {s["vip"]: s for s in (load_spec(f) for f in sorted(glob.glob(os.path.join(SPECS, "[!_]*.py"))))}


def main(argv):
    specs = all_specs()
    names = argv or sorted(specs)
    for v in names:
        if v not in specs:
            raise SystemExit("ERROR: no spec for %s (have: %s)" % (v, ", ".join(sorted(specs))))
        root = os.path.join(VIPS, v)
        n = 0
        if specs[v].get("model"):
            n += scaffold(specs[v], root)
        elif not os.path.isdir(root):
            raise SystemExit("ERROR: %s not found (run tools/extract_vips.sh)" % root)
        n += generate(specs[v], root)
        patch_files(specs[v], root)
        if not specs[v].get("model"):
            patch_readme(specs[v], root)
        print("generated %s (%d files)" % (v, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
