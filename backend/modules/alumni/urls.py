"""URL patterns for M10, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AlumniCollectionView,
    AlumniContactView,
    AlumniExportView,
    CandidateApproveView,
    CandidateCollectionView,
)

app_name = "alumni"

urlpatterns = [
    path("alumni/candidates", CandidateCollectionView.as_view(), name="candidate-collection"),
    path(
        "alumni/candidates/<uuid:candidate_id>/approve",
        CandidateApproveView.as_view(),
        name="candidate-approve",
    ),
    path("alumni", AlumniCollectionView.as_view(), name="alumni-collection"),
    path(
        "alumni/<uuid:profile_id>/contact",
        AlumniContactView.as_view(),
        name="alumni-contact",
    ),
    path("alumni/exports", AlumniExportView.as_view(), name="alumni-exports"),
]
