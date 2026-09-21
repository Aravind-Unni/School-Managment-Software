"""Fixtures for M11's suite. MODULE_ID=M11; fake Access/Registry/Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is notice publisher with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the shared SCHOOL_CLOCK."""
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
    """Seed policy, templates, contacts and draft notices."""
    from modules.communications.seeds import seed_baseline

    return seed_baseline()


@pytest.fixture(autouse=True)
def _inline_platform(db):
    """Run enqueued work inline, which is what these assertions describe.

    The standalone harness sets WORKER_AVAILABLE for modules that declare a
    worker, but the pytest process shares no database with that worker, so a
    queued job could never complete here. Crash/retry behaviour belongs to the
    worker suites, not these acceptance checks.
    """
    from django.urls import get_resolver

    from shared.ports import runtime

    get_resolver()
    platform = runtime.get_registry().resolve("platform")
    previous = getattr(platform, "_worker_available", None)
    if previous is not None:
        platform._worker_available = False
    yield
    if previous is not None:
        platform._worker_available = previous
