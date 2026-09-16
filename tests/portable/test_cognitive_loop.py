import tempfile
import unittest
from pathlib import Path

from portable.cognitive_loop import CognitiveLoop, CognitiveEpisode
from portable.cognitive_runtime import CognitiveRuntime
from portable.persistent_memory import PersistentMemory


class CognitiveLoopTests(unittest.TestCase):
    def test_episode_has_stable_identity_and_phase_history(self):
        episode = CognitiveEpisode.start("project-x", "task-1", "improve parser")
        episode.record_phase("observe")
        episode.record_phase("plan")
        receipt = episode.finish("success")
        self.assertEqual(receipt.project_key, "project-x")
        self.assertEqual(receipt.task_id, "task-1")
        self.assertEqual(receipt.status, "success")
        self.assertEqual(receipt.phases, ("observe", "plan"))
        self.assertTrue(receipt.episode_id)
        self.assertEqual(len(receipt.digest), 64)

    def test_loop_persists_episode_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            cognitive = CognitiveRuntime.create(memory, "project-x")
            loop = CognitiveLoop(cognitive)
            episode = loop.begin("project-x", "task-1", "learn")
            loop.observe(episode, {"event": "execution_started", "status": "running"})
            matches = cognitive.memory.search("project-x", "execution_started", limit=5)
            self.assertTrue(matches)

    def test_complete_marks_successful_episode_for_learning(self):
        loop = CognitiveLoop()
        episode = loop.begin("project-x", "task-1", "learn")
        receipt = loop.complete(episode, "accepted")
        self.assertEqual(receipt.phases, ("observe", "evaluate", "learn", "complete"))


if __name__ == "__main__":
    unittest.main()
