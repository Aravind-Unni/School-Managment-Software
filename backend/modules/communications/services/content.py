"""Forbidden content detection for notices and template variables."""

from __future__ import annotations

import re

from contracts.errors import ValidationFailed

_SECRET_PATTERNS = (
    re.compile(r"password\s*[:=]", re.I),
    re.compile(r"totp", re.I),
    re.compile(r"otp\s*secret", re.I),
    re.compile(r"/api/v1/files/", re.I),
    re.compile(r"evidence[_-]?url", re.I),
    re.compile(r"answer[_-]?sheet", re.I),
    re.compile(r"\bmarks?\b.*=", re.I),
    re.compile(r"grade\s*[:=]\s*[A-F]", re.I),
)


def assert_safe_text(*parts: str) -> None:
    """Raise when body or variables look like secrets, evidence URLs or grades.

    Does not invent school policy beyond the contracted content bans.
    """
    blob = "\n".join(parts)
    for pattern in _SECRET_PATTERNS:
        if pattern.search(blob):
            raise ValidationFailed("communications.error.forbidden_content")


def assert_safe_variables(variables: dict[str, object]) -> None:
    """Validate stringified variable values against forbidden patterns."""
    parts = [f"{key}={value}" for key, value in variables.items()]
    assert_safe_text(*parts)
