# SPDX-License-Identifier: Apache-2.0
"""Pinned public UVM runtime, bounded RTL APB fixture. No product/coverage claim."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from uvm_source_lock import verify_pins

UVM_COMMITS = {'78c06547a2a0a29b3dc9dcafae62b75b2ff61544': '2020.3.1',
               '39dfb0077ae25d69d1e66bf7d6a56861e244150f': '2020-2.0'}


def classify_run(rc, log, seed):
    marker=re.search(r'UVM_PLATFORM_PASS transactions=(\d+) checks=(\d+) seed=(\d+)',log)
    errors=re.search(r'^UVM_ERROR\s*:\s*(\d+)',log,re.M)
    fatals=re.search(r'^UVM_FATAL\s*:\s*(\d+)',log,re.M)
    error_events=re.findall(r'^UVM_(?:ERROR|FATAL)\b(?!\s*:)',log,re.M)
    passed=rc==0 and marker and int(marker[1])==208 and int(marker[2])>=208 and int(marker[3])==seed
    passed=passed and errors and fatals and int(errors[1])==0 and int(fatals[1])==0 and not error_events
    return bool(passed),marker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ip-dir', type=Path, required=True)
    ap.add_argument('--uvm-core', type=Path, required=True, help='official uvm-core checkout, not src/')
    ap.add_argument('--evidence-dir', type=Path, required=True)
    ap.add_argument('--upstream-apb', type=Path)
    ap.add_argument('--verilator', default='verilator')
    args = ap.parse_args()
    ev = args.evidence_dir.resolve(); ev.mkdir(parents=True, exist_ok=True)
    root = args.ip_dir.resolve(); uvm=args.uvm_core.resolve(); here=Path(__file__).resolve().parent
    revision=subprocess.check_output(['git','-C',str(uvm),'rev-parse','HEAD'],text=True).strip()
    if revision not in UVM_COMMITS:
        raise RuntimeError('UVM revision differs from pinned official release')
    if subprocess.check_output(['git','-C',str(uvm),'status','--porcelain'],text=True).strip():
        raise RuntimeError('UVM checkout modified; new fingerprint required')
    rtl=[args.upstream_apb.resolve() if args.upstream_apb else root/'rtl/APB_top.sv',
         root/'rtl/platform/apb_window_router.sv',root/'rtl/platform/platform_apb_slice.sv']
    sv=[here/'platform_apb_if.sv',here/'platform_apb_pkg.sv',here/'platform_uvm_tb.sv']
    locked_source_set=verify_pins(root,here,rtl)
    verification=[Path(__file__).resolve(),here/'test_run_uvm_slice.py']
    report={'scope':'real UVM APB fixture only; not product SoC, RAL or coverage closure',
            'uvm_commit':revision,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl+sv},
            'runs':[], 'raw_coverage_db':None}
    report['locked_source_set_sha256']=locked_source_set
    report['tool']=subprocess.check_output([args.verilator,'--version'],text=True).strip()
    normalized_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl+sv+verification}
    identity={'product':'PLATFORM_COMPONENT_ONLY','scope':'platform_uvm_tb.dut',
              'locked_source_set_sha256':locked_source_set,
              'config':'apb-memory-fixture-v1','uvm_commit':revision,'tool':report['tool'],
              'sources':normalized_sources,'flags':['--timing','--assert','UVM_NO_DPI']}
    report['identity']=identity
    report['source_set_sha256']=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def execute(cmd, filename, timeout=120):
        with (ev/filename).open('w') as log:
            try:
                cp=subprocess.run([str(x) for x in cmd],stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            except subprocess.TimeoutExpired:
                log.write('\nTIMEOUT\n')
                return 124,'TIMEOUT'
        return cp.returncode,(ev/filename).read_text(errors='replace')

    with tempfile.TemporaryDirectory(prefix='platform-uvm-') as tmp:
        obj=Path(tmp)/'obj'
        cmd=[args.verilator,'--binary','--timing','--assert','-j','2','-Wno-fatal','-Wno-lint','-Wno-style',
             '--top-module','platform_uvm_tb','-Mdir',obj,'+define+UVM_NO_DPI',
             '+incdir+'+str(uvm/'src'),uvm/'src/uvm_pkg.sv',sv[0],sv[1],*rtl,sv[2]]
        report['build_command']=[str(x) for x in cmd]
        print('Building pinned UVM APB fixture; full output in build.log',flush=True)
        rc,log=execute(cmd,'build.log',timeout=600)
        report['build_exit_code']=rc
        if rc:
            report['status']='BLOCKED_BUILD'; (ev/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print('\n'.join(l for l in log.splitlines() if '%Error' in l)[:6000])
            raise SystemExit(1)
        exe=obj/'Vplatform_uvm_tb'
        for seed in (1,7,42):
            rc,log=execute([exe,f'+SEED={seed}'],f'seed{seed}.log')
            passed,marker=classify_run(rc,log,seed)
            report['runs'].append({'seed':seed,'exit_code':rc,'passed':bool(passed),
                                   'transactions':int(marker[1]) if marker else 0,'checks':int(marker[2]) if marker else 0})
            if not passed:
                report['status']='FAILED_TEST'; (ev/'result.json').write_text(json.dumps(report,indent=2)+'\n')
                raise RuntimeError(f'UVM test seed{seed} failed; see raw log')
            print(f'UVM fixture seed{seed}: {marker[1]} transactions, {marker[2]} checks',flush=True)
        rc,replay=execute([exe,'+SEED=7'],'seed7-replay.log')
        original=(ev/'seed7.log').read_text()
        trace=lambda log: re.findall(r'APB_EVENT [^\n]+',log)
        if not classify_run(rc,replay,7)[0] or len(trace(replay))!=208 or trace(replay)!=trace(original):
            raise RuntimeError('UVM accepted-wire-event replay mismatch')
        report['replay_trace_sha256']=hashlib.sha256('\n'.join(trace(replay)).encode()).hexdigest()
        rc,bad=execute([exe,'+SEED=7','+CORRUPT_MONITOR_ONCE'],'negative-monitor.log')
        if classify_run(rc,bad,7)[0] or 'passive memory scoreboard mismatch' not in bad:
            raise RuntimeError('passive scoreboard did not detect injected observation error')
        report['negative_checker']='one corrupted monitored read detected; not a DUT mutation'
    report['status']='BOUNDED_UVM_PASS'
    (ev/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
