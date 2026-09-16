"""Project verified execution-journal facts into the durable ContextGraph.

The portable projector is deliberately independent of the harness journal
implementation. A harness-side adapter can verify/read the journal and pass
only verified events here. This keeps the portable runtime dependency-free and
prevents journal internals from becoming an orchestration dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

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
    """Turn already-verified journal milestones into durable graph context."""

    def __init__(self, graph: ContextGraph) -> None:
        if not isinstance(graph, ContextGraph):
            raise TypeError("graph must be a ContextGraph")
        self.graph = graph

    def project(self, events: Sequence[Mapping[str, Any]], run_id: str, *, chain_valid: bool, chain_head: str = "") -> ProjectionResult:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id is required")
        if not chain_valid:
            return ProjectionResult(False, run_id, len(events), 0, 0, "", "journal chain verification failed")
        run_node_id = f"run:{run_id}"
        event_rows = [dict(row) for row in events]
        self.graph.upsert_node(ContextNode(run_node_id, "run", run_id, "run_journal", 1.0, self._run_fields(event_rows, chain_head)))
        nodes = 1
        edges = 0
        for row in event_rows:
            event_name = str(row.get("event", ""))
            sequence = int(row.get("sequence", 0))
            if event_name not in {"phase.start", "phase.finish", "provider.finish", "run.error", "run.crash", "run.finish"}:
                continue
            event_id = f"run-event:{run_id}:{sequence}"
            properties = self._safe_fields(event_name, row)
            node_kind = "risk" if event_name in {"run.error", "run.crash"} else "outcome" if event_name in {"provider.finish", "run.finish"} else "phase"
            self.graph.upsert_node(ContextNode(event_id, node_kind, self._label(event_name, properties), "run_journal", 1.0, properties))
            nodes += 1
            self.graph.link(run_node_id, "observed", event_id, source="run_journal", confidence=1.0, properties={"sequence": sequence})
            edges += 1
        digest_payload = {"run_id": run_id, "chain_head": chain_head, "events": len(event_rows), "nodes": nodes, "edges": edges}
        digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
        return ProjectionResult(True, run_id, len(event_rows), nodes, edges, digest)

    @staticmethod
    def _safe_fields(event_name: str, row: Mapping[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {"sequence": int(row.get("sequence", 0))}
        if event_name in {"phase.start", "phase.finish"} and row.get("phase"):
            fields["phase"] = str(row["phase"])
        elif event_name == "provider.finish":
            for key in ("phase", "exit_code"):
                if row.get(key) is not None:
                    fields[key] = row[key]
        elif event_name in {"run.error", "run.crash"} and row.get("error_type"):
            fields["error_type"] = str(row["error_type"])
        elif event_name == "run.finish" and row.get("status"):
            fields["status"] = str(row["status"])
        return fields

    @staticmethod
    def _label(event_name: str, fields: Mapping[str, Any]) -> str:
        suffix = ", ".join(f"{key}={value}" for key, value in sorted(fields.items()) if key != "sequence")
        return event_name if not suffix else f"{event_name}: {suffix}"

    @classmethod
    def _run_fields(cls, events: Sequence[Mapping[str, Any]], chain_head: str) -> dict[str, Any]:
        finish = next((row for row in reversed(events) if row.get("event") == "run.finish"), None)
        fields: dict[str, Any] = {"events": len(events), "chain_head": chain_head}
        if finish and finish.get("status"):
            fields["status"] = str(finish["status"])
        return fields


__all__ = ["ProjectionResult", "RunContextProjector"]
