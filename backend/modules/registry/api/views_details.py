"""GET/PUT /students/{id}/details: the pupil's admission-register details.

Kept apart from the frozen student record so adding a field here never
changes what other modules receive. GET needs students.read; PUT needs
students.update and the record's current version, and replaces the whole set
(an empty value removes a field). Problems come back per field.

Does not handle: parents' contact details (those live on the parent record)
or identity numbers (not collected).
"""

from __future__ import annotations

from uuid import UUID

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import FieldError, ValidationFailed

from ..models import Student, StudentPhoto
from ..services.student_details import DETAIL_FIELDS, clean_details
from ..services.writes import fetch_in_school, require_expected_version, stamp_update
from .deps import clock, people_service
from .views import validated


class StudentDetailsRequest(serializers.Serializer):
    """Body of PUT /students/{id}/details."""

    details = serializers.DictField(child=serializers.CharField(allow_blank=True))
    expected_version = serializers.IntegerField(min_value=1)


def _wire(row: Student) -> dict:
    """Render the details with the choices the form offers."""
    return {
        "student_id": str(row.id),
        "version": row.version,
        "details": dict(row.details or {}),
        "has_photo": StudentPhoto.objects.filter(student_id=row.id).exists(),
        "choices": {
            key: list(rule) for key, (kind, rule) in DETAIL_FIELDS.items() if kind == "choice"
        },
    }


class StudentDetailsView(APIView):
    """GET/PUT /students/{id}/details."""

    @extend_schema(operation_id="get_student_details", responses={200: dict})
    def get(self, request: Request, student_id: UUID) -> Response:
        """Return the pupil's details and the allowed choices."""
        context = request.school_context
        people_service()._authorise(context, "students.read")
        return Response(
            _wire(fetch_in_school(Student, school_id=context.school_id, row_id=student_id))
        )

    @extend_schema(
        operation_id="put_student_details",
        request=StudentDetailsRequest,
        responses={200: dict},
    )
    def put(self, request: Request, student_id: UUID) -> Response:
        """Replace the pupil's details after checking every field."""
        context = request.school_context
        body = validated(StudentDetailsRequest, request.data)
        people_service()._authorise(context, "students.update")
        cleaned, problems = clean_details(body["details"])
        if problems:
            raise ValidationFailed(
                "error.validation_failed",
                field_errors=tuple(
                    FieldError(f"details.{key}", message) for key, message in problems.items()
                ),
            )
        with transaction.atomic():
            row = fetch_in_school(
                Student, school_id=context.school_id, row_id=student_id, for_update=True
            )
            require_expected_version(row, body["expected_version"])
            row.details = cleaned
            stamp_update(row, now=clock().now())
            row.save()
        return Response(_wire(row))
