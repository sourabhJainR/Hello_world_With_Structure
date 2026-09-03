from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from portable.aer import build, check_update, install, rollback, verify_bundle


class PortableAerTests(unittest.TestCase):
    def make_source(self, root: Path, version: str = "20.1.0") -> None:
        (root / ".ai-harness" / "runtime").mkdir(parents=True)
        (root / ".claude-plugin").mkdir(parents=True)
        (root / "skills" / "ai-coding-orchestrator").mkdir(parents=True)
        (root / "portable").mkdir(parents=True)
        (root / ".ai-harness" / "config.toml").write_text('[harness]\nversion = 20\n', encoding="utf-8")
        (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": version}), encoding="utf-8")
        (root / ".ai-harness" / "runtime" / "engine.py").write_text("print('ok')\n", encoding="utf-8")
        (root / ".ai-harness" / "telemetry.jsonl").write_text("machine-state\n", encoding="utf-8")
        (root / "skills" / "ai-coding-orchestrator" / "SKILL.md").write_text("---\nname: ai-coding-orchestrator\n---\n", encoding="utf-8")
        (root / "portable" / "aer.py").write_text("print('portable')\n", encoding="utf-8")
        (root / "aer.py").write_text("print('launcher')\n", encoding="utf-8")

    def test_build_verify_and_exclude_mutable_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_source(root)
            bundle = Path(tmp) / "aer.zip"
            build(root, bundle, source_commit="test-commit")
            manifest = verify_bundle(bundle)
            self.assertEqual(manifest["version"], "20.1.0")
            self.assertEqual(manifest["source_commit"], "test-commit")
            self.assertFalse(any(item["path"].endswith("telemetry.jsonl") for item in manifest["files"]))
            self.assertFalse(manifest["target_repository_mutation"])
            with zipfile.ZipFile(bundle) as archive:
                self.assertIn("aer.py", archive.namelist())
                self.assertIn("payload/portable/aer.py", archive.namelist())

    def test_install_is_repository_isolated_and_version_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            target = Path(tmp) / "target"
            aer_home = Path(tmp) / "aer-home"
            self.make_source(root)
            target.mkdir()
            (target / "README.md").write_text("user repository", encoding="utf-8")
            before = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            bundle = Path(tmp) / "aer.zip"
            build(root, bundle, source_commit="commit-20.1.0")
            install(bundle, "none", aer_home)
            after = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertFalse((target / ".ai-harness").exists())
            record = json.loads((aer_home / "current" / "install.json").read_text(encoding="utf-8"))
            self.assertEqual(record["version"], "20.1.0")
            self.assertEqual(record["source_commit"], "commit-20.1.0")
            self.assertTrue(record["repository_isolated"])

    def test_install_rejects_same_version_with_different_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            aer_home = Path(tmp) / "aer-home"
            self.make_source(root)
            first = Path(tmp) / "first.zip"
            second = Path(tmp) / "second.zip"
            build(root, first, source_commit="commit-a")
            install(first, "none", aer_home)
            build(root, second, source_commit="commit-b")
            with self.assertRaises(SystemExit):
                install(second, "none", aer_home)

    def test_rollback_selects_previous_immutable_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            aer_home = Path(tmp) / "aer-home"
            self.make_source(root, "20.1.0")
            first = Path(tmp) / "first.zip"
            build(root, first, source_commit="commit-a")
            install(first, "none", aer_home)
            self.make_source(root, "20.2.0")
            second = Path(tmp) / "second.zip"
            build(root, second, source_commit="commit-b")
            install(second, "none", aer_home)
            rollback(aer_home)
            active = json.loads((aer_home / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(active["version"], "20.1.0")
            self.assertEqual(active["source_commit"], "commit-a")

    def test_check_update_uses_exact_remote_commit_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aer_home = Path(tmp) / "aer-home"
            aer_home.mkdir()
            (aer_home / "active.json").write_text(json.dumps({"version": "20.9.0", "source_commit": "old"}), encoding="utf-8")
            with patch("portable.aer._remote_target", return_value=("20.10.0", "new")):
                status = check_update(aer_home)
            self.assertTrue(status["update_available"])
            self.assertEqual(status["latest_version"], "20.10.0")
            self.assertEqual(status["latest_commit"], "new")

    def test_same_semver_different_commit_is_not_an_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aer_home = Path(tmp) / "aer-home"
            aer_home.mkdir()
            (aer_home / "active.json").write_text(json.dumps({"version": "20.10.0", "source_commit": "old"}), encoding="utf-8")
            with patch("portable.aer._remote_target", return_value=("20.10.0", "new")):
                status = check_update(aer_home)
            self.assertFalse(status["update_available"])


if __name__ == "__main__":
    unittest.main()
