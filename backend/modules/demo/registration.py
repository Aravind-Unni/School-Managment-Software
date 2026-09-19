"""The demo module's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

#: M00's registration. Declares the four ports the demo exercises, so that
#: resolving any other port fails at boot.
REGISTRATION = ModuleRegistration(
    id="M00",
    slug="demo",
    api_prefix="/api/demo/",
    django_app="modules.demo",
    frontend_routes=(
        FrontendRoute(
            path="/demo",
            component="DemoNotesPage",
            nav_label_key="nav.demo",
            required_permission="demo.list_notes",
        ),
    ),
    permission_codes=(
        "demo.list_notes",
        "demo.read_note",
        "demo.write_note",
    ),
    consumers=("access", "registry", "platform", "clock"),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(name="demo_table", callable_path="modules.demo.health.check_table"),
    ),
)
