import unittest
from portable.full_stack_contract import ContractEndpoint,FullStackContractEngine
class FullStackContractTests(unittest.TestCase):
 def test_contract_spans_layers(self):
  c=FullStackContractEngine().build(("loading","ready","error"),(ContractEndpoint("GET","/users","query","User[]",("401",)),),("user id unique",),("login->list users",))
  self.assertTrue(c.complete); self.assertEqual(FullStackContractEngine().validate(c),())
 def test_invalid_endpoint_fails(self):
  with self.assertRaises(ValueError): FullStackContractEngine().build(("ready",),(ContractEndpoint("TRACE","users","",""),),("x",),("x",))
