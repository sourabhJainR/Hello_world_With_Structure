import tempfile
import unittest
from pathlib import Path

from portable.ai_coding_agency_bridge import CodingTask, run_coding_task


class CodingCodebaseContextTests(unittest.TestCase):
    def test_worker_receives_minimal_evidence_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "planner.py").write_text(
                "class Planner:\n    def build_plan(self):\n        return 'ok'\n", encoding="utf-8"
            )

            def worker(profile, _assignments):
                context = profile.context
                self.assertIsNotNone(context)
                self.assertIn("planner.py", context.relevant_paths)
                self.assertLessEqual(context.token_estimate, 80)
                return {
                    "deliverables": ["planner change"],
                    "verification": ["context inspected"],
                    "dimensions": {
                        "correctness": 25,
                        "completeness": 15,
                        "evidence": 15,
                        "verification": 15,
                        "scope_discipline": 10,
                        "security_and_safety": 10,
                        "clarity": 5,
                        "maintainability": 5,
                    },
                    "hard_gates": {"tests": True, "evidence": True},
                    "evidence": [
                        {
                            "source": "planner.py",
                            "claim": "Planner.build_plan is defined in planner.py",
                            "locator": "planner.py:1-3",
                        }
                    ],
                }

            run = run_coding_task(
                CodingTask("ctx-1", "Find Planner build_plan", workspace_root=str(root), context_token_budget=80),
                worker,
            )
            self.assertIsNotNone(run.codebase_context)
            self.assertTrue(any("codebase-context-selected" in r.event for r in run.provenance.records))


if __name__ == "__main__":
    unittest.main()
