"""Fee plan and charge posting."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.fees import ChargeDTO
from contracts.identity import RequestContext

from ..models import Charge, FeeHead, FeePlan
from .authority import AuthorityGate
from .ledger import charge_status_for, fingerprint_payload
from .wire import charge_to_wire, fee_plan_to_wire


@dataclass(frozen=True, slots=True)
class PlanService:
    """Create versioned fee plans with heads."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create_plan(
        self,
        context: RequestContext,
        *,
        fee_heads: list[dict],
        applicability: dict,
        schedule: list[dict],
        version: int,
    ) -> dict:
        """Create heads (upsert by code) and a fee plan version."""
        self.gate.require_staff_action(context, "fees.configure")
        if version < 1 or not fee_heads or not schedule:
            raise ValidationFailed("error.validation_failed")
        now = self.clock.now()
        with transaction.atomic():
            heads: list[FeeHead] = []
            code_to_head: dict[str, FeeHead] = {}
            for item in fee_heads:
                head, _ = FeeHead.objects.update_or_create(
                    school_id=context.school_id,
                    code=item["code"],
                    defaults={"label_key": item["label_key"], "version": 1},
                )
                heads.append(head)
                code_to_head[head.code] = head
            resolved_schedule = []
            for row in schedule:
                head = code_to_head.get(row["fee_head_code"])
                if head is None:
                    raise ValidationFailed("error.validation_failed")
                if int(row["amount_paise"]) <= 0:
                    raise ValidationFailed("fees.error.amount_not_positive")
                resolved_schedule.append(
                    {
                        "fee_head_id": str(head.id),
                        "amount_paise": int(row["amount_paise"]),
                        "due_date": str(row["due_date"]),
                    }
                )
            plan = FeePlan.objects.create(
                school_id=context.school_id,
                version=version,
                applicability=applicability or {},
                schedule=resolved_schedule,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.fee_plan_created",
                    resource_id=plan.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": version},
                )
            )
        return fee_plan_to_wire(plan, heads)


@dataclass(frozen=True, slots=True)
class ChargeService:
    """Raise charges with school-unique source_key."""

    gate: AuthorityGate
    registry: object
    platform: object
    clock: object

    def raise_charge(
        self,
        context: RequestContext,
        *,
        source_key: str,
        student_id: UUID,
        fee_head_id: UUID,
        amount_paise: int,
        due_date: date,
        description_key: str,
        via_api: bool = False,
    ) -> tuple[ChargeDTO, bool]:
        """Post a charge or return the existing identical one.

        Returns (dto, created). Changed payload on the same source_key → 409.
        """
        if via_api:
            self.gate.require_staff_action(context, "fees.configure", student_id=student_id)
        else:
            self.gate.require_staff_action(context, "fees.configure", student_id=student_id)
        if amount_paise <= 0:
            raise ValidationFailed("fees.error.amount_not_positive")
        if not source_key:
            raise ValidationFailed("error.validation_failed")
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        try:
            head = FeeHead.objects.get(id=fee_head_id, school_id=context.school_id)
        except FeeHead.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc

        fingerprint = fingerprint_payload(
            {
                "student_id": str(student_id),
                "fee_head_id": str(fee_head_id),
                "amount_paise": amount_paise,
                "due_date": due_date.isoformat(),
                "description_key": description_key,
            }
        )
        existing = Charge.objects.filter(
            school_id=context.school_id, source_key=source_key
        ).first()
        if existing is not None:
            if existing.payload_fingerprint != fingerprint:
                raise StateConflict("fees.error.source_key_conflict")
            return (
                ChargeDTO(
                    id=existing.id,
                    source_key=existing.source_key,
                    amount_paise=existing.amount_paise,
                    balance_paise=existing.balance_paise,
                    status=existing.status,
                    student_id=existing.student_id,
                    fee_head_id=existing.fee_head_id,
                    due_date=existing.due_date,
                    school_id=existing.school_id,
                    description_key=existing.description_key,
                    version=existing.version,
                ),
                False,
            )

        now = self.clock.now()
        with transaction.atomic():
            charge = Charge.objects.create(
                school_id=context.school_id,
                student_id=student_id,
                fee_head=head,
                source_key=source_key,
                amount_paise=amount_paise,
                balance_paise=amount_paise,
                due_date=due_date,
                status=charge_status_for(amount_paise, amount_paise),
                description_key=description_key or None,
                posted_at=now,
                payload_fingerprint=fingerprint,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.charge_posted",
                    resource_id=charge.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"source_key": source_key, "amount_paise": amount_paise},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="fees.charge_posted",
                    occurred_at=now,
                    aggregate_id=charge.id,
                    aggregate_version=charge.version,
                    payload={
                        "charge_id": str(charge.id),
                        "student_id": str(student_id),
                        "source_key": source_key,
                    },
                    correlation_id=context.request_id,
                )
            )
        return (
            ChargeDTO(
                id=charge.id,
                source_key=charge.source_key,
                amount_paise=charge.amount_paise,
                balance_paise=charge.balance_paise,
                status=charge.status,
                student_id=charge.student_id,
                fee_head_id=charge.fee_head_id,
                due_date=charge.due_date,
                school_id=charge.school_id,
                description_key=charge.description_key,
                version=charge.version,
            ),
            True,
        )

    def create_via_api(self, context: RequestContext, body: dict) -> tuple[dict, bool]:
        """Return wire dict and created flag for the HTTP create path."""
        dto, created = self.raise_charge(
            context,
            source_key=body["source_key"],
            student_id=body["student_id"],
            fee_head_id=body["fee_head_id"],
            amount_paise=int(body["amount_paise"]),
            due_date=body["due_date"],
            description_key=body.get("description_key") or "fees.charge",
            via_api=True,
        )
        charge = Charge.objects.get(id=dto.id)
        return charge_to_wire(charge), created
