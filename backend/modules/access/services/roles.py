"""Role and grant administration.

Three protections, each of which is a real failure mode rather than a formality:

  * **No self-escalation.** An actor may only grant what they themselves hold, in a
    scope no wider than their own. Otherwise ``roles.delegate`` would be equivalent
    to owner.
  * **No cycles.** A role graph with a cycle would make "what can this account do"
    non-terminating.
  * **Last active owner is preserved.** The change that would leave a school with no
    owner is refused, because there would then be nobody able to grant it back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    FieldError,
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)

from ..permissions import lookup_permission
from ..scopes import ScopeType
from .policy import GrantFact

#: Depth-first search colours for the role-graph cycle check.
WHITE, GREY, BLACK = 0, 1, 2


@dataclass(frozen=True, slots=True)
class GrantInput:
    """One requested grant, as parsed from a request body."""

    action: str
    scope_type: ScopeType
    scope_id: UUID | None
    valid_from: date
    valid_to: date | None

    def as_fact(self) -> GrantFact:
        """Return the pure-policy equivalent."""
        return GrantFact(
            action=self.action,
            scope_type=self.scope_type,
            scope_id=self.scope_id,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
        )


def validate_grant_shape(grants: tuple[GrantInput, ...]) -> None:
    """Reject grants the system could never enforce.

    Checks the action is in the closed catalogue, that the scope kind is one the
    action supports, and that scope_id is present exactly when the scope needs it.
    Rejecting here means an unenforceable grant is never stored -- a stored grant
    that cannot be evaluated is worse than a refused one.
    """
    problems: list[FieldError] = []
    for index, grant in enumerate(grants):
        spec = lookup_permission(grant.action)
        if spec is None:
            problems.append(FieldError(f"grants[{index}].action", "error.unknown_permission"))
            continue
        if grant.scope_type not in spec.allowed_scopes:
            problems.append(
                FieldError(f"grants[{index}].scope_type", "error.scope_not_allowed")
            )
        if grant.scope_type.needs_scope_id and grant.scope_id is None:
            problems.append(FieldError(f"grants[{index}].scope_id", "error.scope_id_required"))
        if not grant.scope_type.needs_scope_id and grant.scope_id is not None:
            problems.append(FieldError(f"grants[{index}].scope_id", "error.scope_id_forbidden"))
        if grant.valid_to is not None and grant.valid_to < grant.valid_from:
            problems.append(
                FieldError(f"grants[{index}].valid_to", "error.valid_to_before_from")
            )
    if problems:
        raise ValidationFailed("error.validation_failed", field_errors=tuple(problems))


def scope_is_within(candidate: GrantInput, held: GrantFact) -> bool:
    """Return whether ``candidate``'s scope is no wider than ``held``'s.

    The ordering is SCHOOL > SECTION/SUBJECT > SELF. A school-wide holder may grant
    anything; a section holder may grant only that exact section. Section and subject
    are NOT comparable to each other -- holding section C1 does not let you grant
    subject Maths, because they slice the data differently.
    """
    if held.action != candidate.action:
        return False
    if held.scope_type is ScopeType.SCHOOL:
        return True
    if held.scope_type is candidate.scope_type:
        if held.scope_type is ScopeType.SELF:
            return True
        return held.scope_id == candidate.scope_id
    if candidate.scope_type is ScopeType.SELF:
        # Narrowing to self is always permitted from any wider scope.
        return True
    return False


def assert_no_escalation(
    *, requested: tuple[GrantInput, ...], held: tuple[GrantFact, ...], effective_date: date
) -> None:
    """Refuse a grant the actor does not themselves hold, within scope.

    Only grants IN FORCE count as held: an actor cannot delegate a permission whose
    own window has lapsed.
    """
    in_force = tuple(g for g in held if g.is_in_force(effective_date))
    problems: list[FieldError] = []
    for index, candidate in enumerate(requested):
        if not any(scope_is_within(candidate, holder) for holder in in_force):
            problems.append(FieldError(f"grants[{index}].action", "error.grant_escalation"))
    if problems:
        raise ValidationFailed("error.grant_escalation", field_errors=tuple(problems))


def assert_acyclic(edges: dict[UUID, set[UUID]]) -> None:
    """Refuse a role graph containing a cycle.

    Iterative depth-first search with an explicit stack: a recursive walk would blow
    the Python stack on a deep graph, and a school with many nested roles is exactly
    where that would bite.
    """
    colour: dict[UUID, int] = dict.fromkeys(edges, WHITE)

    for root in list(edges):
        if colour.get(root, WHITE) != WHITE:
            continue
        stack: list[tuple[UUID, bool]] = [(root, False)]
        while stack:
            node, finished = stack.pop()
            if finished:
                colour[node] = BLACK
                continue
            if colour.get(node, WHITE) == GREY:
                raise ValidationFailed("error.role_cycle")
            if colour.get(node, WHITE) == BLACK:
                continue
            colour[node] = GREY
            stack.append((node, True))
            for child in edges.get(node, ()):
                if colour.get(child, WHITE) == GREY:
                    raise ValidationFailed("error.role_cycle")
                if colour.get(child, WHITE) == WHITE:
                    stack.append((child, False))


def assert_owner_survives(*, school_id: UUID, role, removing_owner_grant: bool) -> None:
    """Refuse a change that would leave the school with no active owner.

    Counts accounts holding an owner role through an ACTIVE account. If the role
    being edited is the only owner role and the edit strips its owner status, there
    would be nobody left able to grant it back -- an unrecoverable state.
    """
    from ..models import Role, UserRole

    if not (role.is_owner_role and removing_owner_grant):
        return

    other_owner_roles = Role.objects.filter(school_id=school_id, is_owner_role=True).exclude(
        id=role.id
    )
    if other_owner_roles.exists():
        holders = UserRole.objects.filter(
            role__in=other_owner_roles, user__active=True
        ).exists()
        if holders:
            return
    raise StateConflict("error.last_owner_protected")


def replace_grants(
    *,
    role,
    grants: tuple[GrantInput, ...],
    expected_version: int,
    actor_grants: tuple[GrantFact, ...],
    effective_date: date,
    instant: datetime,
) -> object:
    """Replace a role's grants under optimistic concurrency.

    Order is deliberate: shape, then escalation, then version, then last-owner. The
    cheap deterministic checks run first so a malformed request does not consume a
    row lock, and the version check runs inside the transaction that writes.
    """
    from ..models import Grant, PolicyVersion, Role

    validate_grant_shape(grants)
    assert_no_escalation(requested=grants, held=actor_grants, effective_date=effective_date)

    with transaction.atomic():
        locked = Role.objects.select_for_update().filter(pk=role.pk).first()
        if locked is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if locked.version != expected_version:
            raise VersionConflict(
                expected_version=expected_version, actual_version=locked.version
            )

        keeps_owner = any(
            grant.action == "roles.manage" and grant.scope_type is ScopeType.SCHOOL
            for grant in grants
        )
        assert_owner_survives(
            school_id=locked.school_id, role=locked, removing_owner_grant=not keeps_owner
        )

        Grant.objects.filter(role=locked).delete()
        Grant.objects.bulk_create(
            [
                Grant(
                    school_id=locked.school_id,
                    role=locked,
                    action=grant.action,
                    scope_type=grant.scope_type.value,
                    scope_id=grant.scope_id,
                    valid_from=grant.valid_from,
                    valid_to=grant.valid_to,
                    created_at=instant,
                )
                for grant in grants
            ]
        )
        locked.version += 1
        locked.updated_at = instant
        locked.save(update_fields=["version", "updated_at"])

        policy, _ = PolicyVersion.objects.get_or_create(
            school_id=locked.school_id, defaults={"version": 1, "updated_at": instant}
        )
        PolicyVersion.objects.filter(school_id=locked.school_id).update(
            version=policy.version + 1, updated_at=instant
        )
        return locked


def describe_role(role) -> dict[str, object]:
    """Serialise a role and its grants for the API."""
    return {
        "id": str(role.id),
        "school_id": str(role.school_id),
        "name": role.name,
        "is_owner_role": role.is_owner_role,
        "requires_two_factor": role.requires_two_factor,
        "version": role.version,
        "grants": [
            {
                "action": grant.action,
                "scope_type": grant.scope_type,
                "scope_id": str(grant.scope_id) if grant.scope_id else None,
                "valid_from": grant.valid_from.isoformat(),
                "valid_to": grant.valid_to.isoformat() if grant.valid_to else None,
            }
            for grant in role.grants.all().order_by("action", "scope_type")
        ],
    }
