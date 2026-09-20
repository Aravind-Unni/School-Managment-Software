"""M07 REST endpoints for the fee ledger."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    CreateChargeRequest,
    CreateConcessionRequest,
    CreateFeePlanRequest,
    CreatePaymentRequest,
    CreateRefundRequest,
    CreateReversalRequest,
    ErrorEnvelopeResponse,
)

COMMON_ERRORS = {
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated, or 2FA too old."),
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


class FeePlanCollectionView(APIView):
    """POST /fee-plans."""

    @extend_schema(
        operation_id="create_fee_plan",
        request=CreateFeePlanRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a versioned fee plan."""
        body = validated(CreateFeePlanRequest, request.data)
        created = deps.plan_service().create_plan(
            request.school_context,
            fee_heads=body["fee_heads"],
            applicability=body.get("applicability") or {},
            schedule=body["schedule"],
            version=body["version"],
        )
        return Response(created, status=status.HTTP_201_CREATED)


class ChargeCollectionView(APIView):
    """POST /charges."""

    @extend_schema(
        operation_id="create_charge",
        request=CreateChargeRequest,
        responses={201: dict, 200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Raise a charge with school-unique source_key."""
        body = validated(CreateChargeRequest, request.data)
        wire, created = deps.charge_service().create_via_api(request.school_context, body)
        return Response(wire, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PaymentCollectionView(APIView):
    """POST /payments."""

    @extend_schema(
        operation_id="create_payment",
        request=CreatePaymentRequest,
        responses={201: dict, 200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Record a manual payment."""
        body = validated(CreatePaymentRequest, request.data)
        key = request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")
        wire, code = deps.payment_service().create(
            request.school_context,
            student_id=body["student_id"],
            amount_paise=body["amount_paise"],
            method=body["method"],
            reference=body.get("reference"),
            allocations=body["allocations"],
            idempotency_key=key,
        )
        return Response(wire, status=code)


class PaymentDetailView(APIView):
    """GET /payments/{id}."""

    @extend_schema(operation_id="get_payment", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, payment_id: UUID) -> Response:
        """Fetch a payment/receipt."""
        return Response(deps.payment_service().get(request.school_context, payment_id))


class PaymentReversalView(APIView):
    """POST /payments/{id}/reversals."""

    @extend_schema(
        operation_id="reverse_payment",
        request=CreateReversalRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, payment_id: UUID) -> Response:
        """Reverse a posted payment."""
        body = validated(CreateReversalRequest, request.data)
        return Response(
            deps.correction_service().reverse_payment(
                request.school_context,
                payment_id,
                reason=body["reason"],
                expected_version=body["expected_version"],
            )
        )


class ConcessionCollectionView(APIView):
    """POST /concessions."""

    @extend_schema(
        operation_id="create_concession",
        request=CreateConcessionRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Post an approved concession."""
        body = validated(CreateConcessionRequest, request.data)
        return Response(
            deps.correction_service().concede(
                request.school_context,
                charge_id=body["charge_id"],
                amount_paise=body["amount_paise"],
                reason=body["reason"],
                source_key=body["source_key"],
                major=body.get("major", False),
            ),
            status=status.HTTP_201_CREATED,
        )


class RefundCollectionView(APIView):
    """POST /refunds."""

    @extend_schema(
        operation_id="create_refund",
        request=CreateRefundRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Record an explicit refund."""
        body = validated(CreateRefundRequest, request.data)
        return Response(
            deps.correction_service().refund(
                request.school_context,
                student_id=body["student_id"],
                amount_paise=body["amount_paise"],
                reason=body["reason"],
                credit_id=body.get("credit_id"),
            ),
            status=status.HTTP_201_CREATED,
        )


class FeeStatementView(APIView):
    """GET /students/{id}/fee-statement."""

    @extend_schema(
        operation_id="get_fee_statement",
        parameters=[OpenApiParameter("as_of", str, OpenApiParameter.QUERY, required=False)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request, student_id: UUID) -> Response:
        """Ledger statement for one student."""
        as_of = request.query_params.get("as_of")
        parsed = None
        if as_of:
            from datetime import date

            parsed = date.fromisoformat(as_of)
        return Response(
            deps.statement_service().get_statement(request.school_context, student_id, parsed)
        )


class OverdueListView(APIView):
    """GET /fees/overdue."""

    @extend_schema(operation_id="list_overdue", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request) -> Response:
        """Overdue open balances."""
        as_of = request.query_params.get("as_of")
        parsed = None
        if as_of:
            from datetime import date

            parsed = date.fromisoformat(as_of)
        return Response(
            deps.statement_service().list_overdue(
                request.school_context,
                as_of=parsed,
                cursor=request.query_params.get("cursor"),
            )
        )


class DailyCollectionsView(APIView):
    """GET /fees/daily-collections."""

    @extend_schema(operation_id="get_daily_collections", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request) -> Response:
        """Daily collection reconciliation."""
        from datetime import date

        raw = request.query_params.get("date")
        if not raw:
            return Response(
                {"code": "validation_failed", "message_key": "error.validation_failed"},
                status=422,
            )
        return Response(
            deps.statement_service().daily_collections(
                request.school_context, date.fromisoformat(raw)
            )
        )
