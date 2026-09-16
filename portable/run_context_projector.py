"""Project verified execution-journal facts into the durable ContextGraph.

The projector is intentionally one-way and evidence-bound: a valid hash chain
may enrich context, while a corrupt journal produces no graph mutation. Only a
small allowlisted set of operational fields is copied; arbitrary journal
payloads are never promoted into context.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .context_graph import ContextGraph, ContextNode


@dataclass(frozen=True)
class ProjectionResult:
    accepted: bool
    run_id: str
    events: int
    nodes: int
    edges: int
    digest: str
    reason: str = ""


class RunContextProjector:
    """Turn verified run-journal milestones into durable graph context."""

    def __init__(self, graph: ContextGraph) -> None:
        if not isinstance(graph, ContextGraph):
            raise TypeError("graph must be a ContextGraph")
        self.graph = graph

    def project(self, run_dir: Path, run_id: str) -> ProjectionResult:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id is required")
        journal = Path(run_dir)
        journal_module = self._journal_module()
        chain = journal_module.verify_chain(journal)
        if not chain.get("passed"):
            return ProjectionResult(False, run_id, int(chain.get("events", 0)), 0, 0, "", "journal chain verification failed")
        events = journal_module.read_events(journal)
        run_node_id = f"run:{run_id}"
        run_fields = self._run_fields(events, chain)
        self.graph.upsert_node(ContextNode(run_node_id, "run", run_id, "run_journal", 1.0, run_fields))
        nodes = 1
        edges = 0
        for row in events:
            event_name = str(row.get("event", ""))
            sequence = int(row.get("sequence", 0))
            if event_name in {"phase.start", "phase.finish", "provider.finish", "run.error", "run.crash", "run.finish"}:
                event_id = f"run-event:{run_id}:{sequence}"
                label = self._label(event_name, row)
                properties = self._safe_fields(event_name, row)
                node_kind = "risk" if event_name in {"run.error", "run.crash"} else "outcome" if event_name in {"provider.finish", "run.finish"} else "phase"
                self.graph.upsert_node(ContextNode(event_id, node_kind, label, "run_journal", 1.0, properties))
                nodes += 1
                self.graph.link(run_node_id, "observed", event_id, source="run_journal", confidence=1.0, properties={"sequence": sequence})
                edges += 1
        digest_payload = {"run_id": run_id, "chain_head": chain.get("head", ""), "nodes": nodes, "edges": edges}
        digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
        return ProjectionResult(True, run_id, len(events), nodes, edges, digest)

    @staticmethod
    def _journal_module():
        root = Path(__file__).resolve().parents[1] / ".ai-harness"
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from runtime import run_journal
        return run_journal

    @staticmethod
    def _safe_fields(event_name: str, row: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {"sequence": int(row.get("sequence", 0))}
        if event_name == "phase.start" or event_name == "phase.finish":
            if row.get("phase"):
                fields["phase"] = str(row["phase"])
        elif event_name == "provider.finish":
            for key in ("phase", "exit_code"):
                if row.get(key) is not None:
                    fields[key] = row[key]
        elif event_name in {"run.error", "run.crash"}:
            if row.get("error_type"):
                fields["error_type"] = str(row["error_type"])
        elif event_name == "run.finish":
            if row.get("status"):
                fields["status"] = str(row["status"])
        return fields

    @classmethod
    def _label(cls, event_name: str, row: dict[str, Any]) -> str:
        fields = cls._safe_fields(event_name, row)
        suffix = ", ".join(f"{key}={value}" for key, value in sorted(fields.items()) if key != "sequence")
        return event_name if not suffix else f"{event_name}: {suffix}"

    @classmethod
    def _run_fields(cls, events: list[dict[str, Any]], chain: dict[str, Any]) -> dict[str, Any]:
        finish = next((row for row in reversed(events) if row.get("event") == "run.finish"), None)
        fields: dict[str, Any] = {"events": len(events), "chain_head": str(chain.get("head", ""))}
        if finish and finish.get("status"):
            fields["status"] = str(finish["status"])
        return fields


__all__ = ["ProjectionResult", "RunContextProjector"]
