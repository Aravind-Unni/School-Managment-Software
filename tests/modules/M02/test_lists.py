"""Every Registry collection a picker or directory reads answers GET."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path",
    [
        "/academic-years",
        "/terms",
        "/standards",
        "/sections",
        "/subjects",
        "/guardians",
        "/staff",
        "/students",
        "/teaching-assignments",
    ],
)
def test_collection_lists_a_page(api, configured, path):
    response = api.get(path)
    assert response.status_code == 200, response.content
    body = response.json()
    assert "items" in body and "next_cursor" in body


def test_student_search_filters_by_name(api, configured):
    for number, name in ((1, "Anjali Nair"), (2, "Rohan Das")):
        api.post(
            "/students",
            {
                "admission_no": f"S{number}",
                "display_name": name,
                "profile": {"date_of_birth": None, "preferred_language": "en"},
                "guardian_links": [],
                "external_ids": [],
                "duplicate_review": None,
            },
        )
    names = [row["display_name"] for row in api.get("/students?query=anjali").json()["items"]]
    assert names == ["Anjali Nair"]
