"""Title and copy catalogue operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q

from contracts.errors import ObjectInaccessible, ValidationFailed, VersionConflict
from contracts.events import AuditRecord
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor

from ..models import Copy, CopyAdjustment, CopyState, Title
from .authority import AuthorityGate
from .wire import adjustment_to_wire, copy_to_wire, title_to_wire


@dataclass(frozen=True, slots=True)
class CatalogueService:
    """Create titles/copies, search, adjust copy state."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create_title(
        self,
        context: RequestContext,
        *,
        name: str,
        author: str,
        language: str,
        isbn: str | None = None,
    ) -> dict:
        """Create a catalogue title. ISBN optional and not unique."""
        self.gate.require_action(context, "library.catalogue.manage")
        now = self.clock.now()
        with transaction.atomic():
            title = Title.objects.create(
                school_id=context.school_id,
                isbn=isbn,
                name=name.strip(),
                author=author.strip(),
                language=language.strip(),
                version=1,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="library.title_created",
                    resource_id=title.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"name": title.name, "author": title.author},
                )
            )
        return title_to_wire(title)

    def search_titles(
        self,
        context: RequestContext,
        *,
        q: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Unicode substring search on name/author for the actor school."""
        self.gate.require_catalogue_read(context)
        size = clamp_page_size(page_size)
        queryset = Title.objects.filter(school_id=context.school_id).order_by("name", "id")
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(author__icontains=q))
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_name = str(position["name"])
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            queryset = queryset.filter(
                Q(name__gt=after_name) | Q(name=after_name, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor({"name": last.name, "id": str(last.id)})
            rows = rows[:size]
        page = Page(items=tuple(title_to_wire(r) for r in rows), next_cursor=next_cursor)
        return page.to_wire()

    def create_copy(
        self,
        context: RequestContext,
        *,
        title_id: UUID,
        accession_no: str,
    ) -> dict:
        """Register a physical copy; reject duplicate accession."""
        self.gate.require_action(context, "library.catalogue.manage")
        title = Title.objects.filter(id=title_id, school_id=context.school_id).first()
        if title is None:
            raise ObjectInaccessible("error.object_inaccessible")
        now = self.clock.now()
        try:
            with transaction.atomic():
                copy = Copy.objects.create(
                    school_id=context.school_id,
                    title_id=title.id,
                    accession_no=accession_no.strip(),
                    state=CopyState.AVAILABLE,
                    version=1,
                )
                self.platform.record_audit(
                    AuditRecord(
                        audit_id=uuid.uuid4(),
                        school_id=context.school_id,
                        actor_id=context.actor_id,
                        action="library.copy_created",
                        resource_id=copy.id,
                        occurred_at=now,
                        request_id=context.request_id,
                        after={"accession_no": copy.accession_no},
                    )
                )
        except IntegrityError as exc:
            raise ValidationFailed("library.error.duplicate_accession") from exc
        return copy_to_wire(copy)

    def adjust_copy(
        self,
        context: RequestContext,
        copy_id: UUID,
        *,
        new_state: str,
        reason: str,
        expected_version: int,
    ) -> dict:
        """Lost/damaged/withdrawn adjustment with reason."""
        self.gate.require_action(context, "library.catalogue.manage")
        if not reason or not reason.strip():
            raise ValidationFailed("library.error.reason_required")
        if new_state not in {s.value for s in CopyState}:
            raise ValidationFailed("error.validation_failed")
        now = self.clock.now()
        with transaction.atomic():
            copy = (
                Copy.objects.select_for_update()
                .filter(id=copy_id, school_id=context.school_id)
                .first()
            )
            if copy is None:
                raise ObjectInaccessible("error.object_inaccessible")
            if copy.version != expected_version:
                raise VersionConflict("error.version_conflict")
            old_state = copy.state
            copy.state = new_state
            copy.version += 1
            copy.save(update_fields=["state", "version"])
            adjustment = CopyAdjustment.objects.create(
                school_id=context.school_id,
                copy_id=copy.id,
                reason=reason.strip(),
                old_state=old_state,
                new_state=new_state,
                actor_id=context.actor_id,
                adjusted_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="library.copy_adjusted",
                    resource_id=copy.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={"state": old_state, "version": expected_version},
                    after={"state": new_state, "version": copy.version},
                )
            )
        return adjustment_to_wire(adjustment)

    def availability(self, context: RequestContext, title_id: UUID) -> dict:
        """Return available and total (non-withdrawn) counts."""
        self.gate.require_catalogue_read(context)
        title = Title.objects.filter(id=title_id, school_id=context.school_id).first()
        if title is None:
            raise ObjectInaccessible("error.object_inaccessible")
        copies = Copy.objects.filter(school_id=context.school_id, title_id=title_id)
        total = copies.exclude(state=CopyState.WITHDRAWN).count()
        available = copies.filter(state=CopyState.AVAILABLE).count()
        return {"available": available, "total": total}
