import os
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".ai-harness" / "runtime"
HARNESS = ROOT / ".ai-harness"
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(RUNTIME))

from agent_turn import AgentTurnStateMachine
from canary_evaluator import evaluate_canary, evaluate_shadow
from context_planner import EvidenceCandidate, plan_context, select_evidence
from learning_controller import LearningController
from learning_engine import Observation
from policy_registry import Policy, PolicyRegistry
from regression_replay import ReplayCase
from rollback_controller import PolicyHealth
from second_brain import create_memory, load_local_memory, persist_memory, validate_memory
from security_gate import SecurityGateError, safe_environment, validate_prompt_file, validate_provider_command


class RuntimePathTests(unittest.TestCase):
    def test_context_path_is_bounded_and_risk_aware(self):
        plan = plan_context(phase="review", risk="high", uncertainty="unknown", policy_strategy="structural_first")
        self.assertIn("security", plan.retrieval_modes)
        self.assertIn("history", plan.retrieval_modes)
        selected = select_evidence([
            EvidenceCandidate("a", "structural", "A", relevance=.9, confidence=.9, freshness=1, cost=4),
            EvidenceCandidate("a", "duplicate", "A2", relevance=1, confidence=1, freshness=1, cost=1),
            EvidenceCandidate("b", "history", "B", relevance=.7, confidence=.8, freshness=.8, cost=4),
        ], budget=5, max_items=10)
        self.assertEqual([x.evidence_id for x in selected], ["a"])

    def test_agent_turn_full_lifecycle_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            turn = AgentTurnStateMachine("execute", Path(tmp), "turn-1")
            turn.transition("planning")
            turn.transition("acting")
            turn.set_context(["repo-map", "contract"], "ctx-1")
            turn.observe_tool({"sequence": 1, "tool": "read", "status": "completed", "result": "ok"})
            turn.observe_usage("prompt", "output")
            decision = turn.decide_live(event="tool_result", max_tool_calls=10)
            self.assertEqual(decision["action"], "continue")
            turn.transition("deciding")
            turn.finish("completed")
            self.assertEqual(turn.snapshot()["state"], "completed")
            self.assertGreater(turn.snapshot()["usage"]["total_tokens"], 0)

    def test_learning_replay_shadow_canary_promotion_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = PolicyRegistry([Policy("old", 1, "bug", "history_first", "active", .90, promoted_at=1)])
            controller = LearningController(Path(tmp), registry=registry)
            observations = [Observation(str(i), "bug", "targeted_context", True, True, True) for i in range(3)]
            candidate = controller.learn_candidates(observations, min_samples=3)[0]
            cases = [ReplayCase("r1", "bug", True), ReplayCase("r2", "bug", False)]
            replay_result = controller.replay_candidate(candidate, cases, lambda case, _candidate: (case.expected_success, case.expected_verification))
            self.assertTrue(replay_result.passed)
            runner = lambda case, _candidate: (case.expected_success, case.expected_verification)
            shadow = evaluate_shadow(candidate, cases, runner)
            self.assertEqual(shadow.pass_rate, 1.0)
            canary = evaluate_canary(candidate, cases, runner)
            self.assertTrue(canary.gate_passed)
            promoted = controller.promote(candidate, replay_result, canary_report=canary, version=2, now=2)
            self.assertIsNotNone(promoted)
            self.assertEqual(controller.active_strategy("bug"), "targeted_context")
            self.assertTrue(controller.monitor(PolicyHealth(candidate.policy_id, .95, .80, .02, .09), now=3))
            self.assertEqual(controller.active_strategy("bug"), "history_first")

    def test_canary_counts_expected_negative_cases_as_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = LearningController(Path(tmp))
            candidate = controller.learn_candidates([Observation(str(i), "guard", "safe", True, True, True) for i in range(3)])[0]
            cases = [ReplayCase("allow", "guard", True), ReplayCase("deny", "guard", False)]
            report = evaluate_canary(candidate, cases, lambda case, _candidate: (case.expected_success, case.expected_verification))
            self.assertTrue(report.gate_passed)
            self.assertEqual(report.pass_rate, 1.0)
            self.assertEqual(report.failures, ())

    def test_second_brain_persistence_requires_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.jsonl"
            memory = create_memory(kind="lesson", text="Keep validation deterministic", source="run-1", evidence_ids=["verify-1"], intent_digest="intent-1")
            self.assertEqual(validate_memory(memory, expected_intent_digest="intent-1"), [])
            persist_memory(path, memory)
            loaded = load_local_memory(path, query_terms={"validation"})
            self.assertEqual(loaded[0]["id"], memory["id"])
            with self.assertRaises(ValueError):
                persist_memory(path, create_memory(kind="lesson", text="No evidence", source="run-2"))

    def test_security_boundary_blocks_unsafe_commands_and_prompt_escape(self):
        for command in (
            ["claude", "-p", "--dangerously-skip-permissions"],
            ["codex", "exec", "--sandbox", "workspace-write"],
            ["gemini", "-p", "--approval-mode=auto"],
        ):
            with self.assertRaises(SecurityGateError):
                validate_provider_command(command)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = root / "prompt.md"
            prompt.write_text("safe", encoding="utf-8")
            self.assertEqual(validate_prompt_file(prompt, expected_root=root), prompt.resolve())
            outside = root.parent / "outside.md"
            outside.write_text("unsafe", encoding="utf-8")
            try:
                with self.assertRaises(SecurityGateError):
                    validate_prompt_file(outside, expected_root=root)
            finally:
                outside.unlink(missing_ok=True)
        old_secret = os.environ.get("TEST_PRIVATE_KEY")
        os.environ["TEST_PRIVATE_KEY"] = "must-not-cross-provider-boundary"
        try:
            self.assertNotIn("TEST_PRIVATE_KEY", safe_environment())
        finally:
            if old_secret is None:
                os.environ.pop("TEST_PRIVATE_KEY", None)
            else:
                os.environ["TEST_PRIVATE_KEY"] = old_secret


if __name__ == "__main__":
    unittest.main()
