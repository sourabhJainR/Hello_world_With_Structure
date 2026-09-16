# Cognitive Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the existing AER cognitive primitives with `AdaptiveRuntime.run()` so each execution can persist observations, maintain goals/beliefs, select information actions, act through the existing orchestrator, and update cognitive state without replacing the execution authority.

**Architecture:** `AdaptiveRuntime` remains the execution facade and `Orchestrator` remains authoritative for task execution. A new cognitive episode coordinator will wrap the execution lifecycle, using the existing `CognitiveRuntime` facade and persistent memory, while emitting deterministic, bounded episode records. Cognitive side effects are best-effort and must never silently change an orchestration result; failures are recorded and surfaced through the episode receipt.

**Tech Stack:** Python 3, existing `portable` cognitive/runtime modules, pytest, SQLite-backed `PersistentMemory`.

**Spec:** Architectural design agreed in-chat for the Cognitive Closed Loop increment.

## Global Constraints

- Do not replace `StateGraph`, `Graph`, or `Orchestrator` as execution authority.
- Do not add paid-service dependencies.
- Keep cognitive state project-scoped through the canonical `PersistentMemory` path.
- Keep each cognitive episode bounded and serializable.
- Preserve existing `AdaptiveRuntime.run()` return type and failure semantics.
- Add tests before implementation for the new lifecycle behavior.

---

### Task 1: Define the cognitive episode contract

**Files:**
- Create: `portable/cognitive_loop.py`
- Test: `tests/portable/test_cognitive_loop.py`

**Interfaces:**
- Produces `CognitiveEpisode` and `CognitiveLoop`.
- `CognitiveLoop.begin(...) -> CognitiveEpisode`
- `CognitiveLoop.observe(...) -> None`
- `CognitiveLoop.complete(...) -> CognitiveEpisode`

- [ ] **Step 1: Write the failing test**

```python
from portable.cognitive_loop import CognitiveEpisode


def test_episode_has_stable_identity_and_phase_history():
    episode = CognitiveEpisode.start("project-x", "task-1", "improve parser")
    episode.record_phase("observe")
    episode.record_phase("plan")
    receipt = episode.finish("success")
    assert receipt.project_key == "project-x"
    assert receipt.task_id == "task-1"
    assert receipt.status == "success"
    assert receipt.phases == ("observe", "plan")
    assert receipt.episode_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/portable/test_cognitive_loop.py -q`
Expected: FAIL because `portable.cognitive_loop` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class CognitiveEpisodeReceipt:
    episode_id: str
    project_key: str
    task_id: str
    intent: str
    status: str
    phases: tuple[str, ...]
    observations: tuple[dict, ...]
    started_at: str
    finished_at: str
    error: str | None = None


@dataclass
class CognitiveEpisode:
    episode_id: str
    project_key: str
    task_id: str
    intent: str
    started_at: str
    _phases: list[str] = field(default_factory=list)
    _observations: list[dict] = field(default_factory=list)

    @classmethod
    def start(cls, project_key: str, task_id: str, intent: str) -> "CognitiveEpisode":
        return cls(uuid4().hex, project_key, task_id, intent, datetime.now(timezone.utc).isoformat())

    def record_phase(self, phase: str) -> None:
        if phase not in self._phases:
            self._phases.append(phase)

    def observe(self, observation: dict) -> None:
        self._observations.append(dict(observation))

    def finish(self, status: str, error: str | None = None) -> CognitiveEpisodeReceipt:
        return CognitiveEpisodeReceipt(
            self.episode_id, self.project_key, self.task_id, self.intent, status,
            tuple(self._phases), tuple(self._observations), self.started_at,
            datetime.now(timezone.utc).isoformat(), error,
        )


class CognitiveLoop:
    def begin(self, project_key: str, task_id: str, intent: str) -> CognitiveEpisode:
        episode = CognitiveEpisode.start(project_key, task_id, intent)
        episode.record_phase("observe")
        return episode

    def observe(self, episode: CognitiveEpisode, observation: dict) -> None:
        episode.observe(observation)
        episode.record_phase("learn")

    def complete(self, episode: CognitiveEpisode, status: str, error: str | None = None) -> CognitiveEpisodeReceipt:
        episode.record_phase("evaluate")
        episode.record_phase("complete")
        return episode.finish(status, error)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/portable/test_cognitive_loop.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/cognitive_loop.py tests/portable/test_cognitive_loop.py
git commit -m "feat: add bounded cognitive episode contract"
```

### Task 2: Connect the loop to AdaptiveRuntime

**Files:**
- Modify: `portable/adaptive_runtime.py`
- Modify: `portable/__init__.py`
- Test: `tests/test_adaptive_runtime_context.py`

**Interfaces:**
- `AdaptiveRuntime.run()` returns the existing `OrchestrationRun` unchanged.
- New `AdaptiveRuntime.last_cognitive_episode` exposes the most recent receipt for diagnostics.
- The cognitive episode receives start/end observations and uses the project-scoped `CognitiveRuntime` facade already exposed by `cognition()`.

- [ ] **Step 1: Write the failing test**

```python
def test_run_records_cognitive_episode(monkeypatch, tmp_path):
    runtime = make_runtime(tmp_path)
    result = runtime.run(
        session_id="s1", task_id="t1", project_root=tmp_path,
        intent="test cognitive integration",
    )
    receipt = runtime.last_cognitive_episode
    assert result.status.value == "completed"
    assert receipt is not None
    assert receipt.task_id == "t1"
    assert "observe" in receipt.phases
    assert "evaluate" in receipt.phases
    assert receipt.status == result.status.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_runtime_context.py::test_run_records_cognitive_episode -q`
Expected: FAIL because `last_cognitive_episode` does not exist.

- [ ] **Step 3: Write minimal implementation**

Add a `CognitiveLoop` instance and `last_cognitive_episode` field in `AdaptiveRuntime.__init__`. In `run()`, create an episode after the session-start gate, record the resolved context digest when enrichment is enabled, record orchestration completion status, and complete the episode in both success and exception paths. Do not alter the existing `OrchestrationRun` return value or exception behavior.

- [ ] **Step 4: Run focused and regression tests**

Run: `pytest tests/test_adaptive_runtime_context.py -q tests/portable/test_cognitive_loop.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_runtime.py portable/__init__.py tests/test_adaptive_runtime_context.py
git commit -m "feat: integrate cognitive episode lifecycle into runtime"
```

### Task 3: Persist cognitive observations through existing memory

**Files:**
- Modify: `portable/cognitive_loop.py`
- Modify: `portable/cognitive_runtime.py`
- Test: `tests/portable/test_cognitive_loop.py`

**Interfaces:**
- `CognitiveLoop` accepts an optional `CognitiveRuntime` and persists normalized episode observations through canonical memory.
- Persistence is bounded to episode metadata and does not duplicate full orchestration context.

- [ ] **Step 1: Write the failing test**

```python
def test_loop_persists_episode_observation(cognitive_runtime):
    loop = CognitiveLoop(cognitive_runtime)
    episode = loop.begin("project-x", "task-1", "learn")
    loop.observe(episode, {"event": "execution_started", "status": "running"})
    matches = cognitive_runtime.memory.search("execution_started", limit=5)
    assert matches
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/portable/test_cognitive_loop.py::test_loop_persists_episode_observation -q`
Expected: FAIL because loop observations are not persisted.

- [ ] **Step 3: Implement persistence using existing memory APIs**

Use the existing `PersistentMemory` interface already held by `CognitiveRuntime`; store a compact record keyed by `cognitive_episode:{episode_id}:{sequence}` with project/task/phase/status metadata. Do not store raw prompts or large context payloads.

- [ ] **Step 4: Run tests**

Run: `pytest tests/portable/test_cognitive_loop.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/cognitive_loop.py portable/cognitive_runtime.py tests/portable/test_cognitive_loop.py
git commit -m "feat: persist bounded cognitive episode observations"
```

### Task 4: PR review, CI, merge, and branch cleanup

**Files:**
- No source files unless review fixes are required.

**Interfaces:**
- Feature branch merges only after review findings are resolved and every CI check completes successfully.

- [ ] **Step 1: Run the full repository test command defined by CI**
- [ ] **Step 2: Open PR against `main`**
- [ ] **Step 3: Inspect complete diff and review threads**
- [ ] **Step 4: Fix every actionable finding**
- [ ] **Step 5: Wait for all CI checks on the latest head SHA**
- [ ] **Step 6: Merge PR**
- [ ] **Step 7: Delete feature branch**
- [ ] **Step 8: Verify only `main` remains**

After this increment is merged, repeat the same lifecycle for the next backlog item, beginning from the new `main` SHA.
