import tempfile
import unittest
from pathlib import Path

from runtime.instruction_loader import discover, prompt_block


class InstructionLoaderTests(unittest.TestCase):
    def test_discovers_supported_global_instruction_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("shared rules", encoding="utf-8")
            (root / "CLAUDE.md").write_text("provider entry", encoding="utf-8")
            result = discover(root)
            self.assertEqual(result["files"][:2], ["AGENTS.md", "CLAUDE.md"])
            self.assertIn("shared rules", result["text"])
            self.assertIn("provider entry", result["text"])

    def test_deduplicates_identical_instruction_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "same guidance"
            (root / "AGENTS.md").write_text(text, encoding="utf-8")
            (root / "CLAUDE.md").write_text(text, encoding="utf-8")
            result = discover(root)
            self.assertEqual(result["text"].count(text), 1)

    def test_prompt_block_has_safe_no_file_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            block = prompt_block(Path(tmp))
            self.assertIn("No repository-specific", block)


if __name__ == "__main__":
    unittest.main()
