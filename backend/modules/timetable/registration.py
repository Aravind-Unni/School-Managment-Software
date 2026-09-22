"""M03's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

#: M03 mounts under the shared /api/v1/ root, as M01 and M02 do. Only the roots
#: it actually serves are claimed: the host refuses two modules claiming the same
#: root, so declaring one before serving it would block another module for no
#: reason.
REGISTRATION = ModuleRegistration(
    id="M03",
    slug="timetable",
    api_prefix="/api/v1/",
    #: The shared pattern requires a trailing slash on every declared ROOT. The
    #: frozen M03 OpenAPI publishes the same paths without one, so urls.py serves
    #: the bare form; the same reconciliation M02 recorded, carried here so the
    #: two modules do not diverge. See docs/modules/M03/handoff.md.
    api_path_roots=(
        "timetables/",
        "calendar/",
        "calendar-exceptions/",
        "teacher-unavailability/",
        "teacher-schedule/",
        "teacher-slots/",
        "student-schedule/",
        "substitutions/",
        "timetable-sessions/",
    ),
    django_app="modules.timetable",
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/timetable/editor",
            component="TimetablePlannerPage",
            nav_label_key="nav.timetable_editor",
            required_permission="timetable.edit",
        ),
        FrontendRoute(
            path="/timetable/substitutions",
            component="SubstitutionPage",
            nav_label_key="nav.timetable_substitutions",
            required_permission="timetable.substitute",
        ),
        FrontendRoute(
            path="/timetable/class",
            component="ClassSchedulePage",
            nav_label_key="nav.timetable_class",
            required_permission="timetable.read_section",
        ),
        FrontendRoute(
            path="/timetable/teacher",
            component="TeacherSchedulePage",
            nav_label_key="nav.timetable_teacher",
            required_permission="timetable.read_teacher",
        ),
        FrontendRoute(
            path="/timetable/student",
            component="StudentSchedulePage",
            nav_label_key="nav.timetable_student",
            required_permission="timetable.read_student",
        ),
    ),
    #: M03 IS the timetable, so it consumes no timetable port. It consumes Access
    #: for decisions, Registry for sections, rosters and teaching assignments,
    #: Platform for audit and outbox, and the clock. No notifications: publication
    #: notifies through an outbox row after commit, so an SMS outage cannot stop a
    #: timetable being published. No broker and no worker: this module owns no
    #: asynchronous work, and declaring one would claim capability it never tested.
    consumers=("access", "registry", "platform", "clock"),
    middleware=(),
    #: Nothing here is reachable without a session. A school's timetable is not
    #: public, and a class schedule names its teachers.
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="timetable_tables",
            callable_path="modules.timetable.health.check_tables",
        ),
        HealthCheck(
            name="calendar_resolvable",
            callable_path="modules.timetable.health.check_calendar_resolvable",
        ),
    ),
)
