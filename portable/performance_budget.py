"""Performance and resource budget contracts."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PerformanceBudget:
    latency_ms: float
    throughput_per_second: float
    memory_mb: float
    cpu_percent: float

@dataclass(frozen=True)
class PerformanceObservation:
    latency_ms: float
    throughput_per_second: float
    memory_mb: float
    cpu_percent: float

@dataclass(frozen=True)
class PerformanceReport:
    passed: bool
    violations: tuple[str,...]

class PerformanceBudgetGate:
    def evaluate(self,budget:PerformanceBudget,obs:PerformanceObservation)->PerformanceReport:
        if min(budget.latency_ms,budget.throughput_per_second,budget.memory_mb,budget.cpu_percent)<0: raise ValueError("budgets cannot be negative")
        v=[]
        if obs.latency_ms>budget.latency_ms: v.append("latency")
        if obs.throughput_per_second<budget.throughput_per_second: v.append("throughput")
        if obs.memory_mb>budget.memory_mb: v.append("memory")
        if obs.cpu_percent>budget.cpu_percent: v.append("cpu")
        return PerformanceReport(not v,tuple(v))

__all__=["PerformanceBudget","PerformanceObservation","PerformanceReport","PerformanceBudgetGate"]
