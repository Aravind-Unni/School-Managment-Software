"""Demo REST endpoints. The reference for every module's API layer.

Views are thin: they parse, delegate to the service, and render. They contain no
authorisation logic of their own -- that is the service's call to the resolver,
so a worker or an export invoking the same service gets the same decision.
"""

from __future__ import annotations

from uuid import UUID

from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.pagination import clamp_page_size

from .serializers import CreateNoteRequest, UpdateNoteRequest
from .services import DemoNoteService


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

    def get(self, request: Request, note_id: UUID) -> Response:
        """Return one note, or the 404 envelope."""
        view = build_service().get_note(request.school_context, note_id)
        return Response(view.to_wire())

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
