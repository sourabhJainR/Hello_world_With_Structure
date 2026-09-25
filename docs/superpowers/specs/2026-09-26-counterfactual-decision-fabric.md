# Counterfactual Decision Fabric

## Goal

Add a bounded counterfactual layer above the existing historical routing and adaptive inference components. The layer compares explicit candidate branches before execution and can abstain when evidence is insufficient.

## Scope

Phase 1 does not execute speculative branches, mutate active policy, or claim that heuristic scores are causal probabilities. It produces an auditable, typed decision that can be consumed by existing policy gates.

## Decision flow

state -> candidate branches -> bounded utility -> relative probabilities -> confidence/margin gate -> selected branch or abstain

Each candidate includes predicted success, evidence value, risk, cost, expected duration, resource pressure, and prediction confidence.

The utility function rewards expected success and evidence while penalizing risk, cost, duration, and resource pressure. Confidence and the separation between the first and second candidate prevent the system from forcing a choice when alternatives are too close.

## Safety boundaries

- Counterfactual evaluation never executes a candidate.
- A low-confidence or low-margin comparison abstains.
- Branch names are unique and ordering is deterministic.
- The output contains a state digest and auditable branch scores.
- Existing execution, verification, permissions, rollback, and merge gates remain authoritative.
- No learned policy is mutated during an active task.
- The module is dependency-light and provider-neutral.

## Next phases

1. Connect counterfactual decisions to the existing ExperienceRouter and GraphAgentTeam for capability, verification-depth, retry/escalation, and resource-lane choices.
2. Record counterfactual predictions beside observed outcomes and evaluate calibration.
3. Add capability-gap detection and bounded capability acquisition.
4. Build a repository/world-state model that predicts change impact.
5. Add long-horizon mission goals with explicit stop, budget, and regression gates.
