import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from learning import evolve_run, trusted_advice


class LearningTests(unittest.TestCase):
    def _write_run(self, root: Path, run_id: str, review: str, completed: bool = True) -> Path:
        run_dir = root / '.ai-harness' / 'runs' / run_id
        run_dir.mkdir(parents=True)
        (run_dir / 'manifest.json').write_text(json.dumps({
            'run_id': run_id, 'status': 'completed' if completed else 'failed',
            'task': 'Fix export duplication',
            'intent_digest': 'intent-1',
            'validation': {'passed': completed},
        }), encoding='utf-8')
        (run_dir / 'review.output.md').write_text(review, encoding='utf-8')
        return run_dir

    def test_repeated_wins_become_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'learning': {'min_observations_for_promotion': 3, 'min_success_rate_for_promotion': 0.75, 'stale_after_days': 120, 'max_memory_items': 250}}
            for i in range(3):
                run = self._write_run(root, f'r{i}', 'DO: preserve the existing export seam.', True)
                result = evolve_run(run, config)
            self.assertEqual(result['trusted'], 1)
            advice = trusted_advice(root)
            self.assertEqual(advice[0]['status'], 'trusted')

    def test_failed_observation_does_not_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'learning': {'min_observations_for_promotion': 3, 'min_success_rate_for_promotion': 0.75, 'stale_after_days': 120, 'max_memory_items': 250}}
            for i in range(3):
                run = self._write_run(root, f'r{i}', "DON'T: bypass existing validation.", i == 0)
                evolve_run(run, config)
            self.assertEqual(trusted_advice(root), [])

    def test_skill_refinement_is_proposal_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'learning': {'min_observations_for_promotion': 1, 'min_success_rate_for_promotion': 1.0, 'stale_after_days': 120, 'max_memory_items': 250}}
            run = self._write_run(root, 'r1', 'DO: keep the change local.', True)
            result = evolve_run(run, config)
            self.assertEqual(result['proposal_count'], 1)
            proposal = json.loads((root / '.ai-harness' / 'learning' / 'skill-proposals.jsonl').read_text().splitlines()[0])
            self.assertFalse(proposal['executable'])
            self.assertTrue(proposal['requires_eval'])
            self.assertTrue(proposal['requires_review'])

    def test_immutable_topics_never_generate_executable_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'learning': {'min_observations_for_promotion': 1, 'min_success_rate_for_promotion': 1.0, 'stale_after_days': 120, 'max_memory_items': 250}}
            run = self._write_run(root, 'r1', 'DO: repository_rules must always win.', True)
            result = evolve_run(run, config)
            self.assertEqual(result['trusted'], 1)
            advice = trusted_advice(root, topic='repository_rules')
            self.assertEqual(advice[0]['application'], 'advisory-only')


if __name__ == '__main__':
    unittest.main()
