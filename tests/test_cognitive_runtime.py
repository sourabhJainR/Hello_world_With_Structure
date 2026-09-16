import tempfile
import unittest
from pathlib import Path

from portable.adaptive_runtime import AdaptiveRuntime
from portable.context_graph import ContextNode
from portable.persistent_memory import PersistentMemory
from portable.session_state import SessionStore
from portable.orchestration import Node, NodeKind


class CognitiveRuntimeTests(unittest.TestCase):
    def test_cognition_shares_canonical_memory_and_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            runtime = AdaptiveRuntime(Node("root", NodeKind.TASK, lambda ctx: "ok"),
                                      persistent_memory=memory, session_store=SessionStore())
            cognition = runtime.cognition(root)
            cognition.graph.upsert_node(ContextNode("service", "entity", "service", "test"))
            cognition.world.observe(__import__("portable.world_model", fromlist=["Observation"]).Observation("o1", "service", "status", "healthy", "test"))
            cognition.hypotheses.propose(__import__("portable.hypothesis_engine", fromlist=["Hypothesis"]).Hypothesis("h1", "why", "service is healthy", "test"))
            self.assertEqual(cognition.world.current("service", "status")[0].value, "healthy")
            self.assertIsNotNone(cognition.graph.get_node("service"))
            self.assertEqual(cognition.project, runtime.session_store.project_key(root))


if __name__ == "__main__":
    unittest.main()
