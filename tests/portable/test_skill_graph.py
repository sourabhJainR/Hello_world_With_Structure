import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.skill_graph import SkillGraph, SkillNode


class SkillGraphTests(unittest.TestCase):
    def _graph(self, directory: str) -> SkillGraph:
        return SkillGraph(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")

    def test_skill_graph_tracks_prerequisites_and_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = self._graph(directory)
            graph.upsert(SkillNode("parse", "skill", frozenset(), frozenset({"e1"}), frozenset({"parse_error"}), frozenset(), True))
            graph.upsert(SkillNode("recover", "skill", frozenset({"parse"}), frozenset({"e2"}), frozenset({"bad_retry"}), frozenset(), False))
            self.assertTrue(graph.ready("parse"))
            self.assertFalse(graph.ready("recover"))
            self.assertEqual(graph.missing_prerequisites("recover"), ("parse",))
            self.assertEqual(graph.ancestors("recover"), ("parse",))

    def test_readiness_requires_all_transitive_prerequisites(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = self._graph(directory)
            graph.upsert(SkillNode("root", evidence_ids=frozenset({"e1"}), validated=True))
            graph.upsert(SkillNode("middle", prerequisites=frozenset({"root"}), evidence_ids=frozenset({"e2"}), validated=False))
            graph.upsert(SkillNode("leaf", prerequisites=frozenset({"middle"}), evidence_ids=frozenset({"e3"}), validated=True))
            self.assertFalse(graph.ready("leaf"))
            graph.upsert(SkillNode("middle", prerequisites=frozenset({"root"}), evidence_ids=frozenset({"e2"}), validated=True))
            self.assertTrue(graph.ready("leaf"))

    def test_skill_graph_rejects_dependency_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = self._graph(directory)
            graph.upsert(SkillNode("a"))
            graph.upsert(SkillNode("b"))
            graph.add_dependency("b", "a")
            with self.assertRaises(ValueError):
                graph.add_dependency("a", "b")
            self.assertEqual(graph.ancestors("b"), ("a",))

    def test_skill_graph_rejects_unknown_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = self._graph(directory)
            with self.assertRaises(KeyError):
                graph.upsert(SkillNode("recover", prerequisites=frozenset({"parse"})))
            self.assertFalse(graph.ready("recover"))

    def test_unknown_skill_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = self._graph(directory)
            self.assertFalse(graph.ready("missing"))
            self.assertEqual(graph.missing_prerequisites("missing"), ())


if __name__ == "__main__":
    unittest.main()
