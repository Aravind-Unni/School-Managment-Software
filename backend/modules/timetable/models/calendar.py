"""The school calendar and the day overrides that sit on top of a revision.

Nothing here is ever deleted. An exception, an unavailability window and a
substitution are all **withdrawn**, because a published schedule or a past
register may already cite them, and a row that vanishes takes its history with it.

Does not handle: the recurring grid. That is ``models/versions.py``. A day
override never mutates it, which is the property that keeps last term's schedule
intact.
"""

from __future__ import annotations

import uuid

from django.db import models

from .versions import Slot

#: What an exception says about a date. ``holiday`` removes the day's teaching
#: periods; ``exam`` and ``event`` are shown but do not. There is deliberately no
#: working-day override -- review item 9 decided that adding one would be a guess
#: about a rule the school has not published.
CALENDAR_KINDS = (
    ("holiday", "holiday"),
    ("exam", "exam"),
    ("event", "event"),
)


class CalendarException(models.Model):
    """One school-authored exception to the weekly pattern.

    Unique per school, date and kind: a second identical row is a mistake, not a
    second holiday. A withdrawn row keeps the slot free for the same date and
    kind to be recorded again, which is why the create reinstates rather than
    refusing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=16, choices=CALENDAR_KINDS)
    reason_key = models.CharField(max_length=64, null=True, blank=True)
    withdrawn = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_calendar_exception"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "date", "kind"],
                name="timetable_exception_unique_per_date_kind",
            )
        ]
        indexes = [models.Index(fields=["school_id", "date", "withdrawn"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"{self.kind} on {self.date}"


class TeacherUnavailable(models.Model):
    """A half-open UTC interval during which a staff member cannot teach.

    Stored as instants rather than dates because unavailability is rarely a whole
    number of school days -- a teacher leaves at noon -- and a date would round
    the answer in whichever direction happened to be convenient.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    staff_id = models.UUIDField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason_key = models.CharField(max_length=64, null=True, blank=True)
    withdrawn = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_teacher_unavailable"
        indexes = [models.Index(fields=["school_id", "staff_id", "starts_at"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Unavailable {self.staff_id} from {self.starts_at}"


class Substitution(models.Model):
    """An explicit dated replacement for one period.

    ``valid_until`` is what stops this becoming a standing class permission: the
    substitute holds teaching authority for this session and no longer than the
    end of its own school day (review item 7).

    ``timetable_session_id`` is stored, not just derived, so a substituted period
    can be found by its identity without walking the calendar.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    date = models.DateField(db_index=True)
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="substitutions")
    timetable_session_id = models.UUIDField(db_index=True)
    section_id = models.UUIDField(db_index=True)
    subject_id = models.UUIDField()
    original_teacher_id = models.UUIDField()
    substitute_teacher_id = models.UUIDField(db_index=True)
    reason = models.CharField(max_length=200)
    valid_until = models.DateTimeField()
    withdrawn = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_substitution"
        constraints = [
            # Partial: one live substitution per dated period, while withdrawn
            # ones stay as history for the register that may already cite them.
            models.UniqueConstraint(
                fields=["school_id", "date", "slot"],
                condition=models.Q(withdrawn=False),
                name="timetable_substitution_unique_live_per_period",
            )
        ]
        indexes = [models.Index(fields=["school_id", "date", "withdrawn"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Substitution on {self.date}"


class SessionCancellation(models.Model):
    """One dated period cancelled without touching the recurring schedule.

    Proposed addition, approved as review item 6: a whole-day holiday is a
    CalendarException, but cancelling a single period had no record and
    PeriodSessionDTO carries ``cancelled``.

    The row persists when a cancellation is reversed rather than being deleted,
    so ``cancelled`` is a field and its ``version`` keeps counting -- which is
    what makes a concurrent reverse detectable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    date = models.DateField(db_index=True)
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="cancellations")
    timetable_session_id = models.UUIDField(db_index=True)
    section_id = models.UUIDField(db_index=True)
    cancelled = models.BooleanField(default=True)
    reason_key = models.CharField(max_length=64, null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_session_cancellation"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "timetable_session_id"],
                name="timetable_cancellation_unique_per_session",
            )
        ]
        indexes = [models.Index(fields=["school_id", "date"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Cancellation on {self.date}"
