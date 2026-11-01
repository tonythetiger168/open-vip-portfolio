# SPDX-License-Identifier: Apache-2.0
"""Run an isolated APB router check, mutation and generic synthesis on Linux.

No generated VIP zips are changed; this is a cross-repository prototype bench.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ip-dir', type=Path, required=True)
    ap.add_argument('--evidence-dir', type=Path, required=True)
    args = ap.parse_args()
    source = (args.ip_dir / 'rtl/platform/apb_window_router.sv').resolve()
    bench = Path(__file__).with_name('apb_window_router_tb.sv').resolve()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(argv, label, expected=0):
        result = subprocess.run([str(a) for a in argv], capture_output=True, text=True, timeout=120)
        (evidence / (label + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        commands.append({'label': label, 'argv': [str(a) for a in argv], 'exit_code': result.returncode})
        if (result.returncode == 0) != (expected == 0):
            raise RuntimeError(label + ' unexpected exit code: ' + str(result.returncode))
        return result.stdout + result.stderr

    with tempfile.TemporaryDirectory(prefix='platform-apb-') as td:
        td = Path(td)
        image = td / 'apb.vvp'
        run(['iverilog', '-g2012', '-s', 'apb_window_router_tb', '-o', image, source, bench], 'compile')
        log = run(['vvp', image], 'simulation')
        if 'TEST PASSED: PLATFORM_APB checks=16' not in log:
            raise RuntimeError('missing non-vacuous check count')
        mutant = td / 'mutant.sv'
        text = source.read_text(encoding='utf-8')
        if text.count("pslverr = 1'b1;") != 1:
            raise RuntimeError('mutation anchor changed')
        mutant.write_text(text.replace("pslverr = 1'b1;", "pslverr = 1'b0;"), encoding='utf-8')
        run(['iverilog', '-g2012', '-s', 'apb_window_router_tb', '-o', image, mutant, bench], 'mutant_compile')
        log = run(['vvp', image], 'mutant_simulation', expected=1)
        if 'TEST FAILED:' not in log:
            raise RuntimeError('mutant did not fail through checker')
        # No technology library: successful generic synthesis is not physical PPA.
        run(['yosys', '-p', f'read_verilog -sv "{source}"; synth -top apb_window_router; check -assert; stat'], 'synthesis')
    versions = {}
    for cmd in (['iverilog', '-V'], ['yosys', '-V']):
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        versions[cmd[0]] = (out.stdout + out.stderr).splitlines()[0]
    report = {'python': platform.python_version(), 'tools': versions,
              'sha256': {'source': hashlib.sha256(source.read_bytes()).hexdigest(),
                         'bench': hashlib.sha256(bench.read_bytes()).hexdigest()},
              'scope': 'APB two-window combinational router prototype only; not SoC/host qualification',
              'directed_checks': 16, 'mutation': 'default error response removed: detected',
              'generic_synthesis': 'completed; no technology library, STA or PPA', 'commands': commands}
    (evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
