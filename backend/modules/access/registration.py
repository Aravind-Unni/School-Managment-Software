"""M01's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import CATALOGUE

#: M01 mounts under the shared /api/v1/ root and owns four path roots. The host
#: refuses two modules claiming the same root, so this is checkable rather than a
#: convention.
REGISTRATION = ModuleRegistration(
    id="M01",
    slug="access",
    api_prefix="/api/v1/",
    api_path_roots=("auth/", "sessions/", "roles/", "accounts/"),
    django_app="modules.access",
    permission_prefixes=("auth.", "roles.", "accounts."),
    permission_codes=tuple(spec.code for spec in CATALOGUE),
    frontend_routes=(
        FrontendRoute(path="/login", component="LoginPage", nav_label_key=None),
        FrontendRoute(path="/2fa", component="TwoFactorChallengePage", nav_label_key=None),
        FrontendRoute(
            path="/settings/security",
            component="SecuritySettingsPage",
            nav_label_key="nav.security",
            required_permission="auth.factor.manage_self",
        ),
        FrontendRoute(
            path="/settings/roles",
            component="RoleEditorPage",
            nav_label_key="nav.roles",
            required_permission="roles.manage",
        ),
    ),
    #: M01 is Access, so it does NOT consume the access port. It consumes a fake
    #: Registry only, plus Platform for audit/outbox and the clock.
    consumers=("registry", "platform", "clock"),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(name="access_tables", callable_path="modules.access.health.check_tables"),
        HealthCheck(
            name="totp_key_present",
            callable_path="modules.access.health.check_totp_key",
        ),
    ),
)
