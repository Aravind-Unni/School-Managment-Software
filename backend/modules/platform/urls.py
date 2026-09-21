"""URL patterns for M14, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AuditCollectionView,
    HealthLiveView,
    HealthReadyView,
    JobDetailView,
    JobRetryView,
    RestoreRehearsalCollectionView,
)

app_name = "platform"

urlpatterns = [
    path("health/live", HealthLiveView.as_view(), name="health-live"),
    path("health/ready", HealthReadyView.as_view(), name="health-ready"),
    path("jobs/<uuid:job_id>", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/retry", JobRetryView.as_view(), name="job-retry"),
    path("audit", AuditCollectionView.as_view(), name="audit-collection"),
    path(
        "operations/restore-rehearsals",
        RestoreRehearsalCollectionView.as_view(),
        name="restore-rehearsals",
    ),
]
