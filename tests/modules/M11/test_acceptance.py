"""Acceptance cases: notices, dedupe, callbacks, revoke, Malayalam, isolation."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = [pytest.mark.module]


def test_publish_en_and_ml_notices(client, baseline):
    """English and Malayalam drafts publish with audience snapshots."""
    for notice_id in (baseline["notice_en_id"], baseline["notice_ml_id"]):
        res = client.post(
            f"/api/v1/notices/{notice_id}/publish",
            data=json.dumps({"expected_version": 1}),
            content_type="application/json",
        )
        assert res.status_code == 200, res.content
        body = res.json()
        assert body["notice"]["state"] == "published"
        assert body["audience_snapshot"]["recipient_ids"]
    assert (
        HarnessOutboxEvent.objects.filter(
            event_type="communications.notice_published"
        ).count()
        == 2
    )


def test_in_app_notice_survives_sms_outage(client, baseline):
    """Published notice remains readable while SMS provider is down."""
    from modules.communications.services.provider import provider

    provider().set_outage()
    pub = client.post(
        f"/api/v1/notices/{baseline['notice_en_id']}/publish",
        data=json.dumps({"expected_version": 1}),
        content_type="application/json",
    )
    assert pub.status_code == 200
    from modules.communications.models import Notice

    row = Notice.objects.get(id=baseline["notice_en_id"])
    assert row.state == "published"
    assert row.title == "Sports day"


def test_duplicate_dedupe_one_provider_request(client, baseline, as_persona):
    """Identical dedupe_key + payload yields one Delivery and one provider send."""
    from modules.communications.services.provider import provider

    as_persona(UUID(baseline["sender_actor_id"]))
    sms = provider()
    sms.mode = "accepted"
    sms.sends.clear()
    payload = {
        "template_key": baseline["template_key"],
        "recipient_ref": baseline["guardian_contact_ref"],
        "locale": "en",
        "variables": {"name": "G1", "student": "S1"},
        "channel": "sms",
        "dedupe_key": baseline["dedupe_key"],
    }
    first = client.post(
        "/api/v1/messages", data=json.dumps(payload), content_type="application/json"
    )
    second = client.post(
        "/api/v1/messages", data=json.dumps(payload), content_type="application/json"
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(sms.sends) == 1


def test_dedupe_payload_mismatch_conflict(client, baseline, as_persona):
    """Same dedupe_key with different payload returns 409."""
    as_persona(UUID(baseline["sender_actor_id"]))
    base = {
        "template_key": baseline["template_key"],
        "recipient_ref": baseline["guardian_contact_ref"],
        "locale": "en",
        "channel": "sms",
        "dedupe_key": baseline["dedupe_key"] + ":mismatch",
    }
    first = client.post(
        "/api/v1/messages",
        data=json.dumps({**base, "variables": {"name": "A", "student": "S1"}}),
        content_type="application/json",
    )
    second = client.post(
        "/api/v1/messages",
        data=json.dumps({**base, "variables": {"name": "B", "student": "S1"}}),
        content_type="application/json",
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["message_key"] == "communications.error.dedupe_payload_mismatch"


def test_timeout_reconcile_avoids_duplicate_send(client, baseline, as_persona):
    """After timeout, lookup recovers accepted without a second provider send."""
    from modules.communications.api import deps
    from modules.communications.services.provider import provider

    as_persona(UUID(baseline["sender_actor_id"]))
    sms = provider()
    sms.mode = "timeout"
    sms.sends.clear()
    sms.lookups.clear()
    payload = {
        "template_key": baseline["template_key"],
        "recipient_ref": baseline["guardian_contact_ref"],
        "locale": "en",
        "variables": {"name": "G1", "student": "S1"},
        "channel": "sms",
        "dedupe_key": baseline["dedupe_key"] + ":timeout",
    }
    res = client.post(
        "/api/v1/messages", data=json.dumps(payload), content_type="application/json"
    )
    assert res.status_code == 201
    delivery_id = res.json()["id"]
    assert res.json()["state"] == "unknown"
    assert len(sms.sends) == 1
    deps.delivery_service().reconcile(UUID(delivery_id))
    status = client.get(f"/api/v1/deliveries/{delivery_id}")
    assert status.status_code == 200
    assert status.json()["state"] == "accepted"
    assert len(sms.sends) == 1
    assert sms.lookups


def test_forged_callback_rejected(client, baseline, as_persona):
    """Forged signature does not change delivery state."""
    from modules.communications.models import Delivery
    from modules.communications.services.provider import provider

    as_persona(UUID(baseline["sender_actor_id"]))
    sms = provider()
    sms.mode = "accepted"
    payload = {
        "template_key": baseline["template_key"],
        "recipient_ref": baseline["guardian_contact_ref"],
        "locale": "en",
        "variables": {"name": "G1", "student": "S1"},
        "channel": "sms",
        "dedupe_key": baseline["dedupe_key"] + ":callback",
    }
    created = client.post(
        "/api/v1/messages", data=json.dumps(payload), content_type="application/json"
    )
    delivery = Delivery.objects.get(id=created.json()["id"])
    before = delivery.state
    body = json.dumps(
        {
            "provider_ref": delivery.provider_ref,
            "state": "delivered",
            "nonce": "forged-nonce-1",
        }
    ).encode("utf-8")
    forged = client.post(
        "/api/v1/sms/callback/fake",
        data=body,
        content_type="application/json",
        headers={"X-Sms-Signature": baseline["forged_callback_signature"]},
    )
    assert forged.status_code == 401
    delivery.refresh_from_db()
    assert delivery.state == before


def test_valid_callback_updates_state(client, baseline, as_persona):
    """Signed callback moves delivery to delivered."""
    from modules.communications.models import Delivery
    from modules.communications.services.provider import provider

    as_persona(UUID(baseline["sender_actor_id"]))
    sms = provider()
    sms.mode = "accepted"
    created = client.post(
        "/api/v1/messages",
        data=json.dumps(
            {
                "template_key": baseline["template_key"],
                "recipient_ref": baseline["guardian_contact_ref"],
                "locale": "en",
                "variables": {"name": "G1", "student": "S1"},
                "channel": "sms",
                "dedupe_key": baseline["dedupe_key"] + ":ok-callback",
            }
        ),
        content_type="application/json",
    )
    delivery = Delivery.objects.get(id=created.json()["id"])
    body = json.dumps(
        {
            "provider_ref": delivery.provider_ref,
            "state": "delivered",
            "nonce": "ok-nonce-1",
        }
    ).encode("utf-8")
    ok = client.post(
        "/api/v1/sms/callback/fake",
        data=body,
        content_type="application/json",
        headers={"X-Sms-Signature": sms.sign(body)},
    )
    assert ok.status_code == 202
    delivery.refresh_from_db()
    assert delivery.state == "delivered"


def test_guardian_unlink_blocks_pending(client, baseline, as_persona):
    """Revoked contact skips SMS for pending delivery."""
    from modules.communications.models import Attempt, VerifiedContact
    from modules.communications.services.provider import provider

    as_persona(UUID(baseline["sender_actor_id"]))
    sms = provider()
    sms.mode = "accepted"
    sms.sends.clear()
    res = client.post(
        "/api/v1/messages",
        data=json.dumps(
            {
                "template_key": baseline["template_key"],
                "recipient_ref": baseline["revoked_guardian_contact_ref"],
                "locale": "en",
                "variables": {"name": "G2", "student": "S3"},
                "channel": "sms",
                "dedupe_key": baseline["dedupe_key"] + ":revoked",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.json()["state"] == "failed"
    assert len(sms.sends) == 0
    assert Attempt.objects.filter(outcome="skipped_revoked").exists()
    assert VerifiedContact.objects.get(
        recipient_ref=baseline["revoked_guardian_contact_ref"]
    ).revoked


def test_malayalam_template_preserved(client, baseline, as_persona):
    """Malayalam Unicode survives render into delivery body."""
    from modules.communications.models import Delivery

    as_persona(UUID(baseline["sender_actor_id"]))
    res = client.post(
        "/api/v1/messages",
        data=json.dumps(
            {
                "template_key": baseline["template_key"],
                "recipient_ref": baseline["guardian_contact_ref"],
                "locale": "ml",
                "variables": {"name": "രക്ഷിതാവ്", "student": "വിദ്യാർത്ഥി"},
                "channel": "sms",
                "dedupe_key": baseline["dedupe_key"] + ":ml",
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 201
    row = Delivery.objects.get(id=res.json()["id"])
    assert "നമസ്കാരം" in row.rendered_body
    assert "രക്ഷിതാവ്" in row.rendered_body


def test_unrelated_actor_denied(client, baseline, as_persona):
    """Scenario unrelated actor cannot create notices."""
    as_persona(UUID(baseline["unrelated_actor_id"]))
    res = client.post(
        "/api/v1/notices",
        data=json.dumps(
            {
                "title": "x",
                "body": "y",
                "locale": "en",
                "audience": {"kind": "person_ids", "person_ids": [baseline["student_id"]]},
            }
        ),
        content_type="application/json",
    )
    assert res.status_code == 403


def test_stale_publish_version_conflict(client, baseline):
    """Stale expected_version on publish returns 409."""
    res = client.post(
        f"/api/v1/notices/{baseline['notice_en_id']}/publish",
        data=json.dumps({"expected_version": 99}),
        content_type="application/json",
    )
    assert res.status_code == 409


def test_two_school_isolation(client, baseline, as_persona):
    """Other-school school_id on persona cannot see School A notice."""
    as_persona(fixtures.PRINCIPAL_P1, school_id=fixtures.SCHOOL_B)
    from modules.communications.models import Notice

    # Cross-school: object exists but API returns 404 via school filter.
    res = client.post(
        f"/api/v1/notices/{baseline['notice_en_id']}/publish",
        data=json.dumps({"expected_version": 1}),
        content_type="application/json",
    )
    assert res.status_code == 404
    assert Notice.objects.filter(id=baseline["notice_en_id"]).exists()


def test_publish_rollback_drops_outbox(client, baseline):
    """Forced failure after write rolls back notice publish and outbox."""
    from django.db import transaction

    from contracts.errors import ValidationFailed
    from modules.communications.api import deps
    from modules.communications.models import Notice
    from shared.harness.models import HarnessAuditRecord

    before_events = HarnessOutboxEvent.objects.count()
    before_audits = HarnessAuditRecord.objects.filter(
        action="communications.notice_published"
    ).count()
    service = deps.notice_service()
    from contracts.identity import AuthLevel, RequestContext
    from datetime import UTC, datetime

    ctx = RequestContext(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        request_id="rollback-test",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=datetime(2026, 9, 21, 4, 30, tzinfo=UTC),
    )
    try:
        with transaction.atomic():
            service.publish(
                ctx, UUID(baseline["notice_ml_id"]), expected_version=1
            )
            raise ValidationFailed("error.validation_failed")
    except ValidationFailed:
        pass
    row = Notice.objects.get(id=baseline["notice_ml_id"])
    assert row.state == "draft"
    assert HarnessOutboxEvent.objects.count() == before_events
    assert (
        HarnessAuditRecord.objects.filter(
            action="communications.notice_published"
        ).count()
        == before_audits
    )
