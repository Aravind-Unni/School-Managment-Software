"""Alumni policy, candidates, profiles, preferences and amendments.

Snapshot fields carry leaving identity only — no grades or transcripts.
Transfer auto-inclusion is fixture-driven; null means stay pending.
"""

from __future__ import annotations

import uuid

from django.db import models


class LeavingOutcome(models.TextChoices):
    """How the pupil left the school."""

    GRADUATE = "graduate", "graduate"
    TRANSFER = "transfer", "transfer"


class CandidateState(models.TextChoices):
    """Review queue for a leaving candidate."""

    PENDING = "pending", "pending"
    APPROVED = "approved", "approved"
    EXCLUDED = "excluded", "excluded"


class ContactChannel(models.TextChoices):
    """Delivery channel for alumni contact."""

    EMAIL = "email", "email"
    SMS = "sms", "sms"
    POSTAL = "postal", "postal"
    PHONE = "phone", "phone"


class ContactPurpose(models.TextChoices):
    """Why contact may be used."""

    ALUMNI_NOTICE = "alumni_notice", "alumni_notice"
    DIRECTORY = "directory", "directory"


class AlumniPolicy(models.Model):
    """Per-school fixture policy. Seed data, not approved production policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    transfer_include_as_alumni = models.BooleanField(null=True, blank=True)
    alumni_login_enabled = models.BooleanField(default=False)
    exportable_fields = models.JSONField(default=list)
    granted_contact_purposes = models.JSONField(default=list)

    class Meta:
        db_table = "alumni_policy"


class AlumniCandidate(models.Model):
    """Pending/reviewed leavers awaiting directory inclusion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    leaving_event_id = models.UUIDField()
    outcome = models.CharField(max_length=16, choices=LeavingOutcome.choices)
    state = models.CharField(
        max_length=16, choices=CandidateState.choices, default=CandidateState.PENDING
    )
    version = models.IntegerField(default=1)
    admission_no = models.CharField(max_length=64)
    display_name = models.CharField(max_length=256)
    last_standard = models.IntegerField()
    leaving_year = models.IntegerField()

    class Meta:
        db_table = "alumni_candidate"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "student_id", "leaving_event_id"],
                name="alumni_candidate_school_student_event_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "state"]),
            models.Index(fields=["school_id", "leaving_event_id"]),
        ]


class AlumniProfile(models.Model):
    """Approved alumni directory row with contact snapshot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    candidate_id = models.UUIDField()
    last_standard = models.IntegerField()
    leaving_year = models.IntegerField()
    outcome = models.CharField(max_length=16, choices=LeavingOutcome.choices)
    snapshot_version = models.IntegerField(default=1)
    email = models.CharField(max_length=256, null=True, blank=True)
    phone = models.CharField(max_length=64, null=True, blank=True)
    postal_address = models.TextField(null=True, blank=True)
    version = models.IntegerField(default=1)
    display_name = models.CharField(max_length=256)
    admission_no = models.CharField(max_length=64)

    class Meta:
        db_table = "alumni_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "student_id"],
                name="alumni_profile_school_student_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["school_id", "leaving_year"]),
            models.Index(fields=["school_id", "outcome"]),
        ]


class ContactPreference(models.Model):
    """Per-profile opt-in/out for a purpose and channel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    profile_id = models.UUIDField(db_index=True)
    person_id = models.UUIDField()
    purpose = models.CharField(max_length=32, choices=ContactPurpose.choices)
    channel = models.CharField(max_length=16, choices=ContactChannel.choices)
    allowed = models.BooleanField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "alumni_contact_preference"
        constraints = [
            models.UniqueConstraint(
                fields=["profile_id", "purpose", "channel"],
                name="alumni_pref_profile_purpose_channel_uniq",
            )
        ]


class ContactAmendment(models.Model):
    """Append-only contact field change with reason."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    profile_id = models.UUIDField(db_index=True)
    old_json = models.JSONField()
    new_json = models.JSONField()
    reason = models.TextField()
    created_at = models.DateTimeField()
    actor_id = models.UUIDField()

    class Meta:
        db_table = "alumni_contact_amendment"
