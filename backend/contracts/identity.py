"""Server-derived request identity. Never constructed from client input.

Does not handle: authentication itself (M01 access), session storage, or 2FA
verification. This module only describes the *result* of those.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class AuthLevel(enum.StrEnum):
    """How strongly the current actor has proven identity.

    Ordered weakest to strongest by ``rank``. Actions declare a minimum level;
    Access compares and raises StaleAuth or Unauthenticated.
    """

    ANONYMOUS = "anonymous"
    PASSWORD = "password"
    TWO_FACTOR = "two_factor"

    @property
    def rank(self) -> int:
        """Return a comparable integer strength for this level."""
        return _AUTH_LEVEL_RANK[self]


_AUTH_LEVEL_RANK = {
    AuthLevel.ANONYMOUS: 0,
    AuthLevel.PASSWORD: 1,
    AuthLevel.TWO_FACTOR: 2,
}


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Trusted, server-derived facts about the caller of a service port.

    Every field is established server-side: ``school_id`` comes from the
    resolved deployment and session, never from a header or body. Passing a
    RequestContext is how a caller proves it went through the host.

    Does not handle: permission decisions (Access does that), or carrying
    request bodies. It is deliberately small so workers and exports can build
    one without an HTTP request.
    """

    actor_id: UUID
    school_id: UUID
    request_id: str
    auth_level: AuthLevel
    auth_time: datetime

    def __post_init__(self) -> None:
        """Reject a naive ``auth_time``.

        All timestamps in this system are timezone-aware UTC; a naive datetime
        silently compares wrong against freshness windows.
        """
        if self.auth_time.tzinfo is None:
            raise ValueError("auth_time must be timezone-aware UTC")
