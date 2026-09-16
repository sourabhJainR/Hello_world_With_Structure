import tempfile
import unittest
from pathlib import Path

from portable.adaptive_runtime import AdaptiveRuntime
from portable.context_graph import ContextNode
from portable.persistent_memory import PersistentMemory
from portable.session_state import SessionStore
from portable.orchestration import Graph, Node, NodeKind
from portable.world_model import Observation
from portable.hypothesis_engine import Hypothesis


class CognitiveRuntimeTests(unittest.TestCase):
    def test_cognition_shares_canonical_memory_and_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            runtime = AdaptiveRuntime(Graph([Node("agent", NodeKind.AGENT, lambda context: "ok")]),
                                      persistent_memory=memory, session_store=SessionStore(root / "sessions.db"))
            cognition = runtime.cognition(root)
            cognition.graph.upsert_node(ContextNode("service", "entity", "service", "test"))
            cognition.world.observe(Observation("o1", "service", "status", "healthy", "test"))
            cognition.hypotheses.propose(Hypothesis("h1", "why", "service is healthy", "test"))
            self.assertEqual(cognition.world.current("service", "status")[0].value, "healthy")
            self.assertIsNotNone(cognition.graph.get_node("service"))
            self.assertEqual(cognition.project, runtime.session_store.project_key(root))


if __name__ == "__main__":
    unittest.main()
