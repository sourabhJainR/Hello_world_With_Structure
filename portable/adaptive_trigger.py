"""LLM-chat entry point for durable, fire-and-forget AdaptiveRuntime work.

The trigger persists an execution intent first, then optionally dispatches it
on a bounded background worker. Persistence and claim semantics remain owned
by TriggerRuntime, while execution remains owned by AdaptiveRuntime.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from .adaptive_runtime import AdaptiveRuntime
from .trigger_runtime import TriggerEvent, TriggerRuntime


@dataclass(frozen=True)
class AdaptiveTriggerRequest:
    task: str
    project_root: str
    context: Mapping[str, Any]
    priority: str = "normal"


@dataclass(frozen=True)
class TriggerReceipt:
    trigger_id: str
    status: str
    accepted_at: str


@dataclass(frozen=True)
class TriggerOutcome:
    trigger_id: str
    status: str
    result: Any = None


Runner = Callable[[AdaptiveTriggerRequest, str], Any]


class AdaptiveTrigger:
    """Durable LLM-chat trigger with bounded fire-and-forget dispatch."""

    def __init__(
        self,
        trigger_runtime: TriggerRuntime,
        runner: Runner,
        *,
        max_workers: int = 1,
    ) -> None:
        if not isinstance(trigger_runtime, TriggerRuntime):
            raise TypeError("trigger_runtime must be a TriggerRuntime")
        if not callable(runner):
            raise TypeError("runner must be callable")
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.trigger_runtime = trigger_runtime
        self.runner = runner
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="aer-adaptive-trigger")
        self._lock = Lock()
        self._closed = False

    @classmethod
    def for_runtime(cls, runtime: AdaptiveRuntime, *, max_workers: int = 1) -> "AdaptiveTrigger":
        """Bind the trigger to one existing AdaptiveRuntime composition."""
        if not isinstance(runtime, AdaptiveRuntime):
            raise TypeError("runtime must be an AdaptiveRuntime")

        def runner(request: AdaptiveTriggerRequest, trigger_id: str) -> Any:
            provider = request.context.get("provider")
            return runtime.run(
                session_id=f"llm-chat:{trigger_id}",
                task_id=f"llm-chat:{trigger_id}",
                project_root=request.project_root,
                intent=request.task,
                provider=str(provider) if provider else None,
                context=request.context,
            )

        return cls(runtime.trigger_runtime, runner, max_workers=max_workers)

    def trigger_adaptive_runtime(
        self,
        task: str,
        project_root: Path | str,
        context: Mapping[str, Any] | None = None,
        *,
        priority: str = "normal",
        event_id: str | None = None,
        max_attempts: int = 3,
        fire_and_forget: bool = True,
    ) -> TriggerReceipt:
        """Persist a chat request and optionally dispatch it without blocking."""
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task is required")
        if priority not in {"low", "normal", "high"}:
            raise ValueError("priority must be one of: low, normal, high")
        root = str(Path(project_root).expanduser().resolve())
        request = AdaptiveTriggerRequest(task.strip(), root, dict(context or {}), priority)
        with self._lock:
            if self._closed:
                raise RuntimeError("adaptive trigger is closed")
            event = self.trigger_runtime.emit(
                "adaptive_runtime",
                {
                    "task": request.task,
                    "project_root": request.project_root,
                    "context": dict(request.context),
                    "priority": request.priority,
                },
                event_id=event_id,
                max_attempts=max_attempts,
            )
            if fire_and_forget:
                self._executor.submit(self._dispatch_event, event.event_id)
        return TriggerReceipt(event.event_id, event.status, event.created_at)

    def _dispatch_event(self, event_id: str) -> list[TriggerOutcome]:
        return self.trigger_runtime.dispatch_due(self._handle_event, limit=1)

    def _handle_event(self, event: TriggerEvent) -> TriggerOutcome:
        if event.kind != "adaptive_runtime":
            raise ValueError(f"unsupported adaptive trigger kind: {event.kind}")
        payload = event.payload
        request = AdaptiveTriggerRequest(
            task=str(payload["task"]),
            project_root=str(payload["project_root"]),
            context=dict(payload.get("context", {})),
            priority=str(payload.get("priority", "normal")),
        )
        result = self.runner(request, event.event_id)
        return TriggerOutcome(event.event_id, "accepted", result)

    def dispatch_once(self, *, limit: int = 20) -> list[TriggerOutcome]:
        """Synchronously drain currently due chat triggers; useful for service hosts."""
        results = self.trigger_runtime.dispatch_due(self._handle_event, limit=limit)
        return [item for item in results if isinstance(item, TriggerOutcome)]

    def close(self, *, wait: bool = False) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)


def trigger_adaptive_runtime(
    runtime: AdaptiveRuntime,
    task: str,
    project_root: Path | str,
    context: Mapping[str, Any] | None = None,
    *,
    priority: str = "normal",
    event_id: str | None = None,
    max_attempts: int = 3,
    fire_and_forget: bool = True,
) -> TriggerReceipt:
    """Convenience function for LLM tool/chat adapters."""
    trigger = AdaptiveTrigger.for_runtime(runtime)
    receipt = trigger.trigger_adaptive_runtime(
        task,
        project_root,
        context,
        priority=priority,
        event_id=event_id,
        max_attempts=max_attempts,
        fire_and_forget=fire_and_forget,
    )
    if not fire_and_forget:
        trigger.close(wait=True)
    return receipt


__all__ = ["AdaptiveTrigger", "AdaptiveTriggerRequest", "TriggerOutcome", "TriggerReceipt", "trigger_adaptive_runtime"]
