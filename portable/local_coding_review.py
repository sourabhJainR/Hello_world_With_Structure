"""Local, read-only repository coding review runner."""
from __future__ import annotations
import argparse, json, re, subprocess
from dataclasses import dataclass
from pathlib import Path
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
    findings = []
    blocks = re.split(r"(?=^[-*]?\s*severity\s*:)", text, flags=re.I | re.M)
    for block in blocks:
        if "severity:" not in block.lower():
            continue
        def field(name: str) -> str:
            match = re.search(rf"^\s*[-*]?\s*{name}\s*:\s*(.+)$", block, flags=re.I | re.M)
            return match.group(1).strip() if match else ""
        try:
            confidence = float(field("confidence"))
        except ValueError:
            continue
        if not 0.0 <= confidence <= 1.0:
            continue
        finding = ReviewFinding(field("severity"), field("location"), field("evidence"),
                                field("impact"), field("remedy"), confidence)
        if all((finding.severity, finding.location, finding.evidence, finding.impact, finding.remedy)):
            findings.append(finding)
    return tuple(findings)

def deterministic_quality(text: str, repository_context: str) -> dict[str, float | int]:
    findings = parse_findings(text)
    if not findings:
        return {"findings": 0, "grounded": 0, "actionable": 0, "regression_aware": 0}
    context_lower = repository_context.lower()
    grounded = actionable = regression = 0
    for finding in findings:
        location = finding.location.lower()
        path = Path(location.split(":")[0]).as_posix().lower()
        grounded += int(bool(location) and (location in context_lower or path in context_lower))
        actionable += int(bool(finding.remedy and finding.impact))
        regression += int(any(t in (finding.impact + " " + finding.remedy).lower()
                              for t in ("regression", "compatib", "test", "break")))
    return {"findings": len(findings), "grounded": grounded,
            "actionable": actionable, "regression_aware": regression}

def repository_context(project_root: Path, task: str) -> str:
    command = ["python", "-m", "portable.repo_intelligence", str(project_root),
               "--mode=pack-task", f"--for={task}", "--token-budget=12000"]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout

def run(project_root: Path, task: str) -> dict[str, object]:
    context = repository_context(project_root, task)
    output = generate(coding_review_prompt(task, context))
    return {"task": task, "quality": deterministic_quality(output, context),
            "review": output,
            "calibration_note": "Structural quality is not correctness; independently verify findings before calibration."}

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
