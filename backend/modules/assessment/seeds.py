"""Baseline seed for M05: written_test with S1 scored+evidence and S2 absent, published.

Uses contracts/M05/fixtures/scenario.json IDs. Seeds FakeFiles with candidate_v1
(unconfirmed) and confirmed_v2. Leaves the assessment **published** so acceptance
and guardian reads work immediately after `dev.py seed`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures
from shared.ports import runtime

from .api import deps
from .models import Assessment, AssessmentState, EvidenceBinding, Publication, Result

FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

ASSESSMENT_ID = UUID("2247cd89-db77-5471-ac2a-c0b9eea94cc5")
COMPONENT_ID = UUID("b0d00c56-b6e9-5025-a036-6c49617e1d5b")
YEAR_ID = UUID("66632073-44d5-5c85-9583-95ee9424d514")
TERM_ID = UUID("bb72592f-20fa-5e9c-ba91-2f81cd0f47eb")
FILE_V1 = UUID("c987840d-f4e9-5f2f-b7fd-dbdc2e4cfc8c")
FILE_V2 = UUID("4fe00323-e39e-5eb4-80f0-00468702ffce")
RESULT_S1 = UUID("a250f220-9462-5a9d-96df-b20464fd62ef")
ATTEMPT_S1 = UUID("8f5529f7-c6ac-517e-90e9-1052291aa2a4")
BINDING_S1 = UUID("489141dd-3639-5abe-9f5c-9aab70f25f8e")
RESULT_S2 = UUID("78a05f7a-bf3c-5b32-b883-b6302f857640")
SHA_V1 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_V2 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _seed_files(school_id: UUID) -> None:
    """Install scenario files on the bound FakeFiles adapter."""
    files = runtime.get_registry().resolve("files")
    files.seed_file(
        file_id=FILE_V1,
        school_id=school_id,
        review_confirmed=False,
        canonical_version=1,
        sha256=SHA_V1,
    )
    files.seed_file(
        file_id=FILE_V2,
        school_id=school_id,
        review_confirmed=True,
        canonical_version=2,
        sha256=SHA_V2,
    )


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load the contracted baseline scenario and publish it as T1.

    Assumes FakeRegistry M05 overlays and FakeFiles are bound. Creates the
    written_test assessment, marks S1 73.50 with confirmed v2 evidence, marks S2
    absent, then submit → approve → publish.
    """
    school = school_id or fixtures.SCHOOL_A
    _seed_files(school)
    ctx = RequestContext(
        actor_id=fixtures.TEACHER_T1,
        school_id=school,
        request_id="seed-baseline",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=FROZEN_INSTANT,
    )

    Assessment.objects.filter(id=ASSESSMENT_ID).delete()

    created = deps.create_service().create(
        ctx,
        year_id=YEAR_ID,
        term_id=TERM_ID,
        section_id=fixtures.CLASS_C1,
        subject_id=fixtures.SUBJECT_MATHS,
        assessment_type="written_test",
        components=[
            {
                "id": COMPONENT_ID,
                "max_score": "100.00",
                "weight": "1.000",
                "topic": None,
                "question_type": None,
            }
        ],
        policy_version="illustrative-v0",
        max_score="100.00",
        assessment_id=ASSESSMENT_ID,
        result_ids={
            fixtures.STUDENT_S1: RESULT_S1,
            fixtures.STUDENT_S2: RESULT_S2,
        },
        attempt_ids={fixtures.STUDENT_S1: ATTEMPT_S1},
    )
    version = created["version"]

    patched_s1 = deps.marks_service().patch(
        ctx,
        assessment_id=ASSESSMENT_ID,
        student_id=fixtures.STUDENT_S1,
        expected_version=version,
        attempt_id=ATTEMPT_S1,
        status="draft",
        marking_outcome="scored",
        component_scores=[{"component_id": COMPONENT_ID, "score": "73.50"}],
    )
    version = patched_s1["version"]

    files = runtime.get_registry().resolve("files")
    ref = files.pin_evidence(ctx, FILE_V2, 2, BINDING_S1)
    result_s1 = Result.objects.get(id=RESULT_S1)
    EvidenceBinding.objects.filter(result=result_s1, revision_id__isnull=True).delete()
    EvidenceBinding.objects.create(
        id=BINDING_S1,
        result=result_s1,
        revision_id=None,
        file_id=ref.file_id,
        file_version=ref.version,
        sha256=ref.sha256,
        page_no=1,
    )
    assessment = Assessment.objects.get(id=ASSESSMENT_ID)
    assessment.version += 1
    assessment.updated_at = FROZEN_INSTANT
    assessment.save(update_fields=["version", "updated_at"])
    result_s1.version += 1
    result_s1.updated_at = FROZEN_INSTANT
    result_s1.save(update_fields=["version", "updated_at"])
    version = assessment.version

    attempt_s2 = Result.objects.get(id=RESULT_S2).attempt_id
    patched_s2 = deps.marks_service().patch(
        ctx,
        assessment_id=ASSESSMENT_ID,
        student_id=fixtures.STUDENT_S2,
        expected_version=version,
        attempt_id=attempt_s2,
        status="draft",
        marking_outcome="absent",
        component_scores=[],
    )
    version = patched_s2["version"]

    submitted = deps.workflow_service().submit(
        ctx, assessment_id=ASSESSMENT_ID, expected_version=version
    )
    version = submitted["version"]
    approved = deps.workflow_service().approve(
        ctx, assessment_id=ASSESSMENT_ID, expected_version=version
    )
    version = approved["version"]
    published = deps.publish_service().publish(
        ctx,
        assessment_id=ASSESSMENT_ID,
        expected_version=version,
        idempotency_key="seed-baseline-publish",
    )

    pub = (
        Publication.objects.filter(assessment_id=ASSESSMENT_ID)
        .order_by("-published_at")
        .first()
    )
    return {
        "scenario": "baseline",
        "assessment_id": str(ASSESSMENT_ID),
        "publication_id": str(pub.id) if pub else published["publication_id"],
        "state": AssessmentState.PUBLISHED,
        "s1_score": "73.50",
        "s2_outcome": "absent",
        "results": Result.objects.filter(assessment_id=ASSESSMENT_ID).count(),
    }


def empty(*, school_id=None) -> dict[str, int]:
    """No-op empty scenario for harness completeness."""
    return {"assessments": 0, "results": 0}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
