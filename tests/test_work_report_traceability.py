from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


work_report = load("work_report", ROOT / ".ai-harness/runtime/work_report.py")
traceability = load("work_report_traceability", ROOT / ".ai-harness/runtime/work_report_traceability.py")


class WorkReportTraceabilityTests(unittest.TestCase):
    def test_verified_finding_becomes_historical_input_and_report_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = work_report.WorkReport(
                work_id="bug-a",
                title="Bug A",
                status="completed",
                findings=[{"finding": "candidate execution side effect", "component": "orchestration", "failure_signature": "side-effect", "invariant": "candidate-not-executed", "test_pointer": "tests/test_x.py"}],
            )
            report_path = work_report.WorkReportGenerator(root).write(report)
            trace = traceability.integrate_work_report(
                root, report=report,
                manifest={"status": "completed", "validation": {"passed": True}, "findings": report.findings},
                work_type="bug",
            )
            self.assertEqual(len(trace["new_verified_regression_ids"]), 1)
            self.assertTrue(trace["new_verified_regression_ids"][0])
            self.assertTrue(trace["historical_regression_ids"] == [] or trace["historical_regression_ids"])
            html = report_path.read_text(encoding="utf-8")
            self.assertIn("Learning and regression traceability", html)
            self.assertTrue((root / ".ai-harness/reports/traceability/bug-a.json").is_file())
            self.assertTrue((root / ".ai-harness/reports/planning-context.json").is_file())

    def test_unverified_finding_stays_pending_and_cannot_enter_active_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = work_report.WorkReport(work_id="failed", title="Failed", status="failed", findings=[{"finding": "unverified issue", "test_pointer": "tests/test_x.py"}])
            work_report.WorkReportGenerator(root).write(report)
            trace = traceability.integrate_work_report(root, report=report, manifest={"status": "failed", "validation": {"passed": False}, "findings": report.findings}, work_type="bug")
            self.assertEqual(trace["new_verified_regression_ids"], [])
            self.assertEqual(len(trace["new_pending_regression_ids"]), 1)


if __name__ == "__main__":
    unittest.main()
