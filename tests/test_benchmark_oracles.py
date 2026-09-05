from __future__ import annotations
import tempfile
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import benchmark_oracles as b
import conformance_oracles as o


def test_fingerprint_changes_when_file_changes():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/'a.txt').write_text('one',encoding='utf-8')
        before=b.fingerprint(root); (root/'a.txt').write_text('two',encoding='utf-8'); after=b.fingerprint(root)
        assert before['digest'] != after['digest']
        assert after['files']['a.txt'] != before['files']['a.txt']


def test_recovery_requires_ordered_failure_then_success():
    trace=[
        {'event':'failure_injected','command':'pytest','returncode':97,'injected':True,'invocation_id':'1'},
        {'event':'command_end','command':'pytest','returncode':0,'injected':False,'invocation_id':'2'},
    ]
    result=b.failure_recovery(trace)
    assert result['failure_count']==1
    assert result['exact_order_verified'] is True


def test_recovery_does_not_accept_success_without_failure():
    result=b.failure_recovery([{'event':'command_end','command':'pytest','returncode':0,'invocation_id':'1'}])
    assert result['exact_order_verified'] is False


def test_bc02_oracle_and_mutation_are_executable():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); cfg=o.prepare('BC-02',root)
        # Simulate the expected implementation independently of a provider.
        (root/cfg['implementation']).write_text("def slugify_name(name):\n    import re\n    return re.sub(r'[^a-z0-9]+','-',name.strip().lower()).strip('-')\n",encoding='utf-8')
        assert b.ast_invariants(root,'BC-02',cfg)['required_function']
        assert b.hidden_acceptance(root,'BC-02',cfg)['hidden_slug_cases']


def test_observability_reports_missing_telemetry_separately():
    with tempfile.TemporaryDirectory() as td:
        result=b.observability(Path(td)/'missing.jsonl',['repo-map','tests'])
        assert result['telemetry_available'] is False
        assert result['observability_score']==0.0
