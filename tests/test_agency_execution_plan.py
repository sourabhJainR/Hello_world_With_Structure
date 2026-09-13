import unittest

from portable.agency_execution_plan import SpecialistWork, build_plan, detect_conflicts


class ExecutionPlanTests(unittest.TestCase):
    def test_read_only_specialists_can_share_wave(self):
        plan = build_plan(
            [
                SpecialistWork("research", "support", read_paths=("src/a.py",)),
                SpecialistWork("review", "reviewer", read_paths=("src/a.py",)),
            ]
        )
        self.assertEqual(len(plan.waves), 1)
        self.assertFalse(plan.waves[0].mutation)
        self.assertFalse(plan.has_conflicts)

    def test_overlapping_mutations_are_conflicted_and_serialized(self):
        work = [
            SpecialistWork("builder-a", "primary", "bounded", write_paths=("src/a.py",)),
            SpecialistWork("builder-b", "support", "serialized", write_paths=("src/a.py",)),
        ]
        conflicts = detect_conflicts(work)
        self.assertEqual(conflicts[0].paths, ("src/a.py",))
        plan = build_plan(work)
        self.assertEqual(len(plan.waves), 2)
        self.assertTrue(all(w.mutation for w in plan.waves))

    def test_read_write_overlap_is_conflict(self):
        work = [
            SpecialistWork("builder", "primary", "bounded", write_paths=("src/a.py",)),
            SpecialistWork("reviewer", "reviewer", read_paths=("src/a.py",)),
        ]
        self.assertTrue(build_plan(work).has_conflicts)
        self.assertEqual(len(build_plan(work).waves), 2)

    def test_dependency_orders_work(self):
        plan = build_plan(
            [
                SpecialistWork("builder", "primary", "bounded", write_paths=("src/a.py",)),
                SpecialistWork("reviewer", "reviewer", read_paths=("src/a.py",), depends_on=("builder",)),
            ]
        )
        positions = {name: i for i, wave in enumerate(plan.waves) for name in wave.specialists}
        self.assertLess(positions["builder"], positions["reviewer"])

    def test_missing_dependency_is_blocked(self):
        plan = build_plan([SpecialistWork("builder", "primary", "bounded", write_paths=("src/a.py",), depends_on=("missing",))])
        self.assertTrue(plan.blocked)

    def test_invalid_read_only_write_declaration_is_rejected(self):
        with self.assertRaises(ValueError):
            SpecialistWork("bad", "support", "read-only", write_paths=("src/a.py",))

    def test_plan_digest_is_deterministic(self):
        work = [
            SpecialistWork("b", "support", "bounded", write_paths=("src/b.py",)),
            SpecialistWork("a", "primary", read_paths=("src/a.py",)),
        ]
        self.assertEqual(build_plan(work).digest(), build_plan(tuple(reversed(work))).digest())


if __name__ == "__main__":
    unittest.main()
