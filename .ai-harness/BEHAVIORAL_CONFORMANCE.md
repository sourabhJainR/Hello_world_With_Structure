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

## Ground-truth oracles

The benchmark now has executable task-specific ground truth in `scripts/conformance_oracles.py` and the runner `scripts/behavioral_conformance_ground_truth.py`.

Each run creates a disposable, deterministic fixture before the provider starts. The oracle then evaluates the resulting checkout independently of provider claims. Examples:

- **BC-02** independently imports `slugify_name` and tests multiple normalization cases.
- **BC-03** executes retry scenarios and verifies the counter/attempt invariant, including success-on-first-attempt and eventual-success cases.
- **BC-04** checks the requested behavior and proves the unrelated document path was not accessed through the command trace.
- **BC-05** independently reruns the focused test and known broader failure, while requiring evidence that both verification layers were attempted.
- **BC-06** requires the final behavior plus an observed failed verification followed by successful verification.
- **BC-07** checks that the benchmark secret is absent from source, provider output, and traced arguments, and that configuration wiring is present.
- **BC-08** checks read-only behavior plus decision/alternative/trade-off/rollback evidence in the actual response.
- **BC-09** independently exercises behavior after the refactor rather than trusting the provider's test claim.
- **BC-10** checks tests, diff hygiene, scope, and generated-state gates independently.

Provider JSON is diagnostic only. It cannot turn a failed oracle into a pass.

## Behavioral dimensions

Every live run also retains provider-neutral evidence for:

- **Scope adherence** — stayed inside requested files/areas and boundaries.
- **Context selection** — observed command/path behavior rather than trusting lease claims.
- **Tool usage** — actual traced command execution.
- **Verification evidence** — actual test/check results.
- **Regression detection** — baseline/known-failure behavior where applicable.
- **Recovery** — observed failure followed by successful recovery where the task requires it.
- **Final outcome** — provider exit status plus oracle pass/fail.

The ground-truth runner treats oracle failure as a hard task failure. A provider must also emit the normalized contract without missing required fields.

## Provider parity

Providers execute the same task corpus from the same repository `HEAD` in an isolated checkout. Results are summarized per provider. The suite deliberately does **not** rank model intelligence; it measures conformance to AER engineering behavior.

ChatGPT is represented through its executable Codex/MCP surface rather than as a fictitious local `chatgpt` subprocess. Claude, Codex, and Gemini use their local CLIs when installed; Gemini falls back to the configured `antigravity` migration alias.

## Commands

Static corpus/integrity checks are part of the normal eval gate:

```bash
python scripts/run_evals.py
```

Run the original objective-evidence suite:

```bash
python scripts/behavioral_conformance.py --write-report
```

Run the ground-truth engineering benchmark:

```bash
python scripts/behavioral_conformance_ground_truth.py --write-report
```

Run one task or selected providers:

```bash
python scripts/behavioral_conformance_ground_truth.py --task BC-03 --providers claude,codex
```

The suite is intentionally live-only. A provider that is unavailable is not silently replaced by a sentinel result. Behavioral release readiness requires every requested provider to complete every requested task successfully.

## Safety

Execution is opt-in, uses a disposable checkout, and does not write the behavioral report unless `--write-report` is supplied. Provider prompts explicitly prohibit secret disclosure and unrelated access. Behavioral results must never be treated as permission to activate AER self-modification; normal regression, safety, shadow/canary, and promotion gates remain authoritative.
