import unittest
from portable.performance_budget import *
class PerformanceBudgetTests(unittest.TestCase):
 def test_budget_passes(self):
  b=PerformanceBudget(200,10,512,80); o=PerformanceObservation(150,12,400,60)
  self.assertTrue(PerformanceBudgetGate().evaluate(b,o).passed)
 def test_latency_and_memory_block(self):
  b=PerformanceBudget(200,10,512,80); o=PerformanceObservation(250,12,700,60)
  r=PerformanceBudgetGate().evaluate(b,o)
  self.assertEqual(r.violations,("latency","memory"))
