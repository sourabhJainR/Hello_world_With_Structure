import unittest

from portable.agency_multi_specialist import SpecialistResourceProfile, build_specialist_plan
from portable.agency_runtime import Assignment


class MultiSpecialistPlanTests(unittest.TestCase):
    def test_assignment_resources_drive_conflict_planning(self):
        assignments = [
            Assignment("builder", "primary", 100, ()),
            Assignment("reviewer", "reviewer", 90, ()),
        ]
        resources = {
            "builder": SpecialistResourceProfile("builder", write_paths=("src/a.py",), mutation_mode="bounded"),
            "reviewer": SpecialistResourceProfile("reviewer", read_paths=("src/a.py",)),
        }
        plan = build_specialist_plan(assignments, resources)
        self.assertEqual(len(plan.waves), 2)
        self.assertTrue(plan.has_conflicts)

    def test_default_profiles_are_safe_read_only(self):
        assignments = [Assignment("research", "support", 10, ())]
        plan = build_specialist_plan(assignments)
        self.assertEqual(plan.waves[0].specialists, ("research",))
        self.assertFalse(plan.waves[0].mutation)


if __name__ == "__main__":
    unittest.main()
