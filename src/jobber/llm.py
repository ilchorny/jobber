"""Anthropic client wrapper with prompt caching.

A thin façade so we can:
  - swap models centrally (Sonnet for extraction/mapping, Opus for final drafts)
  - cache system prompts (voice rules, library index summaries) across calls
  - mock in tests

No personal data is referenced in this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from anthropic import Anthropic

DEFAULT_FAST_MODEL = "claude-sonnet-4-6"
DEFAULT_DRAFT_MODEL = "claude-opus-4-7"


@dataclass
class LLMConfig:
    fast_model: str = DEFAULT_FAST_MODEL
    draft_model: str = DEFAULT_DRAFT_MODEL
    max_tokens: int = 8000


def _client() -> Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it before running jobber, "
            "or use a credentials manager."
        )
    return Anthropic()


def call(
    *,
    system: str,
    user: str,
    cache_system: bool = True,
    model: str | None = None,
    config: LLMConfig | None = None,
    max_tokens: int | None = None,
) -> str:
    """Single-turn Anthropic call. Returns the assistant's text content.

    The `system` block is sent with `cache_control` enabled by default so
    repeated calls (e.g. mapping over many JDs) share a prompt cache.
    """
    cfg = config or LLMConfig()
    chosen_model = model or cfg.fast_model

    system_blocks: list[dict] = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    client = _client()
    response = client.messages.create(
        model=chosen_model,
        max_tokens=max_tokens or cfg.max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    # Concatenate text parts; tool use blocks are not expected here.
    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "".join(text_parts).strip()
