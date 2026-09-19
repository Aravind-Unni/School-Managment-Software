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

    Returned by RegistryPort.relationship_facts. This is a separate DTO from
    ScopeFacts on purpose: it is the only thing Registry is asked for, so the
    dependency stays one-directional.

    Does not handle: school scoping. The caller already knows the school.
    """

    actor_id: UUID
    subject_person_id: UUID
    relationship: Relationship
    section_id: UUID | None = None
    effective_date: date | None = None


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
            subject_id=subject_id,
            relationship=facts.relationship,
            effective_date=facts.effective_date,
        )
