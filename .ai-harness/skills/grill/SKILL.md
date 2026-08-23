# Grill Skill

Use when a design, implementation, migration, security change, or production decision deserves an adversarial review.

## Required behavior

Challenge the current direction rather than inventing arbitrary objections.

Check:

- assumptions
- missing requirements
- security and privacy
- correctness
- scale and performance
- failure modes
- operational complexity
- rollback and migration risk
- dependency/vendor risk
- observability
- test gaps
- simpler alternatives

## Verdict

Choose one:

- PROCEED
- PROCEED_WITH_CHANGES
- RESEARCH_MORE
- REJECT

For anything other than PROCEED, emit `HARNESS_GRILL_ACTION_REQUIRED` and list concrete actions.
