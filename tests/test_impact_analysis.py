from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from portable.impact_analysis import analyze


class ImpactAnalysisTests(unittest.TestCase):
    def test_shared_consumer_is_flagged_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "common").mkdir()
            (root / "common" / "types.py").write_text("class Contract: pass\n", encoding="utf-8")
            (root / "a.py").write_text("from common.types import Contract\n", encoding="utf-8")
            (root / "b.py").write_text("from common.types import Contract\n", encoding="utf-8")
            report = analyze(root, ["common/types.py"])
            self.assertTrue(report.review_required)
            records = {item.path: item for item in report.impacted}
            self.assertTrue(records["common/types.py"].shared)
            self.assertIn("a.py", records["common/types.py"].inbound_references)
            self.assertIn("b.py", records["common/types.py"].inbound_references)

    def test_unrelated_file_does_not_expand_impact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "b.py").write_text("y = 2\n", encoding="utf-8")
            report = analyze(root, ["a.py"])
            self.assertEqual([item.path for item in report.impacted], ["a.py"])

    def test_same_filename_in_another_directory_is_not_a_false_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one").mkdir()
            (root / "two").mkdir()
            (root / "one" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "two" / "service.py").write_text("VALUE = 2\n", encoding="utf-8")
            (root / "consumer.py").write_text("from one.service import VALUE\n", encoding="utf-8")
            report = analyze(root, ["one/service.py"])
            records = {item.path: item for item in report.impacted}
            self.assertIn("consumer.py", records["one/service.py"].inbound_references)
            self.assertNotIn("consumer.py", records["two/service.py"].inbound_references)
            self.assertNotIn("two/service.py", records)

    def test_package_import_resolves_to_imported_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("\n", encoding="utf-8")
            (root / "pkg" / "worker.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "consumer.py").write_text("from pkg import worker\nworker.VALUE\n", encoding="utf-8")
            report = analyze(root, ["pkg/worker.py"])
            records = {item.path: item for item in report.impacted}
            self.assertIn("consumer.py", records["pkg/worker.py"].inbound_references)


if __name__ == "__main__":
    unittest.main()
