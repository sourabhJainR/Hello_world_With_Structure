import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".ai-harness"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from runtime.requirement_traceability import normalize_requirements, persist_requirement_traceability


def test_requirement_chain_records_full_coverage(tmp_path):
    source = {
        "jira_id": "PROJ-42",
        "requirements": [{
            "requirement_id": "REQ-42",
            "requirement": "Persist the generated engineering report.",
            "acceptance_criteria": [{"criterion_id": "REQ-42.AC-1", "text": "Report is persisted after the run."}],
            "design_pointer": "docs/design.md#report",
            "code_pointer": ".ai-harness/runtime/work_report.py:write",
            "test_pointer": "tests/test_work_report.py::test_report",
            "evidence_pointer": "runs/42/manifest.json"
        }]
    }
    requirements = normalize_requirements(source)
    payload = persist_requirement_traceability(
        tmp_path, "run-42", jira_id="PROJ-42", work_type="engineering",
        requirements=requirements, regression_ids=["REG-1"], replay=[{"replay_id": "RP-1", "passed": True}],
        evidence=[{"type": "manifest", "path": "runs/42/manifest.json"}], source="runs/42/manifest.json"
    )
    assert payload["coverage"] == {"total_criteria": 1, "covered": 1, "partial": 0, "uncovered": 0, "residual_gaps": []}
    row = payload["requirements"][0]
    assert row["requirement_id"] == "REQ-42"
    assert row["criterion_id"] == "REQ-42.AC-1"
    assert row["regression_ids"] == ["REG-1"]
    assert row["replay_ids"] == ["RP-1"]
    assert row["replay_status"] == "passed"


def test_jira_requirement_without_acceptance_criteria_is_an_explicit_gap():
    rows = normalize_requirements({"jira_id": "PROJ-9"}, fallback_goal="Fix report traceability")
    assert len(rows) == 1
    assert rows[0]["requirement"] == "Fix report traceability"
    payload = persist_requirement_traceability(Path("/tmp"), "traceability-test-gap", jira_id="PROJ-9", requirements=rows)
    row = payload["requirements"][0]
    assert row["status"] == "partially-covered"
    assert "acceptance criterion" in row["residual_gap"]


def test_requirement_ids_are_deterministic_and_replay_failure_is_visible(tmp_path):
    a = normalize_requirements({"requirements": ["Same requirement"]})
    b = normalize_requirements({"requirements": ["Same requirement"]})
    assert a[0]["requirement_id"] == b[0]["requirement_id"]
    payload = persist_requirement_traceability(tmp_path, "run-fail", requirements=a, replay=[{"replay_id": "RP-2", "passed": False}])
    assert payload["requirements"][0]["replay_status"] == "failed"
    assert payload["requirements"][0]["status"] == "partially-covered"
    assert "replay" in payload["requirements"][0]["residual_gap"]
