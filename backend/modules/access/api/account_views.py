"""Account administration and self-service password endpoints.

Every administrative write requires ``accounts.manage`` (which demands a fresh
second factor) and is audited. Temporary passwords are returned exactly once,
in the response that created them, and never logged.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ObjectInaccessible
from contracts.scope import ScopeFacts
from contracts.values import school_date

from ..services import accounts as account_service
from . import deps
from .serializers import StrictSerializer


class CreateAccountRequest(StrictSerializer):
    """Body for POST /accounts."""

    login_name = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=200)
    person_id = serializers.UUIDField(required=False, allow_null=True)
    role_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)
    password = serializers.CharField(required=False, allow_null=True, trim_whitespace=False)


class ReplaceRolesRequest(StrictSerializer):
    """Body for PUT /accounts/{id}/roles."""

    role_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)
    expected_version = serializers.IntegerField()


class SetActiveRequest(StrictSerializer):
    """Body for POST /accounts/{id}/activate and /deactivate."""

    expected_version = serializers.IntegerField()


class ChangePasswordRequest(StrictSerializer):
    """Body for POST /auth/password."""

    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)


def _describe(user) -> dict[str, object]:
    """Serialise an account without credential material."""
    from ..models import TotpFactor
    from ..models.accounts import FactorState

    links = list(user.role_links.select_related("role"))
    return {
        "id": str(user.id),
        "school_id": str(user.school_id),
        "login_name": user.login_name,
        "display_name": user.display_name,
        "person_id": str(user.person_id) if user.person_id else None,
        "active": user.active,
        "version": user.version,
        "role_ids": [str(link.role_id) for link in links],
        "has_active_factor": TotpFactor.objects.filter(
            user_id=user.id, state=FactorState.ACTIVE
        ).exists(),
        "two_factor_required": any(link.role.requires_two_factor for link in links),
    }


def _require_manage(request: Request):
    """Return (context, access) after enforcing accounts.manage with step-up."""
    context = deps.require_context(request)
    access = deps.access_service()
    access.require_action(
        context,
        "accounts.manage",
        ScopeFacts(
            resource_school_id=context.school_id,
            effective_date=school_date(context.auth_time),
        ),
    )
    return context, access


class AccountCreateView(APIView):
    """POST /accounts -- create a login, optionally for a Registry person."""

    def post(self, request: Request) -> Response:
        """Create the account; return it plus any generated temporary password."""
        payload = CreateAccountRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        context, access = _require_manage(request)
        data = payload.validated_data
        person_id = data.get("person_id")
        if person_id is not None:
            # The person must exist in this school; RegistryPort answers 404 otherwise.
            deps.registry().person_kind(context, person_id)
        now = deps.clock().now()
        created = account_service.create_account(
            school_id=context.school_id,
            login_name=data["login_name"],
            display_name=data["display_name"],
            person_id=person_id,
            role_ids=tuple(data["role_ids"]),
            password=data.get("password"),
            actor_id=context.actor_id,
            held=access.held_grants(context),
            effective_date=school_date(now),
            instant=now,
        )
        deps.platform().record_audit(
            context,
            "accounts.created",
            created.user.id,
            {
                "login_name": created.user.login_name,
                "role_ids": [str(r) for r in data["role_ids"]],
            },
        )
        body = _describe(created.user)
        body["temporary_password"] = created.temporary_password
        return Response(body, status=201)


class AccountRolesView(APIView):
    """PUT /accounts/{id}/roles -- replace an account's roles."""

    def put(self, request: Request, account_id) -> Response:
        """Replace roles under optimistic concurrency; signs the account out."""
        payload = ReplaceRolesRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        context, access = _require_manage(request)
        now = deps.clock().now()
        user = account_service.replace_roles(
            school_id=context.school_id,
            account_id=account_id,
            role_ids=tuple(payload.validated_data["role_ids"]),
            expected_version=payload.validated_data["expected_version"],
            actor_id=context.actor_id,
            held=access.held_grants(context),
            effective_date=school_date(now),
            instant=now,
        )
        deps.platform().record_audit(
            context,
            "accounts.roles_replaced",
            user.id,
            {"role_ids": [str(r) for r in payload.validated_data["role_ids"]]},
        )
        return Response(_describe(user))


class AccountActivationView(APIView):
    """POST /accounts/{id}/activate or /deactivate."""

    active = True

    def post(self, request: Request, account_id) -> Response:
        """Change the account's active flag."""
        payload = SetActiveRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        context, _ = _require_manage(request)
        user = account_service.set_active(
            school_id=context.school_id,
            account_id=account_id,
            active=self.active,
            expected_version=payload.validated_data["expected_version"],
            actor_id=context.actor_id,
            instant=deps.clock().now(),
        )
        deps.platform().record_audit(
            context,
            "accounts.activated" if self.active else "accounts.deactivated",
            user.id,
            {},
        )
        return Response(_describe(user))


class AccountDeactivateView(AccountActivationView):
    """POST /accounts/{id}/deactivate."""

    active = False


class AccountPasswordResetView(APIView):
    """POST /accounts/{id}/reset-password -- issue a new temporary password."""

    def post(self, request: Request, account_id) -> Response:
        """Return the account and its new temporary password, once."""
        context, _ = _require_manage(request)
        user, temporary = account_service.reset_password(
            school_id=context.school_id,
            account_id=account_id,
            actor_id=context.actor_id,
            instant=deps.clock().now(),
        )
        deps.platform().record_audit(context, "accounts.password_reset", user.id, {})
        body = _describe(user)
        body["temporary_password"] = temporary
        return Response(body)


class AccountDetailView(APIView):
    """GET /accounts/{id}."""

    def get(self, request: Request, account_id) -> Response:
        """Return one account of the caller's school."""
        from ..models import User

        context, _ = _require_manage(request)
        user = User.objects.filter(id=account_id, school_id=context.school_id).first()
        if user is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return Response(_describe(user))


class ChangeOwnPasswordView(APIView):
    """POST /auth/password -- change one's own password."""

    def post(self, request: Request) -> Response:
        """Verify the current password, set the new one, sign out other sessions."""
        payload = ChangePasswordRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        context = deps.require_context(request)
        session = deps.require_session(request)
        account_service.change_own_password(
            user=session.user,
            current_password=payload.validated_data["current_password"],
            new_password=payload.validated_data["new_password"],
            keep_session_id=session.id,
            instant=deps.clock().now(),
        )
        deps.platform().record_audit(context, "auth.password_changed", session.user.id, {})
        return Response(status=204)
