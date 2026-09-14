from pathlib import Path

from portable.agency_observability import Dataset, DatasetItem
from portable.agency_regression_loop import RegressionPlan
from portable.agency_release_lifecycle import ArtifactStore
from portable.agency_runtime import TaskProfile, execute


def test_execute_applies_promote_to_artifact(tmp_path: Path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("candidate", encoding="utf-8")
    store = ArtifactStore(tmp_path / "releases")
    dataset = Dataset("smoke", "1", (DatasetItem("case", "ok"),))
    plan = RegressionPlan(
        dataset=dataset,
        execute_case=lambda trace, value: value,
        judge=lambda trace, item, output: {"quality": 1.0},
    )
    task = TaskProfile("t-release", "ship artifact")

    def worker(task, assignments):
        return {
            "deliverables": [str(artifact)],
            "verification": ["smoke"],
            "dimensions": {
                "correctness": 25, "completeness": 15, "evidence": 15,
                "verification": 15, "scope_discipline": 10,
                "security_and_safety": 10, "clarity": 5, "maintainability": 5,
            },
            "hard_gates": {"tests": True},
            "evidence": [{"source": "test", "claim": "artifact verified"}],
        }

    result = execute(task, worker, regression_plan=plan, release_store=store, release_artifact=str(artifact))
    assert result.promotion_decision.action == "promote"
    assert result.release_state.action == "promote"
    assert store.state()["current"]["artifact_id"] == "t-release"
