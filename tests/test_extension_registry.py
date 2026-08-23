import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness"))

import extension_registry  # noqa: E402


class ExtensionRegistryTests(unittest.TestCase):
    def test_registry_is_present(self):
        self.assertTrue(extension_registry.REGISTRY.exists())

    def test_detection_is_read_only_and_structured(self):
        result = extension_registry.detect_extensions()
        self.assertIn("graphify", result)
        self.assertIn("code_memory", result)
        self.assertIn("superpowers", result)
        self.assertIn("ponytail", result)
        self.assertIn("caveman", result)
        for value in result.values():
            self.assertIn("available", value)
            self.assertIn("capabilities", value)
            self.assertIn("policy", value)


if __name__ == "__main__":
    unittest.main()
