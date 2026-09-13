"""AER specialist registry and deterministic routing helpers."""
from __future__ import annotations
import json, re
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "agency" / "registry.json"


def load_registry(path=DEFAULT_REGISTRY):
    p = Path(path)
    if not p.exists(): return {"schema_version":"1.0","agents":[]}
    return json.loads(p.read_text(encoding="utf-8"))


def _tokens(text):
    return set(re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", text.lower()))


def rank(task: str, registry=None, limit: int = 8):
    """Return candidate specialists; this is routing evidence, not authority."""
    registry = registry or load_registry()
    query = _tokens(task)
    scored = []
    for agent in registry.get("agents", []):
        hay = " ".join([agent.get("name",""), agent.get("description",""), agent.get("division","")])
        score = len(query & _tokens(hay))
        scored.append({"score":score,"name":agent.get("name"),"division":agent.get("division"),"file":agent.get("file"),"description":agent.get("description","")})
    return sorted(scored, key=lambda x:(-x["score"], x["division"], x["name"] or ""))[:limit]
