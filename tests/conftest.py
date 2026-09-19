"""Shared pytest fixtures for every suite.

Collection is PROFILE-AWARE: a module suite under ``tests/modules/<ID>/`` is only
collected when ``MODULE_ID`` selects that module. Standalone mode installs exactly
one business app, so collecting M01's tests under the M00 profile would import a
module the profile excluded -- and would break the very isolation assertion that
proves only one business app is loaded.

Provides the controlled clock, the bound fakes, and ready-made RequestContexts
for each fixture persona, so no test has to assemble identity by hand -- which is
how a test ends up asserting against a persona the runner would never produce.
"""

from __future__ import annotations

import os
import pathlib
from datetime import timedelta

import pytest

from contracts.identity import AuthLevel, RequestContext
from shared import fixtures
from shared.fakes import (
    FailureInjector,
    FakeAccess,
    FakeNotifications,
    FakeObjectStorage,
    FakeRegistry,
    FixedClock,
    TestPlatformAdapter,
)
from shared.scope_resolver import ScopeResolver


@pytest.fixture
def clock() -> FixedClock:
    """Return a clock frozen inside the fixture school term."""
    return FixedClock()


@pytest.fixture
def failures() -> FailureInjector:
    """Return an empty failure injector for deterministic fault tests."""
    return FailureInjector()


@pytest.fixture
def fake_access(clock: FixedClock) -> FakeAccess:
    """Return deny-by-default Access wired to the controlled clock."""
    adapter = FakeAccess()
    adapter._now = clock.now
    return adapter


@pytest.fixture
def fake_registry() -> FakeRegistry:
    """Return fixture-backed Registry."""
    return FakeRegistry()


@pytest.fixture
def fake_platform() -> TestPlatformAdapter:
    """Return the Platform test adapter with NO worker available.

    worker_available is False on purpose: a test that needs async behaviour must
    ask for a real worker explicitly via the requires_worker marker.
    """
    return TestPlatformAdapter(worker_available=False)


@pytest.fixture
def fake_notifications() -> FakeNotifications:
    """Return the in-memory notification sink."""
    return FakeNotifications()


@pytest.fixture
def fake_storage() -> FakeObjectStorage:
    """Return in-memory private object storage."""
    return FakeObjectStorage()


@pytest.fixture
def resolver(fake_access: FakeAccess, fake_registry: FakeRegistry) -> ScopeResolver:
    """Return the host scope resolver over the fakes."""
    return ScopeResolver(access=fake_access, registry=fake_registry)


@pytest.fixture
def context_factory(clock: FixedClock):
    """Return a factory building a RequestContext for any persona.

    Keyword ``auth_age`` ages the 2FA assertion, which is how the stale-auth
    tests avoid sleeping.
    """

    def build(
        actor_id,
        *,
        school_id=fixtures.SCHOOL_A,
        auth_level: AuthLevel = AuthLevel.TWO_FACTOR,
        auth_age: timedelta = timedelta(minutes=1),
        request_id: str = "test-request",
    ) -> RequestContext:
        return RequestContext(
            actor_id=actor_id,
            school_id=school_id,
            request_id=request_id,
            auth_level=auth_level,
            auth_time=clock.now() - auth_age,
        )

    return build


@pytest.fixture
def guardian_g1_context(context_factory):
    """RequestContext for G1, who guards S1 and S2."""
    return context_factory(fixtures.GUARDIAN_G1)


@pytest.fixture
def guardian_g2_context(context_factory):
    """RequestContext for G2, who is unrelated to S1."""
    return context_factory(fixtures.GUARDIAN_G2)


@pytest.fixture
def teacher_t1_context(context_factory):
    """RequestContext for T1, class teacher of C1."""
    return context_factory(fixtures.TEACHER_T1)


@pytest.fixture
def teacher_t2_context(context_factory):
    """RequestContext for T2, who is unassigned."""
    return context_factory(fixtures.TEACHER_T2)


#: The module whose suite may be collected in this run.
_ACTIVE_MODULE_ID = os.environ.get("MODULE_ID", "M00").upper()


def collect_ignore_glob() -> list[str]:
    """Return module-suite directories to skip for the active profile.

    Implemented as a function rather than a module-level list purely for
    readability; pytest accepts either.
    """
    modules_root = pathlib.Path(__file__).parent / "modules"
    if not modules_root.is_dir():
        return []
    return [
        f"modules/{entry.name}/*"
        for entry in sorted(modules_root.iterdir())
        if entry.is_dir() and entry.name.upper() != _ACTIVE_MODULE_ID
    ]


collect_ignore_glob = collect_ignore_glob()  # type: ignore[assignment]
