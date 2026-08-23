# Ten-Pass Implementation and Review Loop

The default orchestration uses up to ten focused passes. It may stop early when all required gates pass, but it must not skip a required high-risk gate.

| Pass | Focus | Question |
|---|---|---|
| 1 | Intake and intent | What outcome is required? |
| 2 | Repository profile | What conventions, architecture, dependencies, and tests already exist? |
| 3 | Context and placement | What evidence is needed and where should changes live? |
| 4 | Design and risk | What is the smallest safe design and what can fail? |
| 5 | Implementation | What is the smallest correct change? |
| 6 | Verification | What direct evidence proves the acceptance criteria? |
| 7 | Adversarial review | What would an independent reviewer or attacker challenge? |
| 8 | Repair and regression | Did the fixes preserve existing behavior and improve the failure? |
| 9 | Optimization and cleanup | Can context, code, dependencies, and run cost be reduced without weakening guarantees? |
| 10 | Final acceptance and learning | Is the result production-ready and what evidence should be retained? |

Each pass should leave a compact artifact or state update. The loop can terminate before pass 10 only when the configured acceptance gates are satisfied and the skipped passes are demonstrably unnecessary for the task risk profile.

For high/critical risk work, passes 6, 7, 8, and 10 are mandatory.
