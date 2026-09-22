"""Participation create, read, patch, list and overlap checks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor

from ..models import Bus, Participation
from .authority import AuthorityGate
from .period import ranges_overlap
from .wire import participation_to_wire


@dataclass(frozen=True, slots=True)
class ParticipationService:
    """Opt students into bus participation and revise end dates."""

    gate: AuthorityGate
    registry: object
    fees: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        from_date: date,
        fee_plan_id: UUID,
        bus_id: UUID | None = None,
    ) -> dict:
        """Create participation after overlap and fee-plan checks."""
        self.gate.require_action(context, "transport.manage", student_id=student_id)
        self.registry.get_student(context, student_id)
        self._require_fee_plan(fee_plan_id)
        if bus_id is not None:
            self._require_active_bus(context, bus_id)
        self._reject_overlap(context, student_id, from_date, None, exclude_id=None)
        now = self.clock.now()
        with transaction.atomic():
            row = Participation.objects.create(
                school_id=context.school_id,
                student_id=student_id,
                bus_id=bus_id,
                from_date=from_date,
                to_date=None,
                fee_plan_id=fee_plan_id,
                version=1,
            )
            self._audit_and_event(context, row, now, action="created")
        return participation_to_wire(row)

    def get(self, context: RequestContext, participation_id: UUID) -> dict:
        """Read one participation visible to the actor school."""
        row = self._load(context, participation_id)
        self.gate.require_participation_read(context, row.student_id)
        return participation_to_wire(row)

    def patch(
        self,
        context: RequestContext,
        participation_id: UUID,
        *,
        expected_version: int,
        reason: str,
        to_date: date | None = None,
        bus_id: UUID | None = None,
        fields_set: frozenset[str] | None = None,
    ) -> dict:
        """Revise end date or bus assignment with optimistic concurrency."""
        if not reason or not reason.strip():
            raise ValidationFailed("transport.error.reason_required")
        provided = fields_set or frozenset()
        row = self._load(context, participation_id)
        self.gate.require_action(context, "transport.manage", student_id=row.student_id)
        if row.version != expected_version:
            raise VersionConflict("error.version_conflict")
        new_to = to_date if "to_date" in provided else row.to_date
        new_bus = bus_id if "bus_id" in provided else row.bus_id
        if new_to is not None and new_to < row.from_date:
            raise ValidationFailed("transport.error.invalid_date_range")
        if new_bus is not None:
            self._require_active_bus(context, new_bus)
        self._reject_overlap(context, row.student_id, row.from_date, new_to, exclude_id=row.id)
        now = self.clock.now()
        with transaction.atomic():
            locked = Participation.objects.select_for_update().get(id=row.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked.to_date = new_to
            locked.bus_id = new_bus
            locked.version += 1
            locked.save(update_fields=["to_date", "bus_id", "version"])
            self._audit_and_event(
                context,
                locked,
                now,
                action="patched",
                before={"version": expected_version},
                after={"version": locked.version, "reason": reason},
            )
        return participation_to_wire(locked)

    def list_participants(
        self,
        context: RequestContext,
        *,
        on_date: date,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Paginated participations effective on a school civil date."""
        self.gate.require_action(context, "transport.read")
        size = clamp_page_size(page_size)
        queryset = (
            Participation.objects.filter(school_id=context.school_id, from_date__lte=on_date)
            .filter(models_to_date_open_or_after(on_date))
            .order_by("student_id", "id")
        )
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_student = str(position["student_id"])
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            from django.db.models import Q

            queryset = queryset.filter(
                Q(student_id__gt=after_student) | Q(student_id=after_student, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(
                {"student_id": str(last.student_id), "id": str(last.id)}
            )
            rows = rows[:size]
        items = []
        buses = Bus.objects.filter(school_id=context.school_id)
        labels = dict(buses.values_list("id", "label"))
        for row in rows:
            student = self.registry.get_student(context, row.student_id)
            items.append(
                {
                    "participation_id": str(row.id),
                    "student_id": str(row.student_id),
                    "display_name": student.display_name,
                    "bus_id": str(row.bus_id) if row.bus_id else None,
                    "bus_label": labels.get(row.bus_id),
                    "version": row.version,
                    "from_date": row.from_date.isoformat(),
                    "to_date": row.to_date.isoformat() if row.to_date else None,
                    "fee_plan_id": str(row.fee_plan_id),
                }
            )
        return Page(items=tuple(items), next_cursor=next_cursor).to_wire()

    def _load(self, context: RequestContext, participation_id: UUID) -> Participation:
        """Load participation or raise 404 for absent/other-school."""
        try:
            row = Participation.objects.get(id=participation_id)
        except Participation.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if row.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return row

    def _require_fee_plan(self, fee_plan_id: UUID) -> None:
        """Raise when FakeFees/provider has no amount for the plan."""
        try:
            self.fees.get_plan(fee_plan_id)
        except Exception as exc:
            raise ValidationFailed("transport.error.fee_plan_missing") from exc

    def _require_active_bus(self, context: RequestContext, bus_id: UUID) -> None:
        """Raise when bus is missing, other-school, or inactive."""
        try:
            bus = Bus.objects.get(id=bus_id)
        except Bus.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if bus.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if not bus.active:
            raise ValidationFailed("transport.error.bus_inactive")

    def _reject_overlap(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date | None,
        *,
        exclude_id: UUID | None,
    ) -> None:
        """Reject when another active participation would overlap."""
        others = Participation.objects.filter(
            school_id=context.school_id, student_id=student_id
        )
        if exclude_id is not None:
            others = others.exclude(id=exclude_id)
        for other in others:
            if ranges_overlap(from_date, to_date, other.from_date, other.to_date):
                raise ValidationFailed("transport.error.overlapping_participation")

    def _audit_and_event(
        self,
        context: RequestContext,
        row: Participation,
        now,
        *,
        action: str,
        before: dict | None = None,
        after: dict | None = None,
    ) -> None:
        """Write audit + transport.participation_changed in the caller txn."""
        self.platform.record_audit(
            AuditRecord(
                audit_id=uuid.uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                action=f"transport.participation_{action}",
                resource_id=row.id,
                occurred_at=now,
                request_id=context.request_id,
                before=before or {},
                after=after or {"version": row.version},
            )
        )
        self.platform.append_event(
            EventEnvelope(
                event_id=uuid.uuid4(),
                school_id=context.school_id,
                event_type="transport.participation_changed",
                occurred_at=now,
                aggregate_id=row.id,
                aggregate_version=row.version,
                payload={
                    "participation_id": str(row.id),
                    "student_id": str(row.student_id),
                    "effective_date": row.from_date.isoformat(),
                    "version": row.version,
                },
                correlation_id=context.request_id,
            )
        )


def models_to_date_open_or_after(on_date: date):
    """Q filter: to_date is null or on_date is still within the range."""
    from django.db.models import Q

    return Q(to_date__isnull=True) | Q(to_date__gte=on_date)
