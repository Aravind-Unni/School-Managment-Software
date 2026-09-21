"""Retention hold, economical source purge and orphan upload cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible, VersionConflict
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import (
    EvidencePin,
    File,
    FilesPolicy,
    FileState,
    PurgeJob,
    PurgeJobState,
    SourceObject,
    UploadSession,
    UploadSessionState,
)
from .authority import AuthorityGate
from .backup import backup_verifier
from .storage import object_store
from .wire import file_to_wire, purge_job_to_wire


def _policy(school_id: UUID) -> FilesPolicy:
    """Return school policy row."""
    return FilesPolicy.objects.get(school_id=school_id)


@dataclass(frozen=True, slots=True)
class RetentionService:
    """Legal hold and economical source purge."""

    gate: AuthorityGate
    platform: object
    clock: object

    def set_retention_hold(
        self,
        context: RequestContext,
        file_id: UUID,
        *,
        legal_hold: bool,
        expected_version: int,
        reason: str | None,
    ) -> dict:
        """Set or clear legal hold with optimistic version."""
        del reason
        self.gate.require_retention(context)
        file_row = self.gate.load_file(context, file_id)
        if file_row.version != expected_version:
            raise VersionConflict("error.version_conflict")
        now = self.clock.now()
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked.legal_hold = legal_hold
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["legal_hold", "version", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="files.retention_hold",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"legal_hold": legal_hold},
                )
            )
            return file_to_wire(locked)

    def attempt_purge(self, file_id: UUID) -> dict:
        """Economical purge of source when confirm + backup + grace + no hold.

        Never deletes pinned canonical derivatives — only quarantine source bytes.
        """
        file_row = File.objects.filter(id=file_id).first()
        if file_row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        now = self.clock.now()
        job = PurgeJob.objects.create(
            id=uuid4(),
            school_id=file_row.school_id,
            source_id=file_row.source_id or uuid4(),
            file_id=file_row.id,
            state=PurgeJobState.PENDING,
            created_at=now,
        )
        block = self.purge_block_reason(file_row)
        if block is not None:
            job.state = PurgeJobState.BLOCKED
            job.block_reason = block
            job.completed_at = now
            job.save()
            return purge_job_to_wire(job)
        source = SourceObject.objects.filter(id=file_row.source_id).first()
        if source is None or source.purged_at is not None:
            job.state = PurgeJobState.BLOCKED
            job.block_reason = "files.error.purge_blocked"
            job.completed_at = now
            job.save()
            return purge_job_to_wire(job)
        policy = _policy(file_row.school_id)
        with transaction.atomic():
            locked = File.objects.select_for_update().get(id=file_row.id)
            # Canonical derivatives and pins stay; only source object is removed.
            if EvidencePin.objects.filter(file_id=locked.id).exists():
                pass
            locked.state = FileState.PURGING
            locked.updated_at = now
            locked.save(update_fields=["state", "updated_at"])
            object_store().delete(source.storage_key)
            source.purged_at = now
            source.save(update_fields=["purged_at"])
            locked.state = FileState.ACCEPTED
            locked.updated_at = now
            locked.save(update_fields=["state", "updated_at"])
            job.state = PurgeJobState.COMPLETED
            job.completed_at = now
            job.save()
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=locked.school_id,
                    event_type="files.source_purged",
                    occurred_at=now,
                    aggregate_id=locked.id,
                    aggregate_version=locked.version,
                    payload={
                        "file_id": str(locked.id),
                        "source_hash": source.sha256,
                        "policy_version": policy.policy_version,
                    },
                    correlation_id=str(locked.id),
                )
            )
        return purge_job_to_wire(job)

    def cleanup_orphans(self) -> int:
        """Abandon expired open uploads and delete quarantine objects."""
        now = self.clock.now()
        count = 0
        for row in UploadSession.objects.filter(
            state=UploadSessionState.OPEN, expires_at__lte=now
        )[:200]:
            object_store().delete(row.quarantine_key)
            row.state = UploadSessionState.ABANDONED
            row.save(update_fields=["state"])
            count += 1
        return count

    def purge_block_reason(self, file_row: File) -> str | None:
        """Return message_key when purge must not run, else None."""
        if not file_row.review_confirmed or file_row.state not in {
            FileState.ACCEPTED,
            FileState.PURGING,
        }:
            return "files.error.unconfirmed_candidate"
        if file_row.legal_hold:
            return "files.error.purge_blocked"
        if file_row.source_id is None:
            return "files.error.purge_blocked"
        if not backup_verifier().is_verified(file_row.source_id):
            return "files.error.purge_blocked"
        if file_row.confirmed_at is None:
            return "files.error.unconfirmed_candidate"
        policy = _policy(file_row.school_id)
        grace = timedelta(days=policy.grace_days)
        if self.clock.now() < file_row.confirmed_at + grace:
            return "files.error.purge_blocked"
        return None
