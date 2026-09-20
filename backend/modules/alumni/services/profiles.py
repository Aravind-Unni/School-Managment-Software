"""Alumni directory listing, contact patch and selection helper."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from contracts.errors import ObjectInaccessible, ValidationFailed, VersionConflict
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor

from ..models import AlumniProfile, ContactAmendment, ContactPreference
from .authority import AuthorityGate
from .wire import profile_to_wire


def is_selectable_for_contact(
    profile_id: UUID,
    *,
    purpose: str,
    channel: str,
) -> bool:
    """Return True when the profile opted in for purpose/channel.

    Withdrawal (allowed=false) or a missing preference excludes selection.
    Does not authorise the caller — that is the caller's Access check.
    """
    row = ContactPreference.objects.filter(
        profile_id=profile_id, purpose=purpose, channel=channel
    ).first()
    return row is not None and row.allowed is True


@dataclass(frozen=True, slots=True)
class ProfileService:
    """Directory search and contact preference updates."""

    gate: AuthorityGate
    platform: object
    clock: object

    def list_alumni(
        self,
        context: RequestContext,
        *,
        year: int | None = None,
        outcome: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """Scoped paginated alumni directory."""
        self.gate.require_action(context, "alumni.read")
        size = clamp_page_size(page_size)
        queryset = AlumniProfile.objects.filter(school_id=context.school_id).order_by(
            "display_name", "id"
        )
        if year is not None:
            queryset = queryset.filter(leaving_year=year)
        if outcome is not None:
            queryset = queryset.filter(outcome=outcome)
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_name = str(position["name"])
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            queryset = queryset.filter(
                Q(display_name__gt=after_name) | Q(display_name=after_name, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor({"name": last.display_name, "id": str(last.id)})
            rows = rows[:size]
        page = Page(items=tuple(profile_to_wire(r) for r in rows), next_cursor=next_cursor)
        return page.to_wire()

    def patch_contact(
        self,
        context: RequestContext,
        profile_id: UUID,
        *,
        expected_version: int,
        reason: str,
        fields: dict | None = None,
        preferences: list[dict] | None = None,
        use_contact_self: bool = False,
    ) -> dict:
        """Update contact fields and/or preferences with optimistic concurrency."""
        if use_contact_self:
            self.gate.require_contact_self_enabled(context)
        else:
            self.gate.require_action(context, "alumni.manage")
        if not reason or not reason.strip():
            raise ValidationFailed("alumni.error.reason_required")
        profile = AlumniProfile.objects.filter(
            id=profile_id, school_id=context.school_id
        ).first()
        if profile is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if profile.version != expected_version:
            raise VersionConflict(
                expected_version=expected_version, actual_version=profile.version
            )

        now = self.clock.now()
        with transaction.atomic():
            old_fields = {
                "email": profile.email,
                "phone": profile.phone,
                "postal_address": profile.postal_address,
            }
            if fields is not None:
                if "email" in fields:
                    profile.email = fields["email"]
                if "phone" in fields:
                    profile.phone = fields["phone"]
                if "postal_address" in fields:
                    profile.postal_address = fields["postal_address"]
                ContactAmendment.objects.create(
                    school_id=context.school_id,
                    profile_id=profile.id,
                    old_json=old_fields,
                    new_json={
                        "email": profile.email,
                        "phone": profile.phone,
                        "postal_address": profile.postal_address,
                    },
                    reason=reason.strip(),
                    created_at=now,
                    actor_id=context.actor_id,
                )
            if preferences is not None:
                for spec in preferences:
                    purpose = spec["purpose"]
                    channel = spec["channel"]
                    allowed = bool(spec["allowed"])
                    pref, _created = ContactPreference.objects.update_or_create(
                        profile_id=profile.id,
                        purpose=purpose,
                        channel=channel,
                        defaults={
                            "school_id": context.school_id,
                            "person_id": profile.student_id,
                            "allowed": allowed,
                            "updated_at": now,
                        },
                    )
                    self.platform.append_event(
                        EventEnvelope(
                            event_id=uuid.uuid4(),
                            school_id=context.school_id,
                            event_type="alumni.contact_preference_changed",
                            occurred_at=now,
                            aggregate_id=profile.id,
                            aggregate_version=profile.version + 1,
                            payload={
                                "profile_id": str(profile.id),
                                "purpose": purpose,
                                "channel": channel,
                                "allowed": allowed,
                            },
                            correlation_id=context.request_id,
                        )
                    )
                    _ = pref
            profile.version += 1
            profile.save()
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="alumni.contact_patched",
                    resource_id=profile.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before=old_fields,
                    after={
                        "email": profile.email,
                        "phone": profile.phone,
                        "postal_address": profile.postal_address,
                        "reason": reason.strip(),
                    },
                )
            )
        return profile_to_wire(profile)

    def get_profile_row(self, context: RequestContext, student_id: UUID) -> AlumniProfile:
        """Load approved profile for student in actor school or raise 404."""
        profile = AlumniProfile.objects.filter(
            school_id=context.school_id, student_id=student_id
        ).first()
        if profile is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return profile
