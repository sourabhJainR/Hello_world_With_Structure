import sys
import tempfile
import time
import unittest
from pathlib import Path

from portable.local_workbench import LocalWorkbench, WorkReceipt, packet


class LocalWorkbenchTests(unittest.TestCase):
    def test_independent_read_only_packets_run_in_parallel(self):
        with tempfile.TemporaryDirectory() as temp:
            started = []

            def runner(item):
                started.append(item.id)
                time.sleep(0.05)
                now = time.time()
                return WorkReceipt(item.id, item.mission_id, "completed", 0, "", "", 50, now, now, "test")

            packets = [
                packet("one", ["noop"], mission_id="m", packet_id="a"),
                packet("two", ["noop"], mission_id="m", packet_id="b"),
            ]
            result = LocalWorkbench(temp, max_workers=2, runner=runner).run(packets)
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(started), 2)

    def test_mutating_packets_are_serialized(self):
        with tempfile.TemporaryDirectory() as temp:
            active = 0
            peak = 0

            def runner(item):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                time.sleep(0.03)
                active -= 1
                now = time.time()
                return WorkReceipt(item.id, item.mission_id, "completed", 0, "", "", 30, now, now, "test")

            packets = [
                packet("one", ["noop"], mission_id="m", effect="mutating", packet_id="a"),
                packet("two", ["noop"], mission_id="m", effect="mutating", packet_id="b"),
            ]
            result = LocalWorkbench(temp, max_workers=4, runner=runner).run(packets)
            self.assertEqual(result.status, "completed")
            self.assertEqual(peak, 1)

    def test_dependencies_block_after_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            def runner(item):
                now = time.time()
                status = "failed" if item.id == "a" else "completed"
                return WorkReceipt(item.id, item.mission_id, status, 1 if status == "failed" else 0, "", "", 0, now, now, "test")

            packets = [
                packet("root", ["noop"], mission_id="m", packet_id="a"),
                packet("dependent", ["noop"], mission_id="m", dependencies=["a"], packet_id="b"),
            ]
            result = LocalWorkbench(temp, runner=runner).run(packets)
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.packets[1].status, "blocked")

    def test_command_runner_uses_workspace_and_no_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            marker = project / "marker.txt"
            result = LocalWorkbench(project).run([
                packet(
                    "write marker",
                    [sys.executable, "-c", "from pathlib import Path; Path('marker.txt').write_text('ok')"],
                    effect="mutating",
                    packet_id="write",
                )
            ])
            self.assertTrue(result.packets[0].succeeded)
            self.assertEqual(marker.read_text(encoding="utf-8"), "ok")

    def test_command_cwd_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            work = packet("escape", [sys.executable, "-c", "print('x')"], cwd="..")
            result = LocalWorkbench(temp).run([work])
            self.assertEqual(result.status, "failed")
            self.assertIn("cwd", result.packets[0].error.lower())


if __name__ == "__main__":
    unittest.main()
