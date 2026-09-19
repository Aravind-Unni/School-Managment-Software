"""Step 1: the duplicate-review gate on student admission.

The reviewed rule: an exact admission-number collision can never be overridden,
while an exact name plus a non-null matching birth date raises a CANDIDATE that a
human must acknowledge. Nothing here merges identities automatically.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.module

TWIN = {
    "admission_no": "2026/0100",
    "display_name": "Arjun Pillai",
    "profile": {"date_of_birth": "2014-08-30", "preferred_language": "en"},
    "guardian_links": [],
    "external_ids": [],
    "duplicate_review": None,
}


def test_same_name_and_birth_date_blocks_creation_without_acknowledgement(api):
    """A likely duplicate is refused until a human says these are two people."""
    api.post("/students", TWIN)

    response = api.post("/students", {**TWIN, "admission_no": "2026/0101"})

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "state_conflict"
    assert error["message_key"] == "registry.error.duplicate_review_required"


def test_duplicate_review_lists_the_candidate_with_its_reason(api):
    """The review endpoint names why each candidate matched, and pins its version."""
    first = api.post("/students", TWIN).json()

    response = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_version"] >= 1
    assert body["candidates"] == [
        {"student_id": first["id"], "version": 1, "reason": "name_and_birth_date"}
    ]
    assert body["expires_at"]


def test_acknowledged_review_allows_the_second_child_to_be_admitted(api):
    """With a stated reason, the distinct person is created."""
    api.post("/students", TWIN)
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()

    response = api.post(
        "/students",
        {
            **TWIN,
            "admission_no": "2026/0101",
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": "Twin siblings; separate birth certificates sighted.",
            },
        },
    )

    assert response.status_code == 201


def test_an_acknowledgement_without_a_reason_is_refused(api):
    """Acknowledging with a null reason is not a decision; it is a click-through."""
    api.post("/students", TWIN)
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()

    response = api.post(
        "/students",
        {
            **TWIN,
            "admission_no": "2026/0101",
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": None,
            },
        },
    )

    assert response.status_code == 409


def test_an_exact_admission_duplicate_cannot_be_acknowledged_away(api):
    """The review token does not unlock a unique-key collision."""
    api.post("/students", TWIN)
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": TWIN["admission_no"],
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()

    response = api.post(
        "/students",
        {
            **TWIN,
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": "Insisting anyway.",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message_key"] == "registry.error.admission_number_exists"


def test_a_review_taken_for_different_input_does_not_transfer(api):
    """The token binds the canonical input it was issued for."""
    api.post("/students", TWIN)
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()

    response = api.post(
        "/students",
        {
            **TWIN,
            "admission_no": "2026/0102",
            "display_name": "Someone Else Entirely",
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": "Reusing a token from another admission.",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message_key"] == "registry.error.duplicate_review_stale"


def test_a_candidate_that_changed_since_the_review_invalidates_it(api):
    """Recheck happens under the final transaction, so a moved version is stale."""
    first = api.post("/students", TWIN).json()
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()
    api.put(
        f"/students/{first['id']}",
        {
            "display_name": TWIN["display_name"],
            "profile": {"date_of_birth": "2014-08-30", "preferred_language": "ml"},
            "external_ids": [],
            "expected_version": 1,
        },
    )

    response = api.post(
        "/students",
        {
            **TWIN,
            "admission_no": "2026/0101",
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": "Twins.",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message_key"] == "registry.error.duplicate_review_stale"


def test_a_null_birth_date_does_not_match_another_null_birth_date(api):
    """Absence of a birth date is not evidence of sameness."""
    unknown_dob = {
        **TWIN,
        "admission_no": "2026/0200",
        "profile": {"date_of_birth": None, "preferred_language": "en"},
    }
    api.post("/students", unknown_dob)

    response = api.post("/students", {**unknown_dob, "admission_no": "2026/0201"})

    assert response.status_code == 201


def test_an_expired_review_is_refused(api, clock):
    """The reviewed fifteen-minute window is enforced, not decorative."""
    api.post("/students", TWIN)
    review = api.post(
        "/students/duplicate-review",
        {
            "admission_no": "2026/0101",
            "display_name": TWIN["display_name"],
            "profile": TWIN["profile"],
        },
    ).json()
    clock.advance(minutes=16)

    response = api.post(
        "/students",
        {
            **TWIN,
            "admission_no": "2026/0101",
            "duplicate_review": {
                "review_id": review["review_id"],
                "review_version": review["review_version"],
                "distinct_person_reason": "Twins.",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message_key"] == "registry.error.duplicate_review_stale"
