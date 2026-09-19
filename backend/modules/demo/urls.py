"""URL patterns for the demo module, mounted at its declared api_prefix."""

from __future__ import annotations

from django.urls import path

from .views import NoteCollectionView, NoteDetailView

app_name = "demo"

urlpatterns = [
    path("notes/", NoteCollectionView.as_view(), name="note-collection"),
    path("notes/<uuid:note_id>/", NoteDetailView.as_view(), name="note-detail"),
]
