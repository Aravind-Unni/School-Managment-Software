"""Marking rules: score above max, absent not zero, incomplete marks, authority."""

from __future__ import annotations

import uuid

import pytest

from modules.assessment.models import Result
from shared import fixtures

pytestmark = pytest.mark.module

COMPONENT_ID = "b0d00c56-b6e9-5025-a036-6c49617e1d5b"


def _attempt_for(assessment_id, student_id):
    """Return the attempt_id for a roster result."""
    return Result.objects.get(assessment_id=assessment_id, student_id=student_id).attempt_id


def test_score_above_max_rejected(api, create_draft):
    """PATCH with component score 100.01 on max 100 is 422."""
    created = create_draft()
    response = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "100.01"}],
        },
    )
    assert response.status_code == 422, response.content
    assert response.json()["message_key"] == "assessment.error.score_above_max"


def test_absent_not_zero(api, create_draft):
    """Absent outcome stores null score, never 0.00."""
    created = create_draft()
    response = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S2}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S2)),
            "status": "draft",
            "marking_outcome": "absent",
        },
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["result"]["marking_outcome"] == "absent"
    assert body["result"]["score"] is None
    assert body["total"] is None
    row = Result.objects.get(assessment_id=created["id"], student_id=fixtures.STUDENT_S2)
    assert row.score is None


def test_absent_with_numeric_score_rejected(api, create_draft):
    """Absent plus a numeric component score is 422."""
    created = create_draft()
    response = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S2}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S2)),
            "status": "draft",
            "marking_outcome": "absent",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "0.00"}],
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "assessment.error.absent_not_zero"


def test_stale_version_409(api, create_draft):
    """Wrong expected_version on PATCH is 409."""
    created = create_draft()
    response = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"] + 5,
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "50.00"}],
        },
    )
    assert response.status_code == 409


def test_unassigned_teacher_denied(api, create_draft, as_persona):
    """T2 marking C1 maths is 403."""
    created = create_draft()
    as_persona(fixtures.TEACHER_T2)
    response = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "40.00"}],
        },
    )
    assert response.status_code == 403


def test_foreign_school_404(api, create_draft):
    """Other-school assessment id is 404, never 403."""
    created = create_draft()
    foreign = uuid.uuid4()
    response = api.patch(
        f"/assessments/{foreign}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"],
            "attempt_id": str(uuid.uuid4()),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "10.00"}],
        },
    )
    assert response.status_code == 404


def test_incomplete_marks_block_submit(api, create_draft):
    """Submit without complete component scores is 422."""
    created = create_draft()
    # Mark S2 absent so only S1 is incomplete.
    patched = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S2}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S2)),
            "status": "draft",
            "marking_outcome": "absent",
        },
    ).json()
    response = api.post(
        f"/assessments/{created['id']}/submit",
        {"expected_version": patched["version"]},
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "assessment.error.incomplete_marks"


def test_policy_version_reproduced(api, create_draft):
    """ResultDTO carries the same policy_version as create."""
    created = create_draft()
    patched = api.patch(
        f"/assessments/{created['id']}/results/{fixtures.STUDENT_S1}",
        {
            "expected_version": created["version"],
            "attempt_id": str(_attempt_for(created["id"], fixtures.STUDENT_S1)),
            "status": "draft",
            "marking_outcome": "scored",
            "component_scores": [{"component_id": str(COMPONENT_ID), "score": "73.50"}],
        },
    ).json()
    assert patched["result"]["policy_version"] == "illustrative-v0"
    assert patched["result"]["grade"] is None
