"""Section-scoped authorisation for M03.

The shared ``ScopeResolver`` answers "how does this actor relate to this PERSON".
Almost every read here is scoped to a SECTION, which it cannot answer: asking it
about a section with no subject person yields facts carrying no relationship, and
a school-scoped policy rule would then let any authenticated actor read any
class's schedule.

So this module resolves section scope itself, using only the frozen
``RegistryPort``:

  * staff  -> ``get_teaching_assignments(actor, date)``, matched on section
  * pupil or guardian -> ``get_relationships(actor, student, date)``, matched on
    ``section_ids``, and only while the relationship is active on that date

It folds the answer into ``ScopeFacts`` and asks Access. **It decides nothing.**
Whether the shared resolver should grow a section entry point is review item 3;
M04 and M05 will want the same thing.

Does not handle: reading any schedule. It answers "may this actor", and the
caller then reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, RelationshipFacts, ScopeFacts


@dataclass(frozen=True, slots=True)
class TimetableScope:
    """Resolves and enforces scope for one request. Holds two ports."""

    access: object
    registry: object

    # --- school-wide staff actions -----------------------------------------

    def require_school_action(self, context: RequestContext, action: str) -> ScopeFacts:
        """Authorise an action that has no single subject person.

        Reference data, the calendar and the draft grid are school-scoped staff
        work. A relationship-gated rule would deny every call here.
        """
        facts = ScopeFacts(resource_school_id=context.school_id)
        self.access.check(context, action, facts)
        return facts

    # --- section-scoped reads ----------------------------------------------

    def require_section_read(
        self,
        context: RequestContext,
        *,
        section_id: UUID,
        on: date,
        student_id: UUID | None = None,
    ) -> ScopeFacts:
        """Authorise reading one section's schedule on a date.

        ``student_id`` is how a pupil or a guardian proves their link to the
        section; staff need not send one, because their link is their dated
        teaching assignment. Naming a pupil does not create a relationship --
        Registry is asked, and a client claim is never trusted.
        """
        if student_id is not None:
            relationship = self._relationship_through_student(
                context, student_id=student_id, section_id=section_id, on=on
            )
        else:
            relationship = self._relationship_through_assignment(
                context, section_id=section_id, on=on
            )
        facts = ScopeFacts(
            resource_school_id=context.school_id,
            subject_person_id=student_id,
            section_id=section_id,
            relationship=relationship,
            effective_date=on,
        )
        self.access.check(context, "timetable.read_section", facts)
        return facts

    def require_student_read(
        self, context: RequestContext, *, student_id: UUID, on: date
    ) -> tuple[ScopeFacts, RelationshipFacts]:
        """Authorise reading one pupil's day, and return the facts that did it.

        The facts carry the pupil's section, so the caller does not ask Registry a
        second time for something it has just been told.
        """
        facts = self._student_facts(context, student_id=student_id, on=on)
        relationship = facts.relationship if facts.is_active_on(on) else Relationship.NONE
        scope = ScopeFacts(
            resource_school_id=context.school_id,
            subject_person_id=student_id,
            section_id=facts.section_id,
            relationship=relationship,
            effective_date=on,
        )
        self.access.check(context, "timetable.read_student", scope)
        return scope, facts

    def require_teacher_read(
        self, context: RequestContext, *, staff_id: UUID, on: date
    ) -> ScopeFacts:
        """Authorise reading one staff member's dated schedule.

        Reading one's OWN day is ``timetable.read_teacher``, gated on SELF.
        Reading someone else's is timetable.edit work -- an academic head building
        cover, not a colleague browsing.
        """
        if staff_id == context.actor_id:
            facts = ScopeFacts(
                resource_school_id=context.school_id,
                subject_person_id=staff_id,
                relationship=Relationship.SELF,
                effective_date=on,
            )
            self.access.check(context, "timetable.read_teacher", facts)
            return facts
        return self.require_school_action(context, "timetable.edit")

    # --- internals ----------------------------------------------------------

    def _student_facts(
        self, context: RequestContext, *, student_id: UUID, on: date
    ) -> RelationshipFacts:
        """Ask Registry once how the actor relates to a pupil on a date.

        A pupil in another school raises ObjectInaccessible (404) rather than
        producing a denial, so a cross-tenant probe cannot tell "exists but not
        yours" from "does not exist".
        """
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.school_id is not None and facts.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return facts

    def _relationship_through_student(
        self, context: RequestContext, *, student_id: UUID, section_id: UUID, on: date
    ) -> Relationship:
        """Return the relationship a pupil link gives to a SECTION.

        NONE unless the link is active on the date and actually covers that
        section: a guardian of a child in C2 is not thereby related to C1.
        """
        facts = self._student_facts(context, student_id=student_id, on=on)
        if not facts.is_active_on(on):
            return Relationship.NONE
        if section_id not in facts.section_ids:
            return Relationship.NONE
        return facts.relationship

    def _relationship_through_assignment(
        self, context: RequestContext, *, section_id: UUID, on: date
    ) -> Relationship:
        """Return the relationship a dated teaching assignment gives to a section.

        ASSIGNED_TEACHER when Registry reports an assignment covering the section
        on that date, NONE otherwise. A lapsed posting gives nothing, which is what
        ``TeachingAssignment.covers`` decides.
        """
        assignments = self.registry.get_teaching_assignments(context, context.actor_id, on)
        for assignment in assignments:
            if assignment.section_id == section_id and assignment.covers(on):
                return Relationship.ASSIGNED_TEACHER
        return Relationship.NONE
