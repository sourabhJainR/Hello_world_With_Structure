import unittest
from datetime import date, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from app import FinancialRecord, FinancialRegister


class FinancialRegisterTests(unittest.TestCase):
    def test_records_can_be_listed_and_sorted(self):
        register = FinancialRegister()
        today = date(2026, 8, 31)
        register.add(FinancialRecord("insurance", "Life", "Example Insurer", "POL-1", "docs/insurance", "family-contact", today))
        register.add(FinancialRecord("investment", "Fund", "Example Bank", "F-1", "docs/investments", "family-contact", today))
        self.assertEqual([r.kind for r in register.all()], ["insurance", "investment"])

    def test_stale_records_are_visible(self):
        register = FinancialRegister()
        today = date(2026, 8, 31)
        register.add(FinancialRecord("investment", "Fund", "Example Bank", "F-1", "docs/investments", "family-contact", today - timedelta(days=200)))
        self.assertEqual(len(register.stale(today)), 1)

    def test_current_records_are_not_stale(self):
        register = FinancialRegister()
        today = date(2026, 8, 31)
        register.add(FinancialRecord("investment", "Fund", "Example Bank", "F-1", "docs/investments", "family-contact", today - timedelta(days=30)))
        self.assertEqual(register.stale(today), [])

    def test_missing_reference_is_rejected(self):
        register = FinancialRegister()
        with self.assertRaises(ValueError):
            register.add(FinancialRecord("investment", "Fund", "Example Bank", "", "docs", "family-contact", date(2026, 8, 31)))

    def test_negative_staleness_window_is_rejected(self):
        with self.assertRaises(ValueError):
            FinancialRegister().stale(date(2026, 8, 31), -1)


if __name__ == "__main__":
    unittest.main()
