"""Baseline seed for M10: policy, graduate+transfer pending candidates."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import (
    AlumniCandidate,
    AlumniPolicy,
    AlumniProfile,
    ContactAmendment,
    ContactPreference,
)

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)
SCENARIO_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "contracts"
    / "M10"
    / "fixtures"
    / "scenario.json"
)


def _load_scenario() -> dict:
    """Load the frozen M10 scenario fixture."""
    return json.loads(SCENARIO_PATH.read_text())


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: policy + two pending candidates.

    Does not invent school policy: transfer_include_as_alumni stays null.
    """
    school = school_id or fixtures.SCHOOL_A
    scenario = _load_scenario()
    policy_fx = scenario["policy_fixture"]
    school_a = scenario["school_a"]

    ContactAmendment.objects.filter(school_id=school).delete()
    ContactPreference.objects.filter(school_id=school).delete()
    AlumniProfile.objects.filter(school_id=school).delete()
    AlumniCandidate.objects.filter(school_id=school).delete()
    AlumniPolicy.objects.filter(school_id=school).delete()

    AlumniPolicy.objects.create(
        school_id=school,
        transfer_include_as_alumni=policy_fx["transfer_include_as_alumni"],
        alumni_login_enabled=policy_fx["alumni_login_enabled"],
        exportable_fields=list(policy_fx["exportable_fields"]),
        granted_contact_purposes=list(policy_fx["granted_contact_purposes"]),
    )

    ctx = RequestContext(
        actor_id=UUID(school_a["reviewer_actor_id"]),
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    service = deps.candidate_service()
    graduate = school_a["graduate"]
    transfer = school_a["transfer"]
    grad_row = service.create_candidate(
        ctx,
        UUID(graduate["student_id"]),
        UUID(graduate["leaving_event_id"]),
        graduate["outcome"],
        last_standard=graduate["last_standard"],
        leaving_year=graduate["leaving_year"],
    )
    xfer_row = service.create_candidate(
        ctx,
        UUID(transfer["student_id"]),
        UUID(transfer["leaving_event_id"]),
        transfer["outcome"],
        last_standard=transfer["last_standard"],
        leaving_year=transfer["leaving_year"],
    )
    return {
        "school_id": str(school),
        "graduate_candidate_id": str(grad_row.id),
        "transfer_candidate_id": str(xfer_row.id),
        "graduate_student_id": graduate["student_id"],
        "transfer_student_id": transfer["student_id"],
        "graduate_leaving_event_id": graduate["leaving_event_id"],
        "duplicate_leaving_event_id": school_a["duplicate_leaving_event_id"],
        "reviewer_actor_id": school_a["reviewer_actor_id"],
        "manager_actor_id": school_a["manager_actor_id"],
        "unrelated_actor_id": school_a["unrelated_actor_id"],
        "exportable_fields": list(policy_fx["exportable_fields"]),
    }


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
