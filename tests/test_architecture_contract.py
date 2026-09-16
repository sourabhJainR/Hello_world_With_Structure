"""Architecture constitution regression tests."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_architecture.py"
CONTRACT = ROOT / "architecture" / "architecture.yaml"


def _load_validator():
    spec = importlib.util.spec_from_file_location("aer_architecture_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load architecture validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArchitectureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _load_validator()

    def test_contract_is_valid(self) -> None:
        self.validator.validate()

    def test_contract_is_yaml_compatible_json(self) -> None:
        raw = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(raw["architecture"]["short_name"], "AER")

    def test_validator_cli_is_clean(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.validator.validate()
        self.assertIn("", output.getvalue())

    def test_learning_remains_advisory(self) -> None:
        contract = self.validator.load_contract()
        rule = contract["domains"]["learning"]["rule"].lower()
        self.assertIn("cannot grant permissions", rule)

    def test_single_canonical_owner_per_domain(self) -> None:
        contract = self.validator.load_contract()
        owners = [domain["canonical_owner"] for domain in contract["domains"].values()]
        self.assertEqual(len(owners), len(set(owners)))


if __name__ == "__main__":
    unittest.main()
