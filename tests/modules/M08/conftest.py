"""Fixtures for M08's suite. MODULE_ID=M08; fake Access/Registry/Fees/Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 6, 15, 9, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is transport principal with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.PRINCIPAL_P1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the shared SCHOOL_CLOCK object Access was bound to."""
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
def fees(db):
    """Return the bound FakeFees adapter after URLconf installs the registry.

    Resolving ports before the URLconf runs would build an on-demand registry
    that ``config.urls`` then replaces, leaving tests holding a stale FakeFees.
    """
    from django.urls import get_resolver

    get_resolver()
    from shared.ports import runtime

    adapter = runtime.get_registry().resolve("fees")
    adapter.calls.clear()
    adapter._charges_by_key.clear()
    adapter._charges_by_id.clear()
    adapter._payloads.clear()
    adapter._credits.clear()
    adapter._timeout_keys.clear()
    adapter.failures = __import__(
        "shared.fakes.failures", fromlist=["FailureInjector"]
    ).FailureInjector()
    return adapter


@pytest.fixture
def baseline(db, clock, fees):
    """Seed baseline bus + S1 participation after FakeFees is the live binding."""
    from modules.transport.seeds import seed_baseline

    return seed_baseline()
