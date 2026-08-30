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


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_skill(path: Path, maximum_chars: int = 24000) -> str:
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


def main() -> int:
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json")
    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    with (ROOT / ".ai-harness/config.toml").open("rb") as handle:
        config = tomllib.load(handle)

    required_plugin = {"name", "description", "version", "author", "license", "skills"}
    missing = required_plugin - plugin.keys()
    if missing:
        raise ValueError(f"plugin.json missing fields: {sorted(missing)}")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError("marketplace.json must contain at least one plugin")

    entry = next((item for item in plugins if item.get("name") == plugin["name"]), None)
    if entry is None:
        raise ValueError("marketplace entry does not reference the plugin")
    if entry.get("version") != plugin["version"]:
        raise ValueError("marketplace and plugin versions must match")
    if config.get("harness", {}).get("version") != int(plugin["version"].split(".", 1)[0]):
        raise ValueError("harness config major version must match plugin major version")

    skill_texts = [validate_skill(path) for path in SKILL_PATHS]
    if skill_texts[0] != skill_texts[1]:
        raise ValueError("canonical and generic Agent Skill copies are out of sync")

    configured_skill = plugin.get("skills")
    if configured_skill != "./skills/":
        raise ValueError("plugin skills root must remain ./skills/")

    print(f"Plugin manifest: {plugin['name']} {plugin['version']}")
    print(f"Marketplace: {marketplace['name']}")
    print(f"Skills: {len(SKILL_PATHS)} aligned/validated")
    print("Context budget: PASS")
    print("Plugin validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
