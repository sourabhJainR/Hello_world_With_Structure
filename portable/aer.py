#!/usr/bin/env python3
"""Portable AER distribution utility.

Build an offline bundle from the canonical repository, verify it, and install
it into any target repository. The bundle carries the complete AER
implementation under .ai-harness plus the provider-neutral Agent Skill.

Examples:
  python portable/aer.py build --output aer-portable.zip
  python portable/aer.py install aer-portable.zip /path/to/repo
  python portable/aer.py verify aer-portable.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

BUNDLE_FORMAT_VERSION = 1
BUNDLE_NAME = "aer-portable"
MANIFEST_NAME = "aer-bundle.json"
PAYLOAD_ROOT = "payload"
REQUIRED_PATHS = (".ai-harness", "skills/ai-coding-orchestrator")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", "worktrees"}
MUTABLE_FILE_NAMES = {"execution.journal.jsonl", "telemetry.jsonl", "task-memory.jsonl", "regression-events.jsonl"}


@dataclass(frozen=True)
class FileRecord:
    path: str
    sha256: str
    size: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.is_file() and path.name in MUTABLE_FILE_NAMES:
        return False
    return path.is_file()


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for top in REQUIRED_PATHS:
        base = root / top
        if not base.exists():
            raise SystemExit(f"required source path is missing: {base}")
        files.extend(p for p in base.rglob("*") if should_include(p, root))
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_manifest(root: Path, files: list[Path]) -> dict:
    config_path = root / ".ai-harness" / "config.toml"
    harness_version = None
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version ="):
                try:
                    harness_version = int(line.split("=", 1)[1].strip().strip('"\''))
                except ValueError:
                    pass
                break
    records = [
        FileRecord(p.relative_to(root).as_posix(), sha256_file(p), p.stat().st_size).__dict__
        for p in files
    ]
    return {
        "format": BUNDLE_FORMAT_VERSION,
        "name": BUNDLE_NAME,
        "harness_version": harness_version,
        "portable": True,
        "provider_neutral": True,
        "source_paths": list(REQUIRED_PATHS),
        "mutable_state_excluded": True,
        "managed_install_paths": [
            ".ai-harness",
            ".agents/skills/ai-coding-orchestrator",
            ".claude/skills/ai-coding-orchestrator",
            ".gemini/skills/ai-coding-orchestrator",
        ],
        "files": records,
    }


def build(root: Path, output: Path) -> Path:
    files = iter_source_files(root)
    manifest = make_manifest(root, files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for source in files:
            rel = source.relative_to(root).as_posix()
            archive.write(source, f"{PAYLOAD_ROOT}/{rel}")
        launcher = root / "aer.py"
        if launcher.is_file():
            archive.write(launcher, "aer.py")
        readme = (
            "AER portable bundle\n\n"
            "Install with: python aer.py install <bundle.zip> <target-repo>\n"
            "The archive contains the portable AER control plane and Agent Skill.\n"
        )
        archive.writestr(f"{PAYLOAD_ROOT}/PORTABLE_BUNDLE.txt", readme)
    return output


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination != target and destination not in target.parents:
            raise SystemExit(f"unsafe archive path: {member.filename}")
    archive.extractall(destination)


def verify_bundle(bundle: Path) -> dict:
    with zipfile.ZipFile(bundle) as archive:
        if MANIFEST_NAME not in archive.namelist():
            raise SystemExit("bundle manifest is missing")
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        if manifest.get("format") != BUNDLE_FORMAT_VERSION:
            raise SystemExit("unsupported bundle format")
        root = Path(tempfile.mkdtemp(prefix="aer-verify-"))
        try:
            safe_extract(archive, root)
            for record in manifest.get("files", []):
                path = root / PAYLOAD_ROOT / record["path"]
                if not path.is_file():
                    raise SystemExit(f"bundle file missing: {record['path']}")
                if sha256_file(path) != record["sha256"]:
                    raise SystemExit(f"bundle integrity failure: {record['path']}")
            if not (root / "aer.py").is_file():
                raise SystemExit("bundle launcher is missing: aer.py")
            return manifest
        finally:
            shutil.rmtree(root, ignore_errors=True)


def backup(path: Path) -> None:
    if not path.exists():
        return
    backup_path = path.with_name(path.name + ".aer-backup")
    counter = 1
    while backup_path.exists():
        backup_path = path.with_name(f"{path.name}.aer-backup-{counter}")
        counter += 1
    if path.is_dir():
        shutil.copytree(path, backup_path)
    else:
        shutil.copy2(path, backup_path)


def install(bundle: Path, target: Path, install_skill: str) -> None:
    manifest = verify_bundle(bundle)
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="aer-install-"))
    try:
        with zipfile.ZipFile(bundle) as archive:
            safe_extract(archive, temp)
        payload = temp / PAYLOAD_ROOT
        source_harness = payload / ".ai-harness"
        target_harness = target / ".ai-harness"
        backup(target_harness)
        if target_harness.exists():
            shutil.rmtree(target_harness)
        shutil.copytree(source_harness, target_harness)

        if install_skill != "none":
            home = Path.home()
            skill_source = payload / "skills" / "ai-coding-orchestrator"
            skill_targets = {
                "agents": home / ".agents" / "skills" / "ai-coding-orchestrator",
                "claude": home / ".claude" / "skills" / "ai-coding-orchestrator",
                "gemini": home / ".gemini" / "skills" / "ai-coding-orchestrator",
            }
            selected = list(skill_targets) if install_skill == "all" else [install_skill]
            for name in selected:
                destination = skill_targets[name]
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup(destination)
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(skill_source, destination)

        print(f"Installed AER harness v{manifest.get('harness_version') or 'unknown'} into {target}")
        print(f"Portable files: {len(manifest.get('files', []))}")
        print("No MCP configuration, permissions, credentials, git settings, or production access were changed.")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aer", description="Build, verify, and install a portable AER bundle")
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build", help="Build an offline bundle from this AER repository")
    build_parser.add_argument("--output", type=Path, default=Path("aer-portable.zip"))

    verify_parser = sub.add_parser("verify", help="Verify a portable bundle")
    verify_parser.add_argument("bundle", type=Path)

    install_parser = sub.add_parser("install", help="Install a bundle into any repository")
    install_parser.add_argument("bundle", type=Path)
    install_parser.add_argument("target_repo", type=Path, nargs="?", default=Path.cwd())
    install_parser.add_argument("--skill", choices=("none", "agents", "claude", "gemini", "all"), default="agents")

    args = parser.parse_args(argv)
    if args.command == "build":
        output = build(repo_root(), args.output.resolve())
        print(output)
        return 0
    if args.command == "verify":
        manifest = verify_bundle(args.bundle.resolve())
        print(f"AER bundle verified: format={manifest['format']} files={len(manifest['files'])} harness={manifest.get('harness_version')}")
        return 0
    install(args.bundle.resolve(), args.target_repo.resolve(), args.skill)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
