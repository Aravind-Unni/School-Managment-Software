"""M14's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration, ScheduledJob

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M14",
    slug="platform",
    api_prefix="/api/v1/",
    api_path_roots=("health/", "jobs/", "audit/", "operations/"),
    django_app="modules.platform",
    permission_prefixes=("platform.", "jobs.", "audit.", "backups."),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/platform/jobs",
            component="OperatorJobsPage",
            nav_label_key="nav.platform_jobs",
            required_permission="jobs.read",
        ),
        FrontendRoute(
            path="/platform/audit",
            component="AuditViewerPage",
            nav_label_key="nav.platform_audit",
            required_permission="audit.read",
        ),
        FrontendRoute(
            path="/platform/backups",
            component="BackupReportsPage",
            nav_label_key="nav.platform_backups",
            required_permission="backups.manage",
        ),
    ),
    consumers=("access", "clock", "object_storage", "platform"),
    middleware=(),
    public_paths=("health/live",),
    scheduled_jobs=(
        ScheduledJob(
            name="platform.dispatch_outbox",
            cron="*/1 * * * *",
            task_path="modules.platform.tasks.dispatch_outbox",
        ),
        ScheduledJob(
            name="platform.monitor_backup_age",
            cron="*/15 * * * *",
            task_path="modules.platform.tasks.monitor_backup_age",
        ),
    ),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="platform_tables",
            callable_path="modules.platform.health.tables_ready",
        ),
    ),
)
