"""M09 REST endpoints for library catalogue and circulation."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from . import deps
from .serializers import (
    AdjustCopyRequest,
    CatalogueImportRequest,
    CreateCopyRequest,
    CreateLoanRequest,
    CreateTitleRequest,
    ErrorEnvelopeResponse,
    RenewLoanRequest,
    ReturnLoanRequest,
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


class TitleCollectionView(APIView):
    """POST/GET /library/titles."""

    @extend_schema(
        operation_id="create_library_title",
        request=CreateTitleRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a catalogue title."""
        body = validated(CreateTitleRequest, request.data)
        created = deps.catalogue_service().create_title(
            request.school_context,
            name=body["name"],
            author=body["author"],
            language=body["language"],
            isbn=body.get("isbn"),
        )
        return Response(created, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="search_library_titles",
        parameters=[
            OpenApiParameter("q", str, required=False),
            OpenApiParameter("cursor", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Search titles."""
        return Response(
            deps.catalogue_service().search_titles(
                request.school_context,
                q=request.query_params.get("q"),
                cursor=request.query_params.get("cursor"),
            )
        )


class TitleAvailabilityView(APIView):
    """GET /library/titles/{id}/availability."""

    @extend_schema(
        operation_id="get_title_availability", responses={200: dict, **COMMON_ERRORS}
    )
    def get(self, request: Request, title_id: UUID) -> Response:
        """Available and total copy counts."""
        return Response(deps.catalogue_service().availability(request.school_context, title_id))


class CopyCollectionView(APIView):
    """GET copies of one title (for the issue desk); POST registers a copy."""

    def get(self, request: Request) -> Response:
        """Return a title's copies with whether each is on the shelf."""
        from uuid import UUID

        from ..models import Copy, Loan

        deps.gate().require_catalogue_read(request.school_context)
        raw = request.query_params.get("title_id") or ""
        try:
            title_id = UUID(raw)
        except ValueError:
            return Response({"items": [], "next_cursor": None})
        rows = Copy.objects.filter(
            school_id=request.school_context.school_id, title_id=title_id
        ).order_by("accession_no")
        on_loan = set(
            Loan.objects.filter(
                school_id=request.school_context.school_id,
                copy_id__in=[row.id for row in rows],
                returned_at__isnull=True,
            ).values_list("copy_id", flat=True)
        )
        items = [
            {
                "id": str(row.id),
                "accession_no": row.accession_no,
                "state": row.state,
                "on_loan": row.id in on_loan,
                "version": row.version,
            }
            for row in rows
        ]
        return Response({"items": items, "next_cursor": None})

    @extend_schema(
        operation_id="create_library_copy",
        request=CreateCopyRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Register a physical copy."""
        body = validated(CreateCopyRequest, request.data)
        created = deps.catalogue_service().create_copy(
            request.school_context,
            title_id=body["title_id"],
            accession_no=body["accession_no"],
        )
        return Response(created, status=status.HTTP_201_CREATED)


class CopyAdjustView(APIView):
    """POST /library/copies/{id}/adjust."""

    @extend_schema(
        operation_id="adjust_library_copy",
        request=AdjustCopyRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, copy_id: UUID) -> Response:
        """Lost/damaged/withdrawn adjustment."""
        body = validated(AdjustCopyRequest, request.data)
        return Response(
            deps.catalogue_service().adjust_copy(
                request.school_context,
                copy_id,
                new_state=body["new_state"],
                reason=body["reason"],
                expected_version=body["expected_version"],
            )
        )


class LoanCollectionView(APIView):
    """POST /library/loans."""

    @extend_schema(
        operation_id="issue_library_loan",
        request=CreateLoanRequest,
        responses={201: dict, 200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Issue a copy to a borrower."""
        body = validated(CreateLoanRequest, request.data)
        key = request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")
        if not key:
            raise ValidationFailed("error.validation_failed")
        wire, code = deps.loan_service().issue(
            request.school_context,
            copy_id=body["copy_id"],
            borrower_person_id=body["borrower_person_id"],
            borrower_type=body["borrower_type"],
            due_date=body["due_date"],
            idempotency_key=key,
        )
        return Response(wire, status=code)


class LoanReturnView(APIView):
    """POST /library/loans/{id}/return."""

    @extend_schema(
        operation_id="return_library_loan",
        request=ReturnLoanRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, loan_id: UUID) -> Response:
        """Return a loan (retry-safe)."""
        body = validated(ReturnLoanRequest, request.data)
        return Response(
            deps.loan_service().return_loan(
                request.school_context,
                loan_id,
                returned_at=body["returned_at"],
                condition=body["condition"],
                expected_version=body["expected_version"],
            )
        )


class LoanRenewView(APIView):
    """POST /library/loans/{id}/renew."""

    @extend_schema(
        operation_id="renew_library_loan",
        request=RenewLoanRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, loan_id: UUID) -> Response:
        """Renew an open loan."""
        body = validated(RenewLoanRequest, request.data)
        return Response(
            deps.loan_service().renew(
                request.school_context,
                loan_id,
                new_due_date=body["new_due_date"],
                expected_version=body["expected_version"],
                reason=body.get("reason"),
            )
        )


class BorrowerLoansView(APIView):
    """GET /library/borrowers/{person_id}/loans."""

    @extend_schema(
        operation_id="list_borrower_loans",
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request, person_id: UUID) -> Response:
        """Borrower loan history."""
        return Response(
            deps.loan_service().list_borrower_loans(
                request.school_context,
                person_id,
                cursor=request.query_params.get("cursor"),
            )
        )


class OverdueCollectionView(APIView):
    """GET /library/overdues."""

    @extend_schema(
        operation_id="list_library_overdues",
        parameters=[
            OpenApiParameter("as_of", str, required=True),
            OpenApiParameter("cursor", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Overdue open loans as of a school civil date."""
        raw = request.query_params.get("as_of")
        if not raw:
            raise ValidationFailed("error.validation_failed")
        try:
            as_of = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationFailed("error.validation_failed") from exc
        return Response(
            deps.overdue_service().list_overdues(
                request.school_context,
                as_of=as_of,
                cursor=request.query_params.get("cursor"),
            )
        )


class CatalogueImportView(APIView):
    """POST /library/catalogue-imports."""

    @extend_schema(
        operation_id="import_library_catalogue",
        request=CatalogueImportRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Import titles/copies with duplicate review."""
        body = validated(CatalogueImportRequest, request.data)
        return Response(deps.import_service().import_rows(request.school_context, body["rows"]))
