"""URL patterns for M07, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    ChargeCollectionView,
    ConcessionCollectionView,
    DailyCollectionsView,
    FeePlanCollectionView,
    FeeStatementView,
    OverdueListView,
    PaymentCollectionView,
    PaymentDetailView,
    PaymentReversalView,
    RefundCollectionView,
)
from .api.views_setup import ChargeClassesView, FeeHeadCollectionView

app_name = "fees"

urlpatterns = [
    path("fee-plans", FeePlanCollectionView.as_view(), name="fee-plan-collection"),
    path("charges", ChargeCollectionView.as_view(), name="charge-collection"),
    path("payments", PaymentCollectionView.as_view(), name="payment-collection"),
    path("payments/<uuid:payment_id>", PaymentDetailView.as_view(), name="payment-detail"),
    path(
        "payments/<uuid:payment_id>/reversals",
        PaymentReversalView.as_view(),
        name="payment-reversal",
    ),
    path("concessions", ConcessionCollectionView.as_view(), name="concession-collection"),
    path("refunds", RefundCollectionView.as_view(), name="refund-collection"),
    path(
        "fees/students/<uuid:student_id>/fee-statement",
        FeeStatementView.as_view(),
        name="fee-statement",
    ),
    path("fee-heads", FeeHeadCollectionView.as_view(), name="fee-head-collection"),
    path("fees/charge-classes", ChargeClassesView.as_view(), name="charge-classes"),
    path("fees/overdue", OverdueListView.as_view(), name="overdue-list"),
    path("fees/daily-collections", DailyCollectionsView.as_view(), name="daily-collections"),
]
