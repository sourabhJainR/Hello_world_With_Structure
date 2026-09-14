from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from portable.agency_release_lifecycle import ArtifactStore
from portable.context_bound_release import bind_release_context
from portable.agency_codebase_context import CodebaseIndex


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".ai-harness" / "runtime"


def _load_runtime_module(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
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
                task_id="T-1",
                query="Service handle",
                phase="implement",
                intent_digest="intent-123",
                risk="medium",
                uncertainty="high",
            )
            self.assertEqual(evidence.intent_digest, "intent-123")
            self.assertTrue(evidence.evidence_digest)
            self.assertTrue(evidence.repository_snapshot_digest)
            self.assertTrue(evidence.items)
            self.assertIn("service.py::Service", evidence.symbol_refs)
            self.assertEqual(evidence.deployment_binding()["evidence_digest"], evidence.evidence_digest)

    def test_same_evidence_digest_reaches_shadow_canary_promote_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "artifact.txt"
            source.write_text("v1", encoding="utf-8")
            store = ArtifactStore(root / "release")
            ref = store.stage(source, "artifact-v1")
            evidence = SimpleNamespace(evidence_digest="evidence-abc")
            release = bind_release_context(root / "release", evidence)

            self.assertIn("context_evidence_digest=evidence-abc", release.shadow(ref).reason)
            self.assertIn("context_evidence_digest=evidence-abc", release.canary(ref).reason)
            self.assertIn("context_evidence_digest=evidence-abc", release.promote(ref).reason)
            rollback = release.rollback(reason="canary observation failed")
            self.assertIn("context_evidence_digest=evidence-abc", rollback.reason)


if __name__ == "__main__":
    unittest.main()
