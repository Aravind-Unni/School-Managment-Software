"""URL patterns for M04, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    EntryCorrectionView,
    PeriodListView,
    SessionCollectionView,
    SessionDetailView,
    SessionSubmitView,
    SummaryView,
)

app_name = "attendance"

urlpatterns = [
    path("attendance/periods", PeriodListView.as_view(), name="period-list"),
    path("attendance/sessions", SessionCollectionView.as_view(), name="session-collection"),
    path(
        "attendance/sessions/<uuid:session_id>/submit",
        SessionSubmitView.as_view(),
        name="session-submit",
    ),
    path(
        "attendance/sessions/<uuid:session_id>",
        SessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "attendance/entries/<uuid:entry_id>/corrections",
        EntryCorrectionView.as_view(),
        name="entry-correction",
    ),
    path("attendance/summary", SummaryView.as_view(), name="summary"),
]
