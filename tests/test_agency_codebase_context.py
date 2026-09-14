import tempfile
import unittest
from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex, retrieve


class CodebaseContextTests(unittest.TestCase):
    def test_ranks_symbol_and_limits_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "class Planner:\n    def build_plan(self):\n        return 'plan'\n\n" + "x = 1\n" * 20,
                encoding="utf-8",
            )
            (root / "noise.py").write_text("def unrelated():\n    return 1\n", encoding="utf-8")
            index = CodebaseIndex.build(root)
            context = retrieve(index, "Planner build_plan", token_budget=30, max_files=3)
            self.assertIn("app.py", context.relevant_paths)
            self.assertLessEqual(context.token_estimate, 30)
            self.assertEqual(context.snapshot_digest, index.digest())

    def test_explicit_unknowns_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("def known():\n    return 1\n", encoding="utf-8")
            context = retrieve(CodebaseIndex.build(root), "missing_symbol")
            self.assertTrue(context.unknowns)
            self.assertEqual(context.chunks, ())


if __name__ == "__main__":
    unittest.main()
