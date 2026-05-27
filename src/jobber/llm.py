"""LLM backend abstraction.

Two backends:

  - `claude-cli`  shells out to the local `claude` CLI for one-shot prompts.
                  Uses the user's existing Claude Code authentication
                  (OAuth subscription or keychain). No ANTHROPIC_API_KEY required.

  - `anthropic-api`  uses the Anthropic Python SDK directly. Requires
                     ANTHROPIC_API_KEY. Default for users who run jobber
                     outside Claude Code.

Selection order:
  1. JOBBER_LLM_BACKEND env var (`claude-cli` or `anthropic-api`)
  2. `claude` on PATH  → claude-cli
  3. ANTHROPIC_API_KEY set → anthropic-api
  4. Error.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

DEFAULT_FAST_MODEL = "claude-sonnet-4-6"
DEFAULT_DRAFT_MODEL = "claude-opus-4-7"


@dataclass
class LLMConfig:
    fast_model: str = DEFAULT_FAST_MODEL
    draft_model: str = DEFAULT_DRAFT_MODEL
    max_tokens: int = 8000


def resolved_backend() -> str:
    """Return 'claude-cli' or 'anthropic-api' based on env + availability."""
    explicit = os.environ.get("JOBBER_LLM_BACKEND")
    if explicit:
        if explicit not in {"claude-cli", "anthropic-api"}:
            raise RuntimeError(
                f"Unknown JOBBER_LLM_BACKEND value: {explicit!r}. "
                "Use 'claude-cli' or 'anthropic-api'."
            )
        return explicit
    if shutil.which("claude"):
        return "claude-cli"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic-api"
    return "anthropic-api"  # will error with a clear message in the SDK path


def _call_anthropic_api(
    *,
    system: str,
    user: str,
    cache_system: bool,
    model: str,
    max_tokens: int,
) -> str:
    from anthropic import Anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set and the claude CLI was not found. "
            "Either install Claude Code (https://claude.com/code) or set "
            "ANTHROPIC_API_KEY to use the direct API backend."
        )
    client = Anthropic()
    system_blocks: list[dict] = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "".join(text_parts).strip()


_NEUTRAL_CWD = "/tmp"

# Tools we never want jobber's CLI subprocess to touch. Disabling them prevents
# the default Claude Code agent from inspecting the working directory, running
# git, editing files, or otherwise leaking project state into our output.
_DISALLOWED_TOOLS = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "Task",
    "TodoWrite",
    "Agent",
]


def _call_claude_cli(
    *,
    system: str,
    user: str,
    model: str,
    timeout: int = 1800,
) -> str:
    """Invoke the `claude` CLI in non-interactive mode.

    Runs with a neutral working directory and all tools disabled so the default
    Claude Code agent behavior cannot inject project state (uncommitted changes,
    CLAUDE.md, etc.) into the response.
    """
    cmd = [
        "claude",
        "--print",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--model",
        model,
        "--disallowedTools",
        *_DISALLOWED_TOOLS,
        "--append-system-prompt",
        system,
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=user,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_NEUTRAL_CWD,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"claude CLI exceeded {timeout}s timeout. The input may be too large "
            "for a single call; consider chunking. To raise the ceiling, set "
            "JOBBER_CLAUDE_TIMEOUT in the environment."
        ) from exc
    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-10:]
        raise RuntimeError(
            "claude CLI returned non-zero exit "
            f"({proc.returncode}). Stderr tail:\n" + "\n".join(stderr_tail)
        )
    return (proc.stdout or "").strip()


def call(
    *,
    system: str,
    user: str,
    cache_system: bool = True,
    model: str | None = None,
    config: LLMConfig | None = None,
    max_tokens: int | None = None,
) -> str:
    """Single-turn LLM call. Returns the assistant's text response.

    `cache_system` is honored only by the anthropic-api backend; the claude-cli
    backend has its own caching path under the hood.
    """
    cfg = config or LLMConfig()
    chosen_model = model or cfg.fast_model
    backend = resolved_backend()

    if backend == "claude-cli":
        timeout = int(os.environ.get("JOBBER_CLAUDE_TIMEOUT", "1800"))
        return _call_claude_cli(system=system, user=user, model=chosen_model, timeout=timeout)

    return _call_anthropic_api(
        system=system,
        user=user,
        cache_system=cache_system,
        model=chosen_model,
        max_tokens=max_tokens or cfg.max_tokens,
    )
