"""Validate the deployable plugin and marketplace manifests using the Python stdlib."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json")
    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")

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

    skill = ROOT / "skills" / "ai-coding-orchestrator" / "SKILL.md"
    if not skill.is_file():
        raise ValueError("canonical skill is missing")

    print(f"Plugin manifest: {plugin['name']} {plugin['version']}")
    print(f"Marketplace: {marketplace['name']}")
    print(f"Skill: {skill.relative_to(ROOT)}")
    print("Plugin validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
