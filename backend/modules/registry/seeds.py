"""Bootstrap and synthetic seed scenarios for M02.

All data here is synthetic and derived from ``shared.fixtures``, so the same
scenario produces byte-identical rows on every machine. Nothing here describes a
real person, and no real CBSE curriculum, grading scale or fee structure is
present: the school publishes its own reference data.

``bootstrap`` is not a scenario. It installs the one SchoolConfig row that the
deployment cannot serve without, which is why the API never creates it
implicitly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from shared import fixtures

from .models import SchoolConfig

#: Fixed instant for seeded rows, inside the fixture school term. A fixed
#: instant rather than "now" keeps seeded data deterministic, which cursor
#: ordering assertions depend on.
SEED_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)

#: Namespace for seeded row ids, so re-running is idempotent rather than
#: accumulating duplicates.
SEED_NAMESPACE = uuid.UUID("9b3f7c41-2a6d-4e58-8f0c-1d9e2a3b4c5d")


def _seed_id(label: str) -> uuid.UUID:
    """Return a stable id for a seeded row label."""
    return uuid.uuid5(SEED_NAMESPACE, label)


def bootstrap(school_id: uuid.UUID | None = None) -> dict[str, int]:
    """Install this deployment's single SchoolConfig row if it is absent.

    Idempotent: running it twice leaves one row and does not advance its
    version. Returns a count summary so the runner can report what it wrote.

    Does not handle: choosing the school. ``school_id`` comes from deployment
    configuration, never from a request.
    """
    resolved = school_id or fixtures.SCHOOL_A
    _, created = SchoolConfig.objects.get_or_create(
        school_id=resolved,
        defaults={
            "id": _seed_id(f"school_config.{resolved}"),
            # A placeholder the school replaces on first setup. Deliberately not
            # a real school's name.
            "display_name": "Unnamed School",
            "board": "CBSE",
            "default_language": "en",
            "version": 1,
            "created_at": SEED_INSTANT,
            "updated_at": SEED_INSTANT,
        },
    )
    return {"school_config": 1 if created else 0}


def baseline(school_id: uuid.UUID | None = None) -> dict[str, int]:
    """Install the bootstrap row. The step-1 baseline is deliberately empty.

    Reference data and people are created through the API in tests and by the
    school in practice. Seeding pupils here would put invented children into
    every developer's database and into any screenshot taken from it.
    """
    return bootstrap(school_id)
