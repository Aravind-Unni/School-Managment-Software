"""The single definition of how fake adapters are bound in non-production runs.

Both the standalone profile and the local SQLite test profile call
``build_fake_registry``. Having one definition means a port added here is
available to both, and a fake cannot be wired differently in tests than in the
standalone runner -- which is how "passes in tests, breaks in the runner" starts.
"""

from __future__ import annotations

from contracts.registration import ModuleRegistration

from .registry import AdapterKind, PortRegistry

#: Every port the harness can fake. A module declaring a consumer absent from
#: this map is a configuration error, not a silent no-op.
FAKEABLE_PORTS: frozenset[str] = frozenset(
    {"access", "registry", "platform", "notifications", "object_storage", "clock"}
)


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
        FakeNotifications,
        FakeObjectStorage,
        FakeRegistry,
        TestPlatformAdapter,
    )

    consumers = tuple(registration.consumers) if registration else ()
    unknown = sorted(set(consumers) - FAKEABLE_PORTS)
    if unknown:
        raise ValueError(
            f"module declares consumers this harness cannot fake: {unknown}; "
            f"fakeable ports are {sorted(FAKEABLE_PORTS)}"
        )

    def access_factory():
        """Build fake Access wired to the injected clock so 2FA age is testable."""
        adapter = FakeAccess()
        adapter._now = clock.now
        return adapter

    factories = {
        "access": access_factory,
        "registry": FakeRegistry,
        "platform": lambda: TestPlatformAdapter(worker_available=worker_available),
        "notifications": FakeNotifications,
        "object_storage": FakeObjectStorage,
        "clock": lambda: clock,
    }

    registry = PortRegistry(app_env=app_env, declared_consumers=frozenset(consumers))
    for port_name in consumers:
        registry.register(port_name, factories[port_name], kind=AdapterKind.FAKE)
    return registry
