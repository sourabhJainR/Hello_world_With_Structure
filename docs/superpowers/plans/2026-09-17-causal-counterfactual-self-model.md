# Causal Intervention, Counterfactual, and Self-Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the empirical causal-learning, alternate-world simulation, and context-sensitive self-model gaps while preserving read-only and permission-safe execution boundaries.

**Architecture:** `CausalLearner` records a proposed intervention and its observed outcome, promoting only positively observed evidence into the existing `CausalModel`. `CounterfactualEngine.simulate()` evaluates causal reachability and runs a caller-owned state transition over a copied alternate state. `SelfModel` persists outcomes with optional context and difficulty dimensions and exposes calibrated profiles/escalation checks.

**Tech Stack:** Python standard library, existing `ContextGraph`, `CausalModel`, `PersistentMemory`, pytest/unittest.

**Spec:** Approved backlog increment: causal intervention loop, counterfactual simulation, advanced self-model.

## Global Constraints
- No paid dependencies.
- Intervention learning never mutates an external environment itself.
- Counterfactual simulation operates on copied state and caller-owned transition functions.
- Self-model data is empirical and does not grant capabilities.
- Existing CausalModel, CounterfactualEngine, SelfModel APIs remain backward-compatible.

---

### Task 1: Causal intervention loop
**Files:** `portable/causal_learning.py`, `tests/portable/test_causal_learning.py`
- [ ] Test positive intervention outcome creates an evidence-backed causal link.
- [ ] Test negative outcome is persisted but does not promote a causal edge.
- [ ] Implement durable interventions/outcomes with project scope and bounded storage.
- [ ] Commit: `feat: add empirical causal intervention learning`

### Task 2: Counterfactual alternate-world simulation
**Files:** `portable/counterfactual.py`, `tests/portable/test_causal_learning.py`
- [ ] Test alternate transition produces explicit target predictions without mutating initial state.
- [ ] Preserve current path/reachability behavior.
- [ ] Add `simulate(...)` with a caller-owned pure transition function.
- [ ] Commit: `feat: add explicit counterfactual alternate-state simulation`

### Task 3: Context-aware self-model
**Files:** `portable/self_model.py`, `tests/portable/test_causal_learning.py`
- [ ] Test separate confidence profiles for context and difficulty.
- [ ] Preserve aggregate profile behavior when filters are omitted.
- [ ] Add bounded outcome storage, segmented `profile(...)`, and `should_escalate(...)`.
- [ ] Commit: `feat: add context and difficulty aware self-model calibration`

### Task 4: Public exports, review, CI, merge
- [ ] Export the new causal-learning APIs.
- [ ] Inspect full PR diff and review all correctness/security/API findings.
- [ ] Fix every actionable finding.
- [ ] Wait for all CI workflows on the latest head SHA.
- [ ] Fix failures and repeat full CI.
- [ ] Merge after all workflows succeed.
- [ ] Delete the feature branch when tooling permits it.
- [ ] Verify merged `main` before starting the next increment.
