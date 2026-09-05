# Loop Engineering Policy

The orchestrator uses a bounded quality loop inspired by the six-layer model:

1. Generation: produce the smallest useful candidate.
2. Evaluation: verify correctness, acceptance, regressions, and evidence.
3. Memory: retain compact evidence-backed outcomes and trusted lessons.
4. Scheduling: decide the next best action.
5. Optimization: improve context, routing, and collaboration efficiency.
6. Recursion: repeat only when explicitly enabled and measurable value remains.

## Problem-solving layer

Every non-trivial run adds an adaptive problem-solving selection between routing and planning:

`Route -> Classify -> Select -> Plan`

Select from OODA, DMAIC, 5 Whys/RCA, Pre-Mortem, First Principles, Six Thinking Hats and Decision Tree Analysis according to problem type, uncertainty, risk and time pressure. Use the smallest useful combination. A framework may be explicitly marked `not needed` with a reason.

The selection must produce a compact reasoning contract: framework, purpose, key findings, decision, evidence and next action. This becomes part of the run evidence and is carried through handoffs and repair.

## Smart collaboration

Subagents are selected by complexity and risk, not by a fixed swarm.

- Planner establishes intent, boundaries, proof obligations and selected problem-solving approach.
- Builder changes code or artifacts.
- Evaluator verifies behavior and evidence.
- Reviewer is added for high-risk or complex work.
- Optimizer is added for difficult research, RCA, or high-context work.
- RCA investigator is used when symptoms may hide a recurring or systemic cause.

Independent read-only analysis may run in parallel. Conflicting edits never run in parallel.

## Graph and memory

Knowledge remains a provenance graph:

`Evidence -> Finding -> Decision -> Change -> Verification -> Outcome -> Learning`

Problem-solving artifacts attach to this graph rather than becoming unverified model memory.

Handoffs carry only the next component's useful state. Full transcripts are not replayed.

## Stop conditions

Stop when any of these is true:

- iteration budget reached;
- quality is sufficient and regressions are absent;
- marginal utility falls below the configured threshold;
- no new evidence is produced;
- the next iteration would only restate or cosmetically rewrite the same result.

The default runtime remains one adaptive run. Explicit loop mode is bounded to prevent runaway cost or recursive self-invocation.

## Quality objective

Optimize for verified artifact quality per token, tool call, retry, and latency. More iterations are not automatically better. A loop earns another cycle only when it can demonstrate likely improvement.

## Framework-specific quality discipline

- OODA: reassess after material new evidence and keep decisions time-bounded.
- DMAIC: establish a baseline and measure the effect of improvements.
- 5 Whys: do not stop at a symptom; branch when multiple causes are plausible and verify the causal hypothesis.
- Pre-Mortem: convert material failure modes into mitigations, tests, rollback triggers or escalation.
- First Principles: distinguish verified constraints from assumptions before redesigning.
- Six Thinking Hats: keep facts, concerns, risks, benefits, alternatives and process decisions distinct.
- Decision Tree: expose options, uncertainty, outcomes and reversibility without invented precision.

Do not run a framework as ceremony. It must improve or validate the decision in observable evidence.
