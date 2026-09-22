"""GET/PUT/DELETE /students/{id}/photo: the pupil's photograph.

PUT takes the image bytes as the request body (JPEG, PNG or WebP, at most
300 KB; the browser shrinks photos before sending). GET returns the image to
staff who may read pupils, and to the pupil and their own parents. A pupil
without a photo answers 204 (nothing to show), and the screens show initials.

Does not handle: resizing on the server, or more than one photo per pupil.
"""

from __future__ import annotations

from uuid import UUID

from django.db.models import Q
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import BaseParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed
from contracts.values import school_date

from ..models import GuardianLink, Student, StudentPhoto
from ..services.writes import fetch_in_school
from .deps import clock, people_service

MAX_BYTES = 300 * 1024
#: Leading bytes of each accepted image type.
SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)


class ImageParser(BaseParser):
    """Hand the raw request body through untouched."""

    media_type = "image/*"

    def parse(self, stream, media_type=None, parser_context=None):
        """Return the body bytes."""
        return stream.read(MAX_BYTES + 1)


def _is_family(context, student_id: UUID) -> bool:
    """Return True when the caller is the pupil or a current parent of the pupil."""
    if context.actor_id == student_id:
        return True
    on = school_date(clock().now())
    return (
        GuardianLink.objects.filter(
            school_id=context.school_id,
            guardian_id=context.actor_id,
            student_id=student_id,
            visibility="academic",
            from_date__lte=on,
        )
        .filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
        .exists()
    )


class StudentPhotoView(APIView):
    """GET/PUT/DELETE /students/{id}/photo."""

    parser_classes = [ImageParser]  # noqa: RUF012 -- DRF convention

    @extend_schema(operation_id="get_student_photo", responses={200: bytes})
    def get(self, request: Request, student_id: UUID):
        """Return the photo bytes, or 204 when the pupil has none."""
        context = request.school_context
        if not _is_family(context, student_id):
            people_service()._authorise(context, "students.read")
        photo = StudentPhoto.objects.filter(
            student_id=student_id, school_id=context.school_id
        ).first()
        if photo is None:
            return HttpResponse(status=204)
        response = HttpResponse(bytes(photo.data), content_type=photo.content_type)
        response["Cache-Control"] = "private, max-age=300"
        return response

    @extend_schema(operation_id="put_student_photo", responses={200: dict})
    def put(self, request: Request, student_id: UUID) -> Response:
        """Store or replace the photo."""
        context = request.school_context
        people_service()._authorise(context, "students.update")
        student = fetch_in_school(Student, school_id=context.school_id, row_id=student_id)
        body = request.data if isinstance(request.data, bytes) else b""
        if not body or len(body) > MAX_BYTES:
            raise ValidationFailed("registry.photo.too_big")
        content_type = next(
            (kind for magic, kind in SIGNATURES if body.startswith(magic)), None
        )
        if content_type is None or (content_type == "image/webp" and body[8:12] != b"WEBP"):
            raise ValidationFailed("registry.photo.not_image")
        StudentPhoto.objects.update_or_create(
            student=student,
            defaults={
                "school_id": context.school_id,
                "content_type": content_type,
                "data": body,
                "updated_at": clock().now(),
            },
        )
        return Response({"student_id": str(student_id), "has_photo": True})

    @extend_schema(operation_id="delete_student_photo", responses={200: dict})
    def delete(self, request: Request, student_id: UUID) -> Response:
        """Remove the photo."""
        context = request.school_context
        people_service()._authorise(context, "students.update")
        StudentPhoto.objects.filter(student_id=student_id, school_id=context.school_id).delete()
        return Response({"student_id": str(student_id), "has_photo": False})
