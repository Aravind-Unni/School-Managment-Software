"""M13's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration, ScheduledJob

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M13",
    slug="exchange",
    api_prefix="/api/v1/",
    api_path_roots=(
        "imports/",
        "import-templates/",
        "exports/",
        "reportcards/",
        "reports/",
    ),
    django_app="modules.exchange",
    permission_prefixes=("imports.", "reports.", "reportcards."),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/imports",
            component="ImportCentrePage",
            nav_label_key="nav.imports",
            required_permission="imports.validate",
        ),
        FrontendRoute(
            path="/exports",
            component="ExportCentrePage",
            nav_label_key="nav.exports",
            required_permission="reports.export",
        ),
        FrontendRoute(
            path="/reports",
            component="ReportCentrePage",
            nav_label_key="nav.reports",
            required_permission="reports.read",
        ),
        FrontendRoute(
            path="/report-cards",
            component="ReportCardPreviewPage",
            nav_label_key="nav.report_cards",
            required_permission="reportcards.generate",
        ),
    ),
    consumers=(
        "access",
        "registry",
        "assessment",
        "attendance",
        "fees",
        "files",
        "platform",
        "clock",
    ),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(
        ScheduledJob(
            name="exchange.cleanup_stale_imports",
            cron="0 2 * * *",
            task_path="modules.exchange.tasks.cleanup_stale_imports",
        ),
        ScheduledJob(
            name="exchange.audit_expired_artifacts",
            cron="30 2 * * *",
            task_path="modules.exchange.tasks.audit_expired_artifacts",
        ),
    ),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="exchange_tables",
            callable_path="modules.exchange.health.tables_ready",
        ),
    ),
)
