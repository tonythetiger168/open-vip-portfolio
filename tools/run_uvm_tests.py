#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""run_uvm_tests.py [VIP ...] [--test NAME] [--smoke] -- build a VIP's UVM
testbench with Verilator and run its UVM tests (default: the RAL test).

The UVM environment (agent, env, register model, tests, tb/top_tb.sv) is
compiled against Accellera uvm-core ($UVM_CORE, else <repo>/uvm-core/src)
with ``verilator --binary --timing +define+UVM_NO_DPI``. Verilator needs no
licence, but builds take a few minutes per VIP (uvm-core is recompiled each
time) and its constraint solver (z3, from tools/install_tools.sh) does not
handle every inline constraint the random sequences use, so only tests that
need no randomize() are run by default.

A test passes when the simulation finishes, reports no UVM_ERROR/UVM_FATAL
and no UVM_WARNING from the VIP's own code (its protocol checkers / SVA warn
rather than error, and legal register traffic must not trip them), and
prints ``RAL_PASS checks=<n>`` (RAL tests) or ``SB_PASS checks=<n>`` (the
agent tests of the template-built VIPs: scoreboard checks against the
reference model of the DUT). Output: one line per test
``UVM_PASS|UVM_FAIL|UVM_ERROR <VIP>/<test> -- detail`` and, for a full run,
``uvm_report.csv`` (vip,test,result,checks,detail) in the repo root.
Exit status is non-zero when any test fails or cannot be built.

--smoke runs the VIPs that have no checked suite above: every .sv file of the
VIP is compiled in tools/elab_scan.py order, packages before their importers
(top: the module that calls run_test()), and the first test derived from the
VIP's base test (``class ... extends uvm_test``; the base test itself usually
starts no sequence), or --test, is run. There is no pass marker to wait for,
so this only shows that the environment builds, runs its sequence to
completion (past time 0) and reports no error: one line per VIP
``UVM_SMOKE_PASS|UVM_SMOKE_WARN|UVM_SMOKE_FAIL|UVM_SMOKE_ERROR <VIP>/<test>``
(WARN: finished without errors, but the VIP's own checkers warned) and
``uvm_smoke_report.csv`` (a run on some VIPs updates their rows; tools/
gen_uvm_smoke_doc.py renders it as docs/UVM_SMOKE.md).
Env: VIPS_DIR (default build/vips), VERILATOR (default verilator on PATH),
     UVM_JOBS (verilator -j, default nproc).
"""
import os, re, sys, csv, glob, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIPS = os.environ.get("VIPS_DIR", os.path.join(ROOT, "build", "vips"))
UVM = os.environ.get("UVM_CORE", os.path.join(ROOT, "uvm-core", "src"))
WORK = os.path.join(ROOT, "build", "uvm")
REPORT = os.path.join(ROOT, "uvm_report.csv")
SMOKE_REPORT = os.path.join(ROOT, "uvm_smoke_report.csv")

# AMBA family: one shared amba_vip_if / amba_vip_pkg layout per VIP
AMBA_FILES = ["rtl/amba_vip_if.sv", "vip/base/amba_vip_pkg.sv", "env/amba_env.sv",
              "tests/amba_tests.sv", "tb/top_tb.sv"]
AMBA_INCS = ["vip/base", "vip/apb", "vip/ahb", "vip/axi", "rtl", "rtl/sva", "env", "tests", "tb"]

# VIPs with a UVM register model and the tests to run on Verilator
SUITES = {
    "APB-VIP": dict(files=AMBA_FILES, incs=AMBA_INCS, tests=["amba_ral_test"]),
    "AHB-VIP": dict(files=AMBA_FILES, incs=AMBA_INCS, tests=["amba_ral_test"]),
    "AXI-VIP": dict(files=AMBA_FILES, incs=AMBA_INCS, tests=["amba_ral_test"]),
    "OCP-VIP": dict(files=["common/common_pkg.sv", "ocp/ocp_defs.sv", "ocp/ocp_if.sv",
                           "ocp/ocp_pkg.sv", "env/ocp_env.sv", "tests/ocp_tests.sv",
                           "tb/top_tb.sv"],
                    incs=["common", "ocp", "env", "tests", "tb"], tests=["ocp_ral_test"]),
    "TileLink-VIP": dict(files=["common/common_pkg.sv", "tilelink/tilelink_defs.sv",
                                "tilelink/tilelink_if.sv", "tilelink/tilelink_pkg.sv",
                                "env/tilelink_env.sv", "tests/tilelink_tests.sv", "tb/top_tb.sv"],
                         incs=["common", "tilelink", "env", "tests", "tb"],
                         tests=["tilelink_ral_test"]),
}

# The template-built agents (tools/uvm_agents/<prefix>.py, rendered by
# tools/gen_uvm_agents.py) share one layout: <dir>/<p>_{defs,if,pkg}.sv,
# env/<p>_env.sv, tests/<p>_tests.sv, <dir>/sva/*.sv. Their <p>_func_test runs
# directed + random traffic against the tb/top_tb.sv DUT model.
def agent_suites():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gen_uvm_agents import all_specs
    out = {}
    for vip, s in all_specs().items():
        d, p = s["dir"], s["p"]
        out[vip] = dict(
            files=["common/common_pkg.sv", "%s/%s_defs.sv" % (d, p), "%s/%s_if.sv" % (d, p),
                   "%s/%s_pkg.sv" % (d, p), "env/%s_env.sv" % p, "tests/%s_tests.sv" % p,
                   "%s/sva/%s_compliance_checker.sv" % (d, p), "tb/top_tb.sv"],
            incs=[d, d + "/sva", "common", "env", "tests", "tb"],
            tests=["%s_func_test" % p] + (["%s_ral_test" % p] if s.get("ral") else []))
    return out

SUITES.update(agent_suites())

def pkg_order(files):
    """Stable reorder so that a file declaring ``package P`` comes before every
    file that imports P (elab_scan's order puts interfaces first; pyslang
    tolerates a forward package reference, Verilator does not)."""
    prov, need = {}, {}
    for f in files:
        src = re.sub(r"//[^\n]*", "", open(f, errors="replace").read())
        prov[f] = set(re.findall(r"^\s*package\s+(\w+)\s*;", src, re.M))
        need[f] = set(re.findall(r"\bimport\s+(\w+)\s*::", src)) - prov[f]
    out, done = [], set()
    def visit(f, stack):
        if f in done or f in stack:
            return
        stack.add(f)
        for g in files:
            if g != f and prov[g] & need[f]:
                visit(g, stack)
        done.add(f)
        out.append(f)
    for f in files:
        visit(f, set())
    return out

def smoke_suite(vip):
    """Generic suite for --smoke: the elab_scan file order, every directory as
    an include path, and the VIP's base test (None when it has no UVM test)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import elab_scan
    vdir = os.path.join(VIPS, vip)
    files, allsv = elab_scan.ordered(vdir)
    base, top = None, "top_tb"
    for f in sorted(glob.glob(os.path.join(vdir, "**", "*.sv*"), recursive=True)):
        src = open(f, errors="replace").read()
        m = re.search(r"\bclass\s+(\w+)\s+extends\s+uvm_test\b", src)
        if m and base is None:
            base = m.group(1)
        # the top module is the one that calls run_test()
        m = re.search(r"^\s*module\s+(\w+)(?:(?!^\s*endmodule).)*?\brun_test\s*\(", src, re.M | re.S)
        if m:
            top = m.group(1)
    # the base test usually starts no sequence: run the first test derived from it
    test = base
    if base:
        for f in sorted(glob.glob(os.path.join(vdir, "**", "*.sv*"), recursive=True)):
            m = re.search(r"\bclass\s+(\w+)\s+extends\s+%s\b" % base, open(f, errors="replace").read())
            if m:
                test = m.group(1)
                break
    return dict(top=top, files=[os.path.relpath(f, vdir) for f in pkg_order(files[1:])],
                incs=sorted({os.path.relpath(os.path.dirname(f), vdir) for f in allsv}),
                tests=[test] if test else [])

def run(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        out = e.stdout if isinstance(e.stdout, str) else ""
        return 124, out + "\nTIMEOUT"

def build(vip, suite, extra=()):
    """Verilate the VIP's UVM testbench; ``extra``: more verilator options
    (tools/coverage.py adds --coverage-user)."""
    vdir = os.path.join(VIPS, vip)
    work = os.path.join(WORK, vip)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    cmd = [os.environ.get("VERILATOR", "verilator"), "--binary", "--timing",
           "-j", os.environ.get("UVM_JOBS", str(os.cpu_count() or 1)),
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", suite.get("top", "top_tb"),
           "-Mdir", os.path.join(work, "obj"), "+define+UVM_NO_DPI",
           "+incdir+" + UVM] + list(extra) + ["+incdir+" + os.path.join(vdir, d) for d in suite["incs"]] \
          + [os.path.join(UVM, "uvm_pkg.sv")] + [os.path.join(vdir, f) for f in suite["files"]]
    rc, out = run(cmd, work, 3600)
    with open(os.path.join(work, "build.log"), "w") as f:
        f.write(out)
    exe = os.path.join(work, "obj", "V" + suite.get("top", "top_tb"))
    if rc != 0 or not os.path.exists(exe):
        errs = [l for l in out.splitlines() if l.startswith("%Error")]
        return None, (errs[0] if errs else "verilator exit %d" % rc)[:300]
    return exe, ""

def classify(rc, out):
    errs = int((re.search(r'^UVM_ERROR\s*:\s*(\d+)', out, re.M) or [0, 0])[1])
    fatals = int((re.search(r'^UVM_FATAL\s*:\s*(\d+)', out, re.M) or [0, 0])[1])
    # warnings raised by the VIP itself (protocol checkers / SVA report with
    # `uvm_warning); uvm-core's own UVM_NO_DPI notices are not counted
    warns = [l for l in out.splitlines()
             if l.startswith("UVM_WARNING ") and not re.match(r'UVM_WARNING\s*:', l)
             and not l.startswith("UVM_WARNING uvm-core") and "/uvm-core/" not in l.split("@")[0]]
    m = re.search(r'^(?:RAL|SB)_PASS checks=(\d+)', out, re.M)
    if rc == 0 and m and errs == 0 and fatals == 0 and not warns:
        return "PASS", int(m.group(1)), ""
    first = [l for l in out.splitlines() if l.startswith(("UVM_ERROR ", "UVM_FATAL "))
             and not re.match(r'UVM_(ERROR|FATAL)\s*:', l)] + warns
    detail = "rc=%d UVM_ERROR=%d UVM_FATAL=%d VIP_WARNINGS=%d" % (rc, errs, fatals, len(warns))
    if "TIMEOUT" in out:
        detail += " timeout"
    if first:
        detail += ": " + first[0]
    return "FAIL", 0, detail[:300]

def classify_smoke(rc, out):
    st, n, detail = classify(rc, out + "\nSB_PASS checks=0")
    if st == "PASS":
        if "UVM_FATAL :" not in out:
            return "FAIL", 0, "no UVM report summary"
        if re.search(r"\$finish at 0s", out):
            return "FAIL", 0, "finished at time 0: the test drove no traffic"
        return "PASS", 0, ""
    if rc == 0 and "UVM_FATAL :" in out and re.search(r"UVM_ERROR=0 UVM_FATAL=0 VIP_WARNINGS=[1-9]", detail):
        return "WARN", 0, detail
    return st, n, detail

def main_smoke(argv, tests_override):
    names = argv or sorted(d for d in os.listdir(VIPS) if d not in SUITES
                           and os.path.isdir(os.path.join(VIPS, d)))
    rows, bad = [], 0
    for vip in names:
        suite = smoke_suite(vip)
        tests = tests_override or suite["tests"]
        if not tests:
            rows.append((vip, "", "NONE", 0, "no uvm_test class"))
            print("UVM_SMOKE_NONE %s" % vip)
            continue
        exe, err = build(vip, suite)
        for t in tests:
            if exe is None:
                st, detail = "ERROR", err
            else:
                rc, out = run([exe, "+UVM_TESTNAME=" + t], os.path.dirname(exe), 900)
                with open(os.path.join(WORK, vip, "run_%s.log" % t), "w") as f:
                    f.write(out)
                st, _, detail = classify_smoke(rc, out)
            rows.append((vip, t, st, 0, detail))
            bad += st not in ("PASS", "WARN")
            print("UVM_SMOKE_%s %s/%s%s" % (st, vip, t, (" -- " + detail) if detail else ""))
            sys.stdout.flush()
        shutil.rmtree(os.path.join(WORK, vip, "obj"), ignore_errors=True)
    if tests_override is None:
        # a run on some VIPs updates their rows in the existing report
        keep = []
        if argv and os.path.exists(SMOKE_REPORT):
            done = {r[0] for r in rows}
            with open(SMOKE_REPORT) as f:
                keep = [r for r in list(csv.reader(f))[1:] if r and r[0] not in done]
        with open(SMOKE_REPORT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["vip", "test", "result", "checks", "detail"])
            w.writerows(sorted(keep + [list(r) for r in rows], key=lambda r: r[0].lower()))
    return 1 if bad else 0

def main(argv):
    tests_override = None
    if "--test" in argv:
        i = argv.index("--test")
        tests_override = [argv[i + 1]]
        argv = argv[:i] + argv[i + 2:]
    if not os.path.exists(os.path.join(UVM, "uvm_pkg.sv")):
        print("ERROR: uvm-core not found at %s (set UVM_CORE)" % UVM, file=sys.stderr)
        return 2
    if "--smoke" in argv:
        return main_smoke([a for a in argv if a != "--smoke"], tests_override)
    names = argv or sorted(SUITES)
    rows, bad = [], 0
    for vip in names:
        if vip not in SUITES:
            print("UVM_NONE %s" % vip)
            continue
        suite = SUITES[vip]
        exe, err = build(vip, suite)
        for t in tests_override or suite["tests"]:
            if exe is None:
                st, n, detail = "ERROR", 0, err
            else:
                rc, out = run([exe, "+UVM_TESTNAME=" + t], os.path.dirname(exe), 1800)
                with open(os.path.join(WORK, vip, "run_%s.log" % t), "w") as f:
                    f.write(out)
                st, n, detail = classify(rc, out)
            rows.append((vip, t, st, n, detail))
            bad += st != "PASS"
            print("UVM_%s %s/%s [checks=%d]%s" % (st, vip, t, n, (" -- " + detail) if detail else ""))
            sys.stdout.flush()
    if not argv and tests_override is None:
        with open(REPORT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["vip", "test", "result", "checks", "detail"])
            w.writerows(rows)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
