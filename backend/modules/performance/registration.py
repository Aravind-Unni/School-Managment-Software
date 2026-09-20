"""M06's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration, ScheduledJob

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M06",
    slug="performance",
    api_prefix="/api/v1/",
    api_path_roots=(
        "performance/",
        "warning-rules/",
        "warnings/",
        "interventions/",
        "meetings/",
    ),
    django_app="modules.performance",
    permission_prefixes=(
        "performance.",
        "warnings.",
        "interventions.",
        "meetings.",
        "observations.",
    ),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/performance",
            component="StudentDashboardPage",
            nav_label_key="nav.performance_dashboard",
            required_permission="performance.read",
        ),
        FrontendRoute(
            path="/performance/at-risk",
            component="AtRiskListPage",
            nav_label_key="nav.performance_at_risk",
            required_permission="warnings.manage",
        ),
        FrontendRoute(
            path="/performance/interventions",
            component="InterventionListPage",
            nav_label_key="nav.performance_interventions",
            required_permission="interventions.manage",
        ),
    ),
    consumers=("access", "registry", "assessment", "attendance", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(
        ScheduledJob(
            name="performance.reconcile_projections",
            cron="15 2 * * *",
            task_path="modules.performance.tasks.reconcile_projections",
        ),
    ),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="performance_tables",
            callable_path="modules.performance.health.tables_ready",
        ),
    ),
)
