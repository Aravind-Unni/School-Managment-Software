"""The one demo aggregate. Shows the mandatory shape of every record.

Every record in this platform carries:
  * ``id``        -- UUID, never a sequential integer
  * ``school_id`` -- the trusted tenant, set from RequestContext, never a body
  * ``version``   -- integer, incremented on each write, compared against
                     ``expected_version`` so a stale client gets 409

Does not handle: soft deletion or history. Those are per-module decisions that
each module packet must specify.
"""

from __future__ import annotations

import uuid

from django.db import models


class DemoNote(models.Model):
    """A trivial school-scoped, versioned aggregate.

    Exists only to exercise the foundation. It has no meaning to the school and
    must never grow a business field: the real domains live in M01-M14.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    section_id = models.UUIDField(null=True, blank=True, db_index=True)
    subject_person_id = models.UUIDField(null=True, blank=True, db_index=True)
    body = models.TextField()
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "demo_note"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["school_id", "created_at", "id"])]

    def __str__(self) -> str:
        """Return a short identification string for test output."""
        return f"DemoNote {self.id} v{self.version}"
