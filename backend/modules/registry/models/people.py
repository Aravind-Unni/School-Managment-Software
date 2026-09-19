"""Students, guardians and staff, and the duplicate-review record.

Personal data lives here and never leaves the owning deployment. Cross-module
events carry identifiers, dates and outcome codes only -- never a birth date, a
contact detail or a free-text reason.

Does not handle: enrolment, guardian links or teaching assignments. Those are
steps 2 and 3 and have their own models.
"""

from __future__ import annotations

import uuid

from django.db import models

from .configuration import LANGUAGES

#: Enrolment state as Registry reports it to other modules. Mirrors the frozen
#: contracts.people.StudentStatus exactly; "withdrawn" is deliberately absent,
#: because the school's withdrawal outcomes map onto these four and adding an
#: enum member would break every existing consumer.
STUDENT_STATUSES = (
    ("active", "active"),
    ("inactive", "inactive"),
    ("transferred", "transferred"),
    ("graduated", "graduated"),
)

#: Why a duplicate candidate was raised. An exact admission collision is a hard
#: refusal; a name-and-birth-date match is a candidate a human must judge.
DUPLICATE_REASONS = (
    ("admission_no", "admission_no"),
    ("name_and_birth_date", "name_and_birth_date"),
)


class Student(models.Model):
    """One pupil.

    ``admission_no`` is unique PER SCHOOL and compared case-sensitively after an
    outer-whitespace trim. That is the reviewed rule: no case folding and no
    fuzzy threshold, because "2026/ab01" and "2026/AB01" may be two real
    children and this module must not decide otherwise.

    ``date_of_birth`` is nullable. A null never matches another null during
    duplicate detection: absence of a birth date is not evidence of sameness.

    A login account is not required. Student identity here is independent of
    whether anyone can sign in as them.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    admission_no = models.CharField(max_length=64)
    display_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    preferred_language = models.CharField(max_length=2, choices=LANGUAGES, default="en")
    status = models.CharField(max_length=16, choices=STUDENT_STATUSES, default="active")
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_student"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "admission_no"],
                name="registry_student_unique_admission_per_school",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "status"]),
            # Serves duplicate detection, which looks up exact name plus a
            # non-null birth date on every admission.
            models.Index(fields=["school_id", "display_name", "date_of_birth"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs. Carries no birth date."""
        return f"Student {self.admission_no}@{self.school_id}"


class Guardian(models.Model):
    """An adult who may be linked to one or more students.

    Contact details are both nullable: a school records some guardians with
    neither an address nor a number, and forcing a placeholder would put false
    data into the record.

    Holds no access rights by itself. What a guardian may see comes from a dated
    GuardianLink, which arrives in step 2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    display_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_guardian"
        indexes = [models.Index(fields=["school_id", "archived"])]

    def __str__(self) -> str:
        """Return a short identifier for logs. Carries no contact detail."""
        return f"Guardian {self.id}@{self.school_id}"


class StaffProfile(models.Model):
    """A member of staff as a person record.

    Deliberately separate from an M01 login account: staff exist in the registry
    whether or not they can sign in, and an account id is not a person id.
    Teaching assignments reference this row and arrive in step 2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    display_name = models.CharField(max_length=200)
    archived = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "registry_staff_profile"
        indexes = [models.Index(fields=["school_id", "archived"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"StaffProfile {self.id}@{self.school_id}"


class ExternalIdentity(models.Model):
    """A stable ``(source, value)`` handle for a person from another system.

    Exists so an import can find the same person again without fuzzy matching.
    ``kind`` plus ``person_id`` is a deliberate loose reference rather than three
    nullable foreign keys, so adding an importable kind does not alter the table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    kind = models.CharField(max_length=16)
    person_id = models.UUIDField(db_index=True)
    source = models.CharField(max_length=64)
    value = models.CharField(max_length=128)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "registry_external_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "source", "kind", "value"],
                name="registry_external_identity_unique_mapping",
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"ExternalIdentity {self.source}:{self.value}"


class DuplicateReview(models.Model):
    """A short-lived token recording that a human was shown duplicate candidates.

    Binds the actor, the school, the canonical input it was issued for and the
    exact versions of the candidates shown. All four are rechecked inside the
    admission transaction, so a token cannot be reused for different input or
    honoured after a candidate changed underneath it.

    Does not handle: merging identities. Acknowledging a review asserts the
    opposite -- that these are two different people.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    #: The canonical input digest. Stored rather than the raw fields so a
    #: comparison cannot drift from how the digest was computed.
    input_digest = models.CharField(max_length=64)
    #: Candidate ids with the versions shown, as ``[{"student_id", "version",
    #: "reason"}]``. Data, so adding a reason does not alter the schema.
    candidates = models.JSONField(default=list)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "registry_duplicate_review"
        indexes = [models.Index(fields=["school_id", "actor_id"])]

    def __str__(self) -> str:
        """Return a short identifier for logs."""
        return f"DuplicateReview {self.id}"
