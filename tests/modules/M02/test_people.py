"""Step 1: students, guardians and staff, and the strict-write rules on them."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.module

MINIMAL_STUDENT = {
    "admission_no": "2026/0001",
    "display_name": "Anjali Menon",
    "profile": {"date_of_birth": "2015-04-12", "preferred_language": "ml"},
    "guardian_links": [],
    "external_ids": [],
    "duplicate_review": None,
}


def test_student_creation_returns_the_minimal_student_dto(api):
    """Creation returns the frozen internal StudentDTO, which carries no version."""
    response = api.post("/students", MINIMAL_STUDENT)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "school_id", "admission_no", "display_name", "status"}
    assert body["status"] == "active"
    assert body["admission_no"] == "2026/0001"


def test_follow_up_get_supplies_the_versioned_browser_record(api):
    """The browser record is a separate, versioned shape from the internal DTO."""
    created = api.post("/students", MINIMAL_STUDENT).json()

    response = api.get(f"/students/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["archived"] is False
    assert body["profile"] == {"date_of_birth": "2015-04-12", "preferred_language": "ml"}
    assert body["external_ids"] == []


def test_admission_number_trims_outer_whitespace_and_keeps_case(api):
    """The reviewed normalisation is an outer trim only; no case folding."""
    created = api.post(
        "/students", {**MINIMAL_STUDENT, "admission_no": "  2026/AB01  "}
    ).json()

    assert created["admission_no"] == "2026/AB01"


def test_duplicate_admission_number_is_a_state_conflict(api):
    """Admission numbers are unique per school and cannot be overridden."""
    api.post("/students", MINIMAL_STUDENT)

    response = api.post(
        "/students", {**MINIMAL_STUDENT, "display_name": "A different child"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "state_conflict"
    assert response.json()["error"]["message_key"] == "registry.error.admission_number_exists"


def test_admission_number_comparison_is_case_sensitive(api):
    """Case is preserved and significant, so these are two different numbers."""
    api.post("/students", {**MINIMAL_STUDENT, "admission_no": "2026/ab01"})

    response = api.post("/students", {**MINIMAL_STUDENT, "admission_no": "2026/AB01"})

    assert response.status_code == 201


def test_student_write_rejects_a_client_supplied_school(api):
    """school is not an accepted field; a closed object refuses it outright."""
    response = api.post("/students", {**MINIMAL_STUDENT, "school_id": "attacker-chosen"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_student_write_rejects_a_client_supplied_version(api):
    """Version is server state, never an input on create."""
    response = api.post("/students", {**MINIMAL_STUDENT, "version": 7})

    assert response.status_code == 422


def test_student_write_rejects_an_unknown_field(api):
    """Closed request objects reject anything not in the contract."""
    response = api.post("/students", {**MINIMAL_STUDENT, "aadhaar": "1234"})

    assert response.status_code == 422


def test_student_update_requires_expected_version(api):
    """An update without expected_version is refused rather than applied blindly."""
    created = api.post("/students", MINIMAL_STUDENT).json()

    response = api.put(
        f"/students/{created['id']}",
        {
            "display_name": "Anjali M Menon",
            "profile": {"date_of_birth": "2015-04-12", "preferred_language": "ml"},
            "external_ids": [],
        },
    )

    assert response.status_code == 422


def test_student_update_with_stale_expected_version_is_409(api):
    """Two writers racing: the one holding the old version is refused."""
    created = api.post("/students", MINIMAL_STUDENT).json()
    update = {
        "display_name": "First",
        "profile": {"date_of_birth": "2015-04-12", "preferred_language": "ml"},
        "external_ids": [],
        "expected_version": 1,
    }
    assert api.put(f"/students/{created['id']}", update).status_code == 200

    response = api.put(f"/students/{created['id']}", {**update, "display_name": "Second"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "version_conflict"


def test_unknown_student_is_404_with_the_shared_envelope(api):
    """A missing id and another school's id are the same answer."""
    response = api.get("/students/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "object_inaccessible"


def test_guardian_accepts_null_contact_details(api):
    """Email and phone are explicitly nullable; a guardian may have neither."""
    response = api.post(
        "/guardians",
        {"display_name": "Ramesh Nair", "email": None, "phone": None, "external_ids": []},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] is None
    assert body["phone"] is None
    assert body["version"] == 1


def test_guardian_rejects_a_malformed_email(api):
    """The contract declares format email, so a non-address is refused."""
    response = api.post(
        "/guardians",
        {"display_name": "Bad", "email": "not-an-address", "phone": None, "external_ids": []},
    )

    assert response.status_code == 422


def test_staff_creation_returns_a_versioned_record(api):
    """Staff are people records; assignments come in step 2."""
    response = api.post("/staff", {"display_name": "Suresh Kumar", "external_ids": []})

    assert response.status_code == 201
    assert response.json()["version"] == 1
    assert response.json()["archived"] is False


def test_external_ids_round_trip_on_a_student(api):
    """External ids are stored as supplied and returned in the browser record."""
    created = api.post(
        "/students",
        {**MINIMAL_STUDENT, "external_ids": [{"source": "previous_school", "value": "X-9"}]},
    ).json()

    record = api.get(f"/students/{created['id']}").json()

    assert record["external_ids"] == [{"source": "previous_school", "value": "X-9"}]


def test_student_list_is_a_page_with_items_and_next_cursor(api):
    """Collections use the shared items/next_cursor shape, never a bare array."""
    api.post("/students", MINIMAL_STUDENT)

    response = api.get("/students")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "next_cursor"}
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1


def test_student_list_rejects_an_invalid_cursor_with_422(api):
    """An opaque cursor is validated, not silently ignored."""
    response = api.get("/students?cursor=not-a-real-cursor")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_student_list_caps_page_size_at_one_hundred(api):
    """page_size above the cap is a validation failure, not a silent clamp."""
    response = api.get("/students?page_size=101")

    assert response.status_code == 422
