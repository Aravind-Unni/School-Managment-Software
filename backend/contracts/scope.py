"""Scope facts passed to Access when deciding an action.

The split between RelationshipFacts and ScopeFacts exists to break a cycle:
Access must not call Registry to learn whether G1 guards S1, because Registry
calls Access to authorise its own reads. Instead the *host* scope resolver asks
Registry once for RelationshipFacts and folds the answer into ScopeFacts.

Does not handle: deciding anything. These are inputs to a policy, not a policy.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from uuid import UUID


class Relationship(enum.StrEnum):
    """How the actor is connected to the subject person, if at all."""

    NONE = "none"
    SELF = "self"
    GUARDIAN = "guardian"
    ASSIGNED_TEACHER = "assigned_teacher"
    CLASS_TEACHER = "class_teacher"


@dataclass(frozen=True, slots=True)
class RelationshipFacts:
    """Registry's answer about actor-to-subject linkage.

    Returned by RegistryPort. This is a separate DTO from ScopeFacts on purpose:
    it is the only thing Registry is asked for, so the dependency stays
    one-directional and Access never calls Registry recursively.

    Extended additively for M01, which needs the school, the full set of sections
    and subjects the relationship covers, and an expiry:

      * ``school_id`` -- present so a caller can detect a cross-school answer
        without a second lookup. Optional only for backward compatibility with
        callers written against the B00 shape.
      * ``section_ids`` / ``subject_ids`` -- a teacher may relate to a pupil
        through several sections or subjects at once. ``section_id`` remains as
        the single primary section.
      * ``valid_until`` -- a guardianship or posting can lapse; None means
        open-ended.

    Does not handle: authorising anything. These are inputs to a policy.
    """

    actor_id: UUID
    subject_person_id: UUID
    relationship: Relationship
    section_id: UUID | None = None
    effective_date: date | None = None
    school_id: UUID | None = None
    section_ids: tuple[UUID, ...] = ()
    subject_ids: tuple[UUID, ...] = ()
    valid_until: date | None = None

    def __post_init__(self) -> None:
        """Keep ``section_id`` and ``section_ids`` consistent.

        A caller that set only the singular field should still see it in the
        plural one, so a policy written against ``section_ids`` cannot silently
        miss a relationship expressed the older way.
        """
        if self.section_id is not None and self.section_id not in self.section_ids:
            object.__setattr__(self, "section_ids", (self.section_id, *self.section_ids))

    def is_active_on(self, effective_date: date) -> bool:
        """Return whether the relationship is still in force on a date.

        A lapsed guardianship must not authorise a read. None means open-ended.
        """
        return self.valid_until is None or effective_date <= self.valid_until


@dataclass(frozen=True, slots=True)
class ScopeFacts:
    """Everything a policy needs about *what* is being acted upon.

    ``resource_school_id`` is mandatory and is compared against
    RequestContext.school_id by every policy; a mismatch is a 404, not a 403.

    Does not handle: the action name or the actor. Those are separate arguments
    to AccessPort.check so that one ScopeFacts can be reused across actions.
    """

    resource_school_id: UUID
    subject_person_id: UUID | None = None
    section_id: UUID | None = None
    subject_id: UUID | None = None
    relationship: Relationship | None = None
    effective_date: date | None = None

    @classmethod
    def from_relationship(
        cls,
        *,
        resource_school_id: UUID,
        facts: RelationshipFacts,
        subject_id: UUID | None = None,
    ) -> ScopeFacts:
        """Fold Registry's RelationshipFacts into ScopeFacts.

        This is the only sanctioned way to populate ``relationship``; doing it
        by hand inside a module is how the recursive-call bug comes back.

        Does not handle: verifying that ``facts`` came from the same school.
        The host resolver checks that before calling this.
        """
        return cls(
            resource_school_id=resource_school_id,
            subject_person_id=facts.subject_person_id,
            section_id=facts.section_id,
            # When Registry reported subjects and the caller named none, carry the
            # first through, so a subject-scoped rule can match without the caller
            # having to re-read the facts it just folded in.
            subject_id=subject_id or (facts.subject_ids[0] if facts.subject_ids else None),
            relationship=facts.relationship,
            effective_date=facts.effective_date,
        )
