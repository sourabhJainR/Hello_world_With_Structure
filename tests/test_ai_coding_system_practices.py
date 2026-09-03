import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AICodingSystemPracticeTests(unittest.TestCase):
    def test_cross_agent_instruction_surfaces_exist(self):
        for relative in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"):
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertLessEqual(len(path.read_text(encoding="utf-8")), 12000, relative)

    def test_harness_skill_stays_within_declared_context_budget(self):
        path = ROOT / "skills/ai-coding-orchestrator/SKILL.md"
        self.assertLessEqual(len(path.read_text(encoding="utf-8")), 9000)

    def test_harness_best_practices_preserve_existing_patterns(self):
        text = (ROOT / ".ai-harness/AI_CODING_SYSTEM_BEST_PRACTICES.md").read_text(encoding="utf-8")
        for pattern in ("Adapter", "Strategy / Policy", "State Machine", "Pipeline", "Dependency Injection"):
            self.assertIn(pattern, text)
        self.assertIn("Do not introduce Factory", text)

    def test_path_specific_instructions_use_supported_frontmatter(self):
        path = ROOT / ".github/instructions/ai-harness.instructions.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("applyTo:", text)
        self.assertIn(".ai-harness", text)


if __name__ == "__main__":
    unittest.main()
