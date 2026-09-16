import tempfile
import time
import unittest
from pathlib import Path

from portable.adaptive_trigger import AdaptiveTrigger
from portable.agent_capabilities import AutomationScheduler
from portable.trigger_runtime import TriggerRuntime


class AdaptiveTriggerTests(unittest.TestCase):
    def _runtime(self, directory, calls, *, fail=False):
        scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
        trigger_runtime = TriggerRuntime(scheduler)

        def runner(request, trigger_id):
            calls.append((request, trigger_id))
            if fail:
                raise RuntimeError("boom")
            return "accepted"

        return scheduler, trigger_runtime, AdaptiveTrigger(trigger_runtime, runner)

    def test_trigger_persists_and_returns_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            started = time.monotonic()
            receipt = trigger.trigger_adaptive_runtime("fix bug", directory, {"source": "llm-chat"}, fire_and_forget=False)
            elapsed = time.monotonic() - started
            self.assertEqual(receipt.status, "pending")
            self.assertTrue(receipt.trigger_id)
            self.assertLess(elapsed, 1.0)
            self.assertEqual(calls[0][0].task, "fix bug")
            self.assertEqual(trigger_runtime.due(), ())
            trigger.close(wait=True)
            scheduler.close()

    def test_same_event_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            first = trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            second = trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            self.assertEqual(first.trigger_id, second.trigger_id)
            trigger.dispatch_once()
            self.assertEqual(len(calls), 1)
            trigger.close(wait=True)
            scheduler.close()

    def test_changed_idempotency_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, _, trigger = self._runtime(directory, calls)
            trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            with self.assertRaisesRegex(ValueError, "different content"):
                trigger.trigger_adaptive_runtime("other", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            trigger.close(wait=True)
            scheduler.close()

    def test_failure_is_durable_and_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls, fail=True)
            receipt = trigger.trigger_adaptive_runtime("task", directory, {}, max_attempts=2, fire_and_forget=False)
            trigger.dispatch_once()
            event = trigger_runtime.due(limit=1)
            self.assertEqual(receipt.status, "pending")
            self.assertEqual(len(event), 0)
            row = scheduler._connect().execute(
                "SELECT status, attempts FROM trigger_events WHERE event_id=?", (receipt.trigger_id,)
            ).fetchone()
            self.assertEqual(row, ("pending", 1))
            trigger.close(wait=True)
            scheduler.close()

    def test_dispatch_does_not_duplicate_claimed_work(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            receipt = trigger.trigger_adaptive_runtime("task", directory, {}, fire_and_forget=False)
            first = trigger.dispatch_once()
            second = trigger.dispatch_once()
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(len(calls), 1)
            self.assertEqual(trigger_runtime.due(), ())
            trigger.close(wait=True)
            scheduler.close()


if __name__ == "__main__":
    unittest.main()
