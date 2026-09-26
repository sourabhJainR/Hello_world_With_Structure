import unittest
from portable.engineering_quality_gate import QualityGate,EngineeringQualityGate
class QualityGateTests(unittest.TestCase):
 def test_all_gates_need_evidence(self):
  r=EngineeringQualityGate().evaluate((QualityGate("tests",True,("t1",)),QualityGate("security",True)))
  self.assertFalse(r.passed); self.assertTrue(r.blocking_defects)
 def test_score_gate(self):
  r=EngineeringQualityGate().from_scores({"tests":.9,"security":.85})
  self.assertTrue(r.passed)
