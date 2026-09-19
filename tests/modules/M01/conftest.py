"""Fixtures for M01's suite.

Runs under the M01 profile (``MODULE_ID=M01``), which installs only
``modules.access`` plus the harness and binds a FAKE REGISTRY ONLY -- M01 provides
the real Access, so it binds no fake Access. There is no synthetic persona: every
test authenticates for real through the login flow.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client
from m01_helpers import LOGINS

from shared import fixtures

pytestmark = pytest.mark.module


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment's school to School A for every test."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture
def clock(settings):
    """Return the injected clock, frozen inside the fixture term."""
    from shared.fakes.clock import FixedClock

    fixed = FixedClock(datetime(2026, 7, 15, 4, 30, tzinfo=UTC))
    settings.SCHOOL_CLOCK = fixed
    return fixed


@pytest.fixture
def seeded(db, clock):
    """Load the baseline scenario and return the account rows by label."""
    from modules.access.models import User
    from modules.access.seeds import baseline

    baseline()
    return {label: User.objects.get(login_name=login) for label, login in LOGINS.items()}


@pytest.fixture
def client() -> Client:
    """Return a test client bound to loopback."""
    return Client()


@pytest.fixture
def api():
    """Return a helper that performs M01 API calls with CSRF handled.

    The double-submit CSRF token must be echoed from the cookie into a header on
    every unsafe request, exactly as the browser app does. Doing it here means each
    test does not have to remember.
    """

    class Api:
        BASE = "/api/v1"

        def __init__(self) -> None:
            self.client = Client()

        def post(self, path: str, body: dict | None = None, **extra):
            csrf = self.client.cookies.get("school_csrf")
            if csrf is not None:
                extra.setdefault("HTTP_X_CSRF_TOKEN", csrf.value)
            return self.client.post(
                f"{self.BASE}{path}",
                data=body if body is not None else {},
                content_type="application/json",
                **extra,
            )

        def put(self, path: str, body: dict, **extra):
            csrf = self.client.cookies.get("school_csrf")
            if csrf is not None:
                extra.setdefault("HTTP_X_CSRF_TOKEN", csrf.value)
            return self.client.put(
                f"{self.BASE}{path}", data=body, content_type="application/json", **extra
            )

        def get(self, path: str, **extra):
            return self.client.get(f"{self.BASE}{path}", **extra)

        @property
        def session_cookie(self) -> str | None:
            morsel = self.client.cookies.get("school_session")
            return morsel.value if morsel else None

    return Api()
