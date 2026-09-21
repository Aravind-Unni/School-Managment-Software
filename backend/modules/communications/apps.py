"""M11 communications Django app."""

from __future__ import annotations

from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    """Registers notice, template and delivery tables."""

    name = "modules.communications"
    label = "communications"
    verbose_name = "M11 notices and third-party SMS"
    default_auto_field = "django.db.models.BigAutoField"
