import unittest

from pathlib import Path

import scripts.validate_plugin as validate_plugin


class PluginValidationTests(unittest.TestCase):
    def test_shared_markers_do_not_require_legacy_optional_word(self):
        self.assertNotIn("optional", validate_plugin.SHARED_CONTRACT_MARKERS)

    def test_orchestrator_skill_entrypoints_are_within_budget(self):
        for path in validate_plugin.SKILL_PATHS:
            text = Path(path).read_text(encoding="utf-8")
            self.assertLessEqual(len(text), 9000, str(path))
            for marker in validate_plugin.SHARED_CONTRACT_MARKERS:
                self.assertIn(marker.lower(), text.lower(), f"{path}: {marker}")


if __name__ == "__main__":
    unittest.main()
