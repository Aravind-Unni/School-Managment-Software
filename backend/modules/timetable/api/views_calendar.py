"""M03 REST endpoints: the calendar, unavailability, substitutions, cancellation.

Split from ``views.py`` only to stay inside the architecture check's file-size
ceiling. Same rule applies: parse, delegate, render, decide nothing.
"""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import params, wire
from .deps import calendar_service, substitution_service
from .serializers import (
    CalendarExceptionPageResponse,
    CalendarExceptionRequest,
    CalendarExceptionResponse,
    CalendarResponse,
    PeriodSessionResponse,
    SessionCancellationRequest,
    SubstitutionPageResponse,
    SubstitutionRequest,
    SubstitutionResponse,
    TeacherUnavailablePageResponse,
    TeacherUnavailableRequest,
    TeacherUnavailableResponse,
    UpdateCalendarExceptionRequest,
    UpdateSubstitutionRequest,
    UpdateTeacherUnavailableRequest,
)
from .views import COMMON_ERRORS, CURSOR_PARAMS, validated
from .views_schedules import with_names

DATE_RANGE_PARAMS = [
    OpenApiParameter("from_date", str, OpenApiParameter.QUERY),
    OpenApiParameter("to_date", str, OpenApiParameter.QUERY),
]


class CalendarView(APIView):
    """Read the school calendar over a bounded range."""

    @extend_schema(
        operation_id="get_calendar",
        summary="Read the school calendar over a range",
        parameters=DATE_RANGE_PARAMS,
        responses={200: CalendarResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one answer per date. The weekly pattern is the school's own."""
        from_date = params.required_date(request, "from_date")
        to_date = params.required_date(request, "to_date")
        days = calendar_service().days(
            request.school_context, from_date=from_date, to_date=to_date
        )
        return Response(
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "days": [wire.calendar_day_to_wire(day) for day in days],
            }
        )


class CalendarExceptionCollectionView(APIView):
    """List and record calendar exceptions."""

    @extend_schema(
        operation_id="list_calendar_exceptions",
        summary="List calendar exceptions",
        parameters=[
            *DATE_RANGE_PARAMS,
            OpenApiParameter("kind", str, OpenApiParameter.QUERY),
            *CURSOR_PARAMS,
        ],
        responses={200: CalendarExceptionPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the school's exceptions, oldest first."""
        queryset = calendar_service().list_exceptions(
            request.school_context,
            from_date=params.optional_date(request, "from_date"),
            to_date=params.optional_date(request, "to_date"),
            kind=params.optional_choice(request, "kind", ("holiday", "exam", "event")),
        )
        return Response(
            params.paginate(
                request,
                queryset,
                order_by=("date", "id"),
                cursor_fields=lambda row: {
                    "date": row.date.isoformat(),
                    "id": str(row.id),
                },
                serialise=wire.exception_to_wire,
            )
        )

    @extend_schema(
        operation_id="create_calendar_exception",
        summary="Record a calendar exception",
        request=CalendarExceptionRequest,
        responses={201: CalendarExceptionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Record one exception, reinstating a withdrawn one for the same date."""
        body = validated(CalendarExceptionRequest, request.data)
        row = calendar_service().create_exception(
            request.school_context,
            on=body["date"],
            kind=body["kind"],
            reason_key=body["reason_key"],
        )
        return Response(wire.exception_to_wire(row), status=201)


class CalendarExceptionDetailView(APIView):
    """Amend or withdraw one calendar exception."""

    @extend_schema(
        operation_id="update_calendar_exception",
        summary="Amend or withdraw a calendar exception",
        request=UpdateCalendarExceptionRequest,
        responses={200: CalendarExceptionResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, exception_id: UUID) -> Response:
        """Update under expected_version. Withdrawn, never deleted."""
        body = validated(UpdateCalendarExceptionRequest, request.data)
        row = calendar_service().update_exception(
            request.school_context,
            exception_id=exception_id,
            kind=body["kind"],
            reason_key=body["reason_key"],
            withdrawn=body["withdrawn"],
            expected_version=body["expected_version"],
        )
        return Response(wire.exception_to_wire(row))


class TeacherUnavailabilityCollectionView(APIView):
    """List and record staff unavailability."""

    @extend_schema(
        operation_id="list_teacher_unavailability",
        summary="List unavailability intervals",
        parameters=[
            OpenApiParameter("staff_id", str, OpenApiParameter.QUERY),
            *DATE_RANGE_PARAMS,
            *CURSOR_PARAMS,
        ],
        responses={200: TeacherUnavailablePageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return recorded windows, earliest first."""
        queryset = calendar_service().list_unavailability(
            request.school_context,
            staff_id=params.optional_uuid(request, "staff_id"),
            from_date=params.optional_date(request, "from_date"),
            to_date=params.optional_date(request, "to_date"),
        )
        return Response(
            params.paginate(
                request,
                queryset,
                order_by=("starts_at", "id"),
                cursor_fields=lambda row: {
                    "starts_at": row.starts_at.isoformat(),
                    "id": str(row.id),
                },
                serialise=wire.unavailability_to_wire,
            )
        )

    @extend_schema(
        operation_id="create_teacher_unavailability",
        summary="Record that a teacher cannot teach over an interval",
        request=TeacherUnavailableRequest,
        responses={201: TeacherUnavailableResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Record one half-open interval."""
        body = validated(TeacherUnavailableRequest, request.data)
        row = calendar_service().create_unavailability(
            request.school_context,
            staff_id=body["staff_id"],
            starts_at=body["starts_at"],
            ends_at=body["ends_at"],
            reason_key=body["reason_key"],
        )
        return Response(wire.unavailability_to_wire(row), status=201)


class TeacherUnavailabilityDetailView(APIView):
    """Amend or withdraw one unavailability interval."""

    @extend_schema(
        operation_id="update_teacher_unavailability",
        summary="Amend or withdraw an unavailability interval",
        request=UpdateTeacherUnavailableRequest,
        responses={200: TeacherUnavailableResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, unavailability_id: UUID) -> Response:
        """Update under expected_version."""
        body = validated(UpdateTeacherUnavailableRequest, request.data)
        row = calendar_service().update_unavailability(
            request.school_context,
            unavailability_id=unavailability_id,
            starts_at=body["starts_at"],
            ends_at=body["ends_at"],
            reason_key=body["reason_key"],
            withdrawn=body["withdrawn"],
            expected_version=body["expected_version"],
        )
        return Response(wire.unavailability_to_wire(row))


class SubstitutionCollectionView(APIView):
    """List and assign dated substitutions."""

    @extend_schema(
        operation_id="list_substitutions",
        summary="List substitutions",
        parameters=[
            OpenApiParameter("date", str, OpenApiParameter.QUERY),
            OpenApiParameter("section_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("teacher_id", str, OpenApiParameter.QUERY),
            *CURSOR_PARAMS,
        ],
        responses={200: SubstitutionPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return substitutions matching the filters, earliest first."""
        queryset = substitution_service().listing(
            request.school_context,
            on=params.optional_date(request, "date"),
            section_id=params.optional_uuid(request, "section_id"),
            teacher_id=params.optional_uuid(request, "teacher_id"),
        )
        return Response(
            params.paginate(
                request,
                queryset,
                order_by=("date", "id"),
                cursor_fields=lambda row: {
                    "date": row.date.isoformat(),
                    "id": str(row.id),
                },
                serialise=wire.substitution_to_wire,
            )
        )

    @extend_schema(
        operation_id="create_substitution",
        summary="Assign a substitute to one dated period",
        request=SubstitutionRequest,
        responses={201: SubstitutionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Assign a dated substitute whose authority expires."""
        body = validated(SubstitutionRequest, request.data)
        row = substitution_service().assign(
            request.school_context,
            on=body["date"],
            slot_id=body["slot_id"],
            teacher_id=body["teacher_id"],
            reason=body["reason"],
            valid_until=body["valid_until"],
        )
        return Response(wire.substitution_to_wire(row), status=201)


class SubstitutionDetailView(APIView):
    """Withdraw one substitution."""

    @extend_schema(
        operation_id="update_substitution",
        summary="Withdraw a substitution",
        request=UpdateSubstitutionRequest,
        responses={200: SubstitutionResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, substitution_id: UUID) -> Response:
        """Withdraw under expected_version."""
        body = validated(UpdateSubstitutionRequest, request.data)
        row = substitution_service().withdraw(
            request.school_context,
            substitution_id=substitution_id,
            withdrawn=body["withdrawn"],
            expected_version=body["expected_version"],
        )
        return Response(wire.substitution_to_wire(row))


class SessionCancellationView(APIView):
    """Cancel or restore one dated period."""

    @extend_schema(
        operation_id="set_session_cancellation",
        summary="Cancel or restore one dated period",
        request=SessionCancellationRequest,
        responses={200: PeriodSessionResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, timetable_session_id: UUID) -> Response:
        """Set the cancellation state. It creates no timetable revision."""
        body = validated(SessionCancellationRequest, request.data)
        session = substitution_service().set_cancellation(
            request.school_context,
            session_id=timetable_session_id,
            cancelled=body["cancelled"],
            reason_key=body["reason_key"],
            expected_version=body["expected_version"],
        )
        # The frozen PeriodSessionDTO is a closed shape and carries no version,
        # so nothing is added to it here. A client tracks the cancellation
        # record's version from its own successful writes: the first cancel
        # leaves it at 1, each further change adds one. A client that did NOT
        # make those writes cannot learn it -- a real gap in the frozen contract,
        # recorded in docs/modules/M03/handoff.md rather than patched around.
        return Response(with_names(request.school_context, [wire.session_to_wire(session)])[0])
