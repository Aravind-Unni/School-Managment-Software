"""GET /students/{id}/results?term_id=: a pupil's published marks for a term.

For parents, pupils and staff. Each published assessment gives one row: subject,
its name and kind, the day it was sat, marks out of the maximum, percentage and grade
(from the school's grade bands). ``subjects`` averages each subject's
percentages, graded the same way, and ``overall`` averages everything.
Access and "published only" come from the assessment port, the same rules
report cards use.

Does not handle: unpublished marks (never shown to families), or ranks.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed
from contracts.values import school_date

from ..models import Assessment, Publication
from ..services.grading import grade_for, school_bands
from . import deps


def _percent(score, max_score) -> Decimal | None:
    """Return score as a percentage of max_score, or None when not scored."""
    if score is None or max_score in (None, "0", "0.00"):
        return None
    return Decimal(str(score)) * 100 / Decimal(str(max_score))


class StudentResultsView(APIView):
    """GET /students/{id}/results."""

    @extend_schema(
        operation_id="get_student_results",
        parameters=[OpenApiParameter("term_id", str, OpenApiParameter.QUERY, required=False)],
        responses={200: dict},
    )
    def get(self, request: Request, student_id: UUID) -> Response:
        """Return published results for the term (default: the current term)."""
        context = request.school_context
        port = deps.assessment_port()
        today = school_date(port.clock.now())
        terms = port.registry.list_terms(context, today)
        term_raw = request.query_params.get("term_id")
        if term_raw:
            term_id = UUID(term_raw)
        else:
            term = port.registry.current_term(context, today)
            started = [row for row in terms if row.start <= today]
            term = term or (started[-1] if started else None)
            if term is None:
                raise ValidationFailed("assessment.error.no_current_term")
            term_id = term.id
        items = list(port.get_published_results(context, student_id, term_id)["items"])
        bands = school_bands(port.registry, context)
        names = port.registry.subject_names(context)
        assessments = {
            str(row.id): row
            for row in Assessment.objects.filter(
                school_id=context.school_id, id__in=[item["assessment_id"] for item in items]
            )
        }
        published = {}
        for row in Publication.objects.filter(assessment_id__in=list(assessments)).order_by(
            "published_at"
        ):
            published[str(row.assessment_id)] = row.published_at
        rows = []
        per_subject: dict[str, list[Decimal]] = defaultdict(list)
        for item in items:
            assessment = assessments.get(item["assessment_id"])
            percent = _percent(item["score"], item["max_score"])
            when = published.get(item["assessment_id"])
            if percent is not None:
                per_subject[item["subject_id"]].append(percent)
            rows.append(
                {
                    "assessment_id": item["assessment_id"],
                    "subject_id": item["subject_id"],
                    "subject_name": names.get(UUID(item["subject_id"])),
                    "type": assessment.type if assessment else None,
                    "title": assessment.title if assessment else "",
                    "sat_on": (
                        school_date(assessment.due_at).isoformat()
                        if assessment and assessment.due_at
                        else None
                    ),
                    "published_on": school_date(when).isoformat() if when else None,
                    "marking_outcome": item["marking_outcome"],
                    "score": item["score"],
                    "max_score": item["max_score"],
                    "percent": f"{percent:.1f}" if percent is not None else None,
                    "grade": item.get("grade")
                    or grade_for(item["score"], item["max_score"], bands),
                }
            )
        rows.sort(
            key=lambda row: (
                row["subject_name"] or "",
                row["sat_on"] or row["published_on"] or "",
            )
        )
        subjects = []
        for subject_id, values in per_subject.items():
            average = sum(values) / len(values)
            subjects.append(
                {
                    "subject_id": subject_id,
                    "subject_name": names.get(UUID(subject_id)),
                    "tests": len(values),
                    "average_percent": f"{average:.1f}",
                    "grade": grade_for(average, 100, bands),
                }
            )
        subjects.sort(key=lambda row: row["subject_name"] or "")
        every = [value for values in per_subject.values() for value in values]
        overall = sum(every) / len(every) if every else None
        return Response(
            {
                "student_id": str(student_id),
                "term_id": str(term_id),
                "terms": [
                    {"id": str(row.id), "name": row.name, "start": row.start.isoformat()}
                    for row in terms
                ],
                "results": rows,
                "subjects": subjects,
                "overall": {
                    "average_percent": f"{overall:.1f}" if overall is not None else None,
                    "grade": grade_for(overall, 100, bands) if overall is not None else None,
                },
            }
        )
