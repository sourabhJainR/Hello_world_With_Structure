# Capability Acquisition and Curiosity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn AER's proposal-only capability acquisition into an evidence-gated practice, evaluation and graduation loop, while adding a deterministic learning frontier that chooses what to learn next from uncertainty, importance, cost and risk.

**Architecture:** `CapabilityAcquirer` remains permission-neutral. A proposal can be practiced only through a caller-supplied bounded runner, evaluated through caller-supplied evidence, and graduated only after repeated successful validation. Graduation records a validated skill in the existing `SkillGraph`. `CuriosityEngine` selects the highest-value unresolved capability need but never executes it automatically.

**Tech Stack:** Python standard library, existing `PersistentMemory`, existing `SkillGraph`, pytest/unittest.

**Spec:** Approved backlog increment: capability acquisition loop and open-ended curiosity.

## Global Constraints

- No paid-service dependencies.
- Capability acquisition cannot grant permissions or bypass risk controls.
- Practice is bounded and caller-owned.
- Graduation requires validation evidence and repeated successful practice.
- Curiosity is a planner, not an executor.
- Existing `CapabilityAcquirer.propose()` and `validate()` remain compatible.

---

### Task 1: Persistent capability practice and graduation

**Files:**
- Modify: `portable/capability_acquisition.py`
- Test: `tests/portable/test_capability_acquisition.py`

**Interfaces:**
- `PracticeResult`
- `GraduationReceipt`
- `CapabilityAcquirer.practice(proposal_id, runner)`
- `CapabilityAcquirer.graduate(proposal_id, results, evidence_ids)`

- [ ] **Step 1: Write failing tests**

```python
def test_practice_records_bounded_success():
    proposal = acquirer.propose(need)
    result = acquirer.practice(proposal.id, lambda: {"tests_passed": True, "safety_reviewed": True})
    assert result.accepted


def test_graduation_requires_repeated_success_and_evidence():
    proposal = acquirer.propose(need)
    first = acquirer.practice(proposal.id, lambda: {"tests_passed": True, "safety_reviewed": True})
    assert not acquirer.graduate(proposal.id, (first,), evidence_ids=("practice-1",)) .accepted
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/portable/test_capability_acquisition.py -q`
Expected: FAIL because practice/graduation APIs do not exist.

- [ ] **Step 3: Implement persistent practice receipts**

Store proposal-scoped practice attempts with bounded normalized results. The runner must be a callable owned by the caller; it receives no extra permissions from AER. Reject non-dict results and cap stored diagnostic text to a small fixed size.

- [ ] **Step 4: Implement repeated-evidence graduation**

Require at least two accepted practice attempts from distinct attempt IDs plus non-empty graduation evidence. On success, persist a validated capability record and add/update a validated `SkillNode` in `SkillGraph` without granting execution permissions.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/portable/test_capability_acquisition.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add portable/capability_acquisition.py tests/portable/test_capability_acquisition.py
git commit -m "feat: add evidence-gated capability practice and graduation"
```

### Task 2: Curiosity and learning frontier

**Files:**
- Create: `portable/curiosity.py`
- Test: `tests/portable/test_curiosity.py`

**Interfaces:**
- `LearningNeed`
- `LearningChoice`
- `CuriosityEngine.rank(...)`
- `CuriosityEngine.choose(...)`

- [ ] **Step 1: Write failing tests**

```python
def test_curiosity_prioritizes_high_value_uncertainty():
    engine = CuriosityEngine()
    choices = engine.rank([
        LearningNeed("parser", 0.8, 0.9, 1.0, 0.1),
        LearningNeed("formatting", 0.5, 0.2, 0.5, 0.1),
    ])
    assert choices[0].capability == "parser"


def test_curiosity_respects_risk_and_budget():
    engine = CuriosityEngine()
    choice = engine.choose([
        LearningNeed("unsafe", 1.0, 1.0, 0.1, 1.0),
        LearningNeed("safe", 0.7, 0.8, 0.5, 0.1),
    ], max_cost=1.0, max_risk=0.5)
    assert choice.capability == "safe"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/portable/test_curiosity.py -q`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement deterministic learning-value scoring**

Score each need using uncertainty × importance × expected gain divided by cost, subtracting risk. Exclude needs exceeding cost/risk limits. Tie-break by capability name for determinism. No external calls.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/portable/test_curiosity.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/curiosity.py tests/portable/test_curiosity.py
 git commit -m "feat: add deterministic curiosity learning frontier"
```

### Task 3: Runtime exports and integration

**Files:**
- Modify: `portable/__init__.py`
- Test: `tests/portable/test_capability_acquisition.py`

- [ ] **Step 1: Export curiosity and practice/graduation types.**
- [ ] **Step 2: Verify graduated skills are queryable through `SkillGraph.ready()`.**
- [ ] **Step 3: Run acquisition and curiosity suites.**

Run: `pytest tests/portable/test_capability_acquisition.py tests/portable/test_curiosity.py tests/portable/test_skill_graph.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add portable/__init__.py tests/portable/test_capability_acquisition.py tests/portable/test_curiosity.py tests/portable/test_skill_graph.py
git commit -m "feat: connect capability graduation to learning frontier"
```

### Task 4: PR review, CI, merge, and branch cleanup

- [ ] Inspect complete diff and review behavior/invariants.
- [ ] Fix every actionable review finding.
- [ ] Wait for every CI workflow on the latest head SHA.
- [ ] Fix any failed checks and repeat the full CI cycle.
- [ ] Merge only after every workflow is successful.
- [ ] Delete the feature branch when repository tooling permits it.
- [ ] Verify the resulting main branch contains the increment.
