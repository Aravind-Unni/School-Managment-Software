"""M12's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration, ScheduledJob

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M12",
    slug="files",
    api_prefix="/api/v1/",
    api_path_roots=("uploads/", "files/", "quarantine/", "file-bytes/"),
    django_app="modules.files",
    permission_prefixes=("files.",),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/files/review",
            component="FileReviewPage",
            nav_label_key="nav.files_review",
            required_permission="files.review_quality",
        ),
        FrontendRoute(
            path="/files/view",
            component="ParentFileViewerPage",
            nav_label_key="nav.files_view",
            required_permission="files.read",
        ),
    ),
    consumers=("access", "platform", "clock"),
    middleware=(),
    public_paths=("quarantine/", "file-bytes/"),
    scheduled_jobs=(
        ScheduledJob(
            name="files.cleanup_orphans",
            cron="0 * * * *",
            task_path="modules.files.tasks.cleanup_orphans",
        ),
        ScheduledJob(
            name="files.economical_purge",
            cron="0 3 * * *",
            task_path="modules.files.tasks.cleanup_orphans",
        ),
    ),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="files_tables",
            callable_path="modules.files.health.tables_ready",
        ),
    ),
)
