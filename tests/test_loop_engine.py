import importlib.util
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("loop_engine", ROOT / ".ai-harness/runtime/loop_engine.py")
loop_engine = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(loop_engine)

class LoopEngineeringTests(unittest.TestCase):
    def test_default_run_does_not_recurse(self):
        plan = loop_engine.loop_plan("fix export", {"mode": "adaptive", "capabilities": []})
        self.assertEqual(plan["budget"]["max_iterations"], 1)
    def test_explicit_loop_is_bounded(self):
        plan = loop_engine.loop_plan("debug legacy architecture regression", {"mode": "debug", "capabilities": ["rca", "review"]}, risk="high", explicit_loop=True, configured_max=10)
        self.assertLessEqual(plan["budget"]["max_iterations"], 6)
        self.assertIn("reviewer", {a["name"] for a in plan["agents"]})
    def test_scheduler_stops_on_diminishing_returns(self):
        action = loop_engine.next_action([{"utility": .70, "regressions": 0, "uncertainty": .2}, {"utility": .71, "regressions": 0, "uncertainty": .2}], {"max_iterations": 4})
        self.assertEqual(action["reason"], "diminishing-returns")
    def test_scheduler_repairs_before_polish(self):
        action = loop_engine.next_action([{"utility": .5, "regressions": 1, "uncertainty": .1}], {"max_iterations": 4})
        self.assertEqual(action["action"], "repair")
    def test_token_cost_affects_utility(self):
        result={"evidence_score":1,"verification_score":1,"quality_score":1,"uncertainty":0}
        self.assertLess(loop_engine.score_iteration(result, token_cost=30000)["utility"], loop_engine.score_iteration(result)["utility"])

if __name__ == "__main__": unittest.main()
