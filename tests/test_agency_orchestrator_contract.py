import unittest

from portable.agency_orchestrator_contract import HostExecutionContext, validate_host_context


class HostOrchestratorContractTests(unittest.TestCase):
    def test_valid_context(self):
        validate_host_context(HostExecutionContext("run-1"))

    def test_external_sandbox_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_host_context(HostExecutionContext("run-1", sandbox="untrusted"))

    def test_permission_authority_must_remain_with_host(self):
        with self.assertRaises(ValueError):
            validate_host_context(HostExecutionContext("run-1", permission_scope="agency"))

    def test_invalid_mutation_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_host_context(HostExecutionContext("run-1", mutation_mode="parallel-write"))


if __name__ == "__main__":
    unittest.main()
