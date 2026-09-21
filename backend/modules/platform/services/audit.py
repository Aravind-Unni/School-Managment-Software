"""Audit list service with cursor pagination."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contracts.errors import ValidationFailed
from contracts.identity import RequestContext

from ..models import AuditRecord
from .authority import AuthorityGate
from .wire import audit_dto

PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class AuditService:
    """Read-only scoped audit records."""

    gate: AuthorityGate
    clock: object

    def list(
        self,
        context: RequestContext,
        *,
        action: str | None = None,
        actor_id: UUID | None = None,
        aggregate_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        cursor: str | None = None,
    ) -> dict:
        """Return AuditCollection for the caller's school."""
        self.gate.require_action(context, "audit.read")
        queryset = AuditRecord.objects.filter(school_id=context.school_id).order_by(
            "-occurred_at", "-id"
        )
        if action:
            queryset = queryset.filter(action=action)
        if actor_id is not None:
            queryset = queryset.filter(actor_id=actor_id)
        if aggregate_id is not None:
            queryset = queryset.filter(resource_id=aggregate_id)
        if occurred_from is not None:
            queryset = queryset.filter(occurred_at__gte=occurred_from)
        if occurred_to is not None:
            queryset = queryset.filter(occurred_at__lte=occurred_to)
        if cursor:
            occurred_at, row_id = self._decode_cursor(cursor)
            queryset = queryset.filter(models_q_after(occurred_at=occurred_at, row_id=row_id))
        rows = list(queryset[: PAGE_SIZE + 1])
        next_cursor = None
        if len(rows) > PAGE_SIZE:
            last = rows[PAGE_SIZE - 1]
            next_cursor = self._encode_cursor(last.occurred_at, last.id)
            rows = rows[:PAGE_SIZE]
        return {"items": [audit_dto(row) for row in rows], "next_cursor": next_cursor}

    def _encode_cursor(self, occurred_at: datetime, row_id: UUID) -> str:
        """Encode keyset cursor as URL-safe base64 JSON."""
        payload = {"occurred_at": occurred_at.isoformat(), "id": str(row_id)}
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    def _decode_cursor(self, cursor: str) -> tuple[datetime, UUID]:
        """Decode cursor or raise 422."""
        try:
            raw = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            return datetime.fromisoformat(raw["occurred_at"]), UUID(raw["id"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationFailed("error.validation_failed") from exc


def models_q_after(*, occurred_at: datetime, row_id: UUID):
    """Build a keyset filter for (occurred_at, id) descending order."""
    from django.db.models import Q

    return Q(occurred_at__lt=occurred_at) | Q(occurred_at=occurred_at, id__lt=row_id)
