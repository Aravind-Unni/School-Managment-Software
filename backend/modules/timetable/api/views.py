"""M03 REST endpoints: revisions, validation, publication and one session.

Views are thin: parse, delegate, render. They hold no authorisation logic of
their own, so an import or an export calling the same service gets the same
decision as an HTTP caller.

Does not handle: the calendar, substitutions or the read-only schedule views.
Those are ``views_calendar.py`` and ``views_schedules.py``, split only to keep
each file inside the architecture check's size ceiling.
"""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import params, wire
from .deps import draft_service, publication_service, timetable_port
from .serializers import (
    CreateTimetableRequest,
    ErrorEnvelopeResponse,
    PeriodSessionResponse,
    PublishRequest,
    PublishResultResponse,
    ReplaceTimetableRequest,
    TimetablePageResponse,
    TimetableVersionResponse,
    ValidationReportResponse,
)

#: Error responses every endpoint in this module can return. Declared once so a
#: generated client carries the full error surface, not just the happy path.
COMMON_ERRORS = {
    400: OpenApiResponse(ErrorEnvelopeResponse, "Client asserted its own identity."),
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated, or 2FA too old."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied in this scope."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible to you."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}

CURSOR_PARAMS = [
    OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
    OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
]


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


class TimetableCollectionView(APIView):
    """List revisions and create a draft."""

    @extend_schema(
        operation_id="list_timetables",
        summary="List timetable versions",
        parameters=[
            OpenApiParameter("year_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("state", str, OpenApiParameter.QUERY),
            *CURSOR_PARAMS,
        ],
        responses={200: TimetablePageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return every revision, current and historical, newest range first."""
        queryset = draft_service().listing(
            request.school_context,
            year_id=params.optional_uuid(request, "year_id"),
            state=params.optional_choice(
                request, "state", ("draft", "published", "superseded")
            ),
        )
        return Response(
            params.paginate(
                request,
                queryset,
                order_by=("-effective_from", "id"),
                cursor_fields=lambda row: {
                    "effective_from": row.effective_from.isoformat(),
                    "id": str(row.id),
                },
                serialise=wire.timetable_summary_to_wire,
            )
        )

    @extend_schema(
        operation_id="create_timetable",
        summary="Create a draft timetable version",
        request=CreateTimetableRequest,
        responses={201: TimetableVersionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a draft revision with its whole grid, and return it."""
        body = validated(CreateTimetableRequest, request.data)
        version = draft_service().create(
            request.school_context,
            year_id=body["year_id"],
            effective_from=body["effective_from"],
            effective_to=body["effective_to"],
            periods=list(body["periods"]),
            slots=list(body["slots"]),
        )
        return Response(wire.timetable_to_wire(version), status=201)


class TimetableDetailView(APIView):
    """Read one revision, or replace a draft's grid."""

    @extend_schema(
        operation_id="get_timetable",
        summary="Read one timetable version with its grid",
        responses={200: TimetableVersionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, timetable_id: UUID) -> Response:
        """Return one revision. A superseded one is still readable."""
        version = draft_service().get(request.school_context, timetable_id=timetable_id)
        return Response(wire.timetable_to_wire(version))

    @extend_schema(
        operation_id="replace_timetable",
        summary="Replace a draft's grid",
        request=ReplaceTimetableRequest,
        responses={200: TimetableVersionResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, timetable_id: UUID) -> Response:
        """Replace a draft's whole week under expected_version."""
        body = validated(ReplaceTimetableRequest, request.data)
        version = draft_service().replace(
            request.school_context,
            timetable_id=timetable_id,
            effective_from=body["effective_from"],
            effective_to=body["effective_to"],
            periods=list(body["periods"]),
            slots=list(body["slots"]),
            expected_version=body["expected_version"],
        )
        return Response(wire.timetable_to_wire(version))


class TimetableValidateView(APIView):
    """Report the conflicts in a draft."""

    @extend_schema(
        operation_id="validate_timetable",
        summary="List the conflicts in a draft",
        request=None,
        responses={200: ValidationReportResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, timetable_id: UUID) -> Response:
        """Return every conflict. Read-only: it reserves nothing."""
        version, conflicts = publication_service().validate(
            request.school_context, timetable_id=timetable_id
        )
        return Response(
            {
                "timetable_id": str(version.id),
                "version": version.version,
                "conflicts": [wire.conflict_to_wire(conflict) for conflict in conflicts],
            }
        )


class TimetablePublishView(APIView):
    """Make a draft the school's effective schedule."""

    @extend_schema(
        operation_id="publish_timetable",
        summary="Publish a draft",
        request=PublishRequest,
        responses={200: PublishResultResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, timetable_id: UUID) -> Response:
        """Publish under expected_version, refusing while a conflict blocks."""
        body = validated(PublishRequest, request.data)
        result = publication_service().publish(
            request.school_context,
            timetable_id=timetable_id,
            expected_version=body["expected_version"],
        )
        version = result.version
        return Response(
            {
                "id": str(version.id),
                "school_id": str(version.school_id),
                "version": version.version,
                "state": version.state,
                "effective_from": version.effective_from.isoformat(),
                "effective_to": (
                    version.effective_to.isoformat() if version.effective_to else None
                ),
                "superseded_timetable_id": (
                    str(result.superseded_timetable_id)
                    if result.superseded_timetable_id
                    else None
                ),
            }
        )


class SessionDetailView(APIView):
    """Read one dated period by its stable identity."""

    @extend_schema(
        operation_id="get_session",
        summary="Read one dated period by its stable identity",
        responses={200: PeriodSessionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, timetable_session_id: UUID) -> Response:
        """Return one dated period, or 404 when it does not run."""
        service = timetable_port()
        dto = service.get_session(request.school_context, timetable_session_id)
        return Response(_session_dto_to_wire(dto))


def _session_dto_to_wire(dto) -> dict[str, object]:
    """Render a PeriodSessionDTO exactly as the schedule views render a session.

    The two shapes must be identical: a client reading a session from a day view
    and then re-reading it by id would otherwise see two different objects.
    """
    return {
        "timetable_session_id": str(dto.timetable_session_id),
        "school_id": str(dto.school_id),
        "section_id": str(dto.section_id),
        "date": dto.date.isoformat(),
        "slot_id": str(dto.slot_id),
        "slot_code": dto.slot_code,
        "subject_id": str(dto.subject_id),
        "assigned_teacher_id": str(dto.assigned_teacher_id),
        "substitute_teacher_id": (
            str(dto.substitute_teacher_id) if dto.substitute_teacher_id else None
        ),
        "starts_at": dto.starts_at.isoformat(),
        "ends_at": dto.ends_at.isoformat(),
        "starts_at_local": dto.starts_at_local.strftime("%H:%M"),
        "ends_at_local": dto.ends_at_local.strftime("%H:%M"),
        "cancelled": dto.cancelled,
        "cancellation_reason_key": dto.cancellation_reason_key,
        "room_code": dto.room_code,
        "timetable_id": str(dto.timetable_id),
        "timetable_version": dto.timetable_version,
    }
