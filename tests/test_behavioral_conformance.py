import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "behavioral_conformance.py"
TASKS = ROOT / ".ai-harness" / "conformance" / "tasks.jsonl"


def load_module():
    spec = importlib.util.spec_from_file_location("aer_behavioral_conformance_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_corpus_has_exactly_ten_representative_tasks():
    module = load_module()
    tasks = module.load_tasks()
    module.validate_tasks(tasks)
    assert len(tasks) == 10
    assert {t["mode"] for t in tasks} == {"read_only", "write"}


def test_behavioral_contract_requires_all_dimensions():
    module = load_module()
    assert module.DIMENSIONS == (
        "scope_adherence", "context_selection", "tool_usage", "verification_evidence",
        "regression_detection", "recovery", "final_outcome",
    )
    result = {key: "evidence" for key in module.REQUIRED_FIELDS}
    result["context_lease_digests"] = ["sha256:test"]
    result["tool_observations"] = [{"tool": "pytest", "reason": "verify"}]
    dims, missing = module.semantic_score({"id": "BC-TEST"}, result)
    assert not missing
    assert all(value == 1.0 for value in dims.values())


def test_pairwise_report_shape_is_provider_neutral():
    module = load_module()
    assert "claude" in module.load_json(module.MATRIX)["providers"]
    assert "codex" in module.load_json(module.MATRIX)["providers"]
    assert "gemini" in module.load_json(module.MATRIX)["providers"]
    assert "chatgpt" in module.load_json(module.MATRIX)["providers"]
