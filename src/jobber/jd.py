"""JD ingestion: from URL or local file/text."""
from __future__ import annotations

import re
from pathlib import Path

import httpx


def fetch_url(url: str, *, timeout: float = 20.0) -> str:
    """Fetch a JD URL and return cleaned text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return html_to_text(resp.text)


def html_to_text(html: str) -> str:
    """Lightweight HTML stripper. Good enough; the LLM cleans up the rest."""
    # Drop scripts/styles entirely.
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level closing tags with line breaks for readability.
    html = re.sub(r"</(p|div|li|h[1-6]|tr|br|section|article)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Remove all remaining tags.
    text = re.sub(r"<[^>]+>", " ", html)
    # Unescape common HTML entities (lightweight).
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#x27;", "'")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    # Collapse whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ingest(jd_input: str) -> str:
    """Accept a URL, a file path, or raw text. Return clean JD text."""
    if jd_input.startswith(("http://", "https://")):
        return fetch_url(jd_input)
    p = Path(jd_input)
    if p.exists() and p.is_file():
        text = p.read_text(errors="replace")
        if p.suffix.lower() in {".html", ".htm"}:
            return html_to_text(text)
        return text.strip()
    # Treat as raw text.
    return jd_input.strip()
