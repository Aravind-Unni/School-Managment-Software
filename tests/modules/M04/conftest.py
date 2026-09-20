"""Fixtures for M04's suite. MODULE_ID=M04; fake Access/Registry/Timetable/Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.fakes.timetable import session_id_for
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)
SAMPLE_DATE = fixtures.TERM_SAMPLE_DATE


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is T1 on loopback."""
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
def _reset_fake_timetable():
    """Clear FakeTimetable mutation state between tests.

    cancel_session / bump_timetable_version persist on the process-bound adapter;
    without a reset, a later seed would see a cancelled P1 and fail.
    """
    from shared.ports import runtime

    try:
        timetable = runtime.get_registry().resolve("timetable")
    except Exception:
        yield
        return
    if hasattr(timetable, "_cancelled_ids"):
        timetable._cancelled_ids.clear()
    if hasattr(timetable, "_version_bump"):
        timetable._version_bump = 0
    yield
    if hasattr(timetable, "_cancelled_ids"):
        timetable._cancelled_ids.clear()
    if hasattr(timetable, "_version_bump"):
        timetable._version_bump = 0


@pytest.fixture
def api(db, clock):
    """Return a helper performing M04 API calls against the real app."""

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
def p1_id():
    """Stable P1 timetable_session_id on the sample date."""
    return session_id_for(
        school_id=fixtures.SCHOOL_A,
        section_id=fixtures.CLASS_C1,
        on=SAMPLE_DATE,
        slot_code="P1",
    )


@pytest.fixture
def p2_id():
    """Stable P2 timetable_session_id on the sample date."""
    return session_id_for(
        school_id=fixtures.SCHOOL_A,
        section_id=fixtures.CLASS_C1,
        on=SAMPLE_DATE,
        slot_code="P2",
    )


@pytest.fixture
def timetable():
    """Return the bound FakeTimetable for mutation in tests."""
    from shared.ports import runtime

    return runtime.get_registry().resolve("timetable")
