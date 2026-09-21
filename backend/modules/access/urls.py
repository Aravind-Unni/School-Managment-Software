"""URL patterns for M01, mounted at its declared /api/v1/ prefix.

The path roots here must match ``REGISTRATION.api_path_roots``; a test asserts it, so
a new root cannot be added without declaring it for collision checking.
"""

from __future__ import annotations

from django.urls import path

from .api import admin_views, auth_views

app_name = "access"

urlpatterns = [
    # auth/
    path("auth/login", auth_views.LoginView.as_view(), name="login"),
    path("auth/2fa/verify", auth_views.TotpVerifyView.as_view(), name="totp-verify"),
    path("auth/2fa/enroll", auth_views.EnrolStartView.as_view(), name="enrol-start"),
    path("auth/2fa/confirm", auth_views.EnrolConfirmView.as_view(), name="enrol-confirm"),
    path("auth/2fa/recover", auth_views.RecoverView.as_view(), name="recover"),
    path("auth/logout", auth_views.LogoutView.as_view(), name="logout"),
    path("auth/session", auth_views.CurrentSessionView.as_view(), name="current-session"),
    path("auth/capabilities", auth_views.CapabilitiesView.as_view(), name="capabilities"),
    path(
        "auth/factor/reset-requests",
        auth_views.ResetRequestView.as_view(),
        name="reset-request",
    ),
    path(
        "auth/factor/reset-requests/<uuid:case_id>/approve",
        auth_views.ResetApproveView.as_view(),
        name="reset-approve",
    ),
    # sessions/
    path("sessions", admin_views.SessionCollectionView.as_view(), name="session-list"),
    path(
        "sessions/<uuid:session_id>/revoke",
        admin_views.SessionRevokeView.as_view(),
        name="session-revoke",
    ),
    # roles/
    path("roles", admin_views.RoleCollectionView.as_view(), name="role-list"),
    path(
        "roles/<uuid:role_id>/grants",
        admin_views.RoleGrantsView.as_view(),
        name="role-grants",
    ),
    # accounts/
    path("accounts", admin_views.AccountCollectionView.as_view(), name="account-list"),
]
