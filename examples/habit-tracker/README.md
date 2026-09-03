# Habit Tracker Reference

A deliberately small Python reference application used to exercise the orchestrator's spec, implementation, regression, review, and observability workflows.

Features:
- create a habit;
- record a completion for a date;
- compute the current streak;
- list active habits.

This example has no dependency on `.ai-harness` and no external service requirement. The control-plane scenarios for this application are documented separately in `HARNESS_SCENARIOS.md` so domain code stays clean.

The scenarios cover the current harness contract:
- complete-job prompting with intent, rationale, done criteria, guardrails, and non-goals;
- material ambiguity and `CLARIFICATION_NEEDED`;
- explicit scope fencing and deferred out-of-scope work;
- script-first routing for repeatable mechanical checks;
- deterministic verification and proof tied to the changeset.

Run:

```bash
python -m unittest discover -s tests -v
python app.py
```
