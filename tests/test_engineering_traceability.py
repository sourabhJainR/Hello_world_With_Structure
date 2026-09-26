import unittest
from portable.engineering_traceability import *
class TraceabilityTests(unittest.TestCase):
 def test_complete_trace(self):
  r=EngineeringTraceability().evaluate((TraceLink("R1",("C1",),("T1",),("E1",)),),("R1",))
  self.assertTrue(r.verified); self.assertEqual(r.completeness,1)
 def test_missing_test_blocks(self):
  r=EngineeringTraceability().evaluate((TraceLink("R1",("C1",),(),("E1",)),),("R1","R2"))
  self.assertEqual(r.missing,("R1","R2")); self.assertFalse(r.verified)
