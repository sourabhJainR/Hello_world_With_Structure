from pathlib import Path

from portable.agent_capabilities import CapabilityFabric, PersistentMemory
from portable.agency_agent_capabilities import MemoryFact, MemoryStore
from portable.capability_fabric import CapabilityFabric as CapabilityFabricFacade
from portable.persistent_memory import PersistentMemory as PersistentMemoryFacade
from portable.repository_intelligence import RepositoryIntelligence


def test_capability_facade_uses_canonical_owner():
    assert issubclass(CapabilityFabricFacade, CapabilityFabric)
    assert CapabilityFabricFacade.default().discover()["memory"].name == "memory"


def test_persistent_memory_facade_uses_canonical_owner():
    assert issubclass(PersistentMemoryFacade, PersistentMemory)


def test_agency_memory_adapter_round_trips_through_canonical_store(tmp_path: Path):
    path = tmp_path / "memory.sqlite"
    store = MemoryStore(path)
    store.upsert(MemoryFact("language", "Python", confidence=0.9))
    store.upsert(MemoryFact("language", "Ruby", confidence=0.4))
    assert store.get("language").value == "Python"

    restored = MemoryStore(path)
    assert restored.get("language").value == "Python"


def test_repository_intelligence_is_budgeted_and_secret_aware(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("class Demo:\n    def run(self):\n        return 'ok'\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("api_key=super-secret-value-123456", encoding="utf-8")

    intelligence = RepositoryIntelligence(tmp_path)
    packed = intelligence.pack(token_budget=100, compress=True)

    paths = {item.path for item in packed.files}
    assert "main.py" in paths
    assert "ignored.txt" not in paths
    assert "secret.txt" not in paths
    assert "secret.txt" in packed.security_exclusions
    assert packed.token_estimate <= 100


def test_repository_intelligence_reuses_graph_aware_retrieval(tmp_path: Path):
    (tmp_path / "service.py").write_text("class Service:\n    def run(self):\n        return 'ok'\n", encoding="utf-8")
    intelligence = RepositoryIntelligence(tmp_path)
    context = intelligence.retrieve("Service run", token_budget=100)
    assert "service.py" in context.relevant_paths
    assert context.graph_trace is not None
