"""M10's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M10",
    slug="alumni",
    api_prefix="/api/v1/",
    api_path_roots=("alumni/",),
    django_app="modules.alumni",
    permission_prefixes=("alumni.",),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/alumni/candidates",
            component="AlumniCandidatesPage",
            nav_label_key="nav.alumni_candidates",
            required_permission="alumni.review",
        ),
        FrontendRoute(
            path="/alumni",
            component="AlumniDirectoryPage",
            nav_label_key="nav.alumni_directory",
            required_permission="alumni.read",
        ),
        FrontendRoute(
            path="/alumni/profile",
            component="AlumniProfilePage",
            nav_label_key="nav.alumni_profile",
            required_permission="alumni.manage",
        ),
        FrontendRoute(
            path="/alumni/export",
            component="AlumniExportPage",
            nav_label_key="nav.alumni_export",
            required_permission="alumni.export",
        ),
    ),
    consumers=("access", "registry", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="alumni_tables",
            callable_path="modules.alumni.health.tables_ready",
        ),
    ),
)
