# Claude Code entry point

Use `AGENTS.md` for repository-wide rules and `.agents/skills/ai-coding-orchestrator/SKILL.md` for adaptive routing.

For non-trivial requests, use the adaptive orchestrator before editing. It determines whether the task needs research, POC, debug, grill, review, or only a focused implementation path. Use `.ai-harness/run.py` for repeatable execution and evidence capture.