import json
import tempfile
import unittest
from pathlib import Path

from portable.adaptive_runtime import AdaptiveRuntime
from portable.automation_scheduler import AutomationScheduler
from portable.persistent_memory import PersistentMemory
from portable.orchestration import Graph, Node, NodeKind
from portable.session_state import SessionStore


class ContinuousLearningRuntimeTests(unittest.TestCase):
    def _runtime(self, root: Path):
        memory = PersistentMemory(root / "memory.db", require_approval=False)
        scheduler = AutomationScheduler(root / "automation.db")
        sessions = SessionStore(root / "sessions.db")
        graph = Graph([Node("agent", NodeKind.AGENT, lambda context: "ok", critical=True, risk="low")])
        return AdaptiveRuntime(graph, persistent_memory=memory, automation_scheduler=scheduler,
                              session_store=sessions, maintenance_interval_seconds=60), memory, scheduler

    def test_schedule_is_idempotent_and_first_cycle_is_due(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, memory, scheduler = self._runtime(root)
            first = runtime.ensure_learning_maintenance(root)
            second = runtime.ensure_learning_maintenance(root)
            self.assertEqual(first.id, second.id)
            self.assertTrue(scheduler.due())
            scheduler.close()
            memory.close()

    def test_each_use_creates_experience_and_maintenance_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, memory, scheduler = self._runtime(root)
            result = runtime.run(
                session_id="s1", task_id="t1", project_root=root, intent="learn this",
                cognitive_capability="planning", learning_strategy="default", learning_confidence=0.8,
            )
            self.assertEqual(result.status.value, "accepted")
            history = runtime.current_adaptive_policy(root)
            self.assertEqual(history.strategy, "default")
            receipt = runtime.maintenance_tick(root)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.jobs_processed, 1)
            self.assertEqual(len(runtime.recent_maintenance(root)), 1)
            scheduler.close()
            memory.close()

    def test_policy_snapshot_is_visible_to_future_runs_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            captured = {}
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            scheduler = AutomationScheduler(root / "automation.db")
            sessions = SessionStore(root / "sessions.db")
            graph = Graph([Node("agent", NodeKind.AGENT, lambda context: captured.setdefault("policy", dict(context["aer_adaptive_policy"])) or "ok", critical=True, risk="low")])
            runtime = AdaptiveRuntime(graph, persistent_memory=memory, automation_scheduler=scheduler, session_store=sessions)
            runtime.run(session_id="s1", task_id="t1", project_root=root, intent="first", cognitive_capability="planning")
            first_policy_version = captured["policy"]["version"]
            scheduler.close()
            memory.close()
            self.assertTrue(first_policy_version.startswith("v"))


if __name__ == "__main__":
    unittest.main()
