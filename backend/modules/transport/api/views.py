"""M08 REST endpoints for bus participation and fee coordination."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    CreateAdjustmentRequest,
    CreateBillingRunRequest,
    CreateBusRequest,
    CreateParticipationRequest,
    ErrorEnvelopeResponse,
    PatchParticipationRequest,
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


class BusCollectionView(APIView):
    """POST/GET /buses."""

    @extend_schema(
        operation_id="create_bus",
        request=CreateBusRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a labelled bus."""
        body = validated(CreateBusRequest, request.data)
        created = deps.bus_service().create(
            request.school_context,
            label=body["label"],
            active=body.get("active", True),
        )
        return Response(created, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="list_buses",
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """List buses for the actor school."""
        return Response(
            deps.bus_service().list_buses(
                request.school_context,
                cursor=request.query_params.get("cursor"),
            )
        )


class ParticipationCollectionView(APIView):
    """POST /bus-participations."""

    @extend_schema(
        operation_id="create_bus_participation",
        request=CreateParticipationRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Opt a student into bus participation."""
        body = validated(CreateParticipationRequest, request.data)
        created = deps.participation_service().create(
            request.school_context,
            student_id=body["student_id"],
            from_date=body["from_date"],
            fee_plan_id=body["fee_plan_id"],
            bus_id=body.get("bus_id"),
        )
        return Response(created, status=status.HTTP_201_CREATED)


class ParticipationDetailView(APIView):
    """GET/PATCH /bus-participations/{id}."""

    @extend_schema(operation_id="get_bus_participation", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, participation_id: UUID) -> Response:
        """Read one participation."""
        return Response(
            deps.participation_service().get(request.school_context, participation_id)
        )

    @extend_schema(
        operation_id="patch_bus_participation",
        request=PatchParticipationRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def patch(self, request: Request, participation_id: UUID) -> Response:
        """Revise bus assignment or end date."""
        body = validated(PatchParticipationRequest, request.data)
        fields_set = frozenset(k for k in ("to_date", "bus_id") if k in request.data)
        return Response(
            deps.participation_service().patch(
                request.school_context,
                participation_id,
                expected_version=body["expected_version"],
                reason=body["reason"],
                to_date=body.get("to_date"),
                bus_id=body.get("bus_id"),
                fields_set=fields_set,
            )
        )


class BillingRunView(APIView):
    """POST /bus-billing-runs."""

    @extend_schema(
        operation_id="create_bus_billing_run",
        request=CreateBillingRunRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Queue a period billing run with validation preview."""
        body = validated(CreateBillingRunRequest, request.data)
        result = deps.billing_service().create_run(
            request.school_context,
            period=body["period"],
            policy_version=body["policy_version"],
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class ParticipantListView(APIView):
    """GET /bus-participants."""

    @extend_schema(
        operation_id="list_bus_participants",
        parameters=[
            OpenApiParameter("date", str, required=True),
            OpenApiParameter("cursor", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Paginated effective participants on a school date."""
        raw = request.query_params.get("date")
        on_date = date.fromisoformat(raw) if raw else None
        if on_date is None:
            from contracts.errors import ValidationFailed

            raise ValidationFailed("error.validation_failed")
        return Response(
            deps.participation_service().list_participants(
                request.school_context,
                on_date=on_date,
                cursor=request.query_params.get("cursor"),
            )
        )


class ReconciliationView(APIView):
    """GET /bus-billing-reconciliation."""

    @extend_schema(
        operation_id="get_bus_billing_reconciliation",
        parameters=[OpenApiParameter("period", str, required=True)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Unmatched participation/charge requests and retry status."""
        period = request.query_params.get("period")
        if not period:
            from contracts.errors import ValidationFailed

            raise ValidationFailed("error.validation_failed")
        return Response(
            deps.reconciliation_service().reconcile(request.school_context, period=period)
        )


class AdjustmentCollectionView(APIView):
    """POST /bus-adjustments."""

    @extend_schema(
        operation_id="create_bus_adjustment",
        request=CreateAdjustmentRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Request an explicit Fees credit for a posted bus charge."""
        body = validated(CreateAdjustmentRequest, request.data)
        created = deps.adjustment_service().create(
            request.school_context,
            charge_id=body["charge_id"],
            amount_paise=body["amount_paise"],
            reason=body["reason"],
            source_key=body["source_key"],
        )
        return Response(created, status=status.HTTP_201_CREATED)


class BillingRequestRetryView(APIView):
    """POST /bus-billing-requests/{id}/retry."""

    @extend_schema(
        operation_id="retry_bus_billing_request",
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, billing_request_id: UUID) -> Response:
        """Retry a failed or lost-link billing request with the same source_key."""
        return Response(
            deps.billing_service().retry(request.school_context, billing_request_id)
        )
