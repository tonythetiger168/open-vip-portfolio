#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""coverage.py [-j J] [VIP ...] -- measure the code coverage the functional
tests reach on each VIP's DUT model, with Verilator.

Every functional test of tools/run_func_tests.py is rebuilt with
``verilator --binary --timing --coverage-line --coverage-toggle
--coverage-expr --coverage-user`` (same compile candidates and flags as the
runner's Verilator flow) and run; the per-test ``coverage.dat`` files are
merged per VIP with ``verilator_coverage``. Only points in the code under
test are counted: the flattened DUT model (``smoke/<VIP>/dut_*.sv``) for
UVM VIPs, ``rtl/*.sv`` for RTL IPs. Testbench code and the VIP packages are
left out.

Metrics (hit / total coverage points, a point is hit with count > 0):

  * line   -- statement blocks and both arms of every if/case (Verilator
              ``v_line`` and ``v_branch`` points)
  * toggle -- every bit of every signal seen rising and falling
  * expr   -- the term combinations of each multi-term condition
              (Verilator ``v_expr``, similar to FEC/condition coverage)
  * assert -- ``cover property`` / ``cover`` statements reached (``v_user``);
              only RTL IPs and a few models have them
  * func   -- covergroup bins hit (``v_covergroup``) in the VIP's own UVM
              code (interface, monitor and coverage collectors). Only for
              the VIPs whose UVM tests run on Verilator
              (tools/run_uvm_tests.py: APB / AHB / AXI / OCP / TileLink
              register tests and the <prefix>_func_test of the 29 generated
              agents); the other UVM environments need a commercial
              simulator (scripts/coverage.mk in each VIP)

A test that only builds on Icarus contributes nothing (Verilator cannot
compare against ``1'bz``, so tri-state checks stay on Icarus); a test that
fails only in the coverage build still contributes its points. Both are
named in the report detail.

Output: one line per VIP, ``coverage_report.csv``
(vip,tests,covered_tests,line_hit,line_total,line_pct,toggle_hit,
toggle_total,toggle_pct,expr_hit,expr_total,expr_pct,assert_hit,
assert_total,assert_pct,func_hit,func_total,func_pct,line_missed,
func_missed,detail) in the repo root (line_missed: source lines of the
never-reached line/branch points; func_missed: unhit bins per coverpoint),
and per VIP the merged
``build/cov/<VIP>/merged.dat`` and annotated sources
(``build/cov/<VIP>/annotated/``, lines prefixed ``%000000`` were never
executed). Env: VIPS_DIR, VERILATOR_COVERAGE (default verilator_coverage).
"""
import os, re, sys, csv, shutil, importlib.util
from multiprocessing import Pool, Lock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "build", "cov")
REPORT = os.path.join(ROOT, "coverage_report.csv")
VCOV = os.environ.get("VERILATOR_COVERAGE", "verilator_coverage")
METRICS = ("line", "toggle", "expr", "assert", "func")
# Verilator coverage page prefix -> metric
PAGE = {"v_line": "line", "v_branch": "line", "v_toggle": "toggle",
        "v_expr": "expr", "v_user": "assert", "v_covergroup": "func"}

AMBA_PROTOCOLS = ("apb", "ahb", "axi")

# with suffix_ok, any VIP source file counts (the UVM covergroups sit in
# included .svh files, not only the files on the command line)
VIP_SRC = os.sep + "vips" + os.sep

_rf = None
def rf():
    global _rf
    if _rf is None:
        spec = importlib.util.spec_from_file_location("run_func_tests",
                                                      os.path.join(ROOT, "tools", "run_func_tests.py"))
        _rf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_rf)
    return _rf

UVM_LOCK = Lock()   # inherited by the fork()ed Pool workers

_ru = None
def ru():
    global _ru
    if _ru is None:
        spec = importlib.util.spec_from_file_location("run_uvm_tests",
                                                      os.path.join(ROOT, "tools", "run_uvm_tests.py"))
        _ru = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ru)
        _ru.WORK = os.path.join(WORK, "uvm")
    return _ru

def cover_uvm(vip):
    """Run the VIP's Verilator UVM tests with covergroup coverage.
    Returns ({metric: [hit, total]} or None, detail)."""
    suite = ru().SUITES[vip]
    # one UVM build at a time: each takes several GB, and parallel ones
    # get the C++ compiler OOM-killed
    with UVM_LOCK:
        exe, err = ru().build(vip, suite, ["--coverage-user"])
    if exe is None:
        return None, "UVM build: " + err
    dats = []
    for t in suite["tests"]:
        dat = os.path.join(os.path.dirname(exe), t + ".dat")
        rc, out = ru().run([exe, "+UVM_TESTNAME=" + t, "+verilator+coverage+file+" + dat],
                           os.path.dirname(exe), 1800)
        st, _, detail = ru().classify(rc, out)
        if st != "PASS":
            return None, "UVM %s: %s" % (t, detail)
        dats.append(dat)
    vdir = os.path.join(rf().VIPS, vip)
    return summarize(dats, [os.path.join(vdir, f) for f in suite["files"]], suffix_ok=True,
                     scope=vip.split("-")[0].lower()), ""

def compile_sets(vip, tb, rtl):
    """(top, defines, [(label, files)]) as run_func_tests.run_test builds them."""
    top = os.path.splitext(os.path.basename(tb))[0]
    if rtl is not None:
        m = re.search(r'^\s*module\s+(\w+)', open(tb, errors="ignore").read(), re.M)
        return (m.group(1) if m else top), [], [("rtl", rtl + [tb])]
    return top, ["VIP_SMOKE_FLATTENED"], list(rf().build_sets(vip, tb))

def cover_test(vip, tb, rtl, wd):
    """Build and run one test with coverage. Returns (status, dat, detail)."""
    top, defines, sets = compile_sets(vip, tb, rtl)
    if not sets:
        return "ERROR", None, "no flattened DUT module instantiated by the test"
    if rf().pinned_sim(tb) == "iverilog":
        return "SKIP", None, "pinned to Icarus"
    log = []
    for label, files in sets:
        obj = os.path.join(wd, "obj_" + top)
        shutil.rmtree(obj, ignore_errors=True)
        rc, out = rf().run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                            "-Wno-ENUMVALUE", "--x-initial", "unique", "--x-assign", "unique",
                            "--coverage-line", "--coverage-toggle", "--coverage-expr", "--coverage-user",
                            "--coverage-max-width", "1024",
                            "-j", "2", "--Mdir", obj, "--top-module", top]
                           + ["+define+" + d for d in defines] + files, wd, 1800)
        if rc != 0:
            errs = [l for l in out.splitlines() if l.startswith("%Error")] or out.strip().splitlines() or [""]
            log.append("%s compile: %s" % (label, errs[0][:160]))
            continue
        dat = os.path.join(wd, top + ".dat")
        if os.path.exists(dat):
            os.remove(dat)
        rc, out = rf().run([os.path.join(obj, "V" + top), "+verilator+coverage+file+" + dat], wd, 600)
        open(os.path.join(wd, top + ".log"), "w").write(out)
        shutil.rmtree(obj, ignore_errors=True)
        st, _, detail = rf().classify(out, rtl is not None)
        if not os.path.exists(dat):
            return "FAIL", None, "no coverage.dat written"
        # a test that fails only in the coverage build (the instrumented
        # model schedules differently, e.g. a signal driven from two
        # processes) still exercised the code: keep its points, flag it
        return st, dat, "" if st == "PASS" else "fails under coverage: " + detail
    return "ERROR", None, "; ".join(log)[:300]

def parse_dat(path):
    """{key: count} of a Verilator coverage.dat; key is the raw point string."""
    pts = {}
    with open(path, errors="replace") as f:
        for l in f:
            m = re.match(r"C '(.*)' (\d+)\s*$", l)
            if m:
                pts[m.group(1)] = pts.get(m.group(1), 0) + int(m.group(2))
    return pts

def fields(key):
    return dict(kv.split("\x02", 1) for kv in key.split("\x01") if "\x02" in kv)

def canon(path):
    """Source file name with the runner's package-import copy suffix dropped
    (``dut_<m>_pkg.sv`` is ``dut_<m>.sv`` with imports injected)."""
    b = os.path.basename(path)
    return b[:-7] + ".sv" if b.endswith("_pkg.sv") and b.startswith("dut_") else b

def in_scope(scope, fn, page):
    """A covergroup belongs to the VIP under test when it names its protocol,
    or no protocol at all (shared interface groups). The AMBA VIPs compile
    the APB, AHB and AXI checkers together; a register test on one bus can
    never hit the others' bins."""
    if not scope:
        return True
    name = (fn + " " + page).lower()
    return scope in name or not any(p in name for p in AMBA_PROTOCOLS)

def summarize(dats, dut_files, suffix_ok=False, scope=None):
    """{metric: [hit, total]} over the points whose source is a DUT file.

    Points are merged per design unit, not per instance: the key leaves out
    the hierarchy, which differs between tests (each test has its own top
    module and instance names), so a point counts as hit when any test, in
    any instance, reached it."""
    names = set(canon(f) for f in dut_files)
    hits = {}
    for dat in dats:
        for key, cnt in parse_dat(dat).items():
            f = fields(key)
            fn = canon(f.get("f", ""))
            metric = PAGE.get(f.get("page", "").split("/")[0])
            if metric is None or (fn not in names and not (
                    suffix_ok and VIP_SRC in f.get("f", "") and "/uvm-core/" not in f.get("f", ""))):
                continue
            if metric in ("func", "assert") and not in_scope(scope, fn, f.get("page", "")):
                continue
            # covergroup points are told apart by bin and coverpoint path
            # ("h" is cg.<coverpoint>.<bin> there, not the instance)
            k = (metric, fn, f.get("page"), f.get("l"), f.get("n"), f.get("o"), f.get("bin"),
                 f.get("h") if metric == "func" else None)
            hits[k] = hits.get(k, 0) + cnt
    res = {m: [0, 0] for m in METRICS}
    missed_lines, missed_bins = {}, {}
    for k, cnt in hits.items():
        res[k[0]][1] += 1
        res[k[0]][0] += cnt > 0
        if cnt:
            continue
        if k[0] == "line" and k[3]:
            missed_lines.setdefault(k[1], set()).add(int(k[3]))
        elif k[0] == "func":
            cp = (k[2].split("/")[-1].replace("__vlAnonCG_", "") + "." + (k[7] or "").split(".")[1]
                  if (k[7] or "").count(".") >= 2 else k[2])
            missed_bins[cp] = missed_bins.get(cp, 0) + 1
    res["line_missed"] = "; ".join("%s:%s" % (fn, ranges(sorted(ls)))
                                   for fn, ls in sorted(missed_lines.items()))
    res["func_missed"] = "; ".join("%s(%d)" % kv for kv in sorted(missed_bins.items()))
    return res

def ranges(nums):
    """[3, 4, 5, 9] -> '3-5,9'"""
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] <= nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else "%d-%d" % (nums[i], nums[j]))
        i = j + 1
    return ",".join(out)

def dut_files_of(vip, tests):
    if tests and tests[0][1] is not None:
        return tests[0][1]
    return sorted(set(rf().flat_modules(vip).values()))

def cover_vip(vip):
    tests = rf().tests_of(vip)
    wd = os.path.join(WORK, vip)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd)
    if not tests:
        return vip, 0, 0, None, "no functional test"
    dats, notes = [], []
    for tb, rtl in tests:
        st, dat, detail = cover_test(vip, tb, rtl, wd)
        if dat:
            dats.append(dat)
        if st != "PASS":
            notes.append("%s: %s %s" % (os.path.basename(tb), st, detail))
    if not dats:
        return vip, len(tests), 0, None, " | ".join(notes)[:400]
    merged = os.path.join(wd, "merged.dat")
    rc, out = rf().run([VCOV, "--write", merged] + dats, wd, 600)
    if rc != 0:
        return vip, len(tests), len(dats), None, "verilator_coverage merge: " + out.strip()[-200:]
    rf().run([VCOV, "--annotate", os.path.join(wd, "annotated"), "--annotate-min", "1", merged], wd, 600)
    res = summarize(dats, dut_files_of(vip, tests))
    if vip in ru().SUITES:
        fres, fdetail = cover_uvm(vip)
        if fres:
            res["func"], res["func_missed"] = fres["func"], fres["func_missed"]
            # SVA cover statements of the VIP's checkers, reached in the UVM run
            res["assert"] = [a + b for a, b in zip(res["assert"], fres["assert"])]
        else:
            notes.append(fdetail)
    return vip, len(tests), len(dats), res, " | ".join(notes).replace(ROOT + os.sep, "")[:400]

def pct(h, t):
    return round(100.0 * h / t, 1) if t else ""

def row(r):
    vip, n, ok, res, detail = r
    out = [vip, n, ok]
    for m in METRICS:
        h, t = res[m] if res else (0, 0)
        out += [h, t, pct(h, t)]
    return out + [(res or {}).get("line_missed", ""), (res or {}).get("func_missed", ""), detail]

def main(argv):
    jobs = 2
    if argv[:1] == ["-j"]:
        jobs, argv = int(argv[1]), argv[2:]
    vips = argv or sorted(d for d in os.listdir(rf().VIPS) if os.path.isdir(os.path.join(rf().VIPS, d)))
    rows = []
    with Pool(jobs) as p:
        for r in p.imap(cover_vip, vips):
            rw = row(r)
            rows.append(rw)
            print("COV %s tests=%d/%d %s%s" % (rw[0], rw[2], rw[1], " ".join(
                "%s=%s%%" % (m, rw[5 + 3 * i]) for i, m in enumerate(METRICS) if rw[4 + 3 * i]),
                (" -- " + rw[-1]) if rw[-1] else ""))
            sys.stdout.flush()
    if not argv:
        with open(REPORT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["vip", "tests", "covered_tests"]
                       + ["%s_%s" % (m, k) for m in METRICS for k in ("hit", "total", "pct")]
                       + ["line_missed", "func_missed", "detail"])
            w.writerows(rows)
    return 0 if all(r[2] for r in rows) else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
