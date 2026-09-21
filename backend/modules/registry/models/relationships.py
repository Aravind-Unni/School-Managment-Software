"""Guardian links, teaching assignments and subject offerings.

Dated links connect people and sections. Subject offerings describe which subjects
a section runs in a year; subject enrolments (in ``enrolments.py``) attach pupils
to those offerings.

Does not handle: people rows. Those live in ``people.py``.
"""

from __future__ import annotations

import uuid

from django.db import models

from .configuration import AcademicYear, Section, Subject
from .people import Guardian, StaffProfile, Student

VISIBILITY_CHOICES = (
    ("academic", "academic"),
    ("none", "none"),
)


class GuardianLink(models.Model):
    """A dated link between one guardian and one student.

    ``visibility`` is the school's vocabulary for what the guardian may see when
    the link is in force. ``none`` still records the relationship for staff; it
    does not grant guardian-scoped reads by itself.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="guardian_links"
    )
    guardian = models.ForeignKey(
        Guardian, on_delete=models.PROTECT, related_name="student_links"
    )
    visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_guardian_link"
        indexes = [
            models.Index(fields=["school_id", "student"]),
            models.Index(fields=["school_id", "guardian"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"GuardianLink {self.guardian_id}->{self.student_id}"


class TeachingAssignment(models.Model):
    """One staff member's dated assignment to teach a subject in a section.

    ``is_class_teacher`` is stored for relationship resolution. The frozen
    browser TeachingAssignment shape carries no such flag; this field is how the
    real provider distinguishes class teacher from assigned teacher without
    inventing a second table the contract did not name.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    staff = models.ForeignKey(
        StaffProfile, on_delete=models.PROTECT, related_name="assignments"
    )
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="teaching_assignments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="teaching_assignments"
    )
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    is_class_teacher = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_teaching_assignment"
        indexes = [
            models.Index(fields=["school_id", "staff"]),
            models.Index(fields=["school_id", "section"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"TeachingAssignment {self.staff_id}@{self.section_id}"


class SubjectOffering(models.Model):
    """One subject taught to one section within an academic year.

    ``optional_group`` groups electives that share a timetable slot. Null means
    the offering is compulsory for pupils in the section unless policy says
    otherwise in a later step.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="subject_offerings"
    )
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="subject_offerings"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="offerings")
    optional_group = models.CharField(max_length=64, null=True, blank=True)
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_subject_offering"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "year", "section", "subject"],
                name="registry_offering_unique_subject_per_section_year",
            )
        ]
        indexes = [models.Index(fields=["school_id", "section", "archived"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"SubjectOffering {self.subject_id}@{self.section_id}"
