"""Sessions, roles and accounts endpoints.

``/accounts`` is the protected business endpoint the acceptance tests use to prove a
password-only session is refused before the factor completes.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.pagination import Page, clamp_page_size
from contracts.scope import ScopeFacts
from contracts.values import school_date
from shared.http.pagination import paginate_queryset

from ..models.accounts import FactorState
from ..scopes import ScopeType
from ..services import roles as role_service
from ..services import sessions as session_service
from . import deps
from .serializers import (
    AccountCollectionResponse,
    ErrorEnvelopeResponse,
    RoleCollectionResponse,
    RoleResponse,
    RoleWriteRequest,
    SessionCollectionResponse,
    SessionResponse,
)

#: Error responses M01 endpoints can return. Declared once so the generated client
#: carries the full error surface, not just the happy path. The authoritative list is
#: contracts/M01/error-codes.json.
COMMON_ERRORS = {
    400: OpenApiResponse(ErrorEnvelopeResponse, "Client asserted its own identity."),
    401: OpenApiResponse(
        ErrorEnvelopeResponse, "Unauthenticated, expired challenge, or step-up required."
    ),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible to you."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Validation failed, or an unknown field."),
    429: OpenApiResponse(ErrorEnvelopeResponse, "Throttled; carries Retry-After."),
}


class SessionCollectionView(APIView):
    """GET /sessions -- the caller's OWN sessions, never anyone else's."""

    @extend_schema(
        operation_id="sessions_list",
        summary="List the caller's own sessions",
        parameters=[
            OpenApiParameter("cursor", str, description="Opaque keyset cursor. Do not parse."),
            OpenApiParameter("page_size", int, description="Capped server-side."),
        ],
        responses={200: SessionCollectionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return a cursor page of the caller's sessions.

        Scoped to the calling user in the query itself, so there is no parameter an
        administrator could supply to view another user's sessions. An administrator
        must never see another account's factor or session detail.
        """
        from ..models import Session

        context = deps.require_context(request)
        current = deps.require_session(request)
        deps.access_service().check(context, "auth.read_own_session", _self_scope(context))

        queryset = Session.objects.filter(user_id=context.actor_id).order_by(
            "-created_at", "id"
        )
        page = paginate_queryset(
            queryset,
            cursor=request.query_params.get("cursor") or None,
            page_size=clamp_page_size(_int_or_none(request.query_params.get("page_size"))),
            order_by=("-created_at", "id"),
            cursor_fields=lambda row: {
                "created_at": row.created_at.isoformat(),
                "id": str(row.id),
            },
        )
        return Response(
            Page(
                items=tuple(
                    session_service.describe_session(row, current_session_id=current.id)
                    for row in page.items
                ),
                next_cursor=page.next_cursor,
            ).to_wire()
        )


class SessionRevokeView(APIView):
    """POST /sessions/{session_id}/revoke -- revoke one of the caller's sessions."""

    @extend_schema(
        operation_id="sessions_revoke",
        summary="Revoke one of the caller's sessions",
        request=None,
        responses={200: SessionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, session_id) -> Response:
        """Revoke a session the caller owns.

        A session belonging to another account yields 404, not 403: revealing that
        the id is valid elsewhere would leak the existence of other sessions.
        """
        from ..models import Session

        context = deps.require_context(request)
        current = deps.require_session(request)
        deps.access_service().check(context, "auth.revoke_own_session", _self_scope(context))

        target = Session.objects.filter(id=session_id, user_id=context.actor_id).first()
        if target is None:
            raise ObjectInaccessible("error.object_inaccessible")

        with transaction.atomic():
            session_service.revoke_session(target, instant=deps.clock().now())
            deps.platform().record_audit(
                context, "auth.session_revoked", target.id, {"revoked": True}
            )
        target.refresh_from_db()
        return Response(session_service.describe_session(target, current_session_id=current.id))


class RoleCollectionView(APIView):
    """GET /roles and POST /roles."""

    @extend_schema(
        operation_id="roles_list",
        summary="List roles in the caller's school",
        parameters=[
            OpenApiParameter("cursor", str, description="Opaque keyset cursor. Do not parse."),
            OpenApiParameter("page_size", int, description="Capped server-side."),
        ],
        responses={200: RoleCollectionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return a cursor page of roles in the caller's school."""
        from ..models import Role

        context = deps.require_context(request)
        deps.access_service().require_action(context, "roles.manage", _school_scope(context))

        queryset = (
            Role.objects.filter(school_id=context.school_id)
            .prefetch_related("grants")
            .order_by("name", "id")
        )
        page = paginate_queryset(
            queryset,
            cursor=request.query_params.get("cursor") or None,
            page_size=clamp_page_size(_int_or_none(request.query_params.get("page_size"))),
            order_by=("name", "id"),
            cursor_fields=lambda row: {"name": row.name, "id": str(row.id)},
        )
        return Response(
            Page(
                items=tuple(role_service.describe_role(row) for row in page.items),
                next_cursor=page.next_cursor,
            ).to_wire()
        )

    @extend_schema(
        operation_id="roles_create",
        summary="Create a role",
        request=RoleWriteRequest,
        responses={201: RoleResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a role, rejecting escalation and unenforceable grants."""
        from ..models import Grant, Role

        payload = RoleWriteRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        if payload.validated_data.get("expected_version") is not None:
            raise ValidationFailed("error.unknown_field")

        context = deps.require_context(request)
        clock = deps.clock()
        access = deps.access_service()
        access.require_action(context, "roles.manage", _school_scope(context))

        grants = _parse_grants(payload.validated_data["grants"])
        effective = school_date(clock.now())
        role_service.validate_grant_shape(grants)
        role_service.assert_no_escalation(
            requested=grants,
            held=access.held_grants(context),
            effective_date=effective,
        )

        with transaction.atomic():
            role = Role.objects.create(
                school_id=context.school_id,
                name=payload.validated_data["name"],
                requires_two_factor=payload.validated_data.get("requires_two_factor", False),
                created_at=clock.now(),
                updated_at=clock.now(),
            )
            Grant.objects.bulk_create(
                [
                    Grant(
                        school_id=context.school_id,
                        role=role,
                        action=grant.action,
                        scope_type=grant.scope_type.value,
                        scope_id=grant.scope_id,
                        valid_from=grant.valid_from,
                        valid_to=grant.valid_to,
                        created_at=clock.now(),
                    )
                    for grant in grants
                ]
            )
            deps.platform().record_audit(context, "roles.created", role.id, {"name": role.name})
        role.refresh_from_db()
        return Response(role_service.describe_role(role), status=201)


class RoleGrantsView(APIView):
    """PUT /roles/{role_id}/grants."""

    @extend_schema(
        operation_id="roles_replace_grants",
        summary="Replace a role's grants",
        request=RoleWriteRequest,
        responses={200: RoleResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, role_id) -> Response:
        """Replace a role's grants under optimistic concurrency."""
        from ..models import Role

        payload = RoleWriteRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        expected_version = payload.validated_data.get("expected_version")
        if expected_version is None:
            # A missing expected_version would be a last-write-wins overwrite.
            raise ValidationFailed("error.validation_failed")

        context = deps.require_context(request)
        clock = deps.clock()
        access = deps.access_service()
        access.require_action(context, "roles.manage", _school_scope(context))

        role = Role.objects.filter(id=role_id, school_id=context.school_id).first()
        if role is None:
            raise ObjectInaccessible("error.object_inaccessible")

        grants = _parse_grants(payload.validated_data["grants"])
        updated = role_service.replace_grants(
            role=role,
            grants=grants,
            expected_version=expected_version,
            actor_grants=access.held_grants(context),
            effective_date=school_date(clock.now()),
            instant=clock.now(),
        )
        platform = deps.platform()
        platform.record_audit(
            context, "roles.grants_replaced", updated.id, {"version": updated.version}
        )
        platform.append_event(
            context,
            "RoleGrantsChanged.v1",
            updated.id,
            updated.version,
            {
                "role_id": str(updated.id),
                "user_ids": [str(link.user_id) for link in updated.user_links.all()],
                "policy_version": _policy_version(context.school_id),
            },
        )
        updated.refresh_from_db()
        return Response(role_service.describe_role(updated))


class AccountCollectionView(APIView):
    """GET /accounts -- the protected business endpoint. POST creates one."""

    def post(self, request: Request) -> Response:
        """Create an account; see ``account_views.AccountCreateView``."""
        from .account_views import AccountCreateView

        return AccountCreateView().post(request)

    @extend_schema(
        operation_id="accounts_list",
        summary="List accounts in the caller's school",
        parameters=[
            OpenApiParameter("cursor", str, description="Opaque keyset cursor. Do not parse."),
            OpenApiParameter("page_size", int, description="Capped server-side."),
        ],
        responses={200: AccountCollectionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return a cursor page of accounts.

        Requires ``accounts.manage``, which the catalogue marks as needing a fresh
        second factor -- so a password-only session is refused here with 401. That is
        the acceptance case "business API refused before 2FA completes".
        """
        from ..models import TotpFactor, User

        context = deps.require_context(request)
        deps.access_service().require_action(context, "accounts.manage", _school_scope(context))

        with_factor = set(
            TotpFactor.objects.filter(
                school_id=context.school_id, state=FactorState.ACTIVE
            ).values_list("user_id", flat=True)
        )
        queryset = (
            User.objects.filter(school_id=context.school_id)
            .prefetch_related("role_links__role")
            .order_by("login_name", "id")
        )
        page = paginate_queryset(
            queryset,
            cursor=request.query_params.get("cursor") or None,
            page_size=clamp_page_size(_int_or_none(request.query_params.get("page_size"))),
            order_by=("login_name", "id"),
            cursor_fields=lambda row: {"login_name": row.login_name, "id": str(row.id)},
        )
        return Response(
            Page(
                items=tuple(
                    _describe_account(row, has_factor=row.id in with_factor)
                    for row in page.items
                ),
                next_cursor=page.next_cursor,
            ).to_wire()
        )


# --- helpers ---------------------------------------------------------------


def _describe_account(user, *, has_factor: bool) -> dict[str, object]:
    """Serialise an account. Never exposes credential material or another's factor."""
    links = list(user.role_links.all())
    return {
        "id": str(user.id),
        "school_id": str(user.school_id),
        "login_name": user.login_name,
        "display_name": user.display_name,
        "active": user.active,
        "version": user.version,
        "role_ids": [str(link.role_id) for link in links],
        "has_active_factor": has_factor,
        "two_factor_required": any(link.role.requires_two_factor for link in links),
    }


def _parse_grants(raw) -> tuple[role_service.GrantInput, ...]:
    """Convert validated grant bodies into service inputs."""
    return tuple(
        role_service.GrantInput(
            action=item["action"],
            scope_type=ScopeType(item["scope_type"]),
            scope_id=item.get("scope_id"),
            valid_from=item["valid_from"],
            valid_to=item.get("valid_to"),
        )
        for item in raw
    )


def _policy_version(school_id) -> int:
    """Return the school's current policy version, defaulting to 1."""
    from ..models import PolicyVersion

    row = PolicyVersion.objects.filter(school_id=school_id).values("version").first()
    return row["version"] if row else 1


def _self_scope(context) -> ScopeFacts:
    """Return ScopeFacts for the actor acting on their own account."""
    return ScopeFacts(
        resource_school_id=context.school_id,
        subject_person_id=context.actor_id,
        effective_date=school_date(context.auth_time),
    )


def _school_scope(context) -> ScopeFacts:
    """Return ScopeFacts for a school-wide action."""
    return ScopeFacts(
        resource_school_id=context.school_id,
        effective_date=school_date(context.auth_time),
    )


def _int_or_none(raw: str | None) -> int | None:
    """Parse an optional integer query parameter, tolerating junk."""
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
