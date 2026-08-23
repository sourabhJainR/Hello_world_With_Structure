#!/usr/bin/env python3
"""Read a prompt file and append its contents as the final CLI argument."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic AI CLI provider bridge")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--", dest="separator", nargs="?")
    args, command = parser.parse_known_args()
    if not command:
        print("No provider command supplied", file=sys.stderr)
        return 2
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    try:
        result = subprocess.run(command + [prompt], text=True, check=False)
    except OSError as exc:
        print(f"Unable to start provider: {exc}", file=sys.stderr)
        return 127
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
