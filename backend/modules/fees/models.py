"""Fee ledger aggregates. Posted rows are immutable; correct via reversal.

Amounts are integer INR paise only — never float.
"""

from __future__ import annotations

import uuid

from django.db import models


class ChargeStatus(models.TextChoices):
    """Derived charge payment state."""

    OPEN = "open", "open"
    PARTIAL = "partial", "partial"
    PAID = "paid", "paid"
    CREDITED = "credited", "credited"
    REVERSED = "reversed", "reversed"


class PaymentMethod(models.TextChoices):
    """Staff-recorded settlement channel. Reference text is not verified."""

    CASH = "cash", "cash"
    BANK = "bank", "bank"
    UPI = "upi", "upi"


class CreditKind(models.TextChoices):
    """Why a credit exists on the ledger."""

    CONCESSION = "concession", "concession"
    OVERPAYMENT = "overpayment", "overpayment"
    ADJUSTMENT = "adjustment", "adjustment"


class FeeHead(models.Model):
    """Named charge category (tuition, bus, opening_balance, …)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=64)
    label_key = models.CharField(max_length=128)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "fees_feehead"
        unique_together = (("school_id", "code"),)


class FeePlan(models.Model):
    """Versioned applicability + schedule of head amounts and due dates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    version = models.IntegerField()
    applicability = models.JSONField(default=dict)
    schedule = models.JSONField(default=list)

    class Meta:
        db_table = "fees_feeplan"
        unique_together = (("school_id", "version"),)


class Charge(models.Model):
    """Immutable posted charge. Unique source_key per school."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="charges")
    source_key = models.CharField(max_length=256)
    amount_paise = models.BigIntegerField()
    balance_paise = models.BigIntegerField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=16, choices=ChargeStatus.choices, default=ChargeStatus.OPEN
    )
    description_key = models.CharField(max_length=128, null=True, blank=True)
    version = models.IntegerField(default=1)
    posted_at = models.DateTimeField()
    payload_fingerprint = models.CharField(max_length=64)

    class Meta:
        db_table = "fees_charge"
        unique_together = (("school_id", "source_key"),)
        indexes = [
            models.Index(fields=["school_id", "student_id"]),
            models.Index(fields=["school_id", "due_date"]),
        ]


class Payment(models.Model):
    """Immutable posted payment with server-allocated receipt number."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    number = models.CharField(max_length=32)
    amount_paise = models.BigIntegerField()
    method = models.CharField(max_length=8, choices=PaymentMethod.choices)
    reference = models.CharField(max_length=128, null=True, blank=True)
    posted_at = models.DateTimeField()
    reversed = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    remaining_paise = models.BigIntegerField()

    class Meta:
        db_table = "fees_payment"
        unique_together = (("school_id", "number"),)
        indexes = [
            models.Index(fields=["school_id", "student_id", "posted_at"]),
        ]


class Allocation(models.Model):
    """Links a payment amount to a charge. Cannot exceed either remainder."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="allocations")
    charge = models.ForeignKey(Charge, on_delete=models.PROTECT, related_name="allocations")
    amount_paise = models.BigIntegerField()
    reversed = models.BooleanField(default=False)

    class Meta:
        db_table = "fees_allocation"


class Credit(models.Model):
    """Concession against a charge, or unallocated overpayment credit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    charge = models.ForeignKey(
        Charge, on_delete=models.PROTECT, related_name="credits", null=True, blank=True
    )
    amount_paise = models.BigIntegerField()
    remaining_paise = models.BigIntegerField()
    reason = models.TextField()
    source_key = models.CharField(max_length=256)
    kind = models.CharField(max_length=16, choices=CreditKind.choices)
    posted_at = models.DateTimeField()
    payload_fingerprint = models.CharField(max_length=64, default="")

    class Meta:
        db_table = "fees_credit"
        unique_together = (("school_id", "source_key"),)


class RefundRecord(models.Model):
    """Explicit refund of available credit. Requires recent 2FA."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    student_id = models.UUIDField(db_index=True)
    credit = models.ForeignKey(
        Credit, on_delete=models.PROTECT, related_name="refunds", null=True, blank=True
    )
    amount_paise = models.BigIntegerField()
    reason = models.TextField()
    posted_at = models.DateTimeField()

    class Meta:
        db_table = "fees_refundrecord"


class Reversal(models.Model):
    """Reversal of a payment; restores charge balances."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="reversals")
    reason = models.TextField()
    posted_at = models.DateTimeField()

    class Meta:
        db_table = "fees_reversal"


class PaymentIdempotency(models.Model):
    """Stores Idempotency-Key outcomes for payment posting."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    idempotency_key = models.CharField(max_length=128)
    payload_fingerprint = models.CharField(max_length=64)
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name="idempotency_rows"
    )

    class Meta:
        db_table = "fees_paymentidempotency"
        unique_together = (("school_id", "idempotency_key"),)


class ReceiptSequence(models.Model):
    """Per-school civil-date counter for receipt numbers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    civil_date = models.DateField()
    next_value = models.IntegerField(default=1)

    class Meta:
        db_table = "fees_receiptsequence"
        unique_together = (("school_id", "civil_date"),)
