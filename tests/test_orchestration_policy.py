import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".ai-harness" / "config.toml"
SKILL = ROOT / ".agents" / "skills" / "ai-coding-orchestrator" / "SKILL.md"


class OrchestrationPolicyTests(unittest.TestCase):
    def test_ten_pass_policy_is_configured(self) -> None:
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        orchestration = config["orchestration"]
        self.assertEqual(orchestration["max_passes"], 10)
        self.assertEqual(orchestration["mandatory_high_risk_passes"], [6, 7, 8, 10])
        self.assertTrue((ROOT / orchestration["policy_file"]).exists())

    def test_skill_references_all_control_plane_policies(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        required = [
            "ORCHESTRATION_SPEC.md",
            "TEN_LOOP_POLICY.md",
            "CONTEXT_POLICY.md",
            "ARCHITECTURE_POLICY.md",
            "EXECUTION_POLICY.md",
            "VERIFICATION_POLICY.md",
            "REVIEW_POLICY.md",
            "LEARNING_POLICY.md",
            "TOKEN_POLICY.md",
            "PROVIDER_CONTRACT.md",
            "QUALITY_GOVERNANCE.md",
        ]
        for name in required:
            self.assertIn(name, skill, name)

    def test_ten_passes_are_distinct(self) -> None:
        policy = (ROOT / ".ai-harness" / "TEN_LOOP_POLICY.md").read_text(encoding="utf-8")
        passes = re.findall(r"\|\s*(\d+)\s*\|", policy)
        self.assertEqual([int(value) for value in passes], list(range(1, 11)))


if __name__ == "__main__":
    unittest.main()
