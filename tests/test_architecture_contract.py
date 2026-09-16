"""Architecture constitution regression tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_architecture.py"
CONTRACT = ROOT / "architecture" / "architecture.yaml"


class ArchitectureContractTests(unittest.TestCase):
    def test_contract_is_valid(self) -> None:
        namespace: dict[str, object] = {}
        source = VALIDATOR.read_text(encoding="utf-8")
        exec(compile(source, str(VALIDATOR), "exec"), namespace)
        self.assertIsNone(namespace["validate"]())

    def test_contract_is_yaml_compatible_json(self) -> None:
        raw = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(raw["architecture"]["short_name"], "AER")

    def test_enforcement_points_exist(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for key in ("validator", "tests", "ci"):
            relative_path = contract["enforcement"][key]
            self.assertIsInstance(relative_path, str)
            self.assertTrue((ROOT / relative_path).is_file(), f"missing architecture enforcement point: {relative_path}")
        self.assertIs(contract["enforcement"]["hard_fail"], True)

    def test_learning_remains_advisory(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        rule = contract["domains"]["learning"]["rule"].lower()
        self.assertIn("cannot grant permissions", rule)
        self.assertIn("bypass verification", rule)

    def test_single_canonical_owner_per_domain(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        owners = [domain["canonical_owner"] for domain in contract["domains"].values()]
        self.assertEqual(len(owners), len(set(owners)))


if __name__ == "__main__":
    unittest.main()
