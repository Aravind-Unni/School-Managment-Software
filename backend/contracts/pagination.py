"""Opaque-cursor pagination. Every collection endpoint returns this shape.

Does not handle: offset/limit. Offsets are deliberately unsupported because a
4,000-student roster shifts under pagination and offsets silently skip rows.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

ItemT = TypeVar("ItemT")

#: Hard ceiling on page size, enforced by the shared list view regardless of
#: what a module asks for.
MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class Page[ItemT]:
    """One page of results plus the cursor for the next.

    ``next_cursor`` is None exactly when there are no further rows.
    """

    items: tuple[ItemT, ...]
    next_cursor: str | None = None

    def to_wire(self, serialise: object = None) -> dict[str, object]:
        """Serialise to ``{"items": [...], "next_cursor": ...}``.

        ``serialise`` is an optional callable applied to each item; when None,
        items are assumed already wire-ready.
        """
        rendered: Sequence[object]
        if serialise is None:
            rendered = list(self.items)
        else:
            rendered = [serialise(item) for item in self.items]  # type: ignore[operator]
        return {"items": list(rendered), "next_cursor": self.next_cursor}


def encode_cursor(payload: dict[str, object]) -> str:
    """Encode keyset position into an opaque URL-safe string.

    Opaque means clients must not parse it. It is base64 of compact JSON, not
    encryption; it carries no secrets, only sort-key values.
    """
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, object]:
    """Decode a cursor produced by encode_cursor.

    Raises ValueError on anything malformed, so a hand-edited cursor becomes a
    422 rather than a 500.
    """
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding)
        decoded = json.loads(raw)
    except Exception as exc:
        raise ValueError("malformed cursor") from exc
    if not isinstance(decoded, dict) or not decoded:
        # An empty object is not a position. Rejecting it here makes a
        # hand-edited cursor a 422 at the boundary rather than a KeyError deep
        # inside the keyset comparison.
        raise ValueError("malformed cursor")
    return decoded


def clamp_page_size(requested: int | None) -> int:
    """Return a safe page size, defaulting and capping as needed."""
    if requested is None or requested <= 0:
        return DEFAULT_PAGE_SIZE
    return min(requested, MAX_PAGE_SIZE)
