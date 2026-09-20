"""Catalogue, copy, loan, renewal and adjustment aggregates.

One open loan per copy is enforced by a partial unique constraint. Accession
numbers are unique per school. No money fields — fines are out of scope.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class CopyState(models.TextChoices):
    """Physical copy lifecycle states."""

    AVAILABLE = "available", "available"
    ON_LOAN = "on_loan", "on_loan"
    LOST = "lost", "lost"
    DAMAGED = "damaged", "damaged"
    WITHDRAWN = "withdrawn", "withdrawn"


class BorrowerType(models.TextChoices):
    """Who may borrow a copy."""

    STUDENT = "student", "student"
    STAFF = "staff", "staff"


class ReturnCondition(models.TextChoices):
    """Condition recorded at return."""

    OK = "ok", "ok"
    DAMAGED = "damaged", "damaged"
    LOST = "lost", "lost"


class LibraryPolicy(models.Model):
    """Per-school fixture limits. Seed data, not approved school policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    max_active_loans_per_borrower = models.IntegerField(default=3)
    max_renewals_per_loan = models.IntegerField(default=2)

    class Meta:
        db_table = "library_policy"


class Title(models.Model):
    """Catalogue title. ISBN optional and not unique."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    isbn = models.CharField(max_length=32, null=True, blank=True)
    name = models.CharField(max_length=512)
    author = models.CharField(max_length=512)
    language = models.CharField(max_length=32)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "library_title"
        indexes = [
            models.Index(fields=["school_id", "name"]),
            models.Index(fields=["school_id", "author"]),
            models.Index(fields=["school_id", "isbn"]),
        ]


class Copy(models.Model):
    """One physical copy of a title."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    title_id = models.UUIDField(db_index=True)
    accession_no = models.CharField(max_length=64)
    state = models.CharField(
        max_length=16, choices=CopyState.choices, default=CopyState.AVAILABLE
    )
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "library_copy"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "accession_no"],
                name="library_copy_school_accession_uniq",
            )
        ]
        indexes = [models.Index(fields=["school_id", "title_id", "state"])]


class Loan(models.Model):
    """Issue of one copy to one borrower. Open while returned_at is null."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    copy_id = models.UUIDField(db_index=True)
    borrower_person_id = models.UUIDField(db_index=True)
    borrower_type = models.CharField(max_length=16, choices=BorrowerType.choices)
    issued_at = models.DateTimeField()
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)
    overdue_event_emitted_as_of = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "library_loan"
        constraints = [
            models.UniqueConstraint(
                fields=["copy_id"],
                condition=Q(returned_at__isnull=True),
                name="library_loan_one_open_per_copy",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "borrower_person_id"]),
            models.Index(fields=["school_id", "due_date", "returned_at"]),
        ]


class Renewal(models.Model):
    """Append-only record of a due-date change."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    loan_id = models.UUIDField(db_index=True)
    old_due = models.DateField()
    new_due = models.DateField()
    actor_id = models.UUIDField()
    reason = models.TextField(null=True, blank=True)
    renewed_at = models.DateTimeField()

    class Meta:
        db_table = "library_renewal"


class CopyAdjustment(models.Model):
    """Lost/damaged/withdrawn state change with reason and actor."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    copy_id = models.UUIDField(db_index=True)
    reason = models.TextField()
    old_state = models.CharField(max_length=16, choices=CopyState.choices)
    new_state = models.CharField(max_length=16, choices=CopyState.choices)
    actor_id = models.UUIDField()
    adjusted_at = models.DateTimeField()

    class Meta:
        db_table = "library_copy_adjustment"


class LoanIdempotency(models.Model):
    """Stores Idempotency-Key outcomes for loan issue."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    idempotency_key = models.CharField(max_length=128)
    payload_fingerprint = models.CharField(max_length=64)
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="idempotency_rows")

    class Meta:
        db_table = "library_loan_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "idempotency_key"],
                name="library_loan_idempotency_school_key_uniq",
            )
        ]
