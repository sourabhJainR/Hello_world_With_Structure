import tempfile
import unittest
from pathlib import Path

from portable.agency_artifact_regression import compare_artifacts, fingerprint_paths


class ArtifactRegressionTests(unittest.TestCase):
    def _files(self, tmp: str, values: dict[str, str]):
        paths = []
        for name, value in values.items():
            path = Path(tmp) / name
            path.write_text(value, encoding="utf-8")
            paths.append(path)
        return fingerprint_paths(paths)

    def test_identical_snapshots_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline = {s.path: s for s in self._files(tmp, {"a.txt": "one"})}
            current = {s.path: s for s in self._files(tmp, {"a.txt": "one"})}
            self.assertTrue(compare_artifacts(baseline, current).passed)

    def test_changed_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text("one", encoding="utf-8")
            before = fingerprint_paths([path])[0]
            path.write_text("two", encoding="utf-8")
            after = fingerprint_paths([path])[0]
            decision = compare_artifacts({"a.txt": before}, {"a.txt": after})
            self.assertFalse(decision.passed)
            self.assertEqual(decision.findings[0].kind, "changed")

    def test_unexpected_addition_and_removal_fail(self):
        baseline = {"a": type("S", (), {"path": "a", "digest": "1", "size": 1})()}
        current = {"b": type("S", (), {"path": "b", "digest": "2", "size": 1})()}
        decision = compare_artifacts(baseline, current)
        self.assertEqual({f.kind for f in decision.findings}, {"added", "removed"})

    def test_allowed_change_is_ignored(self):
        baseline = {"generated": type("S", (), {"path": "generated", "digest": "1", "size": 1})()}
        current = {"generated": type("S", (), {"path": "generated", "digest": "2", "size": 2})()}
        self.assertTrue(compare_artifacts(baseline, current, allowed_changes=["generated"]).passed)


if __name__ == "__main__":
    unittest.main()
