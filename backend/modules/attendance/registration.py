"""M04's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M04",
    slug="attendance",
    api_prefix="/api/v1/",
    api_path_roots=("attendance/",),
    django_app="modules.attendance",
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/attendance",
            component="AttendanceTodayPage",
            nav_label_key="nav.attendance",
            required_permission="attendance.read",
        ),
        FrontendRoute(
            path="/attendance/session/:sessionId",
            component="AttendanceSessionPage",
            required_permission="attendance.mark",
        ),
    ),
    consumers=("access", "registry", "timetable", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="attendance_tables",
            callable_path="modules.attendance.health.tables_ready",
        ),
    ),
)
