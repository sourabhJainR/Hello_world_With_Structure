from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class Habit:
    name: str
    completed_on: set[date] = field(default_factory=set)

    def record(self, when: date) -> None:
        self.completed_on.add(when)

    def streak(self, today: date | None = None) -> int:
        cursor = today or date.today()
        if cursor not in self.completed_on:
            cursor -= timedelta(days=1)
        count = 0
        while cursor in self.completed_on:
            count += 1
            cursor -= timedelta(days=1)
        return count


class HabitTracker:
    def __init__(self) -> None:
        self._habits: dict[str, Habit] = {}

    def add(self, name: str) -> Habit:
        key = name.strip()
        if not key:
            raise ValueError("habit name is required")
        if key in self._habits:
            raise ValueError("habit already exists")
        habit = Habit(key)
        self._habits[key] = habit
        return habit

    def record(self, name: str, when: date) -> None:
        self._habits[name].record(when)

    def active(self) -> list[Habit]:
        return sorted(self._habits.values(), key=lambda habit: habit.name.lower())


if __name__ == "__main__":
    tracker = HabitTracker()
    habit = tracker.add("Read")
    habit.record(date.today())
    print(f"{habit.name}: {habit.streak()} day streak")
