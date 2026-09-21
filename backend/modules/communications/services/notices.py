"""Notice create and publish."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import AudienceSnapshot, Notice, NoticeState
from .authority import AuthorityGate
from .content import assert_safe_text


def _notice_dto(row: Notice) -> dict:
    """Serialize a Notice row to the contracted DTO shape."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "title": row.title,
        "body": row.body,
        "locale": row.locale,
        "audience": row.audience,
        "state": row.state,
        "version": row.version,
        "scheduled_at": row.scheduled_at.isoformat().replace("+00:00", "Z")
        if row.scheduled_at
        else None,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": row.updated_at.isoformat().replace("+00:00", "Z"),
        "audience_snapshot_id": str(row.audience_snapshot_id)
        if row.audience_snapshot_id
        else None,
    }


def _snapshot_dto(row: AudienceSnapshot) -> dict:
    """Serialize an AudienceSnapshot row."""
    return {
        "id": str(row.id),
        "notice_id": str(row.notice_id),
        "recipient_ids": [str(x) for x in row.recipient_ids],
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
    }


@dataclass(frozen=True, slots=True)
class NoticeService:
    """Create draft notices and publish audience snapshots."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        title: str,
        body: str,
        locale: str,
        audience: dict,
        scheduled_at=None,
    ) -> dict:
        """Create a draft notice. Does not invent whole-school audiences."""
        self.gate.require_action(context, "notices.create")
        assert_safe_text(title, body)
        if locale not in ("en", "ml"):
            raise ValidationFailed("error.validation_failed")
        kind = audience.get("kind")
        if kind not in ("section", "person_ids"):
            raise ValidationFailed("error.validation_failed")
        stored_audience = {"kind": kind}
        if kind == "section":
            stored_audience["section_id"] = str(audience["section_id"])
        else:
            stored_audience["person_ids"] = [str(x) for x in audience["person_ids"]]
        now = self.clock.now()
        row = Notice.objects.create(
            school_id=context.school_id,
            title=title,
            body=body,
            locale=locale,
            audience=stored_audience,
            state=NoticeState.DRAFT,
            version=1,
            scheduled_at=scheduled_at,
            created_at=now,
            updated_at=now,
        )
        return _notice_dto(row)

    def get(self, context: RequestContext, notice_id: UUID) -> dict:
        """Return one notice in the actor school, or 404."""
        row = Notice.objects.filter(id=notice_id, school_id=context.school_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return _notice_dto(row)

    def publish(
        self, context: RequestContext, notice_id: UUID, *, expected_version: int
    ) -> dict:
        """Publish draft → snapshot recipients; emit notice_published."""
        self.gate.require_action(context, "notices.publish")
        with transaction.atomic():
            row = (
                Notice.objects.select_for_update()
                .filter(id=notice_id, school_id=context.school_id)
                .first()
            )
            if row is None:
                raise ObjectInaccessible("error.object_inaccessible")
            if row.version != expected_version:
                raise VersionConflict("error.version_conflict")
            if row.state != NoticeState.DRAFT:
                raise StateConflict("communications.error.notice_not_draft")
            recipient_ids = self._resolve_audience(context, row.audience)
            now = self.clock.now()
            snapshot = AudienceSnapshot.objects.create(
                school_id=context.school_id,
                notice_id=row.id,
                recipient_ids=[str(x) for x in recipient_ids],
                created_at=now,
            )
            row.state = NoticeState.PUBLISHED
            row.version = row.version + 1
            row.audience_snapshot_id = snapshot.id
            row.updated_at = now
            row.save(update_fields=["state", "version", "audience_snapshot_id", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="communications.notice_published",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={"state": "draft", "version": expected_version},
                    after={"state": "published", "version": row.version},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=context.school_id,
                    event_type="communications.notice_published",
                    occurred_at=now,
                    aggregate_id=row.id,
                    aggregate_version=row.version,
                    payload={
                        "notice_id": str(row.id),
                        "audience_snapshot_id": str(snapshot.id),
                    },
                    correlation_id=context.request_id,
                )
            )
        return {"notice": _notice_dto(row), "audience_snapshot": _snapshot_dto(snapshot)}

    def _resolve_audience(self, context: RequestContext, audience: dict) -> list[UUID]:
        """Resolve section or person_ids into recipient UUIDs via Registry."""
        if audience["kind"] == "section":
            section_id = UUID(str(audience["section_id"]))
            roster = self.gate.registry.get_roster(
                context, section_id, self.gate.effective_date()
            )
            return [UUID(str(entry.student_id)) for entry in roster.students]
        raw_ids = audience.get("person_ids") or []
        ids = [UUID(str(x)) for x in raw_ids]
        for person_id in ids:
            self.gate.ensure_person_in_school(context, person_id)
        return ids
