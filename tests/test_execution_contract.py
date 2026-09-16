"""Contract tests for the canonical cross-phase execution envelope."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from portable.execution_contract import (
    EvidenceReference,
    ExecutionEnvelope,
    ExecutionIntent,
    ExecutionPlanRef,
    RepositoryReference,
)

ROOT = Path(__file__).resolve().parents[1]


class ExecutionContractTests(unittest.TestCase):
    def _envelope(self) -> ExecutionEnvelope:
        return ExecutionEnvelope(
            intent=ExecutionIntent(task_id="task-1", goal="consolidate execution identity"),
            repository=RepositoryReference(digest="repo-digest", root="/repo"),
            plan=ExecutionPlanRef(plan_id="plan-1", task_ids=("task-1", "task-2")),
            evidence=(EvidenceReference("ev-1", snapshot="repo-digest", freshness="current"),),
            decisions=("use canonical repository model",),
            changeset_id="change-1",
            verification_ids=("verify-1",),
            review_ids=("review-1",),
            regression_ids=("reg-1",),
            release_ids=(),
            metadata={"mode": "single-agent-first"},
        )

    def test_round_trip_is_canonical_and_stable(self) -> None:
        envelope = self._envelope()
        raw = envelope.to_dict()
        restored = ExecutionEnvelope.from_dict(raw)

        self.assertEqual(restored.to_dict(), raw)
        self.assertEqual(restored.digest, envelope.digest)
        self.assertEqual(restored.canonical_bytes(), envelope.canonical_bytes())

    def test_duplicate_evidence_is_rejected(self) -> None:
        envelope = ExecutionEnvelope(
            intent=ExecutionIntent(task_id="task-1", goal="test"),
            repository=RepositoryReference(digest="repo"),
            plan=ExecutionPlanRef(plan_id="plan", task_ids=("task-1",)),
            evidence=(EvidenceReference("ev"), EvidenceReference("ev")),
        )
        with self.assertRaisesRegex(ValueError, "duplicate evidence id"):
            envelope.validate()

    def test_plan_identity_must_contain_task(self) -> None:
        envelope = ExecutionEnvelope(
            intent=ExecutionIntent(task_id="task-1", goal="test"),
            repository=RepositoryReference(digest="repo"),
            plan=ExecutionPlanRef(plan_id="plan", task_ids=("task-2",)),
        )
        with self.assertRaisesRegex(ValueError, "plan/task identity mismatch"):
            envelope.validate()

    def test_schema_matches_serialized_shape(self) -> None:
        schema = json.loads((ROOT / "state" / "execution-envelope.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        envelope_keys = set(self._envelope().to_dict())
        self.assertEqual(envelope_keys, set(schema["required"]))
        self.assertEqual(
            schema["properties"]["repository"]["properties"]["model"]["const"],
            "portable.agency_codebase_context.CodebaseIndex",
        )


if __name__ == "__main__":
    unittest.main()
