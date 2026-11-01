# SPDX-License-Identifier: Apache-2.0
"""Fail-closed export contract checker. NOT a tool DB parser or coverage proof."""
import argparse
import hashlib
import json
from pathlib import Path

METRICS = ('line', 'fsm', 'toggle', 'branch', 'sva', 'functional')
IDENTITY = ('product', 'config_sha256', 'scope', 'source_set_sha256',
            'filelist_sha256', 'tool', 'tool_version', 'instrumentation_sha256')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compatible(a, b):
    for key in IDENTITY:
        require(a.get(key) and a.get(key) == b.get(key), 'identity mismatch: ' + key)


def assess(report, baseline, approvals, root):
    compatible(report['identity'], baseline['identity'])
    require(report.get('build_kind') == 'rtl', 'stub/TLM build cannot close RTL')
    require(report.get('blocked_dependencies') == [], 'unresolved RTL dependencies')
    require(report.get('assertion_failures') == 0, 'assertion failure or missing count')
    require(report.get('scoreboard_errors') == 0, 'scoreboard failure or missing count')
    require(report.get('transactions', 0) > 0, 'vacuous test')
    raw_db = root / report['raw_db']['path']
    require(raw_db.is_file(), 'raw DB missing')
    require(hashlib.sha256(raw_db.read_bytes()).hexdigest() == report['raw_db']['sha256'], 'raw DB hash mismatch')
    require(report.get('exporter_id'), 'missing tool exporter identity')
    result = {}
    for metric in METRICS:
        item = report['metrics'][metric]
        require(item.get('status') == 'measured', metric + ' not measured/supported')
        points = item['raw_points']
        require(len(points) == len(set(points)), metric + ' duplicate points')
        raw = set(points)
        require(raw == set(baseline['points'][metric]) and raw, metric + ' denominator mismatch/empty')
        hits = set(item['hit_points'])
        require(hits <= raw, metric + ' unknown hit')
        excluded = set()
        for waiver in item.get('exclusions', []):
            point = waiver['point']
            approval = approvals.get(waiver['approval_id'])
            require(approval is not None and approval.get('approved_by') and approval.get('evidence'), 'unapproved exclusion')
            require(approval.get('identity') == report['identity'] and approval.get('metric') == metric
                    and approval.get('point') == point, 'exclusion outside approved scope')
            require(point in raw and point not in excluded, 'invalid/duplicate exclusion')
            excluded.add(point)
        effective = raw - excluded
        require(effective, metric + ' no effective denominator')
        if metric == 'fsm':
            require(any(p.startswith('state:') for p in raw) and any(p.startswith('arc:') for p in raw), 'FSM needs states and arcs')
        if metric == 'functional':
            for point in effective:
                req = baseline['functional_requirements'].get(point)
                require(req and req.get('requirement') and req.get('legal') is True, 'untraced/illegal functional bin')
        if metric == 'sva':
            stats = item['assertions']
            require(set(stats) == raw, 'SVA assertion inventory mismatch')
            for point, counters in stats.items():
                require(counters['failures'] == 0, 'SVA failure cannot be waived')
                if point in effective:
                    require(counters['attempts'] >= counters['antecedent_hits'] > 0, 'SVA vacuous antecedent')
                    require(0 < counters['nonvacuous_passes'] <= counters['antecedent_hits'], 'SVA nonvacuous pass missing')
                    require(counters['cover_witnesses'] > 0, 'SVA witness missing')
        result[metric] = {'raw_total': len(raw), 'raw_hit': len(hits),
                          'approved_excluded': len(excluded), 'effective_total': len(effective),
                          'effective_hit': len(effective & hits), 'closed': effective <= hits}
    require(all(m['closed'] for m in result.values()), 'coverage holes remain')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report', type=Path)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--approvals', type=Path, required=True)
    args = ap.parse_args()
    try:
        result = assess(json.loads(args.report.read_text()), json.loads(args.baseline.read_text()),
                        json.loads(args.approvals.read_text()), args.report.parent)
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('BLOCKED/OPEN: ' + str(error))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
