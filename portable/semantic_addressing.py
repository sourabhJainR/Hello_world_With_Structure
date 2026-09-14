"""Stable semantic addresses over the canonical CodebaseIndex.

This module is intentionally an addressing layer, not a second retrieval engine.
It gives agents Serena-style symbol references while keeping indexing, graph
construction and retrieval owned by ``portable.agency_codebase_context``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .agency_codebase_context import CodebaseIndex, Symbol


@dataclass(frozen=True)
class SymbolAddress:
    """Stable-enough semantic location for a symbol within a repository snapshot."""

    path: str
    symbol: str
    kind: str
    line: int
    snapshot_digest: str

    @property
    def ref(self) -> str:
        return f"{self.path}::{self.symbol}"


class SymbolLocator:
    """Resolve symbols against the canonical graph-aware codebase index."""

    def __init__(self, index: CodebaseIndex) -> None:
        self.index = index

    def find(self, symbol: str, *, path: str | None = None) -> tuple[SymbolAddress, ...]:
        needle = symbol.casefold()
        matches: list[SymbolAddress] = []
        digest = self.index.digest()
        records: Iterable[tuple[str, object]] = self.index.files.items()
        for record_path, record in records:
            if path is not None and record_path != path:
                continue
            for item in record.symbols:
                if item.name.casefold() != needle:
                    continue
                matches.append(
                    SymbolAddress(
                        path=item.path,
                        symbol=item.name,
                        kind=item.kind,
                        line=item.line,
                        snapshot_digest=digest,
                    )
                )
        return tuple(sorted(matches, key=lambda x: (x.path, x.line, x.symbol)))

    def resolve(self, ref: str) -> SymbolAddress | None:
        """Resolve ``path::symbol`` and reject malformed or stale paths."""
        if "::" not in ref:
            return None
        path, symbol = ref.split("::", 1)
        if not path or not symbol:
            return None
        matches = self.find(symbol, path=path)
        return matches[0] if matches else None

    def related(self, address: SymbolAddress) -> tuple[dict[str, object], ...]:
        """Return graph edges touching the symbol's file.

        The graph remains owned by ``CodebaseIndex``; callers receive immutable
        dictionaries so the locator cannot mutate the index.
        """
        edges = self.index.neighbors(address.path)
        return tuple(
            {
                "source": edge.source_path,
                "target": edge.target_path,
                "kind": edge.kind,
                "confidence": edge.confidence,
                "reason": edge.reason,
                "source_symbol": edge.source_symbol,
                "target_symbol": edge.target_symbol,
            }
            for edge in edges
            if not edge.source_symbol or edge.source_symbol.casefold() == address.symbol.casefold()
            or not edge.target_symbol or edge.target_symbol.casefold() == address.symbol.casefold()
        )


__all__ = ["SymbolAddress", "SymbolLocator"]
