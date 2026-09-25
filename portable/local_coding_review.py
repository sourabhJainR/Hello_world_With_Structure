"""Local, read-only repository coding review runner.

It combines deterministic repository intelligence with the local LLM, then
scores the returned review for structural/evidence quality. Correctness remains
an independently verified outcome; the model cannot certify itself.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .coding_review_evaluation import CodingReviewEvaluator, CodingReviewObservation
from .local_llm import coding_review_prompt, generate


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    location: str
    evidence: str
    impact: str
    remedy: str
    confidence: float


def parse_findings(text: str) -> tuple[ReviewFinding, ...]:
    findings: list[ReviewFinding] = []
    blocks = re.split(r"(?=^[-*]?\\s*severity\\s*:)", text, flags=re.IGNORECASE | re.MULTILINE)
    for block in blocks:
        if "severity:" not in block.lower():
            continue
        def field(name: str) -> str:
            match = re.search(rf"^\\s*[-*]?\\s*{name}\\s*:\\s*(.+)$", block,
                              flags=re.IGNORECASE | re.MULTILINE)
            return match.group(1).strip() if match else ""
        try:
            confidence = float(field("confidence"))
        except ValueError:
            continue
        if not 0.0 <= confidence <= 1.0:
            continue
        finding = ReviewFinding(
            field("severity"), field("location"), field("evidence"),
            field("impact"), field("remedy"), confidence,
        )
        if all((finding.severity, finding.location, finding.evidence, finding.impact, finding.remedy)):
            findings.append(finding)
    return tuple(findings)


def deterministic_quality(text: str, repository_context: str) -> dict[str, float | int]:
    findings = parse_findings(text)
    if not findings:
        return {"findings": 0, "grounded": 0, "actionable": 0, "regression_aware": 0}
    grounded = 0
    actionable = 0
    regression = 0
    context_lower = repository_context.lower()
    for finding in findings:
        location = finding.location.lower()
        if location and (location in context_lower or Path(location.split(":")[0]).as_posix().lower() in context_lower):
            grounded += 1
        if finding.remedy and finding.impact:
            actionable += 1
        if any(token in (finding.impact + " " + finding.remedy).lower()
               for token in ("regression", "compatib", "test", "break")):
            regression += 1
    total = len(findings)
    return {
        "findings": total,
        "grounded": grounded,
        "actionable": actionable,
        "regression_aware": regression,
    }


def repository_context(project_root: Path, task: str) -> str:
    command = [
        "python", "-m", "portable.repo_intelligence", str(project_root),
        "--mode=pack-task", f"--for={task}", "--token-budget=12000",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def run(project_root: Path, task: str) -> dict[str, object]:
    context = repository_context(project_root, task)
    output = generate(coding_review_prompt(task, context))
    quality = deterministic_quality(output, context)
    return {
        "task": task,
        "quality": quality,
        "review": output,
        "calibration_note": (
            "Structural quality is not correctness. Feed independently verified "
            "outcomes into CodingReviewEvaluator before using calibration for admission."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a read-only local repository coding review")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.project_root), args.task), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ReviewFinding", "parse_findings", "deterministic_quality", "repository_context", "run"]
