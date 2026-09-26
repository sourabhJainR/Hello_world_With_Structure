import unittest
from portable.verified_repair_loop import *
class RepairLoopTests(unittest.TestCase):
 def test_verified_improvement_stops_loop(self):
  def repair(d,i): return RepairAttempt(i,d,.8 if i==2 else .5,i==2,f"e{i}")
  r=VerifiedRepairLoop().run("failure",.7,repair,max_attempts=3)
  self.assertTrue(r.accepted); self.assertEqual(len(r.attempts),2)
 def test_unverified_improvement_does_not_promote(self):
  r=VerifiedRepairLoop().run("failure",.7,lambda d,i:RepairAttempt(i,d,.99,False,f"e{i}"),max_attempts=2)
  self.assertFalse(r.accepted)
