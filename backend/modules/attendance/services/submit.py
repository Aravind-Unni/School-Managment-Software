"""Submit draft attendance sessions with idempotency."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import (
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import (
    AttendanceSession,
    AttendanceStatus,
    SessionState,
    SubmitIdempotency,
)
from .authority import AuthorityGate
from .drafts import DraftService
from .wire import session_to_wire


@dataclass(frozen=True, slots=True)
class SubmitService:
    """Submit a fully marked draft register."""

    drafts: DraftService
    gate: AuthorityGate
    platform: object
    clock: object

    def submit(
        self,
        context: RequestContext,
        *,
        session_id: UUID,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, object]:
        """Submit a draft. Same key retries return the session without a second event."""
        if not idempotency_key:
            raise ValidationFailed("attendance.error.idempotency_key_required")

        existing_key = SubmitIdempotency.objects.filter(
            school_id=context.school_id,
            session_id=session_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing_key is not None:
            session = self.drafts._load_session(context, session_id)
            return session_to_wire(session)

        session = self.drafts._load_session(context, session_id)
        if session.state == SessionState.SUBMITTED:
            raise StateConflict("attendance.error.already_submitted")
        if session.state != SessionState.DRAFT:
            raise StateConflict("attendance.error.not_draft")

        from contracts.errors import ActionDenied

        try:
            self.gate.require_period_action(
                context,
                action="attendance.submit",
                timetable_session_id=session.timetable_session_id,
            )
        except ActionDenied as exc:
            # Assignment may have lapsed between draft and submit.
            raise StateConflict("attendance.error.assignment_stale") from exc

        self.drafts._assert_versions_current(context, session)
        if session.version != expected_version:
            raise VersionConflict("error.version_conflict")

        unmarked = session.entries.filter(status=AttendanceStatus.UNMARKED).exists()
        if unmarked:
            raise ValidationFailed("attendance.error.incomplete_roster")

        now = self.clock.now()
        with transaction.atomic():
            locked = AttendanceSession.objects.select_for_update().get(id=session.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            if locked.state == SessionState.SUBMITTED:
                raise StateConflict("attendance.error.already_submitted")
            locked.state = SessionState.SUBMITTED
            locked.version += 1
            locked.submitted_at = now
            locked.updated_at = now
            locked.save(update_fields=["state", "version", "submitted_at", "updated_at"])
            try:
                SubmitIdempotency.objects.create(
                    id=uuid.uuid4(),
                    school_id=context.school_id,
                    session_id=locked.id,
                    idempotency_key=idempotency_key,
                    created_at=now,
                )
            except IntegrityError:
                # Concurrent duplicate key: other writer won; return their result.
                pass
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="attendance.session_submitted",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": locked.version},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="attendance.submitted",
                    occurred_at=now,
                    aggregate_id=locked.id,
                    aggregate_version=locked.version,
                    payload={
                        "session_id": str(locked.id),
                        "date": locked.date.isoformat(),
                        "section_id": str(locked.section_id),
                        "version": locked.version,
                    },
                    correlation_id=context.request_id,
                )
            )
        return session_to_wire(AttendanceSession.objects.get(id=session_id))
