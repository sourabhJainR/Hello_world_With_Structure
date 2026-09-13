from pathlib import Path

import pytest

from portable.hermes_runtime import (
    ApprovalPolicy,
    DurableStore,
    LocalExecutor,
    ProviderRouter,
    ProviderSpec,
    Skill,
    SkillRegistry,
    ToolRegistry,
    ToolSpec,
)


def test_provider_router_selects_required_capability():
    router = ProviderRouter([
        ProviderSpec("cheap", "m1", capabilities=frozenset({"text"}), priority=1),
        ProviderSpec("vision", "m2", capabilities=frozenset({"text", "vision"}), priority=5),
    ])
    assert router.resolve({"vision"}).name == "vision"


def test_skill_registry_ranks_relevant_skill():
    registry = SkillRegistry()
    registry.register(Skill("python-testing", "pytest and regression testing", "run tests", frozenset({"python", "testing"})))
    registry.register(Skill("docs", "documentation", "write docs", frozenset({"docs"})))
    assert registry.discover("python testing")[0].name == "python-testing"


def test_tool_registry_requires_approval():
    registry = ToolRegistry()
    registry.register(ToolSpec("safe.echo", "echo", lambda value: value))
    registry.register(ToolSpec("danger", "danger", lambda: "ok", requires_approval=True))
    assert registry.call("safe.echo", value="ok") == "ok"
    with pytest.raises(PermissionError):
        registry.call("danger")
    assert registry.call("danger", approved=True) == "ok"


def test_durable_store_persists_and_searches(tmp_path: Path):
    store = DurableStore(tmp_path / "state.db")
    from portable.hermes_runtime import SessionState
    state = SessionState("s1", "default", task_id="t1")
    store.save_session(state)
    store.append_message("s1", "user", "fix authentication timeout")
    store.remember("default", "lesson", "preserve timeout behavior", "test", 0.9)
    assert store.search_sessions("authentication")[0]["session_id"] == "s1"
    assert store.recall("default")[0]["content"] == "preserve timeout behavior"
    store.close()


def test_local_executor_is_fail_closed(tmp_path: Path):
    executor = LocalExecutor(ApprovalPolicy(allowed_commands=[r"^python -c"], blocked_commands=[r"rm -rf"]), tmp_path)
    with pytest.raises(PermissionError):
        executor.run("python -c \"print('x')\"")
    result = executor.run("python -c \"print('x')\"", approved=True)
    assert result["returncode"] == 0
