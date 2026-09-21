"""Baseline seed for M12: policy, synthetic pages, candidate, accepted, hold."""

from __future__ import annotations

import hashlib
import io
import json
import pathlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures

from .api import deps
from .models import (
    Candidate,
    Derivative,
    EvidencePin,
    File,
    FilesPolicy,
    FileState,
    PurgeJob,
    QualityReview,
    SourceObject,
    UploadSession,
)
from .services.backup import backup_verifier
from .services.constants import PROFILE_DEFAULT
from .services.storage import memory_store

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)
SCENARIO_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "contracts"
    / "M12"
    / "fixtures"
    / "scenario.json"
)


def _load_scenario() -> dict:
    """Load the frozen M12 scenario fixture."""
    return json.loads(SCENARIO_PATH.read_text())


def _synthetic_png(*, width: int = 200, height: int = 280, mark: str = "A") -> bytes:
    """Generate a small synthetic PNG with a faint pattern and a red mark."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), color=(245, 245, 240))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, 8):
        draw.line([(0, y), (width, y)], fill=(230, 230, 225))
    draw.rectangle([20, 20, width - 20, height - 20], outline=(180, 180, 180))
    draw.text((30, 40), f"page {mark}", fill=(40, 40, 40))
    draw.ellipse(
        [width // 2 - 10, height // 2 - 10, width // 2 + 10, height // 2 + 10],
        fill=(200, 40, 40),
    )
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _upload_page(ctx: RequestContext, body: bytes) -> UUID:
    """Begin, PUT, complete one answer-sheet page; return file id."""
    life = deps.lifecycle_service()
    session = life.begin_upload(
        ctx,
        purpose="answer_sheet",
        client_name="seed.png",
        declared_bytes=len(body),
        mime="image/png",
    )
    token = session.upload_url.split("token=")[-1]
    life.put_quarantine_bytes(session.id, token, body)
    created = life.complete_upload(ctx, session.id, hashlib.sha256(body).hexdigest())
    return UUID(created["file_id"])


def _rekey_file(row: File, new_id: UUID, *, subject: UUID) -> File:
    """Move a file and related rows onto a contracted fixture UUID."""
    Candidate.objects.filter(file_id=row.id).update(file_id=new_id)
    Derivative.objects.filter(file_id=row.id).update(file_id=new_id)
    QualityReview.objects.filter(file_id=row.id).update(file_id=new_id)
    payload = {
        "school_id": row.school_id,
        "purpose": row.purpose,
        "state": row.state,
        "source_id": row.source_id,
        "subject_person_id": subject,
        "canonical_version": row.canonical_version,
        "sha256": row.sha256,
        "byte_size": row.byte_size,
        "width": row.width,
        "height": row.height,
        "profile_version": row.profile_version,
        "review_confirmed": row.review_confirmed,
        "rejection_reason": row.rejection_reason,
        "legal_hold": row.legal_hold,
        "version": row.version,
        "confirmed_at": row.confirmed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    row.delete()
    return File.objects.create(id=new_id, **payload)


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load contracted baseline: policy, 10+ pages, candidate, accepted, hold.

    Documents generation of 100 synthetic pages; seeds a workable subset of 12.
    """
    school = school_id or fixtures.SCHOOL_A
    scenario = _load_scenario()
    policy_fx = scenario["policy_fixture"]
    school_a = scenario["school_a"]
    school_b = scenario["school_b"]

    EvidencePin.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    QualityReview.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    Candidate.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    Derivative.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    PurgeJob.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    File.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    SourceObject.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    UploadSession.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    FilesPolicy.objects.filter(school_id__in=[school, UUID(school_b["school_id"])]).delete()
    memory_store()._objects.clear()
    backup_verifier().clear()

    for sid in (school, UUID(school_b["school_id"])):
        FilesPolicy.objects.create(
            school_id=sid,
            retention_mode=policy_fx["retention_mode"],
            grace_days=policy_fx["grace_days"],
            max_bytes_per_page=policy_fx["max_bytes_per_page"],
            max_megapixels=policy_fx["max_megapixels"],
            max_batch_pages=policy_fx["max_batch_pages"],
            long_edge_px=policy_fx["long_edge_px"],
            webp_quality=policy_fx["webp_quality"],
            signed_read_seconds=policy_fx["signed_read_seconds"],
            retention_requires_2fa=policy_fx["retention_requires_2fa"],
            policy_version="economical_v1",
        )

    pages_generated_documented = 100
    pages_seeded = 12
    ctx = RequestContext(
        actor_id=UUID(school_a["uploader_actor_id"]),
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )
    seeded = [_upload_page(ctx, _synthetic_png(mark=str(i + 1))) for i in range(pages_seeded)]

    candidate_id = UUID(school_a["file_candidate"])
    accepted_id = UUID(school_a["file_accepted"])
    hold_id = UUID(school_a["file_hold"])
    s1 = UUID(school_a["student_s1"])
    s2 = UUID(school_a["student_s2"])

    candidate = _rekey_file(File.objects.get(id=seeded[0]), candidate_id, subject=s1)
    accepted = _rekey_file(File.objects.get(id=seeded[1]), accepted_id, subject=s1)
    hold = _rekey_file(File.objects.get(id=seeded[2]), hold_id, subject=s2)

    life = deps.lifecycle_service()
    for file_id in (accepted.id, hold.id):
        cand = Candidate.objects.filter(file_id=file_id).order_by("-version").first()
        row = File.objects.get(id=file_id)
        if cand is not None and row.state == FileState.CANDIDATE_READY:
            life.confirm_quality(ctx, file_id, cand.version)

    hold.refresh_from_db()
    deps.retention_service().set_retention_hold(
        ctx,
        hold.id,
        legal_hold=True,
        expected_version=hold.version,
        reason="synthetic legal hold seed",
    )

    foreign_id = UUID(school_b["file_foreign"])
    File.objects.create(
        id=foreign_id,
        school_id=UUID(school_b["school_id"]),
        purpose="answer_sheet",
        state=FileState.ACCEPTED,
        subject_person_id=fixtures.STUDENT_S1_SCHOOL_B,
        canonical_version=1,
        sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        byte_size=100,
        width=100,
        height=100,
        profile_version=PROFILE_DEFAULT,
        review_confirmed=True,
        confirmed_at=FROZEN_INSTANT,
        version=1,
        created_at=FROZEN_INSTANT,
        updated_at=FROZEN_INSTANT,
    )

    for row in File.objects.filter(school_id=school, review_confirmed=True):
        if row.source_id:
            backup_verifier().set_source(row.source_id, verified=True)
            SourceObject.objects.filter(id=row.source_id).update(backup_verified=True)

    File.objects.filter(id=accepted.id).update(confirmed_at=FROZEN_INSTANT - timedelta(days=8))

    return {
        "school_id": str(school),
        "pages_generated_documented": pages_generated_documented,
        "pages_seeded": pages_seeded,
        "file_ids": [str(i) for i in seeded],
        "file_candidate": str(candidate.id),
        "file_accepted": str(accepted_id),
        "file_hold": str(hold_id),
        "file_foreign": str(foreign_id),
        "student_s1": school_a["student_s1"],
        "student_s2": school_a["student_s2"],
        "binding_s1": school_a["binding_s1"],
        "uploader_actor_id": school_a["uploader_actor_id"],
        "unrelated_actor_id": school_a["unrelated_actor_id"],
        "profile_version": PROFILE_DEFAULT,
    }


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
