#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""run_func_tests.py [VIP ...] -- run every self-checking functional test.

Functional tests are the executable part of each VIP's test suite (the UVM
tests need a commercial simulator; these run on open-source tools):

  * UVM VIPs: ``tb/smoke_func_tb.sv`` and ``tb/func_*_tb.sv``. Each is a
    stand-alone module guarded by ``VIP_SMOKE_FLATTENED`` that drives the
    flattened DUT model produced by ``smoke/flatten.py``
    (``smoke/<VIP>/dut_<mod>.sv``) and prints ``FUNC_PASS``/``FUNC_FAIL``.
  * RTL IPs: ``tb/<IP>_tb.sv`` against ``rtl/*.sv`` (prints ``TEST PASSED``).

Compile order tried per test: Icarus without packages, Icarus with the VIP's
sanitised packages imported into the DUT, then Verilator (``--binary
--timing``) for DUT code Icarus cannot parse. A test may pin its flow with a
header line ``// FUNC_SIM: verilator`` or ``// FUNC_SIM: iverilog``.

Output: one line per test ``FUNC_PASS|FUNC_FAIL|FUNC_ERROR <VIP>/<test> -- detail``
and ``func_report.csv`` (vip,test,result,sim,checks,detail) in the repo root.
Exit status is non-zero when any test fails or cannot be built.
"""
import os, re, sys, csv, json, glob, shutil, subprocess, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMOKE = os.path.join(ROOT, "smoke")
VIPS = os.environ.get("VIPS_DIR", os.path.join(ROOT, "build", "vips"))
WORK = os.path.join(ROOT, "build", "func")
REPORT = os.path.join(ROOT, "func_report.csv")

_sr = None
def smoke_run():
    """smoke/smoke_run.py as a module (package sanitiser, import injection)."""
    global _sr
    if _sr is None:
        spec = importlib.util.spec_from_file_location("smoke_run", os.path.join(SMOKE, "smoke_run.py"))
        _sr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_sr)
    return _sr

def run(cmd, cwd, timeout=300):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "") if isinstance(e.stdout, str) else "timeout"

def classify(out, rtl):
    m = re.search(r'FUNC_PASS\b[^\n]*?checks=(\d+)', out)
    if m and "FUNC_FAIL" not in out:
        return "PASS", int(m.group(1)), ""
    if rtl and re.search(r'TEST PASSED', out) and not re.search(r'TEST FAILED|SVA_FAIL', out):
        n = len(re.findall(r'^\s*(PASS|\[PASS\]|ok)\b', out, re.M))
        return "PASS", n, ""
    fails = [l.strip() for l in out.splitlines() if re.search(r'FAIL|ERROR', l)]
    return "FAIL", 0, " | ".join(fails[:4])[:300] or "no PASS marker"

def flat_modules(vip):
    man = os.path.join(SMOKE, vip, "manifest.json")
    if not os.path.exists(man):
        subprocess.run([sys.executable, os.path.join(SMOKE, "flatten.py"), vip],
                       capture_output=True, text=True, timeout=600)
    if not os.path.exists(man):
        return {}
    return {e["module"]: e["file"] for e in json.load(open(man)) if e.get("status") == "FLAT"}

def pinned_sim(tb):
    m = re.search(r'^//\s*FUNC_SIM:\s*(\w+)', open(tb, errors="ignore").read(), re.M)
    return m.group(1) if m else None

_pkg_cache = {}
def vip_pkgs(vip):
    if vip not in _pkg_cache:
        try:
            _pkg_cache[vip] = smoke_run().compilable_pkgs(os.path.join(VIPS, vip), vip)
        except Exception:
            _pkg_cache[vip] = []
    return _pkg_cache[vip]

def build_sets(vip, tb):
    """Yield (label, files) compile candidates for a UVM functional tb."""
    txt = open(tb, errors="ignore").read()
    flats = flat_modules(vip)
    used = [m for m in flats if re.search(r'^\s*%s\b' % re.escape(m), txt, re.M)]
    if not used:
        return
    duts = [flats[m] for m in used]
    yield "plain", duts + [tb]
    pkgs = vip_pkgs(vip)
    if pkgs:
        out = []
        for m in used:
            p = os.path.join(WORK, vip, "dut_%s_pkg.sv" % m)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            smoke_run().inject_imports(flats[m], [n for n, _ in pkgs], p)
            out.append(p)
        yield "pkgs", [f for _, f in pkgs] + out + [tb]

def sim_iverilog(files, top, wd, defines):
    exe = os.path.join(wd, top + ".vvp")
    rc, out = run(["iverilog", "-g2012"] + ["-D" + d for d in defines]
                  + ["-s", top, "-o", exe] + files, wd, 180)
    if rc != 0:
        return None, out
    rc, out = run(["vvp", "-n", exe], wd, 300)
    return out, ""

def sim_verilator(files, top, wd, defines):
    obj = os.path.join(wd, "obj_" + top)
    shutil.rmtree(obj, ignore_errors=True)
    rc, out = run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                   "--x-initial", "unique", "--x-assign", "unique",
                   "-j", "4", "--Mdir", obj, "--top-module", top]
                  + ["+define+" + d for d in defines] + files, wd, 900)
    if rc != 0:
        return None, out
    rc, out = run([os.path.join(obj, "V" + top)], wd, 300)
    return out, ""

def run_test(vip, tb, rtl_files=None):
    top = os.path.splitext(os.path.basename(tb))[0]
    wd = os.path.join(WORK, vip)
    os.makedirs(wd, exist_ok=True)
    if rtl_files is not None:
        sets, defines = [("rtl", rtl_files + [tb])], []
        m = re.search(r'^\s*module\s+(\w+)', open(tb, errors="ignore").read(), re.M)
        top = m.group(1) if m else top
    else:
        sets, defines = list(build_sets(vip, tb)), ["VIP_SMOKE_FLATTENED"]
        if not sets:
            return "ERROR", "-", 0, "no flattened DUT module instantiated by the test"
    pin = pinned_sim(tb)
    sims = [("iverilog", sim_iverilog), ("verilator", sim_verilator)]
    if pin:
        sims = [s for s in sims if s[0] == pin]
    log = []
    for sname, fn in sims:
        for label, files in sets:
            out, err = fn(files, top, wd, defines)
            if out is None:
                log.append("%s/%s compile: %s" % (sname, label, err.strip().splitlines()[-1:] if err.strip() else ""))
                continue
            open(os.path.join(wd, top + ".log"), "w").write(out)
            st, n, detail = classify(out, rtl_files is not None)
            return st, sname, n, detail
    return "ERROR", "-", 0, ("; ".join(str(x) for x in log))[:300]

def rtl_ip(vdir):
    return os.path.isdir(os.path.join(vdir, "rtl")) and glob.glob(os.path.join(vdir, "rtl", "*_top.sv"))

def tests_of(vip):
    vdir = os.path.join(VIPS, vip)
    if rtl_ip(vdir):
        rtl = sorted(glob.glob(os.path.join(vdir, "rtl", "*.sv")))
        return [(tb, rtl) for tb in sorted(glob.glob(os.path.join(vdir, "tb", "*_tb.sv")))]
    # tb/ sits at the VIP root, or one level down (<vip>/<proto>_vip/tb/)
    tbdirs = glob.glob(os.path.join(vdir, "tb")) + glob.glob(os.path.join(vdir, "*", "tb"))
    tbs = []
    for d in tbdirs:
        tbs += glob.glob(os.path.join(d, "smoke_func_tb.sv")) + sorted(glob.glob(os.path.join(d, "func_*_tb.sv")))
    return [(tb, None) for tb in tbs]

def main(argv):
    names = argv or sorted(d for d in os.listdir(VIPS) if os.path.isdir(os.path.join(VIPS, d)))
    rows, bad = [], 0
    for vip in names:
        tests = tests_of(vip)
        if not tests:
            rows.append((vip, "-", "NONE", "-", 0, "no functional test"))
            print("FUNC_NONE %s" % vip)
            continue
        for tb, rtl in tests:
            st, sim, n, detail = run_test(vip, tb, rtl)
            name = os.path.basename(tb)
            rows.append((vip, name, st, sim, n, detail))
            bad += st != "PASS"
            print("FUNC_%s %s/%s [%s checks=%d]%s" % (st, vip, name, sim, n, (" -- " + detail) if detail else ""))
            sys.stdout.flush()
    if not argv:
        with open(REPORT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["vip", "test", "result", "sim", "checks", "detail"])
            w.writerows(rows)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
