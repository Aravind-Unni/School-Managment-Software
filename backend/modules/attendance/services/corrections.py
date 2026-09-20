"""Audited corrections of submitted attendance entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts

from ..models import (
    AttendanceAmendment,
    AttendanceEntry,
    AttendanceSession,
    AttendanceStatus,
    SessionState,
)
from .drafts import WRITABLE
from .wire import entry_to_wire


@dataclass(frozen=True, slots=True)
class CorrectionService:
    """Correct a submitted mark with a mandatory reason."""

    access: object
    platform: object
    clock: object

    def correct(
        self,
        context: RequestContext,
        *,
        entry_id: UUID,
        status: str,
        reason: str,
        expected_version: int,
    ) -> dict[str, object]:
        """Apply an audited amendment. Requires recent 2FA."""
        if not reason or not reason.strip():
            raise ValidationFailed("attendance.error.reason_required")
        if status not in WRITABLE:
            raise ValidationFailed("attendance.error.invalid_status")

        try:
            entry = AttendanceEntry.objects.select_related("session").get(id=entry_id)
        except AttendanceEntry.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        session = entry.session
        if session.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if session.state != SessionState.SUBMITTED:
            raise StateConflict("attendance.error.correction_not_submitted")
        if entry.version != expected_version:
            raise VersionConflict("error.version_conflict")

        self.access.require_recent_2fa(context, max_age_seconds=300)
        self.access.check(
            context,
            "attendance.correct",
            ScopeFacts(
                resource_school_id=session.school_id,
                section_id=session.section_id,
                subject_id=session.subject_id,
                effective_date=session.date,
            ),
        )

        old_status = entry.status
        if old_status == AttendanceStatus.UNMARKED:
            raise ValidationFailed("attendance.error.invalid_status")
        now = self.clock.now()
        with transaction.atomic():
            locked_entry = AttendanceEntry.objects.select_for_update().get(id=entry.id)
            if locked_entry.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked_entry.status = status
            locked_entry.version += 1
            locked_entry.updated_at = now
            locked_entry.save(update_fields=["status", "version", "updated_at"])
            locked_session = AttendanceSession.objects.select_for_update().get(id=session.id)
            locked_session.version += 1
            locked_session.updated_at = now
            locked_session.save(update_fields=["version", "updated_at"])
            amendment = AttendanceAmendment.objects.create(
                id=uuid.uuid4(),
                entry=locked_entry,
                old_status=old_status,
                new_status=status,
                reason=reason.strip(),
                actor_id=context.actor_id,
                occurred_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="attendance.entry_corrected",
                    resource_id=locked_entry.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={"status": old_status},
                    after={"status": status},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="attendance.corrected",
                    occurred_at=now,
                    aggregate_id=locked_session.id,
                    aggregate_version=locked_session.version,
                    payload={
                        "session_id": str(locked_session.id),
                        "student_id": str(locked_entry.student_id),
                        "version": locked_session.version,
                    },
                    correlation_id=context.request_id,
                )
            )
        return {
            "entry": entry_to_wire(AttendanceEntry.objects.get(id=entry_id)),
            "amendment": {
                "id": str(amendment.id),
                "entry_id": str(entry_id),
                "old_status": amendment.old_status,
                "new_status": amendment.new_status,
                "reason": amendment.reason,
                "actor_id": str(amendment.actor_id),
                "occurred_at": amendment.occurred_at.isoformat(),
            },
            "session_version": AttendanceSession.objects.get(id=session.id).version,
        }
