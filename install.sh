#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

printf '%s\n' 'Installing Adaptive AI Coding Orchestrator...'
python3 "$REPO_ROOT/scripts/install_skill.py" --auto
printf '%s\n' '' 'For Claude Code, marketplace installation is also supported:'
printf '%s\n' '  /plugin marketplace add sourabhJainR/Hello_world_With_Structure'
printf '%s\n' '  /plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering'
