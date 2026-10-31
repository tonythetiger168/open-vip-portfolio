#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""sb_mutation.py [-k N] [VIP ...] -- check that the template-built UVM agents'
scoreboards catch faults in the DUT model.

The 29 template-built agents (tools/uvm_agents/, rendered by
tools/gen_uvm_agents.py) predict the DUT response with a reference model that
was written from the same tb/top_tb.sv model the agent drives. A scoreboard
that only mirrors what it observes would pass whatever the DUT does. This
script mutates the DUT model module(s) in tb/top_tb.sv with the operators of
tools/mutation_score.py, rebuilds the UVM testbench with Verilator and runs
the VIP's <p>_func_test (tools/run_uvm_tests.py): a mutant is *killed* when
the test fails (scoreboard mismatch, protocol checker, timeout), *survives*
when it still prints SB_PASS, and is *invalid* when it does not build.

Up to N mutants per VIP (default 4) are spread over the model. Each one is a
full Verilator UVM build (~1-2 min), so a full run takes a few hours.
Survivors reviewed as equivalent are listed in tools/sb_mutation_equivalent.csv
(vip,location,mutation,reason; location is top_tb.sv:<line>) and left out of
the score. Output: one line per VIP and ``sb_mutation_report.csv``
(vip,mutants,valid,killed,survived,equivalent,score,survivors) in the repo root.
"""
import os, re, sys, csv, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mutation_score as ms      # noqa: E402
import run_uvm_tests as ru       # noqa: E402

ROOT = ms.ROOT
WORK = os.path.join(ROOT, "build", "sbmut")
REPORT = os.path.join(ROOT, "sb_mutation_report.csv")
EQUIV = os.path.join(ROOT, "tools", "sb_mutation_equivalent.csv")


def equivalents():
    if not os.path.exists(EQUIV):
        return {}
    with open(EQUIV) as f:
        return {(r["vip"], r["location"], r["mutation"]): r["reason"]
                for r in csv.DictReader(l for l in f if not l.startswith("#"))}


def model_candidates(src):
    """Mutation candidates in every module of top_tb.sv except top_tb itself."""
    lines = src.split("\n")
    out, keep = [], False
    for n, line in enumerate(lines):
        m = re.match(r"\s*module\s+(\w+)", line)
        if m:
            keep = m.group(1) != "top_tb"
        if re.match(r"\s*endmodule\b", line):
            keep = False
            continue
        if keep:
            # candidates() starts at a module header; feed it the header + line
            for c in ms.candidates("module x;\n" + line):
                out.append((n,) + c[1:])
    return out


def run_mutant(vip, suite, vdir_src, mdir, mutated_tb):
    """'killed' / 'survived' / 'invalid' for one mutated copy of the VIP."""
    shutil.copytree(vdir_src, os.path.join(mdir, vip))
    with open(os.path.join(mdir, vip, "tb", "top_tb.sv"), "w") as f:
        f.write(mutated_tb)
    ru.VIPS, ru.WORK = mdir, os.path.join(mdir, "uvm")
    try:
        exe, err = ru.build(vip, suite)
        if exe is None:
            return "invalid", err
        rc, out = ru.run([exe, "+UVM_TESTNAME=" + suite["tests"][0]], os.path.dirname(exe), 600)
        st, _, detail = ru.classify(rc, out)
        return ("survived" if st == "PASS" else "killed"), detail
    finally:
        shutil.rmtree(os.path.join(mdir, "uvm"), ignore_errors=True)
        shutil.rmtree(os.path.join(mdir, vip), ignore_errors=True)


def mutate_vip(vip, k):
    vips0, work0 = ru.VIPS, ru.WORK
    suite = ru.SUITES[vip]
    vdir = os.path.join(vips0, vip)
    tb = os.path.join(vdir, "tb", "top_tb.sv")
    src = open(tb).read()
    chosen = ms.pick(model_candidates(src), k)
    wd = os.path.join(WORK, vip)
    shutil.rmtree(wd, ignore_errors=True)
    eq = equivalents()
    valid = killed = survived = equiv = 0
    surv = []
    try:
        for i, c in enumerate(chosen):
            mdir = os.path.join(wd, "m%02d" % i)
            os.makedirs(mdir)
            verdict, _ = run_mutant(vip, suite, vdir, mdir, ms.apply(src, c))
            if verdict == "invalid":
                continue
            loc = "top_tb.sv:%d" % (c[0] + 1)
            if verdict == "survived" and (vip, loc, c[4]) in eq:
                equiv += 1
                continue
            valid += 1
            if verdict == "killed":
                killed += 1
            else:
                survived += 1
                surv.append("%s %s [%s]" % (loc, c[4], src.split("\n")[c[0]].strip()[:60]))
    finally:
        ru.VIPS, ru.WORK = vips0, work0
    return vip, len(chosen), valid, killed, survived, equiv, surv


def main(argv):
    k = 4
    if "-k" in argv:
        i = argv.index("-k")
        k = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    agents = sorted(ru.agent_suites())
    names = argv or agents
    rows = []
    for vip in names:
        if vip not in agents:
            print("SBMUT_NONE %s (not a template-built agent)" % vip)
            continue
        vip, n, valid, killed, survived, equiv, surv = mutate_vip(vip, k)
        score = "%d%%" % round(100.0 * killed / valid) if valid else "n/a"
        print("SBMUT %s mutants=%d valid=%d killed=%d survived=%d equivalent=%d score=%s"
              % (vip, n, valid, killed, survived, equiv, score))
        for s in surv:
            print("    survived: " + s)
        sys.stdout.flush()
        rows.append((vip, n, valid, killed, survived, equiv, score, "; ".join(surv)))
        if not argv:            # written after every VIP: a full run takes hours
            with open(REPORT, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["vip", "mutants", "valid", "killed", "survived", "equivalent", "score", "survivors"])
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
