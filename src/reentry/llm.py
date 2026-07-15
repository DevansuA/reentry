"""Optional LLM provider adapter.

ReEntry is deterministic-first: every fact in a capsule comes from the
ledger and derived state. An LLM, when configured, is used only for
narrow language tasks (currently: rewriting the objective line for
fluency). If no provider is configured or a call fails, the system
degrades gracefully to the deterministic output.

Providers are selected by environment:
    REENTRY_LLM_PROVIDER = anthropic | openai | none   (default: none)
    ANTHROPIC_API_KEY / OPENAI_API_KEY
    REENTRY_LLM_MODEL   (optional override)

No SDK dependency: plain HTTPS via urllib, 10s timeout, one retry.
"""

from __future__ import annotations

import json
import os
import urllib.request

TIMEOUT = 10


def _post(url: str, headers: dict, body: dict) -> dict | None:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    for _ in range(2):  # one retry
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read())
        except Exception:
            continue
    return None


def complete(prompt: str, max_tokens: int = 200) -> str | None:
    provider = os.environ.get("REENTRY_LLM_PROVIDER", "none").lower()
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        out = _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
             "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": os.environ.get("REENTRY_LLM_MODEL", "claude-haiku-4-5-20251001"),
             "max_tokens": max_tokens,
             "messages": [{"role": "user", "content": prompt}]},
        )
        if out and out.get("content"):
            return "".join(b.get("text", "") for b in out["content"]).strip()
    elif provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        out = _post(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
             "content-type": "application/json"},
            {"model": os.environ.get("REENTRY_LLM_MODEL", "gpt-4o-mini"),
             "max_tokens": max_tokens,
             "messages": [{"role": "user", "content": prompt}]},
        )
        if out and out.get("choices"):
            return out["choices"][0]["message"]["content"].strip()
    return None


def polish_capsule(capsule: dict) -> None:
    """Rewrite the objective line for fluency. Facts are never altered:
    the deterministic text is kept in `text_source` and the model output
    is discarded if it introduces content not present in the input."""
    obj = capsule.get("objective")
    if not obj:
        return
    polished = complete(
        "Rewrite this project objective as one clear sentence. Return only "
        "the sentence, add no new information:\n" + obj["text"])
    if polished and len(polished) < 300:
        # crude containment check: reject rewrites that add novel long tokens
        src_tokens = set(obj["text"].lower().split())
        new_tokens = [t for t in polished.lower().split()
                      if len(t) > 6 and t.strip(".,") not in src_tokens]
        if len(new_tokens) <= 2:
            obj["text_source"] = obj["text"]
            obj["text"] = polished
            obj["inference"] = "inferred"
