"""School configuration and the academic calendar M02 owns.

Every row carries a trusted ``school_id`` taken from the RequestContext, never
from a request body, and an integer ``version`` compared against
``expected_version`` on write.

Archive rather than delete: a section or subject that enrolments once referenced
must stay readable, so ``archived`` hides it from new links without removing
history. There is no destructive DELETE anywhere in this module.

Does not handle: people. That is ``models/people.py``.
"""

from __future__ import annotations

import uuid

from django.db import models

from shared.languages import LANGUAGE_CHOICES

#: The states an academic year moves through. Closing blocks new lifecycle
#: writes; reopening rules were not supplied by the school and are therefore
#: absent rather than guessed.
YEAR_STATES = (
    ("draft", "draft"),
    ("active", "active"),
    ("closed", "closed"),
    ("archived", "archived"),
)

#: Languages the school's records and UI are published in. Imported rather than
#: redeclared: a second copy would drift, and the schema generator would emit two
#: differently named enums for one set of values.
LANGUAGES = LANGUAGE_CHOICES


class SchoolConfig(models.Model):
    """The one configuration row for this deployment's school.

    Installed by the bootstrap seed, never created implicitly by a PUT: a PUT
    that could create would let a misrouted request invent a second school's
    configuration inside this one's database.

    ``board`` is a single-member enum today. It is stored rather than assumed so
    that adding a board is a data and contract change, not a code rewrite.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True, db_index=True)
    display_name = models.CharField(max_length=200)
    board = models.CharField(max_length=16, default="CBSE")
    default_language = models.CharField(max_length=2, choices=LANGUAGES, default="en")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_school_config"

    def __str__(self) -> str:
        """Return a short identifier for logs. Carries no personal data."""
        return f"SchoolConfig {self.school_id}"


class AcademicYear(models.Model):
    """One academic year, such as 2026-2027.

    ``start`` and ``end`` are inclusive, matching how a school states a session
    ("1 June to 31 March"). A year whose end precedes its start is refused at
    the service boundary rather than stored and sorted out later.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=64)
    start = models.DateField()
    end = models.DateField()
    state = models.CharField(max_length=16, choices=YEAR_STATES, default="draft")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_academic_year"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "name"], name="registry_year_unique_name_per_school"
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"AcademicYear {self.name}@{self.school_id}"


class Term(models.Model):
    """A dated division of an academic year.

    Must fall inside its year's inclusive range; a term outside it would put
    attendance and assessment dates in a year that does not contain them.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="terms")
    name = models.CharField(max_length=64)
    start = models.DateField()
    end = models.DateField()
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_term"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "year", "name"],
                name="registry_term_unique_name_per_year",
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Term {self.name}"


class Standard(models.Model):
    """A class level, 1 to 12.

    The bound is the school system's, not a preference: there is no standard 13
    to enrol a pupil into, so the write is refused rather than stored.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    number = models.IntegerField()
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_standard"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "number"],
                name="registry_standard_unique_number_per_school",
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Standard {self.number}"


class Section(models.Model):
    """One division of a standard within a year, such as 5-A.

    Scoped to a year as well as a standard because 5-A in 2026-2027 and 5-A in
    2027-2028 are different cohorts with different rosters.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="sections")
    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=32)
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_section"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "year", "standard", "name"],
                name="registry_section_unique_name_per_standard_year",
            )
        ]
        indexes = [models.Index(fields=["school_id", "year", "archived"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Section {self.name}"


class Subject(models.Model):
    """A school-authored subject. No real curriculum is seeded.

    ``code`` is the school's own short form and is unique per school. This
    module supplies no CBSE subject list: the school publishes its own reference
    data, because inventing one would put an unapproved curriculum into pupil
    records.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=32)
    display_name = models.CharField(max_length=128)
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_subject"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "code"], name="registry_subject_unique_code_per_school"
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"Subject {self.code}"
