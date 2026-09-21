"""Keep a pupil's subject enrolments in step with their section.

A pupil placed in a section takes every compulsory subject offered there
(offerings with no ``optional_group``). Without this, subject-filtered rosters
-- the attendance register for a Maths period, a Maths mark sheet -- would be
empty until someone enrolled every pupil in every subject by hand.
Optional subjects (an elective group) are still chosen per pupil.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from django.db.models import Q

from ..models import Enrolment, SubjectEnrolment, SubjectOffering
from .writes import stamp_new, stamp_update


def enrol_in_compulsory_subjects(
    enrolment: Enrolment, *, from_date: date, to_date: date | None, now: datetime
) -> int:
    """Create subject enrolments for the section's compulsory offerings.

    Skips an offering the pupil already holds an open subject enrolment for.
    Returns how many were created. Assumes the caller holds a transaction.
    """
    offerings = SubjectOffering.objects.filter(
        school_id=enrolment.school_id,
        section_id=enrolment.section_id,
        archived=False,
        optional_group__isnull=True,
    )
    held = set(
        SubjectEnrolment.objects.filter(enrolment=enrolment, to_date__isnull=True).values_list(
            "subject_offering_id", flat=True
        )
    )
    created = 0
    for offering in offerings:
        if offering.id in held:
            continue
        row = SubjectEnrolment(
            school_id=enrolment.school_id,
            enrolment=enrolment,
            subject_offering=offering,
            from_date=from_date,
            to_date=to_date,
        )
        stamp_new(row, now=now)
        row.save()
        created += 1
    return created


def end_open_subject_enrolments(enrolment: Enrolment, *, last_day: date, now: datetime) -> int:
    """Close every subject enrolment of ``enrolment`` still open on ``last_day``."""
    rows = SubjectEnrolment.objects.filter(enrolment=enrolment).filter(
        Q(to_date__isnull=True) | Q(to_date__gt=last_day)
    )
    closed = 0
    for row in rows:
        row.to_date = max(last_day, row.from_date)
        stamp_update(row, now=now)
        row.save()
        closed += 1
    return closed


def enrol_section_pupils_in_offering(
    offering: SubjectOffering, *, on: date, now: datetime
) -> int:
    """Enrol the section's current pupils in a newly added compulsory offering."""
    if offering.optional_group is not None or offering.archived:
        return 0
    enrolments = Enrolment.objects.filter(
        school_id=offering.school_id,
        section_id=offering.section_id,
        state="active",
    ).filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
    created = 0
    for enrolment in enrolments:
        if SubjectEnrolment.objects.filter(
            enrolment=enrolment, subject_offering=offering, to_date__isnull=True
        ).exists():
            continue
        row = SubjectEnrolment(
            school_id=offering.school_id,
            enrolment=enrolment,
            subject_offering=offering,
            from_date=max(on, enrolment.from_date),
            to_date=enrolment.to_date,
        )
        stamp_new(row, now=now)
        row.save()
        created += 1
    return created


def offering_ids_for_section(section_id: UUID) -> list[UUID]:
    """Return compulsory offering ids of a section (used by tests and tools)."""
    return list(
        SubjectOffering.objects.filter(
            section_id=section_id, archived=False, optional_group__isnull=True
        ).values_list("id", flat=True)
    )
