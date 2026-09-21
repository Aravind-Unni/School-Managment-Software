"""Acceptance cases: pin, grants, purge blocks, decode, isolation, orphans."""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = [pytest.mark.module]


def make_png_bytes(*, width: int = 80, height: int = 100) -> bytes:
    """Small valid PNG for upload tests."""
    import io

    from PIL import Image

    image = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def make_animated_webp() -> bytes:
    """Two-frame WebP that must be rejected as animated."""
    import io

    from PIL import Image

    frames = [
        Image.new("RGB", (32, 32), color=(255, 0, 0)),
        Image.new("RGB", (32, 32), color=(0, 0, 255)),
    ]
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    return buf.getvalue()


def sha256_hex(body: bytes) -> str:
    """Hex digest helper."""
    import hashlib

    return hashlib.sha256(body).hexdigest()


def upload_and_process(client, body: bytes, *, mime: str = "image/png") -> dict:
    """HTTP begin → PUT → complete; returns complete JSON."""
    begin = client.post(
        "/api/v1/uploads",
        data=json.dumps(
            {
                "purpose": "answer_sheet",
                "client_name": "page.png",
                "declared_bytes": len(body),
                "mime": mime,
            }
        ),
        content_type="application/json",
    )
    assert begin.status_code == 201, begin.content
    session = begin.json()
    put = client.put(session["upload_url"], data=body, content_type=mime)
    assert put.status_code == 204, put.content
    complete = client.post(
        f"/api/v1/uploads/{session['id']}/complete",
        data=json.dumps({"source_sha256": sha256_hex(body)}),
        content_type="application/json",
    )
    assert complete.status_code == 201, complete.content
    return complete.json()


def test_pin_immutable(baseline, clock):
    """Confirmed pin is immutable; reprocess adds a new candidate only."""
    from contracts.identity import AuthLevel, RequestContext
    from modules.files.api import deps
    from modules.files.models import Candidate, EvidencePin, File

    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        request_id="pin-test",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=clock.now(),
    )
    port = deps.files_port()
    file_id = UUID(baseline["file_accepted"])
    row = File.objects.get(id=file_id)
    before_sha = row.sha256
    before_version = row.canonical_version
    binding = UUID(baseline["binding_s1"])
    ref = port.pin_evidence(ctx, file_id, before_version, binding)
    assert ref.sha256 == before_sha
    assert EvidencePin.objects.filter(binding_id=binding, sha256=before_sha).count() == 1
    candidates_before = Candidate.objects.filter(file_id=file_id).count()
    deps.lifecycle_service().reprocess(ctx, file_id, reason="check fidelity")
    pin = EvidencePin.objects.get(binding_id=binding)
    assert pin.sha256 == before_sha
    assert pin.version == before_version
    assert Candidate.objects.filter(file_id=file_id).count() >= candidates_before


def test_wrong_child_grant_denied(baseline, clock, as_persona):
    """Grant for S2 file under unrelated guardian context is inaccessible."""
    from contracts.errors import ObjectInaccessible
    from contracts.evidence import ResourceGrant
    from contracts.identity import AuthLevel, RequestContext
    from modules.files.api import deps
    from modules.files.models import File

    hold = File.objects.get(id=UUID(baseline["file_hold"]))
    assert hold.subject_person_id == fixtures.STUDENT_S2
    as_persona(fixtures.GUARDIAN_G2)
    now = clock.now()
    ctx = RequestContext(
        actor_id=fixtures.GUARDIAN_G2,
        school_id=fixtures.SCHOOL_A,
        request_id="wrong-child",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=now,
    )
    grant = ResourceGrant(
        grant_id=uuid4(),
        school_id=fixtures.SCHOOL_A,
        actor_id=fixtures.GUARDIAN_G2,
        action="files.read",
        resource_id=hold.id,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    with pytest.raises(ObjectInaccessible):
        deps.files_port().issue_read(ctx, grant)


def test_unreviewed_blocks_purge(baseline):
    """Candidate not confirmed cannot be purged."""
    from modules.files.api import deps
    from modules.files.models import File

    row = File.objects.get(id=UUID(baseline["file_candidate"]))
    assert row.review_confirmed is False
    job = deps.retention_service().attempt_purge(row.id)
    assert job["state"] == "blocked"
    assert job["block_reason"] in {
        "files.error.unconfirmed_candidate",
        "files.error.purge_blocked",
    }


def test_unverified_backup_blocks_purge(baseline):
    """Unverified backup blocks economical purge."""
    from modules.files.api import deps
    from modules.files.models import File
    from modules.files.services.backup import backup_verifier

    row = File.objects.get(id=UUID(baseline["file_accepted"]))
    backup_verifier().set_source(row.source_id, verified=False)
    job = deps.retention_service().attempt_purge(row.id)
    assert job["state"] == "blocked"
    assert job["block_reason"] == "files.error.purge_blocked"


def test_hold_blocks_purge(baseline):
    """Legal hold blocks purge."""
    from modules.files.api import deps
    from modules.files.models import File

    row = File.objects.get(id=UUID(baseline["file_hold"]))
    assert row.legal_hold is True
    job = deps.retention_service().attempt_purge(row.id)
    assert job["state"] == "blocked"
    assert job["block_reason"] == "files.error.purge_blocked"


def test_decode_reject_animated(client, baseline):
    """Animated image is rejected with decode_rejected."""
    from modules.files.models import File

    body = make_animated_webp()
    created = upload_and_process(client, body, mime="image/webp")
    row = File.objects.get(id=created["file_id"])
    assert row.state == "rejected"
    assert row.rejection_reason == "files.error.decode_rejected"
    assert HarnessOutboxEvent.objects.filter(event_type="files.rejected").exists()


def test_cross_school_404(client, baseline):
    """School B file id returns 404 object_inaccessible."""
    res = client.get(f"/api/v1/files/{baseline['file_foreign']}/status")
    assert res.status_code == 404
    assert res.json()["message_key"] == "error.object_inaccessible"


def test_orphan_cleanup(client, baseline, clock):
    """Expired open upload is abandoned and quarantine object removed."""
    from modules.files.api import deps
    from modules.files.models import UploadSession, UploadSessionState
    from modules.files.services.storage import memory_store

    begin = client.post(
        "/api/v1/uploads",
        data=json.dumps(
            {
                "purpose": "answer_sheet",
                "client_name": "orphan.png",
                "declared_bytes": 100,
                "mime": "image/png",
            }
        ),
        content_type="application/json",
    )
    assert begin.status_code == 201
    session_id = UUID(begin.json()["id"])
    row = UploadSession.objects.get(id=session_id)
    memory_store().put(row.quarantine_key, b"pending")
    clock.set(clock.now() + timedelta(hours=1))
    count = deps.retention_service().cleanup_orphans()
    assert count >= 1
    row.refresh_from_db()
    assert row.state == UploadSessionState.ABANDONED
    assert not memory_store().exists(row.quarantine_key)


def test_two_school_isolation(baseline):
    """School A queries never see School B file rows."""
    from modules.files.models import File

    assert (
        File.objects.filter(
            school_id=fixtures.SCHOOL_A, id=UUID(baseline["file_foreign"])
        ).count()
        == 0
    )
    assert (
        File.objects.filter(
            school_id=fixtures.SCHOOL_B, id=UUID(baseline["file_foreign"])
        ).count()
        == 1
    )


def test_stale_version_retention_hold(client, baseline):
    """Wrong expected_version on retention-hold returns 409."""
    res = client.post(
        f"/api/v1/files/{baseline['file_accepted']}/retention-hold",
        data=json.dumps({"legal_hold": True, "expected_version": 999, "reason": "stale"}),
        content_type="application/json",
    )
    assert res.status_code == 409
    assert res.json()["message_key"] == "error.version_conflict"


def test_rollback_confirm_keeps_outbox_empty(baseline, clock):
    """Failed confirm does not leave orphan accepted events (transactional)."""
    from django.db import transaction

    from contracts.errors import VersionConflict
    from contracts.identity import AuthLevel, RequestContext
    from modules.files.api import deps

    before = HarnessOutboxEvent.objects.filter(event_type="files.accepted").count()
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        request_id="rollback",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=clock.now(),
    )
    with pytest.raises(VersionConflict):
        with transaction.atomic():
            deps.lifecycle_service().confirm_quality(
                ctx, UUID(baseline["file_candidate"]), candidate_version=999
            )
    assert HarnessOutboxEvent.objects.filter(event_type="files.accepted").count() == before


def test_wrong_grant_actor_denied(baseline, clock):
    """Unrelated actor cannot issue_read even with a crafted grant."""
    from contracts.errors import ObjectInaccessible
    from contracts.evidence import ResourceGrant
    from contracts.identity import AuthLevel, RequestContext
    from modules.files.api import deps

    now = clock.now()
    actor = UUID(baseline["unrelated_actor_id"])
    ctx = RequestContext(
        actor_id=actor,
        school_id=fixtures.SCHOOL_A,
        request_id="unrelated",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=now,
    )
    grant = ResourceGrant(
        grant_id=uuid4(),
        school_id=fixtures.SCHOOL_A,
        actor_id=actor,
        action="files.read",
        resource_id=UUID(baseline["file_accepted"]),
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    with pytest.raises(ObjectInaccessible):
        deps.files_port().issue_read(ctx, grant)


def test_quality_confirm_happy_path(client, baseline):
    """Teacher confirms candidate → accepted + files.accepted event."""
    from modules.files.models import Candidate

    file_id = baseline["file_candidate"]
    status = client.get(f"/api/v1/files/{file_id}/status")
    assert status.status_code == 200
    assert status.json()["state"] == "candidate_ready"
    cand = Candidate.objects.filter(file_id=file_id).order_by("-version").first()
    res = client.post(
        f"/api/v1/files/{file_id}/quality-confirmation",
        data=json.dumps({"candidate_version": cand.version, "readability_confirmed": True}),
        content_type="application/json",
    )
    assert res.status_code == 200, res.content
    body = res.json()
    assert body["state"] == "accepted"
    assert body["review_confirmed"] is True
    assert HarnessOutboxEvent.objects.filter(
        event_type="files.accepted", aggregate_id=UUID(file_id)
    ).exists()


def test_purge_succeeds_when_economical_ready(baseline, clock):
    """Confirm + verified backup + grace + no hold allows source purge."""
    from modules.files.api import deps
    from modules.files.models import Derivative, File, SourceObject
    from modules.files.services.backup import backup_verifier
    from modules.files.services.storage import memory_store

    row = File.objects.get(id=UUID(baseline["file_accepted"]))
    backup_verifier().set_source(row.source_id, verified=True)
    source = SourceObject.objects.get(id=row.source_id)
    canonical = Derivative.objects.filter(file_id=row.id, kind="canonical").first()
    job = deps.retention_service().attempt_purge(row.id)
    assert job["state"] == "completed", job
    source.refresh_from_db()
    assert source.purged_at is not None
    if canonical is not None:
        assert memory_store().exists(canonical.storage_key)


def test_upload_round_trip(client, baseline):
    """Fresh PNG upload reaches candidate_ready."""
    from modules.files.models import File

    body = make_png_bytes()
    created = upload_and_process(client, body)
    row = File.objects.get(id=created["file_id"])
    assert row.state == "candidate_ready"
    assert row.profile_version is not None
    assert HarnessOutboxEvent.objects.filter(
        event_type="files.candidate_ready", aggregate_id=row.id
    ).exists()
