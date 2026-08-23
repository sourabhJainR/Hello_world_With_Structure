"""Install the harness skill into detected agent skill locations.

The installer is intentionally opt-in, idempotent, backup-aware, and does not
install third-party tools or modify MCP configuration.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "ai-coding-orchestrator"
MARKER = "<!-- ai-coding-orchestrator:managed -->"


def backup(path: Path) -> None:
    if path.exists():
        backup_path = path.with_suffix(path.suffix + ".ai-harness.bak")
        if not backup_path.exists():
            shutil.copy2(path, backup_path)


def install_skill(target_root: Path) -> Path:
    target = target_root / "ai-coding-orchestrator"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup(target / "SKILL.md")
        shutil.rmtree(target)
    shutil.copytree(SOURCE, target)
    return target


def append_bootstrap(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if MARKER in text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    block = f"""\n\n{MARKER}\n## AI Coding Orchestrator\nFor non-trivial software-engineering tasks, use the installed `ai-coding-orchestrator` skill before implementation. It detects repository conventions and available optional extensions, retrieves targeted context, verifies changes, and stops after a single adaptive run unless the user explicitly requests a loop. Optional tools are never installed automatically.\n{MARKER}\n"""
    path.write_text(text.rstrip() + block, encoding="utf-8")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Install AI Coding Orchestrator skills")
    parser.add_argument("--global", dest="global_install", action="store_true", help="Install to user-level agent locations")
    parser.add_argument("--claude", action="store_true", help="Install Claude Code skill and global CLAUDE.md bootstrap")
    parser.add_argument("--agents", action="store_true", help="Install generic Agent Skills location")
    parser.add_argument("--gemini", action="store_true", help="Install Gemini skill and global GEMINI.md bootstrap")
    args = parser.parse_args()

    if not (args.global_install or args.claude or args.agents or args.gemini):
        args.global_install = True

    home = Path.home()
    installed: list[Path] = []

    if args.global_install or args.claude:
        installed.append(install_skill(home / ".claude" / "skills"))
        append_bootstrap(home / ".claude" / "CLAUDE.md")

    if args.global_install or args.agents:
        installed.append(install_skill(home / ".agents" / "skills"))

    if args.global_install or args.gemini:
        installed.append(install_skill(home / ".gemini" / "skills"))
        append_bootstrap(home / ".gemini" / "GEMINI.md")

    print("Installed AI Coding Orchestrator:")
    for path in installed:
        print(f"  {path}")
    print("No third-party tools or MCP servers were installed or modified.")
    print("Restart the coding agent so it reloads global skills and instructions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
