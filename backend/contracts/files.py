"""File-service DTOs owned by M12, consumed by modules that pin evidence.

Added for M05. The future M12 provider must return these shapes; FakeFiles
validates the same schemas in standalone.

Does not handle: storage bytes or HTTP upload transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadSession:
    """A short-lived browser upload handle."""

    id: UUID
    upload_url: str
    expires_at: datetime
    max_bytes: int


@dataclass(frozen=True, slots=True)
class FileDTO:
    """One stored file's status, including quality confirmation."""

    id: UUID
    school_id: UUID
    state: str
    review_confirmed: bool
    canonical_version: int | None = None
    sha256: str | None = None
    bytes: int | None = None
    width: int | None = None
    height: int | None = None
    profile_version: str | None = None

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted FileDTO shape."""
        return {
            "id": str(self.id),
            "school_id": str(self.school_id),
            "state": self.state,
            "canonical_version": self.canonical_version,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "width": self.width,
            "height": self.height,
            "profile_version": self.profile_version,
            "review_confirmed": self.review_confirmed,
        }


@dataclass(frozen=True, slots=True)
class FileEvidenceRef:
    """Pinned immutable file version for an evidence binding."""

    file_id: UUID
    version: int
    sha256: str

    def to_wire(self) -> dict[str, object]:
        """Serialise pin result."""
        return {
            "file_id": str(self.file_id),
            "version": self.version,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ReadUrlDTO:
    """Short-lived signed read URL for an authorised grant."""

    read_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """Service-generated report artifact pointer."""

    file_id: UUID
    version: int
    sha256: str
    mime: str
