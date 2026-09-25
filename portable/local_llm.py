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

    @classmethod
    def from_env(cls) -> "LocalLLMConfig":
        return cls(
            endpoint=os.environ.get("AER_LOCAL_LLM_ENDPOINT", cls.endpoint),
            model=os.environ.get("AER_LOCAL_LLM_MODEL", cls.model),
            timeout_seconds=max(5.0, float(os.environ.get("AER_LOCAL_LLM_TIMEOUT", cls.timeout_seconds))),
            num_ctx=max(512, int(os.environ.get("AER_LOCAL_LLM_CONTEXT", cls.num_ctx))),
            num_predict=max(64, int(os.environ.get("AER_LOCAL_LLM_MAX_TOKENS", cls.num_predict))),
            temperature=max(0.0, min(1.0, float(os.environ.get("AER_LOCAL_LLM_TEMPERATURE", cls.temperature)))),
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

def generate(prompt: str, *, config: LocalLLMConfig | None = None) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")
    cfg=config or LocalLLMConfig.from_env()
    payload=json.dumps({"model":cfg.model,"prompt":prompt,"stream":False,
                        "options":{"temperature":cfg.temperature,"num_ctx":cfg.num_ctx,"num_predict":cfg.num_predict}}).encode()
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
