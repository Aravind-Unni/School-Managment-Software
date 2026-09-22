"""GET/PUT/DELETE /students/{id}/photo."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
BASE = "/api/v1"


def _admit(api):
    return api.post(
        "/students",
        {
            "admission_no": "P1",
            "display_name": "Photo Pupil",
            "profile": {"date_of_birth": None, "preferred_language": "en"},
            "guardian_links": [],
            "external_ids": [],
            "duplicate_review": None,
        },
    ).json()


def test_no_photo_is_204(api, configured):
    student = _admit(api)
    assert api.get(f"/students/{student['id']}/photo").status_code == 204


def test_put_then_get_returns_the_image(api, configured):
    student = _admit(api)
    url = f"{BASE}/students/{student['id']}/photo"
    saved = api.client.put(url, data=PNG, content_type="image/png")
    assert saved.status_code == 200, saved.content
    got = api.client.get(url)
    assert got.status_code == 200
    assert got["Content-Type"] == "image/png"
    assert got.content == PNG
    details = api.get(f"/students/{student['id']}/details").json()
    assert details["has_photo"] is True


def test_non_image_is_refused(api, configured):
    student = _admit(api)
    url = f"{BASE}/students/{student['id']}/photo"
    response = api.client.put(url, data=b"%PDF-1.4 not a photo", content_type="image/png")
    assert response.status_code == 422, response.content


def test_too_big_is_refused(api, configured):
    student = _admit(api)
    url = f"{BASE}/students/{student['id']}/photo"
    response = api.client.put(url, data=PNG + b"\x00" * 400_000, content_type="image/png")
    assert response.status_code == 422, response.content


def test_delete_removes_it(api, configured):
    student = _admit(api)
    url = f"{BASE}/students/{student['id']}/photo"
    api.client.put(url, data=PNG, content_type="image/png")
    assert api.client.delete(url).status_code == 200
    assert api.client.get(url).status_code == 204
