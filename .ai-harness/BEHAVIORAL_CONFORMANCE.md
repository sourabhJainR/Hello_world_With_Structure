# AER Behavioral Conformance Suite

The Behavioral Conformance Suite tests whether providers preserve AER's engineering behavior, rather than merely responding to a prompt.

## Ten-task corpus

The same ten representative tasks are stored in `.ai-harness/conformance/tasks.jsonl`:

1. Repository orientation
2. Targeted feature change
3. Defect root-cause analysis
4. Context minimization
5. Regression detection
6. Recovery after verification failure
7. Security boundary / secret safety
8. Architecture decision
9. Maintenance refactor
10. Release readiness

Each task declares its mode, required capabilities, and acceptance criteria.

## Behavioral dimensions

Every live run is normalized into a provider-neutral contract and scored on:

- **Scope adherence** — stayed inside requested files/areas and boundaries.
- **Context selection** — retrieved only useful context and recorded compact lease digests.
- **Tool usage** — used tools/commands intentionally and recorded observations.
- **Verification evidence** — reported actual tests/checks and results.
- **Regression detection** — distinguished regressions from pre-existing failures and did not hide failures.
- **Recovery** — diagnosed and recovered from failed commands or stopped honestly when blocked.
- **Final outcome** — pass, blocked, or fail is evidence-backed rather than asserted.

A task must also provide the complete normalized evidence contract. The default task threshold is 70% with no missing required contract fields.

## Provider parity

Providers execute the same task corpus from the same repository `HEAD` in an isolated checkout. Results are summarized per provider and pairwise dimension gaps are reported. The suite deliberately does **not** rank model intelligence; it measures conformance to AER engineering behavior.

ChatGPT is represented through its executable Codex/MCP surface rather than as a fictitious local `chatgpt` subprocess. Claude, Codex, and Gemini use their local CLIs when installed; Gemini falls back to the configured `antigravity` migration alias.

## Commands

Static corpus/integrity checks are part of the normal eval gate:

```bash
python scripts/run_evals.py
```

Run all ten tasks against every locally available provider:

```bash
python scripts/behavioral_conformance.py --write-report
```

Run one task or selected providers:

```bash
python scripts/behavioral_conformance.py --task BC-05 --providers claude,codex
```

The suite is intentionally live-only. A provider that is unavailable is not silently replaced by a sentinel result. Behavioral release readiness requires every requested provider to complete every requested task successfully.

## Safety

Execution is opt-in, uses a disposable checkout, and does not write the behavioral report unless `--write-report` is supplied. Provider prompts explicitly prohibit secret disclosure and unrelated access. Behavioral results must never be treated as permission to activate AER self-modification; normal regression, safety, shadow/canary, and promotion gates remain authoritative.
