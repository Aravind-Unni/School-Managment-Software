"""GET /assessments -- the assessments the caller works on.

A teacher sees assessments for the classes and subjects they are assigned
to today; a school-wide reader (principal, academic office) sees all. Each
row carries class and subject names and how many pupils are marked, so a
teacher can pick up where they left off.
"""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework.request import Request
from rest_framework.response import Response

from shared.people import is_school_wide_reader

from ..models import Assessment, MarkingOutcome
from . import deps

#: Newest assessments shown per request.
LIST_LIMIT = 200


def list_assessments(request: Request) -> Response:
    """Return ``{items: [...]}`` newest first."""
    context = request.school_context
    gate = deps.gate()
    on = gate.effective_date()
    queryset = Assessment.objects.filter(school_id=context.school_id)
    if not is_school_wide_reader(gate.access, context, on):
        pairs = gate.registry.get_teaching_assignments(context, context.actor_id, on)
        if not pairs:
            return Response({"items": [], "next_cursor": None})
        condition = Q()
        for row in pairs:
            condition |= Q(section_id=row.section_id, subject_id=row.subject_id)
        queryset = queryset.filter(condition)
    rows = list(
        queryset.annotate(
            pupils=Count("results"),
            marked=Count(
                "results",
                filter=Q(results__score__isnull=False)
                | Q(
                    results__marking_outcome__in=[MarkingOutcome.ABSENT, MarkingOutcome.EXEMPT]
                ),
            ),
        ).order_by("-created_at")[:LIST_LIMIT]
    )
    subjects = {str(k): v for k, v in gate.registry.subject_names(context).items()}
    labels: dict[str, str | None] = {}
    items = []
    for row in rows:
        key = str(row.section_id)
        if key not in labels:
            labels[key] = gate.registry.section_label(context, row.section_id)
        items.append(
            {
                "id": str(row.id),
                "section_id": key,
                "section_label": labels[key],
                "subject_id": str(row.subject_id),
                "subject_name": subjects.get(str(row.subject_id)),
                "term_id": str(row.term_id),
                "type": row.type,
                "max_score": f"{row.max_score:.2f}",
                "state": row.state,
                "version": row.version,
                "pupils": row.pupils,
                "marked": row.marked,
                "created_at": row.created_at.isoformat(),
            }
        )
    return Response({"items": items, "next_cursor": None})


def assessment_detail(request: Request, assessment_id) -> Response:
    """Return one assessment with every pupil's current result, for marking.

    Visible to the class's subject teacher and to school-wide readers; anyone
    else gets 404, like every other assessment read.
    """
    from contracts.errors import ObjectInaccessible

    from ..services.wire import assessment_to_wire

    context = request.school_context
    gate = deps.gate()
    on = gate.effective_date()
    assessment = gate.load_assessment(context, assessment_id)
    if not is_school_wide_reader(gate.access, context, on):
        pairs = gate.registry.get_teaching_assignments(context, context.actor_id, on)
        if not any(
            row.section_id == assessment.section_id and row.subject_id == assessment.subject_id
            for row in pairs
        ):
            raise ObjectInaccessible("error.object_inaccessible")
    results = list(assessment.results.all())
    names = {
        str(key): value
        for key, value in gate.registry.display_names(
            context, tuple(row.student_id for row in results)
        ).items()
    }
    body = assessment_to_wire(assessment)
    body["section_label"] = gate.registry.section_label(context, assessment.section_id)
    body["subject_name"] = {
        str(k): v for k, v in gate.registry.subject_names(context).items()
    }.get(str(assessment.subject_id))
    body["results"] = sorted(
        (
            {
                "student_id": str(row.student_id),
                "display_name": names.get(str(row.student_id), ""),
                "attempt_id": str(row.attempt_id),
                "score": f"{row.score:.2f}" if row.score is not None else None,
                "marking_outcome": row.marking_outcome,
                "status": row.status,
            }
            for row in results
        ),
        key=lambda row: row["display_name"],
    )
    return Response(body)
