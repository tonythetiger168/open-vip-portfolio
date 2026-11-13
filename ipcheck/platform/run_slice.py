# SPDX-License-Identifier: Apache-2.0
"""Bounded RTL elaboration/seed-replay gate, explicitly not a UVM SoC run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip-dir', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--upstream-apb', type=Path)
    args = parser.parse_args()
    root = args.ip_dir.resolve()
    ev = args.evidence_dir.resolve()
    ev.mkdir(parents=True, exist_ok=True)
    source = [args.upstream_apb.resolve() if args.upstream_apb else root/'rtl/APB_top.sv',
              root/'rtl/platform/apb_window_router.sv', root/'rtl/platform/platform_apb_slice.sv']
    bench = Path(__file__).with_name('platform_apb_crv_tb.sv').resolve()
    hashes = {p.name: digest(p) for p in source+[bench]}
    baseline = json.loads((root/'integration/platform/baseline.json').read_text(encoding='utf-8'))
    if digest(root/baseline['filelist']) != baseline['filelist_sha256']:
        raise RuntimeError('filelist differs from frozen fixture baseline')
    for pin, actual in zip(baseline['sources'], source, strict=True):
        if digest(actual) != pin['sha256']:
            raise RuntimeError('RTL differs from frozen fixture baseline: '+pin['path'])
    if digest(bench) != baseline['bench']['sha256']:
        raise RuntimeError('bench differs from frozen fixture baseline')
    vip_root = Path(__file__).resolve().parents[2]
    for pin in baseline['verification_sources']:
        if digest(vip_root/pin['path']) != pin['sha256']:
            raise RuntimeError('verification source differs from frozen baseline: '+pin['path'])
    summary = {'scope': 'platform_apb_slice fixture, not product SoC or UVM coverage',
               'source_sha256': hashes, 'baseline_source_set_sha256': baseline['source_set_sha256'],
               'config_sha256': {p['config']['product']:p['config_sha256'] for p in baseline['profiles']},
               'invocation': ['python3', *sys.argv], 'runs': [], 'coverage_db': None,
               'six_metric_closure': 'BLOCKED: no supported coverage export; full product RTL absent'}

    def run(cmd, logfile, expect_fail=False):
        cp = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, timeout=120)
        (ev/logfile).write_text(cp.stdout+cp.stderr, encoding='utf-8')
        if (cp.returncode == 0) == expect_fail:
            raise RuntimeError(f'{logfile}: exit {cp.returncode}')
        return cp.stdout+cp.stderr

    with tempfile.TemporaryDirectory(prefix='platform-slice-') as tmp:
        image = Path(tmp)/'slice.vvp'
        run(['iverilog','-g2012','-s','platform_apb_crv_tb','-o',image,*source,bench], 'elaboration.log')
        for product_id, product in enumerate(('TV','STB','IPCAM')):
            for seed in (1,7,42):
                log = run(['vvp',image,f'+PRODUCT={product_id}',f'+SEED={seed}'],f'{product}-seed{seed}.log')
                match = re.search(r'TEST PASSED: PLATFORM_SLICE product=(\d+) seed=(\d+) transactions=(\d+) checks=(\d+)',log)
                # Every transaction has setup/completion/response checks; data/wait checks add more.
                if not match or int(match[3]) != 209 or int(match[4]) < 209 * 3:
                    raise RuntimeError('missing nonzero scoreboard witnesses')
                summary['runs'].append({'profile_label':product,'config':'apb-memory-fixture-v1',
                                        'seed':seed,'transactions':int(match[3]),'checks':int(match[4]),
                                        'result':'bounded RTL checks passed; not SoC/UVM closure'})
        # Same seed must reproduce exact log contents; there is no random time seed.
        replay = run(['vvp',image,'+PRODUCT=0','+SEED=7'], 'TV-seed7-replay.log')
        if replay != (ev/'TV-seed7.log').read_text(encoding='utf-8'):
            raise RuntimeError('seed replay changed')
        summary['seed_replay'] = 'TV seed7 exact log match'
        mutant = Path(tmp)/'partial_mutant.sv'
        text = source[2].read_text(encoding='utf-8')
        anchor = "assign partial_write = pwrite && pstrb != 4'hf;"
        if text.count(anchor) != 1:
            raise RuntimeError('partial-write mutation anchor changed')
        mutant.write_text(text.replace(anchor, "assign partial_write = 1'b0;"),encoding='utf-8')
        run(['iverilog','-g2012','-s','platform_apb_crv_tb','-o',image,*source[:2],mutant,bench], 'mutation_compile.log')
        bad = run(['vvp',image,'+PRODUCT=0','+SEED=7'], 'mutation_partial_write.log', expect_fail=True)
        if 'TEST FAILED:' not in bad or 'independent memory scoreboard' not in bad:
            raise RuntimeError('mutant did not exercise independent checker')
        summary['mutation'] = 'removed partial-write rejection detected by response and memory scoreboard'
    version = subprocess.run(['iverilog','-V'],capture_output=True,text=True,timeout=20)
    summary['tool'] = (version.stdout+version.stderr).splitlines()[0]
    summary['command'] = 'python3 ipcheck/platform/run_slice.py --ip-dir <checkout> --evidence-dir <evidence>'
    (ev/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
