"""Reconcile submitted attendance when timetable facts change after the fact.

Preserves Session/Entry/Amendment history. Records an audited reason and stamps
reconciliation metadata used by summary eligibility.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import ObjectInaccessible
from contracts.events import AuditRecord
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts

from ..models import AttendanceSession


@dataclass(frozen=True, slots=True)
class ReconcileService:
    """Audited reconciliation without deleting history."""

    access: object
    timetable: object
    platform: object
    clock: object

    def reconcile_after_cancellation(
        self,
        context: RequestContext,
        *,
        session_id: UUID,
        reason: str,
    ) -> AttendanceSession:
        """Mark a submitted session as reconciled after its period was cancelled.

        Does not delete entries or amendments. Summary eligibility ignores
        cancelled periods via Timetable, so historical marks remain for audit.
        """
        try:
            session = AttendanceSession.objects.get(id=session_id)
        except AttendanceSession.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if session.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        self.access.check(
            context,
            "attendance.correct",
            ScopeFacts(
                resource_school_id=session.school_id,
                section_id=session.section_id,
                subject_id=session.subject_id,
                effective_date=session.date,
            ),
        )
        authority = self.timetable.get_teaching_authority(context, session.timetable_session_id)
        now = self.clock.now()
        with transaction.atomic():
            locked = AttendanceSession.objects.select_for_update().get(id=session.id)
            entry_count = locked.entries.count()
            amendment_count = sum(e.amendments.count() for e in locked.entries.all())
            locked.reconciliation_reason = reason
            locked.reconciled_at = now
            locked.version += 1
            locked.updated_at = now
            locked.save(
                update_fields=[
                    "reconciliation_reason",
                    "reconciled_at",
                    "version",
                    "updated_at",
                ]
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="attendance.session_reconciled",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={
                        "reason": reason,
                        "eligible_for_attendance": authority.eligible_for_attendance,
                        "cancelled": authority.cancelled,
                        "entries_preserved": entry_count,
                        "amendments_preserved": amendment_count,
                    },
                )
            )
        # Reload and assert history still present (anti-cheat).
        refreshed = AttendanceSession.objects.prefetch_related("entries__amendments").get(
            id=session_id
        )
        # History must survive reconciliation — count, don't assert-delete.
        if refreshed.entries.count() != entry_count:
            raise RuntimeError("reconciliation deleted entries; history must be preserved")
        return refreshed
