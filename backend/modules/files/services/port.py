"""In-process FilesPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible, ValidationFailed, VersionConflict
from contracts.events import AuditRecord
from contracts.evidence import ResourceGrant
from contracts.files import ArtifactRef, FileDTO, FileEvidenceRef, ReadUrlDTO, UploadSession
from contracts.identity import RequestContext

from ..models import Derivative, EvidencePin, File, FileState
from . import read_tokens
from .authority import AuthorityGate
from .constants import ANSWER_SHEET, DEFAULT_MAX_BYTES, PURPOSE_MIMES
from .lifecycle import FilesLifecycle
from .storage import object_store
from .wire import file_to_dto


@dataclass(frozen=True, slots=True)
class FilesService:
    """Concrete FilesPort for in-process consumers."""

    gate: AuthorityGate
    platform: object
    clock: object
    lifecycle: FilesLifecycle

    def begin_upload(
        self,
        context: RequestContext,
        purpose: str,
        client_name: str,
        declared_bytes: int,
        mime: str,
    ) -> UploadSession:
        """Open an upload session for an approved purpose."""
        return self.lifecycle.begin_upload(
            context,
            purpose=purpose,
            client_name=client_name,
            declared_bytes=declared_bytes,
            mime=mime,
        )

    def get_status(self, context: RequestContext, file_id: UUID) -> FileDTO:
        """Return file status. Cross-school ids are ObjectInaccessible."""
        self.gate.require_action(context, "files.upload")
        row = self.gate.load_file(context, file_id)
        return file_to_dto(row)

    def confirm_quality(
        self,
        context: RequestContext,
        file_id: UUID,
        candidate_version: int,
    ) -> FileDTO:
        """Mark a candidate version as teacher-confirmed canonical."""
        wire = self.lifecycle.confirm_quality(context, file_id, candidate_version)
        return FileDTO(
            id=UUID(wire["id"]),
            school_id=UUID(wire["school_id"]),
            state=wire["state"],
            review_confirmed=wire["review_confirmed"],
            canonical_version=wire["canonical_version"],
            sha256=wire["sha256"],
            bytes=wire["bytes"],
            width=wire["width"],
            height=wire["height"],
            profile_version=wire["profile_version"],
        )

    def pin_evidence(
        self,
        context: RequestContext,
        file_id: UUID,
        canonical_version: int,
        binding_id: UUID,
    ) -> FileEvidenceRef:
        """Pin an immutable confirmed version into a binding."""
        row = self.gate.load_file(context, file_id)
        if row.purpose != ANSWER_SHEET:
            raise ValidationFailed("files.error.pin_not_answer_sheet")
        if not row.review_confirmed or row.canonical_version != canonical_version:
            raise ValidationFailed("files.error.unconfirmed_candidate")
        if row.sha256 is None:
            raise ValidationFailed("files.error.unconfirmed_candidate")
        existing = EvidencePin.objects.filter(binding_id=binding_id).first()
        if existing is not None:
            if (
                existing.file_id != file_id
                or existing.version != canonical_version
                or existing.sha256 != row.sha256
            ):
                raise VersionConflict("error.version_conflict")
            return FileEvidenceRef(
                file_id=existing.file_id, version=existing.version, sha256=existing.sha256
            )
        now = self.clock.now()
        with transaction.atomic():
            EvidencePin.objects.create(
                id=uuid4(),
                school_id=row.school_id,
                file_id=row.id,
                version=canonical_version,
                sha256=row.sha256,
                binding_id=binding_id,
                pinned_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="files.evidence_pinned",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": canonical_version, "binding_id": str(binding_id)},
                )
            )
        return FileEvidenceRef(file_id=row.id, version=canonical_version, sha256=row.sha256)

    def issue_read(self, context: RequestContext, grant: ResourceGrant) -> ReadUrlDTO:
        """Mint a short-lived read URL for a server-internal grant."""
        now = self.clock.now()
        if not grant.is_valid_at(now):
            raise ObjectInaccessible("error.object_inaccessible")
        if grant.school_id != context.school_id or grant.actor_id != context.actor_id:
            raise ObjectInaccessible("error.object_inaccessible")
        row = File.objects.filter(id=grant.resource_id).first()
        if row is None or row.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.require_file_read_grant(context, row)
        version = row.canonical_version
        if version is None:
            raise ObjectInaccessible("error.object_inaccessible")
        pin = EvidencePin.objects.filter(file_id=row.id, version=version).first()
        derivative = Derivative.objects.filter(
            file_id=row.id, kind="canonical", version=version
        ).first()
        if derivative is None:
            raise ObjectInaccessible("error.object_inaccessible")
        # Prefer pinned version integrity when a pin exists.
        if pin is not None and pin.sha256 != derivative.sha256:
            raise ObjectInaccessible("error.object_inaccessible")
        from ..models import FilesPolicy

        policy = FilesPolicy.objects.filter(school_id=row.school_id).first()
        seconds = policy.signed_read_seconds if policy else 60
        # Always through the API: object storage is private to the server.
        token = read_tokens.mint(row.id, version)
        url = f"/api/v1/file-bytes/{row.id}?token={token}"
        return ReadUrlDTO(read_url=url, expires_at=now + timedelta(seconds=seconds))

    def store_artifact(
        self,
        context: RequestContext,
        purpose: str,
        content_ref: str,
        mime: str,
        sha256: str,
    ) -> ArtifactRef:
        """Store a service-generated report artifact from an existing storage ref."""
        self.gate.require_action(context, "files.upload")
        if purpose not in PURPOSE_MIMES or purpose == ANSWER_SHEET:
            raise ValidationFailed("files.error.unsupported_purpose")
        allowed = PURPOSE_MIMES[purpose]
        if mime not in allowed:
            raise ValidationFailed("files.error.unsupported_mime")
        store = object_store()
        try:
            body = store.get(content_ref)
        except KeyError as exc:
            raise ValidationFailed("files.error.sha256_mismatch") from exc
        digest = __import__("hashlib").sha256(body).hexdigest()
        if digest != sha256:
            raise ValidationFailed("files.error.sha256_mismatch")
        if len(body) > DEFAULT_MAX_BYTES:
            raise ValidationFailed("files.error.bytes_limit")
        now = self.clock.now()
        file_id = uuid4()
        key = f"artifact/{context.school_id}/{file_id}/v1"
        store.put(key, body, content_type=mime)
        with transaction.atomic():
            File.objects.create(
                id=file_id,
                school_id=context.school_id,
                purpose=purpose,
                state=FileState.ACCEPTED,
                canonical_version=1,
                sha256=sha256,
                byte_size=len(body),
                review_confirmed=True,
                confirmed_at=now,
                version=1,
                created_at=now,
                updated_at=now,
            )
            Derivative.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                file_id=file_id,
                kind="canonical",
                version=1,
                storage_key=key,
                sha256=sha256,
                mime=mime,
                byte_size=len(body),
                created_at=now,
            )
        return ArtifactRef(file_id=file_id, version=1, sha256=sha256, mime=mime)
