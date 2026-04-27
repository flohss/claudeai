"""
Central API layer — single Anthropic client with retry, model routing,
timeout configuration, and prompt-caching helpers.
"""

import time
from collections.abc import Iterator
from typing import Any

import anthropic
from anthropic import APIConnectionError, APIStatusError, RateLimitError

# ── Model routing ──────────────────────────────────────────────────────────────
# Use Haiku for cheap/fast tasks, Sonnet for quality-critical ones.

MODEL_CHAT = "claude-sonnet-4-6"
MODEL_SMART = "claude-sonnet-4-6"   # condensation, narrative
MODEL_FAST = "claude-haiku-4-5-20251001"  # extraction, curiosity, summarization

# ── Client singleton ───────────────────────────────────────────────────────────

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=60.0)
    return _client


# ── Retry decorator ────────────────────────────────────────────────────────────

def call_with_retry(fn, max_attempts: int = 3, base_delay: float = 2.0):
    """
    Call fn() with exponential-backoff retry on transient errors.
    Retries on: RateLimitError, APIConnectionError, 5xx APIStatusError.
    """
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
    return response.content[0].text


# ── Chat completion (multi-turn) ───────────────────────────────────────────────

def chat_complete(
    messages: list[dict],
    *,
    system_blocks: list[dict],
    model: str = MODEL_CHAT,
    max_tokens: int = 2048,
) -> str:
    """
    Multi-turn chat with cached system prompt support.
    system_blocks: list of Anthropic content blocks, e.g.:
      [{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}]
    """
    def _call():
        return get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=messages,
        )
    response = call_with_retry(_call)
    return response.content[0].text


# ── Streaming chat ─────────────────────────────────────────────────────────────

def stream_chat(
    messages: list[dict],
    *,
    system_blocks: list[dict],
    model: str = MODEL_CHAT,
    max_tokens: int = 2048,
) -> Iterator[str]:
    """
    Stream a chat response token by token.
    Yields text deltas. Raises on API error (no retry — stream can't retry mid-flight).
    """
    with get_client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=messages,
    ) as stream:
        yield from stream.text_stream


# ── Prompt caching helpers ─────────────────────────────────────────────────────

def cached_block(text: str) -> dict:
    """Wrap a text block with ephemeral cache control."""
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


def plain_block(text: str) -> dict:
    """Plain text block (not cached)."""
    return {"type": "text", "text": text}
