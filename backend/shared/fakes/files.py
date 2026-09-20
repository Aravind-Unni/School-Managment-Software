"""In-memory FakeFiles validating the same shapes as future M12.

Records calls for assertions. Defaults to deny unknown methods via AttributeError
is not used — unused Protocol methods raise ExplicitlyUnused when called with
unsupported purpose. Seedable with candidate (unconfirmed) and confirmed versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID, uuid4

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.evidence import ResourceGrant
from contracts.files import (
    ArtifactRef,
    FileDTO,
    FileEvidenceRef,
    ReadUrlDTO,
    UploadSession,
)
from contracts.identity import RequestContext

from .failures import FailureInjector

ANSWER_SHEET = "answer_sheet"
SUPPORTED_PIN_PURPOSES = frozenset({ANSWER_SHEET})


@dataclass
class _StoredFile:
    """Internal file record."""

    school_id: UUID
    purpose: str
    state: str
    review_confirmed: bool
    canonical_version: int | None
    sha256: str | None
    bytes: int | None = None


@dataclass
class FakeFiles:
    """Dictionary-backed FilesPort for standalone and tests."""

    failures: FailureInjector = field(default_factory=FailureInjector)
    _files: dict[UUID, _StoredFile] = field(default_factory=dict)
    _pins: dict[UUID, FileEvidenceRef] = field(default_factory=dict)
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    _clock: object | None = None

    def seed_file(
        self,
        *,
        file_id: UUID,
        school_id: UUID,
        purpose: str = ANSWER_SHEET,
        state: str = "accepted",
        review_confirmed: bool,
        canonical_version: int,
        sha256: str,
        bytes_count: int = 1024,
    ) -> FileDTO:
        """Install a deterministic file for scenario tests."""
        self._files[file_id] = _StoredFile(
            school_id=school_id,
            purpose=purpose,
            state=state,
            review_confirmed=review_confirmed,
            canonical_version=canonical_version,
            sha256=sha256,
            bytes=bytes_count,
        )
        return self.get_status_unscoped(file_id)

    def get_status_unscoped(self, file_id: UUID) -> FileDTO:
        """Return FileDTO without school check (seed helper)."""
        stored = self._files[file_id]
        return FileDTO(
            id=file_id,
            school_id=stored.school_id,
            state=stored.state,
            review_confirmed=stored.review_confirmed,
            canonical_version=stored.canonical_version,
            sha256=stored.sha256,
            bytes=stored.bytes,
        )

    def _record(self, name: str, *args, **kwargs) -> None:
        """Append a call record for assertions."""
        self.calls.append((name, args, kwargs))

    def begin_upload(
        self,
        context: RequestContext,
        purpose: str,
        client_name: str,
        declared_bytes: int,
        mime: str,
    ) -> UploadSession:
        """Open a synthetic upload session."""
        self._record(
            "begin_upload",
            purpose=purpose,
            client_name=client_name,
            declared_bytes=declared_bytes,
            mime=mime,
        )
        self.failures.maybe_fail("files.begin_upload")
        if purpose not in SUPPORTED_PIN_PURPOSES and purpose not in {
            "report_pdf",
            "import_csv",
        }:
            raise ValidationFailed("files.error.unsupported_purpose")
        from datetime import UTC, datetime

        instant = self._clock.now() if self._clock is not None else datetime.now(tz=UTC)
        return UploadSession(
            id=uuid4(),
            upload_url=f"https://fake-upload.example/{uuid4()}",
            expires_at=instant + timedelta(minutes=15),
            max_bytes=declared_bytes,
        )

    def get_status(self, context: RequestContext, file_id: UUID) -> FileDTO:
        """Return status or 404 for other-school/missing."""
        self._record("get_status", file_id=file_id)
        self.failures.maybe_fail("files.get_status")
        stored = self._files.get(file_id)
        if stored is None or stored.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return FileDTO(
            id=file_id,
            school_id=stored.school_id,
            state=stored.state,
            review_confirmed=stored.review_confirmed,
            canonical_version=stored.canonical_version,
            sha256=stored.sha256,
            bytes=stored.bytes,
        )

    def confirm_quality(
        self,
        context: RequestContext,
        file_id: UUID,
        candidate_version: int,
    ) -> FileDTO:
        """Confirm a candidate version."""
        self._record("confirm_quality", file_id=file_id, candidate_version=candidate_version)
        self.failures.maybe_fail("files.confirm_quality")
        self.get_status(context, file_id)
        stored = self._files[file_id]
        if stored.purpose not in SUPPORTED_PIN_PURPOSES:
            raise ValidationFailed("assessment.error.unconfirmed_evidence")
        stored.review_confirmed = True
        stored.canonical_version = candidate_version
        stored.state = "accepted"
        return self.get_status(context, file_id)

    def pin_evidence(
        self,
        context: RequestContext,
        file_id: UUID,
        canonical_version: int,
        binding_id: UUID,
    ) -> FileEvidenceRef:
        """Pin confirmed bytes; reject unconfirmed."""
        self._record(
            "pin_evidence",
            file_id=file_id,
            canonical_version=canonical_version,
            binding_id=binding_id,
        )
        self.failures.maybe_fail("files.pin_evidence")
        dto = self.get_status(context, file_id)
        if not dto.review_confirmed or dto.canonical_version != canonical_version:
            raise ValidationFailed("assessment.error.unconfirmed_evidence")
        if dto.sha256 is None:
            raise ValidationFailed("assessment.error.unconfirmed_evidence")
        ref = FileEvidenceRef(file_id=file_id, version=canonical_version, sha256=dto.sha256)
        self._pins[binding_id] = ref
        return ref

    def issue_read(self, context: RequestContext, grant: ResourceGrant) -> ReadUrlDTO:
        """Mint a fake read URL when grant is valid."""
        self._record("issue_read", grant_id=grant.grant_id)
        self.failures.maybe_fail("files.issue_read")
        now = self._clock.now() if self._clock is not None else grant.issued_at
        if not grant.is_valid_at(now):
            raise ObjectInaccessible("error.object_inaccessible")
        if grant.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return ReadUrlDTO(
            read_url=f"https://fake-read.example/{grant.resource_id}?g={grant.grant_id}",
            expires_at=grant.expires_at,
        )

    def store_artifact(
        self,
        context: RequestContext,
        purpose: str,
        content_ref: str,
        mime: str,
        sha256: str,
    ) -> ArtifactRef:
        """Store a synthetic report artifact."""
        self._record(
            "store_artifact",
            purpose=purpose,
            content_ref=content_ref,
            mime=mime,
            sha256=sha256,
        )
        self.failures.maybe_fail("files.store_artifact")
        return ArtifactRef(file_id=uuid4(), version=1, sha256=sha256, mime=mime)
