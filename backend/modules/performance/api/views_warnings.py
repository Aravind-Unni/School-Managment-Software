"""GET /warnings: the at-risk list staff work through.

Returns open and acknowledged warnings (or one state with ``?state=``) for
the pupils the caller may read, each with the pupil's name and class and the
figure that triggered it. School-wide readers see every pupil; a teacher sees
the pupils in classes they teach. Pupils the caller cannot read are left out
rather than refused, so the list never confirms who else has a warning.

Does not handle: paging (a school's open warnings fit one response) or
evaluating rules (``POST /performance/rebuild`` does that).
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ActionDenied, ObjectInaccessible

from ..models import Warning as WarningRow
from ..models import WarningState
from . import deps
from .views import COMMON_ERRORS

ACTIVE_STATES = (WarningState.OPEN, WarningState.ACKNOWLEDGED)


class WarningCollectionView(APIView):
    """GET /warnings."""

    @extend_schema(
        operation_id="list_warnings",
        parameters=[OpenApiParameter("state", str, required=False)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """List warnings the caller may see, newest first, with names and classes."""
        context = request.school_context
        requested = request.query_params.get("state")
        states = (requested,) if requested in WarningState.values else ACTIVE_STATES
        gate = deps.warning_service().gate
        registry = gate.registry
        rows = list(
            WarningRow.objects.filter(school_id=context.school_id, state__in=states)
            .select_related("rule")
            .order_by("-opened_at")
        )
        readable: dict = {}
        sections: dict = {}
        on = gate.effective_date()
        for student_id in {row.student_id for row in rows}:
            try:
                gate.require_student_read(context, student_id)
            except (ObjectInaccessible, ActionDenied):
                readable[student_id] = False
                continue
            readable[student_id] = True
            facts = registry.get_relationships(context, context.actor_id, student_id, on)
            sections[student_id] = facts.section_id
        visible = [row for row in rows if readable.get(row.student_id)]
        names = registry.display_names(context, tuple({row.student_id for row in visible}))
        labels = {
            section_id: registry.section_label(context, section_id)
            for section_id in {value for value in sections.values() if value is not None}
        }
        items = []
        for row in visible:
            section_id = sections.get(row.student_id)
            items.append(
                {
                    "id": str(row.id),
                    "student_id": str(row.student_id),
                    "student_name": names.get(row.student_id),
                    "section_id": str(section_id) if section_id else None,
                    "section_label": labels.get(section_id) if section_id else None,
                    "rule_code": row.rule.code,
                    "threshold": str(row.rule.threshold),
                    "state": row.state,
                    "version": row.version,
                    "source_refs": row.source_refs,
                    "explanation_key": row.explanation_key,
                    "reason": row.reason,
                    "opened_at": row.opened_at.isoformat(),
                }
            )
        return Response({"items": items, "next_cursor": None})
