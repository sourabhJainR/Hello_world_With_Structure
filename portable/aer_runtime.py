#!/usr/bin/env python3
"""Build, verify, install and update isolated AER distributions.

AER is machine-scoped. Project repositories are workspaces only and are never
used as an installation location. Installed versions are pinned by semantic
version, exact source commit and bundle hash, so updates are auditable and
rollbacks are deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BUNDLE_FORMAT_VERSION = 2
BUNDLE_NAME = "aer-portable"
AER_REPOSITORY = "sourabhJainR/Hello_world_With_Structure"
AER_BRANCH = "main"
MANIFEST_NAME = "aer-bundle.json"
PAYLOAD_ROOT = "payload"
REQUIRED_PATHS = (".ai-harness", "skills/ai-coding-orchestrator", "portable")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", "worktrees"}
MUTABLE_FILE_NAMES = {"execution.journal.jsonl", "telemetry.jsonl", "task-memory.jsonl", "regression-events.jsonl"}

@dataclass(frozen=True)
class FileRecord:
    path: str
    sha256: str
    size: int

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def home_aer(aer_home: Path | None = None) -> Path:
    return (aer_home or (Path.home() / ".aer")).expanduser().resolve()

def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    return not (path.is_file() and path.name in MUTABLE_FILE_NAMES)

def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for top in REQUIRED_PATHS:
        base = root / top
        if not base.exists():
            raise SystemExit(f"required source path is missing: {base}")
        files.extend(p for p in base.rglob("*") if p.is_file() and should_include(p, root))
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _plugin_version(root: Path) -> str:
    path = root / ".claude-plugin" / "plugin.json"
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        version = value.get("version")
        if isinstance(version, str) and version:
            return version
    config = root / ".ai-harness" / "config.toml"
    if config.exists():
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version ="):
                raw = line.split("=", 1)[1].strip().strip('"\'')
                return f"{raw}.0.0" if raw.isdigit() else raw
    return "0.0.0"

def _version_tuple(version: str) -> tuple[int, int, int]:
    values = []
    for part in version.split(".")[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        values.append(int(digits or 0))
    while len(values) < 3:
        values.append(0)
    return tuple(values[:3])

def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) >= 7 else None

def make_manifest(root: Path, files: list[Path], source_commit: str | None = None, source_ref: str = AER_BRANCH) -> dict:
    records = [FileRecord(p.relative_to(root).as_posix(), sha256_file(p), p.stat().st_size).__dict__ for p in files]
    version = _plugin_version(root)
    return {
        "format": BUNDLE_FORMAT_VERSION,
        "name": BUNDLE_NAME,
        "version": version,
        "harness_version": _version_tuple(version)[0],
        "portable": True,
        "isolated_install": True,
        "provider_neutral": True,
        "target_repository_mutation": False,
        "source_repository": AER_REPOSITORY,
        "source_ref": source_ref,
        "source_commit": source_commit or _git_head(root),
        "mutable_state_excluded": True,
        "files": records,
    }

def build(root: Path, output: Path, source_commit: str | None = None, source_ref: str = AER_BRANCH) -> Path:
    files = iter_source_files(root)
    manifest = make_manifest(root, files, source_commit=source_commit, source_ref=source_ref)
    if not manifest["source_commit"]:
        raise SystemExit("bundle source commit could not be pinned; use --source-commit")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for source in files:
            archive.write(source, f"{PAYLOAD_ROOT}/{source.relative_to(root).as_posix()}")
        archive.write(root / "aer_cli.py", "aer_cli.py")
        archive.writestr(f"{PAYLOAD_ROOT}/PORTABLE_BUNDLE.txt", "AER portable bundle\nInstallation is user-scoped and repository-isolated.\nVersion and exact source commit are pinned in the manifest.\n")
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
        if manifest.get("target_repository_mutation") is not False:
            raise SystemExit("bundle is not marked repository-isolated")
        if not manifest.get("version") or not manifest.get("source_commit"):
            raise SystemExit("bundle must carry a version and exact source commit pin")
        root = Path(tempfile.mkdtemp(prefix="aer-verify-"))
        try:
            safe_extract(archive, root)
            for record in manifest.get("files", []):
                path = root / PAYLOAD_ROOT / record["path"]
                if not path.is_file() or sha256_file(path) != record["sha256"]:
                    raise SystemExit(f"bundle integrity failure: {record['path']}")
            if not (root / "aer_cli.py").is_file():
                raise SystemExit("bundle launcher is missing: aer_cli.py")
            return manifest
        finally:
            shutil.rmtree(root, ignore_errors=True)

def _copy_tree_without_mutable_state(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        rel = item.relative_to(source)
        if any(part in EXCLUDED_PARTS for part in rel.parts) or (item.is_file() and item.name in MUTABLE_FILE_NAMES):
            continue
        target = destination / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

def _copy_payload(payload: Path, version_root: Path) -> None:
    version_root.mkdir(parents=True, exist_ok=True)
    for name in (".ai-harness", "portable"):
        source = payload / name
        if source.is_dir():
            _copy_tree_without_mutable_state(source, version_root / name)
    skill = payload / "skills" / "ai-coding-orchestrator"
    if skill.is_dir():
        _copy_tree_without_mutable_state(skill, version_root / "skills" / "ai-coding-orchestrator")
    shutil.copy2(payload.parent / "aer_cli.py", version_root / "aer_cli.py")

def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)

def _set_current(root: Path, version_root: Path) -> None:
    current = root / "current"
    staged = root / ".current.tmp"
    if staged.exists() or staged.is_symlink():
        shutil.rmtree(staged) if staged.is_dir() and not staged.is_symlink() else staged.unlink()
    try:
        staged.symlink_to(version_root, target_is_directory=True)
        if current.exists() or current.is_symlink():
            shutil.rmtree(current) if current.is_dir() and not current.is_symlink() else current.unlink()
        staged.replace(current)
    except OSError:
        temp_dir = root / ".current-copy.tmp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        _copy_tree_without_mutable_state(version_root, temp_dir)
        if current.exists() or current.is_symlink():
            shutil.rmtree(current) if current.is_dir() and not current.is_symlink() else current.unlink()
        temp_dir.replace(current)

def _skill_destinations() -> dict[str, Path]:
    return {
        "agents": Path.home() / ".agents" / "skills" / "ai-coding-orchestrator",
        "claude": Path.home() / ".claude" / "skills" / "ai-coding-orchestrator",
        "gemini": Path.home() / ".gemini" / "skills" / "ai-coding-orchestrator",
    }

def _sync_skills(source: Path, mode: str) -> None:
    if mode == "none":
        return
    destinations = _skill_destinations()
    selected = list(destinations) if mode == "all" else ([name for name, path in destinations.items() if path.exists()] if mode == "auto" else [mode])
    for name in selected:
        _install_skill(source, destinations[name])

def _install_skill(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise SystemExit("bundle does not contain the canonical Agent Skill")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

def install(bundle: Path, install_skill: str = "agents", aer_home: Path | None = None) -> Path:
    manifest = verify_bundle(bundle)
    root = home_aer(aer_home)
    version = str(manifest["version"])
    version_root = root / "versions" / f"v{version}"
    temp = Path(tempfile.mkdtemp(prefix="aer-install-"))
    try:
        with zipfile.ZipFile(bundle) as archive:
            safe_extract(archive, temp)
        existing = version_root / "install.json"
        bundle_hash = sha256_file(bundle)
        if existing.is_file():
            prior = json.loads(existing.read_text(encoding="utf-8"))
            if prior.get("source_commit") != manifest["source_commit"] or prior.get("bundle_sha256") != bundle_hash:
                raise SystemExit(f"version {version} is already pinned to a different build; refusing overwrite")
        elif version_root.exists():
            raise SystemExit(f"version directory exists without a pin: {version_root}")
        _copy_payload(temp / PAYLOAD_ROOT, version_root)
        record = {
            "format": BUNDLE_FORMAT_VERSION,
            "version": version,
            "harness_version": manifest.get("harness_version"),
            "source_repository": manifest.get("source_repository"),
            "source_ref": manifest.get("source_ref"),
            "source_commit": manifest.get("source_commit"),
            "bundle_sha256": bundle_hash,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "repository_isolated": True,
        }
        _atomic_json(version_root / "install.json", record)
        _set_current(root, version_root)
        _atomic_json(root / "active.json", record)
        with (root / "history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "activate", **record}) + "\n")
        _sync_skills(temp / PAYLOAD_ROOT / "skills" / "ai-coding-orchestrator", install_skill)
        print(f"Installed and pinned AER {version} ({manifest['source_commit'][:12]})")
        print(f"Active installation: {root / 'current'}")
        print("Repository isolation: ON")
        return root / "current"
    finally:
        shutil.rmtree(temp, ignore_errors=True)

def _http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "aer-portable"})
    with urllib.request.urlopen(request, timeout=20) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("unexpected update metadata")
    return value

def _remote_target(ref: str) -> tuple[str, str]:
    commit_data = _http_json(f"https://api.github.com/repos/{AER_REPOSITORY}/commits/{ref}")
    commit = commit_data.get("sha")
    if not isinstance(commit, str) or not commit:
        raise SystemExit("remote AER commit could not be resolved")
    plugin = _http_json(f"https://raw.githubusercontent.com/{AER_REPOSITORY}/{commit}/.claude-plugin/plugin.json")
    version = plugin.get("version")
    if not isinstance(version, str) or not version:
        raise SystemExit("remote AER version could not be resolved")
    return version, commit

def _download_source(ref: str, destination: Path) -> Path:
    request = urllib.request.Request(f"https://api.github.com/repos/{AER_REPOSITORY}/zipball/{ref}", headers={"User-Agent": "aer-portable"})
    archive_path = destination / "source.zip"
    try:
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except urllib.error.URLError as exc:
        raise SystemExit(f"unable to download AER update source: {exc}") from exc
    root = destination / "source"
    root.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        safe_extract(archive, root)
    candidates = [p for p in root.iterdir() if p.is_dir()]
    if len(candidates) != 1:
        raise SystemExit("unexpected AER source archive layout")
    return candidates[0]

def check_update(aer_home: Path | None = None, ref: str = AER_BRANCH) -> dict:
    root = home_aer(aer_home)
    active = json.loads((root / "active.json").read_text(encoding="utf-8")) if (root / "active.json").is_file() else {}
    remote_version, remote_commit = _remote_target(ref)
    current_version = str(active.get("version") or "0.0.0")
    current_commit = str(active.get("source_commit") or "")
    update_available = (
        _version_tuple(remote_version) > _version_tuple(current_version)
        or (
            _version_tuple(remote_version) == _version_tuple(current_version)
            and bool(remote_commit)
            and remote_commit != current_commit
        )
    )
    return {
        "current_version": active.get("version"),
        "current_commit": active.get("source_commit"),
        "latest_version": remote_version,
        "latest_commit": remote_commit,
        "update_available": update_available,
    }

def rollback(aer_home: Path | None = None) -> Path:
    root = home_aer(aer_home)
    versions = []
    for path in (root / "versions").glob("v*") if (root / "versions").exists() else []:
        record = path / "install.json"
        if record.is_file():
            versions.append((json.loads(record.read_text(encoding="utf-8")), path))
    active = json.loads((root / "active.json").read_text(encoding="utf-8")) if (root / "active.json").is_file() else {}
    candidates = [item for item in versions if item[0].get("source_commit") != active.get("source_commit") or item[0].get("bundle_sha256") != active.get("bundle_sha256")]
    if not candidates:
        raise SystemExit("no previous immutable AER version is available")
    candidates.sort(key=lambda item: (_version_tuple(str(item[0].get("version", "0.0.0"))), str(item[0].get("installed_at", ""))))
    record, version_root = candidates[-1]
    _set_current(root, version_root)
    _atomic_json(root / "active.json", record)
    with (root / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": "rollback", **record}) + "\n")
    _sync_skills(version_root / "skills" / "ai-coding-orchestrator", "agents")
    print(f"Rolled back AER to {record['version']} ({record['source_commit'][:12]})")
    return root / "current"

def update(aer_home: Path | None = None, ref: str = AER_BRANCH, install_skill: str = "agents") -> Path:
    remote_version, remote_commit = _remote_target(ref)
    root = home_aer(aer_home)
    active = json.loads((root / "active.json").read_text(encoding="utf-8")) if (root / "active.json").is_file() else {}
    if remote_version == active.get("version") and remote_commit == active.get("source_commit"):
        raise SystemExit("AER is already up to date")
    with tempfile.TemporaryDirectory(prefix="aer-update-") as tmp:
        source = _download_source(remote_commit, Path(tmp))
        bundle = Path(tmp) / "aer-portable.zip"
        build(source, bundle, source_commit=remote_commit, source_ref=ref)
        install(bundle, install_skill, root)
    return root / "current"

def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AER portable distribution manager")
    sub = root.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--output", type=Path, default=Path("aer-portable.zip"))
    build_parser.add_argument("--source-commit", default=None)
    build_parser.add_argument("--source-ref", default=AER_BRANCH)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("bundle", type=Path)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("bundle", type=Path)
    install_parser.add_argument("--skill", choices=("none", "agents", "claude", "gemini", "all", "auto"), default="agents")
    install_parser.add_argument("--aer-home", type=Path, default=None)
    update_parser = sub.add_parser("update")
    update_parser.add_argument("--ref", default=AER_BRANCH)
    update_parser.add_argument("--skill", choices=("none", "agents", "claude", "gemini", "all", "auto"), default="agents")
    update_parser.add_argument("--aer-home", type=Path, default=None)
    check_parser = sub.add_parser("check-update")
    check_parser.add_argument("--ref", default=AER_BRANCH)
    check_parser.add_argument("--aer-home", type=Path, default=None)
    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--aer-home", type=Path, default=None)
    return root

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "build":
        path = build(repo_root(), args.output, args.source_commit, args.source_ref)
        print(path)
    elif args.command == "verify":
        print(json.dumps(verify_bundle(args.bundle), indent=2, sort_keys=True))
    elif args.command == "install":
        install(args.bundle, args.skill, args.aer_home)
    elif args.command == "check-update":
        print(json.dumps(check_update(args.aer_home, args.ref), indent=2, sort_keys=True))
    elif args.command == "update":
        update(args.aer_home, args.ref, args.skill)
    elif args.command == "rollback":
        rollback(args.aer_home)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
