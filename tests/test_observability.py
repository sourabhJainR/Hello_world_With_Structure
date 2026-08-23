import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / ".ai-harness"
sys.path.insert(0, str(HARNESS))

from observability import ConfigurationError, configure_logging, emit_event, exception_summary


class ObservabilityTests(unittest.TestCase):
    def test_local_logging_and_telemetry_are_standard_library_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            logger = configure_logging(run_dir, "INFO")
            logger.info("test-event")
            emit_event(run_dir, "test.event", value=1)

            self.assertTrue((run_dir / "harness.log").exists())
            self.assertTrue((run_dir / "telemetry.jsonl").exists())
            payload = json.loads((run_dir / "telemetry.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["event"], "test.event")
            self.assertEqual(payload["value"], 1)

    def test_exception_summary_does_not_expose_traceback_or_secret_fields(self) -> None:
        error = ConfigurationError("invalid configuration")
        payload = exception_summary(error)
        self.assertEqual(payload["type"], "ConfigurationError")
        self.assertEqual(payload["message"], "invalid configuration")
        self.assertNotIn("traceback", payload)


if __name__ == "__main__":
    unittest.main()
