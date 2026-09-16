"""Regression tests for the single canonical repository model."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex
from portable.repository_intelligence import RepositoryIntelligence


class RepositoryModelConsolidationTests(unittest.TestCase):
    def test_hidden_repository_surfaces_are_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / ".ai-harness" / "example.py"
            marker.parent.mkdir()
            marker.write_text("def marker():\n    return 1\n", encoding="utf-8")

            index = CodebaseIndex.build(root)

            self.assertIn(".ai-harness/example.py", index.files)

    def test_ignore_file_is_part_of_canonical_index_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
            (root / "kept.py").write_text("def kept():\n    return 1\n", encoding="utf-8")
            (root / "ignored.py").write_text("def ignored():\n    return 2\n", encoding="utf-8")

            repo = RepositoryIntelligence.build(root)

            self.assertIn("kept.py", repo.files)
            self.assertNotIn("ignored.py", repo.files)
            self.assertEqual(repo.repository_model.ignore_patterns, ("ignored.py",))

    def test_facade_exposes_the_same_canonical_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")

            repo = RepositoryIntelligence.build(root)

            self.assertIs(repo.repository_model, repo.index)
            self.assertEqual(repo.repository_model.digest(), repo.digest())

    def test_pack_uses_canonical_index_not_a_second_filesystem_crawl(self) -> None:
        source = inspect.getsource(RepositoryIntelligence.pack)
        self.assertNotIn("os.walk", source)
        self.assertNotIn("os.scandir", source)
        self.assertIn("self.index.files", source)

    def test_pack_structure_matches_index_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai-harness").mkdir()
            (root / ".ai-harness" / "config.py").write_text("CONFIG = True\n", encoding="utf-8")
            (root / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")

            repo = RepositoryIntelligence.build(root)
            pack = repo.pack()

            self.assertEqual(pack.structure, tuple(sorted(repo.repository_model.files)))
            self.assertEqual(set(item.path for item in pack.files), set(repo.repository_model.files))


if __name__ == "__main__":
    unittest.main()
