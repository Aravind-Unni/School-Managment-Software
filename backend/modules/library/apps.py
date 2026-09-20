"""M09 library Django app."""

from __future__ import annotations

from django.apps import AppConfig


class LibraryConfig(AppConfig):
    """Registers catalogue and loan tables."""

    name = "modules.library"
    label = "library"
    verbose_name = "M09 library catalogue lending and returns"
    default_auto_field = "django.db.models.BigAutoField"
