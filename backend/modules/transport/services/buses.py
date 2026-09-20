"""Bus create and list."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from contracts.errors import ValidationFailed
from contracts.events import AuditRecord
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor

from ..models import Bus
from .authority import AuthorityGate
from .wire import bus_to_wire


@dataclass(frozen=True, slots=True)
class BusService:
    """Create and list labelled buses for one school."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        label: str,
        active: bool = True,
    ) -> dict:
        """Create a labelled bus. Does not assign students."""
        self.gate.require_action(context, "transport.manage")
        now = self.clock.now()
        with transaction.atomic():
            bus = Bus.objects.create(
                school_id=context.school_id,
                label=label.strip(),
                active=active,
                version=1,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="transport.bus_created",
                    resource_id=bus.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"label": bus.label, "active": bus.active},
                )
            )
        return bus_to_wire(bus)

    def list_buses(
        self,
        context: RequestContext,
        *,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Return a page of buses for the actor school."""
        self.gate.require_action(context, "transport.read")
        size = clamp_page_size(page_size)
        queryset = Bus.objects.filter(school_id=context.school_id).order_by("label", "id")
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_label = str(position["label"])
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            queryset = queryset.filter(
                Q(label__gt=after_label) | Q(label=after_label, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor({"label": last.label, "id": str(last.id)})
            rows = rows[:size]
        page = Page(items=tuple(bus_to_wire(r) for r in rows), next_cursor=next_cursor)
        return page.to_wire()
