"""Fixtures for M06's suite. MODULE_ID=M06; fake Access/Registry/Assessment/Attendance."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)


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


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def baseline(db, clock):
    """Seed baseline scenario after DB and ports are ready."""
    from modules.performance.seeds import seed_baseline

    return seed_baseline(school_id=fixtures.SCHOOL_A)
