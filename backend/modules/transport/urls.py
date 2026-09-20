"""URL patterns for M08, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AdjustmentCollectionView,
    BillingRequestRetryView,
    BillingRunView,
    BusCollectionView,
    ParticipantListView,
    ParticipationCollectionView,
    ParticipationDetailView,
    ReconciliationView,
)

app_name = "transport"

urlpatterns = [
    path("buses", BusCollectionView.as_view(), name="bus-collection"),
    path(
        "bus-participations",
        ParticipationCollectionView.as_view(),
        name="participation-collection",
    ),
    path(
        "bus-participations/<uuid:participation_id>",
        ParticipationDetailView.as_view(),
        name="participation-detail",
    ),
    path("bus-billing-runs", BillingRunView.as_view(), name="billing-run"),
    path("bus-participants", ParticipantListView.as_view(), name="participant-list"),
    path(
        "bus-billing-reconciliation",
        ReconciliationView.as_view(),
        name="billing-reconciliation",
    ),
    path("bus-adjustments", AdjustmentCollectionView.as_view(), name="adjustment-collection"),
    path(
        "bus-billing-requests/<uuid:billing_request_id>/retry",
        BillingRequestRetryView.as_view(),
        name="billing-request-retry",
    ),
]
