#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""sva_lint.py [<vip_dir> ...] -- find assertion expressions that can never fail.

A check such as ``bresp inside {0,1,2,3}`` on a 2-bit signal, or
``awid <= 8'hFF`` on an 8-bit one, holds for every 2-state value of its
operand, so the assertion only fails on X/Z and reports 100% while checking
nothing. This script elaborates each VIP with pyslang (same file set as
tools/elab_scan.py) and reports, inside assert / assume / property / sequence
code:

  inside      ``x inside {...}`` whose constant items cover every value of x
  compare     ``x <= C`` / ``x < C`` / ``x >= C`` / ``x > C`` (either order)
              that holds for every value of the unsigned operand x
  lowest-bit  ``$countones(x & (~x + 1)) == 1``: true for any non-zero x

Prints ``SVA_TAUTOLOGIES=<n>`` per VIP followed by one line per finding
(``file:line kind text``). Exits 1 when any finding is reported, so CI can
gate on it. With no argument, scans every VIP under $VIPS_DIR (build/vips).

--fix rewrites each inside / compare finding in place as
``!$isunknown(<operand>)``: that is all the original expression could ever
catch, so the rewrite keeps the check and stops it from posing as a protocol
rule. A finding that deserves a real rule should be rewritten by hand first;
lowest-bit findings are never rewritten automatically.
"""
import os, re, sys
from pyslang import driver, ast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elab_scan  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIPS = os.environ.get("VIPS_DIR", os.path.join(ROOT, "build", "vips"))
MAX_ENUM_WIDTH = 16
ASSERT_SYNTAX = ("ConcurrentAssertion", "ImmediateAssert", "ImmediateAssume", "PropertyDeclaration",
                 "SequenceDeclaration", "DeferredAssert", "AssertPropertyStatement",
                 "AssumePropertyStatement")
LOWEST_BIT = re.compile(r"\$countones\s*\(\s*([\w.\[\]:]+)\s*&\s*\(\s*~\s*\1\s*\+\s*1\s*\)\s*\)\s*==\s*1")


def in_assertion(syn):
    while syn is not None:
        if any(k in str(syn.kind) for k in ASSERT_SYNTAX):
            return True
        syn = syn.parent
    return False


def strip(e):
    while e.kind == ast.ExpressionKind.Conversion:
        e = e.operand
    return e


def const_int(e):
    cv = e.constant
    if cv is None:
        return None
    try:
        return int(str(cv.value).split("'")[-1].lstrip("sbodhSBODH"), {"b": 2, "o": 8, "d": 10, "h": 16}.get(
            (re.search(r"'s?([bodh])", str(cv.value), re.I) or [None, "d"])[1].lower(), 10)) \
            if "'" in str(cv.value) else int(str(cv.value))
    except (ValueError, TypeError):
        return None


def width(e):
    t = e.type
    if not t.isIntegral or t.isSigned:
        return None
    return t.bitWidth


def inside_tautology(e):
    w = width(strip(e.left))
    if w is None or w > MAX_ENUM_WIDTH:
        return False
    seen = set()
    for r in e.rangeList:
        if r.kind == ast.ExpressionKind.ValueRange:
            lo, hi = const_int(r.left), const_int(r.right)
            if lo is None or hi is None:
                return False
            seen.update(range(max(lo, 0), min(hi, (1 << w) - 1) + 1))
        else:
            v = const_int(r)
            if v is None:
                return False
            seen.add(v)
    return all(v in seen for v in range(1 << w))


CMP = {
    ast.BinaryOperator.LessThanEqual: lambda c, m: c >= m,
    ast.BinaryOperator.LessThan: lambda c, m: c > m,
    ast.BinaryOperator.GreaterThanEqual: lambda c, m: c <= 0,
}
FLIP = {ast.BinaryOperator.GreaterThanEqual: ast.BinaryOperator.LessThanEqual,
        ast.BinaryOperator.GreaterThan: ast.BinaryOperator.LessThan,
        ast.BinaryOperator.LessThanEqual: ast.BinaryOperator.GreaterThanEqual}


def compare_operand(e):
    left, right = strip(e.left), strip(e.right)
    return right if const_int(left) is not None else left


def compare_tautology(e):
    op = e.op
    if op not in (ast.BinaryOperator.LessThanEqual, ast.BinaryOperator.LessThan,
                  ast.BinaryOperator.GreaterThanEqual, ast.BinaryOperator.GreaterThan):
        return False
    left, right = strip(e.left), strip(e.right)
    c = const_int(right)
    var = left
    if c is None:
        c, var = const_int(left), right
        if c is None:
            return False
        op = FLIP.get(op)                     # C <= x  ->  x >= C
        if op is None:
            return False
    if const_int(var) is not None:
        return False
    w = width(var)
    if w is None:
        return False
    rule = CMP.get(op)
    return bool(rule and rule(c, (1 << w) - 1))


def scan(vdir, edits=None):
    files, allsv = elab_scan.ordered(vdir)
    uvm = elab_scan.UVM
    incdirs = sorted({os.path.dirname(f) for f in allsv} | {uvm, uvm + "/macros"})
    d = driver.Driver()
    d.addStandardArgs()
    if not d.parseCommandLine("--lint-only --single-unit --timescale=1ns/1ps " +
                              " ".join("-I" + x for x in incdirs) + " " + " ".join(files)):
        return None
    d.processOptions()
    d.parseAllSources()
    comp = d.createCompilation()
    comp.getAllDiagnostics()
    sm = d.sourceManager
    found = {}

    def report(obj, kind, operand=None):
        loc = obj.sourceRange.start
        f = os.path.abspath(sm.getFileName(loc))
        if not f.startswith(os.path.abspath(vdir) + os.sep):
            return
        found[(os.path.relpath(f, vdir), sm.getLineNumber(loc), kind)] = None
        if edits is not None and operand is not None:
            end, op = obj.sourceRange.end, operand.sourceRange
            if sm.getFileName(end) == sm.getFileName(loc) == sm.getFileName(op.start):
                edits.setdefault(f, set()).add((loc.offset, end.offset, op.start.offset, op.end.offset))

    def cb(obj):
        try:
            if isinstance(obj, ast.InsideExpression) and obj.syntax is not None and in_assertion(obj.syntax):
                if inside_tautology(obj):
                    report(obj, "inside", strip(obj.left))
            elif isinstance(obj, ast.BinaryExpression) and obj.syntax is not None and in_assertion(obj.syntax):
                if compare_tautology(obj):
                    report(obj, "compare", compare_operand(obj))
        except (AttributeError, RuntimeError):
            pass
        return ast.VisitAction.Advance

    comp.getRoot().visit(cb)
    for f in allsv:
        if os.path.abspath(f).startswith(os.path.abspath(elab_scan.UVM)):
            continue
        for i, l in enumerate(open(f, errors="replace"), 1):
            if LOWEST_BIT.search(l):
                found[(os.path.relpath(f, vdir), i, "lowest-bit")] = None
    return sorted(found)


def apply_edits(edits):
    for f, spans in edits.items():
        src = open(f, "rb").read()
        for s0, e0, o0, o1 in sorted(spans, reverse=True):
            new = b"!$isunknown(" + src[o0:o1].strip() + b")"
            src = src[:s0] + new + src[e0:]
        open(f, "wb").write(src)
        print("  fixed %d in %s" % (len(spans), f))


def main(argv):
    fix = "--fix" in argv
    argv = [a for a in argv if a != "--fix"]
    dirs = argv or sorted(os.path.join(VIPS, d) for d in os.listdir(VIPS)
                          if os.path.isdir(os.path.join(VIPS, d)))
    total = 0
    for vdir in dirs:
        edits = {} if fix else None
        res = scan(vdir, edits)
        if fix and edits:
            apply_edits(edits)
            res = scan(vdir)
        name = os.path.basename(os.path.normpath(vdir))
        if res is None:
            print("%s SVA_LINT_FAIL" % name)
            total += 1
            continue
        print("%s SVA_TAUTOLOGIES=%d" % (name, len(res)))
        for f, line, kind in res:
            src = open(os.path.join(vdir, f), errors="replace").read().splitlines()[line - 1].strip()
            print("  %s:%d %s %s" % (f, line, kind, src[:160]))
        total += len(res)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
