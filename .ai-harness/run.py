#!/usr/bin/env python3
"""Public launcher and import-safe compatibility surface."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Keep the historical launcher API available to tests and integrations. The
# legacy module guards its CLI entrypoint, so importing this module never
# consumes sys.argv or exits the process.
import run_legacy as _legacy
from run_legacy import *  # noqa: F401,F403

_original_make_run_dir = _legacy._original_make_run_dir
_original_build_prompt = _legacy._original_build_prompt
_original_run_task = _legacy._original_run_task
_original_run_validation = _legacy._original_run_validation
_session_dir = _legacy._session_dir
_knowledge = _legacy._knowledge
_intent_contract = _legacy._intent_contract
_capability_plan = _legacy._capability_plan
_repository_instructions = _legacy._repository_instructions

# Install graph orchestration only after engine has completed initialization.
# runtime.__init__ deliberately has no import-time side effects.
from runtime import _install_graph_team_bridge
_install_graph_team_bridge()

if __name__ == "__main__":
    raise SystemExit(_legacy.engine.main())
