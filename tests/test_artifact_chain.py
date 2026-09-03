#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness"))
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))
from runtime.artifact_chain import build_artifacts


class ArtifactChainTests(unittest.TestCase):
    def test_builds_intent_spec_plan_with_same_intent_digest(self):
        contract = {
            "goal": "Add an audited API endpoint",
            "intent_digest": "abc123",
            "requirements": ["Return the requested resource"],
            "acceptance": ["API tests pass"],
            "constraints": ["Preserve authentication"],
            "protected_behavior": ["Do not weaken authorization"],
            "boundaries": ["API module only"],
            "non_goals": ["No unrelated refactor"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = build_artifacts(Path(tmp), contract, route={"mode": "implement"})
            self.assertEqual(result["intent_digest"], "abc123")
            for name in ("intent.md", "spec.md", "plan.md", "artifact-chain.json"):
                self.assertTrue((Path(tmp) / name).is_file())
            intent = (Path(tmp) / "intent.md").read_text(encoding="utf-8")
            spec = (Path(tmp) / "spec.md").read_text(encoding="utf-8")
            plan = (Path(tmp) / "plan.md").read_text(encoding="utf-8")
            self.assertIn("abc123", intent)
            self.assertIn("Add an audited API endpoint", spec)
            self.assertIn("Do not expand", plan)

    def test_artifact_manifest_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_artifacts(Path(tmp), {"goal": "Fix X", "intent_digest": "digest"}, route={})
            saved = json.loads((Path(tmp) / "artifact-chain.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, result)
            self.assertEqual(set(saved["artifacts"]), {"intent.md", "spec.md", "plan.md"})


if __name__ == "__main__":
    unittest.main()
