# Habit Tracker Reference

A deliberately small Python reference application used to exercise the orchestrator's spec, implementation, regression, review, and observability workflows.

Features:
- create a habit;
- record a completion for a date;
- compute the current streak;
- list active habits.

This example has no dependency on `.ai-harness` and no external service requirement.

Run:

```bash
python -m unittest discover -s tests -v
python app.py
```
