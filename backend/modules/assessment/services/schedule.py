"""Scheduled tests and term exams, and the calendar of them.

A test or exam is an assessment with a date (``due_at``) and a title. Class
tests are created one at a time by the subject teacher (``CreateService``).
Term exams are set here for many classes at once: one paper per subject, each
on its date, for every chosen class that takes that subject. Setting the same
exam again skips papers that already exist, so the office can add classes
later. ``calendar`` lists what is scheduled for a pupil's class (or a class)
over a date range.

Does not handle: seating plans, invigilation, or moving a paper (reschedule by
creating the paper again with the new date and removing the old draft).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.identity import RequestContext
from shared.people import is_school_wide_reader

from ..models import Assessment, AssessmentType
from .authority import READING_RELATIONSHIPS, AuthorityGate

SCHOOL_TZ = ZoneInfo("Asia/Kolkata")
EXAM_ACTION = "results.publish"


def paper_moment(on: date, at: str | None) -> datetime:
    """Return the school-local start of a paper as an aware datetime."""
    hours, minutes = (at or "09:30").split(":")
    return datetime.combine(on, time(int(hours), int(minutes)), tzinfo=SCHOOL_TZ)


@dataclass(frozen=True, slots=True)
class ScheduleService:
    """Set term exams for many classes; list the calendar of scheduled papers."""

    gate: AuthorityGate
    registry: object
    create: object
    clock: object

    def schedule_exams(
        self,
        context: RequestContext,
        *,
        term_id: UUID,
        title: str,
        section_ids: list[UUID],
        papers: list[dict],
    ) -> dict:
        """Create one exam paper per class per subject. Skips existing papers."""
        self.gate.require_school_wide(context, EXAM_ACTION)
        title = title.strip()
        if not title or not section_ids or not papers:
            raise ValidationFailed("error.validation_failed")
        today = self.gate.effective_date()
        term = next(
            (row for row in self.registry.list_terms(context, today) if row.id == term_id), None
        )
        if term is None:
            raise ValidationFailed("assessment.error.unknown_term")
        created = skipped = not_taught = 0
        for section_id in section_ids:
            for paper in papers:
                subject_id = UUID(str(paper["subject_id"]))
                exists = Assessment.objects.filter(
                    school_id=context.school_id,
                    term_id=term_id,
                    section_id=section_id,
                    subject_id=subject_id,
                    type=AssessmentType.EXAM,
                    title=title,
                ).exists()
                if exists:
                    skipped += 1
                    continue
                roster = self.registry.get_roster(
                    context, section_id, today, subject_id=subject_id
                )
                if not roster.students:
                    not_taught += 1
                    continue
                maximum = f"{Decimal(str(paper.get('max_score') or 80)):.2f}"
                self.create.create(
                    context,
                    year_id=term.year_id,
                    term_id=term_id,
                    section_id=section_id,
                    subject_id=subject_id,
                    assessment_type=AssessmentType.EXAM,
                    components=[
                        {
                            "max_score": maximum,
                            "weight": "1.000",
                            "topic": None,
                            "question_type": None,
                        }
                    ],
                    policy_version="school-v1",
                    due_at=paper_moment(
                        date.fromisoformat(str(paper["date"])), paper.get("time")
                    ),
                    max_score=maximum,
                    assessment_id=uuid.uuid4(),
                    title=title,
                )
                created += 1
        return {"created": created, "already_scheduled": skipped, "not_taught": not_taught}

    def calendar(
        self,
        context: RequestContext,
        *,
        from_date: date,
        to_date: date,
        student_id: UUID | None = None,
        section_id: UUID | None = None,
    ) -> list[dict]:
        """Return tests and exams scheduled in the range for a pupil's class or a class."""
        if (to_date - from_date).days > 400 or to_date < from_date:
            raise ValidationFailed("error.validation_failed")
        today = self.gate.effective_date()
        sections: set[UUID] = set()
        if student_id is not None:
            facts = self.registry.get_relationships(
                context, context.actor_id, student_id, today
            )
            if facts.relationship not in READING_RELATIONSHIPS and not is_school_wide_reader(
                self.gate.access, context, today
            ):
                raise ObjectInaccessible("error.object_inaccessible")
            if facts.section_id is not None:
                sections.add(facts.section_id)
        elif section_id is not None:
            teaches = any(
                row.section_id == section_id
                for row in self.registry.get_teaching_assignments(
                    context, context.actor_id, today
                )
            )
            if not teaches and not is_school_wide_reader(self.gate.access, context, today):
                raise ObjectInaccessible("error.object_inaccessible")
            sections.add(section_id)
        else:
            # A teacher's own classes; a school-wide reader sees every class.
            if is_school_wide_reader(self.gate.access, context, today):
                sections = set(
                    Assessment.objects.filter(school_id=context.school_id).values_list(
                        "section_id", flat=True
                    )
                )
            else:
                sections = {
                    row.section_id
                    for row in self.registry.get_teaching_assignments(
                        context, context.actor_id, today
                    )
                }
        start = datetime.combine(from_date, time.min, tzinfo=SCHOOL_TZ)
        end = datetime.combine(to_date, time.max, tzinfo=SCHOOL_TZ)
        rows = Assessment.objects.filter(
            school_id=context.school_id,
            section_id__in=sections,
            due_at__gte=start,
            due_at__lte=end,
        ).order_by("due_at")
        names = self.registry.subject_names(context)
        labels: dict[UUID, str | None] = {}
        items = []
        for row in rows:
            if row.section_id not in labels:
                labels[row.section_id] = self.registry.section_label(context, row.section_id)
            local = row.due_at.astimezone(SCHOOL_TZ)
            items.append(
                {
                    "assessment_id": str(row.id),
                    "date": local.date().isoformat(),
                    "time": local.strftime("%H:%M"),
                    "title": row.title,
                    "type": row.type,
                    "subject_id": str(row.subject_id),
                    "subject_name": names.get(row.subject_id),
                    "section_id": str(row.section_id),
                    "section_label": labels[row.section_id],
                    "max_score": f"{row.max_score.normalize():f}",
                }
            )
        return items
