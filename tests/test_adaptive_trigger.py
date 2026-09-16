import tempfile
import threading
import time
import unittest
from pathlib import Path

from portable import (
    AdaptiveTriggerRequest,
    TriggerOutcome,
    TriggerReceipt,
    TriggerStatus,
    trigger_adaptive_runtime,
)
from portable.adaptive_trigger import AdaptiveTrigger
from portable.adaptive_runtime import AdaptiveRuntime
from portable.agent_capabilities import AutomationScheduler
from portable.orchestration import Graph
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

    def test_trigger_persists_and_returns_without_execution_when_dispatch_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            started = time.monotonic()
            receipt = trigger.trigger_adaptive_runtime(
                "fix bug", directory, {"source": "llm-chat"}, fire_and_forget=False
            )
            elapsed = time.monotonic() - started
            self.assertEqual(receipt.status, "pending")
            self.assertTrue(receipt.trigger_id)
            self.assertLess(elapsed, 1.0)
            self.assertEqual(calls, [])
            self.assertEqual(trigger_runtime.due(limit=1, kind="adaptive_runtime")[0].event_id, receipt.trigger_id)
            trigger.close()
            scheduler.close()

    def test_fire_and_forget_dispatches_on_background_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            done = threading.Event()
            calls = []
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            trigger_runtime = TriggerRuntime(scheduler)

            def runner(request, trigger_id):
                calls.append((request, trigger_id))
                done.set()
                return "accepted"

            trigger = AdaptiveTrigger(trigger_runtime, runner)
            receipt = trigger.trigger_adaptive_runtime("task", directory, {"source": "llm-chat"})
            self.assertTrue(receipt.trigger_id)
            self.assertTrue(done.wait(2.0))
            self.assertEqual(calls[0][0].task, "task")
            self.assertEqual(trigger_runtime.due(), ())
            self.assertEqual(trigger.get_status(receipt.trigger_id).status, "success")
            trigger.close()
            scheduler.close()

    def test_background_dispatch_claims_requested_event_not_another_due_event(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            first = trigger.trigger_adaptive_runtime("first", directory, {}, fire_and_forget=False)
            second = trigger.trigger_adaptive_runtime("second", directory, {}, fire_and_forget=False)
            outcome = trigger._dispatch_event(second.trigger_id)
            self.assertEqual(outcome.trigger_id, second.trigger_id)
            self.assertEqual(calls[0][0].task, "second")
            self.assertEqual([event.event_id for event in trigger_runtime.due(limit=10, kind="adaptive_runtime")], [first.trigger_id])
            trigger.close()
            scheduler.close()

    def test_same_event_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, _, trigger = self._runtime(directory, calls)
            first = trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            second = trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            self.assertEqual(first.trigger_id, second.trigger_id)
            trigger.dispatch_once()
            self.assertEqual(len(calls), 1)
            trigger.close()
            scheduler.close()

    def test_changed_idempotency_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, _, trigger = self._runtime(directory, calls)
            trigger.trigger_adaptive_runtime("task", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            with self.assertRaisesRegex(ValueError, "different content"):
                trigger.trigger_adaptive_runtime("other", directory, {"x": 1}, event_id="chat-42", fire_and_forget=False)
            trigger.close()
            scheduler.close()

    def test_failure_is_durable_and_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls, fail=True)
            receipt = trigger.trigger_adaptive_runtime("task", directory, {}, max_attempts=2, fire_and_forget=False)
            trigger.dispatch_once()
            status = trigger.get_status(receipt.trigger_id)
            self.assertEqual(status.status, "pending")
            self.assertEqual(status.attempts, 1)
            self.assertEqual(status.outcome["error_type"], "RuntimeError")
            self.assertEqual(trigger_runtime.due(limit=1), ())
            trigger.close()
            scheduler.close()

    def test_dispatch_does_not_duplicate_claimed_work(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            trigger.trigger_adaptive_runtime("task", directory, {}, fire_and_forget=False)
            first = trigger.dispatch_once()
            second = trigger.dispatch_once()
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(len(calls), 1)
            self.assertEqual(trigger_runtime.due(), ())
            trigger.close()
            scheduler.close()

    def test_dispatch_once_ignores_unrelated_trigger_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            trigger_runtime.emit("other", {"task": "leave me alone"}, event_id="unrelated")
            receipt = trigger.trigger_adaptive_runtime("run me", directory, {}, fire_and_forget=False)
            outcomes = trigger.dispatch_once(limit=20)
            self.assertEqual([item.trigger_id for item in outcomes], [receipt.trigger_id])
            self.assertEqual(trigger_runtime.get("unrelated").status, "pending")
            trigger.close()
            scheduler.close()

    def test_runtime_keyed_adapter_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = AdaptiveRuntime(Graph([]), automation_scheduler=AutomationScheduler(Path(directory) / "runtime.sqlite"))
            first = AdaptiveTrigger.for_runtime(runtime)
            second = AdaptiveTrigger.for_runtime(runtime)
            self.assertIs(first, second)
            runtime.automation_scheduler.close()

    def test_priority_is_propagated_to_durable_status(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            scheduler, trigger_runtime, trigger = self._runtime(directory, calls)
            receipt = trigger.trigger_adaptive_runtime("urgent", directory, {}, priority="high", fire_and_forget=False)
            status = trigger.get_status(receipt.trigger_id)
            self.assertEqual(status.priority, 0)
            trigger.close()
            scheduler.close()

    def test_module_convenience_uses_reusable_runtime_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = AutomationScheduler(Path(directory) / "runtime.sqlite")
            runtime = AdaptiveRuntime(Graph([]), automation_scheduler=scheduler)
            first = AdaptiveTrigger.for_runtime(runtime)
            trigger_adaptive_runtime(runtime, "queued", directory, event_id="convenience-1")
            self.assertIs(first, AdaptiveTrigger.for_runtime(runtime))
            first.close()
            scheduler.close()

    def test_public_trigger_types_are_exported(self):
        self.assertTrue(all(value is not None for value in (
            AdaptiveTriggerRequest, TriggerOutcome, TriggerReceipt, TriggerStatus, trigger_adaptive_runtime,
        )))


if __name__ == "__main__":
    unittest.main()
