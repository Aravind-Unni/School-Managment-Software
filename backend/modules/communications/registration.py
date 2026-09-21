"""M11's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration, ScheduledJob

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M11",
    slug="communications",
    api_prefix="/api/v1/",
    api_path_roots=("notices/", "messages/", "deliveries/", "sms/"),
    django_app="modules.communications",
    permission_prefixes=("notices.", "messages.", "sms."),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/notices",
            component="NoticeComposerPage",
            nav_label_key="nav.notices",
            required_permission="notices.create",
        ),
        FrontendRoute(
            path="/templates",
            component="TemplateEditorPage",
            nav_label_key="nav.templates",
            required_permission="messages.send",
        ),
        FrontendRoute(
            path="/deliveries",
            component="DeliveryDashboardPage",
            nav_label_key="nav.deliveries",
            required_permission="messages.read_status",
        ),
    ),
    consumers=("access", "registry", "platform", "clock"),
    middleware=(),
    public_paths=("sms/callback/",),
    scheduled_jobs=(
        ScheduledJob(
            name="communications.reconcile",
            cron="*/5 * * * *",
            task_path="modules.communications.tasks.reconcile_unknown",
        ),
    ),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="communications_tables",
            callable_path="modules.communications.health.tables_ready",
        ),
    ),
)
