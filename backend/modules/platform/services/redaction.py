"""Redact secrets from audit diffs before they leave the service boundary."""

from __future__ import annotations

from typing import Any

from ..fixture_ids import SECRET_KEYS_REDACTED

REDACTED = "[REDACTED]"


def redact_value(key: str, value: Any) -> Any:
    """Return a redacted copy when ``key`` is a secret name.

    Does not handle: nested key paths beyond one level of dict recursion; lists
    of dicts are walked. Binary image payloads are replaced wholesale when the
    key suggests image/blob content.
    """
    lowered = key.lower()
    if lowered in SECRET_KEYS_REDACTED or any(s in lowered for s in SECRET_KEYS_REDACTED):
        return REDACTED
    if lowered in {"image", "image_bytes", "message_body", "raw_bytes"}:
        return REDACTED
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(redact_mapping(item))
            else:
                result.append(redact_value(key, item))
        return result
    return value


def redact_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied mapping with secret keys replaced."""
    return {key: redact_value(key, value) for key, value in payload.items()}


def redacted_diff(*, before: dict, after: dict) -> dict[str, dict]:
    """Build the public audit ``redacted_diff`` object."""
    return {"before": redact_mapping(dict(before)), "after": redact_mapping(dict(after))}
