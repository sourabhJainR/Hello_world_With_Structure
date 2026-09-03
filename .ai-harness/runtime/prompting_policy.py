#!/usr/bin/env python3
"""Provider-neutral prompting practices for autonomous coding runs.

The policy turns the task into a complete job specification: intent, why,
constraints, exit criteria, and response contract. It prefers reasons over
arbitrary prohibitions and asks for clarification only when material
ambiguity blocks safe execution. Deterministic harness verification remains
separate; the prompt does not waste model tokens on redundant self-check
instructions.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PromptQuality:
    has_task: bool
    has_context: bool
    has_why: bool
    has_exit_criteria: bool
    has_guardrails: bool
    has_response_contract: bool
    needs_interview: bool

    @property
    def complete(self) -> bool:
        return all((self.has_task, self.has_context, self.has_why,
                    self.has_exit_criteria, self.has_guardrails,
                    self.has_response_contract))


def assess_prompt(prompt: str) -> PromptQuality:
    text = str(prompt)
    lower = text.lower()
    task = bool(re.search(r"##\s*(task|goal|job)\b", lower))
    context = bool(re.search(r"##\s*(context|repository|background|profile)\b", lower))
    why = bool(re.search(r"##\s*(why|intent|purpose|outcome)\b", lower))
    done = bool(re.search(r"##\s*(exit criteria|acceptance|done|completion)\b", lower))
    guardrails = bool(re.search(r"##\s*(guardrails|constraints|boundaries|non-goals|non-negotiable)", lower))
    response = bool(re.search(r"##\s*(response contract|output contract|deliverable|report format)", lower))
    return PromptQuality(task, context, why, done, guardrails, response,
                         needs_interview=task and (not why or not done))


def compose(prompt: str) -> str:
    """Add the prompting contract without changing the user's task."""
    quality = assess_prompt(prompt)
    interview = (
        "If material information is missing and the ambiguity changes the solution, "
        "stop before making mutating changes and return `CLARIFICATION_NEEDED` with "
        "the smallest set of high-value questions. Do not ask questions whose answer "
        "can be established safely from the repository."
        if quality.needs_interview else
        "Do not start an interview when the repository and task contract already provide the needed information."
    )
    return prompt.rstrip() + "\n\n" + """## Prompting contract
Treat this as one complete job, not a sequence of instructions. Understand the task,
intent, constraints, repository context, and desired end state before choosing an approach.

## Why this matters
Use the stated intent and constraints to resolve ambiguity. Prefer the reason behind a
rule over a mechanical prohibition; when a local decision is needed, preserve the goal,
protected behavior, security boundary, and compatibility requirements.

## What done looks like
Finish when the task contract, acceptance criteria, and required evidence are satisfied.
Do not expand the job because you notice interesting adjacent improvements. Keep the final
response focused on outcome, changed scope, evidence, verification status, and any blockers.

## Response contract
Be concise and decision-oriented. Report only information needed to understand what was
changed or discovered, why the chosen approach satisfies the task, and what evidence exists.
Do not narrate every intermediate thought or repeat the task statement.

## Verification economy
Do not spend model tokens on redundant requests to "double-check" or repeat verification.
The harness owns deterministic tests, diff checks, security gates, and acceptance evidence;
use their results as evidence and correct failures when required.

## Clarification policy
""" + interview + "\n"""


def quality_dict(prompt: str) -> dict[str, object]:
    q = assess_prompt(prompt)
    return {
        "has_task": q.has_task,
        "has_context": q.has_context,
        "has_why": q.has_why,
        "has_exit_criteria": q.has_exit_criteria,
        "has_guardrails": q.has_guardrails,
        "has_response_contract": q.has_response_contract,
        "needs_interview": q.needs_interview,
        "complete": q.complete,
    }
