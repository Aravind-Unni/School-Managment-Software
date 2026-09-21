"""URL routes for M06 performance."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    DashboardView,
    ExportView,
    InterventionCollectionView,
    MeetingCollectionView,
    RebuildView,
    WarningAcknowledgeView,
    WarningDismissView,
    WarningRuleCollectionView,
)
from .api.views_warnings import WarningCollectionView

urlpatterns = [
    path("performance/dashboard", DashboardView.as_view(), name="performance-dashboard"),
    path("performance/export", ExportView.as_view(), name="performance-export"),
    path("performance/rebuild", RebuildView.as_view(), name="performance-rebuild"),
    path("warning-rules", WarningRuleCollectionView.as_view(), name="warning-rules"),
    path("warnings", WarningCollectionView.as_view(), name="warnings"),
    path(
        "warnings/<uuid:warning_id>/acknowledge",
        WarningAcknowledgeView.as_view(),
        name="warning-acknowledge",
    ),
    path(
        "warnings/<uuid:warning_id>/dismiss",
        WarningDismissView.as_view(),
        name="warning-dismiss",
    ),
    path("interventions", InterventionCollectionView.as_view(), name="interventions"),
    path("meetings", MeetingCollectionView.as_view(), name="meetings"),
]
