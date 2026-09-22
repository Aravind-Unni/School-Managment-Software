"""URL patterns for M05, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AssessmentApproveView,
    AssessmentCollectionView,
    AssessmentDetailView,
    AssessmentPublicationView,
    AssessmentReopenView,
    AssessmentSubmitView,
    EvidenceViewView,
    ResultEvidenceView,
    ResultPatchView,
)
from .api.views_schedule import AssessmentCalendarView, ExamScheduleView
from .api.views_student_results import StudentResultsView

app_name = "assessment"

urlpatterns = [
    path("assessments", AssessmentCollectionView.as_view(), name="assessment-collection"),
    path("exam-schedules", ExamScheduleView.as_view(), name="exam-schedules"),
    path("assessment-calendar", AssessmentCalendarView.as_view(), name="assessment-calendar"),
    path(
        "students/<uuid:student_id>/results",
        StudentResultsView.as_view(),
        name="student-results",
    ),
    path(
        "assessments/<uuid:assessment_id>",
        AssessmentDetailView.as_view(),
        name="assessment-detail",
    ),
    path(
        "assessments/<uuid:assessment_id>/results/<uuid:student_id>",
        ResultPatchView.as_view(),
        name="result-patch",
    ),
    path(
        "assessments/<uuid:assessment_id>/submit",
        AssessmentSubmitView.as_view(),
        name="assessment-submit",
    ),
    path(
        "assessments/<uuid:assessment_id>/approve",
        AssessmentApproveView.as_view(),
        name="assessment-approve",
    ),
    path(
        "assessments/<uuid:assessment_id>/publication",
        AssessmentPublicationView.as_view(),
        name="assessment-publication",
    ),
    path(
        "assessments/<uuid:assessment_id>/reopen",
        AssessmentReopenView.as_view(),
        name="assessment-reopen",
    ),
    path(
        "results/<uuid:result_id>/evidence",
        ResultEvidenceView.as_view(),
        name="result-evidence",
    ),
    path(
        "results/<uuid:result_id>/evidence/<uuid:binding_id>/view",
        EvidenceViewView.as_view(),
        name="evidence-view",
    ),
]
