"""Demo REST endpoints. The reference for every module's API layer.

Views are thin: they parse, delegate to the service, and render. They contain no
authorisation logic of their own -- that is the service's call to the resolver,
so a worker or an export invoking the same service gets the same decision.
"""

from __future__ import annotations

from uuid import UUID

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.pagination import clamp_page_size

from .serializers import (
    CreateNoteRequest,
    ErrorEnvelopeResponse,
    NoteCollectionResponse,
    NoteResponse,
    UpdateNoteRequest,
)
from .services import DemoNoteService

#: Error responses every endpoint in this module can return. Declared once so
#: the generated client has the full error surface, not just the happy path.
COMMON_ERRORS = {
    400: OpenApiResponse(ErrorEnvelopeResponse, "Client asserted its own identity."),
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated, or 2FA too old."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied in this scope."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible to you."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}


def build_service() -> DemoNoteService:
    """Assemble the service from the profile's bound ports.

    Reads the PortRegistry the profile built, so standalone gets fakes and
    integrated gets real providers with no change here.

    Does not handle: caching the service. It is cheap to build and holding one
    per process would capture a stale clock in tests.
    """
    from shared.scope_resolver import ScopeResolver

    registry = settings.SCHOOL_PORTS
    return DemoNoteService(
        resolver=ScopeResolver(
            access=registry.resolve("access"),  # type: ignore[arg-type]
            registry=registry.resolve("registry"),  # type: ignore[arg-type]
        ),
        platform=registry.resolve("platform"),  # type: ignore[arg-type]
        clock=registry.resolve("clock"),  # type: ignore[arg-type]
    )


class NoteCollectionView(APIView):
    """GET (list) and POST (create) for demo notes."""

    @extend_schema(
        operation_id="demo_notes_list",
        summary="List demo notes",
        parameters=[
            OpenApiParameter(
                "cursor",
                str,
                description="Opaque keyset cursor from a previous next_cursor. Do not parse.",
            ),
            OpenApiParameter(
                "page_size",
                int,
                description=(
                    "Requested page size. Capped server-side; invalid values "
                    "fall back to the default."
                ),
            ),
        ],
        responses={200: NoteCollectionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return a cursor page of notes.

        Query parameters: ``cursor`` (opaque), ``page_size`` (capped).
        """
        page = build_service().list_notes(
            request.school_context,
            cursor=request.query_params.get("cursor") or None,
            page_size=clamp_page_size(_int_or_none(request.query_params.get("page_size"))),
        )
        return Response(page.to_wire(lambda view: view.to_wire()))

    @extend_schema(
        operation_id="demo_notes_create",
        summary="Create a demo note",
        request=CreateNoteRequest,
        responses={201: NoteResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a note and return it with HTTP 201."""
        payload = CreateNoteRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        view = build_service().create_note(
            request.school_context,
            body=payload.validated_data["body"],
            subject_person_id=payload.validated_data["subject_person_id"],
        )
        return Response(view.to_wire(), status=201)


class NoteDetailView(APIView):
    """GET (read) and PATCH (update) for one demo note."""

    @extend_schema(
        operation_id="demo_notes_read",
        summary="Read one demo note",
        responses={200: NoteResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, note_id: UUID) -> Response:
        """Return one note, or the 404 envelope."""
        view = build_service().get_note(request.school_context, note_id)
        return Response(view.to_wire())

    @extend_schema(
        operation_id="demo_notes_update",
        summary="Update a demo note under optimistic concurrency",
        request=UpdateNoteRequest,
        responses={
            200: NoteResponse,
            409: OpenApiResponse(
                ErrorEnvelopeResponse,
                "expected_version did not match the stored version.",
            ),
            **COMMON_ERRORS,
        },
    )
    def patch(self, request: Request, note_id: UUID) -> Response:
        """Update a note under optimistic concurrency, or return 409."""
        payload = UpdateNoteRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        view = build_service().update_note(
            request.school_context,
            note_id,
            body=payload.validated_data["body"],
            expected_version=payload.validated_data["expected_version"],
        )
        return Response(view.to_wire())


def _int_or_none(raw: str | None) -> int | None:
    """Parse an optional integer query parameter.

    Returns None on anything non-numeric so that ``?page_size=abc`` falls back to
    the default rather than raising a 500.
    """
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
