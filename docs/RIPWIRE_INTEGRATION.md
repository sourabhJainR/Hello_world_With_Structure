# Repository Intelligence Design Lineage

AER incorporates selected engineering ideas observed in Red Hat's `ripwire` repository. This is a design adaptation, not a code dependency or code copy.

## Adopted concepts

| Ripwire concept | AER adaptation | Why it matters |
| --- | --- | --- |
| Deterministic repository crawl | `RepositoryMap.build()` sorts directories/files, ignores generated/build trees, refuses symlink traversal, and records skipped inputs | Identical repository state produces the same map and digest |
| One shared graph for many questions | Search, callers, callees, impact, affected-test candidates, situational change context, and task packing read the same `RepositoryMap` | Prevents each agent feature from inventing its own repository model |
| Ranked structural context | Path, symbol, import and graph signals produce deterministic ranked files | Reduces broad context reads and improves first-pass localization |
| Shallow graph expansion | Default graph depth is 1 and the implementation caps expansion at 2 | Keeps graph retrieval useful without allowing context explosion |
| Token-priced answers | `token_budget` is enforced before evidence is emitted | Context cost becomes an explicit execution constraint |
| Detail ladder | Map first, then ranked files/windows, then full bodies only when selected | Avoids paying for repository-wide file reads |
| Terminal answers | A single `RepoAnswer` contains evidence, graph edges, metrics and unknowns | Reduces follow-up grep/read loops |
| Honest incompleteness | Unknowns include budget omissions, parse errors, skipped files and missing git state | A missing edge is not presented as proof of absence |
| Affected-test discovery | Graph reverse traversal plus conservative filename/content candidates | Gives the verifier a concrete starting set without claiming execution coverage |
| Snapshot identity | SHA-256 digest covers sorted file facts and extracted relationships | Evidence can be tied to a precise repository state |
| Compact machine output | `render_compact()` provides a stable, low-noise answer surface | Coding agents can consume structural evidence without verbose prose |

## Deliberately not adopted

- No ripwire runtime or library dependency.
- No copied ripwire source code.
- No embeddings or vector database.
- No automatic claim that a call edge is semantically proven when static resolution is ambiguous.
- No automatic mutation or edit authority in the repository map.
- No deep graph expansion by default.
- No similarity-selected context as a substitute for structural evidence.

## AER-specific extension

The repository map feeds AER's existing evidence and lifecycle controls rather than becoming a second orchestration system:

```text
intent
  -> RepositoryMap snapshot
  -> ranked structural evidence
  -> bounded context
  -> plan / act
  -> verification
  -> review
  -> regression / learning
```

The map is an accelerator. Verification, policy, provider permissions, and release gates remain authoritative.

## Usage

```bash
python -m portable.repo_intelligence . --for="Fix the authentication timeout regression" --token-budget=4000
python -m portable.repo_intelligence . --mode=callers --symbol="authenticate"
python -m portable.repo_intelligence . --mode=impact --symbol="authenticate" --graph-depth=1
python -m portable.repo_intelligence . --mode=tests --symbol="authenticate"
python -m portable.repo_intelligence . --mode=situ --base=HEAD
python -m portable.repo_intelligence . --mode=pack-task --for="Add retry handling to the payment client"
```

The JSON form is intended for programmatic handoff:

```bash
python -m portable.repo_intelligence . --for="<task>" --json
```
