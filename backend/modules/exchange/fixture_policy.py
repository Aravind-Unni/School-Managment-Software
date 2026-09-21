"""Fixture Access grants for standalone/test profiles. Not a production policy.

Two shapes, deliberately different:

  * bulk staff work (``imports.*``, ``reports.export``, ``reportcards.generate``)
    has no single subject, so it is school-scoped with an EMPTY relationship set.
    A relationship-gated rule would deny every collection call.
  * ``reports.read`` IS subject-scoped: a report card belongs to one pupil, so
    the rule names the relationships that may read it. G2, who guards S3 and not
    S1, therefore fails this rule for S1's report card.
"""

from __future__ import annotations

from contracts.scope import Relationship
from shared.fakes.access import PolicyRule

#: Who may read a student-scoped report artifact. CLASS_TEACHER is included
#: alongside ASSIGNED_TEACHER for the same reason M12's ``files.read`` includes
#: it: in the fixture cast the teacher who generates a card is C1's CLASS
#: teacher, and omitting it would deny the generator their own output while
#: changing nothing about the G2 denial this policy exists to prove.
REPORT_READ_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)

FIXTURE_POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(action="imports.validate", allowed_relationships=frozenset()),
    PolicyRule(action="imports.commit", allowed_relationships=frozenset()),
    PolicyRule(action="reports.export", allowed_relationships=frozenset()),
    PolicyRule(action="reportcards.generate", allowed_relationships=frozenset()),
    PolicyRule(action="reports.read", allowed_relationships=REPORT_READ_RELATIONSHIPS),
)
