"""Deterministic fake Registry adapter.

Answers only RelationshipFacts, from the committed fixture set. It deliberately
exposes nothing else: the narrower this fake is, the harder it is for a module
to grow a hidden dependency on Registry internals.

Does not handle: person or section CRUD. That is M02's real implementation.
"""

from __future__ import annotations

from uuid import UUID

from contracts.identity import RequestContext
from contracts.scope import Relationship, RelationshipFacts

from .. import fixtures
from .failures import FailureInjector


class FakeRegistry:
    """Fixture-backed RegistryPort implementation.

    Relationship resolution is pure table lookup over
    ``shared.fixtures``: G1 guards S1/S2, G2 guards only S3, T1 is class teacher
    of C1, T2 is unassigned. Anything else resolves to Relationship.NONE.
    """

    def __init__(self, *, failures: FailureInjector | None = None) -> None:
        """Build the adapter with optional failure injection."""
        self._failures = failures or FailureInjector()

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return the fixture relationship between actor and subject.

        Returns NONE rather than raising for an unrelated pair, and also for a
        subject in another school: leaking 'exists but not yours' through a
        different exception type would defeat the 404 rule upstream.

        Does not handle: authorising the caller. The host folds this answer into
        ScopeFacts and asks Access.
        """
        self._failures.maybe_fail("registry.relationship_facts")

        actor = context.actor_id
        section_id = fixtures.section_of(subject_person_id)

        if actor == subject_person_id:
            relationship = Relationship.SELF
        elif fixtures.guards(actor, subject_person_id):
            relationship = Relationship.GUARDIAN
        elif section_id is not None and fixtures.teaches(actor, section_id):
            relationship = (
                Relationship.CLASS_TEACHER
                if any(
                    a.teacher_id == actor and a.section_id == section_id and a.is_class_teacher
                    for a in fixtures.TEACHER_ASSIGNMENTS
                )
                else Relationship.ASSIGNED_TEACHER
            )
        else:
            relationship = Relationship.NONE

        return RelationshipFacts(
            actor_id=actor,
            subject_person_id=subject_person_id,
            relationship=relationship,
            section_id=section_id,
            effective_date=fixtures.TERM_SAMPLE_DATE,
        )
