"""References to private stored objects, and server-internal access grants.

Does not handle: storage itself. ObjectStoragePort issues the actual signed
URLs; these DTOs only describe *what* may be reached and by whom.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """A pointer to one immutable object in private storage.

    Used for scanned answer sheets, fee receipts, transport documents and
    bulk-import source files. Carries no URL: a URL is minted per request after
    an Access check, so a leaked EvidenceRef alone grants nothing.

    Does not handle: versioning of the object. Evidence is immutable; a
    correction is a new EvidenceRef, which preserves the audit trail.
    """

    evidence_id: UUID
    school_id: UUID
    storage_key: str
    content_type: str
    byte_size: int
    sha256: str
    uploaded_at: datetime

    def __post_init__(self) -> None:
        """Reject an absolute or traversing storage key.

        A key beginning with '/' or containing '..' could escape the school's
        prefix and read another tenant's objects.
        """
        if self.storage_key.startswith("/") or ".." in self.storage_key:
            raise ValueError(f"unsafe storage_key: {self.storage_key!r}")
        if len(self.sha256) != 64:
            raise ValueError("sha256 must be 64 hex characters")


@dataclass(frozen=True, slots=True)
class ResourceGrant:
    """A narrow, time-boxed, server-minted permission to reach one resource.

    SERVER-INTERNAL. A grant is never accepted from a browser and never appears
    in a request body; the HTTP layer refuses any payload containing the key
    ``resource_grant``. It exists so that a worker or an export job can carry
    proof of an Access decision already made, without re-running the policy on
    a request context it does not have.

    Does not handle: revocation. Grants are short-lived instead; anything
    needing revocation must re-check Access.
    """

    grant_id: UUID
    school_id: UUID
    actor_id: UUID
    action: str
    resource_id: UUID
    issued_at: datetime
    expires_at: datetime

    def is_valid_at(self, instant: datetime) -> bool:
        """Return whether this grant is within its validity window.

        Assumes ``instant`` is timezone-aware UTC. Boundaries: issued_at is
        inclusive, expires_at is exclusive.
        """
        if instant.tzinfo is None:
            raise ValueError("instant must be timezone-aware")
        return self.issued_at <= instant < self.expires_at
