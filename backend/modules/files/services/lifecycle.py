"""Upload begin/complete, process, quality, reprocess, retention and purge."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.files import UploadSession as UploadSessionDTO
from contracts.identity import RequestContext
from shared.fakes.platform import EagerModeNotAsserted

from ..models import (
    Candidate,
    Derivative,
    EvidencePin,
    File,
    FilesPolicy,
    FileState,
    QualityReview,
    SourceObject,
    UploadSession,
    UploadSessionState,
)
from .authority import AuthorityGate
from .constants import (
    ALLOWED_PURPOSES,
    ANSWER_SHEET,
    DEFAULT_MAX_BYTES,
    PROFILE_DEFAULT,
    PROFILE_HIGHER_FIDELITY,
    PURPOSE_MIMES,
    UPLOAD_TTL_SECONDS,
)
from .processing import decode_and_compress
from .storage import object_store
from .wire import file_to_wire


def _policy(school_id: UUID) -> FilesPolicy:
    """Return school policy or raise if seed missing."""
    row = FilesPolicy.objects.filter(school_id=school_id).first()
    if row is None:
        raise ValidationFailed("error.validation_failed")
    return row


def _digest(body: bytes) -> str:
    """SHA-256 hex."""
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True, slots=True)
class FilesLifecycle:
    """HTTP + worker operations for the private file pipeline."""

    gate: AuthorityGate
    platform: object
    clock: object

    def begin_upload(
        self,
        context: RequestContext,
        *,
        purpose: str,
        client_name: str,
        declared_bytes: int,
        mime: str,
    ) -> UploadSessionDTO:
        """Open a quarantine session and return a put URL."""
        self.gate.require_action(context, "files.upload")
        if purpose not in ALLOWED_PURPOSES:
            raise ValidationFailed("files.error.unsupported_purpose")
        allowed = PURPOSE_MIMES.get(purpose, frozenset())
        if mime not in allowed:
            raise ValidationFailed("files.error.unsupported_mime")
        policy = _policy(context.school_id)
        max_bytes = policy.max_bytes_per_page if purpose == ANSWER_SHEET else DEFAULT_MAX_BYTES
        if declared_bytes < 1 or declared_bytes > max_bytes:
            raise ValidationFailed("files.error.bytes_limit")
        now = self.clock.now()
        session_id = uuid4()
        token = secrets.token_urlsafe(24)
        key = f"quarantine/{context.school_id}/{session_id}"
        expires = now + timedelta(seconds=UPLOAD_TTL_SECONDS)
        row = UploadSession.objects.create(
            id=session_id,
            school_id=context.school_id,
            actor_id=context.actor_id,
            purpose=purpose,
            client_name=client_name,
            declared_bytes=declared_bytes,
            mime=mime,
            state=UploadSessionState.OPEN,
            quarantine_key=key,
            put_token=token,
            expires_at=expires,
            max_bytes=max_bytes,
            created_at=now,
        )
        upload_url = self._put_url(row)
        self.platform.record_audit(
            AuditRecord(
                audit_id=uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                action="files.upload_begun",
                resource_id=row.id,
                occurred_at=now,
                request_id=context.request_id,
                after={"purpose": purpose},
            )
        )
        return UploadSessionDTO(
            id=row.id,
            upload_url=upload_url,
            expires_at=expires,
            max_bytes=max_bytes,
        )

    def put_quarantine_bytes(self, session_id: UUID, token: str, body: bytes) -> None:
        """Accept raw PUT into quarantine. No session auth — token is the grant."""
        row = UploadSession.objects.filter(id=session_id).first()
        if row is None or row.put_token != token:
            raise ObjectInaccessible("error.object_inaccessible")
        now = self.clock.now()
        if row.state != UploadSessionState.OPEN or row.expires_at <= now:
            raise StateConflict("files.error.invalid_state")
        if len(body) < 1 or len(body) > row.max_bytes:
            raise ValidationFailed("files.error.bytes_limit")
        object_store().put(row.quarantine_key, body, content_type=row.mime)

    def complete_upload(
        self, context: RequestContext, session_id: UUID, source_sha256: str
    ) -> dict:
        """Verify quarantine bytes and enqueue processing."""
        self.gate.require_action(context, "files.upload")
        row = UploadSession.objects.filter(id=session_id, school_id=context.school_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        now = self.clock.now()
        if row.state != UploadSessionState.OPEN:
            raise StateConflict("files.error.invalid_state")
        if row.expires_at <= now:
            row.state = UploadSessionState.EXPIRED
            row.save(update_fields=["state"])
            raise StateConflict("files.error.invalid_state")
        store = object_store()
        try:
            body = store.get(row.quarantine_key)
        except KeyError as exc:
            raise ValidationFailed("files.error.sha256_mismatch") from exc
        if len(body) > row.max_bytes:
            raise ValidationFailed("files.error.bytes_limit")
        digest = _digest(body)
        if digest != source_sha256:
            raise ValidationFailed("files.error.sha256_mismatch")
        with transaction.atomic():
            source = SourceObject.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                upload_session_id=row.id,
                storage_key=row.quarantine_key,
                sha256=digest,
                byte_size=len(body),
                mime=row.mime,
                backup_verified=False,
                created_at=now,
            )
            file_row = File.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                purpose=row.purpose,
                state=FileState.PROCESSING,
                source_id=source.id,
                review_confirmed=False,
                version=1,
                created_at=now,
                updated_at=now,
            )
            row.state = UploadSessionState.COMPLETED
            row.save(update_fields=["state"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="files.upload_completed",
                    resource_id=file_row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"state": "processing"},
                )
            )
        self._schedule_process(file_row.id)
        return {"file_id": str(file_row.id), "state": "processing"}

    def process_file(self, file_id: UUID, *, profile: str = PROFILE_DEFAULT) -> None:
        """Worker: decode/compress answer sheets or accept preserved import/report bytes."""
        file_row = File.objects.filter(id=file_id).first()
        if file_row is None or file_row.state not in {
            FileState.PROCESSING,
            FileState.CANDIDATE_READY,
        }:
            return
        source = SourceObject.objects.filter(id=file_row.source_id).first()
        if source is None or source.purged_at is not None:
            self._reject(file_row, "files.error.decode_rejected")
            return
        store = object_store()
        try:
            body = store.get(source.storage_key)
        except KeyError:
            self._reject(file_row, "files.error.decode_rejected")
            return
        policy = _policy(file_row.school_id)
        now = self.clock.now()
        if file_row.purpose != ANSWER_SHEET:
            key = f"canonical/{file_row.school_id}/{file_row.id}/v1"
            store.put(key, body, content_type=source.mime)
            with transaction.atomic():
                locked = File.objects.select_for_update().get(id=file_row.id)
                locked.state = FileState.ACCEPTED
                locked.canonical_version = 1
                locked.sha256 = source.sha256
                locked.byte_size = source.byte_size
                locked.review_confirmed = True
                locked.confirmed_at = now
                locked.updated_at = now
                locked.save()
                Derivative.objects.create(
                    id=uuid4(),
                    school_id=locked.school_id,
                    file_id=locked.id,
                    kind="canonical",
                    version=1,
                    storage_key=key,
                    sha256=source.sha256,
                    mime=source.mime,
                    byte_size=source.byte_size,
                    created_at=now,
                )
                self._emit(
                    locked,
                    "files.accepted",
                    {
                        "file_id": str(locked.id),
                        "canonical_version": 1,
                        "sha256": source.sha256,
                    },
                    now,
                )
            return
        try:
            result = decode_and_compress(
                body,
                max_megapixels=policy.max_megapixels,
                long_edge_px=policy.long_edge_px,
                webp_quality=policy.webp_quality,
                profile=profile,
            )
        except ValidationFailed as exc:
            self._reject(file_row, exc.message_key)
            return
        next_version = (
            Candidate.objects.filter(file_id=file_row.id).order_by("-version").first()
        )
        version = 1 if next_version is None else next_version.version + 1
        key = f"candidate/{file_row.school_id}/{file_row.id}/v{version}"
        store.put(key, result.body, content_type=result.mime)
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            Candidate.objects.create(
                id=uuid4(),
                school_id=locked.school_id,
                file_id=locked.id,
                version=version,
                storage_key=key,
                sha256=result.sha256,
                byte_size=len(result.body),
                width=result.width,
                height=result.height,
                profile_version=result.profile_version,
                mime=result.mime,
                created_at=now,
            )
            Derivative.objects.create(
                id=uuid4(),
                school_id=locked.school_id,
                file_id=locked.id,
                kind="candidate",
                version=version,
                storage_key=key,
                sha256=result.sha256,
                mime=result.mime,
                byte_size=len(result.body),
                created_at=now,
            )
            locked.state = FileState.CANDIDATE_READY
            locked.sha256 = result.sha256
            locked.byte_size = len(result.body)
            locked.width = result.width
            locked.height = result.height
            locked.profile_version = result.profile_version
            locked.updated_at = now
            locked.save()
            self._emit(
                locked,
                "files.candidate_ready",
                {
                    "file_id": str(locked.id),
                    "candidate_version": version,
                    "bytes": len(result.body),
                    "profile_version": result.profile_version,
                },
                now,
            )

    def confirm_quality(
        self, context: RequestContext, file_id: UUID, candidate_version: int
    ) -> dict:
        """Promote a candidate to immutable canonical."""
        self.gate.require_action(context, "files.review_quality")
        file_row = self.gate.load_file(context, file_id)
        if file_row.purpose != ANSWER_SHEET:
            raise ValidationFailed("files.error.pin_not_answer_sheet")
        if file_row.state != FileState.CANDIDATE_READY:
            raise StateConflict("files.error.invalid_state")
        candidate = Candidate.objects.filter(
            file_id=file_row.id, version=candidate_version
        ).first()
        if candidate is None:
            raise VersionConflict("error.version_conflict")
        now = self.clock.now()
        canonical_key = f"canonical/{file_row.school_id}/{file_row.id}/v{candidate_version}"
        body = object_store().get(candidate.storage_key)
        object_store().put(canonical_key, body, content_type=candidate.mime)
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            if locked.state != FileState.CANDIDATE_READY:
                raise StateConflict("files.error.invalid_state")
            locked.state = FileState.ACCEPTED
            locked.canonical_version = candidate_version
            locked.sha256 = candidate.sha256
            locked.byte_size = candidate.byte_size
            locked.width = candidate.width
            locked.height = candidate.height
            locked.profile_version = candidate.profile_version
            locked.review_confirmed = True
            locked.confirmed_at = now
            locked.updated_at = now
            locked.version += 1
            locked.save()
            QualityReview.objects.create(
                id=uuid4(),
                school_id=locked.school_id,
                file_id=locked.id,
                candidate_version=candidate_version,
                actor_id=context.actor_id,
                readability_confirmed=True,
                confirmed_at=now,
            )
            Derivative.objects.create(
                id=uuid4(),
                school_id=locked.school_id,
                file_id=locked.id,
                kind="canonical",
                version=candidate_version,
                storage_key=canonical_key,
                sha256=candidate.sha256,
                mime=candidate.mime,
                byte_size=candidate.byte_size,
                created_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="files.quality_confirmed",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"canonical_version": candidate_version},
                )
            )
            self._emit(
                locked,
                "files.accepted",
                {
                    "file_id": str(locked.id),
                    "canonical_version": candidate_version,
                    "sha256": candidate.sha256,
                },
                now,
            )
            return file_to_wire(locked)

    def reprocess(self, context: RequestContext, file_id: UUID, *, reason: str) -> dict:
        """Enqueue higher-fidelity candidate; never rewrite pinned versions."""
        del reason
        self.gate.require_action(context, "files.review_quality")
        file_row = self.gate.load_file(context, file_id)
        if file_row.purpose != ANSWER_SHEET:
            raise ValidationFailed("files.error.pin_not_answer_sheet")
        if EvidencePin.objects.filter(
            file_id=file_row.id, version=file_row.canonical_version or -1
        ).exists():
            # Pinned canonical stays; new candidate only from source.
            pass
        if file_row.source_id is None:
            raise StateConflict("files.error.invalid_state")
        source = SourceObject.objects.filter(id=file_row.source_id).first()
        if source is None or source.purged_at is not None:
            raise StateConflict("files.error.invalid_state")
        now = self.clock.now()
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            if locked.state == FileState.ACCEPTED and locked.review_confirmed:
                locked.state = FileState.PROCESSING
            elif locked.state not in {FileState.CANDIDATE_READY, FileState.REJECTED}:
                if locked.state != FileState.PROCESSING:
                    raise StateConflict("files.error.invalid_state")
            locked.updated_at = now
            locked.save(update_fields=["state", "updated_at"])
        self._schedule_process(file_row.id, profile=PROFILE_HIGHER_FIDELITY)
        file_row.refresh_from_db()
        return file_to_wire(file_row)

    def _reject(self, file_row: File, reason: str) -> None:
        """Mark rejected and emit files.rejected."""
        now = self.clock.now()
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            locked.state = FileState.REJECTED
            locked.rejection_reason = reason
            locked.updated_at = now
            locked.save(update_fields=["state", "rejection_reason", "updated_at"])
            self._emit(
                locked,
                "files.rejected",
                {"file_id": str(locked.id), "reason_code": reason},
                now,
            )

    def _emit(self, file_row: File, event_type: str, payload: dict, now) -> None:
        """Append outbox event in the caller's transaction."""
        self.platform.append_event(
            EventEnvelope(
                event_id=uuid4(),
                school_id=file_row.school_id,
                event_type=event_type,
                occurred_at=now,
                aggregate_id=file_row.id,
                aggregate_version=file_row.version,
                payload=payload,
                correlation_id=str(file_row.id),
            )
        )

    def _schedule_process(self, file_id: UUID, *, profile: str = PROFILE_DEFAULT) -> None:
        """Enqueue worker when available; otherwise process inline."""
        try:
            self.platform.enqueue(
                "modules.files.tasks.process_file",
                payload={"file_id": str(file_id), "profile": profile},
            )
        except EagerModeNotAsserted:
            self.process_file(file_id, profile=profile)

    def _put_url(self, row: UploadSession) -> str:
        """Module-local PUT URL, or signed MinIO URL when S3 is configured."""
        store = object_store()
        if hasattr(store, "presigned_put"):
            return store.presigned_put(row.quarantine_key, expires_in=UPLOAD_TTL_SECONDS)
        return f"/api/v1/quarantine/{row.id}?token={row.put_token}"
