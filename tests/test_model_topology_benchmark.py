import unittest
from portable.model_topology_benchmark import *
class ModelTopologyBenchmarkTests(unittest.TestCase):
 def test_same_tasks_are_run_for_each_model(self):
  r=ModelTopologyBenchmark().run(("local","frontier"),("t1","t2"),lambda m,t:ModelEvaluation(m,t,.8,True,f"{m}-{t}"))
  self.assertEqual(r.coverage,{"local":.8,"frontier":.8}); self.assertTrue(r.verified)
 def test_unverified_result_is_not_marked_verified(self):
  r=ModelTopologyBenchmark().run(("local",),("t1",),lambda m,t:ModelEvaluation(m,t,.9,False,""))
  self.assertFalse(r.verified)
