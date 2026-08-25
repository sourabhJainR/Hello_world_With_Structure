# Agent Compatibility

The orchestrator is designed as a control plane behind multiple coding agents.

## Adapter boundary

An agent adapter is responsible only for translating between the host agent and the orchestrator:

```text
host prompt/events
      |
      v
agent adapter
      |
      v
orchestrator contract
      |
      v
workflow + evidence + policy
```

The core must not depend on Claude, Codex, Gemini or another model's private prompt format.

## Minimum adapter contract

An adapter should provide:

- current repository/workspace;
- user task;
- available tools/capabilities;
- cancellation signal;
- permission state;
- a bounded output channel.

It should consume:

- selected workflow;
- tool requests;
- evidence requests;
- verification results;
- user approval requirements;
- final structured result.

## Capability negotiation

At startup, the adapter and orchestrator negotiate supported capabilities. Unsupported features are disabled rather than emulated with hidden assumptions.

## State

Session state must be explicit and resumable:

```text
NEW -> CLASSIFIED -> PLANNED -> EXECUTING -> VERIFYING -> REVIEWING -> COMPLETED
                         |             |
                         +-> BLOCKED <-+
```

A cancellation or provider failure must leave a recoverable state and must not be interpreted as successful completion.

## Host-specific integrations

Claude Code, Codex, Gemini CLI and other hosts may have different skill, MCP, hook and permission mechanisms. Those details belong in adapters and installation documentation, not in the core workflow rules.
