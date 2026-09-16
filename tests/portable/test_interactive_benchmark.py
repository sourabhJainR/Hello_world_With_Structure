import unittest

from portable.interactive_benchmark import InteractiveBenchmark, KeyDoorEnvironment


class InteractiveBenchmarkTests(unittest.TestCase):
    def test_episode_runs_interactively_and_is_deterministic(self):
        benchmark = InteractiveBenchmark(max_steps=8)

        def policy(observation, actions):
            progress = int(observation.get("sequence_progress", 0))
            if progress == 0:
                return "red"
            if progress == 1:
                return "blue"
            return "open"

        env_a = KeyDoorEnvironment(("red", "blue"), task_seed=7)
        env_b = KeyDoorEnvironment(("red", "blue"), task_seed=7)
        first = benchmark.run_episode("train-a", env_a, policy)
        second = benchmark.run_episode("train-a", env_b, policy)
        self.assertTrue(first.success)
        self.assertEqual(first.action_trace, second.action_trace)
        self.assertEqual(first.digest, second.digest)

    def test_invalid_policy_action_is_rejected(self):
        benchmark = InteractiveBenchmark(max_steps=3)
        with self.assertRaises(ValueError):
            benchmark.run_episode("bad", KeyDoorEnvironment(("red",)), lambda observation, actions: "missing")

    def test_hidden_transfer_is_reported_separately(self):
        benchmark = InteractiveBenchmark(max_steps=8)

        def policy(observation, actions):
            progress = int(observation.get("sequence_progress", 0))
            if progress == 0:
                return "red"
            if progress == 1:
                return "blue"
            return "open"

        tasks = [
            ("train-a", KeyDoorEnvironment(("red", "blue"), task_seed=1)),
            ("train-b", KeyDoorEnvironment(("red", "blue"), task_seed=2)),
            ("hidden-a", KeyDoorEnvironment(("red", "green"), task_seed=3)),
        ]
        result = benchmark.run_suite(tasks, policy, training_count=2)
        self.assertAlmostEqual(result.success_rate, 2 / 3)
        self.assertEqual(result.transfer_rate, 0.0)
        self.assertAlmostEqual(result.generalization_gap, 0.5)

    def test_hidden_environment_parameters_are_not_exposed(self):
        env = KeyDoorEnvironment(("secret", "hidden"), task_seed=11)
        observation = env.reset()
        self.assertNotIn("secret", str(observation))
        self.assertNotIn("hidden", str(observation))


if __name__ == "__main__":
    unittest.main()
