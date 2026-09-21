"""Notice, template, delivery and provider-config models for M11."""

from __future__ import annotations

import uuid

from django.db import models


class NoticeState(models.TextChoices):
    """Lifecycle of an in-app notice."""

    DRAFT = "draft", "draft"
    PUBLISHED = "published", "published"


class DeliveryState(models.TextChoices):
    """Outbound delivery lifecycle."""

    QUEUED = "queued", "queued"
    SENDING = "sending", "sending"
    ACCEPTED = "accepted", "accepted"
    DELIVERED = "delivered", "delivered"
    FAILED = "failed", "failed"
    UNKNOWN = "unknown", "unknown"


class Channel(models.TextChoices):
    """Supported launch channels."""

    IN_APP = "in_app", "in_app"
    SMS = "sms", "sms"


class CommunicationsPolicy(models.Model):
    """Per-school fixture policy. Not approved production policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    sms_configure_requires_2fa = models.BooleanField(default=False)
    live_provider = models.CharField(max_length=32, default="fake")
    channels_enabled = models.JSONField(default=list)

    class Meta:
        db_table = "communications_policy"


class Notice(models.Model):
    """Bilingual-capable in-app notice aggregate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    locale = models.CharField(max_length=8)
    audience = models.JSONField()
    state = models.CharField(
        max_length=16, choices=NoticeState.choices, default=NoticeState.DRAFT
    )
    version = models.IntegerField(default=1)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    audience_snapshot_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "communications_notice"
        indexes = [models.Index(fields=["school_id", "state"])]


class AudienceSnapshot(models.Model):
    """Frozen recipient set at publish time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    notice_id = models.UUIDField(db_index=True)
    recipient_ids = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "communications_audience_snapshot"


class MessageTemplate(models.Model):
    """Versioned bilingual message body."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    key = models.CharField(max_length=100)
    locale = models.CharField(max_length=8)
    version = models.IntegerField(default=1)
    body = models.TextField()
    provider_template_id = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "communications_message_template"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "key", "locale", "version"],
                name="communications_template_school_key_locale_ver_uniq",
            )
        ]


class VerifiedContact(models.Model):
    """Fixture stand-in for Registry verified contact refs until M02 exposes them."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    recipient_ref = models.UUIDField(db_index=True)
    person_id = models.UUIDField()
    channel = models.CharField(max_length=16, choices=Channel.choices)
    verified = models.BooleanField(default=True)
    revoked = models.BooleanField(default=False)
    purpose_allowed = models.BooleanField(default=True)

    class Meta:
        db_table = "communications_verified_contact"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "recipient_ref"],
                name="communications_verified_contact_school_ref_uniq",
            )
        ]


class Delivery(models.Model):
    """One outbound message attempt track."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    recipient_ref = models.UUIDField()
    channel = models.CharField(max_length=16, choices=Channel.choices)
    dedupe_key = models.CharField(max_length=200)
    payload_hash = models.CharField(max_length=64)
    state = models.CharField(
        max_length=16, choices=DeliveryState.choices, default=DeliveryState.QUEUED
    )
    provider_ref = models.CharField(max_length=200, null=True, blank=True)
    template_key = models.CharField(max_length=100)
    locale = models.CharField(max_length=8)
    variables = models.JSONField(default=dict)
    rendered_body = models.TextField(default="")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "communications_delivery"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "dedupe_key"],
                name="communications_delivery_school_dedupe_uniq",
            )
        ]
        indexes = [models.Index(fields=["school_id", "state"])]


class Attempt(models.Model):
    """One provider or worker attempt against a delivery."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    delivery_id = models.UUIDField(db_index=True)
    attempted_at = models.DateTimeField()
    outcome = models.CharField(max_length=32)

    class Meta:
        db_table = "communications_attempt"
        indexes = [models.Index(fields=["delivery_id", "attempted_at"])]


class ProviderConfig(models.Model):
    """Live SMS provider registration. secret_ref is opaque, never the secret."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(unique=True)
    secret_ref = models.CharField(max_length=200)
    sender_id = models.CharField(max_length=20)
    enabled = models.BooleanField(default=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "communications_provider_config"


class CallbackNonce(models.Model):
    """Replay protection for provider callbacks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    provider = models.CharField(max_length=32)
    nonce = models.CharField(max_length=200)
    consumed_at = models.DateTimeField()

    class Meta:
        db_table = "communications_callback_nonce"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "provider", "nonce"],
                name="communications_callback_nonce_uniq",
            )
        ]
