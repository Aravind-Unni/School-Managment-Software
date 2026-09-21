"""Create and save draft attendance sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import AttendanceEntry, AttendanceSession, AttendanceStatus, SessionState
from .authority import AuthorityGate
from .wire import session_to_wire

WRITABLE = frozenset(
    {
        AttendanceStatus.PRESENT,
        AttendanceStatus.ABSENT,
        AttendanceStatus.LATE,
        AttendanceStatus.EXCUSED,
    }
)


@dataclass(frozen=True, slots=True)
class DraftService:
    """Open and save draft registers for dated timetable periods."""

    gate: AuthorityGate
    registry: object
    platform: object
    clock: object
    timetable: object

    def list_periods(self, context: RequestContext, on: date) -> dict[str, object]:
        """Return the actor's authorised periods for a school date."""
        self.gate.require_school_read(context)
        sessions = self.timetable.get_sessions_for_staff(context, context.actor_id, on)
        subject_names = {str(k): v for k, v in self.registry.subject_names(context).items()}
        labels: dict[str, str | None] = {}
        items: list[dict[str, object]] = []
        for period in sessions:
            if period.cancelled:
                continue
            existing = AttendanceSession.objects.filter(
                school_id=context.school_id,
                timetable_session_id=period.timetable_session_id,
            ).first()
            if existing is None:
                submission_state = "unopened"
                missing = len(
                    self.registry.get_roster(
                        context, period.section_id, on, subject_id=period.subject_id
                    ).students
                )
                session_id = None
            else:
                submission_state = existing.state
                missing = existing.entries.filter(status=AttendanceStatus.UNMARKED).count()
                session_id = str(existing.id)
            section_key = str(period.section_id)
            if section_key not in labels:
                labels[section_key] = self.registry.section_label(context, period.section_id)
            items.append(
                {
                    "timetable_session_id": str(period.timetable_session_id),
                    "section_label": labels[section_key],
                    "subject_name": subject_names.get(str(period.subject_id)),
                    "starts_at_local": period.starts_at_local.strftime("%H:%M"),
                    "ends_at_local": period.ends_at_local.strftime("%H:%M"),
                    "date": period.date.isoformat(),
                    "section_id": str(period.section_id),
                    "slot_id": str(period.slot_id),
                    "slot_code": period.slot_code,
                    "subject_id": str(period.subject_id),
                    "assigned_teacher_id": str(period.assigned_teacher_id),
                    "substitute_teacher_id": (
                        str(period.substitute_teacher_id)
                        if period.substitute_teacher_id
                        else None
                    ),
                    "starts_at": period.starts_at.isoformat(),
                    "ends_at": period.ends_at.isoformat(),
                    "cancelled": period.cancelled,
                    "timetable_version": period.timetable_version,
                    "session_id": session_id,
                    "submission_state": submission_state,
                    "missing_count": missing,
                }
            )
        return {"items": items, "next_cursor": None}

    def create_or_get(
        self, context: RequestContext, *, timetable_session_id: UUID
    ) -> dict[str, object]:
        """Create a draft session with roster snapshot, or return the existing one."""
        authority = self.gate.require_period_action(
            context, action="attendance.mark", timetable_session_id=timetable_session_id
        )
        existing = AttendanceSession.objects.filter(
            school_id=context.school_id, timetable_session_id=timetable_session_id
        ).first()
        if existing is not None:
            return session_to_wire(existing)

        period = self.timetable.get_session(context, timetable_session_id)
        roster = self.registry.get_roster(
            context, authority.section_id, authority.date, subject_id=authority.subject_id
        )
        now = self.clock.now()
        snapshot = [
            {
                "student_id": str(row.student_id),
                "enrolment_id": str(row.enrolment_id),
                "display_name": row.display_name,
            }
            for row in roster.students
        ]
        with transaction.atomic():
            session = AttendanceSession.objects.create(
                id=uuid.uuid4(),
                school_id=context.school_id,
                timetable_session_id=timetable_session_id,
                date=authority.date,
                section_id=authority.section_id,
                slot_id=period.slot_id,
                subject_id=authority.subject_id,
                timetable_version=period.timetable_version,
                roster_version=roster.version,
                roster_snapshot=snapshot,
                state=SessionState.DRAFT,
                version=1,
                created_at=now,
                updated_at=now,
            )
            for row in roster.students:
                AttendanceEntry.objects.create(
                    id=uuid.uuid4(),
                    session=session,
                    enrolment_id=row.enrolment_id,
                    student_id=row.student_id,
                    status=AttendanceStatus.UNMARKED,
                    updated_at=now,
                )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="attendance.session_created",
                    resource_id=session.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"timetable_session_id": str(timetable_session_id)},
                )
            )
        return session_to_wire(session)

    def save_entries(
        self,
        context: RequestContext,
        *,
        session_id: UUID,
        expected_version: int,
        entries: list[dict[str, object]],
    ) -> dict[str, object]:
        """Save writable statuses onto a draft session."""
        session = self._load_session(context, session_id)
        if session.state != SessionState.DRAFT:
            raise StateConflict("attendance.error.not_draft")
        self.gate.require_period_action(
            context,
            action="attendance.mark",
            timetable_session_id=session.timetable_session_id,
        )
        self._assert_versions_current(context, session)
        if session.version != expected_version:
            raise VersionConflict("error.version_conflict")

        roster_enrolments = {UUID(row["enrolment_id"]) for row in session.roster_snapshot}
        now = self.clock.now()
        with transaction.atomic():
            locked = AttendanceSession.objects.select_for_update().get(id=session.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            for item in entries:
                enrolment_id = item["enrolment_id"]
                status = item["status"]
                if enrolment_id not in roster_enrolments:
                    raise ValidationFailed("attendance.error.enrolment_not_on_roster")
                if status not in WRITABLE:
                    raise ValidationFailed("attendance.error.invalid_status")
                entry = locked.entries.get(enrolment_id=enrolment_id)
                entry.status = status
                note = item.get("note")
                entry.note = note or ""
                entry.version += 1
                entry.updated_at = now
                entry.save(update_fields=["status", "note", "version", "updated_at"])
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["version", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="attendance.session_saved",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": locked.version},
                )
            )
        return session_to_wire(AttendanceSession.objects.get(id=session_id))

    def _load_session(self, context: RequestContext, session_id: UUID) -> AttendanceSession:
        """Load a school-scoped session or raise 404."""
        try:
            session = AttendanceSession.objects.prefetch_related("entries").get(id=session_id)
        except AttendanceSession.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if session.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return session

    def _assert_versions_current(
        self, context: RequestContext, session: AttendanceSession
    ) -> None:
        """Reject save/submit when timetable or roster facts drifted."""
        period = self.timetable.get_session(context, session.timetable_session_id)
        if period.cancelled:
            raise StateConflict("attendance.error.period_not_eligible")
        if period.timetable_version != session.timetable_version:
            raise StateConflict("attendance.error.roster_stale")
        roster = self.registry.get_roster(
            context, session.section_id, session.date, subject_id=session.subject_id
        )
        if roster.version != session.roster_version:
            raise StateConflict("attendance.error.roster_stale")
