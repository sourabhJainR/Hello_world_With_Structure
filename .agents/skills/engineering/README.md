# Engineering Skills Bridge

The canonical skill implementations live under `skills/engineering/` so the Claude plugin and other packaging can share one source of truth.

Generic agents should discover these capabilities and read the canonical files:

- `skills/engineering/ask-matt/SKILL.md`
- `skills/engineering/grill-with-docs/SKILL.md`
- `skills/engineering/to-spec/SKILL.md`
- `skills/engineering/to-tickets/SKILL.md`
- `skills/engineering/implement/SKILL.md`
- `skills/engineering/tdd/SKILL.md`
- `skills/engineering/code-review/SKILL.md`
- `skills/engineering/diagnosing-bugs/SKILL.md`
- `skills/engineering/codebase-design/SKILL.md`
- `skills/engineering/improve-codebase-architecture/SKILL.md`
- `skills/engineering/domain-modeling/SKILL.md`

Do not copy these files into a second runtime hierarchy. The `.agents` layer is a discovery/compatibility bridge; the root `skills/` tree owns the implementation.
