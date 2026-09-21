"""Candidate creation, listing and approve/exclude."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor
from contracts.values import school_date

from ..models import (
    AlumniCandidate,
    AlumniProfile,
    CandidateState,
    ContactPreference,
    LeavingOutcome,
)
from .authority import AuthorityGate
from .wire import candidate_to_wire, profile_to_wire


@dataclass(frozen=True, slots=True)
class CandidateService:
    """Idempotent leaving candidates and reviewer approve/exclude."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create_candidate(
        self,
        context: RequestContext,
        student_id: UUID,
        leaving_event_id: UUID,
        outcome: str,
        *,
        last_standard: int | None = None,
        leaving_year: int | None = None,
    ) -> AlumniCandidate:
        """Create or return the candidate for (student, leaving_event).

        Idempotent on leaving_event_id within the school. Snapshot uses Registry
        display/admission; last_standard/leaving_year from caller or Registry's latest enrolment
        / clock year. Does not auto-create a directory profile.
        """
        if outcome not in {LeavingOutcome.GRADUATE, LeavingOutcome.TRANSFER}:
            raise ValidationFailed("error.validation_failed")
        student = self.gate.ensure_student_in_school(context, student_id)
        existing = AlumniCandidate.objects.filter(
            school_id=context.school_id,
            leaving_event_id=leaving_event_id,
        ).first()
        if existing is not None:
            return existing

        standard = last_standard
        if standard is None:
            standard = self.gate.registry.latest_standard(context, student_id)
        if standard is None:
            raise ValidationFailed("error.validation_failed")
        year = leaving_year if leaving_year is not None else school_date(self.clock.now()).year

        try:
            with transaction.atomic():
                candidate = AlumniCandidate.objects.create(
                    school_id=context.school_id,
                    student_id=student_id,
                    leaving_event_id=leaving_event_id,
                    outcome=outcome,
                    state=CandidateState.PENDING,
                    version=1,
                    admission_no=student.admission_no,
                    display_name=student.display_name,
                    last_standard=standard,
                    leaving_year=year,
                )
                self.platform.record_audit(
                    AuditRecord(
                        audit_id=uuid.uuid4(),
                        school_id=context.school_id,
                        actor_id=context.actor_id,
                        action="alumni.candidate_created",
                        resource_id=candidate.id,
                        occurred_at=self.clock.now(),
                        request_id=context.request_id,
                        after={
                            "leaving_event_id": str(leaving_event_id),
                            "outcome": outcome,
                            "state": CandidateState.PENDING,
                        },
                    )
                )
        except IntegrityError:
            return AlumniCandidate.objects.get(
                school_id=context.school_id,
                leaving_event_id=leaving_event_id,
            )
        return candidate

    def list_candidates(
        self,
        context: RequestContext,
        *,
        state: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """List candidates for the actor school. Default state is pending."""
        self.gate.require_action(context, "alumni.review")
        filter_state = state or CandidateState.PENDING
        if filter_state not in {
            CandidateState.PENDING,
            CandidateState.APPROVED,
            CandidateState.EXCLUDED,
        }:
            raise ValidationFailed("error.validation_failed")
        size = clamp_page_size(page_size)
        queryset = AlumniCandidate.objects.filter(
            school_id=context.school_id, state=filter_state
        ).order_by("display_name", "id")
        if cursor:
            try:
                position = decode_cursor(cursor)
                after_name = str(position["name"])
                after_id = str(position["id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValidationFailed("error.validation_failed") from exc
            from django.db.models import Q

            queryset = queryset.filter(
                Q(display_name__gt=after_name) | Q(display_name=after_name, id__gt=after_id)
            )
        rows = list(queryset[: size + 1])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor({"name": last.display_name, "id": str(last.id)})
            rows = rows[:size]
        page = Page(items=tuple(candidate_to_wire(r) for r in rows), next_cursor=next_cursor)
        return page.to_wire()

    def approve(
        self,
        context: RequestContext,
        candidate_id: UUID,
        *,
        include: bool,
        reason: str,
        contact_policy: dict | None = None,
    ) -> dict:
        """Include as profile or exclude. Transfer with null policy stays reviewable.

        Explicit include=true creates a profile even for transfer. Does not
        auto-approve via transfer_include_as_alumni when that fixture is null.
        """
        self.gate.require_action(context, "alumni.review")
        if not reason or not reason.strip():
            raise ValidationFailed("alumni.error.reason_required")
        candidate = AlumniCandidate.objects.filter(
            id=candidate_id, school_id=context.school_id
        ).first()
        if candidate is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if candidate.state != CandidateState.PENDING:
            raise StateConflict("alumni.error.candidate_not_pending")

        now = self.clock.now()
        with transaction.atomic():
            if not include:
                candidate.state = CandidateState.EXCLUDED
                candidate.version += 1
                candidate.save(update_fields=["state", "version"])
                self.platform.record_audit(
                    AuditRecord(
                        audit_id=uuid.uuid4(),
                        school_id=context.school_id,
                        actor_id=context.actor_id,
                        action="alumni.candidate_excluded",
                        resource_id=candidate.id,
                        occurred_at=now,
                        request_id=context.request_id,
                        after={"reason": reason.strip(), "state": CandidateState.EXCLUDED},
                    )
                )
                return candidate_to_wire(candidate)

            fields = (contact_policy or {}).get("fields") or {}
            pref_specs = (contact_policy or {}).get("preferences") or []
            profile = AlumniProfile.objects.create(
                school_id=context.school_id,
                student_id=candidate.student_id,
                candidate_id=candidate.id,
                last_standard=candidate.last_standard,
                leaving_year=candidate.leaving_year,
                outcome=candidate.outcome,
                snapshot_version=1,
                email=fields.get("email"),
                phone=fields.get("phone"),
                postal_address=fields.get("postal_address"),
                version=1,
                display_name=candidate.display_name,
                admission_no=candidate.admission_no,
            )
            for spec in pref_specs:
                ContactPreference.objects.create(
                    school_id=context.school_id,
                    profile_id=profile.id,
                    person_id=candidate.student_id,
                    purpose=spec["purpose"],
                    channel=spec["channel"],
                    allowed=bool(spec["allowed"]),
                    updated_at=now,
                )
            candidate.state = CandidateState.APPROVED
            candidate.version += 1
            candidate.save(update_fields=["state", "version"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="alumni.profile_approved",
                    resource_id=profile.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"reason": reason.strip(), "student_id": str(candidate.student_id)},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="alumni.profile_approved",
                    occurred_at=now,
                    aggregate_id=profile.id,
                    aggregate_version=profile.version,
                    payload={
                        "profile_id": str(profile.id),
                        "student_id": str(candidate.student_id),
                    },
                    correlation_id=context.request_id,
                )
            )
        return profile_to_wire(profile)
