"""Minimal OpenAI-compatible client for pipeline full-mode LLM steps."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any, Dict, Optional


BASE_URL = os.getenv("PIPELINE_LLM_BASE_URL", "https://api.openai.com")
API_KEY = os.getenv("PIPELINE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("PIPELINE_LLM_MODEL", "gpt-5.2")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("PIPELINE_LLM_TIMEOUT_SECONDS", "20"))

_GLOBAL_LLM_ENABLED = os.getenv("PIPELINE_ENABLE_LLM", "1").strip().lower() not in {"0", "false", "no"}
_STAGE_LLM_OVERRIDES = {
    1: os.getenv("PIPELINE_STAGE1_ENABLE_LLM"),
    2: os.getenv("PIPELINE_STAGE2_ENABLE_LLM"),
    3: os.getenv("PIPELINE_STAGE3_ENABLE_LLM"),
}
_thread_local = threading.local()

_FAILURE_BACKOFF_SECONDS = 60
_failure_lock = threading.Lock()
_failure_until = 0.0


def set_current_stage(stage: int | None) -> None:
    """Set the active pipeline stage (1/2/3) for per-stage LLM gating."""
    _thread_local.current_stage = stage


def _is_llm_enabled() -> bool:
    """Check LLM availability respecting per-stage overrides."""
    current_stage: int | None = getattr(_thread_local, "current_stage", None)
    if current_stage is not None:
        override = _STAGE_LLM_OVERRIDES.get(current_stage)
        if override is not None:
            return override.strip().lower() not in {"0", "false", "no"}
    return _GLOBAL_LLM_ENABLED


def _chat_completions_url(base_url: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if not normalized:
        normalized = "https://api.openai.com"
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return normalized + "/chat/completions"
    return normalized + "/v1/chat/completions"


def _extract_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts)

    output = payload.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = min((index for index in (text.find("{"), text.find("[")) if index >= 0), default=-1)
    if start < 0:
        return None
    for end in range(len(text), start, -1):
        chunk = text[start:end].strip()
        if not chunk or chunk[-1] not in "}]" or chunk[0] not in "{[":
            continue
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    return None


@lru_cache(maxsize=128)
def _cached_chat_json(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> Any:
    body = {
        "model": MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        url=_chat_completions_url(BASE_URL),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _extract_json(_extract_text(payload))


def chat_json(system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 1200) -> Optional[Any]:
    global _failure_until
    if not _is_llm_enabled() or not API_KEY:
        return None
    with _failure_lock:
        if time.time() < _failure_until:
            return None
    try:
        return _cached_chat_json(system_prompt, user_prompt, float(temperature), int(max_tokens))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError):
        with _failure_lock:
            _failure_until = time.time() + _FAILURE_BACKOFF_SECONDS
        return None
