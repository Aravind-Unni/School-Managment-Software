"""Fixtures for M05's suite. MODULE_ID=M05; fake Access/Registry/Files/Platform."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona
from shared.ports import runtime

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

YEAR_ID = UUID("66632073-44d5-5c85-9583-95ee9424d514")
TERM_ID = UUID("bb72592f-20fa-5e9c-ba91-2f81cd0f47eb")
COMPONENT_ID = UUID("b0d00c56-b6e9-5025-a036-6c49617e1d5b")
FILE_V1 = UUID("c987840d-f4e9-5f2f-b7fd-dbdc2e4cfc8c")
FILE_V2 = UUID("4fe00323-e39e-5eb4-80f0-00468702ffce")
SHA_V1 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_V2 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is T1 with recent 2FA on loopback."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the injected clock."""
    from shared.fakes.clock import FixedClock

    fixed = FixedClock(FROZEN_INSTANT)
    settings.SCHOOL_CLOCK = fixed
    return fixed


@pytest.fixture
def as_persona(settings):
    """Switch the server-side persona mid-test."""

    def switch(actor_id, *, school_id=fixtures.SCHOOL_A, auth_level=AuthLevel.TWO_FACTOR):
        settings.DEV_PERSONA = DevPersona(
            actor_id=actor_id, school_id=school_id, auth_level=auth_level
        )
        return settings.DEV_PERSONA

    return switch


@pytest.fixture(autouse=True)
def _seed_fake_files(db, clock):
    """Seed scenario files onto the bound FakeFiles adapter.

    Depends on ``db`` so Django has imported the URLconf and bound ports.
    """
    files = runtime.get_registry().resolve("files")
    files.seed_file(
        file_id=FILE_V1,
        school_id=fixtures.SCHOOL_A,
        review_confirmed=False,
        canonical_version=1,
        sha256=SHA_V1,
    )
    files.seed_file(
        file_id=FILE_V2,
        school_id=fixtures.SCHOOL_A,
        review_confirmed=True,
        canonical_version=2,
        sha256=SHA_V2,
    )
    # Allow publish enqueue capture without claiming worker crash coverage.
    platform = runtime.get_registry().resolve("platform")
    platform._worker_available = True
    yield


@pytest.fixture
def api(db, clock):
    """Return a helper performing M05 API calls against the real app."""

    class Api:
        BASE = "/api/v1"

        def __init__(self) -> None:
            self.client = Client()

        def get(self, path: str, **extra):
            return self.client.get(f"{self.BASE}{path}", **extra)

        def post(self, path: str, body: dict | None = None, **extra):
            return self.client.post(
                f"{self.BASE}{path}",
                data=body if body is not None else {},
                content_type="application/json",
                **extra,
            )

        def patch(self, path: str, body: dict, **extra):
            return self.client.patch(
                f"{self.BASE}{path}", data=body, content_type="application/json", **extra
            )

    return Api()


@pytest.fixture
def create_draft(api):
    """Create a written_test draft for C1 maths and return the JSON body."""

    def _create(*, component_id: UUID = COMPONENT_ID, max_score: str = "100.00"):
        response = api.post(
            "/assessments",
            {
                "year_id": str(YEAR_ID),
                "term_id": str(TERM_ID),
                "section_id": str(fixtures.CLASS_C1),
                "subject_id": str(fixtures.SUBJECT_MATHS),
                "type": "written_test",
                "policy_version": "illustrative-v0",
                "max_score": max_score,
                "components": [
                    {
                        "id": str(component_id),
                        "max_score": max_score,
                        "weight": "1.000",
                        "topic": None,
                        "question_type": None,
                    }
                ],
            },
        )
        assert response.status_code == 201, response.content
        return response.json()

    return _create
