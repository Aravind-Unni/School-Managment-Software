"""Demo service layer: the reference implementation of a write path.

Every business module's write path must look like this:
  1. resolve scope and authorise through the host ScopeResolver
  2. open ONE transaction
  3. compare expected_version, raise VersionConflict on mismatch
  4. write the aggregate, bumping version
  5. append the audit record and the outbox event in that SAME transaction

Decision logic here is pure; IO and time arrive as arguments so the rules are
testable without a database.

Does not handle: business meaning. There is none -- see the module docstring.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import ObjectInaccessible, VersionConflict
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page
from contracts.ports import ClockPort, PlatformPort
from shared.http.pagination import paginate_queryset
from shared.scope_resolver import ScopeResolver

from .models import DemoNote

#: Action names this module authorises against. Must match
#: ModuleRegistration.permission_codes.
#: School-scoped: a collection has no single subject, so no relationship.
ACTION_LIST = "demo.list_notes"
#: Relationship-gated: resolved from the note's subject_person_id.
ACTION_READ = "demo.read_note"
#: Teachers only, and only with fresh 2FA.
ACTION_WRITE = "demo.write_note"


@dataclass(frozen=True, slots=True)
class NoteView:
    """The read model returned to the API layer.

    A separate type from the ORM model so that adding a column does not silently
    widen the API.
    """

    id: UUID
    school_id: UUID
    body: str
    version: int
    section_id: UUID | None
    subject_person_id: UUID | None

    def to_wire(self) -> dict[str, object]:
        """Serialise to the frozen API shape."""
        return {
            "id": str(self.id),
            "school_id": str(self.school_id),
            "body": self.body,
            "version": self.version,
            "section_id": str(self.section_id) if self.section_id else None,
            "subject_person_id": (
                str(self.subject_person_id) if self.subject_person_id else None
            ),
        }


def _to_view(note: DemoNote) -> NoteView:
    """Map the ORM row to the read model."""
    return NoteView(
        id=note.id,
        school_id=note.school_id,
        body=note.body,
        version=note.version,
        section_id=note.section_id,
        subject_person_id=note.subject_person_id,
    )


def _cursor_position(note: DemoNote) -> dict[str, object]:
    """Return the keyset position of a row, for the next cursor.

    Ends in ``id`` because ``created_at`` alone is not unique and equal
    timestamps would silently skip or repeat rows across pages.
    """
    return {"created_at": note.created_at.isoformat(), "id": str(note.id)}


class DemoNoteService:
    """Reference service. Holds only ports, never another module's code."""

    def __init__(
        self,
        *,
        resolver: ScopeResolver,
        platform: PlatformPort,
        clock: ClockPort,
    ) -> None:
        """Store the injected ports."""
        self._resolver = resolver
        self._platform = platform
        self._clock = clock

    def list_notes(
        self,
        context: RequestContext,
        *,
        cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[NoteView]:
        """Return one page of notes visible to the actor.

        Authorises once for the section-read action, then filters rows by the
        trusted school id. It does NOT authorise per row: that would be N policy
        calls and would still leak timing.

        Raises ActionDenied / StaleAuth via the resolver.
        """
        self._resolver.require(context, ACTION_LIST)
        queryset = DemoNote.objects.filter(school_id=context.school_id).order_by(
            "created_at", "id"
        )
        page = paginate_queryset(
            queryset,
            cursor=cursor,
            page_size=page_size,
            order_by=("created_at", "id"),
            cursor_fields=_cursor_position,
        )
        return Page(
            items=tuple(_to_view(note) for note in page.items),
            next_cursor=page.next_cursor,
        )

    def get_note(self, context: RequestContext, note_id: UUID) -> NoteView:
        """Return one note after authorising against its own scope.

        Raises ObjectInaccessible (404) for a note in another school, before any
        403 could be raised, so cross-tenant probing cannot distinguish them.
        """
        note = DemoNote.objects.filter(id=note_id).first()
        if note is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self._resolver.require(
            context,
            ACTION_READ,
            subject_person_id=note.subject_person_id,
            resource_school_id=note.school_id,
        )
        return _to_view(note)

    def create_note(
        self,
        context: RequestContext,
        *,
        body: str,
        subject_person_id: UUID,
    ) -> NoteView:
        """Create a note about one person, auditing and emitting in one transaction.

        ``subject_person_id`` is mandatory: the read rule is relationship-gated,
        so a note with no subject could never be authorised for reading and would
        be permanently invisible.

        Requires fresh 2FA via the write action, so this path exercises the
        StaleAuth case during development.
        """
        facts = self._resolver.require(
            context,
            ACTION_WRITE,
            subject_person_id=subject_person_id,
        )
        now = self._clock.now()
        note_id = uuid.uuid4()

        with transaction.atomic():
            note = DemoNote.objects.create(
                id=note_id,
                school_id=context.school_id,
                section_id=facts.section_id,
                subject_person_id=subject_person_id,
                body=body,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self._write_trail(context, note, action="demo.create_note", before={}, now=now)
        return _to_view(note)

    def update_note(
        self,
        context: RequestContext,
        note_id: UUID,
        *,
        body: str,
        expected_version: int,
    ) -> NoteView:
        """Update a note under optimistic concurrency.

        Raises VersionConflict (409) when ``expected_version`` does not match the
        stored version, carrying both values so the client can show a useful
        conflict rather than retrying blindly.
        """
        with transaction.atomic():
            note = (
                DemoNote.objects.select_for_update()
                .filter(id=note_id, school_id=context.school_id)
                .first()
            )
            if note is None:
                raise ObjectInaccessible("error.object_inaccessible")

            self._resolver.require(
                context,
                ACTION_WRITE,
                subject_person_id=note.subject_person_id,
                resource_school_id=note.school_id,
            )

            if note.version != expected_version:
                raise VersionConflict(
                    expected_version=expected_version, actual_version=note.version
                )

            before = {"body": note.body, "version": note.version}
            now = self._clock.now()
            note.body = body
            note.version = note.version + 1
            note.updated_at = now
            note.save(update_fields=["body", "version", "updated_at"])
            self._write_trail(context, note, action="demo.update_note", before=before, now=now)
        return _to_view(note)

    def _write_trail(
        self,
        context: RequestContext,
        note: DemoNote,
        *,
        action: str,
        before: dict[str, object],
        now,
    ) -> None:
        """Append the audit record and outbox event for a write.

        Assumes an open transaction. Both writes go through PlatformPort, which
        does not open its own transaction, so a rollback removes them with the
        aggregate -- the property tests/contracts asserts.
        """
        self._platform.record_audit(
            AuditRecord(
                audit_id=uuid.uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                action=action,
                resource_id=note.id,
                occurred_at=now,
                request_id=context.request_id,
                before=before,
                after={"body": note.body, "version": note.version},
            )
        )
        self._platform.append_event(
            EventEnvelope(
                event_id=uuid.uuid4(),
                school_id=context.school_id,
                event_type=f"demo.{action.split('.', 1)[1]}d",
                occurred_at=now,
                aggregate_id=note.id,
                aggregate_version=note.version,
                payload={"version": note.version},
            )
        )
