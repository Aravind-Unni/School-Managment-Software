"""M08's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M08",
    slug="transport",
    api_prefix="/api/v1/",
    api_path_roots=(
        "buses/",
        "bus-participations/",
        "bus-billing-runs/",
        "bus-participants/",
        "bus-billing-reconciliation/",
        "bus-adjustments/",
        "bus-billing-requests/",
    ),
    django_app="modules.transport",
    permission_prefixes=("transport.",),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/transport",
            component="TransportParticipantsPage",
            nav_label_key="nav.transport",
            required_permission="transport.read",
        ),
        FrontendRoute(
            path="/transport/billing",
            component="TransportBillingPage",
            nav_label_key="nav.transport_billing",
            required_permission="transport.bill",
        ),
    ),
    consumers=("access", "registry", "fees", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="transport_tables",
            callable_path="modules.transport.health.tables_ready",
        ),
    ),
)
