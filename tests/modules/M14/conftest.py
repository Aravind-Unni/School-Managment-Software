"""Fixtures for M14's suite. MODULE_ID=M14; Fake Access; real PlatformAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from modules.platform import fixture_ids as ids
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment school to School A."""
    settings.SCHOOL_ID = str(ids.SCHOOL_A)
    return ids.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is the operator with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=ids.OPERATOR_ACTOR,
        school_id=ids.SCHOOL_A,
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

    def switch(actor_id, *, school_id=ids.SCHOOL_A, auth_level=AuthLevel.TWO_FACTOR):
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
    """Seed jobs, audit, backup manifests."""
    from modules.platform.seeds import _seed_baseline_rows

    return _seed_baseline_rows()
