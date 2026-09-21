"""URL patterns for M12, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    FileBytesView,
    FileStatusView,
    QualityConfirmationView,
    ReprocessView,
    RetentionHoldView,
    UploadBytesView,
    UploadCollectionView,
    UploadCompleteView,
)

app_name = "files"

urlpatterns = [
    path("uploads", UploadCollectionView.as_view(), name="upload-collection"),
    path(
        "uploads/<uuid:upload_id>/complete",
        UploadCompleteView.as_view(),
        name="upload-complete",
    ),
    path(
        "quarantine/<uuid:upload_id>",
        UploadBytesView.as_view(),
        name="upload-bytes",
    ),
    path("files/<uuid:file_id>/status", FileStatusView.as_view(), name="file-status"),
    path(
        "files/<uuid:file_id>/quality-confirmation",
        QualityConfirmationView.as_view(),
        name="quality-confirmation",
    ),
    path("files/<uuid:file_id>/reprocess", ReprocessView.as_view(), name="reprocess"),
    path(
        "files/<uuid:file_id>/retention-hold",
        RetentionHoldView.as_view(),
        name="retention-hold",
    ),
    path("file-bytes/<uuid:file_id>", FileBytesView.as_view(), name="file-bytes"),
]
