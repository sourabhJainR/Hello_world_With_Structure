import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".ai-harness/runtime/token_optimizer.py"
spec = importlib.util.spec_from_file_location("token_optimizer", MODULE)
optimizer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
# dataclasses and other runtime introspection expect dynamically loaded modules
# to be registered in sys.modules before execution.
sys.modules[spec.name] = optimizer
spec.loader.exec_module(optimizer)


class TokenOptimizerTests(unittest.TestCase):
    def test_relevance_budget_excludes_unrelated_large_context(self):
        sections = [
            "authentication login token refresh service",
            "unrelated historical document " + ("x " * 500),
            "token refresh integration tests and security policy",
        ]
        selected = optimizer.select_relevant_context("fix token refresh security", sections, 180)
        self.assertTrue(selected)
        self.assertLessEqual(sum(len(x.text) + 1 for x in selected), 180)
        self.assertTrue(any("token refresh" in x.text for x in selected))

    def test_mvm_routes_simple_tasks_low(self):
        decision = optimizer.choose_model_tier(task="rename typo in documentation")
        self.assertEqual(decision.tier, "low")

    def test_risk_escalates(self):
        decision = optimizer.choose_model_tier(task="small change", risk="critical")
        self.assertEqual(decision.tier, "high")

    def test_script_candidate_for_repeatable_work(self):
        self.assertTrue(optimizer.should_use_script("validate configuration", repeat_count=0))
        self.assertTrue(optimizer.should_use_script("inspect repository", repeat_count=2))
        self.assertFalse(optimizer.should_use_script("design architecture", repeat_count=0))

    def test_report_records_token_reduction(self):
        report = optimizer.optimize(
            "fix authentication token refresh",
            ["authentication token refresh implementation", "unrelated " + ("x" * 1000)],
            120,
        )
        self.assertLessEqual(report.selected_chars, 120)
        self.assertGreater(report.estimated_input_tokens, 0)
        self.assertLessEqual(report.compression_ratio, 1.0)


if __name__ == "__main__":
    unittest.main()
