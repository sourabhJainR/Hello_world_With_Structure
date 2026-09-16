"""Bounded workspace sharing over the canonical ContextGraph.

Private graph nodes can be attached to a workspace for ownership bookkeeping,
but they are never returned as shared members. Explicit promotion creates a
new shared summary backed by evidence rather than exposing the private node.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

from .context_graph import ContextGraph, ContextNode


@dataclass(frozen=True)
class WorkspacePromotion:
    node_id: str
    workspace_id: str
    evidence: tuple[str, ...]


class WorkspaceContext:
    """Manage private/shared workspace relationships without another store."""

    def __init__(self, graph: ContextGraph) -> None:
        if not isinstance(graph, ContextGraph):
            raise TypeError("graph must be a ContextGraph")
        self.graph = graph

    def attach(self, workspace_id: str, node_id: str) -> None:
        workspace = self.graph.get_node(workspace_id)
        node = self.graph.get_node(node_id)
        if workspace is None or workspace.kind != "workspace":
            raise KeyError("unknown workspace")
        if node is None:
            raise KeyError("unknown context node")
        relation = "private_member" if self._private(node) else "shared_member"
        self.graph.link(workspace_id, relation, node_id, source="workspace", confidence=1.0)

    def shared_members(self, workspace_id: str, *, limit: int = 50) -> tuple[ContextNode, ...]:
        workspace = self.graph.get_node(workspace_id)
        if workspace is None or workspace.kind != "workspace":
            raise KeyError("unknown workspace")
        nodes: list[ContextNode] = []
        for edge in self.graph.neighbors(workspace_id, relation="shared_member", direction="out", limit=limit):
            node = self.graph.get_node(edge.target_id)
            if node is not None and not self._private(node):
                nodes.append(node)
        return tuple(nodes)

    def promote(self, workspace_id: str, node_id: str, *, summary: str, evidence: Sequence[str]) -> ContextNode:
        workspace = self.graph.get_node(workspace_id)
        node = self.graph.get_node(node_id)
        if workspace is None or workspace.kind != "workspace":
            raise KeyError("unknown workspace")
        if node is None:
            raise KeyError("unknown context node")
        if not summary.strip():
            raise ValueError("summary is required")
        clean_evidence = tuple(dict.fromkeys(value.strip() for value in evidence if isinstance(value, str) and value.strip()))
        if not clean_evidence:
            raise ValueError("evidence is required for promotion")
        attached = self.graph.neighbors(workspace_id, direction="out", limit=200)
        if not any(edge.target_id == node_id and edge.relation in {"private_member", "shared_member"} for edge in attached):
            raise PermissionError("context node is not attached to workspace")
        seed = "|".join((workspace_id, node_id, summary.strip(), *clean_evidence))
        promotion_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        promoted = ContextNode(
            f"shared-summary:{promotion_id}",
            "shared_summary",
            summary.strip(),
            "workspace_promotion",
            min(1.0, node.confidence),
            {"evidence": list(clean_evidence), "promotion_token": promotion_id},
        )
        self.graph.upsert_node(promoted)
        self.graph.link(workspace_id, "shared_member", promoted.node_id, source="workspace_promotion", confidence=promoted.confidence, properties={"evidence": list(clean_evidence)})
        return promoted

    @staticmethod
    def _private(node: ContextNode) -> bool:
        return bool(node.properties.get("private", False)) or node.source.lower() == "private"


__all__ = ["WorkspaceContext", "WorkspacePromotion"]
