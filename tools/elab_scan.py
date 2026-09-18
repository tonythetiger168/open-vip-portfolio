#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""elab_scan.py <vip_dir> — pyslang elaboration gate (L1a).

Prints ``ELAB_ERRORS=<n>`` plus up to 25 error lines with source locations.
Always exits 0; CI must grep for ``^ELAB_ERRORS=0$`` to judge pass/fail.

The Accellera uvm-core ``src`` directory is located via the ``UVM_CORE``
environment variable; if unset, ``<repo>/uvm-core/src`` is used.
"""
import sys, os, glob
from pyslang import driver
from pyslang.pyslang import DiagnosticEngine
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UVM = os.environ.get('UVM_CORE', os.path.join(_repo_root, 'uvm-core', 'src'))
def ordered(root):
    allsv = sorted(glob.glob(os.path.join(root,'**','*.sv'), recursive=True))
    def key(f):
        b = os.path.basename(f)
        if 'common_pkg' in b: return (0,f)
        if b.endswith('_defs.sv'): return (1,f)
        if b.endswith('_if.sv'): return (2,f)
        if b.endswith('_pkg.sv'): return (3,f)
        if 'top_tb' in b or 'tb_top' in b: return (5,f)
        return (4,f)
    return [os.path.join(UVM,'uvm_pkg.sv')] + sorted(allsv,key=key), allsv
def run(root):
    files, allsv = ordered(root)
    incdirs = sorted({os.path.dirname(f) for f in allsv} | {UVM, UVM+'/macros'})
    d = driver.Driver(); d.addStandardArgs()
    if not d.parseCommandLine('--lint-only --single-unit --timescale=1ns/1ps ' + ' '.join(f'-I{x}' for x in incdirs) + ' ' + ' '.join(files)):
        return ['CMDLINE_FAIL']
    d.processOptions()
    if not d.parseAllSources():
        return ['PARSE_FAIL']
    comp = d.createCompilation()
    diags = list(comp.getAllDiagnostics())
    errs = [x for x in diags if x.isError()]
    txt = DiagnosticEngine.reportAll(d.sourceManager, errs) if errs else ''
    lines = [l for l in txt.splitlines() if ': error:' in l]
    return lines[:25]
if __name__ == '__main__':
    lines = run(sys.argv[1])
    print(f'ELAB_ERRORS={len(lines)}')
    for l in lines: print('  ' + l[:260])
