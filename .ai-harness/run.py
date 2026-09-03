#!/usr/bin/env python3
"""Production launcher: one run owns one session and one IO-aware context policy."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import context_engine
import engine
import knowledge_fabric
import p1_lifecycle
import extension_registry
from runtime import capability_catalog, loop_engine
from runtime.agent_turn import AgentTurnStateMachine
from runtime.intent_contract import create_intent_contract, semantic_alignment, verify_intent_contract
from runtime import learning

_original_make_run_dir = engine.make_run_dir
_original_build_prompt = engine.build_prompt
_original_run_task = engine.run_task
_session_dir: Path | None = None
_knowledge: dict = {}
_intent_contract: dict = {}
_capability_plan: dict = {}
_context_metadata: dict[str, dict] = {}


def session_make_run_dir() -> Path:
    global _session_dir
    if _session_dir is None:
        _session_dir = _original_make_run_dir()
    return _session_dir


def optimized_repository_map(limit: int = 500) -> str:
    return context_engine.build_repository_context(
        engine.ROOT,
        "",
        limit_files=min(limit, 180),
        budget_chars=9000,
    )


def _task_from_args(args) -> str:
    task = str(getattr(args, "task", "") or "").strip()
    jira_file = getattr(args, "jira_file", None)
    if jira_file:
        path = Path(jira_file)
        if path.is_file():
            task = (task + "\n\nJira context:\n" + path.read_text(encoding="utf-8")).strip()
    jira = getattr(args, "jira", None)
    if not task and jira:
        task = f"Work on Jira item {jira}"
    return task


def _load_or_create_intent(args, task: str) -> dict:
    global _intent_contract
    if getattr(args, "resume", None):
        path = Path(args.resume).resolve() / "intent-contract.json"
        if not path.is_file():
            raise engine.ConfigurationError("Resume requires intent-contract.json; refusing to resume without the original task contract")
        try:
            contract = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise engine.ConfigurationError("Resume intent-contract.json is invalid") from exc
        if not isinstance(contract, dict):
            raise engine.ConfigurationError("Resume intent contract must be an object")
        if task and task != str(contract.get("goal", "")).strip():
            raise engine.ConfigurationError("Resume task differs from the original intent; refusing to continue")
        _intent_contract = contract
        return contract
    _intent_contract = create_intent_contract(task, source=getattr(args, "jira", None) and "jira" or "prompt")
    return _intent_contract


def _prepare_knowledge(args, config: dict) -> None:
    global _knowledge
    if getattr(args, "resume", None):
        path = Path(args.resume).resolve() / "knowledge.json"
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    _knowledge = value
                    return
            except json.JSONDecodeError:
                pass
    task = _task_from_args(args)
    if not task and _intent_contract:
        task = str(_intent_contract.get("goal", "")).strip()
    if not task:
        _knowledge = {"sources": [], "evidence": "No task-specific knowledge requested."}
        return
    _knowledge = knowledge_fabric.collect(task, config)
    if _session_dir is not None:
        (_session_dir / "knowledge.json").write_text(json.dumps(_knowledge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (_session_dir / "knowledge.md").write_text("# Knowledge Fabric\n\n" + "Sources: " + ", ".join(_knowledge.get("sources", [])) + "\n\n" + str(_knowledge.get("evidence", "")) + "\n", encoding="utf-8")


def _trusted_learning_text(limit: int = 1800) -> str:
    rows = learning.trusted_advice(engine.ROOT, limit=12)
    if not rows:
        return "No trusted learned practices yet."
    lines = []
    for row in rows:
        prefix = "DO" if row.get("kind") == "do" else "DON'T"
        lines.append(f"{prefix}: {row.get('text', '')}")
    return engine.compact("\n".join(lines), limit)


def optimized_build_prompt(phase, task, source, jira, route, repo_map, memory, profile, history):
    global _context_metadata
    repo_tile, memory_tile, history_tile, metadata = context_engine.flash_context_prompt(task, repo_map, memory, history, budget_chars=12000)
    _context_metadata[str(phase)] = metadata if isinstance(metadata, dict) else {}
    prompt = _original_build_prompt(phase, task, source, jira, route, repo_tile, memory_tile, profile, history_tile)
    knowledge = str(_knowledge.get("evidence", "No external structural knowledge available."))[:6000]
    sources = ", ".join(_knowledge.get("sources", [])) or "none"
    contract = _intent_contract or create_intent_contract(task, source=source)
    alignment = semantic_alignment(contract, task + "\n" + history_tile)
    anchor = (
        "\n## Immutable task intent\n"
        "The following contract is the source of truth for this run. Do not reinterpret, replace, broaden, or silently narrow the goal. A nearby finding is not a new task. Deferred findings stay deferred.\n"
        + json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2)
        + f"\nIntent digest: {contract['intent_digest']}"
        + f"\nCurrent alignment score: {alignment['alignment_score']}"
        + "\nBefore acting, verify the planned action serves this goal and does not violate non-goals, boundaries, or protected behavior.\n"
        + "\n## Specialist capability plan\n"
        + json.dumps(_capability_plan or {"selected": ["builder"], "strategy": "fallback"}, ensure_ascii=False, indent=2)
        + "\nUse only the selected roles. Parallel work is permitted only for read-only roles marked safe. Each report must satisfy its declared contract.\n"
        + "\n## Trusted learned practices\n"
        + _trusted_learning_text()
    )
    return prompt + anchor + f"\n## Knowledge fabric\nSources: {sources}\n{knowledge}\n\n## IO-aware context\n{metadata}\n"


def _observe_agent_turns(code: int, plan: dict) -> list[dict]:
    """Build one validated state machine per provider phase from persisted provider output."""
    if _session_dir is None:
        return []
    outcomes = []
    phases = list(plan.get("phases", []))
    for index, phase in enumerate(phases, start=1):
        output_path = _session_dir / f"{phase}.output.md"
        if not output_path.exists():
            continue
        output = output_path.read_text(encoding="utf-8", errors="replace")
        turn = AgentTurnStateMachine(phase, _session_dir, f"{phase}-{index}")
        try:
            turn.transition("planning")
            turn.transition("acting")
            metadata = _context_metadata.get(phase, {})
            pages = metadata.get("pages", []) if isinstance(metadata, dict) else []
            context_digest = None
            if isinstance(metadata, dict):
                context_digest = str(metadata.get("context_digest")) if metadata.get("context_digest") else None
            turn.set_context([str(x) for x in pages] if isinstance(pages, list) else [], context_digest)
            turn.observe_tools(output)
            turn.observe_usage(((_session_dir / f"{phase}.prompt.md").read_text(encoding="utf-8") if (_session_dir / f"{phase}.prompt.md").exists() else ""), output)
            turn.observe_cache(output, context_digest)
            turn.transition("observing")
            turn.transition("verifying")
            validation_ok = code == 0
            if phase == "validate":
                manifest_path = _session_dir / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    validation_ok = bool((manifest.get("validation") or {}).get("passed", False))
            evidence = 1.0 if output.strip() else 0.0
            decision = turn.decide(
                verification_score=1.0 if validation_ok else 0.0,
                evidence_score=evidence,
                uncertainty=0.0 if validation_ok else 0.6,
                regressions=0 if validation_ok else 1,
                max_turns=int(plan.get("budget", {}).get("max_iterations", 1)),
            )
            turn.transition("deciding")
            terminal = "completed" if decision["action"] == "stop" and validation_ok else "stopped" if decision["action"] == "stop" else "repairing" if decision["action"] == "repair" else "completed" if code == 0 else "failed"
            if terminal == "repairing":
                turn.transition("repairing")
                turn.finish("stopped")
            else:
                turn.finish(terminal)
            outcomes.append(turn.snapshot())
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            outcomes.append({"turn_id": turn.turn.turn_id, "phase": phase, "state": "failed", "error": str(exc)})
    return outcomes


def optimized_run_task(args, config, logger):
    global _session_dir, _capability_plan
    _session_dir = Path(args.resume).resolve() if getattr(args, "resume", None) else None
    task = _task_from_args(args)
    if not task and getattr(args, "resume", None):
        manifest_path = Path(args.resume).resolve() / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                task = str(manifest.get("task", "")).strip()
            except json.JSONDecodeError:
                pass
    if not task and not getattr(args, "resume", None):
        return _original_run_task(args, config, logger)
    contract = _load_or_create_intent(args, task)
    if _session_dir is None:
        _session_dir = session_make_run_dir()
    (_session_dir / "intent-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _prepare_knowledge(args, config)
    profile = engine.profile_repository()
    route = engine.heuristic_route(str(contract["goal"]))
    extensions = extension_registry.detect_extensions()
    _capability_plan = capability_catalog.select_capabilities(route, extensions=extensions)
    capability_validation = capability_catalog.validate_plan(_capability_plan)
    if not capability_validation["passed"]:
        raise engine.ConfigurationError("Invalid specialist capability plan: " + ",".join(capability_validation["reasons"]))
    (_session_dir / "capability-plan.json").write_text(json.dumps(_capability_plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    loop_cfg = config.get("loop_engineering", {})
    plan = loop_engine.loop_plan(str(contract["goal"]), route, risk=str(loop_cfg.get("default_risk", "normal")), explicit_loop=bool(getattr(args, "loop", False)) and bool(loop_cfg.get("allow_explicit_bounded_loop", True)), configured_max=int(loop_cfg.get("max_explicit_iterations", 4)), extensions=extensions)
    (_session_dir / "loop-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    p1_lifecycle.start(_session_dir, str(contract["goal"]), "resume" if getattr(args, "resume", None) else "prompt", profile, route)
    code = _original_run_task(args, config, logger)
    manifest_path = _session_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            observed = {**contract, "goal": str(manifest.get("task", "")).strip()}
            check = verify_intent_contract(contract, observed)
            if not check["passed"]:
                (_session_dir / "intent-drift.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
                return 2
            p1_lifecycle.finish(_session_dir, manifest)
            validation = manifest.get("validation", {}) if isinstance(manifest.get("validation"), dict) else {}
            result = {"evidence_score": 1.0 if manifest.get("status") == "completed" else 0.4, "verification_score": 1.0 if validation.get("passed") else 0.0, "quality_score": 1.0 if code == 0 else 0.0, "uncertainty": 0.0 if code == 0 else 0.6, "regressions": 0}
            record = loop_engine.iteration_record(1, result)
            decision = loop_engine.next_action([record], plan["budget"])
            turns = _observe_agent_turns(code, plan)
            (_session_dir / "agent-turn-summary.json").write_text(json.dumps({"schema_version": "1.0", "turns": turns, "count": len(turns)}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (_session_dir / "loop-outcome.json").write_text(json.dumps({"record": record, "next": decision, "agent_turns": {"count": len(turns), "observable": sum(1 for t in turns if t.get("observations"))}}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            learning.evolve_run(_session_dir, config)
        except Exception as exc:
            (_session_dir / "p1-lifecycle.error.txt").write_text(str(exc) + "\n", encoding="utf-8")
            return 1 if code == 0 else code
    return code


engine.make_run_dir = session_make_run_dir
engine.repository_map = optimized_repository_map
engine.build_prompt = optimized_build_prompt
engine.run_task = optimized_run_task

if __name__ == "__main__":
    raise SystemExit(engine.main())
