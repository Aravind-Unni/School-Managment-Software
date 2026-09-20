"""In-process AlumniPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.alumni import AlumniProfileView, ContactPreferenceView, CreateCandidateResult
from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from ..models import ContactPreference
from .authority import AuthorityGate
from .candidates import CandidateService
from .profiles import ProfileService


@dataclass(frozen=True, slots=True)
class AlumniService:
    """Concrete AlumniPort for in-process consumers."""

    gate: AuthorityGate
    candidates: CandidateService
    profiles: ProfileService
    clock: object

    def get_profile(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> AlumniProfileView:
        """Return approved profile contact view for student_id in actor school.

        Raises ObjectInaccessible when absent, other-school, or denied.
        Does not return editable grade or transcript fields.
        """
        self.gate.require_action(context, "alumni.read")
        profile = self.profiles.get_profile_row(context, student_id)
        prefs = list(
            ContactPreference.objects.filter(profile_id=profile.id).order_by(
                "purpose", "channel", "id"
            )
        )
        return AlumniProfileView(
            id=profile.id,
            student_id=profile.student_id,
            leaving_year=profile.leaving_year,
            outcome=profile.outcome,
            approved_contact_fields={
                "email": profile.email,
                "phone": profile.phone,
                "postal_address": profile.postal_address,
            },
            preferences=[
                ContactPreferenceView(
                    person_id=row.person_id,
                    purpose=row.purpose,
                    channel=row.channel,
                    allowed=row.allowed,
                    updated_at=row.updated_at.isoformat().replace("+00:00", "Z"),
                )
                for row in prefs
            ],
        )

    def create_candidate(
        self,
        context: RequestContext,
        student_id: UUID,
        leaving_event_id: UUID,
        outcome: str,
    ) -> CreateCandidateResult:
        """Idempotent candidate for (student_id, leaving_event_id).

        Duplicate leaving_event_id returns the existing candidate id/state.
        Does not auto-create a public directory profile.
        """
        # Port callers are trusted module consumers; school isolation still applies.
        if context.school_id is None:
            raise ObjectInaccessible("error.object_inaccessible")
        row = self.candidates.create_candidate(context, student_id, leaving_event_id, outcome)
        return CreateCandidateResult(id=row.id, state=row.state)
