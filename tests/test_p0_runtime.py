#!/usr/bin/env python3
import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.ai-harness/runtime'))
from p0 import *

class P0RuntimeTests(unittest.TestCase):
    def test_state_shape_and_schema_version(self):
        s=new_state('T-1','fix export duplication'); self.assertEqual(validate_state(s),[]); self.assertEqual(s['schema_version'],'1.0'); self.assertEqual(s['outcome']['status'],'unknown')
    def test_decision_requires_existing_evidence(self):
        s=new_state('T-2','x');
        with self.assertRaises(ValueError): add_decision(s,'use existing pattern',['missing'])
    def test_decision_and_verification_are_traceable(self):
        s=new_state('T-3','x'); e=evidence('source','file.py','function owns filtering','file.py:20','abc','high'); add_evidence(s,e); add_decision(s,'reuse filter',[e['id']]); verification(s,'unit-test','passed','pytest tests/test_x.py',[e['id']]); self.assertEqual(validate_state(s),[])
    def test_outcome_requires_evidence_and_is_traceable(self):
        s=new_state('T-4','x'); e=evidence('runtime','ci','accepted by review','run:1','abc','high'); add_evidence(s,e); record_outcome(s,'accepted',review_result='approved',metrics={'time_to_proven_change':12.5},evidence_ids=[e['id']]); self.assertEqual(validate_state(s),[]); self.assertEqual(s['outcome']['status'],'accepted')
        with self.assertRaises(ValueError): record_outcome(s,'accepted',evidence_ids=['missing'])
    def test_risk_controls_escalate(self):
        self.assertEqual(risk_level({}), 'low'); self.assertEqual(risk_level({'security_risk':3}), 'critical'); self.assertIn('independent_review',risk_controls('high'))
    def test_thrash_detects_repeated_no_progress(self):
        self.assertTrue(detect_thrash([{'signature':'same'}]*5)['thrashing']); self.assertFalse(detect_thrash([{'signature':str(i)} for i in range(5)])['thrashing'])
    def test_proof_is_deterministic_for_same_state(self):
        s=new_state('T-5','x'); a=proof_bundle(s); b=proof_bundle(s); self.assertEqual(a['proof_id'],b['proof_id'])

if __name__=='__main__': unittest.main()
