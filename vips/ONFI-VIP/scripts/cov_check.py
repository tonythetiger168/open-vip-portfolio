#!/usr/bin/env python3
#=============================================================================#
# cov_check.py — 100% coverage closure gate
#
# Parses the merged coverage report (VCS URG / Xcelium IMC / Questa UCDB text)
# and verifies that every metric — line, fsm, toggle, assert(SVA) — reaches
# the required goal (default 100%). Exits 1 if any metric is below goal.
#
# Parsing strategy (conservative — a 100% gate must never false-PASS):
#   1. Table-aware: a line whose tokens contain >=2 metric names is treated as
#      a column header (e.g. URG "SCORE LINE COND TOGGLE FSM ASSERT GROUP");
#      following data rows are mapped to metrics by column position.
#   2. Single-metric lines ("Toggle coverage: 98.5%") are parsed directly.
#   3. The score used per metric is the MINIMUM of all values found — the
#      gate fails if any module/group row is below goal.
#
# Usage:
#   cov_check.py --simulator vcs --report coverage/ --goal 100
#   cov_check.py --simulator questa --report coverage/questa_cov.txt \
#                --metric line=100 fsm=100 toggle=100 assert=100
#=============================================================================#
import argparse
import glob
import os
import re
import sys

METRIC_PATTERNS = {
    "line":   [r"lines?", r"stmts?", r"statements?"],
    "fsm":    [r"fsm", r"states?", r"transitions?"],
    "toggle": [r"toggle", r"tgl"],
    "assert": [r"assertions?", r"assert", r"sva"],
}

PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%?")
SEP_RE = re.compile(r"^[\s\-=+|]+$")


def find_report_files(path, simulator):
    if os.path.isfile(path):
        return [path]
    pats = {
        "vcs":     ["**/summary.txt", "**/dashboard.txt", "**/*.txt"],
        "xcelium": ["**/imc_cov.txt", "**/*.txt", "**/*.rpt"],
        "questa":  ["**/questa_cov.txt", "**/*.txt"],
    }.get(simulator, ["**/*.txt"])
    files = []
    for p in pats:
        files.extend(glob.glob(os.path.join(path, p), recursive=True))
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def match_metric_token(tok):
    t = tok.strip().strip(":").lower()
    for metric, pats in METRIC_PATTERNS.items():
        if any(re.fullmatch(p, t) for p in pats):
            return metric
    return None


def extract_metric_scores(files):
    hits = {m: [] for m in METRIC_PATTERNS}
    for f in files:
        try:
            with open(f, errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        header_cols = None  # {metric: column_index} for table parsing
        for line in lines:
            if not line.strip() or SEP_RE.match(line):
                continue
            toks = line.split()
            col_of = {}
            for i, tok in enumerate(toks):
                m = match_metric_token(tok)
                if m and m not in col_of:
                    col_of[m] = i
            if len(col_of) >= 2:
                header_cols = col_of      # table header row
                continue
            if len(col_of) == 1:
                # single-metric line, e.g. "Toggle coverage: 98.5%"
                metric = next(iter(col_of))
                for m in PCT_RE.finditer(line):
                    hits[metric].append(float(m.group(1)))
                continue
            if header_cols:
                # data row: percentage tokens mapped to metric columns
                pct_at = []
                for i, tok in enumerate(toks):
                    m = PCT_RE.fullmatch(tok)
                    if m:
                        pct_at.append((i, float(m.group(1))))
                if pct_at:
                    for metric, col in header_cols.items():
                        # first percentage token at/after the metric's column,
                        # else the closest preceding one (name offset shift)
                        after = [v for i, v in pct_at if i >= col]
                        if after:
                            hits[metric].append(after[0])
                    continue
        # header scope resets per file
    return {m: min(v) for m, v in hits.items() if v}


def main():
    ap = argparse.ArgumentParser(description="100% coverage closure gate")
    ap.add_argument("--simulator", default="vcs",
                    choices=["vcs", "xcelium", "questa"])
    ap.add_argument("--report", required=True,
                    help="merged report file or coverage directory")
    ap.add_argument("--goal", type=float, default=100.0)
    ap.add_argument("--metric", nargs="*", default=[],
                    help="per-metric goals, e.g. line=100 fsm=100 toggle=100 assert=100")
    args = ap.parse_args()

    goals = {m: args.goal for m in METRIC_PATTERNS}
    for kv in args.metric:
        k, _, v = kv.partition("=")
        if k in goals and v:
            goals[k] = float(v)

    files = find_report_files(args.report, args.simulator)
    if not files:
        print(f"[COV-CHECK] ERROR: no report files found under {args.report}")
        sys.exit(2)

    scores = extract_metric_scores(files)

    print("=" * 62)
    print(" Coverage Closure Check (goal per metric)")
    print("-" * 62)
    failed = False
    for metric in ("line", "fsm", "toggle", "assert"):
        goal = goals[metric]
        if metric not in scores:
            print(f"  {metric:8s}: NOT FOUND in report  -> FAIL (goal {goal:.0f}%)")
            failed = True
            continue
        val = scores[metric]
        ok = val >= goal
        failed |= not ok
        print(f"  {metric:8s}: {val:6.2f}%  (goal {goal:.0f}%)  "
              f"{'PASS' if ok else 'FAIL'}")
    print("=" * 62)

    if failed:
        print("[COV-CHECK] FAIL: coverage goal not met - regression blocked.")
        sys.exit(1)
    print("[COV-CHECK] PASS: 100% closure on line/fsm/toggle/assert.")
    sys.exit(0)


if __name__ == "__main__":
    main()
