"""Baseline seed for M11: policy, templates, contacts, en+ml notices."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import (
    Attempt,
    AudienceSnapshot,
    CallbackNonce,
    CommunicationsPolicy,
    Delivery,
    MessageTemplate,
    Notice,
    ProviderConfig,
    VerifiedContact,
)
from .services.provider import provider

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)
SCENARIO_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "contracts"
    / "M11"
    / "fixtures"
    / "scenario.json"
)


def _load_scenario() -> dict:
    """Load the frozen M11 scenario fixture."""
    return json.loads(SCENARIO_PATH.read_text())


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: en+ml notices, templates, contacts, provider.

    Does not invent school policy beyond the fixture.
    """
    school = school_id or fixtures.SCHOOL_A
    scenario = _load_scenario()
    policy_fx = scenario["policy_fixture"]
    school_a = scenario["school_a"]

    Attempt.objects.filter(school_id=school).delete()
    Delivery.objects.filter(school_id=school).delete()
    CallbackNonce.objects.filter(school_id=school).delete()
    AudienceSnapshot.objects.filter(school_id=school).delete()
    Notice.objects.filter(school_id=school).delete()
    MessageTemplate.objects.filter(school_id=school).delete()
    VerifiedContact.objects.filter(school_id=school).delete()
    ProviderConfig.objects.filter(school_id=school).delete()
    CommunicationsPolicy.objects.filter(school_id=school).delete()

    CommunicationsPolicy.objects.create(
        school_id=school,
        sms_configure_requires_2fa=policy_fx["sms_configure_requires_2fa"],
        live_provider=policy_fx["live_provider"],
        channels_enabled=list(policy_fx["channels_enabled"]),
    )
    ProviderConfig.objects.create(
        school_id=school,
        secret_ref="secrets/fake-sms",
        sender_id="SCHFAKE",
        enabled=True,
        version=1,
    )
    for tmpl in (school_a["template_en"], school_a["template_ml"]):
        MessageTemplate.objects.create(
            school_id=school,
            key=tmpl["key"],
            locale=tmpl["locale"],
            version=1,
            body=tmpl["body"],
            provider_template_id=None,
        )
    VerifiedContact.objects.create(
        school_id=school,
        recipient_ref=UUID(school_a["guardian_contact_ref"]),
        person_id=UUID(school_a["guardian_contact_ref"]),
        channel="sms",
        verified=True,
        revoked=False,
        purpose_allowed=True,
    )
    VerifiedContact.objects.create(
        school_id=school,
        recipient_ref=UUID(school_a["revoked_guardian_contact_ref"]),
        person_id=UUID(school_a["revoked_guardian_contact_ref"]),
        channel="sms",
        verified=True,
        revoked=True,
        purpose_allowed=False,
    )

    sms = provider()
    sms.mode = "accepted"
    sms.sends.clear()
    sms.lookups.clear()
    sms._states.clear()
    sms._idempotency.clear()

    ctx = RequestContext(
        actor_id=UUID(school_a["publisher_actor_id"]),
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    notices = deps.notice_service()
    en = notices.create(
        ctx,
        title=school_a["notice_en"]["title"],
        body=school_a["notice_en"]["body"],
        locale="en",
        audience={"kind": "section", "section_id": school_a["section_id"]},
    )
    ml = notices.create(
        ctx,
        title=school_a["notice_ml"]["title"],
        body=school_a["notice_ml"]["body"],
        locale="ml",
        audience={
            "kind": "person_ids",
            "person_ids": [school_a["student_id"]],
        },
    )
    return {
        "school_id": str(school),
        "notice_en_id": en["id"],
        "notice_ml_id": ml["id"],
        "publisher_actor_id": school_a["publisher_actor_id"],
        "sender_actor_id": school_a["sender_actor_id"],
        "unrelated_actor_id": school_a["unrelated_actor_id"],
        "guardian_contact_ref": school_a["guardian_contact_ref"],
        "revoked_guardian_contact_ref": school_a["revoked_guardian_contact_ref"],
        "dedupe_key": school_a["dedupe_key"],
        "section_id": school_a["section_id"],
        "student_id": school_a["student_id"],
        "template_key": school_a["template_en"]["key"],
        "forged_callback_signature": school_a["forged_callback_signature"],
    }


SCENARIOS = {
    "baseline": seed_baseline,
}
