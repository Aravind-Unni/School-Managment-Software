"""Fixtures for M07's suite. MODULE_ID=M07; fake Access/Registry/Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 6, 20, 9, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is finance principal with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the shared SCHOOL_CLOCK object Access was bound to.

    FakeAccess holds ``adapter._now = SCHOOL_CLOCK.now`` from registry build.
    Replacing ``settings.SCHOOL_CLOCK`` with a new instance desyncs auth_time
    (middleware) from Access age checks. Mutate the shared object instead.
    """
    clk = settings.SCHOOL_CLOCK
    clk.set(FROZEN_INSTANT)
    return clk


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
    """Seed baseline fee charges for S1."""
    from modules.fees.seeds import seed_baseline

    return seed_baseline()
