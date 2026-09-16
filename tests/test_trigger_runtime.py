import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from portable.agent_capabilities import AutomationScheduler
from portable.trigger_runtime import TriggerRuntime


class TriggerRuntimeTests(unittest.TestCase):
    def test_event_is_idempotent_and_claim_is_single_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            event = runtime.emit("email.received", {"message_id": "m1"}, event_id="evt-1")
            duplicate = runtime.emit("email.received", {"message_id": "m1"}, event_id="evt-1")
            self.assertEqual(event.event_id, duplicate.event_id)
            claim = runtime.claim("evt-1")
            self.assertIsNotNone(claim)
            self.assertIsNone(runtime.claim("evt-1"))
            runtime.complete("evt-1", claim.claim_id, "success")
            self.assertIsNone(runtime.claim("evt-1"))
            scheduler.close()

    def test_retry_is_bounded_and_backed_off(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            runtime.emit("job", {"task": "x"}, event_id="evt-2", max_attempts=2)
            claim = runtime.claim("evt-2")
            runtime.complete("evt-2", claim.claim_id, "retryable", detail="temporary")
            self.assertEqual(runtime.due(now=datetime.now(timezone.utc)), ())
            future = datetime.now(timezone.utc) + timedelta(seconds=6)
            due = runtime.due(now=future)
            self.assertEqual([item.event_id for item in due], ["evt-2"])
            claim2 = runtime.claim("evt-2", now=future)
            runtime.complete("evt-2", claim2.claim_id, "retryable", detail="again")
            self.assertEqual(runtime.due(now=future + timedelta(seconds=20)), ())
            scheduler.close()

    def test_dispatch_hands_off_to_handler_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            runtime.emit("manual", {"task": "do it"}, event_id="evt-3")
            seen = []

            def handler(event):
                seen.append((event.event_id, event.kind, event.payload))
                return "accepted"

            result = runtime.dispatch_due(handler)
            self.assertEqual(result[0], "accepted")
            self.assertEqual(seen[0][0], "evt-3")
            self.assertEqual(runtime.due(), ())
            scheduler.close()
