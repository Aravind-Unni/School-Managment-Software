"""Shared mechanics for M02's versioned, school-scoped writes.

Every mutable row in this module carries an integer ``version``. A write states
the version it read; if the stored version moved, the write is refused with 409
rather than silently overwriting whatever the other writer did.

Does not handle: authorisation. Services call Access before reaching here.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db import models

from contracts.errors import ObjectInaccessible, VersionConflict


def fetch_in_school[ModelType: models.Model](
    manager: type[ModelType], *, school_id: UUID, row_id: UUID, for_update: bool = False
) -> ModelType:
    """Return one row belonging to this school, or raise ObjectInaccessible.

    A row that does not exist and a row belonging to ANOTHER school raise the
    identical error, so probing cannot distinguish the two. That is why this is
    one function rather than a get plus a school comparison at each call site:
    the comparison is easy to forget, and forgetting it leaks tenancy.

    ``for_update`` takes a row lock, for the recheck inside a write transaction.

    Does not handle: archived rows. Archive hides a row from NEW links, not from
    reads of history, so an archived row is still returned.
    """
    queryset = manager.objects.filter(school_id=school_id, id=row_id)
    if for_update:
        queryset = queryset.select_for_update()
    row = queryset.first()
    if row is None:
        raise ObjectInaccessible("error.object_inaccessible")
    return row


def require_expected_version(row: models.Model, expected_version: int) -> None:
    """Raise VersionConflict unless the row is at the version the writer read.

    Assumes the row was fetched inside the same transaction, with a lock when
    the caller intends to write. Checking an unlocked row is a check against a
    value another transaction may already have moved.
    """
    current = row.version
    if current != expected_version:
        raise VersionConflict(expected_version=expected_version, actual_version=current)


def stamp_new(row: models.Model, *, now: datetime) -> models.Model:
    """Set the creation timestamps on a new row. Version starts at 1 by default."""
    row.created_at = now
    row.updated_at = now
    return row


def stamp_update(row: models.Model, *, now: datetime) -> models.Model:
    """Advance the version and update timestamp of a row about to be saved.

    Incrementing here rather than at each call site is deliberate: a write that
    forgot to advance the version would make every subsequent stale write
    succeed, and the tests for that would still pass.
    """
    row.version = row.version + 1
    row.updated_at = now
    return row
