"""Harness tables backing the Platform test adapter.

Mirror the shape of contracts.events.AuditRecord and EventEnvelope so that the
same behavioural contract suite can run against these tables and, later,
against M14's real ones.

Does not handle: retention, partitioning or relay to the broker. Production
concerns owned by M14.
"""

from __future__ import annotations

from django.db import models


class HarnessAuditRecord(models.Model):
    """One audit row written inside the caller's transaction."""

    audit_id = models.UUIDField(primary_key=True)
    school_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField()
    action = models.CharField(max_length=128)
    resource_id = models.UUIDField(db_index=True)
    occurred_at = models.DateTimeField()
    request_id = models.CharField(max_length=64, db_index=True)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        db_table = "harness_audit_record"
        indexes = [models.Index(fields=["school_id", "action"])]

    def __str__(self) -> str:
        """Return a short identification string for test output."""
        return f"audit {self.action} on {self.resource_id}"


class HarnessOutboxEvent(models.Model):
    """One outbox row appended inside the caller's transaction."""

    event_id = models.UUIDField(primary_key=True)
    school_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=128, db_index=True)
    occurred_at = models.DateTimeField()
    aggregate_id = models.UUIDField(db_index=True)
    aggregate_version = models.IntegerField()
    payload = models.JSONField(default=dict)
    envelope_version = models.IntegerField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "harness_outbox_event"
        indexes = [models.Index(fields=["school_id", "event_type"])]

    def __str__(self) -> str:
        """Return a short identification string for test output."""
        return f"event {self.event_type} v{self.aggregate_version}"
