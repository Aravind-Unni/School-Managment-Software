"""Grant scope kinds. Plain enum, deliberately free of Django.

The permission catalogue references these, and the catalogue must be importable
without a configured Django settings module -- ``scripts/arch_check.py`` and the
contract suite read it with no database in sight. Keeping the enum here is what
makes that possible.
"""

from __future__ import annotations

import enum


class ScopeType(enum.StrEnum):
    """How far a grant reaches.

    ``SELF`` is narrower than ``SECTION``: it authorises an action only on the
    grantee's own records, which is what lets a guardian read their own child's
    data without holding any section-wide permission.
    """

    SCHOOL = "school"
    SECTION = "section"
    SUBJECT = "subject"
    SELF = "self"

    @property
    def needs_scope_id(self) -> bool:
        """Return whether a grant at this scope must name a target object.

        School-wide and self grants must NOT carry a scope id; section and subject
        grants must. Enforced in the database too, so a bad row cannot exist even
        if a service forgets.
        """
        return self in (ScopeType.SECTION, ScopeType.SUBJECT)


#: Django `choices` for the model field, derived so the two cannot drift.
SCOPE_TYPE_CHOICES: tuple[tuple[str, str], ...] = tuple(
    (member.value, member.value.replace("_", " ").title()) for member in ScopeType
)
