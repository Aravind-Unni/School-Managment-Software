"""POST /exam-schedules and GET /assessment-calendar.

``POST /exam-schedules`` sets a term exam for many classes at once (school-wide
staff only). ``GET /assessment-calendar`` lists tests and exams scheduled in a
date range for a pupil (``student_id``), a class (``section_id``), or, with
neither, the caller's own classes (every class for school-wide staff).

Does not handle: holidays (the timetable's calendar has those).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from ..services.schedule import ScheduleService
from . import deps
from .views import validated


class PaperInput(serializers.Serializer):
    """One exam paper: a subject on a date (and start time)."""

    subject_id = serializers.UUIDField()
    date = serializers.DateField()
    time = serializers.RegexField(regex=r"^\d{2}:\d{2}$", required=False, allow_null=True)
    max_score = serializers.IntegerField(min_value=1, max_value=1000, required=False)


class ExamScheduleRequest(serializers.Serializer):
    """Body of POST /exam-schedules."""

    term_id = serializers.UUIDField()
    title = serializers.CharField(max_length=120)
    section_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    papers = PaperInput(many=True, allow_empty=False)


def schedule_service() -> ScheduleService:
    """Assemble the schedule service from the profile's ports."""
    create = deps.create_service()
    return ScheduleService(
        gate=create.gate, registry=create.registry, create=create, clock=create.clock
    )


class ExamScheduleView(APIView):
    """POST /exam-schedules."""

    @extend_schema(
        operation_id="schedule_exams", request=ExamScheduleRequest, responses={200: dict}
    )
    def post(self, request: Request) -> Response:
        """Create the exam's papers for every chosen class that takes each subject."""
        body = validated(ExamScheduleRequest, request.data)
        result = schedule_service().schedule_exams(
            request.school_context,
            term_id=body["term_id"],
            title=body["title"],
            section_ids=body["section_ids"],
            papers=[dict(paper) for paper in body["papers"]],
        )
        return Response(result)


class AssessmentCalendarView(APIView):
    """GET /assessment-calendar."""

    @extend_schema(
        operation_id="get_assessment_calendar",
        parameters=[
            OpenApiParameter("from", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("to", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("student_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("section_id", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        """Return scheduled tests and exams in the range, earliest first."""
        params = request.query_params
        if not params.get("from") or not params.get("to"):
            raise ValidationFailed("error.validation_failed")
        items = schedule_service().calendar(
            request.school_context,
            from_date=date.fromisoformat(params["from"]),
            to_date=date.fromisoformat(params["to"]),
            student_id=UUID(params["student_id"]) if params.get("student_id") else None,
            section_id=UUID(params["section_id"]) if params.get("section_id") else None,
        )
        return Response({"items": items, "next_cursor": None})
