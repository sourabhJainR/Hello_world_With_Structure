import unittest

from portable.agency_state import ExecutionLifecycle, ExecutionState, validate_transition_graph


class ExecutionLifecycleTests(unittest.TestCase):
    def test_happy_path_and_ledger_chain(self):
        lifecycle = ExecutionLifecycle(max_repairs=2)
        lifecycle.transition(ExecutionState.PLANNED, "plan-ready")
        lifecycle.transition(ExecutionState.EXECUTING, "executor-started")
        lifecycle.transition(ExecutionState.VERIFYING, "execution-finished")
        lifecycle.transition(ExecutionState.PASSED, "verification-clean")
        self.assertTrue(lifecycle.terminal)
        self.assertEqual(lifecycle.state, ExecutionState.PASSED)
        self.assertEqual(len(lifecycle.ledger.events), 5)
        self.assertEqual(lifecycle.ledger.events[1].parent_event_id, lifecycle.ledger.events[0].event_id)

    def test_invalid_transition_is_rejected(self):
        lifecycle = ExecutionLifecycle()
        with self.assertRaises(ValueError):
            lifecycle.transition(ExecutionState.VERIFYING)

    def test_repair_budget_is_bounded(self):
        lifecycle = ExecutionLifecycle(max_repairs=1)
        lifecycle.transition(ExecutionState.PLANNED)
        lifecycle.transition(ExecutionState.EXECUTING)
        lifecycle.transition(ExecutionState.VERIFYING)
        lifecycle.request_repair("material finding")
        lifecycle.transition(ExecutionState.EXECUTING)
        lifecycle.transition(ExecutionState.VERIFYING)
        lifecycle.request_repair("second material finding")
        self.assertEqual(lifecycle.state, ExecutionState.ESCALATED)
        self.assertEqual(lifecycle.repair_attempts, 1)

    def test_terminal_states_cannot_transition(self):
        lifecycle = ExecutionLifecycle()
        lifecycle.transition(ExecutionState.BLOCKED)
        with self.assertRaises(RuntimeError):
            lifecycle.transition(ExecutionState.PLANNED)

    def test_ledger_event_ids_are_deterministic(self):
        a = ExecutionLifecycle()
        b = ExecutionLifecycle()
        ea = a.ledger.events[0]
        eb = b.ledger.events[0]
        self.assertEqual(ea.event_id, eb.event_id)

    def test_transition_graph_is_valid(self):
        validate_transition_graph()


if __name__ == "__main__":
    unittest.main()
