"""Fixtures for M14's suite. MODULE_ID=M14; Fake Access; real PlatformAdapter.

Imports of ``modules.platform`` stay inside fixtures so pytest's conftest
discovery under other MODULE_IDs cannot pollute ``sys.modules`` and break the
standalone isolation assertion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)

#: Scenario school A id from contracts/M14/fixtures/scenario.json (same as shared).
_SCHOOL_A = UUID("83cfc7d4-738c-5527-ba46-c61563fe7c1c")
_OPERATOR = UUID("eda913d7-a893-5ecc-af4e-766d1332b2ee")


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin the deployment school to School A."""
    settings.SCHOOL_ID = str(_SCHOOL_A)
    return _SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is the operator with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=_OPERATOR,
        school_id=_SCHOOL_A,
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

    def switch(actor_id, *, school_id=_SCHOOL_A, auth_level=AuthLevel.TWO_FACTOR):
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
