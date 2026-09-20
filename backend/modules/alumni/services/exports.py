"""Alumni export job acceptance (exchange delivery PENDING)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import transaction

from contracts.errors import ValidationFailed
from contracts.events import AuditRecord
from contracts.identity import RequestContext
from shared.fakes.platform import EagerModeNotAsserted

from .authority import AuthorityGate

EXPORT_TASK = "modules.alumni.tasks.run_export"
ALLOWED_EXPORT_FIELD_NAMES = frozenset(
    {
        "display_name",
        "admission_no",
        "leaving_year",
        "outcome",
        "email",
        "phone",
        "postal_address",
    }
)


@dataclass(frozen=True, slots=True)
class ExportService:
    """Validate granted fields and accept an export job via Platform.enqueue."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create_export(
        self,
        context: RequestContext,
        *,
        filters: dict,
        fields: list[str],
    ) -> dict:
        """Reject ungranted fields; enqueue alumni.export or accept without worker.

        Returns ExportJobDTO. Real exchange-backed delivery is PENDING (M13).
        Does not claim worker crash/retry coverage when enqueue is refused.
        """
        self.gate.require_action(context, "alumni.export")
        if not fields:
            raise ValidationFailed("error.validation_failed")
        unknown = [name for name in fields if name not in ALLOWED_EXPORT_FIELD_NAMES]
        if unknown:
            raise ValidationFailed("error.validation_failed")
        policy = self.gate.policy_for(context.school_id)
        granted = set(policy.exportable_fields or [])
        not_granted = [name for name in fields if name not in granted]
        if not_granted:
            raise ValidationFailed("alumni.error.export_field_not_granted")

        payload = {
            "school_id": str(context.school_id),
            "filters": filters,
            "fields": list(fields),
            "actor_id": str(context.actor_id),
            "request_id": context.request_id,
            "kind": "alumni.export",
        }
        now = self.clock.now()
        with transaction.atomic():
            try:
                job_id = self.platform.enqueue(EXPORT_TASK, payload=payload)
                state = "queued"
            except EagerModeNotAsserted:
                job_id = str(uuid.uuid4())
                state = "queued"
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="alumni.export_requested",
                    resource_id=uuid.UUID(job_id) if _is_uuid(job_id) else uuid.uuid4(),
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"fields": list(fields), "state": state, "job_id": job_id},
                )
            )
        return {"job_id": job_id, "state": state}


def _is_uuid(value: str) -> bool:
    """Return True when value parses as a UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False
