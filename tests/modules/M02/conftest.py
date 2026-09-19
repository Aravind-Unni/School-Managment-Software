"""Fixtures for M02's suite.

Runs under the M02 profile (``MODULE_ID=M02``), which installs only
``modules.registry`` plus the harness. M02 IS the real Registry, so it binds no
fake Registry; it consumes fake Access, fake Platform and the injected clock.

There is no real login in this profile: M01 is not installed. Identity comes from
the server-fixed development persona, exactly as the runner produces it. No test
asserts an identity header, because the shared transport refuses them.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from shared import fixtures

pytestmark = pytest.mark.module


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment's school to School A for every test."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Serve every request as the fixed staff persona on loopback.

    M02 standalone has no login flow to authenticate through, so the persona is
    the only identity the profile can produce. It is configuration, not a client
    claim: the browser cannot select or change it.
    """
    settings.DEV_PERSONA_MODE = "fixed"
    return settings


@pytest.fixture
def clock(settings):
    """Return the injected clock, frozen inside the fixture term."""
    from shared.fakes.clock import FixedClock

    fixed = FixedClock(datetime(2026, 7, 15, 4, 30, tzinfo=UTC))
    settings.SCHOOL_CLOCK = fixed
    return fixed


@pytest.fixture
def bootstrapped(db, clock):
    """Install the one SchoolConfig row a deployment cannot serve without.

    Goes through the module's real bootstrap, not an ORM insert, so a test would
    notice if the seed stopped installing it. The API never creates this row
    implicitly, which is exactly why every suite must install it first.
    """
    from modules.registry.seeds import bootstrap
    from shared import fixtures

    return bootstrap(fixtures.SCHOOL_A)


@pytest.fixture
def api(bootstrapped, clock):
    """Return a helper performing M02 API calls against the real app.

    Mirrors M01's helper so the two suites read the same way. Does not handle
    authentication: this profile has none.
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
def configured(api):
    """Create the reference data step-1 people tests build on.

    Returns the created year, standard and section bodies. Deliberately goes
    through the API rather than the ORM: a test that seeds by ORM would not
    notice an endpoint that rejects its own output.
    """
    year = api.post(
        "/academic-years",
        {"name": "2026-2027", "start": "2026-06-01", "end": "2027-03-31"},
    ).json()
    standard = api.post("/standards", {"number": 5}).json()
    section = api.post(
        "/sections",
        {"year_id": year["id"], "standard_id": standard["id"], "name": "A"},
    ).json()
    return {"year": year, "standard": standard, "section": section}
