"""Re-export wire helpers as api.deps for views."""

from __future__ import annotations

from ..services import wire


def projection_service():
    """Projection rebuild service."""
    return wire.projection_service()


def warning_service():
    """Warning service."""
    return wire.warning_service()


def intervention_service():
    """Intervention service."""
    return wire.intervention_service()


def dashboard_service():
    """Dashboard service."""
    return wire.dashboard_service()


def performance_port():
    """PerformancePort facade."""
    return wire.performance_port()
