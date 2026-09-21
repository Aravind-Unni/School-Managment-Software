"""Section enrolments and subject enrolments.

A pupil's section membership is an ``Enrolment`` row. Which subjects they take
within that membership is recorded separately in ``SubjectEnrolment``, so a
timetable period can filter the roster without guessing from section alone.

Does not handle: promotion, withdrawal or import. Those are step 4.
"""

from __future__ import annotations

import uuid

from django.db import models

from .configuration import AcademicYear, Section
from .people import Student
from .relationships import SubjectOffering

ENROLMENT_STATES = (
    ("active", "active"),
    ("cancelled", "cancelled"),
)


class Enrolment(models.Model):
    """One pupil's dated membership of a section within a year.

    ``previous_enrolment_id`` chains transfers without rewriting history. It is
    stored as a UUID rather than a foreign key so a cancelled row remains
    readable even if the chain is long.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrolments")
    year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="enrolments")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="enrolments")
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    previous_enrolment_id = models.UUIDField(null=True, blank=True)
    state = models.CharField(max_length=16, choices=ENROLMENT_STATES, default="active")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_enrolment"
        indexes = [
            models.Index(fields=["school_id", "student"]),
            models.Index(fields=["school_id", "section"]),
            models.Index(fields=["school_id", "year", "state"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Enrolment {self.student_id}@{self.section_id}"


class SubjectEnrolment(models.Model):
    """One pupil's dated enrolment in a subject offering."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    enrolment = models.ForeignKey(
        Enrolment, on_delete=models.PROTECT, related_name="subject_enrolments"
    )
    subject_offering = models.ForeignKey(
        SubjectOffering, on_delete=models.PROTECT, related_name="subject_enrolments"
    )
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_subject_enrolment"
        indexes = [
            models.Index(fields=["school_id", "enrolment"]),
            models.Index(fields=["school_id", "subject_offering"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"SubjectEnrolment {self.enrolment_id}->{self.subject_offering_id}"
