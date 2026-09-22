"""Authentication endpoints: login, 2FA, enrolment, recovery, logout.

Views are thin. Every rule lives in a service, so a worker or an export invoking the
same service gets the same decision -- which is the point of "access checks apply to
API, service, workers, exports and private files".
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import Unauthenticated
from contracts.values import school_date

from ..cookies import clear_session_cookie, set_session_cookie
from ..services import factors, login, sessions
from . import deps
from .serializers import (
    AuthenticatedResponse,
    ChallengeResponse,
    EnrolConfirmRequest,
    EnrolStartResponse,
    ErrorEnvelopeResponse,
    LoginRequest,
    PasswordConfirmRequest,
    RecoverRequest,
    RecoveryCaseResponse,
    RecoveryCodesResponse,
    ResetRequestBody,
    RevokedResponse,
    TotpVerifyRequest,
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


class LoginView(APIView):
    """POST /auth/login -- password step, returns a challenge, never a session."""

    @extend_schema(
        operation_id="auth_login",
        summary="Begin authentication and receive a challenge",
        request=LoginRequest,
        responses={201: ChallengeResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Verify the password and issue a pre-authentication challenge.

        Returns 201: a challenge is a created resource, and deliberately not a
        session. An unknown login and a wrong password are indistinguishable.
        """
        payload = LoginRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        clock = deps.clock()

        issued, _user = login.begin_login(
            school_id=_deployment_school_id(),
            login_name=payload.validated_data["login_name"],
            password=payload.validated_data["password"],
            instant=clock.now(),
            remote_addr=deps.remote_addr(request),
        )

        body = {
            "challenge_id": str(issued.challenge_id),
            "expires_at": issued.expires_at.isoformat(),
            "next_action": issued.next_action,
        }

        # An account policy does not require a factor for is authenticated by the
        # password alone. The challenge is still consumed, so it cannot be replayed.
        if issued.next_action == login.NextAction.AUTHENTICATED:
            session = login.authenticate_without_factor(
                challenge_id=issued.challenge_id,
                instant=clock.now(),
                user_agent=deps.user_agent(request),
            )
            response = Response(body, status=201)
            set_session_cookie(response, session.token)
            return response

        return Response(body, status=201)


class TotpVerifyView(APIView):
    """POST /auth/2fa/verify -- complete the challenge and rotate the session."""

    @extend_schema(
        operation_id="auth_totp_verify",
        summary="Complete the challenge with a TOTP code",
        request=TotpVerifyRequest,
        responses={200: AuthenticatedResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Verify a TOTP code and issue a business session."""
        payload = TotpVerifyRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        clock = deps.clock()

        issued = login.verify_totp_and_authenticate(
            challenge_id=payload.validated_data["challenge_id"],
            code=payload.validated_data["code"],
            instant=clock.now(),
            remote_addr=deps.remote_addr(request),
            user_agent=deps.user_agent(request),
        )
        response = Response(
            {
                "authenticated": True,
                "auth_level": issued.auth_level,
                "actor_id": None,
                "school_id": None,
                "auth_time": issued.auth_time.isoformat(),
            }
        )
        set_session_cookie(response, issued.token)
        return _fill_identity(response, issued.session_id)


class RecoverView(APIView):
    """POST /auth/2fa/recover -- single-use recovery code sign-in."""

    @extend_schema(
        operation_id="auth_factor_recover",
        summary="Sign in with a single-use recovery code",
        request=RecoverRequest,
        responses={200: AuthenticatedResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Consume a recovery code and issue a recovery-level session.

        Revokes the old factor and every session, and permits factor re-enrolment
        only. There is no SMS fallback on this path or any other.
        """
        payload = RecoverRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        clock = deps.clock()

        issued, user = login.recover_with_code(
            challenge_id=payload.validated_data["challenge_id"],
            recovery_code=payload.validated_data["recovery_code"],
            instant=clock.now(),
            remote_addr=deps.remote_addr(request),
            user_agent=deps.user_agent(request),
        )
        response = Response(
            {
                "authenticated": True,
                "auth_level": issued.auth_level,
                "actor_id": str(user.id),
                "school_id": str(user.school_id),
                "auth_time": issued.auth_time.isoformat(),
            }
        )
        set_session_cookie(response, issued.token)
        return response


class LogoutView(APIView):
    """POST /auth/logout -- revoke the current session."""

    @extend_schema(
        operation_id="auth_logout",
        summary="Revoke the current session",
        request=None,
        responses={200: RevokedResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Revoke the caller's session and clear its cookies."""
        session = deps.require_session(request)
        sessions.revoke_session(session, instant=deps.clock().now())
        response = Response({"revoked": True})
        clear_session_cookie(response)
        return response


class CurrentSessionView(APIView):
    """GET /auth/session -- describe the calling session."""

    @extend_schema(
        operation_id="auth_current_session",
        summary="Describe the calling session",
        responses={200: AuthenticatedResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the caller's identity and auth level."""
        context = deps.require_context(request)
        session = deps.require_session(request)
        return Response(
            {
                "authenticated": True,
                "auth_level": session.auth_level,
                "actor_id": str(context.actor_id),
                "school_id": str(context.school_id),
                "auth_time": context.auth_time.isoformat(),
                # For the product shell's header; never used for authorisation.
                "display_name": session.user.display_name,
                "login_name": session.user.login_name,
                "school_name": deps.school_name(context),
            }
        )


def _resolve_enrolling_account(request, validated):
    """Return (user, challenge) for an enrolment request.

    Two legitimate entry points:

      * an existing SESSION -- replacing or adding a factor while signed in; the
        Access check applies;
      * a valid CHALLENGE plus the password -- a FIRST enrolment, where the account
        has no session because its role requires a factor it does not yet have.
        Without this path such an account could never sign in at all.

    The challenge path still proves possession of the password, and enrolling one's
    own factor is inherently self-scoped, so no grant is consulted.
    """
    from ..services import login as login_service

    session = getattr(request, "school_session", None)
    if session is not None:
        return session.user, None

    challenge_id = validated.get("challenge_id")
    if challenge_id is None:
        raise Unauthenticated("error.unauthenticated")
    challenge = login_service.load_open_challenge(challenge_id, instant=deps.clock().now())
    return challenge.user, challenge


class EnrolStartView(APIView):
    """POST /auth/2fa/enroll -- begin enrolment, returning one-time secrets."""

    @extend_schema(
        operation_id="auth_factor_enrol_start",
        summary="Begin factor enrolment",
        request=PasswordConfirmRequest,
        responses={201: EnrolStartResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Confirm the password, then return provisioning data once.

        The response is the ONLY place the secret appears. It is never logged and
        never retrievable again, including by an administrator.
        """
        payload = PasswordConfirmRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        clock = deps.clock()
        user, _challenge = _resolve_enrolling_account(request, payload.validated_data)

        context = getattr(request, "school_context", None)
        if context is not None:
            deps.access_service().require_action(
                context, "auth.factor.manage_self", _self_scope(context)
            )

        with transaction.atomic():
            login.confirm_password(
                user=user,
                password=payload.validated_data["password"],
                instant=clock.now(),
            )
            enrolment = factors.start_enrolment(user=user, instant=clock.now())
            if context is not None:
                deps.platform().record_audit(
                    context,
                    "auth.factor.enrol_started",
                    enrolment.factor_id,
                    {"factor": "pending"},
                )
        return Response(enrolment.to_wire(), status=201)


class EnrolConfirmView(APIView):
    """POST /auth/2fa/confirm -- activate the factor, return recovery codes once."""

    @extend_schema(
        operation_id="auth_factor_enrol_confirm",
        summary="Activate the factor and receive recovery codes once",
        request=EnrolConfirmRequest,
        responses={201: RecoveryCodesResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Activate the pending factor and return ten single-use codes.

        The codes appear here and nowhere else. Only hashes are stored.
        """
        payload = EnrolConfirmRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        clock = deps.clock()
        user, challenge = _resolve_enrolling_account(request, payload.validated_data)

        context = getattr(request, "school_context", None)
        if context is not None:
            deps.access_service().require_action(
                context, "auth.factor.manage_self", _self_scope(context)
            )

        issued = None
        with transaction.atomic():
            login.confirm_password(
                user=user,
                password=payload.validated_data["password"],
                instant=clock.now(),
            )
            factor, codes = factors.confirm_enrolment(
                user=user,
                factor_id=payload.validated_data["factor_id"],
                code=payload.validated_data["code"],
                instant=clock.now(),
            )
            if context is not None:
                deps.platform().record_audit(
                    context, "auth.factor.activated", factor.id, {"state": "active"}
                )
            if challenge is not None:
                # First enrolment: activating the factor also completes the login,
                # so the account is not made to authenticate twice in a row.
                challenge.consumed_at = clock.now()
                challenge.save(update_fields=["consumed_at"])
                issued = sessions.create_session(
                    user=user,
                    auth_level=sessions.AUTH_LEVEL_PASSWORD_TOTP,
                    instant=clock.now(),
                    user_agent=deps.user_agent(request),
                    challenge_id=challenge.id,
                )

        response = Response(
            {
                "codes": list(codes),
                "generated_at": clock.now().isoformat(),
                "count": len(codes),
            },
            status=201,
        )
        if issued is not None:
            set_session_cookie(response, issued.token)
        return response


class ResetRequestView(APIView):
    """POST /auth/factor/reset-requests -- open a lost-device case."""

    @extend_schema(
        operation_id="auth_factor_reset_request",
        summary="Open a lost-device case",
        request=ResetRequestBody,
        responses={201: RecoveryCaseResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Open a pending case for a DIFFERENT person to approve."""
        payload = ResetRequestBody(data=request.data)
        payload.is_valid(raise_exception=True)
        context = deps.require_context(request)
        session = deps.require_session(request)

        access = deps.access_service()
        access.check(context, "auth.request_factor_reset", _self_scope(context))

        with transaction.atomic():
            case = factors.open_reset_case(
                user=session.user,
                reason=payload.validated_data["reason"],
                instant=deps.clock().now(),
            )
            deps.platform().record_audit(
                context, "auth.factor.reset_requested", case.id, {"state": case.state}
            )
        return Response(factors.describe_case(case), status=201)


class ResetApproveView(APIView):
    """POST /auth/factor/reset-requests/{case_id}/approve."""

    @extend_schema(
        operation_id="auth_factor_reset_approve",
        summary="Approve a lost-device case and reset the factor",
        request=None,
        responses={200: RecoveryCaseResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, case_id) -> Response:
        """Approve a case, reset the factor and revoke every session it authorised.

        Requires ``auth.factor.reset_other`` AND fresh 2FA. The approver may never be
        the subject.
        """
        context = deps.require_context(request)
        session = deps.require_session(request)

        access = deps.access_service()
        access.require_action(context, "auth.factor.reset_other", _school_scope(context))

        with transaction.atomic():
            case, revoked = factors.approve_reset_case(
                case_id=case_id, approver=session.user, instant=deps.clock().now()
            )
            platform = deps.platform()
            platform.record_audit(
                context,
                "auth.factor.reset_approved",
                case.id,
                {"subject_user_id": str(case.user_id), "sessions_revoked": revoked},
            )
            platform.append_event(
                context,
                "FactorReset.v1",
                case.user_id,
                case.version,
                {"user_id": str(case.user_id), "case_id": str(case.id)},
            )
        return Response(factors.describe_case(case))


# --- helpers ---------------------------------------------------------------


def _deployment_school_id():
    """Return the school this deployment serves.

    From configuration, never from the request. One campus per deployment is the
    product's tenancy model, so a login cannot name a different school.
    """
    import uuid

    from django.conf import settings

    return uuid.UUID(str(settings.SCHOOL_ID))


def _self_scope(context):
    """Return ScopeFacts describing the actor acting on their own account."""
    from contracts.scope import ScopeFacts

    return ScopeFacts(
        resource_school_id=context.school_id,
        subject_person_id=context.actor_id,
        effective_date=school_date(context.auth_time),
    )


def _school_scope(context):
    """Return ScopeFacts describing a school-wide action."""
    from contracts.scope import ScopeFacts

    return ScopeFacts(
        resource_school_id=context.school_id,
        effective_date=school_date(context.auth_time),
    )


def _fill_identity(response: Response, session_id) -> Response:
    """Populate actor and school on a response built before the row was read."""
    from ..models import Session

    row = Session.objects.filter(id=session_id).values("user_id", "school_id").first()
    if row is not None:
        response.data["actor_id"] = str(row["user_id"])
        response.data["school_id"] = str(row["school_id"])
    return response
