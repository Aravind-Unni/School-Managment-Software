"""URL patterns for M03, mounted at its declared api_prefix.

Paths carry NO trailing slash, exactly as ``contracts/M03/openapi.json`` declares
them. The shared ``API_PATH_ROOT_PATTERN`` in contracts/registration.py requires
every declared ROOT to end in one, so registration.py declares ``timetables/``
while this file serves ``timetables``. That is the same mismatch M02 recorded and
resolved the same way: serving both forms produces duplicate operationIds and
fails ``spectacular --fail-on-warn``. Reconciling the two is a contract revision,
not a routing choice made here; see docs/modules/M03/handoff.md.
"""

from __future__ import annotations

from django.urls import path

from .api.views import (
    SessionDetailView,
    TimetableCollectionView,
    TimetableDetailView,
    TimetablePublishView,
    TimetableValidateView,
)
from .api.views_calendar import (
    CalendarExceptionCollectionView,
    CalendarExceptionDetailView,
    CalendarView,
    SessionCancellationView,
    SubstitutionCollectionView,
    SubstitutionDetailView,
    TeacherUnavailabilityCollectionView,
    TeacherUnavailabilityDetailView,
)
from .api.views_schedules import (
    CurrentTimetableView,
    StudentScheduleView,
    TeacherScheduleView,
)
from .api.views_slots import TeacherSlotsView

app_name = "timetable"


urlpatterns = [
    # Fixed segments must precede the UUID converter, or "current" would be
    # matched as a malformed timetable id and answered with a 404.
    path("timetables/current", CurrentTimetableView.as_view(), name="timetable-current"),
    path("timetables", TimetableCollectionView.as_view(), name="timetable-collection"),
    path(
        "timetables/<uuid:timetable_id>/validate",
        TimetableValidateView.as_view(),
        name="timetable-validate",
    ),
    path(
        "timetables/<uuid:timetable_id>/publish",
        TimetablePublishView.as_view(),
        name="timetable-publish",
    ),
    path(
        "timetables/<uuid:timetable_id>",
        TimetableDetailView.as_view(),
        name="timetable-detail",
    ),
    path("teacher-schedule", TeacherScheduleView.as_view(), name="teacher-schedule"),
    path("teacher-slots", TeacherSlotsView.as_view(), name="teacher-slots"),
    path("student-schedule", StudentScheduleView.as_view(), name="student-schedule"),
    path("calendar", CalendarView.as_view(), name="calendar"),
    path(
        "calendar-exceptions",
        CalendarExceptionCollectionView.as_view(),
        name="calendar-exception-collection",
    ),
    path(
        "calendar-exceptions/<uuid:exception_id>",
        CalendarExceptionDetailView.as_view(),
        name="calendar-exception-detail",
    ),
    path(
        "teacher-unavailability",
        TeacherUnavailabilityCollectionView.as_view(),
        name="teacher-unavailability-collection",
    ),
    path(
        "teacher-unavailability/<uuid:unavailability_id>",
        TeacherUnavailabilityDetailView.as_view(),
        name="teacher-unavailability-detail",
    ),
    path("substitutions", SubstitutionCollectionView.as_view(), name="substitution-collection"),
    path(
        "substitutions/<uuid:substitution_id>",
        SubstitutionDetailView.as_view(),
        name="substitution-detail",
    ),
    path(
        "timetable-sessions/<uuid:timetable_session_id>/cancellation",
        SessionCancellationView.as_view(),
        name="session-cancellation",
    ),
    path(
        "timetable-sessions/<uuid:timetable_session_id>",
        SessionDetailView.as_view(),
        name="session-detail",
    ),
]
