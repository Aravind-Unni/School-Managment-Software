"""Attendance aggregates: Session, Entry, Amendment.

Unique (school_id, timetable_session_id) and (session, enrolment_id). Mutable
aggregates carry integer version. Roster snapshot is taken at draft create.
"""

from __future__ import annotations

import uuid

from django.db import models


class SessionState(models.TextChoices):
    """Lifecycle of an attendance session for one dated period."""

    DRAFT = "draft", "draft"
    SUBMITTED = "submitted", "submitted"


class AttendanceStatus(models.TextChoices):
    """Per-pupil mark. Unmarked means no mark yet; never treated as present."""

    UNMARKED = "unmarked", "unmarked"
    PRESENT = "present", "present"
    ABSENT = "absent", "absent"
    LATE = "late", "late"
    EXCUSED = "excused", "excused"


class AttendanceSession(models.Model):
    """One dated timetable period's attendance register."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    timetable_session_id = models.UUIDField()
    date = models.DateField()
    section_id = models.UUIDField()
    slot_id = models.UUIDField()
    subject_id = models.UUIDField()
    timetable_version = models.IntegerField()
    roster_version = models.IntegerField()
    roster_snapshot = models.JSONField()
    state = models.CharField(
        max_length=16, choices=SessionState.choices, default=SessionState.DRAFT
    )
    version = models.IntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    #: Last audited reconciliation reason, if any; history rows are never deleted.
    reconciliation_reason = models.TextField(blank=True, default="")
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attendance_session"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "timetable_session_id"],
                name="attendance_session_school_timetable_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "date"]),
            models.Index(fields=["school_id", "section_id", "date"]),
        ]


class AttendanceEntry(models.Model):
    """One pupil's mark inside a session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="entries"
    )
    enrolment_id = models.UUIDField()
    student_id = models.UUIDField()
    status = models.CharField(
        max_length=16, choices=AttendanceStatus.choices, default=AttendanceStatus.UNMARKED
    )
    note = models.CharField(max_length=500, blank=True, default="")
    version = models.IntegerField(default=1)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "attendance_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrolment_id"],
                name="attendance_entry_session_enrolment_uniq",
            )
        ]


class AttendanceAmendment(models.Model):
    """Audited correction of a submitted entry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        AttendanceEntry, on_delete=models.CASCADE, related_name="amendments"
    )
    old_status = models.CharField(max_length=16, choices=AttendanceStatus.choices)
    new_status = models.CharField(max_length=16, choices=AttendanceStatus.choices)
    reason = models.CharField(max_length=500)
    actor_id = models.UUIDField()
    occurred_at = models.DateTimeField()

    class Meta:
        db_table = "attendance_amendment"
        ordering = ["occurred_at", "id"]


class SubmitIdempotency(models.Model):
    """Records Idempotency-Key outcomes so retries do not duplicate events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField()
    session_id = models.UUIDField()
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "attendance_submit_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "session_id", "idempotency_key"],
                name="attendance_submit_idem_uniq",
            )
        ]
