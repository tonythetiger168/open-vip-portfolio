#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""ci_aggregate.py <reports-dir> -- fail unless every shard report covers
the whole catalog with the same pass rules as the single-job workflow.

Elab: every zip stem has PASS and none have FAIL (the ELAB_ERRORS=0 rule
is applied in the elab job; this checks none were dropped).
Smoke: no SMOKE_FAIL, and every zip has a PASS or SKIP row.
SVA: no SVA_LINT_FAIL and no non-zero SVA_TAUTOLOGIES, every zip present.
Functional: no FUNC_FAIL or FUNC_ERROR. FUNC_NONE stays non-failing, matching
tools/run_func_tests.py. Every zip is mentioned.
UVM: every suite test in tools/run_uvm_tests.py is UVM_PASS.
Coverage: every zip has covered_tests > 0, matching tools/coverage.py.
"""
import csv, glob, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ci_shard
import run_uvm_tests


def read(path):
    with open(path, errors="replace") as f:
        return f.read()


def one(paths, label):
    if len(paths) != 1:
        raise SystemExit("%s: expected 1 file, found %s" % (label, paths))
    return paths[0]


def main(argv):
    if len(argv) != 1:
        raise SystemExit("usage: ci_aggregate.py <reports-dir>")
    base = argv[0]
    errors = []

    def bad(msg):
        errors.append(msg)

    zips = ci_shard.vip_names()
    if not zips:
        bad("no vips/*.zip in the checkout")

    elab = one(glob.glob(os.path.join(base, "l1-fast", "elab", "elab_summary.txt")), "elab summary")
    passed, failed = set(), set()
    for line in read(elab).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "PASS":
            passed.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "FAIL":
            failed.add(parts[1])
    if failed:
        bad("elab FAIL: %s" % sorted(failed))
    if passed != set(zips):
        bad("elab PASS set != zip set (missing %s, extra %s)" % (
            sorted(set(zips) - passed), sorted(passed - set(zips))))

    smoke_log = read(one(glob.glob(os.path.join(base, "l1-fast", "smoke", "smoke.log")), "smoke log"))
    if "SMOKE_FAIL" in smoke_log:
        bad("smoke log contains SMOKE_FAIL")
    smoke_csv = one(glob.glob(os.path.join(base, "l1-fast", "smoke", "smoke_report.csv")), "smoke csv")
    with open(smoke_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    smoke_names = [r["vip"] for r in rows]
    if sorted(smoke_names) != sorted(zips) or len(smoke_names) != len(set(smoke_names)):
        bad("smoke_report.csv rows do not match the zip set")
    bad_smoke = [r["vip"] for r in rows if r["result"] not in ("PASS", "SKIP")]
    if bad_smoke:
        bad("smoke results other than PASS/SKIP: %s" % bad_smoke)

    sva = read(one(glob.glob(os.path.join(base, "l1-fast", "sva", "sva_lint.log")), "sva log"))
    sva_seen = set()
    for line in sva.splitlines():
        if line.startswith(" ") or not line.strip():
            continue
        if "SVA_LINT_FAIL" in line:
            bad("sva lint fail: %s" % line[:200])
            continue
        if "SVA_TAUTOLOGIES=" in line:
            name, _, count = line.partition(" SVA_TAUTOLOGIES=")
            sva_seen.add(name)
            if count.split()[0] != "0":
                bad("sva tautology: %s" % line[:200])
    if sva_seen != set(zips):
        bad("sva log names != zip set (missing %s)" % sorted(set(zips) - sva_seen)[:20])

    func = read(one(glob.glob(os.path.join(base, "l1-fast", "func", "func.log")), "func log"))
    func_seen = set()
    for line in func.splitlines():
        if line.startswith("FUNC_FAIL") or line.startswith("FUNC_ERROR"):
            bad(line[:300])
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("FUNC_"):
            func_seen.add(parts[1].split("/")[0])
    if func_seen != set(zips):
        bad("func log names != zip set (missing %s)" % sorted(set(zips) - func_seen)[:20])

    uvm_lines = []
    for path in glob.glob(os.path.join(base, "l1-uvm-*", "uvm", "uvm.log")):
        uvm_lines.extend(read(path).splitlines())
    got = defaultdict(dict)
    for line in uvm_lines:
        parts = line.split()
        if len(parts) < 2 or not parts[0].startswith("UVM_"):
            continue
        status = parts[0][4:]
        vip, _, test = parts[1].partition("/")
        got[vip][test] = status
        if status != "PASS":
            bad(line[:300])
    for vip, suite in sorted(run_uvm_tests.SUITES.items()):
        have = got.get(vip, {})
        for test in suite["tests"]:
            if have.get(test) != "PASS":
                bad("uvm %s/%s status=%s" % (vip, test, have.get(test)))

    cov_rows = []
    seen = []
    for path in sorted(glob.glob(os.path.join(base, "l1-cov-*", "cov", "coverage_report.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                cov_rows.append(row)
                seen.append(row["vip"])
    if len(seen) != len(set(seen)):
        bad("duplicate coverage rows")
    if set(seen) != set(zips):
        bad("coverage rows != zip set (missing %s, extra %s)" % (
            sorted(set(zips) - set(seen)), sorted(set(seen) - set(zips))))
    for row in cov_rows:
        try:
            covered = int(row["covered_tests"])
        except (KeyError, ValueError):
            covered = 0
        if covered <= 0:
            bad("coverage covered_tests=0 for %s" % row.get("vip"))

    if errors:
        print("AGGREGATE_FAIL %d" % len(errors))
        for msg in errors:
            print(msg)
        return 1

    merged = os.path.join(ROOT, "coverage_report.csv")
    with open(merged, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cov_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sorted(cov_rows, key=lambda r: r["vip"].lower()))
    print("AGGREGATE_PASS vips=%d uvm_suites=%d" % (len(zips), len(run_uvm_tests.SUITES)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
