"""GET /notices/inbox -- published notices addressed to me or my children.

A notice's audience snapshot lists pupils; a guardian sees it when one of
their linked children is in it, a pupil when they are. Newest first.
Does not handle: read receipts or dismissing a notice.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.values import school_date

from ..models import AudienceSnapshot, Notice, NoticeState
from . import deps

#: How many recent notices the inbox shows.
INBOX_LIMIT = 50


class NoticeInboxView(APIView):
    """List notices for the calling person."""

    def get(self, request: Request) -> Response:
        """Return ``{items: [...]}`` of published notices reaching the caller."""
        context = request.school_context
        gate = deps.gate()
        on = school_date(gate.clock.now())
        people = {str(context.actor_id)}
        people.update(
            str(student_id)
            for student_id in gate.registry.linked_student_ids(context, context.actor_id, on)
        )
        snapshots = AudienceSnapshot.objects.filter(school_id=context.school_id).order_by(
            "-created_at"
        )[: INBOX_LIMIT * 4]
        notice_ids = [
            row.notice_id
            for row in snapshots
            if people.intersection(str(value) for value in row.recipient_ids)
        ]
        notices = Notice.objects.filter(
            school_id=context.school_id, id__in=notice_ids, state=NoticeState.PUBLISHED
        ).order_by("-updated_at")[:INBOX_LIMIT]
        return Response(
            {
                "items": [
                    {
                        "id": str(row.id),
                        "title": row.title,
                        "body": row.body,
                        "locale": row.locale,
                        "published_at": row.updated_at.isoformat(),
                    }
                    for row in notices
                ],
                "next_cursor": None,
            }
        )


class NoticeListView(APIView):
    """GET /notices/recent -- the school's recent notices, drafts included.

    For staff who write or approve notices: drafts awaiting publication are
    listed first. Requires notices.create.
    """

    def get(self, request: Request) -> Response:
        """Return up to 100 recent notices, drafts first, newest first."""
        from ..services.notices import _notice_dto

        context = request.school_context
        deps.gate().require_action(context, "notices.create")
        rows = Notice.objects.filter(school_id=context.school_id).order_by("-updated_at")[:100]
        items = sorted(
            (_notice_dto(row) for row in rows),
            key=lambda row: 0 if row["state"] == NoticeState.DRAFT else 1,
        )
        return Response({"items": items, "next_cursor": None})
