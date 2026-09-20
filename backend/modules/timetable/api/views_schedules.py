"""M03 REST endpoints: the read-only class, teacher and pupil schedules.

All three come through the same reader as the service port, because the packet
requires every school view to use one effective source.

Split from ``views.py`` only to stay inside the architecture check's file-size
ceiling.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import params, wire
from .deps import schedule_service
from .serializers import SectionDayResponse, StudentDayResponse, TeacherDayResponse
from .views import COMMON_ERRORS


class CurrentTimetableView(APIView):
    """Read one section's effective schedule for a date."""

    @extend_schema(
        operation_id="get_current_timetable",
        summary="Read the effective schedule for one section on one date",
        parameters=[
            OpenApiParameter("section_id", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("student_id", str, OpenApiParameter.QUERY),
        ],
        responses={200: SectionDayResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the published effective periods, with the day's overrides applied.

        ``student_id`` is how a pupil or guardian proves their link to the
        section; staff with a dated teaching assignment need not send one.
        """
        view = schedule_service().section_day(
            request.school_context,
            section_id=params.required_uuid(request, "section_id"),
            on=params.required_date(request, "date"),
            student_id=params.optional_uuid(request, "student_id"),
        )
        return Response(
            {
                "section_id": str(view.section_id),
                "date": view.date.isoformat(),
                "is_school_day": view.day.is_school_day,
                "reason_key": view.day.reason_key,
                "timetable_id": str(view.timetable.id) if view.timetable else None,
                "timetable_version": view.timetable.version if view.timetable else None,
                "sessions": [wire.session_to_wire(session) for session in view.sessions],
            }
        )


class TeacherScheduleView(APIView):
    """Read one staff member's dated schedule."""

    @extend_schema(
        operation_id="get_teacher_schedule",
        summary="Read one teacher's dated schedule",
        parameters=[
            OpenApiParameter("staff_id", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date", str, OpenApiParameter.QUERY, required=True),
        ],
        responses={200: TeacherDayResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the periods a teacher is assigned to or is covering that day."""
        staff_id = params.required_uuid(request, "staff_id")
        on = params.required_date(request, "date")
        day, sessions = schedule_service().teacher_day(
            request.school_context, staff_id=staff_id, on=on
        )
        return Response(
            {
                "staff_id": str(staff_id),
                "date": on.isoformat(),
                "is_school_day": day.is_school_day,
                "reason_key": day.reason_key,
                "sessions": [wire.session_to_wire(session) for session in sessions],
            }
        )


class StudentScheduleView(APIView):
    """Read one pupil's dated schedule."""

    @extend_schema(
        operation_id="get_student_schedule",
        summary="Read one pupil's dated schedule",
        parameters=[
            OpenApiParameter("student_id", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("date", str, OpenApiParameter.QUERY, required=True),
        ],
        responses={200: StudentDayResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the section's sessions, each marked with the pupil's enrolment.

        A pupil who does not take the subject sees a free period rather than a
        lesson they would later be marked absent from.
        """
        day = schedule_service().student_day(
            request.school_context,
            student_id=params.required_uuid(request, "student_id"),
            on=params.required_date(request, "date"),
        )
        return Response(
            {
                "student_id": str(day.student_id),
                "section_id": str(day.section_id),
                "date": day.date.isoformat(),
                "is_school_day": day.day.is_school_day,
                "reason_key": day.day.reason_key,
                "sessions": [
                    {"session": wire.session_to_wire(session), "enrolled": enrolled}
                    for session, enrolled in day.sessions
                ],
            }
        )
