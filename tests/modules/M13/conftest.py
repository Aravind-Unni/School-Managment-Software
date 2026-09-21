"""Fixtures for M13's suite. MODULE_ID=M13; fake Access/Registry/Files/Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is the principal running bulk work, with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the shared SCHOOL_CLOCK inside the fixture term."""
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
def context_for(clock):
    """Build a server-side RequestContext for any persona in School A."""

    def build(actor_id, *, school_id=fixtures.SCHOOL_A, request_id="m13-test"):
        return RequestContext(
            actor_id=actor_id,
            school_id=school_id,
            request_id=request_id,
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=clock.now(),
        )

    return build


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def baseline(db, clock):
    """Seed policy, the staged import CSV, published results and attendance."""
    from modules.exchange.seeds import seed_baseline

    return seed_baseline()
