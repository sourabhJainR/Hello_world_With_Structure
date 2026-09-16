import unittest

from scripts.validate_interactive_docs import validate


class InteractiveDocumentationTests(unittest.TestCase):
    def test_interactive_documentation_contract(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
