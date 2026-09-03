#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from provider import normalize_cache, normalize_tool_event, normalize_usage, streaming_command


def test_claude_stream_tool_start():
    row = {"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {}}}}
    value = normalize_tool_event(row, 1)
    assert value["tool"] == "Read"
    assert value["status"] == "started"
    assert value["metadata"]["call_id"] == "toolu_1"


def test_gemini_tool_result():
    row = {"type": "tool_result", "tool_name": "read_file", "status": "completed", "duration_ms": 12, "output": "ok"}
    value = normalize_tool_event(row, 2)
    assert value["tool"] == "read_file"
    assert value["status"] == "completed"
    assert value["duration_ms"] == 12
    assert value["result_digest"]


def test_provider_usage_and_cache_are_preserved():
    row = {"type": "result", "usage": {"input_tokens": 100, "output_tokens": 25, "cache_read_input_tokens": 60, "cache_creation_input_tokens": 10}}
    usage = normalize_usage(row)
    assert usage == {"input_tokens": 100, "output_tokens": 25, "cached_input_tokens": 60, "reasoning_tokens": 0, "total_tokens": 0}
    cache = normalize_cache(row)
    assert cache["hit"] is True
    assert cache["read_tokens"] == 60
    assert cache["write_tokens"] == 10
    assert cache["source"] == "provider-usage"


def test_streaming_flags():
    assert "stream-json" in streaming_command(["claude", "-p"])
    assert "stream-json" in streaming_command(["gemini", "-p"])
    assert "--json" in streaming_command(["codex", "exec"])
