"""Cross-agent learning extraction kept outside task execution."""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from runtime.task_memory import record
@dataclass(frozen=True)
class Learning:
    outcome:str; detail:str; approach:str=""; command:str=""
class LearningSteward:
    _line=re.compile(r"^-\s*(worked|failed|partial|regressed|not-applicable)\s*\|\s*(.*?)\s*\|\s*(.*)$",re.I)
    def __init__(self,root:Path,*,run_id:str,task:str)->None:self.root=Path(root);self.run_id=run_id;self.task=task
    def extract(self,output:str)->list[Learning]:
        active=False; found=[]
        for raw in str(output).splitlines():
            line=raw.strip()
            if line.lower().startswith(("## learnings","## lessons")):active=True;continue
            if active and line.startswith("## "):break
            if active:
                m=self._line.match(line)
                if m:
                    outcome,approach,detail=m.groups()
                    if detail.strip():found.append(Learning(outcome.lower(),detail.strip(),approach.strip()))
        return found
    def persist(self,output:str,*,evidence_ids:Iterable[str]=())->list[dict[str,object]]:
        evidence=list(evidence_ids); rows=[]
        for learning in self.extract(output):
            rows.append(record(self.root,task=self.task,category="approach",outcome=learning.outcome,detail=learning.detail,approach=learning.approach or None,run_id=self.run_id,evidence_ids=evidence,source_agent="learning-steward",promotion="candidate"))
        return rows
    @staticmethod
    def prompt()->str:
        return """## Learning steward contract
You are not an execution agent. Review completed agent outcomes and capture only reusable lessons that can prevent future agents from repeating a mistake or reproduce a verified success.

Return a short `## LEARNINGS` section using exactly:
- worked | <approach> | <reusable lesson>
- failed | <approach> | <what failed and why>
- partial | <approach> | <what remains unsafe or incomplete>
- regressed | <approach> | <regression and evidence>

Keep the full useful detail within the memory guardrail. Record only evidence-backed observations. Do not turn guesses, generic advice, full logs, transcripts, or one-off task details into team memory. Execution agents stay focused on execution; you own learning and peripheral records.
"""
__all__=["Learning","LearningSteward"]
