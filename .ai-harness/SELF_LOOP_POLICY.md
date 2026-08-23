# Adaptive Self-Improvement Loop

The harness uses a bounded adaptive loop rather than a fixed phase count.

## Objective

Repeatedly improve the task outcome until the acceptance conditions are satisfied, new evidence stops producing material improvement, risk gates are satisfied, or the configured cycle ceiling is reached.

The default ceiling is **500 cycles**. The ceiling is a safety bound, not a target. Most tasks should converge far earlier.

## Cycle model

```text
OBSERVE
  -> UNDERSTAND
  -> DECIDE
  -> ACT
  -> VERIFY
  -> CRITIQUE
  -> IMPROVE
  -> MEASURE
  -> CONVERGE?
       | yes -> ACCEPT
       | no  -> next cycle
```

A cycle may select zero or more capabilities such as research, POC, debug, placement, implementation, testing, review, grill, security review, or cleanup. The router chooses the smallest useful set from current evidence.

## Mandatory invariants

Every cycle must:

- start from current repository state and current task evidence;
- avoid replaying irrelevant history;
- record what new evidence was obtained;
- make a materially different decision only when evidence justifies it;
- verify changes before declaring progress;
- preserve repository conventions and placement rules;
- avoid destructive or irreversible external actions without approval;
- keep changes reversible until acceptance where practical.

## Convergence

The loop should stop when all applicable conditions hold:

1. acceptance criteria are satisfied;
2. required repository-native validation passes;
3. required review findings are resolved;
4. the final diff is consistent with repository architecture, naming and segregation;
5. risk is within the task's accepted boundary;
6. recent cycles produce no material improvement or unresolved blocker;
7. remaining work is either unnecessary, explicitly out of scope, or requires human judgment.

## Anti-loop controls

Do not continue cycling when:

- the same diagnosis and action have failed without new evidence;
- the same files are being rewritten without a measurable improvement;
- validation evidence is unchanged across repeated attempts;
- token/tool cost is increasing without corresponding quality improvement;
- the agent is expanding scope without task evidence;
- a missing human decision is being substituted with guesses.

When an anti-loop condition is reached, either converge or escalate.

## Escalation

Escalate instead of continuing autonomous cycles when the unresolved decision is about:

- product intent;
- authorization or security approval;
- irreversible production action;
- legal/compliance requirements;
- unavailable credentials or external access;
- ambiguous acceptance criteria;
- architectural tradeoffs with materially different business outcomes.

## Learning

A useful cycle contributes evidence, not just text. Promote lessons only after repeated successful observations. Failed hypotheses and retired patterns should remain available for negative learning but must not become trusted guidance.
