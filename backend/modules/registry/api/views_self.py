"""GET /students/mine -- the pupils the caller may act for.

A student gets themselves; a guardian gets the children linked to them today
(academic visibility only). Staff get an empty list. Self-scoped by
construction: nothing here is looked up from the request except the session.
"""

from __future__ import annotations

from django.db.models import Q
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.values import school_date

from ..models import Enrolment, GuardianLink, Student
from .deps import clock


def _section_label(school_id, student_id, on) -> tuple[str | None, str | None]:
    """Return (section id, "Std N - X") of the pupil's enrolment on a date."""
    row = (
        Enrolment.objects.filter(
            school_id=school_id, student_id=student_id, state="active", from_date__lte=on
        )
        .filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
        .select_related("section__standard")
        .order_by("-from_date")
        .first()
    )
    if row is None:
        return None, None
    return str(row.section_id), f"Std {row.section.standard.number} - {row.section.name}"


class MyStudentsView(APIView):
    """List the pupils this account acts for."""

    def get(self, request: Request) -> Response:
        """Return ``{items: [...]}``; never another family's children."""
        context = request.school_context
        on = school_date(clock().now())
        items = []
        own = Student.objects.filter(id=context.actor_id, school_id=context.school_id).first()
        students = [(own, "self")] if own is not None else []
        links = (
            GuardianLink.objects.filter(
                school_id=context.school_id,
                guardian_id=context.actor_id,
                visibility="academic",
                from_date__lte=on,
            )
            .filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
            .values_list("student_id", flat=True)
        )
        for student in Student.objects.filter(school_id=context.school_id, id__in=list(links)):
            students.append((student, "guardian"))
        for student, relationship in students:
            section_id, label = _section_label(context.school_id, student.id, on)
            items.append(
                {
                    "id": str(student.id),
                    "display_name": student.display_name,
                    "admission_no": student.admission_no,
                    "section_id": section_id,
                    "section_label": label,
                    "relationship": relationship,
                }
            )
        items.sort(key=lambda row: row["display_name"])
        return Response({"items": items, "next_cursor": None})
