"""Release policy for agency execution receipts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .agency_quality import ReviewFinding


@dataclass(frozen=True)
class ReleaseDecision:
    status: str
    reasons: tuple[str, ...]

    @property
    def releasable(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict:
        return {"status": self.status, "releasable": self.releasable, "reasons": self.reasons}


def decide_release(
    score: int,
    threshold: int,
    hard_gates: Mapping[str, bool],
    findings: Iterable[ReviewFinding] = (),
    unresolved_risks: Iterable[str] = (),
) -> ReleaseDecision:
    """Never infer success from score alone; distinguish blocked from failed work."""
    reasons: list[str] = []
    if not hard_gates:
        return ReleaseDecision("blocked", ("no hard gates were supplied",))
    missing = sorted(k for k, value in hard_gates.items() if not value)
    if missing:
        reasons.append("failed hard gates: " + ", ".join(missing))
    material = [f for f in findings if f.severity in {"blocker", "material"}]
    if material:
        reasons.extend(f"{f.severity}: {f.message}" for f in material)
    risks = [str(x).strip() for x in unresolved_risks if str(x).strip()]
    if risks:
        reasons.extend("unresolved risk: " + x for x in risks)
    if missing or material or risks:
        return ReleaseDecision("failed", tuple(reasons))
    if score < threshold:
        return ReleaseDecision("failed", (f"score {score} is below threshold {threshold}",))
    return ReleaseDecision("passed", ("all release conditions satisfied",))
