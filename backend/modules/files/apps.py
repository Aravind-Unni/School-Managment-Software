"""M12 files Django app."""

from __future__ import annotations

from django.apps import AppConfig


class FilesConfig(AppConfig):
    """Registers private file lifecycle tables."""

    name = "modules.files"
    label = "files"
    verbose_name = "M12 compressed answer sheet evidence and private files"
    default_auto_field = "django.db.models.BigAutoField"
