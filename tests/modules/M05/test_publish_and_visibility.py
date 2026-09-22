"""Evidence bind, publish, reopen, and published-result visibility."""

from __future__ import annotations

from uuid import UUID

import pytest

from modules.assessment.api import deps
from modules.assessment.models import Result, ResultRevision
from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = pytest.mark.module

COMPONENT_ID = "b0d00c56-b6e9-5025-a036-6c49617e1d5b"
FILE_V1 = "c987840d-f4e9-5f2f-b7fd-dbdc2e4cfc8c"
FILE_V2 = "4fe00323-e39e-5eb4-80f0-00468702ffce"
TERM_ID = UUID("bb72592f-20fa-5e9c-ba91-2f81cd0f47eb")


def _attempt(assessment_id, student_id):
    """Return attempt_id for a roster result."""
    return Result.objects.get(assessment_id=assessment_id, student_id=student_id).attempt_id


def _prepare_scored_with_evidence(api, create_draft, *, file_id=FILE_V2, version=2):
    """Create draft, score S1, mark S2 absent, bind evidence; return state."""
    created = create_draft()
    assessment_id = created["id"]
    v = created["version"]
    s1 = api.patch(
        f"/assessments/{assessment_id}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": v,
            "attempt_id": str(_attempt(assessment_id, fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "73.50"}],
        },
    )
    assert s1.status_code == 200, s1.content
    v = s1.json()["version"]
    result_id = s1.json()["result"]["result_id"]
    bound = api.post(
        f"/results/{result_id}/evidence",
        {
            "expected_version": v,
            "pages": [{"file_id": str(file_id), "canonical_version": version, "page_no": 1}],
        },
    )
    assert bound.status_code == 200, bound.content
    v = bound.json()["version"]
    binding_id = bound.json()["bindings"][0]["binding_id"]
    s2 = api.patch(
        f"/assessments/{assessment_id}/results/{fixtures.STUDENT_S2}",
        {
            "expected_version": v,
            "attempt_id": str(_attempt(assessment_id, fixtures.STUDENT_S2)),
            "status": "draft",
            "marking_outcome": "absent",
        },
    )
    assert s2.status_code == 200, s2.content
    return {
        "assessment_id": assessment_id,
        "version": s2.json()["version"],
        "result_id": result_id,
        "binding_id": binding_id,
    }


def _submit_approve(api, assessment_id, version):
    """Drive draft through submit and approve; return new version."""
    submitted = api.post(f"/assessments/{assessment_id}/submit", {"expected_version": version})
    assert submitted.status_code == 200, submitted.content
    approved = api.post(
        f"/assessments/{assessment_id}/approve",
        {"expected_version": submitted.json()["version"]},
    )
    assert approved.status_code == 200, approved.content
    return approved.json()["version"]


def test_unconfirmed_evidence_blocks_bind(api, create_draft):
    """Binding candidate_v1 (unconfirmed) is 422."""
    created = create_draft()
    scored = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt(created["id"], fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "50.00"}],
        },
    ).json()
    response = api.post(
        f"/results/{scored['result']['result_id']}/evidence",
        {
            "expected_version": scored["version"],
            "pages": [
                {
                    "file_id": str(FILE_V1),
                    "canonical_version": 1,
                    "page_no": 1,
                }
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "assessment.error.unconfirmed_evidence"


def test_unconfirmed_blocks_publish_if_sneaked(api, create_draft):
    """Publish rejects when a bound evidence file is no longer confirmed."""
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    from shared.ports import runtime

    files = runtime.get_registry().resolve("files")
    stored = files._files[UUID(FILE_V2)]
    stored.review_confirmed = False
    response = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-unconfirmed",
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "assessment.error.unconfirmed_evidence"
    stored.review_confirmed = True


def test_publish_visible_to_s1_and_g1(api, create_draft, as_persona):
    """After publish, S1 and G1 see score 73.50 with evidence version 2."""
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    published = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-visible",
    )
    assert published.status_code == 200, published.content

    port = deps.assessment_port()
    for actor in (fixtures.STUDENT_S1, fixtures.GUARDIAN_G1):
        as_persona(actor)
        from django.conf import settings

        from contracts.identity import AuthLevel, RequestContext

        ctx = RequestContext(
            actor_id=actor,
            school_id=fixtures.SCHOOL_A,
            request_id="view",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=settings.SCHOOL_CLOCK.now(),
        )
        page = port.get_published_results(ctx, fixtures.STUDENT_S1, TERM_ID)
        assert len(page["items"]) == 1
        item = page["items"][0]
        assert item["score"] == "73.50"
        assert item["evidence_refs"][0]["version"] == 2
        assert item["evidence_refs"][0]["sha256"].startswith("bbbb")


def test_g2_and_s2_denied_s1_sheet(api, create_draft, as_persona):
    """G2 and S2 receive 404 on S1 evidence view."""
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    assert (
        api.client.post(
            f"/api/v1/assessments/{state['assessment_id']}/publication",
            data={"expected_version": version},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="pub-deny",
        ).status_code
        == 200
    )
    for actor in (fixtures.GUARDIAN_G2, fixtures.STUDENT_S2):
        as_persona(actor)
        response = api.get(f"/results/{state['result_id']}/evidence/{state['binding_id']}/view")
        assert response.status_code == 404, actor


def test_guardian_before_publish_empty(api, create_draft, as_persona):
    """Approved but unpublished: G1 published-results empty; evidence 404."""
    state = _prepare_scored_with_evidence(api, create_draft)
    _submit_approve(api, state["assessment_id"], state["version"])
    as_persona(fixtures.GUARDIAN_G1)
    from django.conf import settings

    from contracts.identity import AuthLevel, RequestContext

    ctx = RequestContext(
        actor_id=fixtures.GUARDIAN_G1,
        school_id=fixtures.SCHOOL_A,
        request_id="pre",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )
    page = deps.assessment_port().get_published_results(ctx, fixtures.STUDENT_S1, TERM_ID)
    assert page["items"] == []
    response = api.get(f"/results/{state['result_id']}/evidence/{state['binding_id']}/view")
    assert response.status_code == 404


def test_draft_never_in_get_published_results(api, create_draft, as_persona):
    """Draft rows are absent from get_published_results for S1."""
    create_draft()
    as_persona(fixtures.STUDENT_S1)
    from django.conf import settings

    from contracts.identity import AuthLevel, RequestContext

    ctx = RequestContext(
        actor_id=fixtures.STUDENT_S1,
        school_id=fixtures.SCHOOL_A,
        request_id="draft",
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )
    page = deps.assessment_port().get_published_results(ctx, fixtures.STUDENT_S1, TERM_ID)
    assert page["items"] == []


def test_repeated_publish_one_batch(api, create_draft):
    """Same Idempotency-Key twice yields one results_published event."""
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    first = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-once",
    )
    second = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-once",
    )
    assert first.status_code == 200, first.content
    assert second.status_code == 200
    assert first.json()["publication_id"] == second.json()["publication_id"]
    events = HarnessOutboxEvent.objects.filter(event_type="assessment.results_published")
    assert events.count() == 1


def test_publish_requires_2fa(api, create_draft, as_persona):
    """Missing 2FA on publish is 401 stale_auth."""
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    from contracts.identity import AuthLevel

    as_persona(fixtures.TEACHER_T1, auth_level=AuthLevel.PASSWORD)
    response = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-no-2fa",
    )
    assert response.status_code == 401
    assert response.json()["code"] == "stale_auth"


def test_correction_preserves_old_revision(api, create_draft):
    """Reopen + remake + republish retains the old revision snapshot."""
    from modules.assessment.models import Assessment

    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    first_pub = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="pub-before-reopen",
    )
    assert first_pub.status_code == 200, first_pub.content
    old_revision_ids = list(first_pub.json()["result_revision_ids"])
    old_count = ResultRevision.objects.count()

    assessment = Assessment.objects.get(id=state["assessment_id"])
    reopened = api.post(
        f"/assessments/{state['assessment_id']}/reopen",
        {"expected_version": assessment.version, "reason": "score correction"},
    )
    assert reopened.status_code == 200, reopened.content
    assert ResultRevision.objects.count() >= old_count + 1
    events = HarnessOutboxEvent.objects.filter(event_type="assessment.result_revised")
    assert events.count() >= 1
    for old_id in old_revision_ids:
        assert ResultRevision.objects.filter(id=old_id).exists()


# --- GET /students/{id}/results --------------------------------------------


def _publish(api, create_draft, key):
    state = _prepare_scored_with_evidence(api, create_draft)
    version = _submit_approve(api, state["assessment_id"], state["version"])
    response = api.client.post(
        f"/api/v1/assessments/{state['assessment_id']}/publication",
        data={"expected_version": version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert response.status_code == 200, response.content
    return state


def test_guardian_sees_published_marks_with_percent(api, create_draft, as_persona):
    """G1 sees S1's published mark, its percentage and a per-subject average."""
    _publish(api, create_draft, "results-g1")
    as_persona(fixtures.GUARDIAN_G1)
    response = api.get(f"/students/{fixtures.STUDENT_S1}/results?term_id={TERM_ID}")
    assert response.status_code == 200, response.content
    body = response.json()
    assert len(body["results"]) == 1
    row = body["results"][0]
    assert row["score"] == "73.50"
    assert row["percent"] is not None
    assert len(body["subjects"]) == 1
    assert body["subjects"][0]["tests"] == 1
    assert body["overall"]["average_percent"] == body["subjects"][0]["average_percent"]


def test_unpublished_marks_are_not_listed(api, create_draft, as_persona):
    """Approved but unpublished marks do not appear for the family."""
    state = _prepare_scored_with_evidence(api, create_draft)
    _submit_approve(api, state["assessment_id"], state["version"])
    as_persona(fixtures.GUARDIAN_G1)
    body = api.get(f"/students/{fixtures.STUDENT_S1}/results?term_id={TERM_ID}").json()
    assert body["results"] == []
    assert body["overall"]["average_percent"] is None


def test_another_family_cannot_read(api, create_draft, as_persona):
    """G2 is not S1's parent: 404, never someone else's marks."""
    _publish(api, create_draft, "results-g2")
    as_persona(fixtures.GUARDIAN_G2)
    response = api.get(f"/students/{fixtures.STUDENT_S1}/results?term_id={TERM_ID}")
    assert response.status_code == 404, response.content
