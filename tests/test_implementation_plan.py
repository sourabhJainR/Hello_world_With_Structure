import unittest
from portable.implementation_plan import WorkStep, ImplementationPlanner

class ImplementationPlanTests(unittest.TestCase):
    def test_parallel_groups_are_dependency_safe(self):
        p=ImplementationPlanner().build([
            WorkStep("api","API",verification=("integration",)),
            WorkStep("ui","UI",verification=("browser",)),
            WorkStep("e2e","E2E",("api","ui"),("e2e",)),
        ])
        self.assertEqual(p.parallel_groups[0],("api","ui"))
        self.assertEqual(p.parallel_groups[1],("e2e",))
        self.assertTrue(p.complete)
    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            ImplementationPlanner().build([WorkStep("a","a",("b",),("t",)),WorkStep("b","b",("a",),("t",))])
