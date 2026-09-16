import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
            with self.assertRaisesRegex(ValueError, "different content"):
                runtime.emit("email.received", {"message_id": "m2"}, event_id="evt-1")
            claim = runtime.claim("evt-1")
            self.assertIsNotNone(claim)
            self.assertIsNone(runtime.claim("evt-1"))
            runtime.complete("evt-1", claim.claim_id, "success", detail="accepted")
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

    def test_timezone_is_required_for_explicit_trigger_time(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            with self.assertRaisesRegex(ValueError, "timezone-aware"):
                runtime.emit("job", {}, event_id="evt-naive", not_before=datetime.now())
            scheduler.close()

    def test_dispatch_hands_off_to_handler_and_records_success(self):
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

    def test_expired_claim_is_recoverable_without_duplicate_attempt_increment(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler, claim_lease_seconds=60)
            created = datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)
            event = runtime.emit("adaptive_runtime", {"task": "x"}, not_before=created)
            first = runtime.claim(event.event_id, now=created)
            self.assertIsNotNone(first)
            self.assertEqual(first.event.attempts, 1)
            before_expiry = runtime.claim(event.event_id, now=created + timedelta(seconds=59))
            self.assertIsNone(before_expiry)
            recovered = runtime.claim(event.event_id, now=created + timedelta(seconds=61))
            self.assertIsNotNone(recovered)
            self.assertNotEqual(first.claim_id, recovered.claim_id)
            self.assertEqual(recovered.event.attempts, 2)
            runtime.complete(event.event_id, recovered.claim_id, "success", now=created + timedelta(seconds=61))
            scheduler.close()

    def test_due_filters_kind_and_orders_by_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            high = runtime.emit("adaptive_runtime", {"task": "high"}, priority=0)
            low = runtime.emit("adaptive_runtime", {"task": "low"}, priority=2)
            unrelated = runtime.emit("other", {"task": "other"}, priority=0)
            due = runtime.due(kind="adaptive_runtime", limit=10)
            self.assertEqual([event.event_id for event in due], [high.event_id, low.event_id])
            self.assertNotIn(unrelated.event_id, [event.event_id for event in due])
            scheduler.close()

    def test_status_and_outcome_are_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler)
            event = runtime.emit("adaptive_runtime", {"task": "x"}, priority=0)
            claim = runtime.claim(event.event_id)
            self.assertIsNotNone(claim)
            runtime.complete(
                event.event_id,
                claim.claim_id,
                "success",
                outcome={"result_status": "accepted"},
            )
            status = runtime.get(event.event_id)
            self.assertIsNotNone(status)
            self.assertEqual(status.status, "success")
            self.assertEqual(status.outcome["result_status"], "accepted")
            self.assertIsNotNone(status.completed_at)
            scheduler.close()

    def test_concurrent_claims_have_single_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = TriggerRuntime(scheduler, claim_lease_seconds=60)
            event = runtime.emit("adaptive_runtime", {"task": "x"})

            def claim_once():
                return runtime.claim(event.event_id)

            with ThreadPoolExecutor(max_workers=8) as executor:
                claims = list(executor.map(lambda _: claim_once(), range(8)))
            winners = [claim for claim in claims if claim is not None]
            self.assertEqual(len(winners), 1)
            runtime.complete(event.event_id, winners[0].claim_id, "success")
            scheduler.close()


if __name__ == "__main__":
    unittest.main()
