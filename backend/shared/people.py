"""Questions about the acting person that several modules ask the same way.

Answered through RegistryPort, never from the request: the client cannot tell
the server what kind of person it is.
"""

from __future__ import annotations

from uuid import UUID, uuid5

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


#: The grant that marks school-wide oversight (principal, academic office):
#: its holder may read any pupil's records without a teaching or family link.
SCHOOL_WIDE_READ_ACTION = "reports.read"


def is_school_wide_reader(access, context: RequestContext, on) -> bool:
    """Return whether the actor holds school-wide oversight of pupil records.

    Teachers hold subject/class relationships instead and do not pass this.
    Assumes ``access`` is an AccessPort. Does not grant any write.
    """
    from contracts.scope import ScopeFacts

    decision = access.authorize(
        context,
        SCHOOL_WIDE_READ_ACTION,
        ScopeFacts(resource_school_id=context.school_id, effective_date=on),
    )
    return decision.allowed


def system_actor_id(school_id) -> UUID:
    """Return the id of the school's "automatic jobs" account.

    Created by install_school with read-only grants and a password that can
    never match, so scheduled work (nightly projections) runs as a real,
    auditable account that no person can sign in as.
    """
    return uuid5(UUID(str(school_id)), "install.system-account")
