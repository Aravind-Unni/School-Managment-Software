"""Binds service-port Protocols to concrete adapters for the active profile.

Standalone mode binds deterministic fakes for every dependency the target
module declares as a consumer. Integrated mode binds real providers. Production
refuses to bind a fake at all -- that refusal is the last line of defence
behind the CI configuration check, and it fires at startup rather than at first
request.

Does not handle: constructing the adapters. Each profile's settings module
supplies factories, so this registry stays free of module imports.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable, Mapping


class AdapterKind(enum.StrEnum):
    """Whether an adapter is a real provider or a test double.

    Every registered adapter must declare its kind. An adapter that forgets to
    is treated as FAKE, because the safe default is the one that fails loudly in
    production.
    """

    REAL = "real"
    FAKE = "fake"


class ProductionSafetyError(RuntimeError):
    """Raised when a production configuration selects a forbidden component.

    Covers fake adapters, development personas and demo fixtures. Never caught
    by application code: the process must not start.
    """


@dataclass(frozen=True, slots=True)
class PortBinding:
    """One port name bound to a factory, tagged with its adapter kind."""

    port_name: str
    kind: AdapterKind
    factory: Callable[[], object]


class PortRegistry:
    """The set of ports available to the running process.

    Ports are resolved by name (``"access"``, ``"platform"``). A module may only
    resolve a port it declared in ``ModuleRegistration.consumers``; the host
    passes that declaration in so an undeclared dependency fails at boot.
    """

    def __init__(
        self,
        *,
        app_env: str,
        declared_consumers: frozenset[str] = frozenset(),
    ) -> None:
        """Create an empty registry for one profile.

        ``app_env`` is compared against 'production' to decide whether fake
        adapters may be registered at all.
        """
        self._app_env = app_env
        self._declared_consumers = declared_consumers
        self._bindings: dict[str, PortBinding] = {}
        self._instances: dict[str, object] = {}

    @property
    def is_production(self) -> bool:
        """Return whether this registry is running a production profile."""
        return self._app_env == "production"

    def register(
        self,
        port_name: str,
        factory: Callable[[], object],
        *,
        kind: AdapterKind = AdapterKind.FAKE,
    ) -> None:
        """Bind a port to a factory.

        Raises ProductionSafetyError immediately when a FAKE adapter is
        registered under a production profile. Raises ValueError on a duplicate
        registration, because silent rebinding is how a real adapter gets
        replaced by a fake without anyone noticing.
        """
        if self.is_production and kind is AdapterKind.FAKE:
            raise ProductionSafetyError(
                f"refusing to bind fake adapter for port {port_name!r} "
                "under APP_ENV=production"
            )
        if port_name in self._bindings:
            raise ValueError(f"port {port_name!r} is already bound")
        self._bindings[port_name] = PortBinding(port_name, kind, factory)

    def resolve(self, port_name: str) -> object:
        """Return the singleton adapter instance for a port.

        Raises LookupError when the port was never bound, or when the running
        module did not declare it as a consumer. The second case is deliberate:
        reaching for an undeclared dependency is an architecture violation even
        if an adapter happens to be available.
        """
        if self._declared_consumers and port_name not in self._declared_consumers:
            raise LookupError(
                f"port {port_name!r} is not a declared consumer of this module; "
                "add it to ModuleRegistration.consumers"
            )
        if port_name not in self._bindings:
            raise LookupError(f"port {port_name!r} is not bound in this profile")
        if port_name not in self._instances:
            self._instances[port_name] = self._bindings[port_name].factory()
        return self._instances[port_name]

    def kinds(self) -> Mapping[str, AdapterKind]:
        """Return port name -> adapter kind, for /healthz and evidence output."""
        return {name: b.kind for name, b in self._bindings.items()}

    def assert_production_safe(
        self,
        *,
        dev_persona_mode: str,
        demo_fixtures_enabled: bool,
    ) -> None:
        """Fail hard if a production process is configured unsafely.

        Checks three things B00 requires production to refuse: fake adapters,
        an active development persona, and loaded demo fixtures.

        Does not handle: secret strength or TLS. Those are M14 deployment
        concerns, checked in infra, not here.
        """
        if not self.is_production:
            return
        fake_ports = sorted(
            name for name, b in self._bindings.items() if b.kind is AdapterKind.FAKE
        )
        problems: list[str] = []
        if fake_ports:
            problems.append(f"fake adapters bound: {fake_ports}")
        if dev_persona_mode not in ("", "off"):
            problems.append(f"DEV_PERSONA_MODE={dev_persona_mode!r} must be 'off'")
        if demo_fixtures_enabled:
            problems.append("demo fixtures are enabled")
        if problems:
            raise ProductionSafetyError(
                "production startup refused: " + "; ".join(problems)
            )
