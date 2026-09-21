"""GET /students/mine: a guardian sees their own linked children only."""

from __future__ import annotations

import uuid

import pytest

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.django_db


def _student(api, admission_no, name):
    return api.post(
        "/students",
        {
            "admission_no": admission_no,
            "display_name": name,
            "profile": {"date_of_birth": None, "preferred_language": "en"},
            "guardian_links": [],
            "external_ids": [],
            "duplicate_review": None,
        },
    ).json()


def test_a_guardian_lists_only_their_linked_children(api, configured, settings):
    parent = api.post(
        "/guardians",
        {"display_name": "Parent", "email": None, "phone": None, "external_ids": []},
    ).json()
    mine = _student(api, "M1", "Own Child")
    _student(api, "M2", "Someone Else")
    api.post(
        "/guardian-links",
        {
            "student_id": mine["id"],
            "guardian_id": parent["id"],
            "visibility": "academic",
            "from_date": "2026-06-01",
            "to_date": None,
        },
    )
    settings.DEV_PERSONA = DevPersona(
        actor_id=uuid.UUID(parent["id"]),
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.PASSWORD,
    )
    body = api.get("/students/mine").json()
    assert [row["display_name"] for row in body["items"]] == ["Own Child"]
    assert body["items"][0]["relationship"] == "guardian"


def test_staff_act_for_no_pupils(api, configured):
    assert api.get("/students/mine").json()["items"] == []
