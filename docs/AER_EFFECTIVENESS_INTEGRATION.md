# AER Effectiveness Integration

## Purpose

AER is an optional representation adapter for the orchestrator's evidence/context boundary. It should be evaluated as an end-to-end productivity change, not only as a payload compression technique.

## Integration boundary

```text
Evidence providers
  -> canonical structured result
  -> context budgeter
  -> representation selector
      -> JSON
      -> AER AI (optional)
  -> agent/model
  -> verification
```

The canonical evidence remains independent of representation. AER must never become the source of truth.

## Selection policy

Use AER AI only when all of the following hold:

1. the downstream model/host accepts the representation;
2. the data is structured enough for a compact representation;
3. an AER adapter is installed and healthy;
4. the expected context reduction is material;
5. the representation has passed the relevant AER fidelity/conformance version;
6. there is no repository or host rule requiring JSON.

For small payloads, highly irregular data, or compatibility-sensitive boundaries, retain JSON when it is simpler and equally effective.

## Real-world experiment

Run paired tasks:

```text
same repository snapshot
same task
same agent
same model
same system instructions
same tools/permissions
same verification
        |
        +--> JSON evidence
        +--> AER AI evidence
```

Measure:

- task completion/pass rate;
- time-to-proven-change;
- human clarification turns;
- tool calls;
- total input/output tokens using an exact tokenizer;
- retries/rework;
- verification failures;
- regression failures;
- model latency;
- total cost.

Use the AER benchmark protocol in `https://github.com/sourabhJainR/AER/blob/main/docs/AI_EFFECTIVENESS_BENCHMARK.md`.

## Evidence standard

Do not claim "AER improves coding" from smaller payloads alone. A valid claim needs paired task evidence showing that quality is maintained or improved while total cost/friction declines.

Record:

`aer_commit, corpus_version, tokenizer_version, model_version, agent_version, repository_commit, task_id, representation, tokens, cost, latency, verification_result`

## Rollout

Start in shadow mode:

1. produce AER and JSON representations;
2. compare size/token estimates without changing model input;
3. enable AER for a small task cohort;
4. compare against the frozen JSON baseline;
5. expand only when quality and regression gates remain healthy.

Feature-flag the representation choice so rollback is a configuration change, not a code rewrite.
