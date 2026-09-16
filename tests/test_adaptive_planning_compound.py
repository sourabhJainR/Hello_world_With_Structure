import unittest

from portable.agency_adaptive_planning import EngineeringLesson, LessonOutcome, compound_lesson


class CompoundLessonTests(unittest.TestCase):
    def test_compounding_adds_evidence_and_tracks_recurrence(self) -> None:
        lesson = EngineeringLesson(
            "lesson-1", "graph-runtime", "retry loop failed", "external effect retried", "declare effect explicitly",
            evidence_ids=("ev-1",), prevention_rule="reject external retries"
        )
        outcome = LessonOutcome("lesson-1", prevented_recurrence=True, observed_again=True, evidence_ids=("ev-2",))
        compounded = compound_lesson(lesson, outcome)
        self.assertEqual(compounded.recurrence_count, 1)
        self.assertEqual(compounded.evidence_ids, ("ev-1", "ev-2"))
        self.assertEqual(compounded.prevention_rule, "reject external retries")

    def test_mismatched_outcome_is_rejected(self) -> None:
        lesson = EngineeringLesson("lesson-1", "general", "problem", "cause", "solution")
        with self.assertRaises(ValueError):
            compound_lesson(lesson, LessonOutcome("lesson-2", False))


if __name__ == "__main__":
    unittest.main()
