# Plugin architecture

The core orchestrator is provider-neutral. Claude Code is an adapter, not the core runtime.

```text
AI coding client
      |
      v
Provider adapter
      |
      v
Adaptive orchestrator
      |
      +--> repository profile
      +--> knowledge fabric
      +--> context engine
      +--> workflow routing
      +--> verification
      +--> review
      +--> learning
      |
      +--> optional extensions
             +-- Graphify
             +-- code-mem
             +-- Superpowers
             +-- Ponytail
             +-- Caveman
             +-- other skills/MCP
```

## Precedence

1. Repository and organization instructions.
2. Security and permission boundaries.
3. Acceptance criteria.
4. Existing architecture and conventions.
5. Verification requirements.
6. Orchestrator policy.
7. Optional extension guidance.
8. Model preference.

## Extension contract

An extension must be treated as a capability provider. The orchestrator should detect availability, capabilities, freshness, provenance, cost, and permission state before use.

An unavailable extension must degrade to another available capability. Core coding, verification, and safety behavior must never depend on an optional extension.

## Context contract

The context engine uses an IO-aware strategy inspired by FlashAttention: maintain a compact stable prefix, retrieve task-specific evidence in bounded tiles, rank before inclusion, and avoid replaying irrelevant history. Verification evidence is lossless and always retained.

## Repository independence

No language, framework, package manager, logging system, telemetry library, test framework, or code-intelligence provider is assumed. Local repository patterns are authoritative whenever they exist.
