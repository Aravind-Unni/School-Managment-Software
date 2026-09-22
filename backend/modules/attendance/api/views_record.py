"""GET /attendance/students/{id}/record: a pupil's attendance by subject and month.

For the family pages and the pupil overview. ``from`` and ``to`` are optional:
by default the current term up to today; ``range=year`` starts from the
first term of the academic year. Each row carries periods due,
present, absent, late, excused and the attended percentage (present and late
over marked, excused left out). Same access as the summary: staff with
attendance.read, or the pupil and their own parents.

Does not handle: day-by-day registers (see the class register) or years before
the current one without explicit dates.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.values import school_date

from . import deps


def _term_start(registry, context, today: date) -> date:
    """First day of the term containing today; today when between terms."""
    term = registry.current_term(context, today)
    return term.start if term is not None else today


class AttendanceRecordView(APIView):
    """GET /attendance/students/{id}/record."""

    @extend_schema(
        operation_id="get_attendance_record",
        parameters=[
            OpenApiParameter("from", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("to", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("range", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: dict},
    )
    def get(self, request: Request, student_id: UUID) -> Response:
        """Return totals, per-subject and per-month attendance for one pupil."""
        context = request.school_context
        service = deps.summary_service()
        today = school_date(service.clock.now())
        to_raw = request.query_params.get("to")
        from_raw = request.query_params.get("from")
        to_date = min(date.fromisoformat(to_raw), today) if to_raw else today
        if from_raw:
            from_date = date.fromisoformat(from_raw)
        elif request.query_params.get("range") == "year":
            terms = service.registry.list_terms(context, to_date)
            from_date = (
                terms[0].start if terms else _term_start(service.registry, context, to_date)
            )
        else:
            from_date = _term_start(service.registry, context, to_date)
        result = service.breakdown(context, student_id, from_date, to_date)
        names = service.registry.subject_names(context)
        subjects = [
            {"subject_id": key, "subject_name": names.get(UUID(key)), **counts}
            for key, counts in result["by_subject"].items()
        ]
        subjects.sort(key=lambda row: row["subject_name"] or "")
        months = [{"month": key, **counts} for key, counts in result["by_month"].items()]
        return Response(
            {
                "student_id": str(student_id),
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "total": result["total"],
                "by_subject": subjects,
                "by_month": months,
            }
        )
