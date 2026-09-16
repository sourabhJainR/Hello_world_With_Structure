import tempfile
import unittest
from pathlib import Path

from portable.causal_model import CausalLink, CausalModel
from portable.context_graph import ContextGraph, ContextNode
from portable.persistent_memory import PersistentMemory


class CausalModelTests(unittest.TestCase):
    def test_records_and_queries_causal_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            graph = ContextGraph(memory, "demo")
            graph.upsert_node(ContextNode("cpu", "metric", "CPU", "test"))
            graph.upsert_node(ContextNode("latency", "metric", "Latency", "test"))
            model = CausalModel(graph)
            link = CausalLink("cause-1", "cpu", "latency", "load increases queueing", "experiment", 0.8,
                              evidence=("obs-1",), interventions=("reduce-load",))
            edge = model.record(link)
            self.assertEqual(edge.relation, "causes")
            self.assertEqual(model.causes_of("latency")[0].source_id, "cpu")
            self.assertEqual(model.effects_of("cpu")[0].target_id, "latency")
            self.assertEqual(edge.properties["interventions"], ["reduce-load"])

    def test_rejects_self_causation_and_missing_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            graph = ContextGraph(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            model = CausalModel(graph)
            with self.assertRaises(ValueError):
                CausalLink("bad", "x", "x", "same", "test")
            with self.assertRaises(KeyError):
                model.record(CausalLink("bad", "x", "y", "missing", "test"))


if __name__ == "__main__":
    unittest.main()
