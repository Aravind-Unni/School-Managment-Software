"""Step 1: school configuration and academic reference data.

Asserts the frozen contract in contracts/M02, not the implementation: every
shape here comes from schemas/dtos.schema.json and openapi.json.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.module


def test_school_config_is_installed_by_the_bootstrap_and_readable(api):
    """The single school-config row exists before any write touches it."""
    response = api.get("/school-config")

    assert response.status_code == 200
    body = response.json()
    assert body["board"] == "CBSE"
    assert body["default_language"] in {"en", "ml"}
    assert body["version"] >= 1


def test_school_config_put_updates_under_expected_version(api):
    """A correct expected_version applies the update and advances the version."""
    current = api.get("/school-config").json()

    response = api.put(
        "/school-config",
        {
            "display_name": "Ayyappa Memorial HSS",
            "board": "CBSE",
            "default_language": "ml",
            "expected_version": current["version"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Ayyappa Memorial HSS"
    assert body["default_language"] == "ml"
    assert body["version"] == current["version"] + 1


def test_school_config_put_with_stale_expected_version_is_409(api):
    """A second writer holding the old version loses, rather than overwriting."""
    current = api.get("/school-config").json()
    body = {
        "display_name": "First writer",
        "board": "CBSE",
        "default_language": "en",
        "expected_version": current["version"],
    }
    assert api.put("/school-config", body).status_code == 200

    response = api.put("/school-config", {**body, "display_name": "Second writer"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "version_conflict"


def test_school_config_put_does_not_implicitly_create(api):
    """PUT is an update of the installed row; it never creates a second one."""
    first = api.get("/school-config").json()
    api.put(
        "/school-config",
        {
            "display_name": "Renamed",
            "board": "CBSE",
            "default_language": "en",
            "expected_version": first["version"],
        },
    )

    second = api.get("/school-config").json()
    assert second["id"] == first["id"]


def test_academic_year_create_returns_201_in_draft_state(api):
    """A new year starts in draft; activation is a separate reviewed transition."""
    response = api.post(
        "/academic-years",
        {"name": "2026-2027", "start": "2026-06-01", "end": "2027-03-31"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "draft"
    assert body["version"] == 1
    assert body["name"] == "2026-2027"


def test_academic_year_rejects_end_before_start(api):
    """A year that ends before it begins is refused, not stored and sorted later."""
    response = api.post(
        "/academic-years",
        {"name": "backwards", "start": "2027-03-31", "end": "2026-06-01"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_standard_number_is_constrained_to_the_twelve_school_years(api):
    """Standard 13 does not exist in this school system, so it is refused."""
    assert api.post("/standards", {"number": 12}).status_code == 201

    response = api.post("/standards", {"number": 13})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_section_must_reference_a_year_and_standard_in_the_same_school(api, configured):
    """A section is created against existing reference rows and starts unarchived."""
    body = api.post(
        "/sections",
        {
            "year_id": configured["year"]["id"],
            "standard_id": configured["standard"]["id"],
            "name": "B",
        },
    )

    assert body.status_code == 201
    assert body.json()["archived"] is False


def test_section_referencing_an_unknown_standard_is_404(api, configured):
    """A missing nested reference is indistinguishable from another school's."""
    response = api.post(
        "/sections",
        {
            "year_id": configured["year"]["id"],
            "standard_id": "00000000-0000-4000-8000-000000000000",
            "name": "C",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "object_inaccessible"


def test_term_must_fall_inside_its_academic_year(api, configured):
    """A term outside its year's dates is a validation failure, not a warning."""
    response = api.post(
        "/terms",
        {
            "year_id": configured["year"]["id"],
            "name": "Impossible term",
            "start": "2025-01-01",
            "end": "2025-03-31",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_subject_code_is_unique_within_the_school(api):
    """Two subjects cannot share a code; the second is a state conflict."""
    assert api.post("/subjects", {"code": "MAL", "display_name": "Malayalam"}).status_code == 201

    response = api.post("/subjects", {"code": "MAL", "display_name": "Malayalam again"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "state_conflict"


def test_archive_preserves_the_row_rather_than_deleting_it(api, configured):
    """Archive is reversible bookkeeping; there is no destructive DELETE API."""
    section_id = configured["section"]["id"]
    section = api.get(f"/sections/{section_id}").json()

    response = api.post(
        f"/sections/{section_id}/archive", {"expected_version": section["version"]}
    )

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert api.get(f"/sections/{section_id}").status_code == 200
