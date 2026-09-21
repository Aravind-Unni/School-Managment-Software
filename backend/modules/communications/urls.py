"""URL patterns for M11, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    DeliveryDetailView,
    MessageCollectionView,
    NoticeCollectionView,
    NoticePublishView,
    SmsCallbackView,
)

app_name = "communications"

urlpatterns = [
    path("notices", NoticeCollectionView.as_view(), name="notice-collection"),
    path(
        "notices/<uuid:notice_id>/publish",
        NoticePublishView.as_view(),
        name="notice-publish",
    ),
    path("messages", MessageCollectionView.as_view(), name="message-collection"),
    path(
        "deliveries/<uuid:delivery_id>",
        DeliveryDetailView.as_view(),
        name="delivery-detail",
    ),
    path(
        "sms/callback/<str:provider>",
        SmsCallbackView.as_view(),
        name="sms-callback",
    ),
]
