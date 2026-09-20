"""Assessment aggregates: Assessment, Component, Result, Mark, Evidence, Revision.

Mutable aggregates carry integer version. Snapshot JSON on ResultRevision preserves
published manifests after reopen. Grade letter is never computed here.
"""

from __future__ import annotations

import uuid

from django.db import models


class AssessmentType(models.TextChoices):
    """Kinds of assessment structure."""

    ASSIGNMENT = "assignment", "assignment"
    WRITTEN_TEST = "written_test", "written_test"
    PRACTICAL = "practical", "practical"
    PROJECT = "project", "project"


class AssessmentState(models.TextChoices):
    """Lifecycle of one assessment batch."""

    DRAFT = "draft", "draft"
    SUBMITTED = "submitted", "submitted"
    APPROVED = "approved", "approved"
    PUBLISHED = "published", "published"
    REOPENED = "reopened", "reopened"


class ResultWorkflowStatus(models.TextChoices):
    """Per-result workflow mirror of the assessment batch."""

    DRAFT = "draft", "draft"
    SUBMITTED = "submitted", "submitted"
    APPROVED = "approved", "approved"
    PUBLISHED = "published", "published"
    REOPENED = "reopened", "reopened"


class MarkingOutcome(models.TextChoices):
    """How a pupil's attempt is recorded. Absent/exempt are never score zero."""

    SCORED = "scored", "scored"
    ABSENT = "absent", "absent"
    EXEMPT = "exempt", "exempt"
    ORAL = "oral", "oral"
    PRACTICAL = "practical", "practical"


class Assessment(models.Model):
    """One assessment structure for a section+subject in a term."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    year_id = models.UUIDField()
    term_id = models.UUIDField()
    section_id = models.UUIDField()
    subject_id = models.UUIDField()
    type = models.CharField(max_length=32, choices=AssessmentType.choices)
    max_score = models.DecimalField(max_digits=8, decimal_places=2)
    policy_version = models.CharField(max_length=64)
    state = models.CharField(
        max_length=16, choices=AssessmentState.choices, default=AssessmentState.DRAFT
    )
    version = models.IntegerField(default=1)
    due_at = models.DateTimeField(null=True, blank=True)
    marks_author_id = models.UUIDField(null=True, blank=True)
    require_distinct_approver = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_assessment"
        indexes = [
            models.Index(fields=["school_id", "term_id"]),
            models.Index(fields=["school_id", "section_id", "subject_id"]),
        ]


class Component(models.Model):
    """One weighted component inside an assessment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="components"
    )
    max_score = models.DecimalField(max_digits=8, decimal_places=2)
    weight = models.DecimalField(max_digits=6, decimal_places=3)
    topic = models.CharField(max_length=200, null=True, blank=True)
    question_type = models.CharField(max_length=80, null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "assessment_component"
        ordering = ["sort_order", "id"]


class Result(models.Model):
    """One pupil's result for one assessment attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="results")
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField()
    attempt_id = models.UUIDField()
    status = models.CharField(
        max_length=16,
        choices=ResultWorkflowStatus.choices,
        default=ResultWorkflowStatus.DRAFT,
    )
    marking_outcome = models.CharField(
        max_length=16,
        choices=MarkingOutcome.choices,
        default=MarkingOutcome.SCORED,
    )
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    version = models.IntegerField(default=1)
    current_revision_id = models.UUIDField(null=True, blank=True)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_result"
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "student_id", "attempt_id"],
                name="assessment_result_attempt_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "student_id"]),
        ]


class Mark(models.Model):
    """One component score inside a result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name="marks")
    component_id = models.UUIDField()
    score = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = "assessment_mark"
        constraints = [
            models.UniqueConstraint(
                fields=["result", "component_id"],
                name="assessment_mark_component_uniq",
            )
        ]


class EvidenceBinding(models.Model):
    """Ordered answer-sheet page bound to a result (and optionally a revision)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(
        Result, on_delete=models.CASCADE, related_name="evidence_bindings"
    )
    revision_id = models.UUIDField(null=True, blank=True, db_index=True)
    file_id = models.UUIDField()
    file_version = models.IntegerField()
    sha256 = models.CharField(max_length=64)
    page_no = models.IntegerField()

    class Meta:
        db_table = "assessment_evidence_binding"
        ordering = ["page_no", "id"]


class ResultRevision(models.Model):
    """Immutable snapshot of marks + evidence + policy at publish/reopen time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name="revisions")
    school_id = models.UUIDField()
    snapshot = models.JSONField()
    reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_result_revision"
        ordering = ["created_at", "id"]


class Publication(models.Model):
    """One published batch for an assessment; retained after reopen."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="publications"
    )
    school_id = models.UUIDField()
    result_revision_ids = models.JSONField()
    actor_id = models.UUIDField()
    published_at = models.DateTimeField()
    report_job_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "assessment_publication"
        ordering = ["published_at", "id"]


class PublishIdempotency(models.Model):
    """Records Idempotency-Key outcomes so retries do not duplicate publish events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField()
    assessment_id = models.UUIDField()
    idempotency_key = models.CharField(max_length=128)
    publication_id = models.UUIDField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_publish_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "assessment_id", "idempotency_key"],
                name="assessment_publish_idem_uniq",
            )
        ]


class Approval(models.Model):
    """Optional approval record when results.approve succeeds."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="approvals"
    )
    actor_id = models.UUIDField()
    approved_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_approval"
        ordering = ["approved_at", "id"]
