"""URL patterns for M13, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    ExportCollectionView,
    ExportDetailView,
    ExportDownloadView,
    ImportCollectionView,
    ImportCommitView,
    ImportDetailView,
    ImportErrorsView,
    ImportTemplateView,
    ReportCardCollectionView,
    ReportCardDetailView,
    ReportDetailView,
    ReportDownloadView,
)

app_name = "exchange"

urlpatterns = [
    path("imports", ImportCollectionView.as_view(), name="import-collection"),
    path("imports/<uuid:job_id>", ImportDetailView.as_view(), name="import-detail"),
    path("imports/<uuid:job_id>/commit", ImportCommitView.as_view(), name="import-commit"),
    path("imports/<uuid:job_id>/errors", ImportErrorsView.as_view(), name="import-errors"),
    path(
        "import-templates/<str:dataset>",
        ImportTemplateView.as_view(),
        name="import-template",
    ),
    path("exports", ExportCollectionView.as_view(), name="export-collection"),
    path("exports/<uuid:job_id>", ExportDetailView.as_view(), name="export-detail"),
    path(
        "exports/<uuid:job_id>/download",
        ExportDownloadView.as_view(),
        name="export-download",
    ),
    path("reportcards", ReportCardCollectionView.as_view(), name="reportcard-collection"),
    path("reportcards/<uuid:job_id>", ReportCardDetailView.as_view(), name="reportcard-detail"),
    path("reports/<uuid:report_id>", ReportDetailView.as_view(), name="report-detail"),
    path(
        "reports/<uuid:report_id>/download",
        ReportDownloadView.as_view(),
        name="report-download",
    ),
]
