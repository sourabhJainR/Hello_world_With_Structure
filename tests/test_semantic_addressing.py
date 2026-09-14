from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex
from portable.semantic_addressing import SymbolLocator


def test_symbol_locator_resolves_stable_symbol_reference(tmp_path: Path):
    service = tmp_path / "service.py"
    service.write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return 'ok'\n",
        encoding="utf-8",
    )

    index = CodebaseIndex.build(tmp_path)
    locator = SymbolLocator(index)

    matches = locator.find("Service")
    assert len(matches) == 1
    address = matches[0]
    assert address.ref == "service.py::Service"
    assert address.line == 1
    assert address.kind == "class"
    assert address.snapshot_digest == index.digest()

    resolved = locator.resolve(address.ref)
    assert resolved == address


def test_symbol_locator_keeps_ambiguous_symbols_explicit(tmp_path: Path):
    (tmp_path / "a.py").write_text("class Handler:\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("class Handler:\n    pass\n", encoding="utf-8")

    locator = SymbolLocator(CodebaseIndex.build(tmp_path))
    matches = locator.find("Handler")

    assert [item.ref for item in matches] == ["a.py::Handler", "b.py::Handler"]
    assert locator.resolve("Handler") is None
    assert locator.resolve("b.py::Handler").path == "b.py"


def test_symbol_locator_exposes_existing_graph_relationships(tmp_path: Path):
    (tmp_path / "base.py").write_text("class Base:\n    pass\n", encoding="utf-8")
    (tmp_path / "service.py").write_text(
        "from base import Base\n\n"
        "class Service(Base):\n"
        "    def run(self):\n"
        "        return 'ok'\n",
        encoding="utf-8",
    )

    index = CodebaseIndex.build(tmp_path)
    address = SymbolLocator(index).resolve("service.py::Service")
    assert address is not None

    related = SymbolLocator(index).related(address)
    assert any(item["target"] == "base.py" and item["kind"] == "implements" for item in related)
