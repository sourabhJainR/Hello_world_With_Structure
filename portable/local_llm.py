"""Minimal local LLM fallback for AER.

Uses a local Ollama HTTP endpoint with no Python dependency. It is deliberately
read-only: the fallback can provide planning/review/synthesis text when the
primary provider is unavailable or exhausts its token budget, but it never
owns tools, credentials, repository mutation, or orchestration.
"""
from __future__ import annotations
import json, os, urllib.error, urllib.request
from dataclasses import dataclass

@dataclass(frozen=True)
class LocalLLMConfig:
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    model: str = "qwen2.5:3b"
    timeout_seconds: float = 120.0
    num_ctx: int = 4096
    num_predict: int = 768
    temperature: float = 0.1
    top_p: float = 0.9
    repeat_penalty: float = 1.05
    reasoning_effort: str = "medium"
    prompt_matrix: bool = True

    @classmethod
    def from_env(cls) -> "LocalLLMConfig":
        return cls(
            endpoint=os.environ.get("AER_LOCAL_LLM_ENDPOINT", cls.endpoint),
            model=os.environ.get("AER_LOCAL_LLM_MODEL", cls.model),
            timeout_seconds=max(5.0, float(os.environ.get("AER_LOCAL_LLM_TIMEOUT", cls.timeout_seconds))),
            num_ctx=max(512, int(os.environ.get("AER_LOCAL_LLM_CONTEXT", cls.num_ctx))),
            num_predict=max(64, int(os.environ.get("AER_LOCAL_LLM_MAX_TOKENS", cls.num_predict))),
            temperature=max(0.0, min(1.0, float(os.environ.get("AER_LOCAL_LLM_TEMPERATURE", cls.temperature)))),
            top_p=max(0.1, min(1.0, float(os.environ.get("AER_LOCAL_LLM_TOP_P", cls.top_p)))),
            repeat_penalty=max(0.8, min(1.5, float(os.environ.get("AER_LOCAL_LLM_REPEAT_PENALTY", cls.repeat_penalty)))),
            reasoning_effort=os.environ.get("AER_LOCAL_LLM_REASONING", cls.reasoning_effort).strip().lower(),
            prompt_matrix=os.environ.get("AER_LOCAL_LLM_MATRIX", "1").strip().lower() not in {"0", "false", "off", "no"},
        )

class LocalLLMError(RuntimeError):
    pass

def enabled() -> bool:
    return os.environ.get("AER_LOCAL_LLM_ENABLED", "0").strip().lower() in {"1","true","yes","on"}

def available(config: LocalLLMConfig | None = None) -> bool:
    cfg=config or LocalLLMConfig.from_env()
    req=urllib.request.Request(cfg.endpoint, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=min(3.0,cfg.timeout_seconds)) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False

_REASONING_MATRIX = {
    # These are behavioral controls, not copied model weights. They combine
    # publicly documented strengths: Kimi-style tool/agent decomposition,
    # Astra-style governed inference admission, Sonnet-style iterative
    # coding/error correction, and Fable-style long-horizon coherence.
    "kimi": ("decompose", "explicit_assumptions", "structured_output"),
    "astra": ("admission_check", "evidence_boundary", "fail_closed"),
    "sonnet": ("verify", "test_impact", "repair_loop"),
    "fable": ("long_horizon_state", "goal_continuity", "self_consistency"),
}

def _matrix_prompt(prompt: str, cfg: LocalLLMConfig) -> str:
    if not cfg.prompt_matrix:
        return prompt
    effort = cfg.reasoning_effort if cfg.reasoning_effort in {"low", "medium", "high"} else "medium"
    traits = ", ".join(item for group in _REASONING_MATRIX.values() for item in group)
    return (
        "LOCAL REASONING CONTRACT\n"
        f"effort={effort}; traits={traits}\n"
        "Use this bounded sequence: understand -> decompose -> check evidence -> "
        "reason -> verify -> state uncertainty. Do not invent tools, files, facts, "
        "credentials, or completed actions. For code, propose the smallest safe "
        "change and identify regression risk. For long tasks, preserve goals and "
        "state explicitly. If evidence is insufficient, say so and abstain.\n\n"
        "USER TASK:\n" + prompt
    )

def generate(prompt: str, *, config: LocalLLMConfig | None = None) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")
    cfg=config or LocalLLMConfig.from_env()
    prompt = _matrix_prompt(prompt, cfg)
    payload=json.dumps({"model":cfg.model,"prompt":prompt,"stream":False,
                        "options":{"temperature":cfg.temperature,"top_p":cfg.top_p,
                                   "repeat_penalty":cfg.repeat_penalty,
                                   "num_ctx":cfg.num_ctx,"num_predict":cfg.num_predict}}).encode()
    req=urllib.request.Request(cfg.endpoint,data=payload,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as response:
            body=json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise LocalLLMError(f"local LLM unavailable: {exc}") from exc
    text=body.get("response")
    if not isinstance(text,str) or not text.strip():
        raise LocalLLMError("local LLM returned no response")
    return text.strip()

def fallback_allowed(prompt: str) -> bool:
    text=prompt.lower()
    # Local fallback is advisory/read-only until it has an explicit tool-capable
    # integration. Mutating agents must remain on the authenticated provider.
    readonly=("read-only: true" in text or "patch_allowed: false" in text or
              "analysis-only" in text or "do not modify source" in text)
    return readonly

__all__=["LocalLLMConfig","LocalLLMError","enabled","available","generate","fallback_allowed"]
