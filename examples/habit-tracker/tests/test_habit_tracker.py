import unittest
from datetime import date, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from app import HabitTracker


class HabitTrackerTests(unittest.TestCase):
    def test_streak_for_consecutive_days(self):
        tracker = HabitTracker()
        habit = tracker.add("Read")
        today = date(2026, 8, 31)
        for offset in range(3):
            tracker.record("Read", today - timedelta(days=offset))
        self.assertEqual(habit.streak(today), 3)

    def test_missed_day_breaks_streak(self):
        tracker = HabitTracker()
        habit = tracker.add("Read")
        today = date(2026, 8, 31)
        tracker.record("Read", today)
        tracker.record("Read", today - timedelta(days=2))
        self.assertEqual(habit.streak(today), 1)

    def test_duplicate_habit_rejected(self):
        tracker = HabitTracker()
        tracker.add("Read")
        with self.assertRaises(ValueError):
            tracker.add("Read")

    def test_blank_habit_rejected(self):
        with self.assertRaises(ValueError):
            HabitTracker().add(" ")


if __name__ == "__main__":
    unittest.main()
