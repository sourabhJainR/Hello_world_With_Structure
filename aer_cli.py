#!/usr/bin/env python3
"""Stable AER command-line entry point.

The launcher bootstraps the repository/installation directory before importing
``portable`` so it works when invoked from any current working directory, both
from a source checkout and from an installed ``~/.aer/current`` bundle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from portable.aer_runtime import main


if __name__ == "__main__":
    raise SystemExit(main())
