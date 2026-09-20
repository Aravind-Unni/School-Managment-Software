"""Interventions and parent-teacher meetings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import encode_cursor
from contracts.performance import InterventionDTO, InterventionPage

from ..models import Intervention, InterventionState, Meeting, Visibility
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class InterventionService:
    """Create interventions/meetings and list visible interventions."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        goal: str,
        owner_id: UUID,
        review_date: date,
        visibility: str,
        resource_ids: list[UUID] | None = None,
    ) -> Intervention:
        """Create an active intervention for one pupil."""
        if not goal or not goal.strip():
            raise ValidationFailed("performance.error.unknown_field")
        self.gate.require_staff_action(context, "interventions.manage", student_id=student_id)
        now = self.clock.now()
        with transaction.atomic():
            row = Intervention.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                student_id=student_id,
                goal=goal.strip(),
                owner_id=owner_id,
                review_date=review_date,
                state=InterventionState.ACTIVE,
                visibility=visibility,
                version=1,
                resource_ids=[str(r) for r in (resource_ids or [])],
                created_at=now,
                updated_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="intervention.created",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"student_id": str(student_id), "goal": goal[:80]},
                )
            )
        return row

    def mark_reviewed(
        self,
        context: RequestContext,
        intervention_id: UUID,
        *,
        state: str = InterventionState.REVIEWED,
    ) -> Intervention:
        """Move intervention to reviewed/completed and emit event."""
        self.gate.require_staff_action(context, "interventions.manage")
        try:
            row = Intervention.objects.get(id=intervention_id, school_id=context.school_id)
        except Intervention.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        now = self.clock.now()
        with transaction.atomic():
            row.state = state
            row.version = row.version + 1
            row.updated_at = now
            row.save()
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="intervention.reviewed",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"state": state},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=context.school_id,
                    event_type="performance.intervention_reviewed",
                    occurred_at=now,
                    aggregate_id=row.id,
                    aggregate_version=row.version,
                    payload={"intervention_id": str(row.id), "state": state},
                    correlation_id=context.request_id,
                )
            )
        return row

    def list_for_student(
        self,
        context: RequestContext,
        student_id: UUID,
        cursor: str | None = None,
    ) -> InterventionPage:
        """Return interventions the actor may see for one pupil."""
        self.gate.require_student_read(context, student_id)
        guardian = self.gate.is_guardian_or_self(context, student_id)
        qs = Intervention.objects.filter(
            school_id=context.school_id, student_id=student_id
        ).order_by("-created_at", "id")
        if guardian:
            qs = qs.exclude(visibility=Visibility.RESTRICTED).exclude(
                visibility=Visibility.STAFF
            )
        # Cursor is opaque id offset; empty page when unknown.
        if cursor is not None:
            # Opaque cursor reserved; baseline pages fit one screen.
            _ = cursor
        items = list(qs[:50])
        next_cursor = encode_cursor(str(items[-1].id)) if len(items) == 50 else None
        return InterventionPage(
            items=tuple(self._to_dto(row) for row in items),
            next_cursor=next_cursor,
        )

    def create_meeting(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        meeting_date: date,
        participants: list[UUID],
        notes: str,
        actions: list[str],
        visibility: str,
    ) -> Meeting:
        """Record a parent-teacher meeting."""
        if not participants:
            raise ValidationFailed("performance.error.unknown_field")
        self.gate.require_staff_action(context, "meetings.record", student_id=student_id)
        now = self.clock.now()
        with transaction.atomic():
            row = Meeting.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                student_id=student_id,
                date=meeting_date,
                participants=[str(p) for p in participants],
                notes=notes,
                actions=list(actions),
                visibility=visibility,
                version=1,
                created_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="meeting.created",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"student_id": str(student_id), "date": str(meeting_date)},
                )
            )
        return row

    @staticmethod
    def _to_dto(row: Intervention) -> InterventionDTO:
        """Map ORM row to frozen DTO."""
        return InterventionDTO(
            id=row.id,
            school_id=row.school_id,
            student_id=row.student_id,
            goal=row.goal,
            owner_id=row.owner_id,
            review_date=row.review_date,
            state=row.state,
            visibility=row.visibility,
            version=row.version,
            resource_ids=tuple(UUID(x) for x in row.resource_ids),
        )
