#!/usr/bin/env python3
"""Production entrypoint with graph-agent orchestration enabled first."""
from __future__ import annotations

import runpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# engine.py imports runtime modules while it is loading. runtime/__init__.py
# therefore cannot safely install the bridge during that first import. Invoke
# the bootstrap once more after engine is fully initialized, then run the
# unchanged production launcher.
import engine
from runtime import _install_graph_team_bridge

_install_graph_team_bridge()
runpy.run_path(str(ROOT / "run_legacy.py"), run_name="__main__")
