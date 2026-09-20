"""M09's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M09",
    slug="library",
    api_prefix="/api/v1/",
    api_path_roots=("library/",),
    django_app="modules.library",
    permission_prefixes=("library.",),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/library",
            component="LibraryCataloguePage",
            nav_label_key="nav.library",
            required_permission="library.read_own",
        ),
        FrontendRoute(
            path="/library/desk",
            component="LibraryDeskPage",
            nav_label_key="nav.library_desk",
            required_permission="library.issue",
        ),
        FrontendRoute(
            path="/library/overdues",
            component="LibraryOverduesPage",
            nav_label_key="nav.library_overdues",
            required_permission="library.read_overdues",
        ),
    ),
    consumers=("access", "registry", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="library_tables",
            callable_path="modules.library.health.tables_ready",
        ),
    ),
)
