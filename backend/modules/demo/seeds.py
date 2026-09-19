"""Synthetic seed scenarios for the placeholder module.

All data is synthetic and derived from ``shared.fixtures``, so the same scenario
produces byte-identical rows on every machine. Nothing here describes a real
person.

Scenarios are functions returning a count summary, so ``seed_scenario`` can
report what it wrote without knowing the domain.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from shared import fixtures

from .models import DemoNote

#: Fixed instant for seeded rows, inside the fixture school term. Using a fixed
#: instant rather than "now" keeps seeded data deterministic, which matters for
#: cursor-pagination ordering assertions.
SEED_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

#: Namespace for seeded row ids, so re-running a scenario is idempotent rather
#: than accumulating duplicates.
SEED_NAMESPACE = uuid.UUID("2c7d1b90-5e3a-4f1c-9a8b-7d6e5f4c3b2a")


def _seed_id(label: str) -> uuid.UUID:
    """Return the deterministic id for a seeded row."""
    return uuid.uuid5(SEED_NAMESPACE, label)


def _note(label: str, *, body: str, subject_person_id, section_id, offset_minutes: int):
    """Create or update one seeded note, idempotently."""
    note, _created = DemoNote.objects.update_or_create(
        id=_seed_id(label),
        defaults={
            "school_id": fixtures.SCHOOL_A,
            "section_id": section_id,
            "subject_person_id": subject_person_id,
            "body": body,
            "version": 1,
            "created_at": SEED_INSTANT.replace(
                minute=SEED_INSTANT.minute + offset_minutes % 30
            ),
            "updated_at": SEED_INSTANT,
        },
    )
    return note


def baseline() -> dict[str, int]:
    """Three notes in School A, one per student, plus one in School B.

    The School B row is deliberate: it is what makes a cross-tenant leak visible.
    A suite that only ever has one school's data cannot detect a missing
    school_id filter.
    """
    for index, student in enumerate(
        (fixtures.STUDENT_S1, fixtures.STUDENT_S2, fixtures.STUDENT_S3)
    ):
        _note(
            f"baseline.{student}",
            body=f"Synthetic baseline note for {fixtures.FIXTURE_LABELS[student]}.",
            subject_person_id=student,
            section_id=fixtures.section_of(student),
            offset_minutes=index,
        )

    DemoNote.objects.update_or_create(
        id=_seed_id("baseline.school_b"),
        defaults={
            "school_id": fixtures.SCHOOL_B,
            "section_id": None,
            "subject_person_id": fixtures.STUDENT_S1_SCHOOL_B,
            "body": "Synthetic note belonging to School B. Must never be visible "
            "to a School A actor.",
            "version": 1,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    return {
        "school_a_notes": DemoNote.objects.filter(school_id=fixtures.SCHOOL_A).count(),
        "school_b_notes": DemoNote.objects.filter(school_id=fixtures.SCHOOL_B).count(),
    }


def paging() -> dict[str, int]:
    """Enough rows to force several cursor pages.

    Sized just above the default page size so that a paging bug shows up as a
    missing or repeated row rather than needing a large dataset.
    """
    baseline()
    from contracts.pagination import DEFAULT_PAGE_SIZE

    total = DEFAULT_PAGE_SIZE + 7
    for index in range(total):
        _note(
            f"paging.{index}",
            body=f"Synthetic paging note {index:03d}.",
            subject_person_id=fixtures.STUDENT_S1,
            section_id=fixtures.CLASS_C1,
            offset_minutes=index,
        )
    return {"school_a_notes": DemoNote.objects.filter(school_id=fixtures.SCHOOL_A).count()}


def empty() -> dict[str, int]:
    """No rows at all.

    Exists so that empty-state UI and terminal pagination are exercised
    deliberately rather than only before the first seed.
    """
    DemoNote.objects.all().delete()
    return {"school_a_notes": 0, "school_b_notes": 0}


#: Scenario name -> loader. Must match dev/modules/M00/module.json.
SCENARIOS = {"baseline": baseline, "paging": paging, "empty": empty}
