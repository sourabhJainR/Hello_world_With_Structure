import tempfile
import unittest
from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex, retrieve


class GraphAwareRetrievalTests(unittest.TestCase):
    def test_expands_callee_caller_interface_test_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "service.py").write_text("from repo import Repo\n\nclass Service:\n    def run(self):\n        return Repo().save()\n", encoding="utf-8")
            (root / "repo.py").write_text("class Repo:\n    def save(self):\n        return True\n", encoding="utf-8")
            (root / "test_service.py").write_text("from service import Service\n\ndef test_run():\n    return Service().run()\n", encoding="utf-8")
            (root / "config.json").write_text('{"service": "service", "repo": "repo"}', encoding="utf-8")
            index = CodebaseIndex.build(root)
            context = retrieve(index, "Service run", max_files=6, token_budget=500, graph_hops=2)
            paths = set(context.relevant_paths)
            self.assertIn("service.py", paths)
            self.assertIn("repo.py", paths)
            self.assertTrue(any(e.kind == "calls" for e in index.edges))
            self.assertTrue(any(e.kind == "tests" for e in index.edges))
            self.assertTrue(any(e.kind == "configures" for e in index.edges))
            self.assertTrue(context.graph_trace.seed_paths)
            self.assertTrue(context.graph_trace.edges)

    def test_hop_budget_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("from b import B\nclass A:\n    def run(self):\n        return B().run()\n", encoding="utf-8")
            (root / "b.py").write_text("class B:\n    def run(self):\n        return 1\n", encoding="utf-8")
            context = retrieve(CodebaseIndex.build(root), "A run", graph_hops=1)
            self.assertTrue(any("hop_budget_exhausted" in x for x in context.unknowns))


if __name__ == "__main__":
    unittest.main()
