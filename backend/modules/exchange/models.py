"""Import, export, report-card and report-snapshot aggregates for M13.

Every row is school-scoped and every mutable aggregate carries an integer
``version``. Snapshots are deliberately NOT mutable: a policy change produces a
new snapshot linked by ``superseded_by``, which is what makes a report issued
last term still say what it said last term.
"""

from __future__ import annotations

import uuid

from django.db import models


class ImportDataset(models.TextChoices):
    """Frozen import dataset allowlist (review-decisions item 6)."""

    ENROLMENTS = "enrolments", "enrolments"
    OPENING_BALANCES = "opening_balances", "opening_balances"
    RESULTS = "results", "results"
    LIBRARY_LOANS = "library_loans", "library_loans"


class ExportDataset(models.TextChoices):
    """Frozen export/report dataset allowlist (review-decisions item 7)."""

    ATTENDANCE_SUMMARY = "attendance_summary", "attendance_summary"
    PROGRESS = "progress", "progress"
    AT_RISK = "at_risk", "at_risk"
    PTM_SUMMARY = "ptm_summary", "ptm_summary"
    CLASS_ROSTER = "class_roster", "class_roster"
    SUBJECT_SUMMARY = "subject_summary", "subject_summary"


class ImportJobState(models.TextChoices):
    """Lifecycle of one bulk import job."""

    VALIDATING = "validating", "validating"
    VALIDATED = "validated", "validated"
    VALIDATION_FAILED = "validation_failed", "validation_failed"
    COMMITTING = "committing", "committing"
    APPLIED = "applied", "applied"
    COMMIT_FAILED = "commit_failed", "commit_failed"


class ImportRowState(models.TextChoices):
    """Per-row outcome within an import job."""

    ACCEPTED = "accepted", "accepted"
    REJECTED = "rejected", "rejected"
    APPLIED = "applied", "applied"


class JobState(models.TextChoices):
    """Shared queued/processing/ready/failed lifecycle for async artifacts."""

    QUEUED = "queued", "queued"
    PROCESSING = "processing", "processing"
    READY = "ready", "ready"
    FAILED = "failed", "failed"


class SnapshotState(models.TextChoices):
    """Lifecycle of an immutable report snapshot."""

    PENDING = "pending", "pending"
    READY = "ready", "ready"
    SUPERSEDED = "superseded", "superseded"
    REVOKED = "revoked", "revoked"


class ExchangePolicy(models.Model):
    """Per-school fixture policy. NOT approved production policy.

    Mirrors ``policy_fixture`` in contracts/M13/fixtures/scenario.json so the
    neutralisation prefix and the signed-URL lifetime are data rather than
    constants buried in a service.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    formula_neutralization_prefix = models.CharField(max_length=2, default="\t")
    malayalam_pdf_font_bundle = models.CharField(max_length=100, default="")
    signed_read_seconds = models.IntegerField(default=120)
    commit_requires_2fa = models.BooleanField(default=False)
    commit_chunk_rows = models.IntegerField(default=2)

    class Meta:
        db_table = "exchange_policy"


class ImportJob(models.Model):
    """One uploaded file's validate-then-commit lifecycle.

    ``source_digest`` is the digest FilesPort reported for ``file_ref`` at
    validate time. Commit compares the client's claim against it; a mismatch
    means the file moved under the reviewer and the commit is refused.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    dataset = models.CharField(max_length=32, choices=ImportDataset.choices)
    file_ref = models.UUIDField()
    state = models.CharField(
        max_length=24, choices=ImportJobState.choices, default=ImportJobState.VALIDATING
    )
    source_digest = models.CharField(max_length=64, null=True, blank=True)
    validation_version = models.IntegerField(default=0)
    template_version = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=64)
    mode = models.CharField(max_length=16, default="validate")
    version = models.IntegerField(default=1)
    accepted_count = models.IntegerField(default=0)
    applied_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    commit_key = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_import_job"
        indexes = [models.Index(fields=["school_id", "state"])]


class ImportRow(models.Model):
    """One parsed source row, with its neutralised payload and row errors.

    ``payload`` holds the values AFTER formula neutralisation, so what the
    commit applies is exactly what validation inspected.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    job_id = models.UUIDField(db_index=True)
    number = models.IntegerField()
    external_key = models.CharField(max_length=300, default="")
    validation_errors = models.JSONField(default=list)
    state = models.CharField(
        max_length=16, choices=ImportRowState.choices, default=ImportRowState.ACCEPTED
    )
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "exchange_import_row"
        constraints = [
            models.UniqueConstraint(
                fields=["job_id", "number"], name="exchange_import_row_job_number_uniq"
            )
        ]
        indexes = [models.Index(fields=["job_id", "state"])]


class CommitBatch(models.Model):
    """One idempotent chunk of a commit, keyed by Idempotency-Key plus index.

    Existence of the row IS the idempotency record: a resumed commit skips any
    batch already present, which is what stops a retry double-applying rows.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    job_id = models.UUIDField(db_index=True)
    key = models.CharField(max_length=200, unique=True)
    result = models.JSONField(default=dict)
    applied_count = models.IntegerField(default=0)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_commit_batch"


class ExportJob(models.Model):
    """One dataset export rendered to an artifact in the background.

    ``field_grants`` records the fields that actually survived the allowlist, so
    a reviewer can see what was withheld without re-deriving the policy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    dataset = models.CharField(max_length=32, choices=ExportDataset.choices)
    filters = models.JSONField(default=dict)
    requested_fields = models.JSONField(default=list)
    field_grants = models.JSONField(default=list)
    format = models.CharField(max_length=8)
    locale = models.CharField(max_length=8)
    state = models.CharField(max_length=16, choices=JobState.choices, default=JobState.QUEUED)
    expires_at = models.DateTimeField(null=True, blank=True)
    artifact_file_id = models.UUIDField(null=True, blank=True)
    artifact_sha256 = models.CharField(max_length=64, null=True, blank=True)
    failure_message_key = models.CharField(max_length=100, null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_export_job"
        indexes = [models.Index(fields=["school_id", "state"])]


class ReportSnapshot(models.Model):
    """An immutable rendered report bound to the revisions it was built from.

    Only ``state`` and ``superseded_by`` ever change after creation, and only to
    retire the row. ``source_revision_ids`` and ``policy_versions`` are frozen
    at render time; re-rendering under a newer policy creates a new row.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    type = models.CharField(max_length=32)
    source_revision_ids = models.JSONField(default=list)
    policy_versions = models.JSONField(default=list)
    locale = models.CharField(max_length=8)
    artifact_ref = models.JSONField(default=dict)
    state = models.CharField(
        max_length=16, choices=SnapshotState.choices, default=SnapshotState.PENDING
    )
    superseded_by = models.UUIDField(null=True, blank=True)
    publication_id = models.UUIDField(null=True, blank=True)
    student_id = models.UUIDField(null=True, blank=True)
    template_version = models.CharField(max_length=64, default="")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_report_snapshot"
        indexes = [models.Index(fields=["school_id", "state"])]


class Supersession(models.Model):
    """The audit link between a retired snapshot and its replacement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    old_report_id = models.UUIDField(db_index=True)
    new_report_id = models.UUIDField()
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_supersession"


class ReportCardJob(models.Model):
    """One student's report-card generation job.

    A bulk request fans out to one row per student so a single failure does not
    hide the students whose cards rendered.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    publication_id = models.UUIDField()
    student_id = models.UUIDField()
    locale = models.CharField(max_length=8)
    template_version = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=JobState.choices, default=JobState.QUEUED)
    report_id = models.UUIDField(null=True, blank=True)
    failure_message_key = models.CharField(max_length=100, null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "exchange_report_card_job"
        indexes = [models.Index(fields=["school_id", "state"])]
