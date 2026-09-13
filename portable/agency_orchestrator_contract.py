"""Contracts for integrating a host AI coding orchestrator with Agency Runtime.

The interfaces are deliberately small and provider-neutral. A host implementation
supplies the actual execution callback; Agency Runtime remains authoritative for
specialist planning, evidence, regression and release decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from .agency_runtime import Assignment, TaskProfile


@dataclass(frozen=True)
class HostExecutionContext:
    task_id: str
    sandbox: str = "repository-local"
    permission_scope: str = "host-controlled"
    mutation_mode: str = "bounded"


class HostExecutor(Protocol):
    def __call__(
        self,
        task: TaskProfile,
        assignments: list[Assignment],
        context: HostExecutionContext,
    ) -> Mapping[str, object]: ...


class HostPolicy(Protocol):
    def allow(self, context: HostExecutionContext) -> bool: ...


def validate_host_context(context: HostExecutionContext) -> None:
    """Reject host contexts that contradict the Agency execution boundary."""
    if not context.task_id.strip():
        raise ValueError("task_id is required")
    if context.sandbox != "repository-local":
        raise ValueError("agency integration requires repository-local sandbox declaration")
    if context.permission_scope != "host-controlled":
        raise ValueError("host must retain permission authority")
    if context.mutation_mode not in {"read-only", "bounded", "serialized"}:
        raise ValueError("unsupported mutation mode")
