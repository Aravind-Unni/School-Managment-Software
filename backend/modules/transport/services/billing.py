"""Period billing runs, charge requests, timeout recovery and retries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.transport import PeriodChargeResult
from shared.fakes.fees import FeesCommitTimeout
from shared.fakes.platform import EagerModeNotAsserted

from ..models import BillingRequest, BillingRequestState, ChargeKind, Participation
from .authority import AuthorityGate
from .period import (
    covers_full_period,
    overlaps_period,
    period_bounds,
    prorated_amount,
    source_key_for,
)
from .wire import billing_request_to_wire

BILLING_TASK = "modules.transport.tasks.process_billing_run"


@dataclass(frozen=True, slots=True)
class BillingService:
    """Queue and process period billing against FeesPort."""

    gate: AuthorityGate
    fees: object
    platform: object
    clock: object

    def create_run(
        self,
        context: RequestContext,
        *,
        period: str,
        policy_version: int,
    ) -> dict:
        """Preview eligible rows, enqueue job, or process sync when no worker."""
        self.gate.require_action(context, "transport.bill")
        if policy_version < 1:
            raise ValidationFailed("error.validation_failed")
        preview = self._preview(context, period)
        payload = {
            "school_id": str(context.school_id),
            "period": period,
            "policy_version": policy_version,
            "actor_id": str(context.actor_id),
            "request_id": context.request_id,
        }
        try:
            job_id = self.platform.enqueue(BILLING_TASK, payload=payload)
            state = "queued"
        except EagerModeNotAsserted:
            job_id = str(uuid.uuid4())
            self.process_period(context, period=period)
            state = "succeeded"
        return {
            "job_id": job_id,
            "state": state,
            "period": period,
            "policy_version": policy_version,
            "preview": preview,
        }

    def process_period(self, context: RequestContext, *, period: str) -> int:
        """Raise charges for every eligible participation in the period.

        Returns the number of BillingRequest rows created or updated. Does not
        invent proration amounts when policy is missing.
        """
        count = 0
        for participation in self._eligible_participations(context, period):
            self.request_period_charge(context, participation.id, period)
            count += 1
        return count

    def request_period_charge(
        self,
        context: RequestContext,
        participation_id: UUID,
        period: str,
    ) -> PeriodChargeResult:
        """Request Fees.raise_charge for one participation/period.

        Idempotent on source_key. Partial periods without proration return
        state=blocked. FeesCommitTimeout leaves state=requested without charge_id.
        """
        participation = self._load_participation(context, participation_id)
        source_key = source_key_for(participation.id, period, ChargeKind.PERIOD)
        existing = BillingRequest.objects.filter(
            school_id=context.school_id,
            participation_id=participation.id,
            period=period,
            charge_kind=ChargeKind.PERIOD,
        ).first()
        if existing is not None and existing.state == BillingRequestState.POSTED:
            return PeriodChargeResult(
                source_key=existing.source_key,
                state=existing.state,
                charge_id=existing.charge_id,
            )

        plan = self._plan_or_block(participation.fee_plan_id)
        if plan is None:
            return self._persist_blocked(
                context,
                participation,
                period,
                source_key,
                error_code="transport.error.fee_plan_missing",
                existing=existing,
            )

        full = covers_full_period(
            from_date=participation.from_date,
            to_date=participation.to_date,
            period=period,
        )
        if not full and plan.proration_policy is None:
            return self._persist_blocked(
                context,
                participation,
                period,
                source_key,
                error_code="transport.error.proration_policy_missing",
                existing=existing,
            )

        amount = prorated_amount(
            amount_paise=plan.amount_paise,
            from_date=participation.from_date,
            to_date=participation.to_date,
            period=period,
            policy=None if full else plan.proration_policy,
        )
        _, period_end = period_bounds(period)
        due_date = period_end
        now = self.clock.now()
        # Persist REQUESTED before calling Fees so a post-commit timeout cannot
        # roll back the local request row with the Fees charge still stored.
        with transaction.atomic():
            row = existing or BillingRequest(
                school_id=context.school_id,
                participation_id=participation.id,
                period=period,
                charge_kind=ChargeKind.PERIOD,
                source_key=source_key,
                state=BillingRequestState.PENDING,
                amount_paise=amount,
            )
            if existing is None:
                try:
                    row.save()
                except IntegrityError as exc:
                    raise StateConflict("transport.error.billing_already_posted") from exc
            row.state = BillingRequestState.REQUESTED
            row.amount_paise = amount
            row.error_code = None
            row.charge_id = None
            row.save()
            self._emit_billing_requested(context, row, now)
        try:
            charge = self.fees.raise_charge(
                context,
                source_key=source_key,
                student_id=participation.student_id,
                fee_head_id=plan.fee_head_id,
                amount_paise=amount,
                due_date=due_date,
                description_key="transport.charge.period",
            )
        except FeesCommitTimeout:
            return PeriodChargeResult(
                source_key=source_key,
                state=BillingRequestState.REQUESTED,
                charge_id=None,
            )
        with transaction.atomic():
            locked = BillingRequest.objects.select_for_update().get(id=row.id)
            locked.charge_id = charge.id
            locked.state = BillingRequestState.POSTED
            locked.version += 1
            locked.save(
                update_fields=["charge_id", "state", "version", "error_code", "amount_paise"]
            )
        return PeriodChargeResult(
            source_key=source_key,
            state=BillingRequestState.POSTED,
            charge_id=charge.id,
        )

    def retry(self, context: RequestContext, billing_request_id: UUID) -> dict:
        """Retry a failed or lost-link billing request with the same source_key."""
        self.gate.require_action(context, "transport.bill")
        try:
            row = BillingRequest.objects.get(id=billing_request_id)
        except BillingRequest.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if row.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if row.state == BillingRequestState.POSTED and row.charge_id is not None:
            return billing_request_to_wire(row)
        if row.state == BillingRequestState.BLOCKED:
            raise StateConflict("transport.error.billing_already_posted")
        result = self.request_period_charge(context, row.participation_id, row.period)
        refreshed = BillingRequest.objects.get(id=row.id)
        if result.charge_id is not None and refreshed.charge_id is None:
            # Recover lost link when Fees already has the charge.
            existing_charge = self.fees.get_by_source_key(row.source_key)
            if existing_charge is not None:
                refreshed.charge_id = existing_charge.id
                refreshed.state = BillingRequestState.POSTED
                refreshed.error_code = None
                refreshed.version += 1
                refreshed.save(update_fields=["charge_id", "state", "error_code", "version"])
        refreshed = BillingRequest.objects.get(id=row.id)
        return billing_request_to_wire(refreshed)

    def _preview(self, context: RequestContext, period: str) -> dict[str, int]:
        """Count eligible, blocked and already-billed participations."""
        eligible = 0
        blocked = 0
        already = 0
        for participation in self._eligible_participations(context, period):
            existing = BillingRequest.objects.filter(
                school_id=context.school_id,
                participation_id=participation.id,
                period=period,
                charge_kind=ChargeKind.PERIOD,
            ).first()
            if existing is not None and existing.state == BillingRequestState.POSTED:
                already += 1
                continue
            plan = None
            try:
                plan = self.fees.get_plan(participation.fee_plan_id)
            except Exception:
                blocked += 1
                continue
            full = covers_full_period(
                from_date=participation.from_date,
                to_date=participation.to_date,
                period=period,
            )
            if not full and plan.proration_policy is None:
                blocked += 1
            else:
                eligible += 1
        return {
            "eligible_count": eligible,
            "blocked_count": blocked,
            "already_billed_count": already,
        }

    def _eligible_participations(
        self, context: RequestContext, period: str
    ) -> list[Participation]:
        """Participations that intersect the period for this school."""
        rows = Participation.objects.filter(school_id=context.school_id).order_by("id")
        return [
            row
            for row in rows
            if overlaps_period(from_date=row.from_date, to_date=row.to_date, period=period)
        ]

    def _load_participation(
        self, context: RequestContext, participation_id: UUID
    ) -> Participation:
        """Load participation or raise 404."""
        try:
            row = Participation.objects.get(id=participation_id)
        except Participation.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if row.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return row

    def _plan_or_block(self, fee_plan_id: UUID):
        """Return plan seed or None when missing."""
        try:
            return self.fees.get_plan(fee_plan_id)
        except Exception:
            return None

    def _persist_blocked(
        self,
        context: RequestContext,
        participation: Participation,
        period: str,
        source_key: str,
        *,
        error_code: str,
        existing: BillingRequest | None,
    ) -> PeriodChargeResult:
        """Record a blocked BillingRequest without calling Fees."""
        now = self.clock.now()
        with transaction.atomic():
            row = existing or BillingRequest(
                school_id=context.school_id,
                participation_id=participation.id,
                period=period,
                charge_kind=ChargeKind.PERIOD,
                source_key=source_key,
            )
            row.state = BillingRequestState.BLOCKED
            row.error_code = error_code
            row.amount_paise = None
            row.charge_id = None
            if existing is None:
                try:
                    row.save()
                except IntegrityError as exc:
                    raise StateConflict("transport.error.billing_already_posted") from exc
            else:
                row.version += 1
                row.save()
            self._emit_billing_requested(context, row, now)
        return PeriodChargeResult(
            source_key=source_key,
            state=BillingRequestState.BLOCKED,
            charge_id=None,
        )

    def _emit_billing_requested(
        self, context: RequestContext, row: BillingRequest, now
    ) -> None:
        """Audit + transport.billing_requested event."""
        self.platform.record_audit(
            AuditRecord(
                audit_id=uuid.uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                action="transport.billing_requested",
                resource_id=row.id,
                occurred_at=now,
                request_id=context.request_id,
                after={"state": row.state, "source_key": row.source_key},
            )
        )
        self.platform.append_event(
            EventEnvelope(
                event_id=uuid.uuid4(),
                school_id=context.school_id,
                event_type="transport.billing_requested",
                occurred_at=now,
                aggregate_id=row.id,
                aggregate_version=row.version,
                payload={
                    "request_id": str(row.id),
                    "source_key": row.source_key,
                    "period": row.period,
                },
                correlation_id=context.request_id,
            )
        )
