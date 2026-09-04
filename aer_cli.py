#!/usr/bin/env python3
"""Stable, self-bootstrapping AER command-line entry point.

The launcher works from a source checkout, an extracted portable bundle, or
next to a downloaded GitHub Actions artifact. When ``portable`` is not beside
the launcher, it loads the runtime from the bundle's ``payload`` directory.

For convenience, ``python aer_cli.py <bundle.zip>`` is treated as
``python aer_cli.py install <bundle.zip>``.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_runtime_from(root: Path):
    runtime = root / "portable" / "aer_runtime.py"
    if not runtime.is_file():
        runtime = root / "payload" / "portable" / "aer_runtime.py"
    if not runtime.is_file():
        return None

    runtime_root = str(runtime.parent.parent)
    if runtime_root not in sys.path:
        sys.path.insert(0, runtime_root)

    spec = importlib.util.spec_from_file_location("portable.aer_runtime", runtime)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load AER runtime: {runtime}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_runtime_from_bundle(bundle: Path):
    """Extract only the portable runtime from a bundle/artifact ZIP."""
    temp_root = Path(tempfile.mkdtemp(prefix="aer-cli-runtime-"))
    try:
        with zipfile.ZipFile(bundle) as archive:
            names = {name.rstrip("/") for name in archive.namelist()}
            runtime_name = "payload/portable/aer_runtime.py"
            if runtime_name not in names:
                # A downloaded GitHub artifact normally wraps aer-portable.zip.
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

    # When invoked from a downloaded artifact, the CLI is beside the bundle
    # rather than beside the Python package. Load the runtime from that bundle.
    bundle_candidates = [Path(arg).expanduser() for arg in argv if not arg.startswith("-")]
    for candidate in bundle_candidates:
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            return _load_runtime_from_bundle(candidate.resolve())

    raise SystemExit(
        "AER runtime not found. Run from the AER source checkout or portable bundle, "
        "or provide an AER .zip bundle."
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # Friendly shorthand for the common downloaded-bundle flow.
    if len(args) == 1 and Path(args[0]).suffix.lower() == ".zip":
        args = ["install", *args]

    runtime, temp_root = _load_runtime(args)
    try:
        return int(runtime.main(args))
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
