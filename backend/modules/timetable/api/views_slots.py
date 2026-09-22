"""GET /teacher-slots: the periods a teacher actually has, for scheduling.

A class test belongs in a lesson the teacher already has with that class, so
the Assessments screen offers these periods rather than a free-text time.
Filter by ``section_id`` and ``subject_id``; the range is capped at 60 days.
Cancelled periods and days the school is closed are left out.

Does not handle: booking the period (the assessment carries the date itself,
so two tests in one period are the teacher's own business).
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from . import params, wire
from .deps import schedule_service

MAX_DAYS = 60


class TeacherSlotsView(APIView):
    """GET /teacher-slots."""

    @extend_schema(
        operation_id="list_teacher_slots",
        summary="The periods a teacher has with one class and subject",
        parameters=[
            OpenApiParameter("staff_id", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("from", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("to", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("section_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("subject_id", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        """Return the teacher's periods in the range, earliest first."""
        staff_id = params.required_uuid(request, "staff_id")
        from_date = params.required_date(request, "from")
        to_date = params.required_date(request, "to")
        if to_date < from_date or (to_date - from_date).days > MAX_DAYS:
            raise ValidationFailed("error.validation_failed")
        section = request.query_params.get("section_id")
        subject = request.query_params.get("subject_id")
        wanted_section = UUID(section) if section else None
        wanted_subject = UUID(subject) if subject else None

        service = schedule_service()
        items = []
        cursor = from_date
        while cursor <= to_date:
            day, sessions = service.teacher_day(
                request.school_context, staff_id=staff_id, on=cursor
            )
            if day.is_school_day:
                for view in sessions:
                    row = wire.session_to_wire(view)
                    if row["cancelled"]:
                        continue
                    if wanted_section and row["section_id"] != str(wanted_section):
                        continue
                    if wanted_subject and row["subject_id"] != str(wanted_subject):
                        continue
                    items.append(
                        {
                            "date": cursor.isoformat(),
                            "slot_code": row["slot_code"],
                            "starts_at_local": row["starts_at_local"],
                            "ends_at_local": row["ends_at_local"],
                            "section_id": row["section_id"],
                            "subject_id": row["subject_id"],
                            "timetable_session_id": row["timetable_session_id"],
                        }
                    )
            cursor += timedelta(days=1)
        return Response({"items": items, "next_cursor": None})
