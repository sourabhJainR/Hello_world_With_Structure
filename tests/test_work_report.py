from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("work_report", ROOT / ".ai-harness" / "runtime" / "work_report.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_report_contains_required_engineering_sections(tmp_path: Path) -> None:
    report = MODULE.WorkReport(
        work_id="test-work",
        title="Test engineering report",
        objective="Validate reporting contract",
        assumptions=["A"],
        constraints=["B"],
        findings=["C"],
        risks=["D"],
        threats=["E"],
        regressions=["F"],
        hld=["HLD"],
        lld=["LLD"],
        references=[{"path": "src/example.py", "line": 10}],
        evidence=[{"type": "test", "status": "passed"}],
    )
    path = MODULE.WorkReportGenerator(tmp_path).write(report)
    html = path.read_text(encoding="utf-8")
    for marker in ("HLD", "LLD", "A", "B", "C", "D", "E", "F", "src/example.py", "flowchart", "sequenceDiagram", "latest.html"):
        assert marker in html
    assert (tmp_path / ".ai-harness" / "reports" / "latest.html").is_file()
