---
name: grill-with-docs
description: Resolve ambiguous engineering intent through focused questions while leaving a durable, repository-native decision trail.
disable-model-invocation: true
---

# Grill With Docs

Use this before substantial work when requirements, terminology, ownership, acceptance criteria, constraints, or stopping conditions are unclear.

## Method

Ask one question at a time. Prefer questions that eliminate a design branch. Start with goal and acceptance behavior, then constraints, affected modules, compatibility, failure behavior, and explicit non-goals.

Do not ask questions whose answer can be established from the repository. Retrieve repository evidence first.

## Durable state

When a decision changes the shared domain vocabulary or is hard to reverse, update the existing context/glossary or ADR location. Do not create a second decision store.

End with a compact intent summary containing: goal, in-scope, out-of-scope, acceptance checks, constraints, risks, unresolved questions, and stopping condition. Carry the existing intent/context identifiers into implementation rather than rewriting them silently.
