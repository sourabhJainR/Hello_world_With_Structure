#!/usr/bin/env python3
"""Stable, self-bootstrapping AER command-line entry point.

The launcher works from a source checkout, an extracted portable bundle, or
next to a downloaded GitHub Actions artifact. When ``portable`` is not beside
the launcher, it loads the runtime from the bundle's ``payload`` directory.

AER also activates its Claude Code plugin when Claude is available. The
portable runtime is kept provider-neutral; this launcher owns provider
integration so existing bundles remain usable.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "adaptive-ai-coding-orchestrator"
MARKETPLACE_NAME = "adaptive-ai-engineering"


def _load_runtime_from(root: Path):
    runtime = root / "portable" / "aer_runtime.py"
    if not runtime.is_file():
        runtime = root / "payload" / "portable" / "aer_runtime.py"
    if not runtime.is_file():
        return None

    runtime_root = str(runtime.parent.parent)
    if runtime_root not in sys.path:
        sys.path.insert(0, runtime_root)

    package = sys.modules.get("portable")
    if package is None:
        package = types.ModuleType("portable")
        package.__path__ = [runtime_root]
        sys.modules["portable"] = package

    spec = importlib.util.spec_from_file_location("portable.aer_runtime", runtime)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load AER runtime: {runtime}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def _load_runtime_from_bundle(bundle: Path):
    """Extract only the portable runtime from a bundle/artifact ZIP."""
    temp_root = Path(tempfile.mkdtemp(prefix="aer-cli-runtime-"))
    try:
        with zipfile.ZipFile(bundle) as archive:
            names = {name.rstrip("/") for name in archive.namelist()}
            runtime_name = "payload/portable/aer_runtime.py"
            if runtime_name not in names:
                nested = [
                    name for name in names
                    if name.lower().endswith(".zip") and Path(name).name.lower() == "aer-portable.zip"
                ]
                if len(nested) != 1:
                    raise SystemExit(
                        "unable to find portable AER runtime; expected payload/portable/aer_runtime.py "
                        "or an artifact containing aer-portable.zip"
                    )
                inner = temp_root / "aer-portable.zip"
                inner.write_bytes(archive.read(nested[0]))
                with zipfile.ZipFile(inner) as nested_archive:
                    if runtime_name not in {name.rstrip("/") for name in nested_archive.namelist()}:
                        raise SystemExit("aer-portable.zip does not contain payload/portable/aer_runtime.py")
                    nested_archive.extract(runtime_name, temp_root)
            else:
                archive.extract(runtime_name, temp_root)
        return _load_runtime_from(temp_root), temp_root
    except (OSError, zipfile.BadZipFile) as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise SystemExit(f"invalid AER bundle: {exc}") from exc


def _load_runtime(argv: list[str]):
    module = _load_runtime_from(_ROOT)
    if module is not None:
        return module, None

    bundle_candidates = [Path(arg).expanduser() for arg in argv if not arg.startswith("-")]
    for candidate in bundle_candidates:
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            return _load_runtime_from_bundle(candidate.resolve())

    raise SystemExit(
        "AER runtime not found. Run from the AER source checkout or portable bundle, "
        "or provide an AER .zip bundle."
    )


def _prepare_runtime_for_distribution(runtime) -> None:
    """Extend the provider-neutral runtime with bundled Claude metadata.

    Keeping this compatibility shim in the launcher avoids making the core
    runtime depend on Claude Code while ensuring the portable bundle contains
    the plugin manifest required for real Claude installation.
    """
    required = tuple(runtime.REQUIRED_PATHS)
    if ".claude-plugin" not in required:
        runtime.REQUIRED_PATHS = (*required, ".claude-plugin")

    original_copy_payload = runtime._copy_payload

    def copy_payload(payload: Path, version_root: Path) -> None:
        original_copy_payload(payload, version_root)
        source = payload / ".claude-plugin"
        if source.is_dir():
            runtime._copy_tree_without_mutable_state(source, version_root / ".claude-plugin")

    runtime._copy_payload = copy_payload


def _has_flag(args: list[str], flag: str) -> bool:
    return flag in args or any(value.startswith(flag + "=") for value in args)


def _claude_available() -> str | None:
    return shutil.which("claude")


def _claude_plugin_install(current_root: Path) -> None:
    """Register and install the bundled Claude plugin at user scope."""
    claude = _claude_available()
    if not claude:
        print("Claude Code not found on PATH; AER Claude integration was not activated.")
        return

    marketplace = current_root / ".claude-plugin" / "marketplace.json"
    plugin_manifest = current_root / ".claude-plugin" / "plugin.json"
    if not marketplace.is_file() or not plugin_manifest.is_file():
        print("AER Claude integration skipped: plugin metadata is missing from the installed bundle.")
        return

    def run(*command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [claude, *command],
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    try:
        added = run("plugin", "marketplace", "add", str(current_root), "--scope", "user")
        added_output = (added.stdout + added.stderr).strip()
        if added.returncode != 0 and "already" not in added_output.lower():
            print("Claude marketplace registration warning:", added_output)

        installed = run("plugin", "install", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}", "--scope", "user")
        install_output = (installed.stdout + installed.stderr).strip()
        if installed.returncode != 0 and not any(
            phrase in install_output.lower() for phrase in ("already installed", "already enabled")
        ):
            print("Claude plugin installation warning:", install_output)
            return

        print(f"Claude integration active: {PLUGIN_NAME}@{MARKETPLACE_NAME}")
        print("Restart Claude Code or run /reload-plugins to load the skill and hook.")
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Claude integration could not be activated: {exc}")


def _should_activate_claude(args: list[str]) -> bool:
    if not args or args[0] not in {"install", "update"}:
        return False
    skill = None
    for index, value in enumerate(args):
        if value == "--skill" and index + 1 < len(args):
            skill = args[index + 1]
        elif value.startswith("--skill="):
            skill = value.split("=", 1)[1]
    return skill in {"claude", "all", "auto"} or (skill is None and _claude_available() is not None)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) == 1 and Path(args[0]).suffix.lower() == ".zip":
        args = ["install", *args, "--skill", "auto"]
    elif args and args[0] in {"install", "update"} and not _has_flag(args, "--skill"):
        args = [*args, "--skill", "auto"]

    runtime, temp_root = _load_runtime(args)
    _prepare_runtime_for_distribution(runtime)
    try:
        result = int(runtime.main(args))
        if result == 0 and _should_activate_claude(args):
            aer_home = Path.home() / ".aer"
            current = aer_home / "current"
            if current.exists():
                _claude_plugin_install(current)
        return result
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
