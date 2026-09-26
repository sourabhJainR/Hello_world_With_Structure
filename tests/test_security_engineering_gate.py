import unittest
from portable.security_engineering_gate import Threat,SecurityEngineeringGate
class SecurityGateTests(unittest.TestCase):
 def test_verified_threat_model_passes(self):
  r=SecurityEngineeringGate().assess((Threat("T1","api","unauthorized access","authz",True),))
  self.assertTrue(r.passed)
 def test_unverified_threat_blocks(self):
  r=SecurityEngineeringGate().assess((Threat("T1","api","bad input","validation"),))
  self.assertFalse(r.passed); self.assertEqual(r.unresolved,("T1",))
