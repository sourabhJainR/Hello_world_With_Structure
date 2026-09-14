from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from portable.agency_release_lifecycle import ArtifactStore
from portable.context_bound_release import bind_release_context


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".ai-harness" / "runtime"
sys.path.insert(0, str(RUNTIME))


def _load_runtime_module(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    assert module and spec.loader
    spec.loader.exec_module(module)
    return module


class ContextEvidenceLifecycleTests(unittest.TestCase):
    def test_context_acquisition_returns_stable_evidence_envelope(self) -> None:
        module = _load_runtime_module("context_pipeline")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "service.py").write_text(
                "class Base: pass\nclass Service(Base):\n    def handle(self):\n        return True\n",
                encoding="utf-8",
            )
            evidence = module.ContextAcquisitionPipeline(root).acquire(
                task_id="T-1", query="Service handle", phase="implement",
                intent_digest="intent-123", risk="medium", uncertainty="high",
            )
            self.assertEqual(evidence.intent_digest, "intent-123")
            self.assertTrue(evidence.evidence_digest)
            self.assertTrue(evidence.repository_snapshot_digest)
            self.assertTrue(evidence.items)
            self.assertIn("service.py::Service", evidence.symbol_refs)
            self.assertEqual(evidence.deployment_binding()["evidence_digest"], evidence.evidence_digest)

    def test_verification_receipt_is_bound_to_artifact_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "artifact.txt"
            source.write_text("v1", encoding="utf-8")
            store = ArtifactStore(root / "release")
            ref = store.stage(source, "artifact-v1")
            release = bind_release_context(root / "release", SimpleNamespace(evidence_digest="evidence-abc"))

            receipt = release.verify(ref, {"unit_tests": True, "policy_check": True})
            self.assertEqual(receipt.artifact_digest, ref.digest)
            self.assertEqual(receipt.context_evidence_digest, "evidence-abc")
            self.assertTrue(receipt.verification_digest)

            promoted = release.promote(ref, verification=receipt)
            self.assertEqual(promoted.context_evidence_digest, "evidence-abc")
            self.assertEqual(promoted.verification_digest, receipt.verification_digest)

            with self.assertRaises(ValueError):
                release.verify(ref, {"unit_tests": False})

    def test_same_evidence_digest_reaches_shadow_canary_promote_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "artifact.txt"
            source.write_text("v1", encoding="utf-8")
            store = ArtifactStore(root / "release")
            ref = store.stage(source, "artifact-v1")
            release = bind_release_context(root / "release", SimpleNamespace(evidence_digest="evidence-abc"))

            shadow = release.shadow(ref)
            canary = release.canary(ref)
            promoted = release.promote(ref, verification_digest="verification-123")
            rollback = release.rollback(reason="canary observation failed", verification_digest="verification-456")

            for state in (shadow, canary, promoted, rollback):
                self.assertEqual(state.context_evidence_digest, "evidence-abc")
            self.assertEqual(promoted.verification_digest, "verification-123")
            self.assertEqual(rollback.verification_digest, "verification-456")

            history = [line for line in store.history.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(history), 4)
            self.assertTrue(all('"context_evidence_digest": "evidence-abc"' in line for line in history))
            self.assertIn('"verification_digest": "verification-123"', history[2])


if __name__ == "__main__":
    unittest.main()
