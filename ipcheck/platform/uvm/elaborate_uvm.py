# SPDX-License-Identifier: Apache-2.0
"""Strict native SV frontend gate; does not execute UVM or replace simulator build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--ip-dir',type=Path,required=True)
    ap.add_argument('--uvm-core',type=Path,required=True)
    ap.add_argument('--evidence-dir',type=Path,required=True)
    ap.add_argument('--pyslang-root',type=Path)
    ap.add_argument('--upstream-apb',type=Path)
    args=ap.parse_args()
    if args.pyslang_root: sys.path.insert(0,str(args.pyslang_root.resolve()))
    import pyslang
    if pyslang.__version__!='12.1.0': raise RuntimeError('frontend version differs from pinned 12.1.0')
    from pyslang import driver, DiagnosticEngine, DiagnosticSeverity
    from run_uvm_slice import UVM_COMMITS
    from uvm_source_lock import verify_pins
    core=args.uvm_core.resolve(); root=args.ip_dir.resolve(); here=Path(__file__).resolve().parent
    revision=subprocess.check_output(['git','-C',str(core),'rev-parse','HEAD'],text=True).strip()
    if revision not in UVM_COMMITS: raise RuntimeError('unpinned UVM source')
    dirty=subprocess.check_output(['git','-c','core.filemode=false','-C',str(core),'status','--porcelain'],text=True)
    if dirty.strip(): raise RuntimeError('modified UVM source')
    files=[core/'src/uvm_pkg.sv',here/'platform_apb_if.sv',here/'platform_apb_pkg.sv',
           args.upstream_apb.resolve() if args.upstream_apb else root/'rtl/APB_top.sv',
           root/'rtl/platform/apb_window_router.sv',root/'rtl/platform/platform_apb_slice.sv',here/'platform_uvm_tb.sv']
    lock_id=verify_pins(root,here,files[3:6])
    quote=lambda value:'"'+str(value).replace('\\','/')+'"'
    command='--lint-only --single-unit --timescale=1ns/1ps -DUVM_NO_DPI -I'+quote(core/'src')+' '+' '.join(quote(p) for p in files)
    d=driver.Driver(); d.addStandardArgs()
    if not d.parseCommandLine(command): raise RuntimeError('frontend command line rejected')
    d.processOptions()
    if not d.parseAllSources(): raise RuntimeError('source parsing rejected')
    comp=d.createCompilation(); diags=list(comp.getAllDiagnostics())
    errors=[x for x in diags if d.diagEngine.getSeverity(x.code,x.location) in (DiagnosticSeverity.Error,DiagnosticSeverity.Fatal)]
    text=DiagnosticEngine.reportAll(d.sourceManager,diags)
    ev=args.evidence_dir.resolve(); ev.mkdir(parents=True,exist_ok=True)
    (ev/'frontend.log').write_text(text,encoding='utf-8')
    report={'scope':'static SV/UVM frontend semantics only; no simulation, coverage or runtime topology proof',
            'tool':'pyslang '+pyslang.__version__,'uvm_commit':revision,'strict_errors':len(errors),
            'locked_source_set_sha256':lock_id,
            'warnings':sum(d.diagEngine.getSeverity(x.code,x.location)==DiagnosticSeverity.Warning for x in diags),
            'diagnostics_total':len(diags),'status':'FRONTEND_PASS' if not errors else 'FRONTEND_FAIL',
            'command':command,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'simulation':'NOT_RUN_BY_THIS_GATE','raw_coverage_db':None}
    (ev/'frontend.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    raise SystemExit(1 if errors else 0)


if __name__=='__main__': main()
