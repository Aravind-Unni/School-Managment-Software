"""Fixtures for M03's suite.

Runs under the M03 profile (``MODULE_ID=M03``), which installs only
``modules.timetable`` plus the harness. M03 consumes fake Access, fake Registry,
the Platform test adapter and the injected clock; it is the real provider of the
timetable itself, so nothing here fakes a timetable.

There is no real login in this profile: M01 is not installed. Identity comes from
the server-fixed development persona, exactly as the runner produces it, and it is
switched by changing a SETTING -- never by a header, because the shared transport
rejects client-asserted identity outright.

Written from the frozen contract in contracts/M03. Nothing here reads an
implementation; at the time these were written there was none.
"""

from __future__ import annotations

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

from m03_helpers import (
    FROZEN_INSTANT,
    THURSDAY_HOLIDAY,
    grid,
)

pytestmark = pytest.mark.module

@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment's school to School A for every test."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Serve every request as T1, the class teacher of C1, on loopback.

    M03 standalone has no login flow to authenticate through, so the persona is
    the only identity the profile can produce. It is configuration, not a client
    claim.
    """
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Return the injected clock, frozen on the fixture Wednesday."""
    from shared.fakes.clock import FixedClock

    fixed = FixedClock(FROZEN_INSTANT)
    settings.SCHOOL_CLOCK = fixed
    return fixed


@pytest.fixture
def as_persona(settings):
    """Return a function switching the server-side persona mid-test.

    Switching a SETTING is the point: the browser cannot do this, and a test that
    sent an identity header would be answered with 400 by the shared middleware.
    """

    def switch(actor_id, *, school_id=fixtures.SCHOOL_A, auth_level=AuthLevel.TWO_FACTOR):
        settings.DEV_PERSONA = DevPersona(
            actor_id=actor_id, school_id=school_id, auth_level=auth_level
        )
        return settings.DEV_PERSONA

    return switch


@pytest.fixture
def api(db, clock):
    """Return a helper performing M03 API calls against the real app.

    Mirrors M01's and M02's helpers so the three suites read the same way. Does
    not handle authentication: this profile has none.
    """

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

        def put(self, path: str, body: dict, **extra):
            return self.client.put(
                f"{self.BASE}{path}", data=body, content_type="application/json", **extra
            )

    return Api()


@pytest.fixture
def year_id():
    """Return the synthetic academic year id every draft is created against.

    Opaque to this module: the frozen RegistryPort exposes no academic year, so
    M03 stores the id and validates nothing about it. Recorded as gap 4 in
    contracts/M03/ports.md.
    """
    return str(fixtures.fixture_uuid("school_a.year.2026_2027"))


@pytest.fixture
def draft(api, year_id):
    """Create the baseline draft through the real API and return its body."""
    response = api.post(
        "/timetables",
        {"year_id": year_id, "effective_from": "2026-06-01", **grid()},
    )
    assert response.status_code == 201, response.content
    return response.json()


@pytest.fixture
def published(api, draft):
    """Publish the baseline draft and return the reread published version."""
    response = api.post(
        f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]}
    )
    assert response.status_code == 200, response.content
    return api.get(f"/timetables/{draft['id']}").json()


@pytest.fixture
def holiday(api, published):
    """Record the fixture holiday on the Thursday after the frozen date."""
    response = api.post(
        "/calendar-exceptions",
        {"date": THURSDAY_HOLIDAY, "kind": "holiday", "reason_key": "timetable.reason.holiday"},
    )
    assert response.status_code == 201, response.content
    return response.json()
