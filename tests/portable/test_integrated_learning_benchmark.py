import tempfile
import unittest
from pathlib import Path

from portable.adaptive_learning import AdaptiveLearningStore
from portable.adaptive_runtime import AdaptiveRuntime
from portable.empirical_improvement import ImprovementObservation
from portable.orchestration import Graph, Node, NodeKind
from portable.persistent_memory import PersistentMemory
from portable.session_state import SessionStore


class IntegratedLearningBenchmarkTests(unittest.TestCase):
    @staticmethod
    def _runtime(root: Path) -> AdaptiveRuntime:
        node = Node("worker", NodeKind.DETERMINISTIC, lambda _context: "ok", evaluator=lambda value: value == "ok")
        memory = PersistentMemory(root / "memory.db", require_approval=False)
        return AdaptiveRuntime(Graph([node]), session_store=SessionStore(root / "sessions"), persistent_memory=memory)

    def test_run_defers_learning_until_maintenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self._runtime(root)
            result = runtime.run(
                session_id="s1", task_id="t1", project_root=root, intent="repair parser",
                enrich_cognition=False, learning_context="concise", learning_evidence=("ev1",),
            )
            self.assertEqual(result.status.value, "accepted")
            store = AdaptiveLearningStore(runtime.persistent_memory, runtime.session_store.project_key(root))
            self.assertEqual(len(store.pending()), 1)
            self.assertEqual(store.profile().observations, 0)
            processed = runtime.process_learning(root)
            self.assertEqual(len(processed), 1)
            self.assertEqual(store.profile().observations, 1)
            self.assertEqual(store.pending(), ())

    def test_workstyle_guidance_is_available_to_worker_before_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            project = SessionStore.project_key(root)
            store = AdaptiveLearningStore(memory, project)
            store.record_outcome(task_id="old", intent="old", status="accepted", quality=1.0, iterations=1, context="concise")
            store.process()
            guidance = store.guidance()
            self.assertEqual(guidance["preferred_detail"], "concise")
            self.assertGreater(guidance["confidence"], 0)

    def test_benchmark_api_does_not_change_active_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self._runtime(root)
            cases = ["c1", "c2"]

            def evaluator(case, strategy):
                if strategy == "baseline":
                    return ImprovementObservation(case, strategy, 0.8, 2, 0.8, (f"{case}-b",))
                return ImprovementObservation(case, strategy, 0.95, 1, 0.9, (f"{case}-c",))

            report = runtime.benchmark_improvement(root, cases, "baseline", "candidate", evaluator)
            self.assertTrue(report.accepted)
            self.assertEqual(runtime.last_deferred_learning_job, None)


if __name__ == "__main__":
    unittest.main()
