from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").lower()


def test_canonical_policy_mentions_curated_change_requirements():
    policy = _read(".ai-harness/ENGINEERING_DESIGN_POLICY.md")
    for phrase in (
        "reuse-first",
        "minimal db",
        "performance",
        "logging",
        "exception handling",
        "regression",
        "usage patterns",
    ):
        assert phrase in policy


def test_deployable_orchestrator_requires_reuse_and_verification():
    skill = _read("skills/ai-coding-orchestrator/SKILL.md")
    for phrase in (
        "reuse existing",
        "n+1",
        "database",
        "performance",
        "logging",
        "exception",
        "regression",
    ):
        assert phrase in skill


def test_repository_instructions_preserve_existing_workflow_usage():
    instructions = _read("AGENTS.md")
    assert "preserve" in instructions
    assert "usage pattern" in instructions
    assert "reuse existing" in instructions
    assert "final diff" in instructions
