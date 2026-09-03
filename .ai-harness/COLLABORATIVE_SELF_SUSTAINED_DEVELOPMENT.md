# Collaborative Self-Sustained Development Contract

This harness is designed to let AI-led engineering continue with minimal human interruption while keeping humans in control of decisions that cannot be established from repository evidence.

## 1. Operating loop

```text
INTAKE
  -> PROFILE
  -> CONSTRUCT + VERSION BASELINE
  -> ROUTE
  -> PLAN
  -> PARALLEL READ-ONLY SPECIALISTS
  -> SMALL MUTATING CHUNK
  -> VERIFY
  -> REVIEW
  -> REPAIR (bounded)
  -> ACCEPT / BLOCK
  -> LEARN
```

A run should stop only for a meaningful human decision, missing access, exhausted safe repair budget, or insufficient evidence. Routine low-risk continuation is autonomous.

## 2. Collaborative execution

Specialists may independently research, inspect architecture, review tests, analyze failures, or validate assumptions. They must report evidence and must not mutate the same file concurrently. Mutating work is isolated with worktrees when risk requires it.

Every specialist result carries a task boundary, evidence references, actual construct references, status, uncertainty and next action. Unsupported claims are not treated as evidence.

## 3. Minimal interruption

The system should resolve routine decisions from repository evidence and learned history. It should ask for human input only for:

- product intent or acceptance criteria that are genuinely ambiguous;
- destructive or irreversible actions;
- production external side effects;
- security, permission or approval-policy changes;
- incompatible toolchain or dependency upgrades;
- missing credentials/access or unavailable required evidence.

Low-risk implementation, verification, bounded repair and continuation should not require a confirmation after every step.

## 4. Legacy project compatibility

Before implementation, the profile detects language, compiler, runtime, framework and package-manager version constraints from repository evidence such as `pyproject.toml`, `.python-version`, `package.json`, `.nvmrc`, `*.csproj`, `global.json`, `go.mod`, `Cargo.toml`, `rust-toolchain.toml`, `pom.xml`, Gradle files, `composer.json`, `Gemfile`, `.ruby-version` and related declarations.

Detected versions are compatibility boundaries. The agent must use syntax, APIs, standard libraries, compiler flags and dependency versions supported by the target. An unknown version is represented as `UNRESOLVED VERSION`; the agent must verify it before choosing a newer-language implementation.

The construct index remains authoritative for actual code locations. Language version and construct identity are both required context for legacy changes.

## 5. Durable learning

The learning system keeps two complementary stores:

- `patterns.jsonl`: promoted, evidence-backed practices and anti-patterns;
- `task-memory.jsonl`: append-only task observations, including commands, approaches, bugs, features, regressions, environment constraints and verification outcomes.

A failed command records the exact command and failure evidence. A failed approach records what was attempted and why it did not solve the task. A later regression records the original run, intent digest and evidence IDs. These observations are fed into future context so the system can avoid repeating known dead ends.

Learning is advisory and evidence-driven. It cannot directly alter executable harness code, permissions, security policy, approval policy, dependency allowlists or architecture rules. Repeated successful evidence is required before a pattern becomes trusted.

## 6. Regression memory

A regression is not erased when its product bug is fixed. The historical event remains linked to the original run and evidence. Future tasks can retrieve it by task terms, approach, command or affected construct.

A corrective pattern is trusted only after repeated successful verification and without unresolved contradictory evidence.

## 7. Construct-grounded artifacts

Plans, HLDs, LLDs, implementation notes, reviews and validation records must reference actual repository constructs. References may identify files, namespaces/modules, classes, interfaces, records/structs, enums, methods/functions, properties/fields, endpoints, messages, schemas, configuration keys, SQL objects, tests and build targets.

If resolution fails, use `UNRESOLVED CONSTRUCT`; never invent a plausible symbol.

## 8. Self-improvement boundary

The system improves through better routing, context selection, verification choices, repair strategies, compatibility awareness and learned failure avoidance. It does not silently rewrite its own control policies. Proposed skill changes remain non-executable until separately evaluated and approved.

## 9. Acceptance standard

A task is complete only when acceptance criteria, repository-native validation, diff checks and required review evidence support completion. If verification fails, the system either performs a bounded evidence-changing repair or returns `BLOCKED` with the exact unresolved evidence gap.
