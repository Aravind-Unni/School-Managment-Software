"""Timetable revisions and the weekly grid they own.

Every row carries a trusted ``school_id`` taken from the RequestContext, never
from a request body, and the version aggregate carries an integer ``version``
compared against ``expected_version`` on write.

A published version is immutable and is never deleted. When a later revision
takes effect, the earlier one's ``effective_to`` is closed and its state becomes
``superseded`` -- it stays readable forever, because a register taken last term
was taken against it and reconciliation needs it.

Does not handle: the calendar or day overrides. Those are ``models/calendar.py``.
"""

from __future__ import annotations

import uuid

from django.db import models

#: The states a revision moves through. ``superseded`` is not "deleted": it
#: remains authoritative for the dates inside its own closed range.
TIMETABLE_STATES = (
    ("draft", "draft"),
    ("published", "published"),
    ("superseded", "superseded"),
)


class TimetableVersion(models.Model):
    """One dated revision of the central timetable.

    ``year_id`` is stored opaquely: the frozen RegistryPort exposes no academic
    year, so this module cannot check a version's range against the year it
    names. Recorded as gap 4 in contracts/M03/ports.md rather than guessed at.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    year_id = models.UUIDField(db_index=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=16, choices=TIMETABLE_STATES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_version"
        indexes = [
            models.Index(fields=["school_id", "state", "effective_from"]),
            models.Index(fields=["school_id", "year_id"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs. Carries no personal data."""
        return f"Timetable {self.state} from {self.effective_from}"

    @property
    def is_effective_source(self) -> bool:
        """Return whether this revision may be served to a schedule reader.

        A draft never is. A superseded revision still is, for the dates inside
        its own closed range.
        """
        return self.state in ("published", "superseded")


class PeriodTemplate(models.Model):
    """One bell-time slot on one weekday, owned by a revision.

    Scoped to the revision rather than to the school, deliberately (review item
    12): a school that moves the bell does so in a new revision, and the old one
    must keep the times a past register was taken under.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    timetable = models.ForeignKey(
        TimetableVersion, on_delete=models.CASCADE, related_name="periods"
    )
    #: ISO-8601 weekday: 1 Monday .. 7 Sunday. Which weekdays exist here is the
    #: school's own data, and is what makes a date a teaching day. This module
    #: never assumes a week.
    day_of_week = models.IntegerField()
    slot_code = models.CharField(max_length=16)
    starts_at_local = models.TimeField()
    ends_at_local = models.TimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_period_template"
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "day_of_week", "slot_code"],
                name="timetable_period_unique_per_day",
            )
        ]
        indexes = [models.Index(fields=["timetable", "day_of_week"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Period {self.slot_code} day {self.day_of_week}"


class Slot(models.Model):
    """One recurring teaching assignment: a section, a subject and a teacher.

    ``subject_id`` and ``teacher_id`` are Registry's ids, stored opaquely. The
    frozen RegistryPort has no subject or staff lookup, so neither is validated;
    gaps 2 and 3 in contracts/M03/ports.md.

    ``room_code`` is free text with no Room aggregate behind it and no clash
    detection (review item 5).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    timetable = models.ForeignKey(
        TimetableVersion, on_delete=models.CASCADE, related_name="slots"
    )
    period = models.ForeignKey(PeriodTemplate, on_delete=models.CASCADE, related_name="slots")
    section_id = models.UUIDField(db_index=True)
    subject_id = models.UUIDField()
    teacher_id = models.UUIDField(db_index=True)
    room_code = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "timetable_slot"
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "section_id", "period"],
                name="timetable_slot_unique_section_period",
            )
        ]
        indexes = [
            models.Index(fields=["timetable", "section_id"]),
            models.Index(fields=["timetable", "teacher_id"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Slot {self.section_id} {self.period_id}"
