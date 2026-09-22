"""Bus participation, billing request and adjustment aggregates.

Unique billing constraint: one period charge per (school, participation, period,
charge_kind). Posted Fees charges are never deleted; corrections use credits.
"""

from __future__ import annotations

import uuid

from django.db import models


class BillingRequestState(models.TextChoices):
    """Lifecycle of one Fees charge request."""

    PENDING = "pending", "pending"
    REQUESTED = "requested", "requested"
    POSTED = "posted", "posted"
    BLOCKED = "blocked", "blocked"
    FAILED = "failed", "failed"


class AdjustmentRequestState(models.TextChoices):
    """Lifecycle of one Fees credit request."""

    PENDING = "pending", "pending"
    REQUESTED = "requested", "requested"
    POSTED = "posted", "posted"
    FAILED = "failed", "failed"


class ChargeKind(models.TextChoices):
    """BillingRequest charge_kind discriminator."""

    PERIOD = "period", "period"
    ADJUSTMENT = "adjustment", "adjustment"


class Bus(models.Model):
    """Optional labelled vehicle. Participation may omit bus_id."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    label = models.CharField(max_length=128)
    active = models.BooleanField(default=True)
    #: The fee plan pupils on this bus are billed under, and its monthly amount
    #: (set from the school config's [transport] section).
    fee_plan_id = models.UUIDField(null=True, blank=True)
    monthly_fee_paise = models.BigIntegerField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "transport_bus"
        indexes = [models.Index(fields=["school_id", "label"])]


class Participation(models.Model):
    """Student bus opt-in with fee plan reference and date range."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    bus_id = models.UUIDField(null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    fee_plan_id = models.UUIDField()
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "transport_participation"
        indexes = [
            models.Index(fields=["school_id", "student_id"]),
            models.Index(fields=["school_id", "from_date", "to_date"]),
        ]


class BillingRequest(models.Model):
    """One attempt to raise a Fees period charge for a participation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    participation_id = models.UUIDField(db_index=True)
    period = models.CharField(max_length=7)
    charge_kind = models.CharField(
        max_length=16, choices=ChargeKind.choices, default=ChargeKind.PERIOD
    )
    source_key = models.CharField(max_length=256)
    state = models.CharField(
        max_length=16, choices=BillingRequestState.choices, default=BillingRequestState.PENDING
    )
    charge_id = models.UUIDField(null=True, blank=True)
    error_code = models.CharField(max_length=128, null=True, blank=True)
    amount_paise = models.BigIntegerField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "transport_billing_request"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "participation_id", "period", "charge_kind"],
                name="transport_billing_school_part_period_kind_uniq",
            )
        ]
        indexes = [models.Index(fields=["school_id", "period", "state"])]


class AdjustmentRequest(models.Model):
    """Explicit Fees credit against a posted bus charge."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    source_key = models.CharField(max_length=256)
    charge_id = models.UUIDField()
    amount_paise = models.BigIntegerField()
    reason = models.TextField()
    state = models.CharField(
        max_length=16,
        choices=AdjustmentRequestState.choices,
        default=AdjustmentRequestState.PENDING,
    )
    credit_id = models.UUIDField(null=True, blank=True)
    error_code = models.CharField(max_length=128, null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "transport_adjustment_request"
        indexes = [models.Index(fields=["school_id", "charge_id"])]
