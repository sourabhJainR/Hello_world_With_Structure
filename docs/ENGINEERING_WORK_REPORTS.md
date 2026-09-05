# Engineering Work Reports

Every orchestrated work item must produce a durable HTML engineering report. The report is an evidence package, not an approval mechanism.

## Output

Reports are written to:

```text
.ai-harness/reports/<work-id>.html
.ai-harness/reports/latest.html
```

The CLI emits a report for every invocation, including failed commands. Report generation is best-effort and never changes the primary command exit status.

The runtime also exposes `WorkReport` and `WorkReportGenerator` so agent-turn, learning, verification, review, RCA, research, implementation, and repair paths can emit the same contract.

## Mandatory content

Each report should contain, when applicable:

- work objective and executive summary;
- exact scope, out-of-scope boundaries, assumptions and constraints;
- repository and external references with paths, identifiers, URLs, commits, or line pointers when available;
- evidence and provenance for important claims;
- findings, decisions and unresolved questions;
- HLD and LLD;
- implementation/change summary;
- system/component flow;
- data-flow diagram;
- user/use-case flow;
- UML sequence diagram;
- verification results and regression areas;
- risks and threats, including security boundaries;
- operational and rollback considerations;
- metrics such as retries, latency, cost, verification and regression counts;
- audit/event trail where available.

Unknown information must be represented as an unknown or an explicit evidence gap. The reporter must not invent evidence.

## Diagram contract

Diagrams are emitted as inspectable Mermaid source inside the HTML. The renderer keeps the source visible so diagrams remain reproducible and reviewable. The report includes at least system flow, data flow, user flow and UML sequence views; callers may supply richer domain-specific diagrams later.

## Reference contract

A reference should identify the strongest available pointer:

```json
{
  "type": "repository",
  "path": "src/service.py",
  "line": 42,
  "commit": "<sha>"
}
```

External evidence may use `url`, `title`, `source`, `retrieved_at`, or `identifier`. Sensitive credentials, tokens and secrets must never be copied into reports.

## Engineering lifecycle

```text
Intent
  -> Contract
  -> Repository / domain evidence
  -> HLD
  -> LLD
  -> Implementation
  -> Verification
  -> Regression analysis
  -> Risk / threat assessment
  -> Evidence package
  -> HTML report
  -> Learning / future experience
```

For self-improvement, the report complements the existing closed loop:

```text
Experience
  -> Candidate
  -> Task-family regression replay
  -> Shadow
  -> Canary
  -> Promotion
  -> Monitoring
  -> Rollback
  -> New experience + report evidence
```

Promotion and rollback controls remain authoritative. Documentation generation cannot grant execution, security, permission, merge, or approval authority.

## Quality gates

A report is considered complete only when the work path has attempted to populate the relevant sections. A section may legitimately say `No evidence recorded` when that category does not apply or the evidence is unavailable. This is preferable to fabricated certainty.

For implementation work, the expected minimum is HLD + LLD + references + assumptions/boundaries + findings + risks/threats + verification + regression areas + system/data/user/UML diagrams.
