import tempfile
import unittest
from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex, ContextReuseKey, retrieve


class ContextControlTests(unittest.TestCase):
    def test_reuse_key_is_snapshot_and_recipe_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("def target():\n    return 1\n", encoding="utf-8")
            index = CodebaseIndex.build(root)
            context = retrieve(index, "target", token_budget=20, max_files=2, context_lines=10, graph_hops=1)
            key = context.reuse_key(token_budget=20, max_files=2, context_lines=10, graph_hops=1)
            self.assertEqual(context.retrieval_fingerprint, key.digest())
            self.assertEqual(context.snapshot_digest, index.digest())
            self.assertEqual(context.context_version, "1")

    def test_hidden_project_configuration_can_be_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hidden = root / ".ai-harness"
            hidden.mkdir()
            (hidden / "policy.md").write_text("runtime policy", encoding="utf-8")
            index = CodebaseIndex.build(root)
            self.assertIn(".ai-harness/policy.md", index.files)

    def test_reuse_key_rejects_invalid_recipe(self) -> None:
        with self.assertRaises(ValueError):
            ContextReuseKey("snapshot", "query", 0, 1, 1, 0)


if __name__ == "__main__":
    unittest.main()
