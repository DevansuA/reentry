"""Redaction of likely secrets before anything enters the ledger.

The ledger is append-only, so redaction MUST happen at ingestion time.
You cannot scrub a secret out later without violating immutability.
"""

from __future__ import annotations

import re

_PATTERNS = [
    # bearer tokens (must run before key:value so the token itself is caught)
    re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9\-._~+/]{16,}=*)"),
    # key=value style assignments for sensitive-looking names
    re.compile(
        r"(?i)\b((?:api[_-]?key|secret|token|passwd|password|authorization|"
        r"access[_-]?key|private[_-]?key)\s*[=:]\s*)(\S+)"
    ),
    # common provider key shapes
    re.compile(r"\b(sk-[A-Za-z0-9]{16,})\b"),
    re.compile(r"\b(ghp_[A-Za-z0-9]{20,})\b"),
    re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)"),
]

REDACTED = "[REDACTED]"


def redact_text(text: str) -> str:
    for pat in _PATTERNS:
        if pat.groups >= 2:
            text = pat.sub(lambda m: m.group(1) + REDACTED, text)
        else:
            text = pat.sub(REDACTED, text)
    return text


def redact_payload(payload):
    """Recursively redact string values in a JSON-ish payload."""
    if isinstance(payload, dict):
        return {k: redact_payload(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(v) for v in payload]
    if isinstance(payload, str):
        return redact_text(payload)
    return payload
