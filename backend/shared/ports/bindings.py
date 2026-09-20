"""The single definition of how fake adapters are bound in non-production runs.

Both the standalone profile and the local SQLite test profile call
``build_fake_registry``. Having one definition means a port added here is
available to both, and a fake cannot be wired differently in tests than in the
standalone runner -- which is how "passes in tests, breaks in the runner" starts.
"""

from __future__ import annotations

from uuid import UUID

from contracts.registration import ModuleRegistration

from .registry import AdapterKind, PortRegistry

#: Every port the harness can fake. A module declaring a consumer absent from
#: this map is a configuration error, not a silent no-op.
FAKEABLE_PORTS: frozenset[str] = frozenset(
    {
        "access",
        "registry",
        "timetable",
        "assessment",
        "attendance",
        "fees",
        "platform",
        "notifications",
        "object_storage",
        "files",
        "clock",
    }
)

#: M08 scenario fee plan (contracts/M08/fixtures/scenario.json).
M08_FEE_PLAN_ID = UUID("b8e2c1a0-4f3d-5e6a-9b0c-1d2e3f4a5b6c")
M08_FEE_HEAD_ID = UUID("c9f3d2b1-5a4e-6f7b-0c1d-2e3f4a5b6c7d")
M08_FEE_AMOUNT_PAISE = 50000


def build_fake_registry(
    registration: ModuleRegistration | None,
    *,
    app_env: str,
    clock,
    worker_available: bool,
) -> PortRegistry:
    """Bind a deterministic fake for each port the module declares.

    Only declared consumers are bound, so ``resolve`` on an undeclared port fails
    with a clear message instead of handing back a working adapter the module
    never admitted depending on.

    Raises ValueError naming the unknown ports when a registration declares a
    consumer this harness cannot fake.

    Does not handle: real adapters. Integrated and production profiles have their
    own builders, which is what keeps a fake out of them structurally.
    """
    from shared.fakes import (
        FakeAccess,
        FakeAssessment,
        FakeAttendance,
        FakeFees,
        FakeFiles,
        FakeNotifications,
        FakeObjectStorage,
        FakeRegistry,
        FakeTimetable,
        TestPlatformAdapter,
    )
    from shared.fakes.registry import (
        m04_baseline_registry_kwargs,
        m05_baseline_registry_kwargs,
        m06_baseline_registry_kwargs,
    )

    consumers = tuple(registration.consumers) if registration else ()
    unknown = sorted(set(consumers) - FAKEABLE_PORTS)
    if unknown:
        raise ValueError(
            f"module declares consumers this harness cannot fake: {unknown}; "
            f"fakeable ports are {sorted(FAKEABLE_PORTS)}"
        )

    def access_factory():
        """Build fake Access wired to the injected clock so 2FA age is testable.

        Loads the module's own fixture grants when it declares any. Without this
        the fake denies every module-specific action, and the tempting fix is a
        test-only bypass inside the module -- which would mean its authorisation
        path never ran in development. Grants stay enumerated in the module, and
        only the FAKE builder reads them: the real profiles never call this.
        """
        adapter = FakeAccess(extra_rules=_module_fixture_rules(registration))
        adapter._now = clock.now
        return adapter

    def registry_factory():
        """Bind FakeRegistry, applying M04/M05/M06 baseline overlays when needed."""
        if registration is not None and registration.id == "M04":
            return FakeRegistry(**m04_baseline_registry_kwargs())
        if registration is not None and registration.id == "M05":
            return FakeRegistry(**m05_baseline_registry_kwargs())
        if registration is not None and registration.id == "M06":
            return FakeRegistry(**m06_baseline_registry_kwargs())
        return FakeRegistry()

    def files_factory():
        """Bind FakeFiles with the profile clock for grant expiry checks."""
        adapter = FakeFiles()
        adapter._clock = clock
        return adapter

    def assessment_factory():
        """Bind FakeAssessment for modules that consume published results."""
        return FakeAssessment()

    def attendance_factory():
        """Bind FakeAttendance for modules that consume period summaries."""
        return FakeAttendance()

    def fees_factory():
        """Bind FakeFees; seed M08 scenario plan when the module is transport."""
        adapter = FakeFees()
        if registration is not None and registration.id == "M08":
            adapter.seed_plan(
                fee_plan_id=M08_FEE_PLAN_ID,
                fee_head_id=M08_FEE_HEAD_ID,
                amount_paise=M08_FEE_AMOUNT_PAISE,
                proration_policy=None,
            )
        return adapter

    factories = {
        "access": access_factory,
        "registry": registry_factory,
        "timetable": FakeTimetable,
        "assessment": assessment_factory,
        "attendance": attendance_factory,
        "fees": fees_factory,
        "platform": lambda: TestPlatformAdapter(worker_available=worker_available),
        "notifications": FakeNotifications,
        "object_storage": FakeObjectStorage,
        "files": files_factory,
        "clock": lambda: clock,
    }

    registry = PortRegistry(app_env=app_env, declared_consumers=frozenset(consumers))
    for port_name in consumers:
        registry.register(port_name, factories[port_name], kind=AdapterKind.FAKE)
    return registry


def _module_fixture_rules(registration) -> tuple:
    """Return the fixture PolicyRules a module declares, or none.

    Looks for ``FIXTURE_POLICY_RULES`` in ``modules.<slug>.fixture_policy``. The
    module is absent for M00 and for any module that has not declared grants, so
    a missing file is a normal empty answer rather than an error.

    Does not handle: validating the rules. They are ordinary PolicyRule values
    and the fake applies its own deny-by-default semantics to them.
    """
    import importlib

    if registration is None:
        return ()
    try:
        module = importlib.import_module(f"modules.{registration.slug}.fixture_policy")
    except ModuleNotFoundError:
        return ()
    return tuple(getattr(module, "FIXTURE_POLICY_RULES", ()))
