import unittest
from threading import Event

from portable.agency_state_graph import StateGraph


class StateGraphControlLoopTests(unittest.TestCase):
    def test_explicit_join_alias_preserves_deterministic_superstep_join(self) -> None:
        graph = StateGraph()
        graph.add_node("a", lambda state: {"a": True})
        graph.add_node("b", lambda state: {"b": True})
        graph.add_node("join", lambda state: {"joined": state["a"] and state["b"]})
        graph.add_edge(StateGraph.START, "a")
        graph.add_edge(StateGraph.START, "b")
        graph.add_join("a", "join")
        graph.add_join("b", "join")
        graph.add_edge("join", StateGraph.END)
        result = graph.compile().invoke({}, parallel_nodes=lambda name: name in {"a", "b"})
        self.assertEqual(result.state["joined"], True)
        self.assertEqual(result.trace, ("a", "b", "join"))

    def test_cooperative_cancellation_returns_checkpointable_run(self) -> None:
        graph = StateGraph()
        graph.add_node("work", lambda state: {"done": True})
        graph.add_edge(StateGraph.START, "work")
        graph.add_edge("work", StateGraph.END)
        cancellation = Event()
        cancellation.set()
        result = graph.compile().invoke({}, run_id="cancelled", cancellation=cancellation)
        self.assertTrue(result.interrupted)
        self.assertEqual(result.steps, 0)
        self.assertEqual(result.trace, ())


if __name__ == "__main__":
    unittest.main()
