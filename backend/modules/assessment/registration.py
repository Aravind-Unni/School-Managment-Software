"""M05's declaration to the host."""

from __future__ import annotations

from contracts.registration import FrontendRoute, HealthCheck, ModuleRegistration

from .permissions import PERMISSION_CODES

REGISTRATION = ModuleRegistration(
    id="M05",
    slug="assessment",
    api_prefix="/api/v1/",
    api_path_roots=("assessments/", "results/"),
    django_app="modules.assessment",
    permission_prefixes=("assessment.", "marks.", "results.", "evidence."),
    permission_codes=PERMISSION_CODES,
    frontend_routes=(
        FrontendRoute(
            path="/assessment/setup",
            component="AssessmentSetupPage",
            nav_label_key="nav.assessment_setup",
            required_permission="assessment.manage",
        ),
        FrontendRoute(
            path="/assessment/:assessmentId/marking",
            component="MarkingGridPage",
            required_permission="marks.edit",
        ),
        FrontendRoute(
            path="/assessment/:assessmentId/publish",
            component="PublishPreviewPage",
            required_permission="results.publish",
        ),
        FrontendRoute(
            path="/assessment/results/:resultId",
            component="PublishedResultPage",
            nav_label_key="nav.assessment_results",
            required_permission="evidence.view",
        ),
    ),
    consumers=("access", "registry", "files", "platform", "clock"),
    middleware=(),
    public_paths=(),
    scheduled_jobs=(),
    migration_dependencies=(),
    health_checks=(
        HealthCheck(
            name="assessment_tables",
            callable_path="modules.assessment.health.tables_ready",
        ),
    ),
)
