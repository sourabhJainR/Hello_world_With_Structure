"""Harness-side adapter from the append-only run journal to portable context."""
from __future__ import annotations

from pathlib import Path

from portable.context_graph import ContextGraph
from portable.run_context_projector import ProjectionResult, RunContextProjector
from runtime.run_journal import read_events, verify_chain


def project_verified_journal(run_dir: Path, run_id: str, graph: ContextGraph) -> ProjectionResult:
    chain = verify_chain(Path(run_dir))
    return RunContextProjector(graph).project(
        read_events(Path(run_dir)),
        run_id,
        chain_valid=bool(chain.get("passed")),
        chain_head=str(chain.get("head", "")),
    )


__all__ = ["project_verified_journal"]
