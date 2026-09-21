"""Upload, source, candidate, pin, derivative and purge aggregates for M12.

Economical retention and image limits live on FilesPolicy as fixture data, not
approved school policy. Pinned canonical bytes are never purged.
"""

from __future__ import annotations

import uuid

from django.db import models


class UploadSessionState(models.TextChoices):
    """Lifecycle of a quarantine upload session."""

    OPEN = "open", "open"
    COMPLETED = "completed", "completed"
    EXPIRED = "expired", "expired"
    ABANDONED = "abandoned", "abandoned"


class FilePurpose(models.TextChoices):
    """Allowed storage purposes."""

    ANSWER_SHEET = "answer_sheet", "answer_sheet"
    IMPORT_CSV = "import_csv", "import_csv"
    IMPORT_XLSX = "import_xlsx", "import_xlsx"
    REPORT_PDF = "report_pdf", "report_pdf"
    REPORT_CSV = "report_csv", "report_csv"
    REPORT_XLSX = "report_xlsx", "report_xlsx"


class FileState(models.TextChoices):
    """Public file lifecycle states."""

    PROCESSING = "processing", "processing"
    CANDIDATE_READY = "candidate_ready", "candidate_ready"
    ACCEPTED = "accepted", "accepted"
    REJECTED = "rejected", "rejected"
    PURGING = "purging", "purging"


class PurgeJobState(models.TextChoices):
    """Source purge job states."""

    PENDING = "pending", "pending"
    BLOCKED = "blocked", "blocked"
    COMPLETED = "completed", "completed"
    FAILED = "failed", "failed"


class FilesPolicy(models.Model):
    """Per-school fixture limits. Seed data, not approved school policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    retention_mode = models.CharField(max_length=32, default="economical")
    grace_days = models.IntegerField(default=7)
    max_bytes_per_page = models.IntegerField(default=12_582_912)
    max_megapixels = models.IntegerField(default=40)
    max_batch_pages = models.IntegerField(default=40)
    long_edge_px = models.IntegerField(default=2400)
    webp_quality = models.IntegerField(default=85)
    signed_read_seconds = models.IntegerField(default=60)
    retention_requires_2fa = models.BooleanField(default=True)
    policy_version = models.CharField(max_length=64, default="economical_v1")

    class Meta:
        db_table = "files_policy"


class UploadSession(models.Model):
    """Short-lived quarantine upload handle."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    purpose = models.CharField(max_length=32, choices=FilePurpose.choices)
    client_name = models.CharField(max_length=255)
    declared_bytes = models.IntegerField()
    mime = models.CharField(max_length=128)
    state = models.CharField(
        max_length=16, choices=UploadSessionState.choices, default=UploadSessionState.OPEN
    )
    quarantine_key = models.CharField(max_length=512)
    put_token = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    max_bytes = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "files_upload_session"
        indexes = [models.Index(fields=["school_id", "state", "expires_at"])]


class SourceObject(models.Model):
    """Immutable quarantine/source bytes before economical purge."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    upload_session_id = models.UUIDField(null=True, blank=True)
    storage_key = models.CharField(max_length=512)
    sha256 = models.CharField(max_length=64)
    byte_size = models.IntegerField()
    mime = models.CharField(max_length=128)
    backup_verified = models.BooleanField(default=False)
    purged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "files_source_object"


class File(models.Model):
    """One private file aggregate visible via status and FilesPort."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    purpose = models.CharField(max_length=32, choices=FilePurpose.choices)
    state = models.CharField(
        max_length=32, choices=FileState.choices, default=FileState.PROCESSING
    )
    source_id = models.UUIDField(null=True, blank=True, db_index=True)
    subject_person_id = models.UUIDField(null=True, blank=True, db_index=True)
    canonical_version = models.IntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, null=True, blank=True)
    byte_size = models.IntegerField(null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    profile_version = models.CharField(max_length=64, null=True, blank=True)
    review_confirmed = models.BooleanField(default=False)
    rejection_reason = models.CharField(max_length=128, null=True, blank=True)
    legal_hold = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "files_file"
        indexes = [
            models.Index(fields=["school_id", "state"]),
            models.Index(fields=["school_id", "sha256"]),
        ]


class Candidate(models.Model):
    """One compression candidate version for an answer sheet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    file_id = models.UUIDField(db_index=True)
    version = models.IntegerField()
    storage_key = models.CharField(max_length=512)
    sha256 = models.CharField(max_length=64)
    byte_size = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    profile_version = models.CharField(max_length=64)
    mime = models.CharField(max_length=128, default="image/webp")
    created_at = models.DateTimeField()

    class Meta:
        db_table = "files_candidate"
        constraints = [
            models.UniqueConstraint(
                fields=["file_id", "version"],
                name="files_candidate_file_version_uniq",
            )
        ]


class QualityReview(models.Model):
    """Teacher confirmation that a candidate is readable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    file_id = models.UUIDField(db_index=True)
    candidate_version = models.IntegerField()
    actor_id = models.UUIDField()
    readability_confirmed = models.BooleanField(default=True)
    confirmed_at = models.DateTimeField()

    class Meta:
        db_table = "files_quality_review"


class EvidencePin(models.Model):
    """Immutable pin of a confirmed canonical version into a binding."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    file_id = models.UUIDField(db_index=True)
    version = models.IntegerField()
    sha256 = models.CharField(max_length=64)
    binding_id = models.UUIDField(unique=True)
    pinned_at = models.DateTimeField()

    class Meta:
        db_table = "files_evidence_pin"
        indexes = [models.Index(fields=["file_id", "version"])]


class Derivative(models.Model):
    """Stored derivative bytes (canonical, candidate, or artifact)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    file_id = models.UUIDField(db_index=True)
    kind = models.CharField(max_length=32)
    version = models.IntegerField()
    storage_key = models.CharField(max_length=512)
    sha256 = models.CharField(max_length=64)
    mime = models.CharField(max_length=128)
    byte_size = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "files_derivative"
        indexes = [models.Index(fields=["file_id", "kind", "version"])]


class PurgeJob(models.Model):
    """Economical source purge attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    source_id = models.UUIDField(db_index=True)
    file_id = models.UUIDField(db_index=True)
    state = models.CharField(
        max_length=16, choices=PurgeJobState.choices, default=PurgeJobState.PENDING
    )
    block_reason = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "files_purge_job"
