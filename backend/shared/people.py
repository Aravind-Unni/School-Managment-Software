"""Questions about the acting person that several modules ask the same way.

Answered through RegistryPort, never from the request: the client cannot tell
the server what kind of person it is.
"""

from __future__ import annotations

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

#: Registry kinds that are never staff, whatever grants the account holds.
FAMILY_KINDS = frozenset({"guardian", "student"})


def actor_kind(registry, context: RequestContext) -> str | None:
    """Return "student", "guardian" or "staff" for the actor, or None.

    None means the account is not linked to a Registry person in this school
    (an owner or service account). Does not handle: a registry outage; the
    port's own error propagates.
    """
    try:
        return registry.person_kind(context, context.actor_id)
    except ObjectInaccessible:
        return None


def actor_is_family(registry, context: RequestContext) -> bool:
    """Return True when the actor is a guardian or student in Registry."""
    return actor_kind(registry, context) in FAMILY_KINDS
