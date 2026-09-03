"""Validate plugin packaging, metadata, skill alignment, and context budgets."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATHS = [
    ROOT / "skills/ai-coding-orchestrator/SKILL.md",
    ROOT / ".agents/skills/ai-coding-orchestrator/SKILL.md",
    ROOT / ".claude/skills/ai-coding-orchestrator/SKILL.md",
]
SHARED_CONTRACT_MARKERS = (
    "Engineering State Ledger",
    "repository-aware",
    "minimal safe change",
    "regression",
    "evidence",
    "optional",
)
HARNESS_VERSION_COMPARISON = re.compile(
    r"(?:harness(?:\s*['\"]?\s*\]\s*\[\s*['\"]?version['\"]?|\s*\.\s*version)|['\"]?version['\"]?\s*\]\s*\)?)\s*==\s*\d+",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_skill(path: Path, maximum_chars: int = 9000) -> str:
    if not path.is_file():
        raise ValueError(f"skill is missing: {path}")
    text = path.read_text(encoding="utf-8")
    if len(text) > maximum_chars:
        raise ValueError(f"skill exceeds context budget: {path} ({len(text)} chars)")
    if not re.search(r"(?m)^name:\s*ai-coding-orchestrator\s*$", text):
        raise ValueError(f"skill metadata name is invalid: {path}")
    if not re.search(r"(?m)^description:\s*\S", text):
        raise ValueError(f"skill metadata description is missing: {path}")
    return text


def validate_no_hard_coded_harness_version() -> None:
    workflow_root = ROOT / ".github" / "workflows"
    if not workflow_root.is_dir():
        return
    violations: list[str] = []
    for path in sorted(workflow_root.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if HARNESS_VERSION_COMPARISON.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
    if violations:
        raise ValueError(
            "workflows must derive harness version from .ai-harness/config.toml; "
            "hard-coded numeric comparisons found:\n" + "\n".join(violations)
        )


def main() -> int:
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json")
    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    with (ROOT / ".ai-harness/config.toml").open("rb") as handle:
        config = tomllib.load(handle)

    required_plugin = {"name", "description", "version", "author", "license", "skills"}
    missing = required_plugin - plugin.keys()
    if missing:
        raise ValueError(f"plugin.json missing fields: {sorted(missing)}")

    harness_version = config.get("harness", {}).get("version")
    if not isinstance(harness_version, int) or harness_version <= 0:
        raise ValueError("harness.version must be a positive integer")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError("marketplace.json must contain at least one plugin")

    entry = next((item for item in plugins if item.get("name") == plugin["name"]), None)
    if entry is None:
        raise ValueError("marketplace entry does not reference the plugin")
    if entry.get("version") != plugin["version"]:
        raise ValueError("marketplace and plugin versions must match")
    try:
        plugin_major = int(str(plugin["version"]).split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise ValueError("plugin version must use numeric semver") from exc
    if harness_version != plugin_major:
        raise ValueError("harness config major version must match plugin major version")

    validate_no_hard_coded_harness_version()

    skill_texts = [validate_skill(path) for path in SKILL_PATHS]
    missing_contract = {
        str(path): [marker for marker in SHARED_CONTRACT_MARKERS if marker.lower() not in text.lower()]
        for path, text in zip(SKILL_PATHS, skill_texts)
    }
    missing_contract = {path: markers for path, markers in missing_contract.items() if markers}
    if missing_contract:
        raise ValueError(f"skill contract markers missing: {missing_contract}")

    configured_skill = plugin.get("skills")
    if configured_skill != "./skills/":
        raise ValueError("plugin skills root must remain ./skills/")

    print(f"Harness version: {harness_version} (source: .ai-harness/config.toml)")
    print(f"Plugin manifest: {plugin['name']} {plugin['version']}")
    print(f"Marketplace: {marketplace['name']}")
    print(f"Skills: {len(SKILL_PATHS)} independently validated with shared contract")
    print("Version source-of-truth guard: PASS")
    print("Context budget: PASS")
    print("Plugin validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
