"""Standard-library logging, exception handling, local telemetry, and durable run journaling."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from runtime.run_journal import append_event as append_journal_event

HARNESS_NAME = "ai-coding-harness"


class HarnessError(Exception):
    """Base exception for expected harness failures."""


class ConfigurationError(HarnessError):
    """Raised when harness configuration is invalid."""


class ProviderError(HarnessError):
    """Raised when an AI provider cannot be started or completed."""


def configure_logging(run_dir: Path | None = None, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(HARNESS_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    if run_dir is not None:
        log_path = run_dir / "harness.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def emit_event(run_dir: Path | None, event: str, **fields: Any) -> None:
    """Emit local telemetry and a durable hash-chained journal event.

    The journal is a second, append-only record rather than the source of truth for telemetry. If
    journaling fails, normal telemetry must continue: observability must never become a run failure.
    """
    if run_dir is None:
        return
    record = {
        "timestamp": time.time(),
        "event": event,
        "pid": os.getpid(),
        **fields,
    }
    path = run_dir / "telemetry.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    try:
        append_journal_event(run_dir, event, fields)
    except (OSError, TypeError, ValueError):
        logging.getLogger(HARNESS_NAME).debug("durable event journal append failed", exc_info=True)


def exception_summary(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
    }
