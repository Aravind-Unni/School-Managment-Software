"""M07's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M07",
    slug="fees",
    api_prefix="/api/v1/",
    api_path_roots=(
        "fee-plans/",
        "charges/",
        "payments/",
        "concessions/",
        "refunds/",
        "fees/",
    ),
    django_app="modules.fees",
    permission_prefixes=("fees.",),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/fees/setup",
            component="FeeSetupPage",
            nav_label_key="nav.fees_setup",
            required_permission="fees.configure",
        ),
        FrontendRoute(
            path="/fees/statement",
            component="FeeStatementPage",
            nav_label_key="nav.fees_statement",
            required_permission="fees.read",
        ),
        FrontendRoute(
            path="/fees/collect",
            component="FeeCollectionPage",
            nav_label_key="nav.fees_collect",
            required_permission="fees.record_payment",
        ),
        FrontendRoute(
            path="/fees/receipt/:paymentId",
            component="FeeReceiptPage",
            required_permission="fees.read",
        ),
        FrontendRoute(
            path="/fees/overdue",
            component="FeeOverduePage",
            nav_label_key="nav.fees_overdue",
            required_permission="fees.read",
        ),
        FrontendRoute(
            path="/fees/concessions",
            component="FeeConcessionPage",
            nav_label_key="nav.fees_concessions",
            required_permission="fees.concede",
        ),
    ),
    consumers=("access", "registry", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="fees_tables",
            callable_path="modules.fees.health.tables_ready",
        ),
    ),
)
