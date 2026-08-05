from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, quote_plus, urlsplit, urlunsplit

REDACTED_VALUE = "********"

SENSITIVE_QUERY_KEY_PARTS = (
    "access_token",
    "apikey",
    "api_key",
    "auth",
    "credential",
    "key",
    "login",
    "pass",
    "password",
    "secret",
    "session",
    "sig",
    "signature",
    "token",
    "user",
    "username",
)

URL_PATTERN = re.compile(r"""https?://[^\s<>"']+""", re.IGNORECASE)
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"""(?P<key>\b(?:username|user|password|pass|passwd|pwd|token|auth|key|api[_-]?key|secret|signature|sig|access[_-]?token|session)\b)\s*=\s*(?P<value>[^\s&;,]+)""",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    compact = normalized.replace("_", "")
    return any(part in normalized or part in compact for part in SENSITIVE_QUERY_KEY_PARTS)


def redact_url(raw_url: str) -> str:
    split = urlsplit(raw_url.strip())
    if split.scheme.lower() not in {"http", "https"} or not split.netloc:
        return redact_text(raw_url)

    host = split.hostname or ""
    try:
        parsed_port = split.port
    except ValueError:
        parsed_port = None
    port = f":{parsed_port}" if parsed_port else ""
    if split.username or split.password:
        netloc = f"{REDACTED_VALUE}@{host}{port}"
    else:
        netloc = f"{host}{port}"

    query_items = []
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        query_items.append((key, REDACTED_VALUE if is_sensitive_key(key) else value))
    redacted_query = "&".join(
        f"{quote_plus(key)}={quote_plus(value, safe='*')}" for key, value in query_items
    )
    return urlunsplit((split.scheme, netloc, split.path, redacted_query, split.fragment))


def redact_text(value: str) -> str:
    redacted = URL_PATTERN.sub(lambda match: redact_url(match.group(0)), value)
    return SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group('key')}={REDACTED_VALUE}",
        redacted,
    )


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        redacted_mapping: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            redacted_mapping[key_text] = REDACTED_VALUE if is_sensitive_key(key_text) else redact_payload(item)
        return redacted_mapping
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [redact_payload(item) for item in value]
    return value
