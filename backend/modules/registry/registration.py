"""M02's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

#: M02 mounts under the shared /api/v1/ root. Only the roots step 1 serves are
#: claimed: the host refuses two modules claiming the same root, so declaring a
#: root before serving it would block another module for no reason.
REGISTRATION = ModuleRegistration(
    id="M02",
    slug="registry",
    api_prefix="/api/v1/",
    #: The shared pattern requires a trailing slash on every root. The frozen
    #: M02 OpenAPI publishes the same paths without one, so urls.py serves both
    #: forms; see its module docstring. This declares ownership of the
    #: namespaces, which is what the host's collision check uses them for.
    api_path_roots=(
        "school-config/",
        "academic-years/",
        "terms/",
        "standards/",
        "sections/",
        "subjects/",
        "students/",
        "guardians/",
        "guardian-links/",
        "staff/",
        "teaching-assignments/",
        "subject-offerings/",
        "enrolments/",
        "subject-enrolments/",
    ),
    django_app="modules.registry",
    permission_prefixes=("registry.", "students.", "guardians.", "staff.", "year."),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/registry/setup",
            component="SchoolSetupPage",
            nav_label_key="nav.registry_setup",
            required_permission="registry.manage",
        ),
        FrontendRoute(
            path="/registry/students",
            component="StudentDirectoryPage",
            nav_label_key="nav.students",
            required_permission="students.read",
        ),
        FrontendRoute(
            path="/registry/students/:studentId",
            component="StudentProfilePage",
            nav_label_key=None,
            required_permission="students.read",
        ),
    ),
    #: M02 IS the Registry, so it does NOT consume the registry port. It
    #: consumes Access for decisions, Platform for audit and outbox, and the
    #: clock. No broker, worker or object storage: step 1 needs none, and
    #: declaring one would claim capability this module has not tested.
    consumers=("access", "platform", "clock"),
    middleware=(),
    #: Nothing here is reachable without a session. A school's pupil directory
    #: has no public surface.
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="registry_tables",
            callable_path="modules.registry.health.check_tables",
        ),
        HealthCheck(
            name="school_config_installed",
            callable_path="modules.registry.health.check_school_config_installed",
        ),
    ),
)
