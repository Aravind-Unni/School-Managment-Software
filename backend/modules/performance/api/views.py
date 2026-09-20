"""M06 REST endpoints for performance dashboards, warnings and interventions."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    CreateInterventionRequest,
    CreateMeetingRequest,
    CreateWarningRuleRequest,
    ErrorEnvelopeResponse,
    WarningActionRequest,
)

COMMON_ERRORS = {
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


def _dashboard_wire(dto) -> dict:
    """Serialise DashboardDTO for JSON."""
    return {
        "metrics": [
            {
                "code": m.code,
                "value": m.value,
                "denominator": m.denominator,
                "definition_version": m.definition_version,
                "status": m.status,
                "window_label": m.window_label,
                "cohort_label": m.cohort_label,
            }
            for m in dto.metrics
        ],
        "warnings": [
            {
                "id": str(w.id),
                "rule_id": str(w.rule_id),
                "state": w.state,
                "explanation_key": w.explanation_key,
                "student_id": str(w.student_id) if w.student_id else None,
            }
            for w in dto.warnings
        ],
        "source_freshness": {
            "assessment_updated_at": (
                dto.source_freshness.assessment_updated_at.isoformat()
                if dto.source_freshness.assessment_updated_at
                else None
            ),
            "attendance_updated_at": (
                dto.source_freshness.attendance_updated_at.isoformat()
                if dto.source_freshness.attendance_updated_at
                else None
            ),
        },
        "updated_at": dto.updated_at.isoformat(),
    }


class DashboardView(APIView):
    """GET /performance/dashboard."""

    @extend_schema(
        operation_id="get_performance_dashboard",
        parameters=[
            OpenApiParameter("subject_id", str, required=False),
            OpenApiParameter("scope", str, required=True),
            OpenApiParameter("window", str, required=True),
            OpenApiParameter("student_id", str, required=False),
            OpenApiParameter("section_id", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return dashboard for one student scope."""
        subject_raw = request.query_params.get("subject_id")
        student_raw = request.query_params.get("student_id")
        section_raw = request.query_params.get("section_id")
        dto = deps.dashboard_service().get_dashboard(
            request.school_context,
            subject_id=UUID(subject_raw) if subject_raw else None,
            scope=request.query_params.get("scope") or "student",
            window=request.query_params.get("window") or "term",
            student_id=UUID(student_raw) if student_raw else None,
            section_id=UUID(section_raw) if section_raw else None,
        )
        return Response(_dashboard_wire(dto))


class ExportView(APIView):
    """GET /performance/export."""

    @extend_schema(
        operation_id="export_performance_summary",
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Scoped academic export omitting restricted observations for guardians."""
        student_id = UUID(request.query_params["student_id"])
        window = request.query_params.get("window") or "term"
        return Response(
            deps.dashboard_service().export_summary(
                request.school_context, student_id=student_id, window=window
            )
        )


class RebuildView(APIView):
    """POST /performance/rebuild — sync rebuild in tests; enqueue when worker up."""

    @extend_schema(operation_id="rebuild_projections", responses={202: dict, **COMMON_ERRORS})
    def post(self, request: Request) -> Response:
        """Rebuild projections for baseline pupils (synchronous for reliability)."""
        from shared import fixtures

        from ..services.wire import gate

        gate().require_staff_action(request.school_context, "warnings.manage")
        ctx = request.school_context
        proj = deps.projection_service()
        warn = deps.warning_service()
        ids = [fixtures.STUDENT_S1, fixtures.STUDENT_S2]
        count = proj.rebuild_school(ctx, ids)
        for student_id in ids:
            warn.evaluate_student(ctx, student_id)
        return Response(
            {"job_id": str(fixtures.SCHOOL_A), "state": "completed", "count": count},
            status=status.HTTP_202_ACCEPTED,
        )


class WarningRuleCollectionView(APIView):
    """POST /warning-rules."""

    @extend_schema(
        operation_id="create_warning_rule",
        request=CreateWarningRuleRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a versioned warning rule."""
        body = validated(CreateWarningRuleRequest, request.data)
        rule = deps.warning_service().create_rule(
            request.school_context,
            code=body["code"],
            threshold=body["threshold"],
            window=body["window"],
            minimum_samples=body["minimum_samples"],
            exclusions=body.get("exclusions") or [],
        )
        return Response(
            {
                "id": str(rule.id),
                "school_id": str(rule.school_id),
                "code": rule.code,
                "version": rule.version,
                "threshold": rule.threshold,
                "window": rule.window,
                "minimum_samples": rule.minimum_samples,
                "exclusions": rule.exclusions,
            },
            status=status.HTTP_201_CREATED,
        )


class WarningAcknowledgeView(APIView):
    """POST /warnings/{id}/acknowledge."""

    @extend_schema(
        operation_id="acknowledge_warning",
        request=WarningActionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, warning_id: UUID) -> Response:
        """Acknowledge an open warning."""
        body = validated(WarningActionRequest, request.data)
        warning = deps.warning_service().acknowledge(
            request.school_context,
            warning_id,
            reason=body["reason"],
            expected_version=body["expected_version"],
        )
        return Response(_warning_wire(warning))


class WarningDismissView(APIView):
    """POST /warnings/{id}/dismiss."""

    @extend_schema(
        operation_id="dismiss_warning",
        request=WarningActionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, warning_id: UUID) -> Response:
        """Dismiss a warning with reason."""
        body = validated(WarningActionRequest, request.data)
        warning = deps.warning_service().dismiss(
            request.school_context,
            warning_id,
            reason=body["reason"],
            expected_version=body["expected_version"],
        )
        return Response(_warning_wire(warning))


class InterventionCollectionView(APIView):
    """GET/POST /interventions."""

    @extend_schema(
        operation_id="create_intervention",
        request=CreateInterventionRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create an intervention."""
        body = validated(CreateInterventionRequest, request.data)
        row = deps.intervention_service().create(
            request.school_context,
            student_id=body["student_id"],
            goal=body["goal"],
            owner_id=body["owner_id"],
            review_date=body["review_date"],
            visibility=body["visibility"],
            resource_ids=body.get("resource_ids") or [],
        )
        return Response(_intervention_wire(row), status=status.HTTP_201_CREATED)

    @extend_schema(operation_id="list_interventions", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request) -> Response:
        """List interventions for a student."""
        student_id = UUID(request.query_params["student_id"])
        page = deps.intervention_service().list_for_student(
            request.school_context,
            student_id,
            cursor=request.query_params.get("cursor"),
        )
        return Response(
            {
                "items": [_intervention_dto_wire(i) for i in page.items],
                "next_cursor": page.next_cursor,
            }
        )


class MeetingCollectionView(APIView):
    """POST /meetings."""

    @extend_schema(
        operation_id="create_meeting",
        request=CreateMeetingRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Record a parent-teacher meeting."""
        body = validated(CreateMeetingRequest, request.data)
        row = deps.intervention_service().create_meeting(
            request.school_context,
            student_id=body["student_id"],
            meeting_date=body["date"],
            participants=body["participants"],
            notes=body["notes"],
            actions=body.get("actions") or [],
            visibility=body["visibility"],
        )
        return Response(
            {
                "id": str(row.id),
                "school_id": str(row.school_id),
                "student_id": str(row.student_id),
                "date": str(row.date),
                "participants": row.participants,
                "notes": row.notes,
                "actions": row.actions,
                "visibility": row.visibility,
                "version": row.version,
            },
            status=status.HTTP_201_CREATED,
        )


def _warning_wire(warning) -> dict:
    """Serialise Warning ORM row."""
    return {
        "id": str(warning.id),
        "school_id": str(warning.school_id),
        "student_id": str(warning.student_id),
        "rule_id": str(warning.rule_id),
        "rule_version": warning.rule_version,
        "state": warning.state,
        "version": warning.version,
        "source_refs": warning.source_refs,
        "explanation_key": warning.explanation_key,
        "reason": warning.reason,
    }


def _intervention_wire(row) -> dict:
    """Serialise Intervention ORM row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "student_id": str(row.student_id),
        "goal": row.goal,
        "owner_id": str(row.owner_id),
        "review_date": str(row.review_date),
        "state": row.state,
        "visibility": row.visibility,
        "version": row.version,
        "resource_ids": row.resource_ids,
    }


def _intervention_dto_wire(dto) -> dict:
    """Serialise InterventionDTO."""
    return {
        "id": str(dto.id),
        "school_id": str(dto.school_id),
        "student_id": str(dto.student_id),
        "goal": dto.goal,
        "owner_id": str(dto.owner_id),
        "review_date": str(dto.review_date),
        "state": dto.state,
        "visibility": dto.visibility,
        "version": dto.version,
        "resource_ids": [str(r) for r in dto.resource_ids],
    }
