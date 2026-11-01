#!/usr/bin/env python3
# Copyright 2026 VIP Portfolio Contributors
# SPDX-License-Identifier: Apache-2.0
"""elab_scan.py <vip_dir> — pyslang elaboration gate (L1a).

Prints ``ELAB_ERRORS=<n>`` (all errors, not capped), ``ELAB_LRM_ERRORS=<n>``
(diagnostics slang's engine rates as errors; see run()) and up to 25
diagnostic lines with source locations. ELAB_STRICT=1 makes ELAB_ERRORS
count the LRM errors too.
Always exits 0; CI must grep for ``^ELAB_ERRORS=0$`` to judge pass/fail.

The Accellera uvm-core ``src`` directory is located via the ``UVM_CORE``
environment variable; if unset, ``<repo>/uvm-core/src`` is used.

``xchk/`` directories hold cross-check benches for open-ip-portfolio RTL
that this repo does not ship (see tools/sync_xchk_models.py). They are left
out unless ``OIP_DIR`` names an open-ip-portfolio checkout; then they are
elaborated too, with ``$OIP_DIR/rtl`` as a library directory (``-y``).
"""
import sys, os, glob
from pyslang import driver
from pyslang.pyslang import DiagnosticEngine, DiagnosticSeverity
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UVM = os.environ.get('UVM_CORE', os.path.join(_repo_root, 'uvm-core', 'src'))
OIP = os.environ.get('OIP_DIR', '')
def ordered(root):
    allsv = sorted(glob.glob(os.path.join(root,'**','*.sv'), recursive=True))
    if not OIP:
        allsv = [f for f in allsv
                 if 'xchk' not in os.path.relpath(f, root).split(os.sep)[:-1]]
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
    lib = f" -y {os.path.join(OIP, 'rtl')} --libext .sv" if OIP else ''
    d = driver.Driver(); d.addStandardArgs()
    if not d.parseCommandLine('--lint-only --single-unit --timescale=1ns/1ps ' + ' '.join(f'-I{x}' for x in incdirs) + lib + ' ' + ' '.join(files)):
        return ['CMDLINE_FAIL'], ['CMDLINE_FAIL'], ['CMDLINE_FAIL']
    d.processOptions()
    if not d.parseAllSources():
        return ['PARSE_FAIL'], ['PARSE_FAIL'], ['PARSE_FAIL']
    comp = d.createCompilation()
    diags = list(comp.getAllDiagnostics())
    # Diagnostic.isError() reports slang's built-in default severity. The
    # driver's engine raises more codes to error, e.g. Redefinition (duplicate
    # class / clocking item), VirtualArgNameMismatch, UnknownSystemName; those
    # are LRM violations other simulators reject, but reportAll() prints them
    # as "warning:". They are counted as ELAB_LRM_ERRORS and only gate the
    # result (ELAB_ERRORS) when ELAB_STRICT=1.
    eng = d.diagEngine
    lrm = [x for x in diags
           if eng.getSeverity(x.code, x.location) in (DiagnosticSeverity.Error, DiagnosticSeverity.Fatal)]
    errs = lrm if os.environ.get('ELAB_STRICT') == '1' else [x for x in diags if x.isError()]
    shown = errs + [x for x in lrm if x not in errs]
    txt = DiagnosticEngine.reportAll(d.sourceManager, shown) if shown else ''
    lines = [l for l in txt.splitlines() if ': error:' in l or ': warning:' in l or ': fatal' in l]
    return errs, lrm, lines
if __name__ == '__main__':
    errs, lrm, lines = run(sys.argv[1])
    print(f'ELAB_ERRORS={len(errs)}')
    print(f'ELAB_LRM_ERRORS={len(lrm)}')
    for l in lines[:25]: print('  ' + l[:260])
