import tempfile
import unittest
from pathlib import Path

from portable.agency_codebase_context import CodebaseIndex
from portable.semantic_addressing import SymbolLocator


class SemanticAddressingTests(unittest.TestCase):
    def test_symbol_locator_resolves_stable_symbol_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = root / "service.py"
            service.write_text(
                "class Service:\n"
                "    def run(self):\n"
                "        return 'ok'\n",
                encoding="utf-8",
            )

            index = CodebaseIndex.build(root)
            locator = SymbolLocator(index)

            matches = locator.find("Service")
            self.assertEqual(len(matches), 1)
            address = matches[0]
            self.assertEqual(address.ref, "service.py::Service")
            self.assertEqual(address.line, 1)
            self.assertEqual(address.kind, "class")
            self.assertEqual(address.snapshot_digest, index.digest())
            self.assertEqual(locator.resolve(address.ref), address)

    def test_symbol_locator_keeps_ambiguous_symbols_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("class Handler:\n    pass\n", encoding="utf-8")
            (root / "b.py").write_text("class Handler:\n    pass\n", encoding="utf-8")

            locator = SymbolLocator(CodebaseIndex.build(root))
            matches = locator.find("Handler")

            self.assertEqual(
                [item.ref for item in matches],
                ["a.py::Handler", "b.py::Handler"],
            )
            self.assertIsNone(locator.resolve("Handler"))
            self.assertEqual(locator.resolve("b.py::Handler").path, "b.py")

    def test_symbol_locator_exposes_existing_graph_relationships(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "base.py").write_text(
                "class Base:\n    pass\n", encoding="utf-8"
            )
            (root / "service.py").write_text(
                "from base import Base\n\n"
                "class Service(Base):\n"
                "    def run(self):\n"
                "        return 'ok'\n",
                encoding="utf-8",
            )

            index = CodebaseIndex.build(root)
            address = SymbolLocator(index).resolve("service.py::Service")
            self.assertIsNotNone(address)

            related = SymbolLocator(index).related(address)
            self.assertTrue(
                any(
                    item["target"] == "base.py" and item["kind"] == "implements"
                    for item in related
                )
            )


if __name__ == "__main__":
    unittest.main()
