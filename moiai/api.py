"""
Central API layer — single Anthropic client with retry, model routing,
timeout configuration, prompt-caching helpers, and cost tracking.
"""

import time
from collections.abc import Iterator
from typing import Any

import anthropic
import httpx
from anthropic import APIConnectionError, APIStatusError, RateLimitError

# ── Model routing ──────────────────────────────────────────────────────────────

MODEL_CHAT = "claude-sonnet-4-6"
MODEL_SMART = "claude-sonnet-4-6"   # condensation, narrative
MODEL_FAST = "claude-haiku-4-5-20251001"  # extraction, curiosity, summarization

# Override with user config (if any) — must come before PRICING dict
try:
    from .models_config import load as _load_mc
    _mc = _load_mc()
    MODEL_CHAT = _mc.get("chat", MODEL_CHAT)
    MODEL_SMART = _mc.get("smart", MODEL_SMART)
    MODEL_FAST = _mc.get("fast", MODEL_FAST)
except Exception:
    pass

# ── Pricing (USD per million tokens) ──────────────────────────────────────────

_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":           {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-sonnet-4-6":         {"input": 3.0,  "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.0,  "cache_read": 0.10, "cache_write": 1.25},
}

_PRICING_FALLBACK = _PRICING["claude-sonnet-4-6"]

# ── Session cost tracking ──────────────────────────────────────────────────────

_session_cost: float = 0.0
_last_call_cost: float = 0.0


def _compute_cost(usage: Any, model: str) -> float:
    p = _PRICING.get(model, _PRICING_FALLBACK)
    return (
        getattr(usage, "input_tokens", 0)            * p["input"]
        + getattr(usage, "output_tokens", 0)         * p["output"]
        + getattr(usage, "cache_read_input_tokens", 0)    * p["cache_read"]
        + getattr(usage, "cache_creation_input_tokens", 0) * p["cache_write"]
    ) / 1_000_000


def _track(usage: Any, model: str) -> None:
    global _session_cost, _last_call_cost
    cost = _compute_cost(usage, model)
    _last_call_cost = cost
    _session_cost += cost


def get_last_call_cost() -> float:
    return _last_call_cost


def get_session_cost() -> float:
    return _session_cost


def reset_session_cost() -> None:
    global _session_cost, _last_call_cost
    _session_cost = 0.0
    _last_call_cost = 0.0


# ── Debug mode ─────────────────────────────────────────────────────────────────

_debug_enabled: bool = False
_last_debug: dict = {}
_debug_log: list[dict] = []


def set_debug(enabled: bool) -> None:
    global _debug_enabled
    _debug_enabled = enabled


def get_debug_enabled() -> bool:
    return _debug_enabled


def get_last_debug() -> dict:
    return _last_debug


def get_debug_log() -> list[dict]:
    return list(_debug_log)


def clear_debug_log() -> None:
    _debug_log.clear()


_debug_chat_only: bool = True  # only capture main chat calls, not background extraction


def _store_debug(model: str, system_blocks, messages, response_text: str, usage) -> None:
    p = _PRICING.get(model, _PRICING_FALLBACK)
    input_tok   = getattr(usage, "input_tokens", 0)
    output_tok  = getattr(usage, "output_tokens", 0)
    cache_read  = getattr(usage, "cache_read_input_tokens", 0)
    cache_write = getattr(usage, "cache_creation_input_tokens", 0)
    entry = {
        "model":        model,
        "system_blocks": system_blocks,
        "messages":     messages,
        "response":     response_text,
        "usage": {
            "input_tokens":        input_tok,
            "output_tokens":       output_tok,
            "cache_read_tokens":   cache_read,
            "cache_write_tokens":  cache_write,
        },
        "cost": {
            "input":       input_tok   * p["input"]       / 1_000_000,
            "output":      output_tok  * p["output"]      / 1_000_000,
            "cache_read":  cache_read  * p["cache_read"]  / 1_000_000,
            "cache_write": cache_write * p["cache_write"] / 1_000_000,
        },
    }
    _last_debug.update(entry)
    import copy
    _debug_log.append(copy.deepcopy(entry))


# ── Client singleton ───────────────────────────────────────────────────────────

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            timeout=httpx.Timeout(
                connect=10.0,
                read=600.0,
                write=30.0,
                pool=10.0,
            )
        )
    return _client


# ── Retry decorator ────────────────────────────────────────────────────────────

def call_with_retry(fn, max_attempts: int = 3, base_delay: float = 2.0):
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except RateLimitError as e:
            last_exc = e
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
        except APIConnectionError as e:
            last_exc = e
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
        except APIStatusError as e:
            last_exc = e
            if e.status_code >= 500 and attempt < max_attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ── Simple text completion ─────────────────────────────────────────────────────

def complete(
    prompt: str,
    *,
    model: str = MODEL_FAST,
    system: str = "",
    max_tokens: int = 1024,
) -> str:
    """Single-turn text completion with retry."""
    def _call():
        return get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    response = call_with_retry(_call)
    _track(response.usage, model)
    text = response.content[0].text
    if _debug_enabled and not _debug_chat_only:
        _store_debug(model, [{"type": "text", "text": system}],
                     [{"role": "user", "content": prompt}], text, response.usage)
    return text


# ── Chat completion (multi-turn) ───────────────────────────────────────────────

def chat_complete(
    messages: list[dict],
    *,
    system_blocks: list[dict],
    model: str = MODEL_CHAT,
    max_tokens: int = 2048,
) -> str:
    def _call():
        return get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=messages,
        )
    response = call_with_retry(_call)
    _track(response.usage, model)
    text = response.content[0].text
    if _debug_enabled and not _debug_chat_only:
        _store_debug(model, system_blocks, messages, text, response.usage)
    return text


# ── Streaming chat ─────────────────────────────────────────────────────────────

def stream_chat(
    messages: list[dict],
    *,
    system_blocks: list[dict],
    model: str = MODEL_CHAT,
    max_tokens: int = 2048,
) -> Iterator[str]:
    """Stream a chat response token by token. Tracks cost after stream ends."""
    full_text = ""
    with get_client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
            yield chunk
        usage = stream.get_final_message().usage
        _track(usage, model)
        if _debug_enabled:  # always capture stream_chat — it's always the main chat
            _store_debug(model, system_blocks, messages, full_text, usage)


# ── Prompt caching helpers ─────────────────────────────────────────────────────

def cached_block(text: str) -> dict:
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


def plain_block(text: str) -> dict:
    return {"type": "text", "text": text}
