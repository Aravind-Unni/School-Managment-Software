"""Host-owned resolver: Registry facts -> ScopeFacts -> Access decision.

This is the only place that calls RegistryPort.relationship_facts and folds the
answer into ScopeFacts. Keeping it here, in the host, is what prevents the
recursive policy/registry call: Access never needs Registry, because the host
already asked.

A module calls ``resolver.require(context, action, subject_person_id=...)`` and
gets either None or the right exception. It never assembles a relationship
itself.

Does not handle: row-level list filtering. A list endpoint asks Access for the
sections it may see and filters on that, rather than resolving per row.
"""

from __future__ import annotations

from uuid import UUID

from contracts.identity import RequestContext
from contracts.ports import AccessPort, RegistryPort
from contracts.scope import Relationship, RelationshipFacts, ScopeFacts


class ScopeResolver:
    """Resolves and enforces scope for one request.

    Holds an AccessPort and a RegistryPort. Both are Protocols, so standalone
    mode passes fakes and integrated mode passes real providers with no change
    here.
    """

    def __init__(self, *, access: AccessPort, registry: RegistryPort) -> None:
        """Store the two ports this resolver coordinates."""
        self._access = access
        self._registry = registry

    def facts_for_subject(
        self,
        context: RequestContext,
        *,
        subject_person_id: UUID,
        resource_school_id: UUID | None = None,
        subject_id: UUID | None = None,
    ) -> ScopeFacts:
        """Build ScopeFacts about one person, asking Registry exactly once.

        ``resource_school_id`` defaults to the context's school. Passing it
        explicitly is how a caller tests the cross-tenant path, and a mismatch is
        resolved by Access as a 404.

        Does not handle: caching. One request may resolve the same subject twice;
        that is two cheap in-process calls, and caching here would make stale
        relationships possible mid-request.
        """
        school_id = resource_school_id or context.school_id
        facts: RelationshipFacts = self._registry.relationship_facts(context, subject_person_id)
        if facts.subject_person_id != subject_person_id:
            raise ValueError(
                "registry returned facts for a different subject; "
                f"asked {subject_person_id}, got {facts.subject_person_id}"
            )
        return ScopeFacts.from_relationship(
            resource_school_id=school_id,
            facts=facts,
            subject_id=subject_id,
        )

    def require(
        self,
        context: RequestContext,
        action: str,
        *,
        subject_person_id: UUID | None = None,
        resource_school_id: UUID | None = None,
        section_id: UUID | None = None,
        subject_id: UUID | None = None,
    ) -> ScopeFacts:
        """Authorise ``action`` and return the ScopeFacts that authorised it.

        When ``subject_person_id`` is given, Registry is consulted for the
        relationship. When it is not, the facts carry no relationship and only
        school-scoped rules can match -- which is correct for staff-wide actions.

        Raises ActionDenied, ObjectInaccessible or StaleAuth. Returns the facts so
        the caller can reuse them for a second check without re-resolving.
        """
        if subject_person_id is not None:
            facts = self.facts_for_subject(
                context,
                subject_person_id=subject_person_id,
                resource_school_id=resource_school_id,
                subject_id=subject_id,
            )
            if section_id is not None and facts.section_id != section_id:
                facts = ScopeFacts(
                    resource_school_id=facts.resource_school_id,
                    subject_person_id=facts.subject_person_id,
                    section_id=section_id,
                    subject_id=facts.subject_id,
                    relationship=Relationship.NONE,
                    effective_date=facts.effective_date,
                )
        else:
            facts = ScopeFacts(
                resource_school_id=resource_school_id or context.school_id,
                section_id=section_id,
                subject_id=subject_id,
            )

        self._access.check(context, action, facts)
        return facts

    def allows(
        self,
        context: RequestContext,
        action: str,
        *,
        subject_person_id: UUID | None = None,
    ) -> bool:
        """Return whether the action is allowed, for navigation metadata only.

        Never use on a write path: the write must call ``require`` so that the
        denial and its reason are raised, logged and audited.
        """
        try:
            self.require(context, action, subject_person_id=subject_person_id)
        except Exception:
            return False
        return True
