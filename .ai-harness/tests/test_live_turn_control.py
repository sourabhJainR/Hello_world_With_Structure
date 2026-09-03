#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.agent_turn import AgentTurnStateMachine


def make_turn(tmp_path):
    turn = AgentTurnStateMachine("execute", tmp_path, "execute-live-test")
    turn.transition("planning")
    turn.transition("acting")
    return turn


def test_tool_failure_requests_repair_before_turn_completes(tmp_path):
    turn = make_turn(tmp_path)
    turn.transition("observing")
    turn.observe_tool({"sequence": 1, "tool": "run_tests", "status": "failed", "error": "exit 1", "result_digest": "bad"})
    decision = turn.decide_live(event="tool_result")
    assert decision["action"] == "repair"
    assert decision["reason"] == "tool-failure-observed"
    turn.transition("deciding")
    turn.transition("repairing")
    turn.finish("stopped")
    assert turn.turn.decision["interruptible"] is True


def test_tool_budget_can_stop_live_turn(tmp_path):
    turn = make_turn(tmp_path)
    for sequence in (1, 2):
        turn.transition("observing")
        turn.observe_tool({"sequence": sequence, "tool": "read_file", "status": "completed", "result_digest": f"result-{sequence}"})
        if sequence == 1:
            turn.transition("acting")
    decision = turn.decide_live(event="tool_result", max_tool_calls=2)
    assert decision["action"] == "stop"
    assert decision["reason"] == "live-tool-call-budget-exhausted"
