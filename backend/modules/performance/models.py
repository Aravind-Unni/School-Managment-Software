"""Performance aggregates: metrics, projections, warnings, interventions, meetings.

Mutable aggregates carry integer version. Topic weakness is never inferred from
totals — only tagged item data can populate it.
"""

from __future__ import annotations

import uuid

from django.db import models


class WarningState(models.TextChoices):
    """Lifecycle of one warning."""

    OPEN = "open", "open"
    ACKNOWLEDGED = "acknowledged", "acknowledged"
    DISMISSED = "dismissed", "dismissed"
    CLOSED = "closed", "closed"


class InterventionState(models.TextChoices):
    """Lifecycle of one intervention."""

    ACTIVE = "active", "active"
    REVIEWED = "reviewed", "reviewed"
    COMPLETED = "completed", "completed"
    CANCELLED = "cancelled", "cancelled"


class Visibility(models.TextChoices):
    """Who may see a note, meeting or intervention."""

    STAFF = "staff", "staff"
    GUARDIAN_VISIBLE = "guardian_visible", "guardian_visible"
    RESTRICTED = "restricted", "restricted"


class MetricStatus(models.TextChoices):
    """Projection metric availability."""

    OK = "ok", "ok"
    INSUFFICIENT_DATA = "insufficient_data", "insufficient_data"
    INCOMPLETE = "incomplete", "incomplete"
    INCOMPATIBLE = "incompatible", "incompatible"


class MetricDefinition(models.Model):
    """Versioned metric formula. Formula is data, not code branches."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=64)
    version = models.IntegerField(default=1)
    formula = models.CharField(max_length=64)
    denominator = models.CharField(max_length=32, default="100")

    class Meta:
        db_table = "performance_metricdefinition"
        unique_together = (("school_id", "code", "version"),)


class Projection(models.Model):
    """Materialised student metrics for one window."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    window = models.CharField(max_length=32)
    subject_id = models.UUIDField(null=True, blank=True)
    metrics_json = models.JSONField(default=dict)
    source_versions = models.JSONField(default=dict)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "performance_projection"
        indexes = [
            models.Index(fields=["school_id", "student_id", "window"]),
        ]
        unique_together = (("school_id", "student_id", "window", "subject_id"),)


class WarningRule(models.Model):
    """Versioned threshold rule. Never auto-disciplines."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=64)
    version = models.IntegerField(default=1)
    threshold = models.CharField(max_length=32)
    window = models.CharField(max_length=32)
    minimum_samples = models.IntegerField(default=1)
    exclusions = models.JSONField(default=list)

    class Meta:
        db_table = "performance_warningrule"
        unique_together = (("school_id", "code", "version"),)


class Warning(models.Model):  # noqa: A001 — domain name from M06 contract
    """One opened warning with triggering source refs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    rule = models.ForeignKey(WarningRule, on_delete=models.PROTECT, related_name="warnings")
    rule_version = models.IntegerField()
    state = models.CharField(
        max_length=16, choices=WarningState.choices, default=WarningState.OPEN
    )
    version = models.IntegerField(default=1)
    source_refs = models.JSONField(default=list)
    explanation_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=128, db_index=True)
    reason = models.TextField(null=True, blank=True)
    opened_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "performance_warning"
        indexes = [
            models.Index(fields=["school_id", "student_id", "state"]),
            models.Index(fields=["school_id", "fingerprint", "state"]),
        ]


class WarningHistory(models.Model):
    """Append-only state transition for a warning."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warning = models.ForeignKey(Warning, on_delete=models.CASCADE, related_name="history")
    from_state = models.CharField(max_length=16)
    to_state = models.CharField(max_length=16)
    reason = models.TextField()
    actor_id = models.UUIDField()
    at = models.DateTimeField()

    class Meta:
        db_table = "performance_warninghistory"
        ordering = ["at", "id"]


class Resource(models.Model):
    """School-authored revision/enrichment resource."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    topic = models.CharField(max_length=128)
    level = models.CharField(max_length=64)
    url = models.URLField(max_length=500)

    class Meta:
        db_table = "performance_resource"


class Intervention(models.Model):
    """Teacher-authored support plan."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    goal = models.TextField()
    owner_id = models.UUIDField()
    review_date = models.DateField()
    state = models.CharField(
        max_length=16, choices=InterventionState.choices, default=InterventionState.ACTIVE
    )
    visibility = models.CharField(max_length=32, choices=Visibility.choices)
    version = models.IntegerField(default=1)
    resource_ids = models.JSONField(default=list)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "performance_intervention"
        indexes = [models.Index(fields=["school_id", "student_id"])]


class Meeting(models.Model):
    """Parent-teacher meeting record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    date = models.DateField()
    participants = models.JSONField(default=list)
    notes = models.TextField()
    actions = models.JSONField(default=list)
    visibility = models.CharField(max_length=32, choices=Visibility.choices)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "performance_meeting"


class Observation(models.Model):
    """Behavior/participation note; restricted ones omit from guardian export."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    kind = models.CharField(max_length=64)
    body = models.TextField()
    visibility = models.CharField(max_length=32, choices=Visibility.choices)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "performance_observation"
