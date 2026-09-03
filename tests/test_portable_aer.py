from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from portable.aer import build, verify_bundle, install


class PortableAerTests(unittest.TestCase):
    def make_source(self, root: Path) -> None:
        (root / ".ai-harness" / "runtime").mkdir(parents=True)
        (root / "skills" / "ai-coding-orchestrator").mkdir(parents=True)
        (root / ".ai-harness" / "config.toml").write_text('[harness]\nversion = 20\n', encoding="utf-8")
        (root / ".ai-harness" / "runtime" / "engine.py").write_text("print('ok')\n", encoding="utf-8")
        (root / ".ai-harness" / "telemetry.jsonl").write_text("machine-state\n", encoding="utf-8")
        (root / "skills" / "ai-coding-orchestrator" / "SKILL.md").write_text("---\nname: ai-coding-orchestrator\n---\n", encoding="utf-8")
        (root / "aer.py").write_text("print('launcher')\n", encoding="utf-8")

    def test_build_verify_and_exclude_mutable_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_source(root)
            bundle = Path(tmp) / "aer.zip"
            build(root, bundle)
            manifest = verify_bundle(bundle)
            self.assertEqual(manifest["harness_version"], 20)
            self.assertTrue(any(item["path"] == ".ai-harness/runtime/engine.py" for item in manifest["files"]))
            self.assertFalse(any(item["path"].endswith("telemetry.jsonl") for item in manifest["files"]))
            with zipfile.ZipFile(bundle) as archive:
                self.assertIn("aer.py", archive.namelist())

    def test_install_creates_target_harness_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            target = Path(tmp) / "target"
            self.make_source(root)
            bundle = Path(tmp) / "aer.zip"
            build(root, bundle)
            install(bundle, target, "none")
            self.assertTrue((target / ".ai-harness" / "runtime" / "engine.py").is_file())
            self.assertTrue((target / ".ai-harness" / "config.toml").is_file())
            self.assertFalse((target / ".ai-harness" / "telemetry.jsonl").exists())

    def test_install_backs_up_existing_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            target = Path(tmp) / "target"
            self.make_source(root)
            (target / ".ai-harness").mkdir(parents=True)
            (target / ".ai-harness" / "legacy.txt").write_text("preserve me", encoding="utf-8")
            bundle = Path(tmp) / "aer.zip"
            build(root, bundle)
            install(bundle, target, "none")
            backups = list(target.glob(".ai-harness.aer-backup*"))
            self.assertTrue(backups)
            self.assertEqual((backups[0] / "legacy.txt").read_text(encoding="utf-8"), "preserve me")


if __name__ == "__main__":
    unittest.main()
