"""Opaque keyset cursors for M02 collections.

A cursor is base64 of the last row's UUID, bound to nothing else. It is opaque
to the client by contract: a client that parses one is relying on an
implementation detail that may change without a contract revision.

An invalid cursor is a 422, not an ignored parameter. Ignoring it would silently
return page one to a caller that believes it is on page nine, which reads as
data loss rather than as an error.
"""

from __future__ import annotations

import base64
import binascii
from uuid import UUID

from contracts.errors import ValidationFailed

#: Page sizes, frozen in the contract. A request above the cap is refused rather
#: than clamped: a caller that asked for 500 and silently got 100 will page
#: wrongly and never find out.
DEFAULT_PAGE_SIZE = 50
MAXIMUM_PAGE_SIZE = 100


def encode_cursor(last_id: UUID) -> str:
    """Return the opaque cursor that resumes after a given row."""
    return base64.urlsafe_b64encode(str(last_id).encode("ascii")).decode("ascii").rstrip("=")


def decode_cursor(raw: str | None) -> UUID | None:
    """Return the row id a cursor resumes after, or None when absent.

    Raises ValidationFailed on anything that is not a cursor this module issued.
    """
    if not raw:
        return None
    padded = raw + "=" * (-len(raw) % 4)
    try:
        return UUID(base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii"))
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationFailed("registry.error.invalid_cursor") from exc


def resolve_page_size(raw: str | None) -> int:
    """Return the page size for a request, refusing anything out of range.

    Absent means the default. Non-numeric, zero, negative or above the cap are
    all validation failures.
    """
    if raw is None or raw == "":
        return DEFAULT_PAGE_SIZE
    try:
        requested = int(raw)
    except ValueError as exc:
        raise ValidationFailed("registry.error.invalid_page_size") from exc
    if requested < 1 or requested > MAXIMUM_PAGE_SIZE:
        raise ValidationFailed("registry.error.invalid_page_size")
    return requested
