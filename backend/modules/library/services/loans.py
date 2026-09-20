"""Issue, return and renew loans."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor
from contracts.values import school_date

from ..models import (
    BorrowerType,
    Copy,
    CopyState,
    LibraryPolicy,
    Loan,
    LoanIdempotency,
    Renewal,
    ReturnCondition,
)
from .authority import AuthorityGate
from .wire import loan_to_wire


def fingerprint_payload(payload: dict) -> str:
    """Stable sha256 hex of a sorted JSON payload for idempotency."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def policy_for(school_id: UUID) -> LibraryPolicy:
    """Return or create fixture policy defaults for the school."""
    row, _ = LibraryPolicy.objects.get_or_create(
        school_id=school_id,
        defaults={
            "max_active_loans_per_borrower": 3,
            "max_renewals_per_loan": 2,
        },
    )
    return row


@dataclass(frozen=True, slots=True)
class LoanService:
    """Issue, return, renew and list borrower loans."""

    gate: AuthorityGate
    platform: object
    clock: object

    def issue(
        self,
        context: RequestContext,
        *,
        copy_id: UUID,
        borrower_person_id: UUID,
        borrower_type: str,
        due_date: date,
        idempotency_key: str,
    ) -> tuple[dict, int]:
        """Issue a copy. Returns (loan_wire, 201|200)."""
        self.gate.require_action(context, "library.issue")
        if not idempotency_key:
            raise ValidationFailed("error.validation_failed")
        if borrower_type not in {t.value for t in BorrowerType}:
            raise ValidationFailed("error.validation_failed")
        if borrower_type == BorrowerType.STUDENT:
            self.gate.ensure_student_in_school(context, borrower_person_id)

        civil = school_date(self.clock.now())
        if due_date < civil:
            raise ValidationFailed("library.error.invalid_due_date")

        fingerprint = fingerprint_payload(
            {
                "copy_id": str(copy_id),
                "borrower_person_id": str(borrower_person_id),
                "borrower_type": borrower_type,
                "due_date": due_date.isoformat(),
            }
        )
        existing = (
            LoanIdempotency.objects.filter(
                school_id=context.school_id, idempotency_key=idempotency_key
            )
            .select_related("loan")
            .first()
        )
        if existing is not None:
            if existing.payload_fingerprint != fingerprint:
                raise StateConflict("library.error.idempotency_conflict")
            return loan_to_wire(existing.loan), 200

        policy = policy_for(context.school_id)
        open_count = Loan.objects.filter(
            school_id=context.school_id,
            borrower_person_id=borrower_person_id,
            returned_at__isnull=True,
        ).count()
        if open_count >= policy.max_active_loans_per_borrower:
            raise ValidationFailed("library.error.borrower_limit_exceeded")

        now = self.clock.now()
        try:
            with transaction.atomic():
                raced = (
                    LoanIdempotency.objects.select_for_update()
                    .filter(school_id=context.school_id, idempotency_key=idempotency_key)
                    .select_related("loan")
                    .first()
                )
                if raced is not None:
                    if raced.payload_fingerprint != fingerprint:
                        raise StateConflict("library.error.idempotency_conflict")
                    return loan_to_wire(raced.loan), 200

                copy = (
                    Copy.objects.select_for_update()
                    .filter(id=copy_id, school_id=context.school_id)
                    .first()
                )
                if copy is None:
                    raise ObjectInaccessible("error.object_inaccessible")
                if copy.state != CopyState.AVAILABLE:
                    raise StateConflict("library.error.copy_not_available")
                if Loan.objects.filter(copy_id=copy.id, returned_at__isnull=True).exists():
                    raise StateConflict("library.error.copy_not_available")

                loan = Loan.objects.create(
                    school_id=context.school_id,
                    copy_id=copy.id,
                    borrower_person_id=borrower_person_id,
                    borrower_type=borrower_type,
                    issued_at=now,
                    due_date=due_date,
                    returned_at=None,
                    version=1,
                )
                copy.state = CopyState.ON_LOAN
                copy.version += 1
                copy.save(update_fields=["state", "version"])
                LoanIdempotency.objects.create(
                    school_id=context.school_id,
                    idempotency_key=idempotency_key,
                    payload_fingerprint=fingerprint,
                    loan=loan,
                )
                self.platform.record_audit(
                    AuditRecord(
                        audit_id=uuid.uuid4(),
                        school_id=context.school_id,
                        actor_id=context.actor_id,
                        action="library.loan_issued",
                        resource_id=loan.id,
                        occurred_at=now,
                        request_id=context.request_id,
                        after={"copy_id": str(copy.id), "due_date": due_date.isoformat()},
                    )
                )
                self.platform.append_event(
                    EventEnvelope(
                        event_id=uuid.uuid4(),
                        school_id=context.school_id,
                        event_type="library.loan_issued",
                        occurred_at=now,
                        aggregate_id=loan.id,
                        aggregate_version=loan.version,
                        payload={
                            "loan_id": str(loan.id),
                            "borrower_person_id": str(borrower_person_id),
                            "due_date": due_date.isoformat(),
                        },
                        correlation_id=context.request_id,
                    )
                )
        except IntegrityError as exc:
            raise StateConflict("library.error.copy_not_available") from exc
        return loan_to_wire(loan), 201

    def return_loan(
        self,
        context: RequestContext,
        loan_id: UUID,
        *,
        returned_at,
        condition: str,
        expected_version: int,
    ) -> dict:
        """Close a loan. Retry-safe: already closed returns the closed DTO."""
        self.gate.require_action(context, "library.return")
        if condition not in {c.value for c in ReturnCondition}:
            raise ValidationFailed("error.validation_failed")
        now = self.clock.now()
        with transaction.atomic():
            loan = (
                Loan.objects.select_for_update()
                .filter(id=loan_id, school_id=context.school_id)
                .first()
            )
            if loan is None:
                raise ObjectInaccessible("error.object_inaccessible")
            if loan.returned_at is not None:
                return loan_to_wire(loan)
            if loan.version != expected_version:
                raise VersionConflict("error.version_conflict")

            copy = (
                Copy.objects.select_for_update()
                .filter(id=loan.copy_id, school_id=context.school_id)
                .first()
            )
            if copy is None:
                raise ObjectInaccessible("error.object_inaccessible")

            loan.returned_at = returned_at
            loan.version += 1
            loan.save(update_fields=["returned_at", "version"])

            if condition == ReturnCondition.OK:
                new_state = CopyState.AVAILABLE
            elif condition == ReturnCondition.DAMAGED:
                new_state = CopyState.DAMAGED
            else:
                new_state = CopyState.LOST
            copy.state = new_state
            copy.version += 1
            copy.save(update_fields=["state", "version"])

            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="library.loan_returned",
                    resource_id=loan.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"condition": condition, "copy_state": new_state},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="library.loan_returned",
                    occurred_at=now,
                    aggregate_id=loan.id,
                    aggregate_version=loan.version,
                    payload={"loan_id": str(loan.id), "copy_id": str(loan.copy_id)},
                    correlation_id=context.request_id,
                )
            )
        return loan_to_wire(loan)

    def renew(
        self,
        context: RequestContext,
        loan_id: UUID,
        *,
        new_due_date: date,
        expected_version: int,
        reason: str | None = None,
    ) -> dict:
        """Extend due date; append Renewal preserving old_due."""
        self.gate.require_action(context, "library.renew")
        civil = school_date(self.clock.now())
        policy = policy_for(context.school_id)
        now = self.clock.now()
        with transaction.atomic():
            loan = (
                Loan.objects.select_for_update()
                .filter(id=loan_id, school_id=context.school_id)
                .first()
            )
            if loan is None:
                raise ObjectInaccessible("error.object_inaccessible")
            if loan.returned_at is not None:
                raise ValidationFailed("library.error.renewal_not_allowed")
            if loan.version != expected_version:
                raise VersionConflict("error.version_conflict")
            if loan.due_date < civil:
                raise ValidationFailed("library.error.renewal_not_allowed")
            if new_due_date <= loan.due_date:
                raise ValidationFailed("library.error.renewal_not_allowed")
            renewals = Renewal.objects.filter(loan_id=loan.id).count()
            if renewals >= policy.max_renewals_per_loan:
                raise ValidationFailed("library.error.renewal_limit_exceeded")

            old_due = loan.due_date
            Renewal.objects.create(
                school_id=context.school_id,
                loan_id=loan.id,
                old_due=old_due,
                new_due=new_due_date,
                actor_id=context.actor_id,
                reason=reason,
                renewed_at=now,
            )
            loan.due_date = new_due_date
            loan.version += 1
            loan.save(update_fields=["due_date", "version"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="library.loan_renewed",
                    resource_id=loan.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={"due_date": old_due.isoformat()},
                    after={"due_date": new_due_date.isoformat()},
                )
            )
        return loan_to_wire(loan)

    def list_borrower_loans(
        self,
        context: RequestContext,
        person_id: UUID,
        *,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Borrower history visible to staff or self/guardian."""
        self.gate.require_borrower_visibility(context, person_id)
        size = clamp_page_size(page_size)
        queryset = Loan.objects.filter(
            school_id=context.school_id, borrower_person_id=person_id
        ).order_by("-issued_at", "id")
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_issued = position["issued_at"]
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            queryset = queryset.filter(
                Q(issued_at__lt=after_issued) | Q(issued_at=after_issued, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(
                {"issued_at": last.issued_at.isoformat(), "id": str(last.id)}
            )
            rows = rows[:size]
        page = Page(items=tuple(loan_to_wire(r) for r in rows), next_cursor=next_cursor)
        return page.to_wire()
