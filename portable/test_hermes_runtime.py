import tempfile
import unittest
from pathlib import Path

from portable.hermes_runtime import (
    ApprovalPolicy,
    DurableStore,
    LocalExecutor,
    ProviderRouter,
    ProviderSpec,
    SessionState,
    Skill,
    SkillRegistry,
    ToolRegistry,
    ToolSpec,
)


class HermesRuntimeTests(unittest.TestCase):
    def test_provider_router_selects_required_capability(self):
        router = ProviderRouter([
            ProviderSpec("cheap", "m1", capabilities=frozenset({"text"}), priority=1),
            ProviderSpec("vision", "m2", capabilities=frozenset({"text", "vision"}), priority=5),
        ])
        self.assertEqual(router.resolve({"vision"}).name, "vision")

    def test_skill_registry_ranks_relevant_skill(self):
        registry = SkillRegistry()
        registry.register(Skill("python-testing", "pytest and regression testing", "run tests", frozenset({"python", "testing"})))
        registry.register(Skill("docs", "documentation", "write docs", frozenset({"docs"})))
        self.assertEqual(registry.discover("python testing")[0].name, "python-testing")

    def test_tool_registry_requires_approval(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("safe.echo", "echo", lambda value: value))
        registry.register(ToolSpec("danger", "danger", lambda: "ok", requires_approval=True))
        self.assertEqual(registry.call("safe.echo", value="ok"), "ok")
        with self.assertRaises(PermissionError):
            registry.call("danger")
        self.assertEqual(registry.call("danger", approved=True), "ok")

    def test_durable_store_persists_and_searches(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DurableStore(Path(directory) / "state.db")
            store.save_session(SessionState("s1", "default", task_id="t1"))
            store.append_message("s1", "user", "fix authentication timeout")
            store.remember("default", "lesson", "preserve timeout behavior", "test", 0.9)
            self.assertEqual(store.search_sessions("authentication")[0]["session_id"], "s1")
            self.assertEqual(store.recall("default")[0]["content"], "preserve timeout behavior")
            store.close()

    def test_local_executor_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = LocalExecutor(ApprovalPolicy(allowed_commands=[r"^python -c"], blocked_commands=[r"rm -rf"]), Path(directory))
            with self.assertRaises(PermissionError):
                executor.run("python -c \"print('x')\"")
            result = executor.run("python -c \"print('x')\"", approved=True)
            self.assertEqual(result["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
