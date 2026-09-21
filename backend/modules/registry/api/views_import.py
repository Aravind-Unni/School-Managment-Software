"""POST /students/import: admit pupils from the office's admissions spreadsheet.

The browser reads the chosen CSV file and sends its text. ``apply: false``
(the default) only checks the file and reports what would happen;
``apply: true`` admits everyone in one go, or nobody when any row has a
problem. See ``services/student_import.py``.

Does not handle: files over 2 MB of text or 2000 pupils (split the file).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.student_import import StudentImportService
from .deps import clock, enrolment_service, guardian_link_service, people_service
from .views import validated

MAX_TEXT = 2 * 1024 * 1024


class StudentImportRequest(serializers.Serializer):
    """Body of POST /students/import."""

    csv = serializers.CharField(max_length=MAX_TEXT, trim_whitespace=False)
    apply = serializers.BooleanField(default=False)


class StudentImportView(APIView):
    """POST /students/import."""

    @extend_schema(
        operation_id="import_students",
        request=StudentImportRequest,
        responses={200: dict},
    )
    def post(self, request: Request) -> Response:
        """Check, or admit, every pupil in an admissions spreadsheet."""
        body = validated(StudentImportRequest, request.data)
        service = StudentImportService(
            people=people_service(),
            links=guardian_link_service(),
            enrolments=enrolment_service(),
            clock=clock(),
        )
        context = request.school_context
        if body["apply"]:
            return Response(service.apply(context, body["csv"]))
        return Response(service.preview(context, body["csv"]))
