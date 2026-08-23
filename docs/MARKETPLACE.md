# Distribution and marketplace

## Claude Code marketplace

This repository contains both the plugin manifest and a Claude Code marketplace manifest.

Install the marketplace from Claude Code:

```text
/plugin marketplace add sourabhJainR/Hello_world_With_Structure
```

Install the plugin:

```text
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

The marketplace is intentionally small: it publishes the orchestrator as one plugin while optional integrations remain external capabilities.

## Local development

```text
/plugin marketplace add .
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

## Universal installer

```bash
./install.sh
```

or:

```bash
python3 scripts/install_skill.py --auto
```

The installer detects supported agent environments and installs the skill without installing third-party tools or modifying MCP configuration.

## Optional integrations

The following integrations are opt-in:

- Graphify
- code-mem / codebase-memory-mcp
- Superpowers
- Ponytail
- Caveman
- other compatible Agent Skills and MCP servers

Detection never implies permission. The harness uses an integration only when it is present, enabled, compatible, and useful for the task.

## Release checklist

1. Update the plugin version using semantic versioning.
2. Update the marketplace entry to the same plugin version.
3. Run the repository test suite.
4. Validate JSON manifests.
5. Run a clean local plugin installation test.
6. Verify optional extensions remain optional.
7. Review permissions and installer behavior.
8. Create a GitHub release and tag.
9. Test marketplace installation from a clean Claude Code environment.

The repository name is currently retained for history compatibility. The intended product identity is `adaptive-ai-coding-orchestrator`.
