#!/usr/bin/env python3
"""Deterministic P1 integration evaluations; no network, model or optional provider required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / '.ai-harness' / 'runtime'
sys.path.insert(0, str(RUNTIME))

from p1 import affected_profile_fields, extension_manifest, negotiate, profile, regression_case
from p1_pipeline import apply_route, build_task_state, finalize_proof, plan_controls, record_verification


def check(case_id: str, fn):
    try:
        fn()
        return {'id': case_id, 'passed': True}
    except Exception as exc:
        return {'id': case_id, 'passed': False, 'error': f'{type(exc).__name__}: {exc}'}


def main() -> int:
    cases = [
        check('dna-provenance', lambda: dna()),
        check('dna-targeted-invalidation', lambda: invalidation()),
        check('state-route-proof-chain', lambda: chain()),
        check('risk-controls-derived', lambda: risk()),
        check('optional-extension-degradation', lambda: extension()),
        check('regression-stability', lambda: regression()),
        check('proof-determinism', lambda: proof()),
        check('no-provider-required', lambda: provider_free()),
    ]
    passed = sum(item['passed'] for item in cases)
    report = {'suite': 'p1', 'cases': len(cases), 'passed': passed, 'failed': len(cases) - passed, 'release_ready': passed == len(cases), 'results': cases}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['release_ready'] else 1


def dna():
    p = profile('repo', {'tests': {'status': 'observed', 'value': 'native', 'evidence_ids': ['z', 'a']}})
    assert p['facts']['tests']['status'] == 'observed'
    assert p['facts']['tests']['evidence_ids'] == ['a', 'z']


def invalidation():
    assert affected_profile_fields(['deploy/Dockerfile']) == ['deployment']
    assert 'tests' in affected_profile_fields(['src/service.py'])


def chain():
    s = build_task_state('EVAL-CHAIN', 'Fix export')
    apply_route(s, {'mode': 'debug', 'risk': 'medium'})
    record_verification(s, 'unit', 'passed', 'native-test')
    assert s['decisions'] and s['decisions'][0]['evidence_ids']
    assert s['verification'] and s['verification'][0]['evidence_ids']
    assert finalize_proof(s)['evidence_ids']


def risk():
    s = build_task_state('EVAL-RISK', 'Change authentication')
    plan_controls(s, {'security_risk': 3})
    assert s['metadata']['risk']['level'] == 'critical'
    assert s['metadata']['risk']['controls'] == ['explicit_approval', 'isolated_execution', 'broader_verification', 'independent_review']


def extension():
    result = negotiate(['graph.search', 'memory.read'], [extension_manifest('memory', ['memory.read'])])
    assert result['degraded'] and result['missing'] == ['graph.search']


def regression():
    assert regression_case('bug', 'fixed') == regression_case('bug', 'fixed')


def proof():
    s = build_task_state('EVAL-PROOF', 'goal')
    assert finalize_proof(s)['proof_id'] == finalize_proof(s)['proof_id']


def provider_free():
    s = build_task_state('EVAL-OFFLINE', 'goal')
    assert s['metadata']['profile']['profile_version'] == '1.0'


if __name__ == '__main__':
    raise SystemExit(main())
