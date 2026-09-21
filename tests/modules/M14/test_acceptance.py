"""M14 standalone acceptance: rollback, dedupe, isolation, redaction, restore."""

from __future__ import annotations

from uuid import uuid4

import pytest
from django.db import transaction

from contracts.events import AuditRecord, EventEnvelope
from modules.platform import fixture_ids as ids
from modules.platform.models import ConsumerReceipt, OutboxEvent
from modules.platform.services.outbox import (
    SAMPLE_SIDE_EFFECTS,
    dispatch_pending,
    reset_sample_side_effects,
    sample_consumer_handle,
)
from shared.ports import runtime

pytestmark = [pytest.mark.module]


def test_health_live_is_public(client, baseline):
    """GET /health/live needs no persona."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_get_job_and_cross_school_404(client, baseline, as_persona):
    """Same-school job is visible; foreign school job is 404."""
    ok = client.get(f"/api/v1/jobs/{ids.JOB_FAILED}")
    assert ok.status_code == 200
    assert ok.json()["state"] == "failed"
    foreign = client.get(f"/api/v1/jobs/{ids.JOB_FOREIGN}")
    assert foreign.status_code == 404


def test_retry_failed_job_202(client, baseline):
    """Failed job retries to queued."""
    response = client.post(
        f"/api/v1/jobs/{ids.JOB_FAILED}/retry",
        data={"reason": "operator replay after interrupt"},
        content_type="application/json",
    )
    assert response.status_code == 202
    assert response.json()["state"] == "queued"


def test_retry_running_job_409(client, baseline):
    """Running job is not retryable."""
    response = client.post(
        f"/api/v1/jobs/{ids.JOB_RUNNING}/retry",
        data={"reason": "should fail"},
        content_type="application/json",
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "platform.error.job_not_retryable"


def test_audit_redacts_secrets(client, baseline):
    """GET /audit never returns raw secret values."""
    response = client.get("/api/v1/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    blob = str(body)
    assert "super-secret-value" not in blob
    assert "[REDACTED]" in blob


def test_restore_rehearsal_ops_only(client, baseline, as_persona):
    """School admin is denied; company ops verifies hashes and fee total."""
    as_persona(ids.SCHOOL_ADMIN_ACTOR)
    denied = client.post(
        "/api/v1/operations/restore-rehearsals",
        data={
            "backup_manifest_id": str(ids.BACKUP_MANIFEST_ID),
            "isolated_target_label": "restore-rehearsal-a",
        },
        content_type="application/json",
    )
    assert denied.status_code == 403
    assert denied.json()["message_key"] == "platform.error.ops_identity_required"

    as_persona(ids.COMPANY_OPS_ACTOR)
    ok = client.post(
        "/api/v1/operations/restore-rehearsals",
        data={
            "backup_manifest_id": str(ids.BACKUP_MANIFEST_ID),
            "isolated_target_label": "restore-rehearsal-a",
        },
        content_type="application/json",
    )
    assert ok.status_code == 202
    body = ok.json()
    assert body["state"] == "verified"
    assert body["object_hashes_matched"] is True
    assert body["fee_total_paise"] == ids.SAMPLE_FEE_TOTAL_PAISE


def test_production_target_forbidden(client, baseline, as_persona):
    """Isolated label must not name production."""
    as_persona(ids.COMPANY_OPS_ACTOR)
    response = client.post(
        "/api/v1/operations/restore-rehearsals",
        data={
            "backup_manifest_id": str(ids.BACKUP_MANIFEST_ID),
            "isolated_target_label": "production",
        },
        content_type="application/json",
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "platform.error.production_target_forbidden"


def test_rollback_leaves_no_dispatched_event(db, clock, baseline):
    """Rolled-back audit/outbox writes are invisible after the transaction."""
    platform = runtime.get_registry().resolve("platform")
    before_audit = len(platform.audit_rows(school_id=ids.SCHOOL_A))
    before_outbox = len(platform.outbox_rows(school_id=ids.SCHOOL_A))
    try:
        with transaction.atomic():
            platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=ids.SCHOOL_A,
                    actor_id=ids.OPERATOR_ACTOR,
                    action="platform.rollback_probe",
                    resource_id=uuid4(),
                    occurred_at=clock.now(),
                    request_id="rollback-1",
                    before={},
                    after={"x": 1},
                )
            )
            platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=ids.SCHOOL_A,
                    event_type="platform.job_state_changed",
                    occurred_at=clock.now(),
                    aggregate_id=uuid4(),
                    aggregate_version=1,
                    payload={
                        "job_id": str(uuid4()),
                        "kind": "platform.sample_producer",
                        "from_state": "queued",
                        "to_state": "running",
                    },
                    correlation_id="rollback-1",
                )
            )
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass
    assert len(platform.audit_rows(school_id=ids.SCHOOL_A)) == before_audit
    assert len(platform.outbox_rows(school_id=ids.SCHOOL_A)) == before_outbox
    dispatch_pending(clock=clock)
    # Nothing new to dispatch from the rolled-back write.


def test_duplicate_delivery_one_effect(db, clock, baseline):
    """Second delivery of the same event_id has no second side effect."""
    reset_sample_side_effects()
    event_id = uuid4()
    row = OutboxEvent.objects.create(
        event_id=event_id,
        school_id=ids.SCHOOL_A,
        event_type="platform.job_state_changed",
        occurred_at=clock.now(),
        aggregate_id=uuid4(),
        aggregate_version=1,
        payload={
            "job_id": str(uuid4()),
            "kind": "platform.sample_producer",
            "from_state": "failed",
            "to_state": "queued",
        },
        envelope_version=1,
        state="pending",
        attempts=0,
    )
    assert sample_consumer_handle(row, clock=clock) is True
    assert sample_consumer_handle(row, clock=clock) is False
    assert SAMPLE_SIDE_EFFECTS.count(f"effect-{event_id}") == 1
    assert ConsumerReceipt.objects.filter(event_id=event_id).count() == 1


def test_platform_module_does_not_import_other_business_modules():
    """M14 imports contracts and shared only; a domain import would be a breach."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3] / "backend" / "modules" / "platform"
    forbidden = (
        "modules.fees",
        "modules.files",
        "modules.exchange",
        "modules.attendance",
        "modules.registry",
    )
    for path in root.rglob("*.py"):
        text = path.read_text()
        for name in forbidden:
            assert f"import {name}" not in text
            assert f"from {name}" not in text
