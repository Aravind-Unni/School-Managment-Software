"""Audit, outbox, job, backup and restore aggregates for M14.

Mutable aggregates carry integer ``version``. Audit and consumer receipts are
append-only. Outbox rows join the caller's transaction; dispatch is separate.
"""

from __future__ import annotations

import uuid

from django.db import models


class JobState(models.TextChoices):
    """Lifecycle of one background job."""

    QUEUED = "queued", "queued"
    RUNNING = "running", "running"
    SUCCEEDED = "succeeded", "succeeded"
    FAILED = "failed", "failed"
    DEAD = "dead", "dead"


class OutboxState(models.TextChoices):
    """Lifecycle of one outbox event."""

    PENDING = "pending", "pending"
    DISPATCHING = "dispatching", "dispatching"
    DISPATCHED = "dispatched", "dispatched"
    FAILED = "failed", "failed"


class RestoreRehearsalState(models.TextChoices):
    """Lifecycle of one isolated restore rehearsal."""

    QUEUED = "queued", "queued"
    RUNNING = "running", "running"
    VERIFIED = "verified", "verified"
    FAILED = "failed", "failed"


class PlatformPolicy(models.Model):
    """Per-school fixture policy. NOT approved production policy."""

    school_id = models.UUIDField(primary_key=True)
    backup_age_alert_minutes = models.PositiveIntegerField(default=20)
    rpo_minutes_hypothesis = models.PositiveIntegerField(default=15)
    rto_hours_hypothesis = models.PositiveIntegerField(default=4)

    class Meta:
        db_table = "platform_policy"


class AuditRecord(models.Model):
    """Append-only audit row written inside the caller's transaction."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    action = models.CharField(max_length=128)
    resource_id = models.UUIDField(db_index=True)
    occurred_at = models.DateTimeField()
    request_id = models.CharField(max_length=64, db_index=True)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        db_table = "platform_audit_record"
        indexes = [models.Index(fields=["school_id", "action", "occurred_at"])]


class OutboxEvent(models.Model):
    """Outbox row appended inside the caller's transaction."""

    event_id = models.UUIDField(primary_key=True)
    school_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=128, db_index=True)
    occurred_at = models.DateTimeField()
    aggregate_id = models.UUIDField(db_index=True)
    aggregate_version = models.IntegerField()
    payload = models.JSONField(default=dict)
    envelope_version = models.IntegerField(default=1)
    correlation_id = models.CharField(max_length=64, null=True, blank=True)
    state = models.CharField(
        max_length=16, choices=OutboxState.choices, default=OutboxState.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_outbox_event"
        indexes = [models.Index(fields=["state", "occurred_at"])]


class ConsumerReceipt(models.Model):
    """Dedupe key for at-least-once delivery: (consumer, event_id)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consumer = models.CharField(max_length=128)
    event_id = models.UUIDField()
    school_id = models.UUIDField(db_index=True)
    received_at = models.DateTimeField()
    side_effect_token = models.CharField(max_length=128, default="")

    class Meta:
        db_table = "platform_consumer_receipt"
        constraints = [
            models.UniqueConstraint(
                fields=["consumer", "event_id"],
                name="platform_consumer_receipt_uniq",
            )
        ]


class Job(models.Model):
    """Background job with sanitized progress and error."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    kind = models.CharField(max_length=128)
    payload_ref = models.CharField(max_length=512)
    #: Dotted path of the handler the worker runs, and the arguments it gets.
    #: Empty for bookkeeping kinds that have no worker handler.
    task_path = models.CharField(max_length=256, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=16, choices=JobState.choices, default=JobState.QUEUED)
    progress = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=128, null=True, blank=True)
    idempotency_key = models.CharField(max_length=128)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "platform_job"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "kind", "idempotency_key"],
                name="platform_job_idempotency_uniq",
            )
        ]
        indexes = [models.Index(fields=["school_id", "state"])]


class BackupManifest(models.Model):
    """Named DB point plus pinned object versions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    db_point = models.CharField(max_length=256)
    object_versions = models.JSONField(default=list)
    fee_total_paise = models.PositiveIntegerField(null=True, blank=True)
    record_counts = models.JSONField(default=dict)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "platform_backup_manifest"


class RestoreRehearsal(models.Model):
    """Isolated restore rehearsal; never targets production."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    backup_manifest_id = models.UUIDField()
    isolated_target_label = models.CharField(max_length=128)
    state = models.CharField(
        max_length=16,
        choices=RestoreRehearsalState.choices,
        default=RestoreRehearsalState.QUEUED,
    )
    record_counts = models.JSONField(default=dict)
    object_hashes_matched = models.BooleanField(default=False)
    fee_total_paise = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_restore_rehearsal"
