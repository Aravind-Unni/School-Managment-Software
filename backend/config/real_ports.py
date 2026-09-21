"""Real (non-fake) port factories for the integrated profile.

Each factory imports the owning module's existing service assembler. The host
must not invent alternate domain implementations; it only binds what the owner
already ships.

Integrated mode refuses to start when a declared consumer has no factory here.
That is intentional: a silent FakeAccess / FakeRegistry would prove nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.conf import settings

from shared.ports.registry import AdapterKind

#: Port name -> zero-arg factory. Factories are lazy so Django apps are ready.
REAL_PORT_FACTORIES: dict[str, Callable[[], Any]] = {}


def _register(name: str, factory: Callable[[], Any]) -> None:
    """Record one real factory. Internal helper for module import side effects."""
    REAL_PORT_FACTORIES[name] = factory


def _bind_known_factories() -> None:
    """Populate REAL_PORT_FACTORIES once. Idempotent."""
    if REAL_PORT_FACTORIES:
        return

    def clock_factory():
        """Return the process clock from settings."""
        return settings.SCHOOL_CLOCK

    def access_factory():
        """Bind M01 AccessService as AccessPort."""
        from modules.access.api.deps import access_service

        return access_service()

    def platform_factory():
        """Bind M14 PlatformAdapter as PlatformPort."""
        from modules.platform.services.adapter import PlatformAdapter

        worker_available = bool(getattr(settings, "WORKER_AVAILABLE", False))
        return PlatformAdapter(worker_available=worker_available, clock=settings.SCHOOL_CLOCK)

    def registry_factory():
        """Bind M02 RegistryService as RegistryPort."""
        from modules.registry.api.deps import registry_port

        return registry_port()

    def timetable_factory():
        """Bind M03 TimetableService as TimetablePort."""
        from modules.timetable.api.deps import timetable_port

        return timetable_port()

    def attendance_factory():
        """Bind M04 AttendanceService as AttendancePort."""
        from modules.attendance.api.deps import attendance_port

        return attendance_port()

    def assessment_factory():
        """Bind M05 AssessmentService as AssessmentPort."""
        from modules.assessment.api.deps import assessment_port

        return assessment_port()

    def performance_factory():
        """Bind M06 PerformanceService as PerformancePort."""
        from modules.performance.api.deps import performance_port

        return performance_port()

    def fees_factory():
        """Bind M07 FeesService as FeesPort."""
        from modules.fees.api.deps import fees_port

        return fees_port()

    def files_factory():
        """Bind M12 FilesService as FilesPort."""
        from modules.files.api.deps import files_port

        return files_port()

    def object_storage_factory():
        """Bind S3-compatible ObjectStoragePort with grant enforcement."""
        from config.object_storage import S3ObjectStorageAdapter

        return S3ObjectStorageAdapter()

    def notifications_factory():
        """Bind controlled SMS-sandbox NotificationPort (no real gateway)."""
        from config.sandbox_notifications import ControlledSandboxNotifications

        return ControlledSandboxNotifications()

    _register("clock", clock_factory)
    _register("access", access_factory)
    _register("platform", platform_factory)
    _register("registry", registry_factory)
    _register("timetable", timetable_factory)
    _register("attendance", attendance_factory)
    _register("assessment", assessment_factory)
    _register("performance", performance_factory)
    _register("fees", fees_factory)
    _register("files", files_factory)
    _register("object_storage", object_storage_factory)
    _register("notifications", notifications_factory)


def build_real_providers(required_ports: frozenset[str]) -> dict[str, tuple]:
    """Return ``{port: (factory, AdapterKind.REAL)}`` for every required port.

    Raises ConfigurationError naming missing providers rather than falling back
    to a fake. Does not handle: partial integration with intentional fakes.
    """
    from config import env

    _bind_known_factories()
    missing = sorted(required_ports - set(REAL_PORT_FACTORIES))
    if missing:
        raise env.ConfigurationError(
            "integrated mode has no real provider for ports "
            f"{missing}; finish the owning module's port adapter first, or run "
            "the standalone profile instead"
        )
    # Probe registry specially: ImportError means M02 RegistryPort is absent.
    if "registry" in required_ports:
        try:
            REAL_PORT_FACTORIES["registry"]
            # Import path only — actual construction happens at resolve time.
            import importlib

            importlib.import_module("modules.registry.api.deps")
            if not hasattr(
                importlib.import_module("modules.registry.api.deps"), "registry_port"
            ):
                raise env.ConfigurationError(
                    "integrated mode requires modules.registry.api.deps.registry_port; "
                    "M02 RegistryPort is not implemented yet"
                )
        except ModuleNotFoundError as exc:
            raise env.ConfigurationError(
                "integrated mode requires M02 RegistryPort "
                f"({exc.name} missing); complete registry steps 2-3 first"
            ) from exc

    return {
        name: (REAL_PORT_FACTORIES[name], AdapterKind.REAL) for name in sorted(required_ports)
    }


def required_ports_for(registrations: list) -> frozenset[str]:
    """Union every approved registration's consumers."""
    names: set[str] = set()
    for registration in registrations:
        names.update(getattr(registration, "consumers", ()) or ())
    return frozenset(names)
